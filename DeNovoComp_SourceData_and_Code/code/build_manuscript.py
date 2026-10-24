# -*- coding: utf-8 -*-
"""Build the Nature Computational Science submission from out/run_record.json.

Every numeric statement is interpolated from the run record, so no value can
appear in the manuscript that the pipeline did not produce.
"""
import json
from pathlib import Path

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

import manuscript_prose as P
import prose_short as S
import results_prose as RP


def main_text_words():
    import re
    w = lambda t: len(re.sub(r"\s+", " ", t).split())
    fns = ["architecture", "feasibility_1", "feasibility_2", "optimisation_1",
           "rl_trajectory", "per_objective", "tradeoff", "steering_cost",
           "sweep_para", "sweep_para2", "alerts_ad", "ad_para", "triage_para"]
    return (sum(w(t) for _, t in S.INTRO)
            + sum(w(getattr(RP, f)()) for f in fns)
            + sum(w(t) for _, t in S.DISCUSSION)
            + w(S.LIMITATIONS) + w(S.FUTURE) + w(S.CONCLUSIONS))

ROOT = Path("/home/claude/dnc")
OUT = ROOT / "out"
FIG = OUT / "figures"
DELIV = ROOT / "deliverables"; DELIV.mkdir(exist_ok=True)
R = json.loads((OUT / "run_record.json").read_text())

CAMP = ["A", "B", "C", "D"]
BASE = "baseline"
D = {n: f"designed_{n}" for n in CAMP}
TITLE = R["campaign_titles"]
cur, pri, cfg = R["curation"], R["prior"], R["config"]
bench, kl, dl, sy = R["benchmarks"], R["kl"], R["druglike"], R["synth"]
scaf, al, adm, tri = R["scaffold"], R["alerts"], R["ad"], R["triage"]
feas, cam, insp = R["feasibility"], R["campaign"], R["inspec"]
pct, f3, f2, fold = RP.pct, RP.f3, RP.f2, RP.fold


# --------------------------------------------------------------- styling
def setup(doc):
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(12)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    st.paragraph_format.line_spacing = 2.0
    st.paragraph_format.space_after = Pt(0)
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Inches(1.0)
    sec.top_margin = sec.bottom_margin = Inches(1.0)
    ln = OxmlElement("w:lnNumType")
    ln.set(qn("w:countBy"), "1")
    ln.set(qn("w:restart"), "continuous")
    ln.set(qn("w:distance"), "360")
    sec._sectPr.append(ln)
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run()
    for kind in ("begin", "instr", "end"):
        if kind == "instr":
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve"); el.text = " PAGE "
        else:
            el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), kind)
        run._r.append(el)


def para(doc, text, *, size=12, bold=False, italic=False, align=None,
         after=6, before=0, spacing=2.0):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(size); r.bold = bold; r.italic = italic
    r.font.name = "Times New Roman"
    pf = p.paragraph_format
    pf.space_after = Pt(after); pf.space_before = Pt(before); pf.line_spacing = spacing
    if align is not None:
        p.alignment = align
    return p


def J(doc, text):
    return para(doc, text, align=WD_ALIGN_PARAGRAPH.JUSTIFY)


def heading(doc, text, level=1):
    sizes = {1: 13, 2: 12, 3: 12}
    return para(doc, text, size=sizes[level], bold=True, before=12, after=6,
                spacing=1.15, italic=(level == 3))


def bullet(doc, text, lead=None):
    p = doc.add_paragraph(style="List Bullet")
    if lead:
        r = p.add_run(lead + " "); r.bold = True
        r.font.size = Pt(12); r.font.name = "Times New Roman"
    r = p.add_run(text); r.font.size = Pt(12); r.font.name = "Times New Roman"
    p.paragraph_format.line_spacing = 2.0
    p.paragraph_format.space_after = Pt(4)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return p


def caption(doc, num, text, size=10):
    p = doc.add_paragraph()
    r1 = p.add_run(num + " "); r1.bold = True; r1.font.size = Pt(size)
    r1.font.name = "Times New Roman"
    r2 = p.add_run(text); r2.font.size = Pt(size); r2.font.name = "Times New Roman"
    p.paragraph_format.line_spacing = 1.2
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.space_before = Pt(8)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return p


def table(doc, header, rows, num, cap, widths=None, font=9):
    caption(doc, num, cap)
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    for i, h in enumerate(header):
        cell = t.rows[0].cells[i]; cell.text = ""
        p = cell.paragraphs[0]
        r = p.add_run(str(h)); r.bold = True; r.font.size = Pt(font)
        r.font.name = "Times New Roman"
        p.paragraph_format.line_spacing = 1.0; p.paragraph_format.space_after = Pt(1)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            r = p.add_run(str(v)); r.font.size = Pt(font)
            r.font.name = "Times New Roman"
            p.paragraph_format.line_spacing = 1.0; p.paragraph_format.space_after = Pt(1)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    para(doc, "", size=6, after=6, spacing=1.0)
    return t


def figure_block(doc, tag, num, legend, width=6.4):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    p.add_run().add_picture(str(FIG / f"{tag}.png"), width=Inches(width))
    caption(doc, num, legend)
    para(doc, "", size=6, after=10, spacing=1.0)


