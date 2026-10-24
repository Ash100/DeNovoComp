"""Independent verification: recompute headline numbers from the raw generated
libraries and compare against the text of the built manuscript."""
import json, re, zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import QED, FilterCatalog, RDConfig
from rdkit.Chem.Scaffolds import MurckoScaffold
import sys, os
RDLogger.DisableLog("rdApp.*")
sys.path.append(os.path.join(RDConfig.RDContribDir, "SA_Score"))
import sascorer

ROOT = Path("/home/claude/dnc")
T = ROOT / "out" / "tables"
DOCX = ROOT / "deliverables" / "DeNovoComp_Manuscript_NatComputSci.docx"

# ---- pull the manuscript's own text out of the .docx -------------------
with zipfile.ZipFile(DOCX) as z:
    xml = z.read("word/document.xml").decode("utf8")
text = re.sub(r"<[^>]+>", "", xml)
text = re.sub(r"\s+", " ", text)

params = FilterCatalog.FilterCatalogParams()
for cat in (FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS,
            FilterCatalog.FilterCatalogParams.FilterCatalogs.BRENK,
            FilterCatalog.FilterCatalogParams.FilterCatalogs.NIH):
    params.AddCatalog(cat)
AL = FilterCatalog.FilterCatalog(params)

mfp = Chem.rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)


def recompute(path):
    smi = pd.read_csv(path)["smiles"].tolist()
    valid = [s for s in smi if Chem.MolFromSmiles(s) is not None]
    mols = [Chem.MolFromSmiles(s) for s in valid]
    uniq = len(set(valid)) / len(valid)
    sa = float(np.mean([sascorer.calculateScore(m) for m in mols]))
    qed = float(np.mean([QED.qed(m) for m in mols]))
    alert = float(np.mean([len(AL.GetMatches(m)) > 0 for m in mols]))
    scs = set()
    for m in mols:
        try:
            sc = MurckoScaffold.GetScaffoldForMol(m)
            smi_sc = Chem.MolToSmiles(sc) if sc else ""
            if smi_sc:            # acyclic molecules have no Bemis-Murcko framework
                scs.add(smi_sc)
        except Exception:
            pass
    import random
    pool = random.Random(42).sample(valid, min(1000, len(valid)))
    fps = [mfp.GetFingerprint(Chem.MolFromSmiles(s)) for s in pool]
    d = []
    for i in range(len(fps)):
        d.extend([1 - x for x in DataStructs.BulkTanimotoSimilarity(fps[i], fps[i + 1:])])
    return dict(n=len(valid), uniqueness=uniq, SAscore=sa, QED=qed,
                any_alert=alert, n_scaffolds=len(scs),
                int_diversity=float(np.mean(d)))


checks, failures = [], []


def check(label, recomputed, claimed, tol, *, in_text=None):
    ok = abs(recomputed - claimed) <= tol
    text_ok = (in_text is None) or (in_text in text)
    checks.append((label, recomputed, claimed, ok, text_ok, in_text))
    if not ok or not text_ok:
        failures.append(label)


R = json.loads((ROOT / "out" / "run_record.json").read_text())

for camp in ["A", "B", "C", "D"]:
    rc = recompute(T / f"designed_generated_{camp}.csv")
    rec = R["benchmarks"][f"designed_{camp}"]
    check(f"{camp} uniqueness", rc["uniqueness"], rec["uniqueness"], 1e-6)
    check(f"{camp} int_diversity", rc["int_diversity"], rec["int_diversity"], 0.02)
    check(f"{camp} SAscore", rc["SAscore"], R["synth"][f"designed_{camp}"]["SAscore"], 1e-3)
    check(f"{camp} QED", rc["QED"], R["druglike"][f"designed_{camp}"]["QED"], 1e-3)
    check(f"{camp} any_alert", rc["any_alert"],
          R["alerts"][f"designed_{camp}"]["any_alert"], 1e-3)
    check(f"{camp} scaffolds", rc["n_scaffolds"],
          R["scaffold"][f"designed_{camp}"]["n_scaffolds"], 0)

rb = recompute(T / "baseline_generated.csv")
check("baseline uniqueness", rb["uniqueness"], R["benchmarks"]["baseline"]["uniqueness"], 1e-6)
check("baseline SAscore", rb["SAscore"], R["synth"]["baseline"]["SAscore"], 1e-3)
check("baseline alerts", rb["any_alert"], R["alerts"]["baseline"]["any_alert"], 1e-3)
check("baseline scaffolds", rb["n_scaffolds"], R["scaffold"]["baseline"]["n_scaffolds"], 0)

# ---- strings that must literally appear in the manuscript --------------
must = [
    "0.412", "0.638", "0.909", "0.710", "0.621",          # design scores
    "0.103", "0.711", "1469", "804",                       # diversity / scaffolds
    "249,455", "25,000", "1,809,408",                      # corpus / model
    "99.4%", "92.8%", "6.7%",                              # validity / gate
    "244", "71", "50", "12",                               # GO counts
]
for m in must:
    if m not in text:
        failures.append(f"MISSING FROM TEXT: {m}")

print(f"{'check':<24}{'recomputed':>14}{'claimed':>14}  ok")
for label, rec, cl, ok, tok, _ in checks:
    print(f"{label:<24}{rec:>14.4f}{cl:>14.4f}  {'PASS' if ok else 'FAIL'}")
print()
if failures:
    print("FAILURES:")
    for f in failures:
        print("  -", f)
else:
    print(f"ALL {len(checks)} numeric checks PASS; all {len(must)} key strings present "
          f"in the manuscript.")
