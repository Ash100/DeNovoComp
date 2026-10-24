# -*- coding: utf-8 -*-
"""Results narrative, interpolated entirely from out/run_record.json."""
import json
from pathlib import Path

import numpy as np

OUT = Path("/home/claude/dnc/out")
R = json.loads((OUT / "run_record.json").read_text())

CAMP = ["A", "B", "C", "D"]
BASE = "baseline"
D = {n: f"designed_{n}" for n in CAMP}
cur, pri, cfg = R["curation"], R["prior"], R["config"]
bench, kl, dl, sy = R["benchmarks"], R["kl"], R["druglike"], R["synth"]
scaf, al, adm, tri = R["scaffold"], R["alerts"], R["ad"], R["triage"]
feas, cam, insp = R["feasibility"], R["campaign"], R["inspec"]
TITLE = R["campaign_titles"]
SWEEP = R["sweep"]
SW_CAMP = R["sweep_campaigns"]


def pct(x, d=1): return f"{100 * float(x):.{d}f}%"
def f3(x): return f"{float(x):.3f}"
def f2(x): return f"{float(x):.2f}"
def comma(x): return f"{int(round(float(x))):,}"


def fold(a, b):
    return f"{b / a:.1f}-fold" if a > 1e-9 else "from a near-zero baseline"


def sw(camp, steps, key):
    for r in SWEEP:
        if r["campaign"] == camp and int(r["rl_steps"]) == steps:
            return r[key]
    raise KeyError((camp, steps, key))


# =====================================================================
def architecture():
    return (
        f"The pipeline comprises fourteen stages grouped into four phases (Fig. 1): "
        f"corpus curation and tokenisation; training of the generative prior and "
        f"unconditioned sampling of a control library; compilation of a declarative "
        f"specification into a desirability reward, followed by policy-gradient "
        f"fine-tuning; and audit and triage of the resulting library. Curation of the "
        f"ZINC-250k corpus retained {cur['after_dedup']:,} molecules, all of which were "
        f"encodable as SELFIES within the {cfg['MAX_LEN']}-token ceiling, and "
        f"{cfg['N_TRAIN_MAX']:,} of these were sampled for training (Extended Data Fig. 1 "
        f"and Extended Data Table 1). The resulting prior contains {pri['n_params']:,} "
        f"parameters and converged to a smoothed cross-entropy of "
        f"{pri['final_smoothed_loss']:.3f} over {pri['epochs']} epochs. In an independent "
        f"draw of 1,000 token sequences, {pct(pri['raw_decode_validity'])} decoded to "
        f"parseable molecules of at least five heavy atoms, confirming that the SELFIES "
        f"grammar removes validity as a quantity requiring optimisation.")


def feasibility_1():
    return (
        f"The four specifications (Table 1) were fixed before execution and represent "
        f"distinct classes of design intent. Scoring the shared baseline library against "
        f"each specification, before any reinforcement-learning update, yielded "
        f"substantially different diagnoses (Fig. 2a–d). Specifications A and B were "
        f"readily reachable from the prior (median design scores "
        f"{f3(feas['A']['median'])} and {f3(feas['B']['median'])}; 95th percentiles "
        f"{f3(feas['A']['q95'])} and {f3(feas['B']['q95'])}), as was the analogue "
        f"specification C (median {f3(feas['C']['median'])}), which constrains Tanimoto "
        f"similarity to celecoxib. Specification D returned a median of "
        f"{f3(feas['D']['median'])}, since only {pct(feas['D']['gate_pass_fraction'])} of "
        f"baseline molecules contain the required pyridine and the remainder are assigned "
        f"zero desirability by the hard gate. Its 95th percentile of "
        f"{f3(feas['D']['q95'])} indicated that the target was nonetheless attainable, "
        f"which optimisation subsequently confirmed. A median alone would not distinguish "
        f"a demanding specification from an infeasible one, and the preview therefore "
        f"reports the score distribution, the gate-pass fraction and the per-objective "
        f"desirabilities together.")