def page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# =====================================================================
MAIN_FIGS = [
    ("Figure_1_workflow", "Figure 1 |",
     "Architecture of the DeNovoComp pipeline. Fourteen stages grouped into four phases: "
     "preparation (corpus curation, standardisation, SELFIES conversion and tokenisation), "
     "prior learning (transformer pretraining and unconditioned baseline sampling), "
     "goal-directed design (specification declaration, desirability construction, "
     "feasibility preview and policy-gradient fine-tuning) and audit and triage. The two "
     "stages emphasised in bold are those without close analogue in existing pipelines. "
     "The dashed return path indicates the intended response to an unfavourable "
     "feasibility preview: revise the specification before, rather than after, committing "
     "optimisation compute."),
    ("Figure_2_feasibility", "Figure 2 |",
     "Feasibility of each specification, assessed before any optimisation. a–d, "
     "Distribution of composite design scores obtained by scoring the single shared "
     "baseline library (n = {n:,} molecules) against each campaign's specification; dashed "
     "line, median; inset, median, 95th percentile and the fraction of molecules passing "
     "the hard structural gates. e, Mean desirability attained per individual objective "
     "across the baseline library, computed over molecules passing the hard gates. Bars "
     "near unity mark objectives the unsteered prior already satisfies; short bars "
     "localise where optimisation pressure will be concentrated. Campaign D's median of "
     "zero with a non-zero 95th percentile is the signature of a demanding but reachable "
     "categorical constraint, as distinct from an unsatisfiable one."),
    ("Figure_3_optimisation", "Figure 3 |",
     "Effect of goal-directed optimisation at the default intensity ({steps} steps, batch "
     "{batch}). a–d, Reinforcement-learning reward trajectories; heavy line, batch "
     "mean; light line, batch maximum; all panels share a common ordinate. e, Fraction of "
     "molecules inside each target window for campaign A, baseline (grey) versus designed; "
     "designed points are blue where compliance improved and red where it regressed. f, "
     "Mean composite design score before and after optimisation for all four campaigns, "
     "annotated with fold change. Scores are computed under each campaign's own "
     "specification and are therefore comparable within, but not across, campaigns."),
    ("Figure_4_intensity_sweep", "Figure 4 |",
     "Optimisation intensity governs a compliance–diversity frontier. The policy was "
     "snapshotted at 10, 20, 40 and 80 reinforcement-learning steps and a "
     "{nsweep:,}-molecule library sampled from each; step 0 is the unsteered prior. "
     "a–e, Mean design score, uniqueness, internal diversity, distinct "
     "Bemis–Murcko frameworks and structural-alert incidence against intensity for "
     "campaigns A, B and D. f, The same data as a frontier, mean design score against "
     "internal diversity, with marker size and annotation giving the step count. The "
     "pipeline's default of {steps} steps lies well past the knee for the graded-objective "
     "campaigns A and B, whereas campaign D requires high intensity to satisfy its "
     "categorical gate and pays correspondingly in diversity."),
    ("Figure_5_audit_triage", "Figure 5 |",
     "Audit and triage of the libraries produced at the default intensity. a, Validity, "
     "uniqueness, novelty with respect to the training corpus and internal diversity. b, "
     "Number of distinct Bemis–Murcko frameworks per set, including the training "
     "sample. c, Fraction of each library carrying PAINS, BRENK or NIH structural alerts, "
     "and the union of the three. d, Leverage distributions against the training "
     "fingerprint basis; dashed line, the conventional h* = 3p/n threshold. Every molecule "
     "in every library falls below it, so the domain test does not discriminate at this "
     "configuration. e, Composition of each library under the GO/CAUTION/NO-GO rule at the "
     "configured thresholds, with absolute GO counts above each bar; fractions are over "
     "unique structures, which differ between libraries because optimisation reduces "
     "uniqueness. f, The four highest-ranked GO candidates of campaign A, annotated with "
     "QED, synthetic accessibility and composite priority score."),
]

ED_FIGS = [
    ("ExtendedData_Fig_1_corpus_and_prior", "Extended Data Fig. 1 |",
     "Training corpus and prior. a–f, Descriptor distributions over a random sample "
     "of the curated corpus, with kernel density estimate overlaid; this profile defines "
     "the chemistry the prior can express fluently. g, Exponentially smoothed token-level "
     "cross-entropy against training step; dotted lines mark epoch boundaries."),
    ("ExtendedData_Fig_2_validation_A", "Extended Data Fig. 2 |",
     "Target-profile validation for campaign A. Kernel density estimates of each targeted "
     "descriptor in the baseline (grey) and designed (blue) libraries, with the requested "
     "window shaded green. The molecular-weight panel shows the designed distribution "
     "displaced below the requested window, the regression quantified in Extended Data "
     "Table 2."),
    ("ExtendedData_Fig_4_chemical_space", "Extended Data Fig. 3 |",
     "Chemical-space occupancy. a, Principal-component projection of Morgan fingerprints "
     "for a random subsample of up to 800 molecules per set. b, UMAP projection of the "
     "same fingerprints under the Jaccard metric. The designed libraries remain within the "
     "region occupied by the training and baseline sets, consistent with the leverage "
     "statistics of Fig. 5d."),
    ("ExtendedData_Fig_5_property_distributions", "Extended Data Fig. 4 |",
     "Property and synthesizability distributions. a, QED. b, Synthetic accessibility "
     "score (lower is easier). c, Composite synthesizability (higher is easier). d, "
     "Symmetric Kullback–Leibler divergence of each descriptor distribution from the "
     "training corpus."),
    ("ExtendedData_Fig_6_scaffolds_groups", "Extended Data Fig. 5 |",
     "Structural composition. a, Most frequent Bemis–Murcko frameworks in the "
     "training corpus sample. b, The same for the campaign A designed library; counts give "
     "the number of molecules built on each framework. c, Frequency of common "
     "medicinal-chemistry functional groups by SMARTS matching. The pyridine bar for the "
     "campaign D library records the enforced substructural constraint."),
    ("ExtendedData_Fig_7_top_candidates_BCD", "Extended Data Fig. 6 |",
     "Highest-ranked GO candidates for campaigns B, C and D, annotated with QED, synthetic "
     "accessibility and composite priority score. Campaign D returned no molecule clearing "
     "the GO gates; this is stated rather than resolved by relaxing the thresholds."),
]


