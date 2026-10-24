"""DeNovoComp stage 5: display items at 600 dpi (PNG + vector PDF).

Nature Computational Science Article format: five main figures (plus Table 1,
built in the manuscript) and seven Extended Data figures.
"""
import io, json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import seaborn as sns
from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D
from PIL import Image

import dnc_core as C
from campaigns import SPECS

OUT, CFG = C.OUT, C.CFG
T = OUT / "tables"
FIG = OUT / "figures"; FIG.mkdir(exist_ok=True)
DPI = 600

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": DPI, "savefig.bbox": "tight",
    "font.family": "DejaVu Sans", "font.size": 7.5,
    "axes.labelsize": 7.5, "axes.titlesize": 8, "legend.fontsize": 6.5,
    "xtick.labelsize": 6.8, "ytick.labelsize": 6.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.6, "lines.linewidth": 1.1,
    "savefig.facecolor": "white", "figure.facecolor": "white", "pdf.fonttype": 42,
})
sns.set_style("white")

GREY, BLUE, RED, GREEN, ORANGE, PURPLE = ("#7F7F7F", "#3B6EA5", "#C0392B",
                                          "#4E9A51", "#D98A28", "#7D5BA6")
CAMP = [s["name"] for s in SPECS]
TITLE = {s["name"]: s["title"] for s in SPECS}
SHORT = {"A": "General drug-like", "B": "CNS-oriented",
         "C": "Analogue", "D": "Substructure"}
CCOL = {"A": BLUE, "B": GREEN, "C": ORANGE, "D": PURPLE}
ORDER = ["baseline"] + [f"designed_{n}" for n in CAMP]
OCOL = [GREY] + [CCOL[n] for n in CAMP]
OLAB = ["baseline"] + [f"designed {n}" for n in CAMP]
saved = []


def save(fig, tag):
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{tag}.{ext}", dpi=DPI, format=ext)
    plt.close(fig)
    saved.append(tag)
    print(f"  saved {tag}", flush=True)


def panel(ax, letter, dx=-0.17, dy=1.04):
    ax.text(dx, dy, letter, transform=ax.transAxes, fontsize=9,
            fontweight="bold", va="bottom", ha="left")


def mol_png(smiles_list, legends, per_row, size=(330, 290)):
    mols = [Chem.MolFromSmiles(s) for s in smiles_list]
    keep = [(m, l) for m, l in zip(mols, legends) if m is not None]
    if not keep:
        return None
    mols, legends = zip(*keep)
    rows = int(np.ceil(len(mols) / per_row))
    d = rdMolDraw2D.MolDraw2DCairo(size[0] * per_row, size[1] * rows, size[0], size[1])
    o = d.drawOptions(); o.legendFontSize = 19; o.bondLineWidth = 2
    d.DrawMolecules(list(mols), legends=list(legends))
    d.FinishDrawing()
    return Image.open(io.BytesIO(d.GetDrawingText()))


# -------------------------------------------------------------- data
train_desc = pd.read_csv(T / "training_descriptors.csv")
base_desc = pd.read_csv(T / "baseline_descriptors.csv")
des_desc = {n: pd.read_csv(T / f"designed_descriptors_{n}.csv") for n in CAMP}
prior_loss = np.load(OUT / "npz" / "prior_loss.npy")
bench = pd.read_csv(T / "generative_benchmarks.csv").set_index("set")
kl = pd.read_csv(T / "kl_divergence.csv", index_col=0)
synth = pd.read_csv(T / "synth_composite.csv")
flags = pd.read_csv(T / "druglike_flags.csv")
scaf = pd.read_csv(T / "scaffold_stats.csv").set_index("set")
alerts = pd.read_csv(T / "structural_alerts.csv")
ad = pd.read_csv(T / "applicability_domain.csv")
space = pd.read_csv(T / "chemical_space.csv")
emb_name = json.loads((T / "embedding_method.json").read_text())["method"]
ad_meta = json.loads((T / "ad_meta.json").read_text())
feas = {n: json.loads((T / f"feasibility_{n}.json").read_text()) for n in CAMP}
camp = {n: json.loads((T / f"campaign_summary_{n}.json").read_text()) for n in CAMP}
inspec = {n: pd.read_csv(T / f"target_inspec_fractions_{n}.csv") for n in CAMP}
top_scaf = json.loads((T / "top_scaffolds.json").read_text())
tri_sum = pd.read_csv(T / "triage_summary.csv").set_index("set")
prior_meta = json.loads((T / "prior_meta.json").read_text())
sweep = pd.read_csv(T / "intensity_sweep.csv")
SW = sorted(sweep["campaign"].unique())


