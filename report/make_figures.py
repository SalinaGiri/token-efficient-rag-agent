"""Build the two result figures from results.csv and latency_fit.csv.

Fill both CSV files with your measured values and set placeholder to "no";
the PLACEHOLDER watermark then disappears. Run:  python make_figures.py
"""
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for f in ["/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
          "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"]:
    try:
        font_manager.fontManager.addfont(f)
    except Exception:
        pass
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "Times", "DejaVu Serif"],
    "font.size": 10, "axes.titlesize": 10.5, "axes.labelsize": 10,
    "axes.edgecolor": "#333333", "axes.linewidth": 0.6,
    "xtick.color": "#333333", "ytick.color": "#333333",
})

DARK, MID, LIGHT, GRID = "#1A1A1A", "#8C8C8C", "#C8C8C8", "#E3E3E3"

def read(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))

rows = read("results.csv")
fit = read("latency_fit.csv")[0]
placeholder = any(r["placeholder"].strip().lower() == "yes" for r in rows + [fit])

def watermark(fig):
    if placeholder:
        fig.text(0.5, 0.5, "PLACEHOLDER DATA\nreplace with measured results", ha="center", va="center",
                 fontsize=22, color="#000000", alpha=0.12, rotation=18, fontweight="bold")

def clean(ax):
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)

# ---------- Figure 1: tokens and quality per variant ----------
names = [r["variant"] for r in rows][::-1]
inp = [float(r["input_tokens"]) for r in rows][::-1]
out = [float(r["output_tokens"]) for r in rows][::-1]
cor = [float(r.get("good_pct") or r["correct_pct"]) for r in rows][::-1]
y = range(len(names))

fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True,
                           gridspec_kw={"width_ratios": [1.6, 1], "wspace": 0.08})
a.barh(y, inp, color=MID, height=0.58, edgecolor="white", linewidth=1.2, label="Input tokens")
a.barh(y, out, left=inp, color=DARK, height=0.58, edgecolor="white", linewidth=1.2, label="Output tokens")
for i, (x1, x2) in enumerate(zip(inp, out)):
    a.text(x1 + x2 + max(inp) * 0.015, i, f"{int(x1 + x2):,}", va="center", fontsize=9, color="#333333")
a.set_yticks(list(y)); a.set_yticklabels(names)
a.set_xlabel("Tokens per query (mean)")
a.set_title("(a) Token usage", loc="left", fontweight="bold")
a.set_xlim(0, max(i + o for i, o in zip(inp, out)) * 1.17)
a.xaxis.grid(True, color=GRID, linewidth=0.6); a.set_axisbelow(True)
a.legend(loc="lower right", frameon=False, fontsize=8.5)
clean(a)

correct = [float(r["correct_pct"]) for r in rows][::-1]
b.barh(y, correct, color=LIGHT, height=0.58, edgecolor=DARK, linewidth=0.6, label="Correct")
b.barh(y, cor, color=DARK, height=0.28, label="Correct and correctly cited")
for i, (c, g) in enumerate(zip(correct, cor)):
    b.text(c + 1.5, i, f"{c:.0f}% / {g:.0f}%", va="center", fontsize=8.5, color="#333333")
b.set_xlim(0, 125); b.set_xticks([0, 25, 50, 75, 100])
b.set_xlabel("Answers (%)")
b.set_title("(b) Answer quality", loc="left", fontweight="bold")
b.xaxis.grid(True, color=GRID, linewidth=0.6); b.set_axisbelow(True)
clean(b)
watermark(fig)
fig.savefig("fig1_tokens_quality.png", dpi=300, bbox_inches="tight")
plt.close(fig)

# ---------- Figure 2: latency cost of one input vs one output token ----------
ci, co = float(fit["ms_per_input_token"]), float(fit["ms_per_output_token"])