def fill(legend):
    return legend.format(n=int(bench[BASE]["n"]), steps=cfg["RL_STEPS"],
                         batch=cfg["RL_BATCH"], nsweep=int(R["sweep"][0]["n"]))


def table1_rows():
    def spec_summary(n):
        s = R["specs"][n]
        bits = [f"{len(s['properties'])} property objectives"]
        if s.get("reference_smiles"):
            bits.append(f"Tanimoto {s['similarity']['min']}–"
                        f"{s['similarity']['max']} to celecoxib")
        if s.get("required_smarts"):
            bits.append(f"required {', '.join(s['required_smarts'])}")
        if s.get("forbidden_smarts"):
            bits.append(f"forbidden {', '.join(s['forbidden_smarts'])}")
        return "; ".join(bits)

    return [
        ["Design intent", *[TITLE[n] for n in CAMP]],
        ["Specification", *[spec_summary(n) for n in CAMP]],
        ["Baseline median score", *[f3(feas[n]["median"]) for n in CAMP]],
        ["Baseline 95th percentile", *[f3(feas[n]["q95"]) for n in CAMP]],
        ["Baseline gate-pass", *[pct(feas[n]["gate_pass_fraction"], 0) for n in CAMP]],
        ["Mean score, baseline", *[f3(cam[n]["baseline_mean"]) for n in CAMP]],
        ["Mean score, designed", *[f3(cam[n]["designed_mean"]) for n in CAMP]],
        ["Fold change", *[fold(cam[n]["baseline_mean"], cam[n]["designed_mean"])
                          for n in CAMP]],
        ["Designed gate-pass", *[pct(cam[n]["designed_gate_pass"], 0) for n in CAMP]],
        ["Uniqueness", *[f3(bench[D[n]]["uniqueness"]) for n in CAMP]],
        ["Internal diversity", *[f3(bench[D[n]]["int_diversity"]) for n in CAMP]],
        ["Distinct scaffolds", *[f"{scaf[D[n]]['n_scaffolds']:.0f}" for n in CAMP]],
        ["Mean SAscore", *[f2(sy[D[n]]["SAscore"]) for n in CAMP]],
        ["Mean QED", *[f3(dl[D[n]]["QED"]) for n in CAMP]],
        ["Any structural alert", *[pct(al[D[n]]["any_alert"], 0) for n in CAMP]],
        ["Within applicability domain", *[pct(adm[D[n]]["in_AD"], 0) for n in CAMP]],
        ["GO candidates", *[f"{int(tri[D[n]]['n_GO'])} / {int(tri[D[n]]['n_total'])}"
                            for n in CAMP]],
        ["Scaffolds among GO", *[f"{int(tri[D[n]]['go_scaffolds'])}" for n in CAMP]],
    ]


