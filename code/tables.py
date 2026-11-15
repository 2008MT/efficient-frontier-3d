"""LaTeX tables and every number quoted in the note (numbers.tex), built from results/*.json."""
import json, os
from common import ASSETS, ROOT

RES = os.path.join(ROOT, "results")
TAB = os.path.join(ROOT, "tables")
NAMES = {"max_sharpe": "Maximum Sharpe", "min_variance": "Minimum variance", "risk_parity": "Risk parity",
         "equal_weight": "Equal weight", "min_cvar": "Minimum CVaR", "v1_max_sharpe": "Published July 2025"}


def pc(x, d=1):
    return f"{100 * x:.{d}f}"


def write(name, lines):
    with open(os.path.join(TAB, name), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("tables/" + name)


def main():
    os.makedirs(TAB, exist_ok=True)
    p1 = json.load(open(os.path.join(RES, "part1.json")))
    p2 = json.load(open(os.path.join(RES, "part2.json")))
    p3 = json.load(open(os.path.join(RES, "part3.json")))
    A, P, G, F = p1["assets"], p1["portfolios"], p1["grid"], p1["frontier"]

    # Table 1: assets
    rows = [r"\begin{tabular}{lrrrrrrr}", r"\toprule",
            r" & Excess & Compound & Volatility & Sharpe & Skewness & Max.\ & CVaR $\div$ \\",
            r" & return & growth & & ratio & & drawdown & normal \\", r"\midrule"]
    for a in ASSETS:
        s = A[a]
        rows.append(f"{a} & {pc(s['mean_excess'])} & {pc(s['cagr'])} & {pc(s['volatility'])} & {s['sharpe']:.2f} & "
                    f"{s['skewness']:.2f} & {pc(s['max_drawdown'], 0)} & {s['cvar_ratio']:.2f} \\\\")
    rows += [r"\bottomrule", r"\end{tabular}"]
    write("tab_assets.tex", rows)

    # Table 2: correlations under three measurement choices
    C = p1["correlations"]
    pairs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    rows = [r"\begin{tabular}{lrrr}", r"\toprule",
            r" & Daily, local & Weekly, & Four-weekly, \\", r"Pair & currency & US dollars & US dollars \\", r"\midrule"]
    for i, j in pairs:
        rows.append(f"{ASSETS[i]}--{ASSETS[j]} & {C['daily_local_currency'][i][j]:.2f} & {C['weekly_usd'][i][j]:.2f} & {C['four_weekly_usd'][i][j]:.2f} \\\\")
    rows += [r"\bottomrule", r"\end{tabular}"]
    write("tab_corr.tex", rows)

    # Table 3: reference portfolios in sample
    rows = [r"\begin{tabular}{lrrrrrrrr}", r"\toprule",
            r" & \multicolumn{4}{c}{Weights (\%)} & Excess & Volatility & Sharpe & CVaR \\", r"\cmidrule(lr){2-5}",
            r" & NVDA & VOO & ARU & SGLN & return & & ratio & (weekly) \\", r"\midrule"]
    for k in ["max_sharpe", "v1_max_sharpe", "equal_weight", "risk_parity", "min_variance", "min_cvar"]:
        d = P[k]
        w = " & ".join(pc(d["weights"][a]) for a in ASSETS)
        rows.append(f"{NAMES[k]} & {w} & {pc(d['excess_return'])} & {pc(d['volatility'])} & {d['sharpe']:.2f} & {pc(d['cvar95_weekly'])} \\\\")
    rows += [r"\bottomrule", r"\end{tabular}"]
    write("tab_portfolios.tex", rows)

    # Table 4: rolling out-of-sample test
    S = p2["rolling"]["strategies"]
    ci = p3["rolling_sharpe_ci"]
    rows = [r"\begin{tabular}{lrrrrrr}", r"\toprule",
            r" & Compound & Volatility & Sharpe & 90\% interval & Max.\ & Turnover \\",
            r" & growth & & ratio & for Sharpe & drawdown & a year \\", r"\midrule"]
    for k in ["max_sharpe", "equal_weight", "risk_parity", "min_variance"]:
        d = S[k]
        rows.append(f"{NAMES[k]} & {pc(d['cagr'])} & {pc(d['vol'])} & {d['sharpe']:.2f} & [{ci[k]['p05']:.2f}, {ci[k]['p95']:.2f}] & "
                    f"{pc(d['max_drawdown'], 0)} & {pc(d['turnover_per_year'], 0)} \\\\")
    rows.append(r"\midrule")
    for a in ASSETS:
        d = S[a]
        rows.append(f"{a} & {pc(d['cagr'])} & {pc(d['vol'])} & {d['sharpe']:.2f} & & {pc(d['max_drawdown'], 0)} & \\\\")
    rows += [r"\bottomrule", r"\end{tabular}"]
    write("tab_rolling.tex", rows)

    # Table 5: hold-out
    H = p2["hold_out"]["portfolios"]
    rows = [r"\begin{tabular}{lrrrrr}", r"\toprule",
            r" & Sharpe ratio & \multicolumn{4}{c}{1 August 2025 to 13 November 2026} \\", r"\cmidrule(lr){3-6}",
            r" & to July 2025 & Total return & Volatility & Sharpe ratio & Max.\ drawdown \\", r"\midrule"]
    for k in ["v1_max_sharpe", "max_sharpe", "equal_weight", "risk_parity", "min_variance"]:
        d = H[k]
        rows.append(f"{NAMES[k]} & {d['in_sample_sharpe']:.2f} & {pc(d['total_return'])} & {pc(d['vol'])} & {d['sharpe']:.2f} & {pc(d['max_drawdown'], 0)} \\\\")
    rows.append(r"\midrule")
    for a in ASSETS:
        d = H[a]
        rows.append(f"{a} & {d['in_sample_sharpe']:.2f} & {pc(d['total_return'])} & {pc(d['vol'])} & {d['sharpe']:.2f} & {pc(d['max_drawdown'], 0)} \\\\")
    rows += [r"\bottomrule", r"\end{tabular}"]
    write("tab_holdout.tex", rows)

    # Table 6: bootstrap intervals for the weights
    W = p3["weights"]
    rows = [r"\begin{tabular}{lrrrr}", r"\toprule", r" & NVDA & VOO & ARU & SGLN \\", r"\midrule"]
    for k in ["max_sharpe", "min_variance", "risk_parity"]:
        rows.append(f"{NAMES[k]} & " + " & ".join(pc(W[k]["point_estimate"][a], 0) for a in ASSETS) + r" \\")
        rows.append(r"\quad 90\% interval & " + " & ".join(f"[{pc(W[k]['p05'][a], 0)}, {pc(W[k]['p95'][a], 0)}]" for a in ASSETS) + r" \\")
    rows += [r"\bottomrule", r"\end{tabular}"]
    write("tab_bootstrap.tex", rows)

    # ---- numbers quoted in the text ---------------------------------------------------------
    ms, v1 = P["max_sharpe"], P["v1_max_sharpe"]
    Hs = p2["hold_out"]
    E = Hs["end_date_sensitivity"]
    F3 = p3["max_sharpe_facts"]
    C = p1["correlations"]
    mv, cv = F["mean_variance"], F["mean_cvar"]
    n = len(mv["cvar95_weekly"])
    cvar_gain = sum((a - b) / a for a, b in zip(mv["cvar95_weekly"], cv["cvar95_weekly"])) / n
    vol_cost = sum((b - a) / a for a, b in zip(mv["volatility"], cv["volatility"])) / n
    N = {
        "nWeeks": p1["sample"]["weeks"], "rfMean": pc(p1["sample"]["rf_mean"]),
        "nDailyObs": f"{C['daily_obs']:,}".replace(",", "{,}"),
        "goldCorrGood": f"{p1['gold_check']['corr_sgln_usd_vs_igln']:.2f}", "goldCorrBad": f"{p1['gold_check']['corr_same_day_fx_vs_igln']:.2f}",
        "aruMeanTotal": pc(A["ARU"]["mean_total"], 0), "aruCagr": pc(A["ARU"]["cagr"], 0), "aruVol": pc(A["ARU"]["volatility"], 0),
        "nvdaCagr": pc(A["NVDA"]["cagr"], 0),
        "msNvda": pc(ms["weights"]["NVDA"], 0), "msSgln": pc(ms["weights"]["SGLN"], 0), "msAru": pc(ms["weights"]["ARU"], 0),
        "msSharpe": f"{ms['sharpe']:.2f}", "msVol": pc(ms["volatility"], 0), "vOneSharpe": f"{v1['sharpe']:.2f}", "vOneVol": pc(v1["volatility"], 0),
        "ewSharpe": f"{P['equal_weight']['sharpe']:.2f}",
        "gridN": f"{G['portfolios']:,}".replace(",", "{,}"), "gridShareTen": pc(G["share_within_10pct_of_max_sharpe"], 0),
        "gridShareFive": pc(G["share_within_5pct_of_max_sharpe"], 1),
        "nearNvdaLo": pc(G["near_optimal_weight_ranges"]["NVDA"][0], 0), "nearNvdaHi": pc(G["near_optimal_weight_ranges"]["NVDA"][1], 0),
        "nearSglnLo": f"{100 * G['near_optimal_weight_ranges']['SGLN'][0]:g}", "nearSglnHi": f"{100 * G['near_optimal_weight_ranges']['SGLN'][1]:g}",
        "nearVooHi": pc(G["near_optimal_weight_ranges"]["VOO"][1], 0),
        "ratioVoo": f"{A['VOO']['cvar_ratio']:.2f}", "ratioAru": f"{A['ARU']['cvar_ratio']:.2f}", "ratioNvda": f"{A['NVDA']['cvar_ratio']:.2f}",
        "ratioSgln": f"{A['SGLN']['cvar_ratio']:.2f}", "ratioMin": f"{G['cvar_ratio_min']:.2f}", "ratioMax": f"{G['cvar_ratio_max']:.2f}",
        "ratioShareAbove": pc(G["share_cvar_ratio_above_1"], 0), "skewAru": f"{A['ARU']['skewness']:.2f}", "skewVoo": f"{A['VOO']['skewness']:.2f}",
        "cvarGain": pc(cvar_gain, 1), "cvarVolCost": pc(vol_cost, 1), "cvarMaxGap": pc(F["max_weight_gap_mv_vs_cvar"], 0),
        "rollWeeks": p2["rolling"]["weeks"], "rollRebal": p2["rolling"]["rebalances"],
        "rollExpected": f"{p2['rolling']['max_sharpe_expected_sharpe_mean']:.2f}",
        "rollMs": f"{S['max_sharpe']['sharpe']:.2f}", "rollEw": f"{S['equal_weight']['sharpe']:.2f}", "rollRp": f"{S['risk_parity']['sharpe']:.2f}",
        "rollMv": f"{S['min_variance']['sharpe']:.2f}", "rollMsDd": pc(-S["max_sharpe"]["max_drawdown"], 0), "rollRpDd": pc(-S["risk_parity"]["max_drawdown"], 0),
        "rollMsTurn": pc(S["max_sharpe"]["turnover_per_year"], 0), "rollRpTurn": pc(S["risk_parity"]["turnover_per_year"], 0),
        "rollMsLo": f"{ci['max_sharpe']['p05']:.2f}", "rollMsHi": f"{ci['max_sharpe']['p95']:.2f}",
        "diffEst": f"{p3['rolling_sharpe_difference_risk_parity_minus_max_sharpe']['estimate']:.2f}",
        "diffLo": f"{p3['rolling_sharpe_difference_risk_parity_minus_max_sharpe']['p05']:.2f}",
        "diffHi": f"{p3['rolling_sharpe_difference_risk_parity_minus_max_sharpe']['p95']:.2f}",
        "hoWeeks": Hs["weeks"], "hoVOneRet": pc(H["v1_max_sharpe"]["total_return"]), "hoVOneSharpe": f"{H['v1_max_sharpe']['sharpe']:.2f}",
        "hoVOneVol": pc(H["v1_max_sharpe"]["vol"], 0), "hoVOneDd": pc(-H["v1_max_sharpe"]["max_drawdown"], 0),
        "hoVooRet": pc(H["VOO"]["total_return"]), "hoVooSharpe": f"{H['VOO']['sharpe']:.2f}", "hoVooDd": pc(-H["VOO"]["max_drawdown"], 0),
        "hoVooVol": pc(H["VOO"]["vol"], 0),
        "hoNvdaRet": pc(-H["NVDA"]["total_return"]), "hoAruRet": pc(-H["ARU"]["total_return"], 0), "hoSglnRet": pc(H["SGLN"]["total_return"]),
        "hoSglnVol": pc(Hs["asset_volatility"]["SGLN"], 0), "isSglnVol": pc(A["SGLN"]["volatility"], 0),
        "hoCorrAruSgln": f"{Hs['correlations'][2][3]:.2f}", "isCorrAruSgln": f"{C['weekly_usd'][2][3]:.2f}",
        "hoEndAhead": E["end_dates_total_return_above_voo"], "hoEndTotal": E["end_dates_considered"], "hoPeak": pc(E["peak_total_return"], 0),
        "bootVooZero": pc(F3["share_voo_below_1pct"], 0), "bootSglnLargest": pc(F3["share_sgln_largest"], 0), "bootNvdaLargest": pc(F3["share_nvda_largest"], 0),
        "bootRatio": f"{p3['dispersion_ratio_max_sharpe_vs_min_variance']:.1f}",
        "bootNvdaLo": pc(W["max_sharpe"]["p05"]["NVDA"], 0), "bootNvdaHi": pc(W["max_sharpe"]["p95"]["NVDA"], 0),
        "bootSglnLo": pc(W["max_sharpe"]["p05"]["SGLN"], 0), "bootSglnHi": pc(W["max_sharpe"]["p95"]["SGLN"], 0),
        "bootSharpeLo": f"{p3['max_sharpe_value']['p05']:.2f}", "bootSharpeHi": f"{p3['max_sharpe_value']['p95']:.2f}",
        "bootVooSglnShare": pc(p3["share_voo_sharpe_above_sgln"], 0),
        "srVoo": f"{A['VOO']['sharpe']:.2f}", "srSgln": f"{A['SGLN']['sharpe']:.2f}", "srNvda": f"{A['NVDA']['sharpe']:.2f}", "srAru": f"{A['ARU']['sharpe']:.2f}",
        "srNvdaLo": f"{p3['asset_sharpe']['NVDA']['p05']:.2f}", "srNvdaHi": f"{p3['asset_sharpe']['NVDA']['p95']:.2f}",
        "srVooLo": f"{p3['asset_sharpe']['VOO']['p05']:.2f}", "srVooHi": f"{p3['asset_sharpe']['VOO']['p95']:.2f}",
        "corrVooAruDaily": f"{C['daily_local_currency'][1][2]:.2f}", "corrVooAruWeekly": f"{C['weekly_usd'][1][2]:.2f}",
        "corrVooSglnDaily": f"{C['daily_local_currency'][1][3]:.2f}", "corrVooSglnWeekly": f"{C['weekly_usd'][1][3]:.2f}",
    }
    with open(os.path.join(ROOT, "numbers.tex"), "w") as f:
        f.write("% generated by code/tables.py -- do not edit\n")
        for k, v in N.items():
            f.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
    print("numbers.tex:", len(N), "numbers")


if __name__ == "__main__":
    main()
