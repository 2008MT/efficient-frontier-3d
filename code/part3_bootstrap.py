"""Part 3. Estimation error.

Ten years of weekly data give one estimate of the means and covariances. A stationary block
bootstrap (Politis and Romano, 1994) redraws the sample 2,000 times, and each redraw gives its own
"optimal" portfolio. The spread of those portfolios shows how much of the answer is noise.

Output: results/part3.json, results/bootstrap_weights.csv
"""
import json, os
import numpy as np
import pandas as pd
from common import (ASSETS, ROOT, WEEKS, load_weekly, in_sample, port_stats, min_variance, max_sharpe, risk_parity)
from part2_out_of_sample import run_rolling

B = 2000
MEAN_BLOCK = 8        # weeks
SEED = 2025


def stationary_indices(n, mean_block, rng):
    """Index vector of length n for one stationary-bootstrap resample (blocks wrap around)."""
    idx = np.empty(n, dtype=int)
    idx[0] = rng.integers(n)
    new_block = rng.random(n) < 1 / mean_block
    starts = rng.integers(n, size=n)
    for t in range(1, n):
        idx[t] = starts[t] if new_block[t] else (idx[t - 1] + 1) % n
    return idx


def pct(x, q):
    return [float(v) for v in np.percentile(x, q, axis=0)]