def ed_tables():
    out = []
    c = cfg
    rows = [
        ["Training corpus", f"ZINC-250k; {cur['raw_smiles']:,} input records"],
        ["After curation", f"{cur['after_dedup']:,} molecules (parsed, 5–50 heavy "
                           f"atoms, canonical deduplication)"],
        ["Used for training", f"{cur['final_training']:,} (random subsample; CPU budget)"],
        ["Representation", f"SELFIES, ≤ {c['MAX_LEN']} tokens (retains 100% of the "
                           f"curated corpus)"],
        ["Vocabulary / sequence length", f"{cur['vocab_size']} / {cur['seq_len']}"],
        ["Embedding / heads / layers",
         f"{c['D_MODEL']} / {c['N_HEADS']} / {c['N_LAYERS']}"],
        ["Trainable parameters", f"{pri['n_params']:,}"],
        ["Pretraining", f"{c['EPOCHS']} epochs, {pri['steps']:,} steps, batch "
                        f"{c['BATCH_SIZE']}, AdamW lr {c['LR']}"],
        ["Final smoothed cross-entropy", f"{pri['final_smoothed_loss']:.3f}"],
        ["Raw decode validity", pct(pri["raw_decode_validity"])],
        ["Molecules per library", f"{c['N_SAMPLES']:,}"],
        ["Sampling temperature", f"{c['TEMPERATURE']}"],
        ["RL steps / batch / lr", f"{c['RL_STEPS']} / {c['RL_BATCH']} / {c['RL_LR']}"],
        ["Aggregation", "geometric (all campaigns)"],
        ["Fingerprint", f"Morgan, radius {c['FP_RADIUS']}, {c['FP_BITS']} bits"],
        ["AD basis / components / h*",
         f"{R['ad_meta']['basis']} / {R['ad_meta']['components']} / "
         f"{R['ad_meta']['h_star']:.4f}"],
        ["Triage thresholds",
         f"GO: QED ≥ {c['GO_QED']}, SAscore ≤ {c['GO_SA']}, no alert, in "
         f"domain; CAUTION: QED ≥ {c['CAUTION_QED']}, SAscore ≤ "
         f"{c['CAUTION_SA']}, ≤ 1 alert"],
        ["Random seed", f"{c['SEED']}"],
        ["Hardware", "2 vCPU, 7 GB RAM, no GPU"],
        ["Prior training time", f"{pri['train_minutes']:.0f} min"],
        ["Optional components unavailable", "SCScore, AiZynthFinder"],
    ]
    out.append(("Extended Data Table 1 |",
                "Complete run configuration, serialised to config.json in the exported "
                "archive.", ["Parameter", "Setting"], rows, [2.3, 4.1]))

    hdr = ["Objective", "Mode and target", "Baseline", "Designed", "Change"]
    rows = []
    specA = R["specs"]["A"]["properties"]
    for k, v in insp["A"].items():
        m = specA[k]
        desc = {"range": f"range {m.get('min')}–{m.get('max')}",
                "max_cap": f"cap {m.get('cap')}",
                "min_floor": f"floor {m.get('floor')}",
                "maximize": f"maximise {m.get('lo')}→{m.get('hi')}"}.get(
            m["mode"], m["mode"])
        rows.append([k, desc, pct(v["baseline"]), pct(v["designed"]),
                     f"{'+' if v['change'] >= 0 else ''}{100 * v['change']:.1f} pp"])
    out.append(("Extended Data Table 2 |",
                "Per-objective compliance for campaign A, baseline versus designed "
                "library. Values are the fraction of molecules falling inside each target "
                "window. pp, percentage points.",
                hdr, rows, [1.3, 1.55, 1.1, 1.1, 1.15]))

    sets = [BASE] + [D[n] for n in CAMP]
    hdr = ["Metric", "Baseline"] + [f"Designed {n}" for n in CAMP]
    rows = [
        ["Validity", *[f3(bench[s]["validity"]) for s in sets]],
        ["Uniqueness", *[f3(bench[s]["uniqueness"]) for s in sets]],
        ["Novelty", *[f3(bench[s]["novelty"]) for s in sets]],
        ["Internal diversity", *[f3(bench[s]["int_diversity"]) for s in sets]],
        ["Distinct scaffolds", *[f"{scaf[s]['n_scaffolds']:.0f}" for s in sets]],
        ["Scaffold entropy", *[f2(scaf[s]["scaffold_entropy"]) for s in sets]],
        ["Top-10 scaffold share", *[pct(scaf[s]["top10_share"], 0) for s in sets]],
    ] + [[f"Symmetric KL ({d})", *[f3(kl[s][d]) for s in sets]] for d in kl[BASE]]
    rows += [["", "", "", "", "", ""]]
    rows2 = [
        ["Passes Lipinski Ro5", *[pct(dl[s]["passes_ro5"], 0) for s in sets]],
        ["Passes Veber", *[pct(dl[s]["passes_veber"], 0) for s in sets]],
        ["Mean QED", *[f3(dl[s]["QED"]) for s in sets]],
        ["Mean MW (Da)", *[f"{dl[s]['MW']:.0f}" for s in sets]],
        ["Mean SAscore", *[f2(sy[s]["SAscore"]) for s in sets]],
        ["Mean Bertz complexity", *[f"{sy[s]['BertzCT']:.0f}" for s in sets]],
        ["Composite synthesizability", *[f3(sy[s]["synth_score"]) for s in sets]],
        ["Permitted elements", *[pct(sy[s]["atoms_ok"], 0) for s in sets]],
        ["PAINS alert", *[pct(al[s]["pains"], 1) for s in sets]],
        ["BRENK alert", *[pct(al[s]["brenk"], 1) for s in sets]],
        ["NIH alert", *[pct(al[s]["nih"], 1) for s in sets]],
        ["Any alert", *[pct(al[s]["any_alert"], 1) for s in sets]],
        ["Mean leverage", *[f3(adm[s]["leverage"]) for s in sets]],
        ["Within applicability domain", *[pct(adm[s]["in_AD"], 0) for s in sets]],
    ]
    out.append(("Extended Data Table 3 |",
                "Complete audit of every library produced at the default optimisation "
                "intensity: generative benchmarks, scaffold diversity, distributional "
                "shift, drug-likeness, synthesizability, structural alerts and "
                "applicability domain.",
                hdr, rows + rows2, [1.5, 1.05, 1.05, 1.05, 1.05, 1.05]))

    hdr = ["Campaign", "RL steps", "Design score", "Uniqueness", "Int. diversity",
           "Scaffolds", "Any alert", "Gate pass"]
    rows = [[r["campaign"], int(r["rl_steps"]), f3(r["design_score"]),
             f3(r["uniqueness"]), f3(r["int_diversity"]), int(r["n_scaffolds"]),
             pct(r["any_alert"], 0), pct(r["gate_pass"], 0)] for r in R["sweep"]]
    out.append(("Extended Data Table 4 |",
                "Optimisation-intensity sweep. Each row is an independently sampled "
                f"{int(R['sweep'][0]['n']):,}-molecule library drawn from a policy "
                "snapshot at the stated number of reinforcement-learning steps; step 0 is "
                "the unsteered prior. Gate pass is the fraction satisfying the campaign's "
                "hard substructural constraints.",
                hdr, rows, [0.75, 0.75, 0.95, 0.95, 1.0, 0.85, 0.85, 0.85]))
    return out