# =========================================================== Figure 1
def figure1():
    fig, ax = plt.subplots(figsize=(7.1, 7.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 25); ax.axis("off")
    phases = [("PREPARATION", 23.6, BLUE), ("PRIOR LEARNING", 18.4, BLUE),
              ("GOAL-DIRECTED DESIGN", 13.7, RED), ("AUDIT AND TRIAGE", 7.4, GREEN)]
    boxes = [(22.6, "1  Corpus: ZINC-250k or user CSV", BLUE),
             (21.2, "2  Standardise · canonicalise · dedup · 5–50 heavy atoms", BLUE),
             (19.8, "3  SMILES → SELFIES → token vocabulary", BLUE),
             (17.4, "4  Causal transformer prior (next-token cross-entropy)", BLUE),
             (16.0, "5  Baseline sampling — the unsteered control", BLUE),
             (12.7, "6a  DESIGN SPECIFICATION (declarative, auditable)", RED),
             (11.3, "6b  Derringer–Suich desirability → scalar reward", RED),
             (9.9, "6c  FEASIBILITY PREVIEW — before any RL compute", RED),
             (8.5, "6d  REINFORCE fine-tuning → designed library", RED),
             (6.4, "7–9   Benchmarks · drug-likeness · synthesizability", GREEN),
             (5.0, "10–12  Scaffolds · chemical space · alerts · domain", GREEN),
             (3.6, "13  GO / CAUTION / NO-GO triage → ranked shortlist", GREEN),
             (2.2, "14  Single-archive export (tables · figures · checkpoints)", GREEN)]
    for label, y, col in phases:
        ax.add_patch(FancyBboxPatch((0.15, y - 0.42), 9.7, 0.78,
                                    boxstyle="round,pad=0.02,rounding_size=0.12",
                                    linewidth=0, facecolor=col, alpha=0.13))
        ax.text(0.45, y - 0.03, label, fontsize=8, fontweight="bold",
                color=col, va="center")
    for y, txt, col in boxes:
        hl = "FEASIBILITY" in txt or "SPECIFICATION" in txt
        ax.add_patch(FancyBboxPatch((0.7, y - 0.45), 8.7, 0.9,
                                    boxstyle="round,pad=0.03,rounding_size=0.1",
                                    linewidth=1.5 if hl else 0.7,
                                    edgecolor=col, facecolor="white"))
        ax.text(1.0, y, txt, fontsize=7.3, va="center",
                fontweight="bold" if hl else "normal", color="#111111")
    ys = [b[0] for b in boxes]
    for y0, y1 in zip(ys[:-1], ys[1:]):
        ax.add_patch(FancyArrowPatch((5.05, y0 - 0.47), (5.05, y1 + 0.47),
                                     arrowstyle="-|>", mutation_scale=7,
                                     color="#555555", linewidth=0.7))
    ax.add_patch(FancyArrowPatch((0.68, 9.9), (0.22, 9.9), arrowstyle="-|>",
                                 mutation_scale=7, color=RED, linewidth=0.9))
    ax.plot([0.22, 0.22], [9.9, 12.7], color=RED, lw=0.9, ls=(0, (3, 2)))
    ax.add_patch(FancyArrowPatch((0.22, 12.7), (0.68, 12.7), arrowstyle="-|>",
                                 mutation_scale=7, color=RED, linewidth=0.9))
    ax.text(0.03, 11.3, "revise spec", fontsize=6.3, color=RED, rotation=90,
            va="center", ha="center")
    ax.text(5.0, 0.8, "Ranked candidates → downstream ADMET / toxicity evaluation",
            fontsize=7.4, style="italic", ha="center", color="#333333")
    save(fig, "Figure_1_workflow")


# =========================================================== Figure 2
def figure2():
    fig = plt.figure(figsize=(7.1, 4.9))
    gs = fig.add_gridspec(2, 4, height_ratios=[1, 1.25], hspace=0.66, wspace=0.34)
    for i, n in enumerate(CAMP):
        ax = fig.add_subplot(gs[0, i])
        sc = np.load(OUT / "npz" / f"pre_scores_{n}.npy")
        ax.hist(sc, bins=40, color=CCOL[n], alpha=0.9, edgecolor="none")
        ax.axvline(np.median(sc), color="k", ls="--", lw=0.8)
        ax.set_title(f"{n} — {SHORT[n]}", fontsize=7.2)
        ax.set_xlabel("Baseline design score"); ax.set_xlim(-0.02, 1)
        if i == 0:
            ax.set_ylabel("Molecules")
        ax.text(0.96, 0.95,
                f"med {np.median(sc):.3f}\np95 {np.quantile(sc, .95):.3f}\n"
                f"gate {feas[n]['gate_pass_fraction']*100:.0f}%",
                transform=ax.transAxes, ha="right", va="top", fontsize=5.9)
        panel(ax, "abcd"[i], dx=-0.24)
    ax2 = fig.add_subplot(gs[1, :])
    keys = sorted({k for n in CAMP for k in feas[n]["per_objective_mean_desirability"]})
    xs = np.arange(len(keys)); width = 0.2
    for i, n in enumerate(CAMP):
        vals = [feas[n]["per_objective_mean_desirability"].get(k, np.nan) for k in keys]
        ax2.bar(xs + (i - 1.5) * width, vals, width, color=CCOL[n], label=n)
    ax2.set_xticks(xs); ax2.set_xticklabels(keys, rotation=28, ha="right")
    ax2.set_ylabel("Mean desirability (baseline)"); ax2.set_ylim(0, 1.06)
    ax2.axhline(1.0, color=GREY, lw=0.5, ls=":")
    ax2.legend(title="Campaign", ncol=4, frameon=False, loc="lower left",
               fontsize=6.3, title_fontsize=6.3)
    ax2.set_title("Per-objective attribution across the unsteered baseline", fontsize=7.6)
    panel(ax2, "e", dx=-0.055)
    save(fig, "Figure_2_feasibility")


# =========================================================== Figure 3
def figure3():
    fig = plt.figure(figsize=(7.1, 5.3))
    gs = fig.add_gridspec(2, 4, height_ratios=[1, 1.2], hspace=0.62, wspace=0.42)
    ymax = max(np.load(OUT / "npz" / f"rl_best_{n}.npy").max() for n in CAMP)
    for i, n in enumerate(CAMP):
        ax = fig.add_subplot(gs[0, i])
        mean = np.load(OUT / "npz" / f"rl_mean_{n}.npy")
        best = np.load(OUT / "npz" / f"rl_best_{n}.npy")
        ax.plot(best, color=CCOL[n], alpha=0.33, lw=0.8)
        ax.plot(mean, color=CCOL[n], lw=1.4)
        ax.set_ylim(0, ymax * 1.08)
        ax.set_title(f"{n} — {SHORT[n]}", fontsize=7.2)
        ax.set_xlabel("RL step")
        if i == 0:
            ax.set_ylabel("Design score")
            ax.text(0.05, 0.97, "batch max", color=CCOL[n], alpha=0.65,
                    fontsize=5.8, transform=ax.transAxes, va="top")
            ax.text(0.05, 0.86, "batch mean", color=CCOL[n], fontsize=5.8,
                    transform=ax.transAxes, va="top")
        panel(ax, "abcd"[i], dx=-0.26)

    axe = fig.add_subplot(gs[1, :2])
    d = inspec["A"]
    ys = np.arange(len(d))[::-1]
    axe.hlines(ys, d["baseline_in_spec"], d["designed_in_spec"],
               color="#CCCCCC", lw=1.8, zorder=1)
    for y, b, g in zip(ys, d["baseline_in_spec"], d["designed_in_spec"]):
        axe.annotate("", xy=(g, y), xytext=(b, y),
                     arrowprops=dict(arrowstyle="-|>", lw=0.0,
                                     color=RED if g < b else BLUE,
                                     mutation_scale=7), zorder=2)
    axe.scatter(d["baseline_in_spec"], ys, s=22, color=GREY, zorder=3,
                label="baseline")
    axe.scatter(d["designed_in_spec"], ys, s=22,
                color=[RED if g < b else BLUE
                       for b, g in zip(d["baseline_in_spec"], d["designed_in_spec"])],
                zorder=4, label="designed (red = regression)")
    axe.set_yticks(ys); axe.set_yticklabels(d["objective"], fontsize=6.6)
    axe.set_xlabel("Fraction inside target window"); axe.set_xlim(-0.03, 1.05)
    axe.legend(frameon=False, fontsize=6.2, loc="lower left")
    axe.set_title("Campaign A per-objective compliance", fontsize=7.6)
    panel(axe, "e", dx=-0.33)

    axf = fig.add_subplot(gs[1, 2:])
    xs = np.arange(len(CAMP)); width = 0.36
    b = [camp[n]["baseline_mean"] for n in CAMP]
    g = [camp[n]["designed_mean"] for n in CAMP]
    axf.bar(xs - width / 2, b, width, color=GREY, label="baseline")
    axf.bar(xs + width / 2, g, width, color=[CCOL[n] for n in CAMP], label="designed")
    for i, n in enumerate(CAMP):
        lab = f"×{g[i]/b[i]:.1f}" if b[i] > 1e-6 else "n/a"
        axf.text(xs[i], max(b[i], g[i]) + 0.02, lab, ha="center", fontsize=6.2)
    axf.set_xticks(xs); axf.set_xticklabels(CAMP)
    axf.set_xlabel("Campaign"); axf.set_ylabel("Mean design score")
    axf.set_ylim(0, 1.08)
    axf.legend(frameon=False, fontsize=6.2, ncol=2, loc="upper left")
    axf.set_title("Composite design score", fontsize=7.6)
    panel(axf, "f", dx=-0.21)
    save(fig, "Figure_3_optimisation")


# =========================================================== Figure 4
def figure4():
    fig, axes = plt.subplots(2, 3, figsize=(7.1, 4.5))
    specs = [("design_score", "Mean design score", "a"),
             ("uniqueness", "Uniqueness", "b"),
             ("int_diversity", "Internal diversity", "c"),
             ("n_scaffolds", "Distinct scaffolds", "d"),
             ("any_alert", "Fraction with any alert", "e")]
    for ax, (col, lab, L) in zip(axes.flat, specs):
        for n in SW:
            sub = sweep[sweep["campaign"] == n].sort_values("rl_steps")
            ax.plot(sub["rl_steps"], sub[col], "o-", color=CCOL[n], ms=3.2,
                    lw=1.2, label=f"{n}")
        ax.set_xlabel("RL steps"); ax.set_ylabel(lab)
        ax.set_xticks([0, 10, 20, 40, 80])
        ax.set_title(lab, fontsize=7.6)
        panel(ax, L)
    axes.flat[1].legend(title="Campaign", frameon=False, fontsize=6,
                        title_fontsize=6, ncol=3, loc="lower left")

    ax = axes.flat[5]
    for n in SW:
        sub = sweep[sweep["campaign"] == n].sort_values("rl_steps")
        ax.plot(sub["design_score"], sub["int_diversity"], "-", color=CCOL[n],
                lw=1.0, alpha=0.6)
        ax.scatter(sub["design_score"], sub["int_diversity"],
                   s=[14 + 0.45 * s for s in sub["rl_steps"]], color=CCOL[n], zorder=3)
        for _, r in sub.iterrows():
            ax.annotate(f"{int(r['rl_steps'])}", (r["design_score"], r["int_diversity"]),
                        textcoords="offset points", xytext=(4, 3), fontsize=5.4,
                        color=CCOL[n])
    ax.set_xlabel("Mean design score"); ax.set_ylabel("Internal diversity")
    ax.set_title("Compliance–diversity frontier", fontsize=7.6)
    panel(ax, "f")
    fig.tight_layout()
    save(fig, "Figure_4_intensity_sweep")


# =========================================================== Figure 5
def figure5():
    fig = plt.figure(figsize=(7.1, 6.3))
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 1.15], hspace=0.62, wspace=0.32)

    ax = fig.add_subplot(gs[0, 0])
    mets = ["validity", "uniqueness", "novelty", "int_diversity"]
    labs = ["Validity", "Uniq.", "Novelty", "Diversity"]
    xs = np.arange(len(mets)); w = 0.16
    for i, (s, c) in enumerate(zip(ORDER, OCOL)):
        ax.bar(xs + (i - 2) * w, [bench.loc[s, m] for m in mets], w, color=c)
    ax.set_xticks(xs); ax.set_xticklabels(labs, fontsize=6.4)
    ax.set_ylim(0, 1.12); ax.set_ylabel("Score")
    ax.set_title("Generative benchmarks (80 RL steps)", fontsize=7.6)
    panel(ax, "a", dx=-0.235)

    ax = fig.add_subplot(gs[0, 1])
    order2 = ["training"] + ORDER
    cols2 = ["#333333"] + OCOL
    sub = scaf.loc[order2]
    xs = np.arange(len(order2))
    ax.bar(xs, sub["n_scaffolds"], color=cols2)
    ax.set_xticks(xs); ax.set_xticklabels(["train", "base"] + CAMP, fontsize=6.4)
    ax.set_ylabel("Distinct scaffolds")
    ax.set_title("Bemis–Murcko scaffolds", fontsize=7.6); panel(ax, "b")

    ax = fig.add_subplot(gs[1, 0])
    summ = alerts.groupby("set")[["pains", "brenk", "nih", "any_alert"]].mean()
    mets = ["pains", "brenk", "nih", "any_alert"]
    xs = np.arange(len(mets))
    for i, (s, c) in enumerate(zip(ORDER, OCOL)):
        ax.bar(xs + (i - 2) * w, summ.loc[s, mets].values, w, color=c)
    ax.set_xticks(xs); ax.set_xticklabels(["PAINS", "BRENK", "NIH", "any"], fontsize=6.4)
    ax.set_ylabel("Fraction flagged"); ax.set_ylim(0, 1.08)
    ax.set_title("Structural alerts", fontsize=7.6); panel(ax, "c", dx=-0.235)

    ax = fig.add_subplot(gs[1, 1])
    up = ad["leverage"].quantile(0.995)
    for s, c in zip(ORDER, OCOL):
        sns.kdeplot(ad[ad["set"] == s]["leverage"].clip(upper=up), ax=ax, color=c, lw=1.2)
    ax.axvline(ad_meta["h_star"], color="k", ls="--", lw=0.9)
    ax.set_xlim(0, ad_meta["h_star"] * 1.25)
    ax.text(ad_meta["h_star"], ax.get_ylim()[1] * 0.95,
            f" h* = {ad_meta['h_star']:.3f}", fontsize=6, va="top", ha="left")
    ax.set_xlabel("Leverage"); ax.set_ylabel("Density")
    ax.set_title("Applicability domain (all in-domain)", fontsize=7.6); panel(ax, "d")

    ax = fig.add_subplot(gs[2, 0])
    labels = ["GO", "CAUTION", "NO-GO"]
    cols = [GREEN, ORANGE, "#BBBBBB"]
    xs = np.arange(len(ORDER)); bottom = np.zeros(len(ORDER))
    for lab, c in zip(labels, cols):
        key = {"GO": "n_GO", "CAUTION": "n_CAUTION", "NO-GO": "n_NOGO"}[lab]
        vals = np.array([tri_sum.loc[s, key] / tri_sum.loc[s, "n_total"] for s in ORDER])
        ax.bar(xs, vals, 0.62, bottom=bottom, color=c, label=lab)
        bottom += vals
    for i, s in enumerate(ORDER):
        ax.text(xs[i], 1.02, f"{int(tri_sum.loc[s, 'n_GO'])} GO", ha="center",
                fontsize=5.8)
    ax.set_xticks(xs); ax.set_xticklabels(["base"] + CAMP, fontsize=6.6)
    ax.set_ylabel("Fraction of structures"); ax.set_ylim(0, 1.12)
    ax.legend(frameon=False, fontsize=6, ncol=3, loc="lower center",
              bbox_to_anchor=(0.5, -0.46))
    ax.set_title("Triage composition", fontsize=7.6); panel(ax, "e", dx=-0.235)

    ax = fig.add_subplot(gs[2, 1]); ax.axis("off")
    try:
        t = pd.read_csv(T / "top_candidates_A.csv").head(4)
        legs = [f"QED {r.QED:.2f} | SA {r.SAscore:.1f} | C {r.composite:.2f}"
                for r in t.itertuples()]
        img = mol_png(t["smiles"].tolist(), legs, 2)
        if img is not None:
            ax.imshow(img)
    except Exception as e:
        ax.text(0.5, 0.5, "no GO candidates", ha="center", fontsize=7)
    ax.set_title("Top GO candidates, campaign A", fontsize=7.6)
    panel(ax, "f", dy=0.99)

    handles = [plt.Line2D([], [], color=c, lw=3) for c in OCOL]
    fig.legend(handles, OLAB, ncol=5, frameon=False, fontsize=6.4,
               loc="lower center", bbox_to_anchor=(0.5, -0.025))
    save(fig, "Figure_5_audit_triage")


