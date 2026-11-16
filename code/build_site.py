"""Build the landing page of the project website (index.html) from results/*.json."""
import json, os
from common import ROOT

RES = os.path.join(ROOT, "results")
REPO = "https://github.com/2008MT/efficient-frontier-3d"
NOTE = "TOK_EFFICIENT_FRONTIER_3D.pdf"

CSS = """
:root{--bg:#fcfcfb;--card:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--line:#e6e5e0;--link:#1f4e8c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
main{max-width:1000px;margin:0 auto;padding:48px 20px 64px}
h1{font-size:2rem;line-height:1.2;margin:0 0 8px;letter-spacing:-0.01em}
h2{font-size:1.3rem;margin:56px 0 8px}
p{margin:0 0 14px;max-width:72ch}
a{color:var(--link)}
.meta{color:var(--ink2);margin:0 0 20px}
.links a{display:inline-block;margin:0 14px 6px 0;font-weight:600}
.lead{font-size:1.1rem}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:28px 0 8px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.tile b{display:block;font-size:1.55rem;line-height:1.25}
.tile span{color:var(--ink2);font-size:0.86rem;line-height:1.35;display:block;margin-top:4px}
figure{margin:16px 0 0}
iframe{display:block;width:100%;border:1px solid var(--line);border-radius:8px;background:#fff}
.frame{position:relative}
.frame iframe{pointer-events:none}
.frame.on iframe{pointer-events:auto;border-color:#8a8983}
.frame button{position:absolute;right:14px;bottom:14px;font:inherit;font-size:0.85rem;color:var(--ink);background:#fff;
border:1px solid #b5b4ae;border-radius:999px;padding:5px 14px;cursor:pointer}
.frame.on button{display:none}
figcaption{color:var(--ink2);font-size:0.9rem;margin-top:8px;max-width:80ch}
figcaption a{white-space:nowrap}
table{border-collapse:collapse;margin:8px 0 4px;font-size:0.93rem;font-variant-numeric:tabular-nums}
th,td{padding:5px 14px 5px 0;text-align:right;border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left}
th{color:var(--ink2);font-weight:600}
footer{margin-top:64px;padding-top:20px;border-top:1px solid var(--line);color:var(--ink2);font-size:0.9rem}
@media (max-width:760px){.tiles{grid-template-columns:repeat(2,1fr)}h1{font-size:1.6rem}}
"""


def pc(x, d=0):
    return f"{100 * x:.{d}f}%"


def fig(src, height, caption):
    return (f'<figure><div class="frame"><iframe src="plots/{src}" height="{height}" loading="lazy" title="{caption[:60]}"></iframe>'
            f'<button type="button">Click to interact</button></div>'
            f'<figcaption>{caption} <a href="plots/{src}">Open full screen</a></figcaption></figure>')


def main():
    p1 = json.load(open(os.path.join(RES, "part1.json")))
    p2 = json.load(open(os.path.join(RES, "part2.json")))
    p3 = json.load(open(os.path.join(RES, "part3.json")))
    P, G, A = p1["portfolios"], p1["grid"], p1["assets"]
    S, H = p2["rolling"]["strategies"], p2["hold_out"]["portfolios"]
    E = p2["hold_out"]["end_date_sensitivity"]
    W = p3["weights"]["max_sharpe"]
    ms = P["max_sharpe"]
    names = {"max_sharpe": "Maximum Sharpe", "equal_weight": "Equal weight", "risk_parity": "Risk parity", "min_variance": "Minimum variance"}

    roll_rows = "".join(
        f"<tr><td>{names[k]}</td><td>{S[k]['sharpe']:.2f}</td><td>{pc(S[k]['cagr'])}</td><td>{pc(S[k]['vol'])}</td>"
        f"<td>{pc(S[k]['max_drawdown'])}</td><td>{pc(S[k]['turnover_per_year'])}</td></tr>" for k in names)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>A four-asset efficient frontier in three dimensions | Mael Tok</title>
<meta name="description" content="Interactive 3D portfolio optimisation for NVDA, VOO, ARU and SGLN, with an out-of-sample test and a bootstrap of the optimal weights.">
<style>{CSS}</style>
</head>
<body>
<main>
<h1>A four-asset efficient frontier in three dimensions</h1>
<p class="meta">Mael Tok · McGill University · first version July 2025, this version November 2026</p>
<p class="links"><a href="{NOTE}">Read the note (PDF)</a><a href="{REPO}">Code on GitHub</a></p>

<p class="lead">In July 2025 I optimised a portfolio of Nvidia, an S&amp;P 500 fund, a rare-earth developer and gold, and published the mix
with the highest Sharpe ratio. This page redoes that exercise with the measurement fixed, then tests it on data the optimiser never saw.</p>
<p>The in-sample answer is still a barbell of Nvidia and gold. It does not hold up: re-estimated through time it did no better than equal weights,
and the "optimal" Nvidia weight could plausibly be anywhere from {pc(W['p05']['NVDA'])} to {pc(W['p95']['NVDA'])}.</p>

<div class="tiles">
<div class="tile"><b>{ms['sharpe']:.2f}</b><span>Sharpe ratio of the best portfolio in sample, 2015 to 2025</span></div>
<div class="tile"><b>{p2['rolling']['max_sharpe_expected_sharpe_mean']:.2f} → {S['max_sharpe']['sharpe']:.2f}</b><span>Sharpe ratio the optimiser expected, and what it then earned out of sample</span></div>
<div class="tile"><b>{pc(W['p05']['NVDA'])} to {pc(W['p95']['NVDA'])}</b><span>90% bootstrap range for the optimal Nvidia weight</span></div>
<div class="tile"><b>{100 * H['v1_max_sharpe']['total_return']:+.1f}%</b><span>Return of the portfolio published in July 2025, to 13 November 2026 (Sharpe {H['v1_max_sharpe']['sharpe']:.2f})</span></div>
</div>

