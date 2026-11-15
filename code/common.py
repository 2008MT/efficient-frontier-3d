"""Shared data preparation and portfolio mathematics.

All returns are weekly simple returns in US dollars, measured Friday to Friday.
"""
import os
import numpy as np
import pandas as pd
from scipy.optimize import minimize, linprog

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

ASSETS = ["NVDA", "VOO", "ARU", "SGLN"]
COLORS = {"NVDA": "#1baf7a", "VOO": "#2a78d6", "ARU": "#e34948", "SGLN": "#eda100"}
WEEKS = 52

# Sample periods (dates are week-ending Fridays)
IS_START = "2015-07-31"     # first weekly return of the estimation sample
IS_END = "2025-07-25"       # last week before the original analysis (28-29 July 2025)
HO_END = "2026-11-13"       # end of the hold-out period added in November 2026

# Maximum-Sharpe weights published in the first version of this project (July 2025)
V1_WEIGHTS = np.array([0.286, 0.000, 0.061, 0.653])


# ----------------------------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------------------------
def load_daily():
    path = os.path.join(ROOT, "data", "prices_daily.csv")
    if not os.path.exists(path):
        raise FileNotFoundError("data/prices_daily.csv not found: run  python fetch_data.py  first")
    return pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()


def weekly_prices_usd(daily=None):
    """Friday (last available) price of each asset in US dollars, dividends reinvested.

    Yahoo stamps a daily exchange-rate bar with the rate at the start of that UTC day, so the rate
    that applies to the end of day D is the one in the next bar. Using the same-day bar instead
    mixes a price with an exchange rate from about 16 hours earlier. Shifting by one bar raises the
    weekly correlation between SGLN converted to dollars and the fund's own dollar line (IGLN)
    from 0.92 to 0.97 (see results/part1.json, "gold_check").
    """
    d = load_daily() if daily is None else daily
    fx = d[["AUDUSD", "GBPUSD"]].dropna()
    fx_end_of_day = fx.shift(-1).reindex(d.index)
    d = d.assign(AUDUSD_EOD=fx_end_of_day.AUDUSD, GBPUSD_EOD=fx_end_of_day.GBPUSD)
    d = d.loc[:d[ASSETS].dropna(how="all").index.max()]
    w = d.resample("W-FRI").last().ffill()
    usd = pd.DataFrame(index=w.index)
    usd["NVDA"] = w.NVDA
    usd["VOO"] = w.VOO
    usd["ARU"] = w.ARU * w.AUDUSD_EOD            # A$ -> US$
    usd["SGLN"] = w.SGLN * w.GBPUSD_EOD / 100    # pence -> US$
    usd["SGLN_same_day_fx"] = w.SGLN * w.GBPUSD / 100
    usd["IGLN"] = w.IGLN
    usd["IRX"] = w.IRX
    return usd


def load_weekly():
    """Weekly simple returns in US dollars and the weekly risk-free return.

    Returns (R, rf): R is a DataFrame with one column per asset, rf a Series. The risk-free return
    for a week is the 13-week Treasury-bill yield observed at the start of that week, divided by 52.
    """
    p = weekly_prices_usd()
    R = p[ASSETS].pct_change()
    rf = (p.IRX.shift(1) / 100 / WEEKS).rename("rf")
    R, rf = R.loc[IS_START:HO_END], rf.loc[IS_START:HO_END]
    if R.isna().any().any():
        raise ValueError("missing weekly returns")
    return R, rf


def in_sample(x):
    return x.loc[IS_START:IS_END]


def hold_out(x):
    return x.loc[pd.Timestamp(IS_END) + pd.Timedelta(days=1):HO_END]


def moments(R, rf):
    """Annualised mean excess return vector, covariance matrix and mean risk-free rate."""
    mu = (R.sub(rf, axis=0)).mean().values * WEEKS
    cov = R.cov().values * WEEKS
    return mu, cov, rf.mean() * WEEKS


# ----------------------------------------------------------------------------------------------
# Portfolio statistics
# ----------------------------------------------------------------------------------------------
def simplex_grid(n):
    """All long-only weight vectors on four assets whose weights are multiples of 1/n."""
    out = []
    for a in range(n + 1):
        for b in range(n + 1 - a):
            for c in range(n + 1 - a - b):
                out.append((a, b, c, n - a - b - c))
    return np.array(out, dtype=float) / n


def port_stats(W, mu, cov):
    """Annualised excess return, volatility and Sharpe ratio of each row of W."""
    W = np.atleast_2d(W)
    ret = W @ mu
    vol = np.sqrt(np.einsum("ij,jk,ik->i", W, cov, W))
    return ret, vol, ret / vol


def cvar(W, R, alpha=0.95):
    """Historical expected shortfall of weekly returns, as a positive loss: the average loss in
    the worst (1 - alpha) share of weeks."""
    W = np.atleast_2d(W)
    X = np.asarray(R) @ W.T                     # weeks x portfolios
    k = int(np.ceil((1 - alpha) * X.shape[0]))
    worst = np.partition(X, k - 1, axis=0)[:k]
    return -worst.mean(axis=0)


def gaussian_cvar(mean_w, sd_w, alpha=0.95):
    """Expected shortfall of a normal weekly return with the given mean and standard deviation."""
    from scipy.stats import norm
    z = norm.ppf(1 - alpha)
    return -mean_w + sd_w * norm.pdf(z) / (1 - alpha)