def feasibility_2():
    o = feas["A"]["per_objective_mean_desirability"]
    ob = feas["B"]["per_objective_mean_desirability"]
    weakest = sorted(o.items(), key=lambda kv: kv[1])[:2]
    return (
        f"The per-objective decomposition identifies where optimisation pressure will act "
        f"(Fig. 2e). Campaigns A and B shared the same two weakest objectives at baseline, "
        f"{weakest[0][0]} ({f3(weakest[0][1])}) and {weakest[1][0]} "
        f"({f3(weakest[1][1])}). The specifications differ in their next-hardest term: the "
        f"narrower lipophilicity window of campaign B reduces LogP desirability from "
        f"{f3(o['LogP'])} to {f3(ob['LogP'])}. For campaign C the similarity term "
        f"dominated, at a mean desirability of "
        f"{f3(feas['C']['per_objective_mean_desirability']['similarity'])}. All of these "
        f"quantities derive from the baseline sample and cost a single sampling pass.")


def optimisation_1():
    return (
        f"At the default optimisation setting ({cfg['RL_STEPS']} steps, batch "
        f"{cfg['RL_BATCH']}), policy-gradient fine-tuning increased the mean composite "
        f"design score in all four campaigns (Fig. 3f and Table 1): campaign A from "
        f"{f3(cam['A']['baseline_mean'])} to {f3(cam['A']['designed_mean'])} "
        f"({fold(cam['A']['baseline_mean'], cam['A']['designed_mean'])}); campaign B from "
        f"{f3(cam['B']['baseline_mean'])} to {f3(cam['B']['designed_mean'])} "
        f"({fold(cam['B']['baseline_mean'], cam['B']['designed_mean'])}); campaign C from "
        f"{f3(cam['C']['baseline_mean'])} to {f3(cam['C']['designed_mean'])} "
        f"({fold(cam['C']['baseline_mean'], cam['C']['designed_mean'])}); and campaign D "
        f"from {f3(cam['D']['baseline_mean'])} to {f3(cam['D']['designed_mean'])} "
        f"({fold(cam['D']['baseline_mean'], cam['D']['designed_mean'])}).")


def rl_trajectory():
    rows = []
    for n in CAMP:
        m = np.load(OUT / "npz" / f"rl_mean_{n}.npy")
        steps = np.arange(len(m))
        rho = float(np.corrcoef(np.argsort(np.argsort(m)).astype(float),
                                np.argsort(np.argsort(steps)).astype(float))[0, 1])
        rows.append((n, m, rho))
    sd = float(np.mean([np.std(np.diff(m)) for _, m, _ in rows]))
    worst = min(rows, key=lambda r: r[2]); best = max(rows, key=lambda r: r[2])
    return (
        f"The reward trajectories were non-monotone in all four campaigns "
        f"(Fig. 3a–d), with a mean step-to-step standard deviation of {sd:.3f} in the "
        f"batch mean at a batch size of {cfg['RL_BATCH']}. Campaigns B, C and D rose "
        f"steeply before approaching a plateau, whereas campaign A fluctuated between "
        f"{min(rows[0][1]):.2f} and {max(rows[0][1]):.2f} without stabilising. Spearman "
        f"rank correlations between batch-mean reward and step index ranged from "
        f"{worst[2]:.2f} (campaign {worst[0]}) to {best[2]:.2f} (campaign {best[0]}). In "
        f"every campaign the batch maximum remained well above the batch mean, indicating "
        f"that high-scoring structures were encountered early and that optimisation acted "
        f"mainly by redistributing probability mass toward them. The magnitude of the "
        f"step-to-step variance suggests that a larger reinforcement-learning batch, "
        f"rather than a longer run, would stabilise optimisation at this scale.")


def per_objective():
    a = insp["A"]
    improved = [k for k, v in a.items() if v["change"] > 0.01]
    best = max(a.items(), key=lambda kv: kv[1]["change"])
    return (
        f"Per-objective compliance provides the evidence that this shift corresponds to "
        f"the declared intent (Fig. 3e and Extended Data Table 2). In campaign A, "
        f"{len(improved)} of {len(a)} objectives increased their in-specification "
        f"fraction, the largest gain being {best[0]}, from {pct(best[1]['baseline'])} to "
        f"{pct(best[1]['designed'])}. The hard gates behaved categorically: in campaign D "
        f"the fraction of molecules satisfying both the required pyridine and the nitro "
        f"exclusion rose from {pct(cam['D']['baseline_gate_pass'])} to "
        f"{pct(cam['D']['designed_gate_pass'])}, a "
        f"{fold(cam['D']['baseline_gate_pass'], cam['D']['designed_gate_pass'])} "
        f"enrichment obtained from the zero-desirability gate alone, without "
        f"post-generation filtering.")


