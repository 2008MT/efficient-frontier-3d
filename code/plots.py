"""Interactive figures (Plotly) for the project website. Writes plots/*.html.

Each page loads plotly.js from a CDN and stores hover information as compact numeric arrays, so the
pages are about 1 MB or less.
"""
import json, os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from common import (ASSETS, COLORS, ROOT, WEEKS, V1_WEIGHTS, load_weekly, in_sample, moments, simplex_grid,
                    port_stats, cvar, gaussian_cvar)

DOCS = os.path.join(ROOT, "plots")
RES = os.path.join(ROOT, "results")
ALPHA = 0.95
GRID_N = 40

INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e0"
FONT = dict(family='-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif', size=13, color=INK)
SEQ = [[0, "#dbe9f8"], [0.5, "#5a9be0"], [1, "#0c2f66"]]                     # one hue, light to dark
DIV = [[0, "#2a78d6"], [0.5, "#dddcd6"], [1, "#e34948"]]                     # two hues, neutral midpoint
RULE_COLORS = {"max_sharpe": "#eb6834", "min_variance": "#2a78d6", "risk_parity": "#1baf7a", "equal_weight": "#8a8983"}
RULE_NAMES = {"max_sharpe": "Maximum Sharpe", "min_variance": "Minimum variance", "risk_parity": "Risk parity",
              "equal_weight": "Equal weight", "v1_max_sharpe": "Published July 2025", "min_cvar": "Minimum CVaR"}
# vertices of a regular tetrahedron, one per asset
VERT = np.array([[0.0, 0.0, 1.0], [0.943, 0.0, -0.333], [-0.471, 0.816, -0.333], [-0.471, -0.816, -0.333]])
VERT = VERT[[0, 1, 2, 3]]            # NVDA on top; VOO, ARU, SGLN on the base

HOVER = ("NVDA %{customdata[0]:.1f}%  ·  VOO %{customdata[1]:.1f}%<br>ARU %{customdata[2]:.1f}%  ·  SGLN %{customdata[3]:.1f}%"
         "<br>Excess return %{customdata[4]:.1f}%  ·  Volatility %{customdata[5]:.1f}%<br>Sharpe %{customdata[6]:.2f}"
         "<br>Weekly CVaR %{customdata[7]:.2f}%  (%{customdata[8]:.2f}× normal)")


def f32(x):
    return np.asarray(x, dtype=np.float32)


def custom(W, ret, vol, sh, es, ratio):
    return f32(np.column_stack([100 * W, 100 * ret, 100 * vol, sh, 100 * es, ratio]))


def stats(W, mu, cov, R):
    ret, vol, sh = port_stats(W, mu, cov)
    es = cvar(W, R, ALPHA)
    X = np.asarray(R) @ np.atleast_2d(W).T
    ratio = es / gaussian_cvar(X.mean(axis=0), X.std(axis=0, ddof=1), ALPHA)
    return ret, vol, sh, es, ratio


