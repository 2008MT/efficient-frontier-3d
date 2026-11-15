"""Part 2. Out-of-sample tests.

(a) Rolling test: every four weeks, estimate means and covariances on the previous 156 weeks only,
    form each portfolio, and hold it for the next four weeks. Nothing from the future is used.
(b) Hold-out test: portfolios fixed with data to 25 July 2025 (including the maximum-Sharpe weights
    published in the first version of this project) are followed to 13 November 2026.

Output: results/part2.json, results/oos_wealth.csv
"""
import json, os
import numpy as np
import pandas as pd
from common import (ASSETS, ROOT, WEEKS, IS_END, V1_WEIGHTS, load_weekly, in_sample, hold_out, moments, perf,
                    min_variance, max_sharpe, risk_parity)

WINDOW = 156       # weeks of data used for each estimate (three years)
HOLD = 4           # weeks between rebalances

RULES = {
    "max_sharpe": lambda mu, cov: max_sharpe(mu, cov),
    "min_variance": lambda mu, cov: min_variance(cov),
    "risk_parity": lambda mu, cov: risk_parity(cov),
    "equal_weight": lambda mu, cov: np.full(len(mu), 1 / len(mu)),
}


def run_fixed(R, target, hold=HOLD):
    """Weekly returns of a portfolio rebalanced to `target` every `hold` weeks (weights drift in between).
    Returns (returns, average one-way turnover per rebalance)."""
    X = R.values
    w = target.copy()
    out, turn = np.empty(len(X)), []
    for t in range(len(X)):
        if t > 0 and t % hold == 0:
            turn.append(np.abs(target - w).sum() / 2)
            w = target.copy()
        out[t] = w @ X[t]
        w = w * (1 + X[t]) / (1 + out[t])
    return out, float(np.mean(turn)) if turn else 0.0


def run_rolling(R, rf, window=WINDOW, hold=HOLD):
    """Rolling backtest of every rule. Returns (DataFrame of weekly returns, weights history, turnover)."""
    X, F = R.values, rf.values
    n = len(X)
    rets = {k: np.full(n, np.nan) for k in RULES}
    hist = {k: [] for k in RULES}
    turn = {k: [] for k in RULES}
    w = {k: None for k in RULES}
    for t in range(window, n):
        if (t - window) % hold == 0:
            past, past_rf = X[t - window:t], F[t - window:t]
            mu = (past - past_rf[:, None]).mean(axis=0) * WEEKS
            cov = np.cov(past, rowvar=False) * WEEKS
            for k, rule in RULES.items():
                target = rule(mu, cov)
                if w[k] is not None:
                    turn[k].append(np.abs(target - w[k]).sum() / 2)
                w[k] = target
                hist[k].append((R.index[t], *target))
        for k in RULES:
            r = w[k] @ X[t]
            rets[k][t] = r
            w[k] = w[k] * (1 + X[t]) / (1 + r)
    rets = pd.DataFrame(rets, index=R.index).iloc[window:]
    hist = {k: pd.DataFrame(v, columns=["date"] + ASSETS).set_index("date") for k, v in hist.items()}
    turnover = {k: float(np.mean(v) * WEEKS / hold) for k, v in turn.items()}     # one-way, per year
    return rets, hist, turnover