def perf(r, rf):
    """Performance summary of a weekly return series."""
    r, rf = np.asarray(r), np.asarray(rf)
    ex = r - rf
    wealth = np.cumprod(1 + r)
    years = len(r) / WEEKS
    dd = wealth / np.maximum.accumulate(np.concatenate([[1.0], wealth]))[1:] - 1
    return {
        "mean_excess": float(ex.mean() * WEEKS),
        "cagr": float(wealth[-1] ** (1 / years) - 1),
        "vol": float(r.std(ddof=1) * np.sqrt(WEEKS)),
        "sharpe": float(ex.mean() / ex.std(ddof=1) * np.sqrt(WEEKS)),
        "max_drawdown": float(dd.min()),
        "total_return": float(wealth[-1] - 1),
        "weeks": int(len(r)),
    }


# ----------------------------------------------------------------------------------------------
# Optimisation (long only, fully invested)
# ----------------------------------------------------------------------------------------------
def _solve(fun, jac, n, cons, x0=None):
    x0 = np.full(n, 1 / n) if x0 is None else x0
    res = minimize(fun, x0, jac=jac, bounds=[(0, 1)] * n, constraints=cons, method="SLSQP",
                   options={"ftol": 1e-12, "maxiter": 500})
    w = np.clip(res.x, 0, None)
    return w / w.sum()


def min_variance(cov, mu=None, target=None):
    """Minimum-variance weights, optionally for a target expected (excess) return."""
    n = len(cov)
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1, "jac": lambda w: np.ones(n)}]
    if target is not None:
        cons.append({"type": "eq", "fun": lambda w: w @ mu - target, "jac": lambda w: mu})
    return _solve(lambda w: w @ cov @ w, lambda w: 2 * cov @ w, n, cons)


def max_sharpe(mu, cov):
    """Maximum-Sharpe weights. Solved as the convex problem  min y'Sy  s.t.  mu'y = 1, y >= 0,
    then rescaled to sum to one. If no asset has a positive mean excess return the
    minimum-variance portfolio is returned."""
    n = len(mu)
    if mu.max() <= 0:
        return min_variance(cov)
    y0 = np.full(n, 1.0) / max(mu.sum(), 1e-6) if mu.sum() > 0 else np.eye(n)[mu.argmax()] / mu.max()
    res = minimize(lambda y: y @ cov @ y, y0, jac=lambda y: 2 * cov @ y, bounds=[(0, None)] * n,
                   constraints=[{"type": "eq", "fun": lambda y: y @ mu - 1, "jac": lambda y: mu}],
                   method="SLSQP", options={"ftol": 1e-14, "maxiter": 1000})
    y = np.clip(res.x, 0, None)
    w = y / y.sum()
    # polish from a few starting points on the Sharpe ratio itself (guards against a poor start)
    best, best_s = w, (w @ mu) / np.sqrt(w @ cov @ w)
    for x0 in [w] + list(np.eye(n)) + [np.full(n, 1 / n)]:
        cand = _solve(lambda v: -(v @ mu) / np.sqrt(v @ cov @ v), None, n,
                      [{"type": "eq", "fun": lambda v: v.sum() - 1}], x0=0.98 * x0 + 0.02 / n)
        s = (cand @ mu) / np.sqrt(cand @ cov @ cand)
        if s > best_s + 1e-10:
            best, best_s = cand, s
    return best


def risk_parity(cov):
    """Equal-risk-contribution weights: every asset contributes the same share of portfolio variance."""
    n = len(cov)
    res = minimize(lambda y: 0.5 * y @ cov @ y - np.log(y).sum() / n,
                   np.full(n, 1.0), jac=lambda y: cov @ y - 1 / (n * y),
                   bounds=[(1e-8, None)] * n, method="L-BFGS-B", options={"ftol": 1e-14, "gtol": 1e-10})
    return res.x / res.x.sum()


def frontier(mu, cov, n_points=80):
    """Exact long-only efficient frontier, from the minimum-variance portfolio to the highest-return asset."""
    w0 = min_variance(cov)
    targets = np.linspace(w0 @ mu, mu.max(), n_points)
    W = np.array([w0] + [min_variance(cov, mu, t) for t in targets[1:-1]] + [np.eye(len(mu))[mu.argmax()]])
    return W


def min_cvar(R, mu=None, target=None, alpha=0.95):
    """Minimum expected-shortfall weights (Rockafellar and Uryasev, 2000), solved as a linear programme.

    Variables: weights w (n), value-at-risk level a (1), shortfalls u (T).
    Minimise  a + sum(u) / ((1 - alpha) T)   s.t.   u_t >= -r_t'w - a,  u >= 0,  sum(w) = 1,  w >= 0.
    """
    X = np.asarray(R)
    T, n = X.shape
    c = np.concatenate([np.zeros(n), [1.0], np.full(T, 1 / ((1 - alpha) * T))])
    A_ub = np.hstack([-X, -np.ones((T, 1)), -np.eye(T)])
    b_ub = np.zeros(T)
    A_eq = [np.concatenate([np.ones(n), [0.0], np.zeros(T)])]
    b_eq = [1.0]
    if target is not None:
        A_eq.append(np.concatenate([mu, [0.0], np.zeros(T)]))
        b_eq.append(target)
    bounds = [(0, 1)] * n + [(None, None)] + [(0, None)] * T
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=np.array(A_eq), b_eq=b_eq, bounds=bounds, method="highs")
    if not res.success:
        raise RuntimeError(res.message)
    w = np.clip(res.x[:n], 0, None)
    return w / w.sum()