def save(fig, name, title):
    html = fig.to_html(include_plotlyjs="cdn", full_html=True, default_height="100vh",
                       config={"displaylogo": False, "responsive": True,
                               "modeBarButtonsToRemove": ["lasso2d", "select2d"]})
    head = ('<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{title}</title><style>html,body{{margin:0;background:#fff;overflow:hidden}}</style>")
    html = html.replace('<head><meta charset="utf-8" /></head>', f'<head><meta charset="utf-8" />{head}</head>')
    path = os.path.join(DOCS, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"plots/{name}: {os.path.getsize(path) / 1e6:.2f} MB")


def base_layout(fig, **kw):
    fig.update_layout(template="plotly_white", font=FONT, paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                      margin=dict(l=10, r=10, t=10, b=10), autosize=True,
                      hoverlabel=dict(bgcolor="#ffffff", bordercolor=GRID, font=dict(family=FONT["family"], size=12, color=INK)),
                      legend=dict(orientation="h", yanchor="bottom", y=0.0, xanchor="left", x=0.0, bgcolor="rgba(255,255,255,0.8)"),
                      **kw)
    return fig


def tetra_frame():
    """Edges and vertex labels of the weight tetrahedron."""
    ex, ey, ez = [], [], []
    for i in range(4):
        for j in range(i + 1, 4):
            ex += [VERT[i, 0], VERT[j, 0], None]
            ey += [VERT[i, 1], VERT[j, 1], None]
            ez += [VERT[i, 2], VERT[j, 2], None]
    edges = go.Scatter3d(x=ex, y=ey, z=ez, mode="lines", line=dict(color="#b5b4ae", width=2), hoverinfo="skip", showlegend=False)
    lab = VERT * 1.12
    labels = go.Scatter3d(x=lab[:, 0], y=lab[:, 1], z=lab[:, 2], mode="text", text=[f"<b>100% {a}</b>" for a in ASSETS],
                          textfont=dict(size=13, color=INK), hoverinfo="skip", showlegend=False)
    return [edges, labels]


def tetra_scene():
    ax = dict(visible=False)
    return dict(xaxis=ax, yaxis=ax, zaxis=ax, aspectmode="data", domain=dict(x=[0, 1], y=[0.04, 1]),
                camera=dict(eye=dict(x=1.15, y=-1.05, z=0.6), center=dict(x=0, y=0, z=-0.1)))


def reference_trace(ports, mu, cov, R, coords):
    keys = ["max_sharpe", "min_variance", "risk_parity", "equal_weight", "v1_max_sharpe"]
    W = np.array([ports[k] for k in keys])
    xyz = coords(W, *stats(W, mu, cov, R))
    return go.Scatter3d(x=xyz[0], y=xyz[1], z=xyz[2], mode="markers+text", name="Reference portfolios",
                        text=[RULE_NAMES[k] for k in keys], textposition="top center", textfont=dict(size=11, color=INK),
                        marker=dict(size=6, color=INK, symbol="diamond", line=dict(color="#ffffff", width=2)),
                        customdata=custom(W, *stats(W, mu, cov, R)), hovertemplate="<b>%{text}</b><br>" + HOVER + "<extra></extra>")


# ------------------------------------------------------------------------------------------------
def fig_simplex(G, gs, ports, fr, mu, cov, R):
    """Every long-only portfolio as a point inside a tetrahedron."""
    ret, vol, sh, es, ratio = gs
    best = sh.max()
    masks = [np.ones(len(G), bool), sh >= 0.90 * best, sh >= 0.95 * best]
    names = ["All portfolios", "Sharpe within 10% of the best", "Sharpe within 5% of the best"]
    fig = go.Figure(tetra_frame())
    for m, nm, vis in zip(masks, names, [False, True, False]):
        xyz = G[m] @ VERT
        fig.add_trace(go.Scatter3d(
            x=f32(xyz[:, 0]), y=f32(xyz[:, 1]), z=f32(xyz[:, 2]), mode="markers", name=nm, visible=vis, showlegend=False,
            marker=dict(size=3.2, color=f32(sh[m]), colorscale=SEQ, cmin=float(sh.min()), cmax=float(best), opacity=0.9 if m.mean() < 1 else 0.45,
                        colorbar=dict(title=dict(text="Sharpe ratio", side="right"), thickness=12, len=0.6, x=0.98)),
            customdata=custom(G[m], ret[m], vol[m], sh[m], es[m], ratio[m]), hovertemplate=HOVER + "<extra></extra>"))
    for key, nm, dash in [("mean_variance", "Efficient frontier (mean-variance)", "solid"), ("mean_cvar", "Efficient frontier (mean-CVaR)", "dash")]:
        W = np.array(fr[key]["weights"])
        xyz = W @ VERT
        fig.add_trace(go.Scatter3d(x=xyz[:, 0], y=xyz[:, 1], z=xyz[:, 2], mode="lines", name=nm,
                                   line=dict(color=INK if dash == "solid" else "#eb6834", width=6, dash=dash), hoverinfo="skip"))
    fig.add_trace(reference_trace(ports, mu, cov, R, lambda W, *a: (W @ VERT).T))

    span = float(np.abs(ratio - 1).max())
    colourings = [
        ("Sharpe ratio", sh, SEQ, float(sh.min()), float(best)),
        ("Volatility (%)", 100 * vol, SEQ, float(100 * vol.min()), float(100 * vol.max())),
        ("CVaR ÷ normal CVaR", ratio, DIV, 1 - span, 1 + span),
    ]
    colour_buttons = [dict(label=lab, method="restyle", args=[{
        "marker.color": [np.round(v[m], 3).tolist() for m in masks], "marker.colorscale": [cs] * 3,
        "marker.cmin": [lo] * 3, "marker.cmax": [hi] * 3, "marker.colorbar.title.text": [lab] * 3}, [2, 3, 4]])
        for lab, v, cs, lo, hi in colourings]
    show_buttons = [dict(label=nm, method="restyle", args=[{"visible": [i == j for j in range(3)]}, [2, 3, 4]])
                    for i, nm in enumerate(names)]
    base_layout(fig, scene=tetra_scene(), updatemenus=[
        dict(type="dropdown", buttons=show_buttons, active=1, x=0.0, xanchor="left", y=1.0, yanchor="top", showactive=True, bgcolor="#ffffff", bordercolor=GRID),
        dict(type="dropdown", buttons=colour_buttons, x=0.0, xanchor="left", y=0.93, yanchor="top", showactive=True, bgcolor="#ffffff", bordercolor=GRID)])
    save(fig, "simplex.html", "Every portfolio in one picture")


def fig_tail(G, gs, ports, fr, mu, cov, R):
    """Volatility, return and the size of the left tail relative to a normal distribution.

    Height is the historical expected shortfall (CVaR) of a portfolio divided by the expected
    shortfall of a normal distribution with the same mean and volatility. On the grey plane the
    normal distribution is exactly right; above it the left tail is fatter, below it thinner.
    """
    ret, vol, sh, es, ratio = gs
    span = float(np.abs(ratio - 1).max())
    top = G.argmax(axis=1).astype(float)
    cat = [[0, COLORS["NVDA"]], [0.25, COLORS["NVDA"]], [0.25, COLORS["VOO"]], [0.5, COLORS["VOO"]],
           [0.5, COLORS["ARU"]], [0.75, COLORS["ARU"]], [0.75, COLORS["SGLN"]], [1, COLORS["SGLN"]]]
    fig = go.Figure()
    vv = np.array([100 * vol.min(), 100 * vol.max()])
    rr = np.array([100 * ret.min(), 100 * ret.max()])
    fig.add_trace(go.Surface(x=vv, y=rr, z=np.ones((2, 2)), opacity=0.3, showscale=False, name="Normal distribution (ratio = 1)",
                             colorscale=[[0, "#8a8983"], [1, "#8a8983"]], hoverinfo="skip", showlegend=True))
    fig.add_trace(go.Scatter3d(
        x=f32(100 * vol), y=f32(100 * ret), z=f32(ratio), mode="markers", name="Portfolios", showlegend=False,
        marker=dict(size=2.8, color=f32(top), colorscale=cat, cmin=-0.5, cmax=3.5, opacity=0.9,
                    colorbar=dict(title=dict(text="Largest holding", side="right"), thickness=12, len=0.6, x=0.98,
                                  tickvals=[0, 1, 2, 3], ticktext=ASSETS)),
        customdata=custom(G, ret, vol, sh, es, ratio), hovertemplate=HOVER + "<extra></extra>"))
    for key, nm, col, dash in [("mean_variance", "Efficient frontier (mean-variance)", INK, "solid"), ("mean_cvar", "Efficient frontier (mean-CVaR)", "#eb6834", "dash")]:
        W = np.array(fr[key]["weights"])
        r_, v_, s_, e_, q_ = stats(W, mu, cov, R)
        fig.add_trace(go.Scatter3d(x=100 * v_, y=100 * r_, z=q_, mode="lines", name=nm, line=dict(color=col, width=6, dash=dash), hoverinfo="skip"))
    E = np.eye(4)
    e = stats(E, mu, cov, R)
    fig.add_trace(go.Scatter3d(x=100 * e[1], y=100 * e[0], z=e[4], mode="markers+text", name="Single assets", text=ASSETS, showlegend=False,
                               textposition="top center", textfont=dict(size=12, color=INK),
                               marker=dict(size=7, color=[COLORS[a] for a in ASSETS], line=dict(color="#ffffff", width=2)),
                               customdata=custom(E, *e), hovertemplate="<b>%{text}</b><br>" + HOVER + "<extra></extra>"))
    fig.add_trace(reference_trace(ports, mu, cov, R, lambda W, r, v, s, c, q: (100 * v, 100 * r, q)))

    buttons = [
        dict(label="Colour: largest holding", method="restyle", args=[{
            "marker.color": [top.tolist()], "marker.colorscale": [cat], "marker.cmin": -0.5, "marker.cmax": 3.5,
            "marker.colorbar.title.text": "Largest holding", "marker.colorbar.tickmode": "array",
            "marker.colorbar.tickvals": [[0, 1, 2, 3]], "marker.colorbar.ticktext": [ASSETS]}, [1]]),
        dict(label="Colour: tail against normal", method="restyle", args=[{
            "marker.color": [np.round(ratio, 3).tolist()], "marker.colorscale": [DIV], "marker.cmin": 1 - span, "marker.cmax": 1 + span,
            "marker.colorbar.title.text": "CVaR ÷ normal CVaR", "marker.colorbar.tickmode": "auto"}, [1]]),
        dict(label="Colour: Sharpe ratio", method="restyle", args=[{
            "marker.color": [np.round(sh, 3).tolist()], "marker.colorscale": [SEQ], "marker.cmin": float(sh.min()), "marker.cmax": float(sh.max()),
            "marker.colorbar.title.text": "Sharpe ratio", "marker.colorbar.tickmode": "auto"}, [1]]),
    ]
    axis = dict(backgroundcolor="#ffffff", gridcolor=GRID, zerolinecolor=GRID, showbackground=True)
    base_layout(fig, scene=dict(
        xaxis=dict(title="Volatility (% a year)", **axis), yaxis=dict(title="Excess return (% a year)", **axis),
        zaxis=dict(title="CVaR ÷ normal CVaR", **axis), domain=dict(x=[0, 1], y=[0.05, 1]), aspectmode="manual",
        aspectratio=dict(x=1.2, y=1.2, z=0.75), camera=dict(eye=dict(x=-1.5, y=-1.45, z=0.6), center=dict(x=0, y=0, z=-0.15))),
        updatemenus=[dict(type="dropdown", buttons=buttons, x=0.0, xanchor="left", y=1.0, yanchor="top", showactive=True, bgcolor="#ffffff", bordercolor=GRID)])
    save(fig, "risk_return_tail.html", "Volatility, return and tail risk")


def fig_frontier(G, gs, ports, fr, mu, cov, R):
    """Classic two-dimensional frontier, with the weights along it underneath."""
    ret, vol, sh, es, ratio = gs
    f = fr["mean_variance"]
    fv, fret, FW = 100 * np.array(f["volatility"]), 100 * np.array(f["excess_return"]), 100 * np.array(f["weights"])
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.66, 0.34], vertical_spacing=0.06)
    fig.add_trace(go.Scattergl(x=f32(100 * vol), y=f32(100 * ret), mode="markers", name="Portfolios", showlegend=False,
                               marker=dict(size=4, color=f32(sh), colorscale=SEQ, cmin=float(sh.min()), cmax=float(sh.max()),
                                           colorbar=dict(title=dict(text="Sharpe ratio", side="right"), thickness=12, len=0.6, y=0.68)),
                               customdata=custom(G, ret, vol, sh, es, ratio), hovertemplate=HOVER + "<extra></extra>"), row=1, col=1)
    ms = ports["max_sharpe"]
    r_ms, v_ms, s_ms = (float(x[0]) for x in port_stats(ms, mu, cov))
    xs = np.array([0, 78 / s_ms])
    fig.add_trace(go.Scatter(x=xs, y=s_ms * xs, mode="lines", name=f"Capital market line (Sharpe {s_ms:.2f})",
                             line=dict(color=INK2, width=1.5, dash="dot"), hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=fv, y=fret, mode="lines", name="Efficient frontier", line=dict(color=INK, width=3),
                             customdata=FW, hovertemplate="Volatility %{x:.1f}%  ·  Excess return %{y:.1f}%<extra>Efficient frontier</extra>"), row=1, col=1)
    e = stats(np.eye(4), mu, cov, R)
    fig.add_trace(go.Scatter(x=100 * e[1], y=100 * e[0], mode="markers+text", text=ASSETS, textposition="top center", name="Single assets", showlegend=False,
                             marker=dict(size=12, color=[COLORS[a] for a in ASSETS], line=dict(color="#ffffff", width=2)),
                             customdata=custom(np.eye(4), *e), hovertemplate="<b>%{text}</b><br>" + HOVER + "<extra></extra>"), row=1, col=1)
    keys = ["max_sharpe", "min_variance", "risk_parity", "equal_weight", "v1_max_sharpe"]
    W = np.array([ports[k] for k in keys])
    s = stats(W, mu, cov, R)
    pos = ["top left", "bottom right", "bottom right", "bottom right", "top left"]
    fig.add_trace(go.Scatter(x=100 * s[1], y=100 * s[0], mode="markers+text", text=[RULE_NAMES[k] for k in keys], textposition=pos, name="Reference portfolios", showlegend=False,
                             marker=dict(size=11, symbol="diamond", color="#ffffff", line=dict(color=INK, width=2)), textfont=dict(size=11),
                             customdata=custom(W, *s), hovertemplate="<b>%{text}</b><br>" + HOVER + "<extra></extra>"), row=1, col=1)
    for j, a in enumerate(ASSETS):
        fig.add_trace(go.Scatter(x=fv, y=FW[:, j], mode="lines", name=a, stackgroup="w", line=dict(width=0.5, color="#ffffff"),
                                 fillcolor=COLORS[a], hovertemplate=f"{a} %{{y:.1f}}%<extra></extra>"), row=2, col=1)
    base_layout(fig, hovermode="closest")
    fig.update_layout(margin=dict(l=60, r=50, t=40, b=50), modebar=dict(orientation="v"),
                      legend=dict(y=1.01, yanchor="bottom", x=0, orientation="h", traceorder="normal"))
    grid = dict(gridcolor=GRID, zeroline=False, linecolor=GRID)
    fig.update_xaxes(**grid)
    fig.update_yaxes(**grid)
    fig.update_xaxes(title_text="Volatility (% a year)", row=2, col=1, range=[8, 78])
    fig.update_yaxes(title_text="Excess return (% a year)", row=1, col=1, range=[0, 80])
    fig.update_yaxes(title_text="Frontier weights (%)", row=2, col=1, range=[0, 100])
    save(fig, "frontier.html", "The efficient frontier and what it holds")


