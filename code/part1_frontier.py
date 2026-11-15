"""Part 1. In-sample description: asset statistics, correlations, the exact efficient frontier,
reference portfolios, and expected shortfall (CVaR) against its Gaussian benchmark.

Sample: weekly US-dollar returns, 31 July 2015 to 25 July 2025. Output: results/part1.json
"""
import json, os
import numpy as np
import pandas as pd
from common import (ASSETS, ROOT, WEEKS, IS_START, IS_END, V1_WEIGHTS, load_daily, load_weekly, weekly_prices_usd,
                    in_sample, moments, simplex_grid, port_stats, cvar, gaussian_cvar, perf,
                    min_variance, max_sharpe, risk_parity, frontier, min_cvar)

ALPHA = 0.95
GRID_N = 40          # lattice step 2.5%


def describe(w, mu, cov, R, rf_mean):
    w = np.asarray(w, float)
    ret, vol, sh = (float(x[0]) for x in port_stats(w, mu, cov))
    X = np.asarray(R) @ w
    es = float(cvar(w, R, ALPHA)[0])
    es_n = float(gaussian_cvar(X.mean(), X.std(ddof=1), ALPHA))
    return {"weights": dict(zip(ASSETS, np.round(w, 4).tolist())), "excess_return": ret, "volatility": vol,
            "sharpe": sh, "cvar95_weekly": es, "cvar95_gaussian": es_n, "cvar_ratio": es / es_n}