def main():
    R, rf = load_weekly()
    out = {"design": {"window_weeks": WINDOW, "hold_weeks": HOLD}}

    # ---------------- (a) rolling ------------------------------------------------------------
    rets, hist, turnover = run_rolling(R, rf)
    rf_oos = rf.loc[rets.index]
    out["rolling"] = {"start": str(rets.index[0].date()), "end": str(rets.index[-1].date()), "weeks": int(len(rets)),
                      "rebalances": int(len(hist["max_sharpe"])), "strategies": {}}
    for k in RULES:
        p = perf(rets[k], rf_oos)
        p["turnover_per_year"] = turnover[k]
        p["mean_weights"] = dict(zip(ASSETS, hist[k].mean().round(4).tolist()))
        p["weight_range"] = {a: [float(hist[k][a].min()), float(hist[k][a].max())] for a in ASSETS}
        out["rolling"]["strategies"][k] = p
    for a in ASSETS:
        out["rolling"]["strategies"][a] = perf(R[a].loc[rets.index], rf_oos)

    # the Sharpe ratio the optimiser expected at each rebalance, against what followed
    X, F = R.values, rf.values
    expected = []
    for t in range(WINDOW, len(X), HOLD):
        past = X[t - WINDOW:t]
        mu = (past - F[t - WINDOW:t, None]).mean(axis=0) * WEEKS
        cov = np.cov(past, rowvar=False) * WEEKS
        w = max_sharpe(mu, cov)
        expected.append((w @ mu) / np.sqrt(w @ cov @ w))
    out["rolling"]["max_sharpe_expected_sharpe_mean"] = float(np.mean(expected))

    # sensitivity to the estimation window
    sens = {}
    for win in [104, 156, 260]:
        r_w, _, t_w = run_rolling(R, rf, window=win)
        common_idx = r_w.index[r_w.index >= R.index[260]]           # same evaluation period for all windows
        sens[str(win)] = {k: {"sharpe": perf(r_w[k].loc[common_idx], rf.loc[common_idx])["sharpe"],
                              "turnover_per_year": t_w[k]} for k in RULES}
    out["rolling"]["window_sensitivity"] = {"evaluation_start": str(R.index[260].date()), "by_window": sens}

    wealth = (1 + rets).cumprod()
    for a in ASSETS:
        wealth[a] = (1 + R[a].loc[rets.index]).cumprod()
    wealth.round(5).to_csv(os.path.join(ROOT, "results", "oos_wealth.csv"))
    for k in RULES:
        hist[k].round(4).to_csv(os.path.join(ROOT, "results", f"oos_weights_{k}.csv"))

    # ---------------- (b) hold-out -----------------------------------------------------------
    Ri, rfi = in_sample(R), in_sample(rf)
    Rh, rfh = hold_out(R), hold_out(rf)
    mu, cov, _ = moments(Ri, rfi)
    fixed = {
        "v1_max_sharpe": V1_WEIGHTS / V1_WEIGHTS.sum(),
        "max_sharpe": max_sharpe(mu, cov),
        "min_variance": min_variance(cov),
        "risk_parity": risk_parity(cov),
        "equal_weight": np.full(4, 0.25),
    }
    out["hold_out"] = {"start": str(Rh.index[0].date()), "end": str(Rh.index[-1].date()), "weeks": int(len(Rh)),
                       "rf_mean": float(rfh.mean() * WEEKS), "portfolios": {}}
    ho_wealth = pd.DataFrame(index=Rh.index)
    for k, w in fixed.items():
        r, _ = run_fixed(Rh, w)
        p = perf(r, rfh)
        p["weights"] = dict(zip(ASSETS, np.round(w, 4).tolist()))
        p["in_sample_sharpe"] = float((w @ mu) / np.sqrt(w @ cov @ w))
        p["in_sample_volatility"] = float(np.sqrt(w @ cov @ w))
        bh = (1 + Rh.values).cumprod(axis=0) @ w                    # buy and hold, no rebalancing
        p["total_return_buy_and_hold"] = float(bh[-1] - 1)
        out["hold_out"]["portfolios"][k] = p
        ho_wealth[k] = np.cumprod(1 + r)
    for i, a in enumerate(ASSETS):
        p = perf(Rh[a], rfh)
        p["in_sample_sharpe"] = float(mu[i] / np.sqrt(cov[i, i]))
        out["hold_out"]["portfolios"][a] = p
        ho_wealth[a] = (1 + Rh[a]).cumprod()
    ho_wealth.round(5).to_csv(os.path.join(ROOT, "results", "holdout_wealth.csv"))

    # how much the hold-out verdict depends on the day it ends: compare the published portfolio
    # with VOO at every possible end date from six months in
    tr = ho_wealth - 1
    later = tr.iloc[25:]
    ex = pd.DataFrame({k: np.diff(np.concatenate([[1.0], ho_wealth[k].values])) / np.concatenate([[1.0], ho_wealth[k].values[:-1]]) - rfh.values
                       for k in ["v1_max_sharpe", "VOO"]}, index=Rh.index)
    run_sharpe = (ex.expanding(26).mean() / ex.expanding(26).std() * np.sqrt(WEEKS)).dropna()
    out["hold_out"]["end_date_sensitivity"] = {
        "end_dates_considered": int(len(later)),
        "share_total_return_above_voo": float((later.v1_max_sharpe > later.VOO).mean()),
        "share_sharpe_above_voo": float((run_sharpe.v1_max_sharpe > run_sharpe.VOO).mean()),
        "end_dates_total_return_above_voo": int((later.v1_max_sharpe > later.VOO).sum()),
        "peak_total_return": float(tr.v1_max_sharpe.max()), "peak_date": str(tr.v1_max_sharpe.idxmax().date()),
        "sharpe_range_published": [float(run_sharpe.v1_max_sharpe.min()), float(run_sharpe.v1_max_sharpe.max())],
        "sharpe_range_voo": [float(run_sharpe.VOO.min()), float(run_sharpe.VOO.max())],
    }
    mu_h, cov_h, _ = moments(Rh, rfh)
    out["hold_out"]["correlations"] = Rh.corr().round(4).values.tolist()
    out["hold_out"]["asset_volatility"] = dict(zip(ASSETS, np.sqrt(np.diag(cov_h)).round(4).tolist()))

    with open(os.path.join(ROOT, "results", "part2.json"), "w") as f:
        json.dump(out, f, indent=1)

    # ---------------- console ----------------------------------------------------------------
    ro = out["rolling"]
    print(f"Rolling test {ro['start']} to {ro['end']}: {ro['weeks']} weeks, {ro['rebalances']} rebalances")
    print(f"{'':14}{'CAGR':>8}{'vol':>8}{'Sharpe':>8}{'maxDD':>8}{'turnover':>10}")
    for k, p in ro["strategies"].items():
        print(f"{k:14}{p['cagr']:8.1%}{p['vol']:8.1%}{p['sharpe']:8.2f}{p['max_drawdown']:8.1%}{p.get('turnover_per_year', float('nan')):10.2f}")
    print("mean weights:", {k: ro["strategies"][k]["mean_weights"] for k in RULES})
    print("expected Sharpe at rebalance (max Sharpe rule):", round(ro["max_sharpe_expected_sharpe_mean"], 3))
    print("window sensitivity:", json.dumps(sens))
    ho = out["hold_out"]
    print(f"\nHold-out {ho['start']} to {ho['end']}: {ho['weeks']} weeks, T-bill {ho['rf_mean']:.2%}")
    print(f"{'':14}{'total':>8}{'vol':>8}{'Sharpe':>8}{'maxDD':>8}{'IS Sharpe':>10}{'B&H':>8}")
    for k, p in ho["portfolios"].items():
        print(f"{k:14}{p['total_return']:8.1%}{p['vol']:8.1%}{p['sharpe']:8.2f}{p['max_drawdown']:8.1%}{p['in_sample_sharpe']:10.2f}"
              f"{p.get('total_return_buy_and_hold', float('nan')):8.1%}")
    print("end-date sensitivity:", ho["end_date_sensitivity"])
    print("hold-out vols:", ho["asset_volatility"])
    print("hold-out corr:", ho["correlations"])


if __name__ == "__main__":
    main()