def fig_rolling():
    wealth = pd.read_csv(os.path.join(RES, "oos_wealth.csv"), parse_dates=["date"], index_col="date")
    wts = pd.read_csv(os.path.join(RES, "oos_weights_max_sharpe.csv"), parse_dates=["date"], index_col="date")
    p2 = json.load(open(os.path.join(RES, "part2.json")))["rolling"]["strategies"]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.62, 0.38], vertical_spacing=0.07)
    for k in ["max_sharpe", "equal_weight", "min_variance", "risk_parity"]:
        fig.add_trace(go.Scatter(x=wealth.index, y=wealth[k], mode="lines", name=f"{RULE_NAMES[k]} (Sharpe {p2[k]['sharpe']:.2f})",
                                 line=dict(color=RULE_COLORS[k], width=2),
                                 hovertemplate="%{x|%d %b %Y}: $%{y:.2f}<extra>" + RULE_NAMES[k] + "</extra>"), row=1, col=1)
    for a in ASSETS:
        fig.add_trace(go.Scatter(x=wts.index, y=100 * wts[a], mode="lines", name=a, stackgroup="w", line=dict(width=0.5, color="#ffffff", shape="hv"),
                                 fillcolor=COLORS[a], hovertemplate=f"{a} %{{y:.0f}}%<extra></extra>", legendgroup="w"), row=2, col=1)
    base_layout(fig, hovermode="x unified")
    fig.update_layout(margin=dict(l=60, r=50, t=60, b=40), modebar=dict(orientation="v"),
                      legend=dict(y=1.01, yanchor="bottom", x=0, orientation="h", traceorder="normal"))
    grid = dict(gridcolor=GRID, zeroline=False, linecolor=GRID)
    fig.update_xaxes(**grid)
    fig.update_yaxes(**grid)
    fig.update_yaxes(title_text="Value of $1 (log scale)", type="log", row=1, col=1)
    fig.update_yaxes(title_text="Weights (%)", range=[0, 100], row=2, col=1)
    save(fig, "out_of_sample.html", "Rolling out-of-sample test")