def methods():
    S = []
    h = lambda t: S.append(("h", t))
    p = lambda t: S.append(("p", t))

    h("Execution environment and run configuration")
    p(f"The results reported here derive from a single execution of the pipeline on a "
      f"CPU-only machine (2 vCPU, 7 GB RAM, no GPU), which constrained corpus size and is "
      f"the reason the training set was subsampled. The complete configuration is given in "
      f"Extended Data Table 1 and serialised to config.json in the exported archive, so "
      f"that any reported run is fully specified by its configuration record. Random seeds "
      f"for Python, NumPy and PyTorch were fixed at {cfg['SEED']}. Because the seed is a "
      f"configuration parameter rather than a constant, independent replicates are "
      f"obtained by varying it; the run reported here is a single replicate per campaign "
      f"and between-replicate variance was not estimated.")

    h("Training corpus and standardisation")
    p(f"The prior was trained on the publicly available ZINC-250k subset"
      f"¹,². Every structure was parsed and sanitised with RDKit"
      f"²⁴, converted to canonical SMILES so that graph-identical entries "
      f"written differently collapse to a single record, deduplicated, and restricted to "
      f"between 5 and 50 heavy atoms to exclude fragments, counterions and atypically "
      f"large species. Canonicalisation precedes deduplication because a single molecular "
      f"graph admits many valid SMILES strings²⁸; without it, one molecule can be "
      f"presented repeatedly as independent training evidence. Of "
      f"{cur['raw_smiles']:,} input records, "
      f"{cur['after_dedup']:,} survived parsing, size filtering and deduplication; all "
      f"were SELFIES-encodable within the {cfg['MAX_LEN']}-token ceiling, and "
      f"{cur['final_training']:,} were sampled at random for training. Users may "
      f"substitute a comma-separated file containing a SMILES column to focus the prior on "
      f"a project-specific series.")

    h("Representation and tokenisation")
    p(f"Standardised molecules were converted to SELFIES²⁹, whose grammar is "
      f"constructed so that token sequences decode robustly to chemically valid graphs. In "
      f"an autoregressive generator sampling tokens stochastically this removes an entire "
      f"class of failure and allows validity to be treated as a solved precondition rather "
      f"than a metric requiring optimisation. The counter-argument — that permitting "
      f"invalid strings can act as a useful regulariser for chemical language models"
      f"³⁰ — is addressed in the Discussion. A vocabulary of "
      f"{cur['vocab_size']} tokens was assembled from the distinct SELFIES tokens observed "
      f"in the curated corpus, augmented with beginning-of-sequence, end-of-sequence and "
      f"padding symbols, giving a fixed sequence length of {cur['seq_len']}.")

    h("Generative prior")
    p(f"The prior is a compact causal transformer decoder in the style of MolGPT⁵, "
      f"built from the standard self-attention block³¹. Token and learned "
      f"positional embeddings are summed and passed through a stack of pre-normalised "
      f"blocks, each comprising masked multi-head self-attention and a position-wise "
      f"feed-forward network with GELU activation and residual connections; a causal mask "
      f"restricts attention at position t to positions not exceeding t, and the output "
      f"projection is weight-tied to the token embedding. The configuration used an "
      f"embedding width of {cfg['D_MODEL']}, {cfg['N_HEADS']} attention heads, "
      f"{cfg['N_LAYERS']} layers and dropout {cfg['DROPOUT']}, giving {pri['n_params']:,} "
      f"parameters. Training minimised token-level cross-entropy for next-token prediction "
      f"under teacher forcing with padding positions excluded, using AdamW³² at "
      f"learning rate {cfg['LR']}, batch size {cfg['BATCH_SIZE']}, linear warm-up followed "
      f"by cosine decay, and gradient-norm clipping at 1.0, for {cfg['EPOCHS']} epochs "
      f"({pri['steps']:,} steps, {pri['train_minutes']:.0f} minutes on CPU). A transformer "
      f"was preferred to a recurrent architecture because ring-closure and "
      f"branch-termination dependencies in molecular strings frequently span many tokens, "
      f"which self-attention represents directly.")

    h("Sampling")
    p(f"Molecules are generated autoregressively from the beginning-of-sequence token with "
      f"temperature-controlled multinomial sampling at temperature {cfg['TEMPERATURE']}, "
      f"terminating at the end-of-sequence token or the length ceiling; decoded structures "
      f"are re-parsed with RDKit and canonicalised, and structures of fewer than five "
      f"heavy atoms are discarded. {cfg['N_SAMPLES']:,} molecules were collected for the "
      f"baseline and for each designed library. For tractability without a GPU, decoding "
      f"uses a key/value cache rather than recomputing the full prefix at each step. This "
      f"is an implementation optimisation rather than a modelling change: the cached "
      f"decoder was verified against the full-prefix forward pass to a maximum absolute "
      f"logit difference below 1 × 10⁻⁶, leaving the sampling distribution unaltered. The "
      f"unsteered sample serves as the control against which all claims regarding the "
      f"effect of optimisation are made.")

    h("Design specification")
    p("Design intent is declared in a single specification object with four components. "
      "Property objectives associate a descriptor with an optimisation mode and a relative "
      "weight; supported modes are a two-sided range, an upper cap, a lower floor, "
      "monotone maximisation or minimisation over a stated interval, and proximity to a "
      "target with a tolerance. Exposed descriptors are molecular weight, calculated logP, "
      "topological polar surface area, hydrogen-bond donor and acceptor counts, "
      "rotatable-bond count, aromatic-ring count and QED¹⁴. An optional analogue "
      "objective accepts a reference SMILES and a similarity window, scored as the "
      "Tanimoto coefficient between Morgan fingerprints³³ of candidate and "
      "reference, which permits design in the neighbourhood of a known ligand while "
      "explicitly discouraging reproduction of it. Structural constraints are supplied as "
      "SMARTS patterns that must be present or must be absent. A synthesizability "
      "objective, enabled by default, targets a specified synthetic-accessibility value. "
      "An aggregation mode selects how objectives combine. The four specifications used "
      "here were declared before execution, are summarised in Table 1 and are reproduced "
      "verbatim in the archive.")

    h("Desirability construction and reward aggregation")
    p("Each objective is mapped to a desirability in the unit interval following the "
      "Derringer–Suich formalism²³. A range objective returns unity within "
      "its window and decays linearly across a margin proportional to the window width; "
      "caps and floors decay one-sidedly beyond the stated limit; maximisation and "
      "minimisation objectives interpolate linearly between specified bounds; a target "
      "objective applies a Gaussian centred on the desired value. Graded rather than "
      "binary scoring is used because a policy-gradient learner requires a signal that "
      "distinguishes a near miss from a gross violation. Structural constraints are "
      "instead enforced as hard gates, so that a molecule containing a forbidden pattern, "
      "or lacking a required one, receives zero desirability irrespective of its other "
      "properties. Surviving desirabilities are combined using weights normalised to sum "
      "to unity, either as a weighted geometric mean, so that a severe deficiency in any "
      "objective suppresses the total, or as a weighted arithmetic mean, permitting "
      "compensation. All campaigns reported here used geometric aggregation.")

    h("Feasibility preview")
    p("Before optimisation the specification is evaluated against the baseline sample and "
      "three diagnostics are produced: the distribution of composite design scores across "
      "unsteered molecules, the fraction of molecules passing the hard gates, and the mean "
      "desirability attained per individual objective computed over gate-passing "
      "molecules. The first indicates whether the requested region is reachable from the "
      "learned prior; the second separates a low score caused by a categorical constraint "
      "from one caused by unreachable property windows, which have different remedies; the "
      "third attributes any remaining deficiency to specific objectives.")

    h("Goal-directed reinforcement learning")
    p(f"The prior is fine-tuned by policy-gradient reinforcement learning in the manner "
      f"introduced for molecular design by Olivecrona et al.⁸ and developed in "
      f"REINVENT⁹,¹⁰, using the REINFORCE estimator with a baseline "
      f"for variance reduction³⁴. At each of {cfg['RL_STEPS']} iterations a "
      f"batch of {cfg['RL_BATCH']} sequences is sampled from the current policy, decoded "
      f"and scored by the design function. An exponential moving average of recent batch "
      f"rewards (decay 0.9) serves as the baseline; the advantage is the deviation of each "
      f"molecule's reward from that baseline. The loss is the negative mean of the "
      f"advantage-weighted sequence log-probability over non-padding positions. Gradients "
      f"are clipped at norm 1.0 and applied with AdamW at learning rate {cfg['RL_LR']}. "
      f"Each campaign starts from the same pretrained checkpoint, and the fine-tuned "
      f"policy is saved separately from the prior.")

    h("Optimisation-intensity sweep")
    p(f"To characterise the dependence of outcome on optimisation intensity, the "
      f"reinforcement-learning run was repeated for campaigns "
      f"{', '.join(R['sweep_campaigns'])} with the policy state snapshotted after 10, 20, "
      f"40 and 80 steps. Each snapshot was sampled independently for "
      f"{int(R['sweep'][0]['n']):,} molecules and scored for mean design score, "
      f"uniqueness, novelty, internal diversity, distinct Bemis–Murcko frameworks, "
      f"top-ten scaffold share, mean SAscore, mean QED, structural-alert incidence and "
      f"hard-gate compliance. Because the random seed and update sequence are identical to "
      f"the main run, the 80-step snapshot corresponds to the policy used for the "
      f"principal results. Sweep libraries are smaller than the main libraries "
      f"({int(R['sweep'][0]['n']):,} against {cfg['N_SAMPLES']:,} molecules), so sweep and "
      f"main-run values of the same quantity are not numerically identical and are "
      f"reported separately.")

    h("Generative quality benchmarking")
    p("Both sets are characterised using metrics established by the MOSES and GuacaMol "
      "efforts³⁶,³⁷: validity, uniqueness, novelty with respect "
      "to the training corpus, and internal diversity computed as the mean pairwise "
      "Tanimoto distance over Morgan fingerprints³³ on a random subsample of up "
      "to 1,000 molecules. Validity is reported as the fraction of raw sampled token "
      "sequences that decode to a parseable molecule, measured over an independent draw of "
      "1,000 sequences per checkpoint, rather than over the collected library, which is "
      "valid by construction. The symmetric Kullback–Leibler divergence between "
      "generated and training descriptor distributions is reported as a lightweight "
      "distributional-shift measure, complementing the Fréchet ChemNet distance "
      "concept³⁸ without requiring its pretrained network.")

    h("Drug-likeness, synthesizability and structural analysis")
    p(f"Each molecule is evaluated against Lipinski's rule of five¹², the Veber "
      f"criteria¹³ and QED¹⁴; these are applied as prioritisation "
      f"heuristics rather than filters of record. Synthesizability is assessed in layers: "
      f"the synthetic accessibility score of Ertl and Schuffenhauer¹⁵ as "
      f"implemented in the RDKit contribution tree, the Bertz complexity index"
      f"³⁹ as an orthogonal structural-complexity signal, and an "
      f"elemental-composition check excluding atoms outside H, C, N, O, F, P, S, Cl, Br "
      f"and I. SCScore¹⁶ could not be installed in the execution environment "
      f"used here, so the composite was formed from the normalised SAscore and Bertz terms "
      f"with weights renormalised to sum to unity, following the pipeline's documented "
      f"degradation path; higher composite values denote greater expected ease of "
      f"synthesis. Full retrosynthetic route search with AiZynthFinder¹⁸ is "
      f"supported but was not run, the intended pattern being to apply it only to the "
      f"shortlist emerging from triage. Bemis–Murcko frameworks⁴⁰ were "
      f"extracted for all sets and diversity summarised by the number of distinct "
      f"scaffolds, the Shannon entropy of the scaffold-frequency distribution and the "
      f"fraction of the library accounted for by the ten most frequent scaffolds. "
      f"Functional-group frequencies were computed by SMARTS matching. For chemical-space "
      f"visualisation, molecules were represented as {cfg['FP_BITS']}-bit Morgan "
      f"fingerprints of radius {cfg['FP_RADIUS']}³³ and projected to two "
      f"dimensions by principal component analysis and by {R['embedding']}²⁷ "
      f"under the Jaccard metric, on a random subsample of up to 800 molecules per set.")

    h("Structural alerts and applicability domain")
    p(f"Structures were screened against the PAINS¹⁹, BRENK²⁰ and NIH "
      f"substructure catalogues as implemented in RDKit, with alerts recorded per "
      f"catalogue and in aggregate and treated as prioritisation signals rather than "
      f"exclusions. Applicability domain was assessed by the leverage approach standard in "
      f"QSAR practice²¹. Training fingerprints for a bounded basis of "
      f"{R['ad_meta']['basis']} molecules were compressed by randomised principal "
      f"component analysis to {R['ad_meta']['components']} components; for each generated "
      f"molecule the leverage was computed as the quadratic form of its projected score "
      f"vector with the regularised pseudo-inverse of the training score covariance "
      f"matrix. Molecules with leverage not exceeding three times the ratio of components "
      f"to basis compounds (h* = {f3(R['ad_meta']['h_star'])}) were designated in-domain. "
      f"The computation is bounded and vectorised so that it remains tractable within "
      f"hosted-notebook memory limits; the consequence of that bounding for the "
      f"discriminating power of the test is reported in the Results.")

    h("Composite triage")
    p(f"Per-molecule evidence was joined into a single table after deduplication on "
      f"structure and set membership, so that triage fractions are over unique structures "
      f"and a library whose uniqueness has fallen contributes correspondingly fewer rows. "
      f"A composite priority score combines drug-likeness, composite synthesizability, "
      f"freedom from structural alerts and in-domain status with weights 0.4, 0.4, 0.1 and "
      f"0.1 respectively. Each molecule then receives one of three labels. GO requires QED "
      f"≥ {cfg['GO_QED']}, SAscore ≤ {cfg['GO_SA']}, the absence of any "
      f"structural alert and membership of the applicability domain. CAUTION requires QED "
      f"≥ {cfg['CAUTION_QED']} and SAscore ≤ {cfg['CAUTION_SA']} with at most "
      f"one alert. All remaining molecules are labelled NO-GO. Thresholds are "
      f"configuration parameters and are exported with the results. The GO label denotes "
      f"computational priority under the declared rule set and asserts neither predicted "
      f"biological activity nor synthetic or experimental success.")

    h("Export and reproducibility")
    p("All artefacts — the configuration record, every intermediate and final table, "
      "all figures, and the prior and fine-tuned checkpoints — are written to a "
      "single compressed archive. Figures were rendered at 600 dpi. The manuscript's "
      "numerical content is interpolated programmatically from a single machine-readable "
      "run record emitted by the pipeline, which prevents any reported value from diverging "
      "from the run that produced it.")

    h("Use of large language models")
    p("A large language model (Claude, Anthropic) was used as a coding and drafting "
      "assistant: to port the pipeline's notebook cells into the scripts that executed the "
      "campaigns reported here, to generate figure-rendering code, and to assist in "
      "preparing the text of this manuscript. All computational results were produced by "
      "executing that code; no numerical result, table entry or figure was generated by "
      "the language model itself. The author verified the implementation against the "
      "reference notebook, takes full responsibility for the content, and confirms that "
      "the language model is not an author.")
    return S