<h2>1. Every portfolio in one picture</h2>
<p>Four weights that sum to one leave three free dimensions, so the set of all long-only portfolios is a tetrahedron. Each corner is 100% in one asset.
The cloud below is the {pc(G['share_within_10pct_of_max_sharpe'])} of portfolios whose Sharpe ratio is within 10% of the best: the optimum is a wide, flat region, not a point.</p>
{fig("simplex.html", 620, "Click the figure, then drag to rotate and scroll to zoom. The menus switch between all portfolios and the near-optimal ones, and change what the colour shows. The black line is the efficient frontier.")}

<h2>2. The efficient frontier</h2>
<p>The frontier is solved exactly by quadratic programming. The best portfolio holds {pc(ms['weights']['NVDA'])} Nvidia, {pc(ms['weights']['SGLN'])} gold,
{pc(ms['weights']['ARU'])} Arafura and no S&amp;P 500. The lower panel shows what the frontier holds at each level of risk.</p>
{fig("frontier.html", 600, f"Each dot is one of {G['portfolios']:,} portfolios. Returns are weekly, in US dollars, over Treasury bills, 31 July 2015 to 25 July 2025.")}

<h2>3. Tail risk that volatility misses</h2>
<p>Height shows each portfolio's average loss in its worst 5% of weeks (CVaR), divided by what a normal distribution with the same volatility implies.
On the grey plane the normal distribution is right. The S&amp;P 500 fund sits highest at {A['VOO']['cvar_ratio']:.2f}: its large moves are crashes.
Arafura sits lowest at {A['ARU']['cvar_ratio']:.2f}: its large moves are jumps upwards.</p>
{fig("risk_return_tail.html", 620, "Colour shows the largest holding; the menu switches it to the tail ratio or the Sharpe ratio.")}

<h2>4. Out of sample</h2>
<p>Every four weeks from July 2018, each rule is estimated on the previous three years only and held for the next four weeks.
The maximum-Sharpe rule expected a Sharpe ratio of {p2['rolling']['max_sharpe_expected_sharpe_mean']:.2f} and earned {S['max_sharpe']['sharpe']:.2f},
with the deepest drawdown and the most trading. The differences between the rules are within sampling error; the gap between expected and earned is the point.</p>
<table>
<tr><th>Rule</th><th>Sharpe</th><th>Growth a year</th><th>Volatility</th><th>Worst drawdown</th><th>Turnover a year</th></tr>
{roll_rows}
</table>
{fig("out_of_sample.html", 600, "Top: value of $1 under each rule. Bottom: the weights the maximum-Sharpe rule chose at each rebalance.")}

<h2>5. What happened after July 2025</h2>
<p>The published portfolio is a real hold-out test. It returned {100 * H['v1_max_sharpe']['total_return']:+.1f}% with a Sharpe ratio of {H['v1_max_sharpe']['sharpe']:.2f},
against {H['v1_max_sharpe']['in_sample_sharpe']:.2f} in sample. The S&amp;P 500 fund, which it excluded, returned {100 * H['VOO']['total_return']:+.1f}%.
The comparison depends on the end date: the portfolio was ahead of the S&amp;P 500 at {E['end_dates_total_return_above_voo']} of {E['end_dates_considered']} possible end dates since January 2026
and fell behind in the last two weeks. Its risk was misjudged either way: gold's volatility was {pc(p2['hold_out']['asset_volatility']['SGLN'])} against {pc(A['SGLN']['volatility'])} before.</p>
{fig("holdout.html", 520, "Return since 25 July 2025. The portfolio is rebalanced to its published weights every four weeks.")}

<h2>6. How stable are the optimal weights?</h2>
<p>Resampling the ten years 2,000 times gives 2,000 "optimal" portfolios. The maximum-Sharpe points smear along the whole Nvidia–gold edge,
while minimum-variance and risk-parity portfolios, which do not use expected returns, stay in tight clusters.
The maximum-Sharpe weights are {p3['dispersion_ratio_max_sharpe_vs_min_variance']:.1f} times as dispersed as the minimum-variance ones.</p>
{fig("bootstrap.html", 620, "Each dot is the optimal portfolio in one bootstrap resample. Diamonds are the estimates from the actual sample.")}

<footer>
<p>Data: Yahoo Finance, weekly returns in US dollars with dividends reinvested. Method, limitations and references are in the <a href="{NOTE}">note</a>;
everything here is reproducible from the <a href="{REPO}">code</a>. This is a study of method, not investment advice.</p>
<p>AI tools assisted with the first version. Claude (Anthropic) was used in the November 2026 update, including the out-of-sample
backtest on data from July 2025 to November 2026.</p>
</footer>
</main>
<script>
// Figures respond to the mouse only after a click, so that scrolling the page never gets caught in one.
document.querySelectorAll(".frame").forEach(function (f) {{
  f.addEventListener("click", function () {{ f.classList.add("on"); }});
  f.addEventListener("mouseleave", function () {{ f.classList.remove("on"); }});
}});
document.addEventListener("pointerdown", function (e) {{
  document.querySelectorAll(".frame.on").forEach(function (f) {{ if (!f.contains(e.target)) f.classList.remove("on"); }});
}});
</script>
</body>
</html>
"""
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html")


if __name__ == "__main__":
    main()
