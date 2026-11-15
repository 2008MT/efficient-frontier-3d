"""Static figures for the README and the note. Writes figures/*.png and figures/*.pdf."""
import json, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from common import (ASSETS, COLORS, ROOT, load_weekly, in_sample, moments, simplex_grid, port_stats, cvar, gaussian_cvar)

FIG = os.path.join(ROOT, "figures")
RES = os.path.join(ROOT, "results")
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e0"
SEQ = LinearSegmentedColormap.from_list("seq", ["#dbe9f8", "#5a9be0", "#0c2f66"])
DIV = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#dddcd6", "#e34948"])
RULE_COLORS = {"max_sharpe": "#eb6834", "min_variance": "#2a78d6", "risk_parity": "#1baf7a", "equal_weight": "#8a8983"}
RULE_NAMES = {"max_sharpe": "Maximum Sharpe", "min_variance": "Minimum variance", "risk_parity": "Risk parity",
              "equal_weight": "Equal weight", "v1_max_sharpe": "Published July 2025"}
VERT = np.array([[0.0, 0.0, 1.0], [0.943, 0.0, -0.333], [-0.471, 0.816, -0.333], [-0.471, -0.816, -0.333]])

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": "#b5b4ae", "axes.linewidth": 0.6,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "xtick.color": INK2, "ytick.color": INK2, "axes.labelcolor": INK, "text.color": INK, "legend.frameon": False,
    "figure.dpi": 110, "savefig.dpi": 220, "savefig.bbox": "tight", "axes.axisbelow": True,
})


def save(fig, name):
    fig.savefig(os.path.join(FIG, name + ".png"))
    fig.savefig(os.path.join(FIG, name + ".pdf"))
    plt.close(fig)
    print("figures/" + name)


def tetra_axes(ax, elev=18, azim=-48):
    for i in range(4):
        for j in range(i + 1, 4):
            ax.plot(*zip(VERT[i], VERT[j]), color="#b5b4ae", lw=0.8, zorder=1)
    for v, a in zip(VERT, ASSETS):
        ax.text(*(1.13 * v), a, ha="center", va="center", fontsize=9, fontweight="bold")
    ax.set_axis_off()
    ax.set_box_aspect((1, 1, 0.8), zoom=1.3)
    ax.view_init(elev=elev, azim=azim)
    lim = 0.85
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-0.4, 1.0)