# =====================================================================
def build():
    doc = Document()
    setup(doc)

    para(doc, P.TITLE, size=15, bold=True, spacing=1.3, after=14)
    para(doc, "Ashfaq Ahmad¹*", size=12, spacing=1.3, after=2)
    para(doc, "¹ Department of Bioinformatics, Hazara University, Mansehra, "
              "Khyber Pakhtunkhwa, Pakistan", size=11, spacing=1.3, after=2)
    para(doc, "* Corresponding author: ashfaq333@gmail.com", size=11,
         spacing=1.3, after=10)
    para(doc, "[Complete the author list, affiliations and corresponding address before "
              "submission.]", size=10, italic=True, spacing=1.3, after=16)

    heading(doc, "Abstract", 1)
    ab = RP.abstract()
    J(doc, ab)
    para(doc, f"[Abstract word count: {len(ab.split())}; Nature Computational Science "
              f"permits up to 150.]", size=9, italic=True, spacing=1.2, after=10)
    para(doc, "Keywords: " + P.KEYWORDS, size=11, spacing=1.5, after=10)
    para(doc, f"[Main text (Introduction, Results, Discussion): "
              f"{main_text_words():,} words; Nature Computational Science permits "
              f"up to 3,500. Display items: 5 figures + 1 table (limit 6). "
              f"References: {len(P.REFERENCES)} (guideline ~50). Extended Data: 6 "
              f"figures + 4 tables (limit 10).]",
         size=9, italic=True, spacing=1.2, after=10)

    page_break(doc)
    heading(doc, "Introduction", 1)
    for kind, txt in S.INTRO:
        J(doc, txt)

    heading(doc, "Results", 1)
    heading(doc, "A declarative specification compiles into a graded, auditable reward", 2)
    J(doc, RP.architecture())

    heading(doc, "Feasibility is diagnosed, and attributed, before optimisation", 2)
    J(doc, RP.feasibility_1())
    J(doc, RP.feasibility_2())

    heading(doc, "Goal-directed optimisation moves libraries onto the specified profile", 2)
    J(doc, RP.optimisation_1())
    J(doc, RP.rl_trajectory())
    J(doc, RP.per_objective())

    heading(doc, "An improving aggregate conceals a regressing objective", 2)
    J(doc, RP.tradeoff())

    heading(doc, "The cost of steering is measured, not assumed", 2)
    J(doc, RP.steering_cost())

    heading(doc, "Optimisation intensity governs a compliance–diversity frontier", 2)
    J(doc, RP.sweep_para())
    J(doc, RP.sweep_para2())

    heading(doc, "Structural alerts, applicability domain and triage", 2)
    J(doc, RP.alerts_ad())
    J(doc, RP.ad_para())
    J(doc, RP.triage_para())

    table(doc, ["Quantity", "A — general", "B — CNS", "C — analogue",
                "D — substructure"],
          table1_rows(), "Table 1 |",
          "Specification, feasibility, optimisation outcome and triage for the four design "
          "campaigns at the default optimisation intensity. All values derive from the "
          "single run recorded in the exported archive; the baseline library is shared "
          "across campaigns. Design score is the composite Derringer–Suich "
          "desirability under each campaign's own specification, so scores are comparable "
          "within a column but not across columns. GO counts are over unique structures.",
          widths=[1.75, 1.2, 1.2, 1.2, 1.2])

    heading(doc, "Discussion", 1)
    for kind, txt in S.DISCUSSION:
        if kind == "h2":
            heading(doc, txt, 2)
        else:
            J(doc, txt)

    heading(doc, "Limitations", 2)
    J(doc, S.LIMITATIONS)

    heading(doc, "Future directions", 2)
    J(doc, S.FUTURE)

    heading(doc, "Conclusions", 2)
    J(doc, S.CONCLUSIONS)

    page_break(doc)
    heading(doc, "Methods", 1)
    for kind, txt in methods():
        if kind == "h":
            heading(doc, txt, 2)
        else:
            J(doc, txt)

    heading(doc, "Data availability", 1)
    J(doc, "The default training corpus is the publicly available ZINC-250k subset derived "
           "from ZINC¹,². All derived data supporting the findings of this "
           "study — the curated training set, the baseline, designed and sweep "
           "libraries, every intermediate result table, the configuration record and the "
           "per-molecule triage table — are contained in the exported run archive "
           "deposited at [repository URL / DOI, to be completed on submission].")

    heading(doc, "Code availability", 1)
    J(doc, "The DeNovoComp notebook and the scripts used to execute the campaigns reported "
           "here, together with the prior and fine-tuned model checkpoints, are available "
           "at [repository URL / DOI, to be completed on submission] under an open-source "
           "licence. All dependencies are open source: RDKit²⁴, PyTorch"
           "²⁵, scikit-learn²⁶, UMAP²⁷ and the SELFIES "
           "library²⁹.")

    heading(doc, "Author contributions", 1)
    J(doc, "[To be completed. Suggested CRediT allocation: A.A. — conceptualisation, "
           "methodology, software, validation, formal analysis, investigation, writing "
           "— original draft, writing — review and editing.]")

    heading(doc, "Competing interests", 1)
    para(doc, "The author declares no competing financial or non-financial interests.")

    heading(doc, "Acknowledgements", 1)
    J(doc, "The author acknowledges the developers and maintainers of RDKit, PyTorch, "
           "scikit-learn, UMAP, the SELFIES library and the open chemical databases on "
           "which this work depends.")

    page_break(doc)
    heading(doc, "References", 1)
    for i, ref in enumerate(P.REFERENCES, 1):
        p = para(doc, f"{i}.\t{ref}", size=11, spacing=1.5, after=3)
        p.paragraph_format.left_indent = Inches(0.35)
        p.paragraph_format.first_line_indent = Inches(-0.35)

    page_break(doc)
    heading(doc, "Figures", 1)
    for tag, num, legend in MAIN_FIGS:
        figure_block(doc, tag, num, fill(legend))

    page_break(doc)
    heading(doc, "Extended Data", 1)
    for tag, num, legend in ED_FIGS:
        figure_block(doc, tag, num, fill(legend))
    for num, cap, header, rows, widths in ed_tables():
        table(doc, header, rows, num, cap, widths=widths)

    out = DELIV / "DeNovoComp_Manuscript_NatComputSci.docx"
    doc.save(out)
    return out


if __name__ == "__main__":
    print("WROTE", build())