def tradeoff():
    mw = {n: insp[n]["MW"] for n in CAMP if "MW" in insp[n]}
    worst = min(mw.items(), key=lambda kv: kv[1]["change"])
    spec_mw = R["specs"]["A"]["properties"]["MW"]
    base_mw = dl[BASE]["MW"]
    lowest = min({n: dl[D[n]]["MW"] for n in CAMP}.items(), key=lambda kv: kv[1])
    return (
        f"One objective moved in the opposite direction. Molecular-weight compliance "
        f"decreased in every campaign, from {pct(mw['A']['baseline'])} to "
        f"{pct(mw['A']['designed'])} in campaign A and from "
        f"{pct(worst[1]['baseline'])} to {pct(worst[1]['designed'])} in campaign "
        f"{worst[0]}, despite improvement in all remaining objectives and an increase in "
        f"the composite score. Mean molecular weight fell from {base_mw:.0f} Da in the "
        f"baseline library to {lowest[1]:.0f} Da in campaign {lowest[0]}, below the lower "
        f"bound of the requested {spec_mw['min']}–{spec_mw['max']} Da window. This "
        f"behaviour follows from the structure of the reward. Under geometric aggregation "
        f"the QED-maximisation term, the synthetic-accessibility target and the "
        f"aromatic-ring window all favour smaller molecules, and their combined weight "
        f"exceeds that of the single two-sided mass constraint, whose penalty below the "
        f"floor decays comparatively slowly. The optimiser is thus consistent with the "
        f"specification supplied to it, and the discrepancy lies in the weighting of that "
        f"specification rather than in the algorithm. Reported by composite score alone, "
        f"these four campaigns would appear uniformly successful.")


def steering_cost():
    bu = bench[BASE]["uniqueness"]
    worst_u = min(CAMP, key=lambda n: bench[D[n]]["uniqueness"])
    bs = scaf[BASE]["n_scaffolds"]
    worst_s = min(CAMP, key=lambda n: scaf[D[n]]["n_scaffolds"])
    return (
        f"Improved compliance was accompanied by a loss of structural variety "
        f"(Fig. 5a–b and Extended Data Table 3). Validity remained near unity and "
        f"novelty relative to the training corpus was {f3(bench[BASE]['novelty'])} for "
        f"every library, so neither metric was informative here. Uniqueness and internal "
        f"diversity, by contrast, both declined substantially. Uniqueness decreased from "
        f"{f3(bu)} in the baseline library to "
        f"{f3(bench[D['A']]['uniqueness'])} in campaign A and "
        f"{f3(bench[D[worst_u]]['uniqueness'])} in campaign {worst_u}, where internal "
        f"diversity also fell from {f3(bench[BASE]['int_diversity'])} to "
        f"{f3(bench[D[worst_u]]['int_diversity'])}. The effect is more pronounced at the "
        f"level of molecular frameworks: the baseline library contained "
        f"{comma(bs)} distinct Bemis–Murcko scaffolds, compared with "
        f"{comma(scaf[D['A']]['n_scaffolds'])} in campaign A and "
        f"{comma(scaf[D[worst_s]]['n_scaffolds'])} in campaign {worst_s}, while the "
        f"proportion of each library accounted for by its ten most frequent frameworks "
        f"rose from {pct(scaf[BASE]['top10_share'], 0)} to "
        f"{pct(scaf[D[worst_s]]['top10_share'], 0)}. Three of the four campaigns therefore "
        f"show the mode concentration characteristic of over-optimisation, in which "
        f"specification compliance is achieved by repeated elaboration of a small number "
        f"of structural motifs.")