def fig_holdout():
    w = pd.read_csv(os.path.join(RES, "holdout_wealth.csv"), parse_dates=["date"], index_col="date")
    p = json.load(open(os.path.join(RES, "part2.json")))["hold_out"]["portfolios"]
    start = w.index[0] - pd.Timedelta(days=7)
    w = pd.concat([pd.DataFrame(1.0, index=[start], columns=w.columns), w])
    fig = go.Figure()
    for a in ASSETS:
        fig.add_trace(go.Scatter(x=w.index, y=100 * (w[a] - 1), mode="lines", name=f"{a} ({p[a]['total_return']:+.0%})",
                                 line=dict(color=COLORS[a], width=1.8), hovertemplate="%{y:+.1f}%<extra>" + a + "</extra>"))
    fig.add_trace(go.Scatter(x=w.index, y=100 * (w["equal_weight"] - 1), mode="lines", name=f"Equal weight ({p['equal_weight']['total_return']:+.0%})",
                             line=dict(color="#8a8983", width=2, dash="dash"), hovertemplate="%{y:+.1f}%<extra>Equal weight</extra>"))
    fig.add_trace(go.Scatter(x=w.index, y=100 * (w["v1_max_sharpe"] - 1), mode="lines",
                             name=f"Portfolio published July 2025 ({p['v1_max_sharpe']['total_return']:+.0%})",
                             line=dict(color=INK, width=3.5), hovertemplate="%{y:+.1f}%<extra>Published portfolio</extra>"))
    base_layout(fig, hovermode="x unified")
    fig.update_layout(margin=dict(l=60, r=50, t=60, b=40), modebar=dict(orientation="v"),
                      legend=dict(y=1.01, yanchor="bottom", x=0, orientation="h", traceorder="normal"))
    fig.update_xaxes(gridcolor=GRID, linecolor=GRID, hoverformat="%d %b %Y")
    fig.update_yaxes(title_text="Return since 25 July 2025 (%)", gridcolor=GRID, zeroline=True, zerolinecolor="#b5b4ae", linecolor=GRID)
    save(fig, "holdout.html", "What happened after July 2025")