# ====================================================== Extended Data
def ed1():
    fig = plt.figure(figsize=(7.1, 5.6))
    gs = fig.add_gridspec(3, 3, hspace=0.62, wspace=0.34)
    cols = [("MW", "MW (Da)"), ("LogP", "cLogP"), ("TPSA", "TPSA (Å²)"),
            ("HBD", "H-bond donors"), ("HBA", "H-bond acceptors"), ("QED", "QED")]
    for i, (c, xl) in enumerate(cols):
        ax = fig.add_subplot(gs[i // 3, i % 3])
        sns.histplot(train_desc[c], bins=40, kde=True, ax=ax, color=BLUE,
                     edgecolor="none", alpha=0.85)
        ax.set_xlabel(xl); ax.set_ylabel("Count")
        ax.set_title(f"{c} (mean {train_desc[c].mean():.2f})", fontsize=7.4)
        panel(ax, "abcdef"[i])
    ax = fig.add_subplot(gs[2, :])
    ax.plot(prior_loss, color=BLUE, lw=0.9)
    for e in range(1, prior_meta["epochs"]):
        ax.axvline(e * prior_meta["steps_per_epoch"], color=GREY, lw=0.5, ls=":")
    ax.set_xlabel("Training step"); ax.set_ylabel("Cross-entropy (EMA)")
    ax.set_title(f"Prior pretraining — {prior_meta['n_params']:,} parameters, "
                 f"final {prior_loss[-1]:.3f}", fontsize=7.6)
    panel(ax, "g", dx=-0.055)
    save(fig, "ExtendedData_Fig_1_corpus_and_prior")


def ed_validation(camp_name, tag):
    spec = [s for s in SPECS if s["name"] == camp_name][0]
    props = list(spec["properties"])
    ncol = 4; nrow = int(np.ceil(len(props) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(7.1, 1.95 * nrow))
    axes = np.array(axes).reshape(-1)
    dd = des_desc[camp_name]
    for i, (ax, prop) in enumerate(zip(axes, props)):
        col = prop if prop in dd.columns else "Rings"
        if col not in dd.columns:
            ax.axis("off"); continue
        sns.kdeplot(base_desc[col], ax=ax, color=GREY, fill=True, alpha=0.3, lw=1.0)
        sns.kdeplot(dd[col], ax=ax, color=CCOL[camp_name], fill=True, alpha=0.35, lw=1.0)
        cfg = spec["properties"][prop]
        lo_all = min(dd[col].min(), base_desc[col].min())
        hi_all = max(dd[col].max(), base_desc[col].max())
        if cfg["mode"] == "range":
            ax.axvspan(cfg["min"], cfg["max"], color=GREEN, alpha=0.16, lw=0)
        elif cfg["mode"] == "max_cap":
            ax.axvspan(lo_all, cfg["cap"], color=GREEN, alpha=0.16, lw=0)
        elif cfg["mode"] == "maximize":
            ax.axvspan(cfg["lo"], hi_all, color=GREEN, alpha=0.16, lw=0)
        ax.set_title(prop, fontsize=7.4); ax.set_ylabel(""); ax.set_yticks([])
        panel(ax, "abcdefgh"[i], dx=-0.12)
    for ax in axes[len(props):]:
        ax.axis("off")
    fig.suptitle(f"Campaign {camp_name} — {TITLE[camp_name]}", fontsize=7.8, y=1.02)
    fig.tight_layout()
    save(fig, tag)


def ed4():
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.3))
    for s, c, lab in zip(["training"] + ORDER, ["#333333"] + OCOL,
                         ["training"] + OLAB):
        sub = space[space["set"] == s]
        axes[0].scatter(sub["pca1"], sub["pca2"], s=2.6, alpha=0.5, c=c,
                        linewidths=0, label=lab)
        axes[1].scatter(sub["emb1"], sub["emb2"], s=2.6, alpha=0.5, c=c, linewidths=0)
    axes[0].set_xlabel("PC1"); axes[0].set_ylabel("PC2")
    axes[0].set_title("PCA of Morgan fingerprints", fontsize=7.8)
    axes[0].legend(frameon=False, fontsize=5.6, markerscale=3, ncol=2)
    panel(axes[0], "a")
    axes[1].set_xlabel("dim 1"); axes[1].set_ylabel("dim 2")
    axes[1].set_title(f"{emb_name} projection", fontsize=7.8); panel(axes[1], "b")
    fig.tight_layout()
    save(fig, "ExtendedData_Fig_4_chemical_space")


def ed5():
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 4.4))
    for s, c in zip(ORDER, OCOL):
        sns.kdeplot(flags[flags["set"] == s]["QED"], ax=axes[0, 0], color=c, lw=1.2)
        sns.kdeplot(synth[synth["set"] == s]["SAscore"], ax=axes[0, 1], color=c, lw=1.2)
        sns.kdeplot(synth[synth["set"] == s]["synth_score"], ax=axes[1, 0],
                    color=c, lw=1.2)
    axes[0, 0].set_xlabel("QED"); axes[0, 0].set_title("Drug-likeness", fontsize=7.6)
    panel(axes[0, 0], "a")
    axes[0, 1].set_xlabel("SAscore (1 easy → 10 hard)")
    axes[0, 1].set_title("Synthetic accessibility", fontsize=7.6); panel(axes[0, 1], "b")
    axes[1, 0].set_xlabel("Composite synthesizability")
    axes[1, 0].set_title("Composite synthesizability", fontsize=7.6); panel(axes[1, 0], "c")
    ax = axes[1, 1]
    kcols = list(kl.index); xs = np.arange(len(kcols)); w = 0.16
    for i, (s, c) in enumerate(zip(ORDER, OCOL)):
        ax.bar(xs + (i - 2) * w, kl[s].values, w, color=c)
    ax.set_xticks(xs); ax.set_xticklabels(kcols, fontsize=6.4)
    ax.set_ylabel("Symmetric KL")
    ax.set_title("Shift from training corpus", fontsize=7.6); panel(ax, "d")
    handles = [plt.Line2D([], [], color=c, lw=3) for c in OCOL]
    fig.legend(handles, OLAB, ncol=5, frameon=False, fontsize=6.4,
               loc="lower center", bbox_to_anchor=(0.5, -0.05))
    fig.tight_layout()
    save(fig, "ExtendedData_Fig_5_property_distributions")