def main():
    R_all, rf_all = load_weekly()
    R, rf = in_sample(R_all), in_sample(rf_all)
    mu, cov, rf_mean = moments(R, rf)
    out = {"sample": {"start": str(R.index[0].date()), "end": str(R.index[-1].date()), "weeks": int(len(R)),
                      "rf_mean": float(rf_mean), "alpha": ALPHA}}

    # --- asset statistics -------------------------------------------------------------------
    assets = {}
    for i, a in enumerate(ASSETS):
        p = perf(R[a], rf)
        e = np.eye(4)[i]
        d = describe(e, mu, cov, R, rf_mean)
        assets[a] = {"mean_excess": float(mu[i]), "mean_total": float(R[a].mean() * WEEKS), "cagr": p["cagr"],
                     "volatility": d["volatility"], "sharpe": d["sharpe"], "skewness": float(R[a].skew()),
                     "excess_kurtosis": float(R[a].kurt()), "max_drawdown": p["max_drawdown"],
                     "cvar95_weekly": d["cvar95_weekly"], "cvar95_gaussian": d["cvar95_gaussian"],
                     "cvar_ratio": d["cvar_ratio"], "worst_week": float(R[a].min()), "best_week": float(R[a].max())}
    out["assets"] = assets

    # --- correlations under three measurement choices ----------------------------------------
    daily = load_daily()[ASSETS].dropna().pct_change().dropna().loc[:IS_END]
    R4 = (1 + R).groupby(np.arange(len(R)) // 4).prod() - 1
    out["correlations"] = {
        "daily_local_currency": daily.corr().round(4).values.tolist(),
        "weekly_usd": R.corr().round(4).values.tolist(),
        "four_weekly_usd": R4.corr().round(4).values.tolist(),
        "daily_obs": int(len(daily)), "four_weekly_obs": int(len(R4)),
    }
    # the first version's inputs: daily, local currency, no risk-free rate
    out["v1_replication"] = {a: {"mean": float(daily[a].mean() * 252), "volatility": float(daily[a].std() * np.sqrt(252)),
                                 "sharpe_rf0": float(daily[a].mean() / daily[a].std() * np.sqrt(252))} for a in ASSETS}

    # check on the currency conversion: SGLN in dollars against the dollar line of the same fund
    p = weekly_prices_usd().pct_change().loc[IS_START:IS_END]
    out["gold_check"] = {"corr_sgln_usd_vs_igln": float(p.SGLN.corr(p.IGLN)),
                         "corr_same_day_fx_vs_igln": float(p.SGLN_same_day_fx.corr(p.IGLN)),
                         "mean_diff_annual": float((p.SGLN - p.IGLN).mean() * WEEKS)}

    # --- reference portfolios ---------------------------------------------------------------
    ports = {
        "max_sharpe": max_sharpe(mu, cov),
        "min_variance": min_variance(cov),
        "risk_parity": risk_parity(cov),
        "equal_weight": np.full(4, 0.25),
        "min_cvar": min_cvar(R, alpha=ALPHA),
        "v1_max_sharpe": V1_WEIGHTS / V1_WEIGHTS.sum(),
    }
    out["portfolios"] = {k: describe(w, mu, cov, R, rf_mean) for k, w in ports.items()}
    rc = ports["risk_parity"] * (cov @ ports["risk_parity"]) / (ports["risk_parity"] @ cov @ ports["risk_parity"])
    out["portfolios"]["risk_parity"]["risk_contributions"] = np.round(rc, 4).tolist()

    # --- lattice of all portfolios -----------------------------------------------------------
    G = simplex_grid(GRID_N)
    g_ret, g_vol, g_sh = port_stats(G, mu, cov)
    g_es = cvar(G, R, ALPHA)
    Xg = np.asarray(R) @ G.T
    g_ratio = g_es / gaussian_cvar(Xg.mean(axis=0), Xg.std(axis=0, ddof=1), ALPHA)
    best = g_sh.max()
    out["grid"] = {
        "step": 1 / GRID_N, "portfolios": int(len(G)),
        "sharpe_min": float(g_sh.min()), "sharpe_max": float(best),
        "vol_min": float(g_vol.min()), "vol_max": float(g_vol.max()),
        "share_within_5pct_of_max_sharpe": float((g_sh >= 0.95 * best).mean()),
        "share_within_10pct_of_max_sharpe": float((g_sh >= 0.90 * best).mean()),
        "cvar_ratio_min": float(g_ratio.min()), "cvar_ratio_max": float(g_ratio.max()),
        "share_cvar_ratio_above_1": float((g_ratio > 1).mean()),
        "max_sharpe_on_grid": dict(zip(ASSETS, G[g_sh.argmax()].tolist())),
        "optimiser_vs_grid_sharpe_gap": float(out["portfolios"]["max_sharpe"]["sharpe"] - best),
    }
    near = G[g_sh >= 0.95 * best]
    out["grid"]["near_optimal_weight_ranges"] = {a: [float(near[:, i].min()), float(near[:, i].max())] for i, a in enumerate(ASSETS)}

    # --- efficient frontiers: mean-variance and mean-CVaR ------------------------------------
    W = frontier(mu, cov, 80)
    f_ret, f_vol, f_sh = port_stats(W, mu, cov)
    Wc = np.array([min_cvar(R, mu / WEEKS, t / WEEKS, ALPHA) for t in f_ret])   # same target returns
    c_ret, c_vol, c_sh = port_stats(Wc, mu, cov)
    out["frontier"] = {
        "mean_variance": {"weights": np.round(W, 4).tolist(), "excess_return": f_ret.tolist(), "volatility": f_vol.tolist(),
                          "sharpe": f_sh.tolist(), "cvar95_weekly": cvar(W, R, ALPHA).tolist()},
        "mean_cvar": {"weights": np.round(Wc, 4).tolist(), "excess_return": c_ret.tolist(), "volatility": c_vol.tolist(),
                      "sharpe": c_sh.tolist(), "cvar95_weekly": cvar(Wc, R, ALPHA).tolist()},
    }
    diff = np.abs(W - Wc)
    out["frontier"]["max_weight_gap_mv_vs_cvar"] = float(diff.max())
    out["frontier"]["mean_abs_weight_gap_by_asset"] = dict(zip(ASSETS, diff.mean(axis=0).round(4).tolist()))
    out["frontier"]["mean_weight_gap_cvar_minus_mv"] = dict(zip(ASSETS, (Wc - W).mean(axis=0).round(4).tolist()))
    out["frontier"]["voo_max_weight_above_20vol"] = float(W[f_vol > 0.20, 1].max())

    # weights along the frontier at chosen volatility levels
    scale = []
    for v in [0.12, 0.15, 0.20, 0.25, 0.30, 0.40]:
        i = int(np.argmin(np.abs(f_vol - v)))
        scale.append({"target_vol": v, "volatility": float(f_vol[i]), "excess_return": float(f_ret[i]),
                      "sharpe": float(f_sh[i]), "weights": dict(zip(ASSETS, np.round(W[i], 3).tolist()))})
    out["frontier"]["by_volatility"] = scale

    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "part1.json"), "w") as f:
        json.dump(out, f, indent=1)

    # --- console summary --------------------------------------------------------------------
    print(f"Sample {out['sample']['start']} to {out['sample']['end']}: {len(R)} weeks, mean T-bill rate {rf_mean:.2%}")
    print(f"{'':6}{'excess':>8}{'CAGR':>8}{'vol':>8}{'Sharpe':>8}{'skew':>7}{'ES95':>7}{'ES/N':>7}")
    for a, s in assets.items():
        print(f"{a:6}{s['mean_excess']:8.1%}{s['cagr']:8.1%}{s['volatility']:8.1%}{s['sharpe']:8.2f}{s['skewness']:7.2f}"
              f"{s['cvar95_weekly']:7.1%}{s['cvar_ratio']:7.2f}")
    for k, d in out["portfolios"].items():
        w = " ".join(f"{d['weights'][a]:6.1%}" for a in ASSETS)
        print(f"{k:14} {w}  ret {d['excess_return']:6.1%} vol {d['volatility']:6.1%} SR {d['sharpe']:.3f} ES {d['cvar95_weekly']:.2%} ratio {d['cvar_ratio']:.2f}")
    print("grid:", {k: v for k, v in out["grid"].items() if not isinstance(v, dict)})
    print("near-optimal ranges:", out["grid"]["near_optimal_weight_ranges"])
    print("MV vs CVaR frontier gap:", out["frontier"]["max_weight_gap_mv_vs_cvar"], out["frontier"]["mean_weight_gap_cvar_minus_mv"])
    for s in scale:
        print(s)
    print("corr daily local:", out["correlations"]["daily_local_currency"])
    print("corr weekly usd :", out["correlations"]["weekly_usd"])
    print("corr 4-weekly   :", out["correlations"]["four_weekly_usd"])
    print("v1 replication:", out["v1_replication"])
    print("gold check:", out["gold_check"])


if __name__ == "__main__":
    main()