def fig_bootstrap(ports):
    b = pd.read_csv(os.path.join(RES, "bootstrap_weights.csv"))
    fig = go.Figure(tetra_frame())
    for k in ["max_sharpe", "min_variance", "risk_parity"]:
        W = b.loc[b.portfolio == k, ASSETS].values
        xyz = W @ VERT
        fig.add_trace(go.Scatter3d(x=f32(xyz[:, 0]), y=f32(xyz[:, 1]), z=f32(xyz[:, 2]), mode="markers", name=f"{RULE_NAMES[k]}: 2,000 resamples",
                                   marker=dict(size=2.6, color=RULE_COLORS[k], opacity=0.55), customdata=f32(100 * W),
                                   hovertemplate="NVDA %{customdata[0]:.0f}%  ·  VOO %{customdata[1]:.0f}%<br>ARU %{customdata[2]:.0f}%  ·  SGLN %{customdata[3]:.0f}%<extra>" + RULE_NAMES[k] + "</extra>"))
    keys = ["max_sharpe", "min_variance", "risk_parity"]
    W = np.array([ports[k] for k in keys])
    xyz = W @ VERT
    fig.add_trace(go.Scatter3d(x=xyz[:, 0], y=xyz[:, 1], z=xyz[:, 2], mode="markers+text", name="Estimate from the actual sample",
                               text=[RULE_NAMES[k] for k in keys], textposition="top center", textfont=dict(size=11, color=INK),
                               marker=dict(size=7, symbol="diamond", color=INK, line=dict(color="#ffffff", width=2)), customdata=100 * W,
                               hovertemplate="<b>%{text}</b><br>NVDA %{customdata[0]:.0f}%  ·  VOO %{customdata[1]:.0f}%<br>ARU %{customdata[2]:.0f}%  ·  SGLN %{customdata[3]:.0f}%<extra></extra>"))
    base_layout(fig, scene=tetra_scene())
    save(fig, "bootstrap.html", "How stable are the optimal weights?")


def main():
    os.makedirs(DOCS, exist_ok=True)
    R_all, rf_all = load_weekly()
    R, rf = in_sample(R_all), in_sample(rf_all)
    mu, cov, rf_mean = moments(R, rf)
    p1 = json.load(open(os.path.join(RES, "part1.json")))
    ports = {k: np.array([v["weights"][a] for a in ASSETS]) for k, v in p1["portfolios"].items()}
    G = simplex_grid(GRID_N)
    gs = stats(G, mu, cov, R)
    fig_simplex(G, gs, ports, p1["frontier"], mu, cov, R)
    fig_tail(G, gs, ports, p1["frontier"], mu, cov, R)
    fig_frontier(G, gs, ports, p1["frontier"], mu, cov, R)
    fig_rolling()
    fig_holdout()
    fig_bootstrap(ports)


if __name__ == "__main__":
    main()