def ed6():
    fig = plt.figure(figsize=(7.1, 7.0))
    gs = fig.add_gridspec(3, 1, height_ratios=[1.1, 1.1, 1.0], hspace=0.3)
    for i, (key, title) in enumerate([("training", "Training corpus sample"),
                                      ("designed_A", "Campaign A designed library")]):
        ax = fig.add_subplot(gs[i]); ax.axis("off")
        tops = [t for t in top_scaf[key][:8] if t[0]]
        img = mol_png([t[0] for t in tops], [f"n = {t[1]}" for t in tops], 4)
        if img is not None:
            ax.imshow(img)
        ax.set_title(f"Most frequent Bemis–Murcko scaffolds — {title}",
                     fontsize=7.6)
        ax.text(-0.02, 1.04, "ab"[i], transform=ax.transAxes, fontsize=9,
                fontweight="bold")
    fg = pd.read_csv(T / "functional_group_freq.csv", index_col=0)
    ax = fig.add_subplot(gs[2])
    cols = ["training"] + ORDER
    xs = np.arange(len(fg.index)); w = 0.15
    for i, (c, col) in enumerate(zip(cols, ["#333333"] + OCOL)):
        ax.bar(xs + (i - 2) * w, fg[c].values, w, color=col)
    ax.set_xticks(xs); ax.set_xticklabels(fg.index, rotation=45, ha="right", fontsize=6.0)
    ax.set_ylabel("Fraction of molecules")
    ax.set_title("Functional-group frequency", fontsize=7.6)
    ax.text(-0.055, 1.04, "c", transform=ax.transAxes, fontsize=9, fontweight="bold")
    save(fig, "ExtendedData_Fig_6_scaffolds_groups")