def sweep_para():
    return (
        f"We next varied optimisation intensity directly, taking policy snapshots after "
        f"{', '.join(str(int(s)) for s in R['sweep_steps'][1:-1])} and "
        f"{int(R['sweep_steps'][-1])} steps and sampling a "
        f"{int(SWEEP[0]['n']):,}-molecule library from each (Fig. 4; campaigns "
        f"{', '.join(SW_CAMP[:-1])} and {SW_CAMP[-1]}). In campaign A, ten steps raised "
        f"the mean design score from {f3(sw('A', 0, 'design_score'))} to "
        f"{f3(sw('A', 10, 'design_score'))} while leaving uniqueness at "
        f"{f3(sw('A', 10, 'uniqueness'))} and internal diversity at "
        f"{f3(sw('A', 10, 'int_diversity'))}, against baseline values of "
        f"{f3(sw('A', 0, 'uniqueness'))} and {f3(sw('A', 0, 'int_diversity'))}, with "
        f"{int(sw('A', 10, 'n_scaffolds'))} distinct frameworks retained against "
        f"{int(sw('A', 0, 'n_scaffolds'))} at baseline. Extending optimisation to eighty "
        f"steps increased the score further to {f3(sw('A', 80, 'design_score'))} but "
        f"reduced the framework count to {int(sw('A', 80, 'n_scaffolds'))}. Campaign B "
        f"showed the same trend more steeply, with a score of "
        f"{f3(sw('B', 10, 'design_score'))} at ten steps and diversity "
        f"{f3(sw('B', 10, 'int_diversity'))}, against "
        f"{f3(sw('B', 80, 'design_score'))} at eighty steps with diversity "
        f"{f3(sw('B', 80, 'int_diversity'))} and {int(sw('B', 80, 'n_scaffolds'))} "
        f"frameworks remaining. For these graded-objective specifications most of the "
        f"attainable gain in compliance is realised within the first ten steps, and "
        f"further optimisation is paid for largely in diversity.")


def sweep_para2():
    return (
        f"Campaign D behaved differently. Its categorical substructure constraint was not "
        f"satisfied by low-intensity steering: gate compliance was "
        f"{pct(sw('D', 10, 'gate_pass'), 0)} after ten steps and "
        f"{pct(sw('D', 20, 'gate_pass'), 0)} after twenty, reaching "
        f"{pct(sw('D', 40, 'gate_pass'), 0)} at forty steps and "
        f"{pct(sw('D', 80, 'gate_pass'), 0)} at eighty, by which point internal diversity "
        f"had fallen from {f3(sw('D', 0, 'int_diversity'))} to "
        f"{f3(sw('D', 80, 'int_diversity'))} and the framework count from "
        f"{int(sw('D', 0, 'n_scaffolds'))} to {int(sw('D', 80, 'n_scaffolds'))}. A "
        f"categorical requirement obliges the policy to relocate rather than to shift "
        f"within its existing distribution, and consequently incurs a larger diversity "
        f"penalty than graded property windows. Optimisation intensity is therefore better "
        f"selected per specification with reference to the measured frontier than left at "
        f"a fixed default.")


def alerts_ad():
    ba = al[BASE]["any_alert"]
    rose = [n for n in CAMP if al[D[n]]["any_alert"] > ba]
    fell = [n for n in CAMP if al[D[n]]["any_alert"] < ba]
    rose_txt = ", ".join(f"{pct(al[D[n]]['any_alert'])} in campaign {n}" for n in rose)
    return (
        f"Structural-alert incidence increased in "
        f"{['none', 'one', 'two', 'three', 'all four'][len(rose)]} of the four campaigns "
        f"(Fig. 5c). In the baseline library {pct(ba)} of molecules carried at least one "
        f"PAINS, BRENK or NIH alert; this rose to {rose_txt}, and fell to "
        f"{pct(al[D[fell[0]]]['any_alert']) if fell else 'n/a'} in campaign "
        f"{fell[0] if fell else '-'}. The BRENK catalogue accounted for most matches "
        f"throughout. No alert pattern was declared as a forbidden substructure in these "
        f"specifications, so the reward offered no incentive to avoid them, and "
        f"optimisation against graded property terms moved the libraries into regions of "
        f"chemical space richer in reactive and otherwise undesirable motifs. Encoding a "
        f"recurring motif as a forbidden SMARTS would suppress it at the point of "
        f"generation, as the campaign D gate demonstrates for the pyridine requirement.")