def main():
    os.makedirs(FIG, exist_ok=True)
    R_all, rf_all = load_weekly()
    R, rf = in_sample(R_all), in_sample(rf_all)
    mu, cov, _ = moments(R, rf)
    p1 = json.load(open(os.path.join(RES, "part1.json")))
    p2 = json.load(open(os.path.join(RES, "part2.json")))
    ports = {k: np.array([v["weights"][a] for a in ASSETS]) for k, v in p1["portfolios"].items()}
    G = simplex_grid(40)
    ret, vol, sh = port_stats(G, mu, cov)
    es = cvar(G, R)
    X = np.asarray(R) @ G.T
    ratio = es / gaussian_cvar(X.mean(axis=0), X.std(axis=0, ddof=1))
    f = p1["frontier"]["mean_variance"]
    fv, fr, FW = 100 * np.array(f["volatility"]), 100 * np.array(f["excess_return"]), 100 * np.array(f["weights"])

    # ---- Figure 1: frontier and its composition ----------------------------------------------
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 6.0), sharex=True, gridspec_kw={"height_ratios": [2, 1], "hspace": 0.08})
    o = np.argsort(sh)
    sc = a1.scatter(100 * vol[o], 100 * ret[o], c=sh[o], cmap=SEQ, s=3, linewidths=0, rasterized=True)
    s_ms = p1["portfolios"]["max_sharpe"]["sharpe"]
    xs = np.array([0, 78 / s_ms])
    a1.plot(xs, s_ms * xs, color=INK2, lw=0.9, ls=":", label=f"Capital market line (Sharpe {s_ms:.2f})")
    a1.plot(fv, fr, color=INK, lw=1.8, label="Efficient frontier")
    for i, a in enumerate(ASSETS):
        s = p1["assets"][a]
        a1.scatter(100 * s["volatility"], 100 * s["mean_excess"], s=46, color=COLORS[a], edgecolor="white", linewidth=1.2, zorder=5)
        dx, dy, ha = {"NVDA": (0, 7, "center"), "ARU": (0, 7, "center"), "VOO": (8, -3, "left"), "SGLN": (3, -13, "center")}[a]
        a1.annotate(a, (100 * s["volatility"], 100 * s["mean_excess"]), textcoords="offset points", xytext=(dx, dy), ha=ha, fontsize=8.5)
    offs = {"max_sharpe": (-7, 5, "right"), "min_variance": (-7, -3, "right"), "risk_parity": (8, -3, "left"),
            "equal_weight": (8, -3, "left"), "v1_max_sharpe": (-7, 5, "right")}
    for k, (dx, dy, ha) in offs.items():
        d = p1["portfolios"][k]
        a1.scatter(100 * d["volatility"], 100 * d["excess_return"], marker="D", s=30, color="white", edgecolor=INK, linewidth=1.2, zorder=6)
        a1.annotate(RULE_NAMES[k], (100 * d["volatility"], 100 * d["excess_return"]), textcoords="offset points", xytext=(dx, dy), ha=ha, fontsize=7.5)
    a1.set_ylabel("Excess return (% a year)"); a1.set_ylim(0, 80); a1.set_xlim(0, 78)
    a1.legend(loc="lower right", fontsize=8)
    cb = fig.colorbar(sc, ax=[a1, a2], pad=0.02, shrink=0.5, anchor=(0, 0.95)); cb.set_label("Sharpe ratio"); cb.outline.set_visible(False)
    a2.stackplot(fv, FW.T, colors=[COLORS[a] for a in ASSETS], labels=ASSETS, edgecolor="white", linewidth=0.5)
    a2.set_ylim(0, 100); a2.set_ylabel("Frontier weights (%)"); a2.set_xlabel("Volatility (% a year)")
    a2.legend(loc="center right", fontsize=8, ncol=1)
    save(fig, "fig1_frontier")

    # ---- Figure 2: weight tetrahedron and bootstrap clouds ------------------------------------
    fig = plt.figure(figsize=(8.6, 4.3))
    ax = fig.add_subplot(121, projection="3d")
    tetra_axes(ax)
    m = sh >= 0.90 * sh.max()
    P = G[m] @ VERT
    sc = ax.scatter(P[:, 0], P[:, 1], P[:, 2], c=sh[m], cmap=SEQ, vmin=sh.min(), vmax=sh.max(), s=5, linewidths=0, depthshade=False, rasterized=True)
    Fp = np.array(f["weights"]) @ VERT
    ax.plot(Fp[:, 0], Fp[:, 1], Fp[:, 2], color=INK, lw=1.8, zorder=10)
    ax.set_title("Portfolios within 10% of the best Sharpe ratio\n(black line: efficient frontier)", fontsize=9)
    cb = fig.colorbar(sc, ax=ax, shrink=0.5, pad=0.0); cb.set_label("Sharpe ratio"); cb.outline.set_visible(False)
    ax = fig.add_subplot(122, projection="3d")
    tetra_axes(ax)
    b = pd.read_csv(os.path.join(RES, "bootstrap_weights.csv"))
    for k in ["max_sharpe", "min_variance", "risk_parity"]:
        P = b.loc[b.portfolio == k, ASSETS].values @ VERT
        ax.scatter(P[:, 0], P[:, 1], P[:, 2], s=3, color=RULE_COLORS[k], alpha=0.45, linewidths=0, depthshade=False, label=RULE_NAMES[k], rasterized=True)
    ax.set_title("Optimal weights in 2,000 bootstrap resamples", fontsize=9)
    leg = ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.08), ncol=3, fontsize=8, markerscale=3, handletextpad=0.2, columnspacing=1.0)
    for h in leg.legend_handles:
        h.set_alpha(1)
    save(fig, "fig2_simplex")

    # ---- Figure 3: tail risk against the normal benchmark --------------------------------------
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.6, 3.6), gridspec_kw={"width_ratios": [1.7, 1], "wspace": 0.28})
    span = np.abs(ratio - 1).max()
    o = np.argsort(np.abs(ratio - 1))
    sc = a1.scatter(100 * vol[o], 100 * ret[o], c=ratio[o], cmap=DIV, norm=TwoSlopeNorm(1, 1 - span, 1 + span), s=3, linewidths=0, rasterized=True)
    for a in ASSETS:
        s = p1["assets"][a]
        a1.scatter(100 * s["volatility"], 100 * s["mean_excess"], s=40, color="white", edgecolor=INK, linewidth=1, zorder=5)
        dx, dy, ha = {"NVDA": (0, 7, "center"), "ARU": (0, 7, "center"), "VOO": (8, -3, "left"), "SGLN": (-8, -3, "right")}[a]
        a1.annotate(a, (100 * s["volatility"], 100 * s["mean_excess"]), textcoords="offset points", xytext=(dx, dy), ha=ha, fontsize=8.5)
    a1.set_xlabel("Volatility (% a year)"); a1.set_ylabel("Excess return (% a year)"); a1.set_xlim(0, 78); a1.set_ylim(0, 78)
    cb = fig.colorbar(sc, ax=a1, pad=0.02); cb.set_label("CVaR ÷ normal CVaR"); cb.outline.set_visible(False)
    x = np.arange(4)
    hist = [100 * p1["assets"][a]["cvar95_weekly"] for a in ASSETS]
    gau = [100 * p1["assets"][a]["cvar95_gaussian"] for a in ASSETS]
    a2.bar(x - 0.2, gau, 0.36, color="#c9c8c2", label="Normal distribution")
    a2.bar(x + 0.2, hist, 0.36, color=[COLORS[a] for a in ASSETS], label="Historical")
    for xi, h, g in zip(x, hist, gau):
        a2.text(xi + 0.2, h + 0.3, f"{h / g:.2f}×", ha="center", fontsize=8)
    a2.set_xticks(x); a2.set_xticklabels(ASSETS); a2.set_ylabel("Weekly 95% CVaR (%)"); a2.grid(axis="x", visible=False)
    a2.set_ylim(0, 27)
    from matplotlib.patches import Patch
    a2.legend(handles=[Patch(color="#c9c8c2", label="Normal distribution"), Patch(color=INK2, label="Historical (asset colour)")], fontsize=8, loc="upper left")
    save(fig, "fig3_tail")

    # ---- Figure 4: out of sample ----------------------------------------------------------------
    wealth = pd.read_csv(os.path.join(RES, "oos_wealth.csv"), parse_dates=["date"], index_col="date")
    ho = pd.read_csv(os.path.join(RES, "holdout_wealth.csv"), parse_dates=["date"], index_col="date")
    ho = pd.concat([pd.DataFrame(1.0, index=[ho.index[0] - pd.Timedelta(days=7)], columns=ho.columns), ho])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.8, 3.7), gridspec_kw={"wspace": 0.24})
    st = p2["rolling"]["strategies"]
    for k in ["max_sharpe", "equal_weight", "risk_parity", "min_variance"]:
        a1.plot(wealth.index, wealth[k], color=RULE_COLORS[k], lw=1.3, label=f"{RULE_NAMES[k]} ({st[k]['sharpe']:.2f})")
    a1.set_yscale("log"); a1.set_yticks([1, 2, 4, 8]); a1.set_yticklabels(["$1", "$2", "$4", "$8"]); a1.minorticks_off()
    a1.set_title("Rolling test: value of $1 (Sharpe ratio in brackets)", fontsize=9, loc="left")
    a1.legend(fontsize=7.8, loc="upper left")
    a1.xaxis.set_major_locator(matplotlib.dates.YearLocator(2))
    hp = p2["hold_out"]["portfolios"]
    for a in ASSETS:
        a2.plot(ho.index, 100 * (ho[a] - 1), color=COLORS[a], lw=1.0, label=f"{a} ({hp[a]['total_return']:+.0%})")
    a2.plot(ho.index, 100 * (ho["v1_max_sharpe"] - 1), color=INK, lw=2.2, label=f"Published portfolio ({hp['v1_max_sharpe']['total_return']:+.0%})")
    a2.axhline(0, color="#b5b4ae", lw=0.8)
    a2.set_title("After publication: return since 25 July 2025 (%)", fontsize=9, loc="left")
    a2.legend(fontsize=7.8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, columnspacing=1.0, handlelength=1.5)
    a2.xaxis.set_major_locator(matplotlib.dates.MonthLocator(bymonth=[1, 5, 9]))
    a2.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %Y"))
    save(fig, "fig4_out_of_sample")


if __name__ == "__main__":
    main()