def ed7():
    fig, axes = plt.subplots(3, 1, figsize=(7.1, 7.2))
    for ax, n, L in zip(axes, ["B", "C", "D"], "abc"):
        ax.axis("off")
        try:
            t = pd.read_csv(T / f"top_candidates_{n}.csv").head(4)
        except Exception:
            t = pd.DataFrame()
        if len(t) == 0:
            ax.text(0.5, 0.5, f"Campaign {n}: no molecule cleared the GO gates",
                    ha="center", va="center", fontsize=8.5, style="italic")
        else:
            legs = [f"QED {r.QED:.2f} | SA {r.SAscore:.1f} | C {r.composite:.2f}"
                    for r in t.itertuples()]
            img = mol_png(t["smiles"].tolist(), legs, 4)
            if img is not None:
                ax.imshow(img)
        ax.set_title(f"Campaign {n} — {TITLE[n]}", fontsize=7.6)
        ax.text(-0.02, 1.02, L, transform=ax.transAxes, fontsize=9, fontweight="bold")
    fig.tight_layout()
    save(fig, "ExtendedData_Fig_7_top_candidates_BCD")


if __name__ == "__main__":
    figure1(); figure2(); figure3(); figure4(); figure5()
    ed1()
    ed_validation("A", "ExtendedData_Fig_2_validation_A")
    ed_validation("B", "ExtendedData_Fig_3_validation_B")
    ed4(); ed5(); ed6(); ed7()
    (FIG / "figure_manifest.json").write_text(json.dumps(saved, indent=2))
    print("STAGE 5 COMPLETE", flush=True)