def exchange_panel(ax, title_prefix=""):
    bars = ax.bar(["One input token\n(prefill)", "One output token\n(decode)"], [ci, co],
                  color=[MID, DARK], width=0.5, edgecolor="white")
    for r, v in zip(bars, [ci, co]):
        ax.text(r.get_x() + r.get_width() / 2, v + co * 0.03, (f"{v:.2f} ms" if v < 10 else f"{v:.1f} ms"), ha="center", fontsize=9.5)
    ax.set_ylabel("Added latency (ms per token)")
    ax.set_ylim(0, co * 1.25)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6); ax.set_axisbelow(True)
    ax.set_title(f"{title_prefix}1 output token ≈ {co / ci:,.0f} input tokens", loc="left",
                 fontweight="bold", fontsize=10)
    clean(ax)

def tradeoff_panel(ax, trade, chosen_tau=None, title_prefix=""):
    """Tokens vs correctness for every swept TAU; V0 as the reference point."""
    styles = {"V1": dict(color=MID, marker="o", linestyle="--", label="V1 (T1 only)"),
              "V3": dict(color=DARK, marker="s", linestyle="-", label="V3 (T1 + T4)")}
    for v, st in styles.items():
        pts = sorted([r for r in trade if r["variant"] == v], key=lambda r: float(r["tau"]))
        if not pts:
            continue
        xs = [float(r["tokens_per_query"]) for r in pts]
        ys = [float(r["correct_pct"]) for r in pts]
        ax.plot(xs, ys, markersize=4, linewidth=1, **st)
        if v == "V3":
            for r, x, y in zip(pts, xs, ys):
                ax.annotate(f"τ={float(r['tau']):g}", (x, y), textcoords="offset points", xytext=(4, -10), fontsize=7.5)
                if chosen_tau is not None and abs(float(r["tau"]) - chosen_tau) < 1e-9:
                    ax.plot([x], [y], marker="o", markersize=11, markerfacecolor="none", markeredgecolor=DARK,
                            linewidth=0, label=f"chosen τ = {chosen_tau:g}")
    base = [r for r in trade if r["variant"] == "V0"]
    if base:
        bx, by = float(base[0]["tokens_per_query"]), float(base[0]["correct_pct"])
        ax.plot([bx], [by], marker="*", markersize=10, color=DARK, linewidth=0, label="V0 baseline")
        ax.axhline(by - 3, color=LIGHT, linewidth=0.8, linestyle=":")
        ax.text(bx, by - 3, "V0 - 3 points", fontsize=7.5, ha="right", va="bottom", color="#555555")
    ax.set_xscale("log")
    from matplotlib.ticker import NullFormatter, FixedLocator, FuncFormatter
    lo, hi = ax.get_xlim()
    ticks = [t for t in (100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000) if lo <= t <= hi]
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("Tokens per query (log scale)")
    ax.set_ylabel("Correct (%)")
    ax.set_title(f"{title_prefix}Threshold trade-off (sweep)", loc="left", fontweight="bold", fontsize=10)
    ax.grid(True, color=GRID, linewidth=0.6); ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    clean(ax)

try:
    trade = read("tradeoff.csv")
except FileNotFoundError:
    trade = []
try:
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    import config
    chosen = config.TAU
except Exception:
    chosen = None

if trade:
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 2.6), gridspec_kw={"width_ratios": [1, 1.25], "wspace": 0.35})
    exchange_panel(a, "(a) ")
    tradeoff_panel(b, trade, chosen, "(b) ")
    watermark(fig)
    fig.savefig("fig2_token_exchange_rate.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(4.2, 2.8))
    tradeoff_panel(ax, trade, chosen)
    fig.savefig("fig3_tradeoff.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
else:
    fig, ax = plt.subplots(figsize=(3.8, 2.5))
    exchange_panel(ax)
    watermark(fig)
    fig.savefig("fig2_token_exchange_rate.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
print("figures written; placeholder =", placeholder, "; trade-off panel =", bool(trade))