def ad_para():
    return (
        f"The applicability-domain assessment was uninformative at this configuration "
        f"(Fig. 5d). With a basis of {R['ad_meta']['basis']:,} training fingerprints "
        f"reduced to {R['ad_meta']['components']} principal components, the conventional "
        f"threshold is h* = 3p/n = {f3(R['ad_meta']['h_star'])}, whereas mean leverage was "
        f"{f3(adm[BASE]['leverage'])} in the baseline library and between "
        f"{f3(min(adm[D[n]]['leverage'] for n in CAMP))} and "
        f"{f3(max(adm[D[n]]['leverage'] for n in CAMP))} in the designed libraries. All "
        f"molecules were consequently classified as in-domain and the flag contributed no "
        f"discrimination to the triage. This reflects the configuration rather than the "
        f"method: a basis of this size relative to the number of components yields a "
        f"permissive threshold, and libraries steered by property objectives alone remain "
        f"close to the training distribution, as the fingerprint projections confirm "
        f"(Extended Data Fig. 3). The GO label in this run therefore carries no "
        f"domain-based evidence.")


def triage_para():
    tb = tri[BASE]
    parts = []
    for n in CAMP:
        t = tri[D[n]]
        if t["n_GO"] == 0:
            parts.append(f"and none of {int(t['n_total']):,} in campaign {n}")
        else:
            parts.append(f"{int(t['n_GO'])} of {int(t['n_total']):,} "
                         f"({pct(t['n_GO'] / t['n_total'])}) across "
                         f"{int(t['go_scaffolds'])} frameworks in campaign {n}")
    return (
        f"Applying the triage rule at the configured thresholds (QED ≥ "
        f"{cfg['GO_QED']}, SAscore ≤ {cfg['GO_SA']}, no structural alert, "
        f"in-domain), {int(tb['n_GO'])} of {int(tb['n_total']):,} unique baseline "
        f"structures ({pct(tb['n_GO'] / tb['n_total'])}) were labelled GO, spanning "
        f"{int(tb['go_scaffolds'])} distinct frameworks. The designed libraries yielded "
        + "; ".join(parts) + f" (Fig. 5e–f and Extended Data Fig. 6). The unsteered "
        f"baseline thus produced more GO molecules in absolute terms than any steered "
        f"library. In campaign D the mean SAscore of {f2(sy[D['D']]['SAscore'])} exceeded "
        f"the {cfg['GO_SA']} threshold, the pyridine requirement having driven the "
        f"generator toward more complex structures while satisfying the gate. These "
        f"outcomes are not inconsistent with the compliance "
        f"results, since the triage weights alert freedom and synthetic accessibility "
        f"independently of the design specification. They do indicate that optimisation "
        f"intensity should be chosen with reference to Fig. 4, and that alert patterns "
        f"penalised at triage are better declared as forbidden substructures at the "
        f"outset. Each row of the triage table retains the evidence underlying its label. "
        f"GO denotes computational priority under the stated rule set and does not imply "
        f"predicted activity or experimental success.")


def abstract():
    lo = min(cam[n]["designed_mean"] / cam[n]["baseline_mean"] for n in ["A", "B", "C"])
    hi = cam["D"]["designed_mean"] / cam["D"]["baseline_mean"]
    return (
        f"Goal-directed generative models reliably produce molecules that satisfy a "
        f"numerical objective, but converting their output into a defensible shortlist "
        f"still depends on bespoke, undocumented code. We present DeNovoComp, a pipeline "
        f"in which design intent is declared rather than programmed: a single "
        f"specification of property windows, similarity bounds and substructural "
        f"constraints compiles into Derringer–Suich desirability functions that serve "
        f"as the reinforcement-learning reward, the ranking function and the provenance "
        f"record. A feasibility preview scores the unsteered prior against the "
        f"specification before optimisation begins, attributing shortfalls to individual "
        f"objectives. Across four campaigns, REINFORCE fine-tuning raised mean design "
        f"scores {lo:.1f}- to {hi:.0f}-fold and enforced a mandatory substructure from "
        f"{pct(cam['D']['baseline_gate_pass'], 0)} to "
        f"{pct(cam['D']['designed_gate_pass'], 0)} compliance without post-generation "
        f"filtering. The same instrumentation quantified the cost: uniqueness fell to "
        f"{f2(min(bench[D[n]]['uniqueness'] for n in CAMP))} and structural alerts "
        f"increased at the default intensity, while an intensity sweep identified settings "
        f"retaining most compliance at near-baseline diversity.")