def main():
    rng = np.random.default_rng(SEED)
    R_all, rf_all = load_weekly()
    R, rf = in_sample(R_all), in_sample(rf_all)
    X, F = R.values, rf.values
    n = len(X)

    mu0 = (X - F[:, None]).mean(axis=0) * WEEKS
    cov0 = np.cov(X, rowvar=False) * WEEKS
    w0 = {"max_sharpe": max_sharpe(mu0, cov0), "min_variance": min_variance(cov0), "risk_parity": risk_parity(cov0)}

    W = {k: np.empty((B, 4)) for k in w0}
    asset_sharpe = np.empty((B, 4))
    best_sharpe = np.empty(B)           # Sharpe of the resample's optimum, measured on the resample
    best_on_original = np.empty(B)      # Sharpe of the same weights, measured on the original sample
    for b in range(B):
        i = stationary_indices(n, MEAN_BLOCK, rng)
        Xb, Fb = X[i], F[i]
        mu = (Xb - Fb[:, None]).mean(axis=0) * WEEKS
        cov = np.cov(Xb, rowvar=False) * WEEKS
        W["max_sharpe"][b] = max_sharpe(mu, cov)
        W["min_variance"][b] = min_variance(cov)
        W["risk_parity"][b] = risk_parity(cov)
        asset_sharpe[b] = mu / np.sqrt(np.diag(cov))
        w = W["max_sharpe"][b]
        best_sharpe[b] = (w @ mu) / np.sqrt(w @ cov @ w)
        best_on_original[b] = (w @ mu0) / np.sqrt(w @ cov0 @ w)

    out = {"design": {"resamples": B, "mean_block_weeks": MEAN_BLOCK, "seed": SEED, "weeks": n}, "weights": {}}
    for k in w0:
        out["weights"][k] = {
            "point_estimate": dict(zip(ASSETS, np.round(w0[k], 4).tolist())),
            "p05": dict(zip(ASSETS, np.round(pct(W[k], 5), 4))),
            "p50": dict(zip(ASSETS, np.round(pct(W[k], 50), 4))),
            "p95": dict(zip(ASSETS, np.round(pct(W[k], 95), 4))),
            "std": dict(zip(ASSETS, np.round(W[k].std(axis=0), 4).tolist())),
        }
    ms = W["max_sharpe"]
    out["max_sharpe_facts"] = {
        "share_voo_below_1pct": float((ms[:, 1] < 0.01).mean()),
        "share_voo_above_20pct": float((ms[:, 1] > 0.20).mean()),
        "share_nvda_largest": float((ms.argmax(axis=1) == 0).mean()),
        "share_sgln_largest": float((ms.argmax(axis=1) == 3).mean()),
        "share_aru_above_10pct": float((ms[:, 2] > 0.10).mean()),
        "mean_total_std": float(ms.std(axis=0).mean()),
    }
    out["dispersion_ratio_max_sharpe_vs_min_variance"] = float(ms.std(axis=0).mean() / W["min_variance"].std(axis=0).mean())
    s0 = mu0 / np.sqrt(np.diag(cov0))
    out["asset_sharpe"] = {a: {"estimate": float(s0[j]), "p05": float(np.percentile(asset_sharpe[:, j], 5)),
                               "p95": float(np.percentile(asset_sharpe[:, j], 95))} for j, a in enumerate(ASSETS)}
    out["share_voo_sharpe_above_sgln"] = float((asset_sharpe[:, 1] > asset_sharpe[:, 3]).mean())
    out["share_nvda_sharpe_highest"] = float((asset_sharpe.argmax(axis=1) == 0).mean())
    sh0 = float(port_stats(w0["max_sharpe"], mu0, cov0)[2][0])
    out["max_sharpe_value"] = {"estimate": sh0, "p05": float(np.percentile(best_sharpe, 5)),
                               "p95": float(np.percentile(best_sharpe, 95)),
                               "mean_in_resample": float(best_sharpe.mean()),
                               "mean_of_same_weights_on_original_sample": float(best_on_original.mean())}

    # confidence intervals for the rolling out-of-sample Sharpe ratios of Part 2
    rets, _, _ = run_rolling(R_all, rf_all)
    ex = rets.sub(rf_all.loc[rets.index], axis=0).values
    m = len(ex)
    cols = list(rets.columns)
    sh = np.empty((B, len(cols)))
    for b in range(B):
        e = ex[stationary_indices(m, MEAN_BLOCK, rng)]
        sh[b] = e.mean(axis=0) / e.std(axis=0, ddof=1) * np.sqrt(WEEKS)
    point = ex.mean(axis=0) / ex.std(axis=0, ddof=1) * np.sqrt(WEEKS)
    out["rolling_sharpe_ci"] = {c: {"estimate": float(point[j]), "p05": float(np.percentile(sh[:, j], 5)),
                                    "p95": float(np.percentile(sh[:, j], 95))} for j, c in enumerate(cols)}
    d = sh[:, cols.index("risk_parity")] - sh[:, cols.index("max_sharpe")]
    out["rolling_sharpe_difference_risk_parity_minus_max_sharpe"] = {
        "estimate": float(point[cols.index("risk_parity")] - point[cols.index("max_sharpe")]),
        "p05": float(np.percentile(d, 5)), "p95": float(np.percentile(d, 95)), "share_positive": float((d > 0).mean())}

    with open(os.path.join(ROOT, "results", "part3.json"), "w") as f:
        json.dump(out, f, indent=1)
    frames = []
    for k in W:
        df = pd.DataFrame(np.round(W[k], 4), columns=ASSETS)
        df.insert(0, "portfolio", k)
        frames.append(df)
    pd.concat(frames).to_csv(os.path.join(ROOT, "results", "bootstrap_weights.csv"), index=False)

    for k in w0:
        o = out["weights"][k]
        print(k)
        for a in ASSETS:
            print(f"   {a:5} estimate {o['point_estimate'][a]:6.1%}   90% interval {o['p05'][a]:6.1%} to {o['p95'][a]:6.1%}   sd {o['std'][a]:.3f}")
    print(out["max_sharpe_facts"])
    print("dispersion ratio:", round(out["dispersion_ratio_max_sharpe_vs_min_variance"], 2))
    print("asset Sharpe:", {a: [round(v, 2) for v in o.values()] for a, o in out["asset_sharpe"].items()})
    print("P(VOO Sharpe > SGLN Sharpe):", out["share_voo_sharpe_above_sgln"], " P(NVDA highest):", out["share_nvda_sharpe_highest"])
    print("max Sharpe value:", {k: round(v, 3) for k, v in out["max_sharpe_value"].items()})
    print("rolling Sharpe CI:", {c: [round(v, 2) for v in o.values()] for c, o in out["rolling_sharpe_ci"].items()})
    print("RP - MS:", {k: round(v, 3) for k, v in out["rolling_sharpe_difference_risk_parity_minus_max_sharpe"].items()})


if __name__ == "__main__":
    main()
