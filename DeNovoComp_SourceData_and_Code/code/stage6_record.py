"""Assemble a single machine-readable record of every number the manuscript cites.

Writes out/run_record.json. build_manuscript.py reads ONLY this file, so no
value can appear in the manuscript that was not produced by the run.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

import dnc_core as C
from campaigns import SPECS

OUT, CFG = C.OUT, C.CFG
T = OUT / "tables"
CAMP = [s["name"] for s in SPECS]
R = {}

R["config"] = CFG
R["curation"] = json.loads((T / "curation_provenance.json").read_text())
R["prior"] = json.loads((T / "prior_meta.json").read_text())
R["ad_meta"] = json.loads((T / "ad_meta.json").read_text())
R["embedding"] = json.loads((T / "embedding_method.json").read_text())["method"]
R["campaign_titles"] = {s["name"]: s["title"] for s in SPECS}
R["specs"] = {s["name"]: {k: v for k, v in s.items() if k != "name"} for s in SPECS}
R["feasibility"] = {n: json.loads((T / f"feasibility_{n}.json").read_text()) for n in CAMP}
R["campaign"] = {n: json.loads((T / f"campaign_summary_{n}.json").read_text()) for n in CAMP}

bench = pd.read_csv(T / "generative_benchmarks.csv").set_index("set")
R["benchmarks"] = {k: {c: float(v) for c, v in row.items()}
                   for k, row in bench.to_dict("index").items()}
kl = pd.read_csv(T / "kl_divergence.csv", index_col=0)
R["kl"] = {c: {i: float(kl.loc[i, c]) for i in kl.index} for c in kl.columns}

flags = pd.read_csv(T / "druglike_flags.csv")
R["druglike"] = {k: {c: float(v) for c, v in row.items()} for k, row in
                 flags.groupby("set")[["passes_ro5", "passes_veber", "QED", "MW",
                                       "LogP", "TPSA", "ro5_violations"]]
                 .mean().to_dict("index").items()}

synth = pd.read_csv(T / "synth_composite.csv")
R["synth"] = {k: {c: float(v) for c, v in row.items()} for k, row in
              synth.groupby("set")[["SAscore", "BertzCT", "atoms_ok", "synth_score"]]
              .mean().to_dict("index").items()}
R["sa_source"] = C.SA_SOURCE

scaf = pd.read_csv(T / "scaffold_stats.csv").set_index("set")
R["scaffold"] = {k: {c: float(v) for c, v in row.items()}
                 for k, row in scaf.to_dict("index").items()}

alerts = pd.read_csv(T / "structural_alerts.csv")
R["alerts"] = {k: {c: float(v) for c, v in row.items()} for k, row in
               alerts.groupby("set")[["pains", "brenk", "nih", "any_alert"]]
               .mean().to_dict("index").items()}

ad = pd.read_csv(T / "applicability_domain.csv")
R["ad"] = {k: {c: float(v) for c, v in row.items()} for k, row in
           ad.groupby("set")[["leverage", "in_AD"]].mean().to_dict("index").items()}

tri = pd.read_csv(T / "triage_summary.csv").set_index("set")
R["triage"] = {k: {c: (float(v) if not isinstance(v, str) else v)
                   for c, v in row.items()} for k, row in tri.to_dict("index").items()}

R["inspec"] = {}
for n in CAMP:
    d = pd.read_csv(T / f"target_inspec_fractions_{n}.csv")
    R["inspec"][n] = {r["objective"]: dict(baseline=float(r["baseline_in_spec"]),
                                           designed=float(r["designed_in_spec"]),
                                           change=float(r["change"]))
                      for _, r in d.iterrows()}

fg = pd.read_csv(T / "functional_group_freq.csv", index_col=0)
R["functional_groups"] = {c: {i: float(fg.loc[i, c]) for i in fg.index}
                          for c in fg.columns}

sw = pd.read_csv(T / "intensity_sweep.csv")
R["sweep"] = sw.round(5).to_dict("records")
R["sweep_campaigns"] = sorted(sw["campaign"].unique().tolist())
R["sweep_steps"] = sorted(sw["rl_steps"].unique().tolist())

R["top_candidates"] = {}
for n in CAMP:
    try:
        t = pd.read_csv(T / f"top_candidates_{n}.csv").head(5)
        R["top_candidates"][n] = t[["smiles", "QED", "SAscore", "synth_score",
                                    "composite", "leverage"]].round(4).to_dict("records")
    except Exception:
        R["top_candidates"][n] = []

(OUT / "run_record.json").write_text(json.dumps(R, indent=2, default=float))
print(json.dumps(R, indent=2, default=float)[:4000])
print("\nSTAGE 6 COMPLETE", flush=True)
