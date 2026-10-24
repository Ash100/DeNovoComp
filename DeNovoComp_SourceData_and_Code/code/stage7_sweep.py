"""DeNovoComp stage 7: optimisation-intensity sweep.

Re-runs goal-directed RL for selected campaigns, snapshotting the policy at
several step counts, and samples a library from each snapshot. Produces the
compliance-versus-diversity frontier that identifies a recommended operating
point.
"""
import json, random, time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from rdkit import Chem, DataStructs
from rdkit.Chem import QED, FilterCatalog
from rdkit.Chem.Scaffolds import MurckoScaffold

import dnc_core as C
from campaigns import SPECS

OUT, CFG = C.OUT, C.CFG
SEED = CFG["SEED"]
SNAPSHOTS = [10, 20, 40, 80]
SWEEP_CAMPAIGNS = ["A", "B", "D"]
N_SWEEP = 1000

train_set = set(pd.read_csv(OUT / "tables" / "training_set.csv")["smiles"].tolist())
baseline = pd.read_csv(OUT / "tables" / "baseline_generated.csv")["smiles"].tolist()
base_valid = [s for s in baseline if Chem.MolFromSmiles(s) is not None]

params = FilterCatalog.FilterCatalogParams()
for cat in (FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS,
            FilterCatalog.FilterCatalogParams.FilterCatalogs.BRENK,
            FilterCatalog.FilterCatalogParams.FilterCatalogs.NIH):
    params.AddCatalog(cat)
ALERTS = FilterCatalog.FilterCatalog(params)


def metrics(smiles, scorer, label):
    valid = [s for s in smiles if Chem.MolFromSmiles(s) is not None]
    scores = np.array([scorer(s) for s in valid])
    fps = [C.morgan_fp(s) for s in random.Random(SEED).sample(
        valid, min(500, len(valid)))]
    fps = [f for f in fps if f is not None]
    dists = []
    for i in range(len(fps)):
        dists.extend([1 - x for x in DataStructs.BulkTanimotoSimilarity(fps[i], fps[i+1:])])
    scs = []
    sa, qed, alert = [], [], 0
    gate = 0
    for s in valid:
        m = Chem.MolFromSmiles(s)
        try:
            sc = MurckoScaffold.GetScaffoldForMol(m)
            if sc:
                scs.append(Chem.MolToSmiles(sc, canonical=True))
        except Exception:
            pass
        sa.append(C.sa_score(m)); qed.append(QED.qed(m))
        if len(ALERTS.GetMatches(m)) > 0:
            alert += 1
        _, brk = scorer(s, return_breakdown=True)
        if not ("forbidden" in brk or "required" in brk):
            gate += 1
    counts = Counter(scs); total = max(1, sum(counts.values()))
    return dict(
        label=label, n=len(valid),
        design_score=float(scores.mean()),
        design_median=float(np.median(scores)),
        uniqueness=len(set(valid)) / max(1, len(valid)),
        novelty=sum(1 for s in valid if s not in train_set) / max(1, len(valid)),
        int_diversity=float(np.mean(dists)) if dists else 0.0,
        n_scaffolds=len(counts),
        top10_share=sum(c for _, c in counts.most_common(10)) / total,
        mean_SA=float(np.mean(sa)), mean_QED=float(np.mean(qed)),
        any_alert=alert / max(1, len(valid)),
        gate_pass=gate / max(1, len(valid)),
    )


def log_prob_of_sequence(model, seq):
    model.train()
    x, y = seq[:, :-1], seq[:, 1:]
    lp = F.log_softmax(model(x), dim=-1)
    y_lp = lp.gather(-1, y.unsqueeze(-1)).squeeze(-1)
    mask = (y != C.PAD_ID).float()
    return (y_lp * mask).sum(dim=1)


rows = []
for spec in SPECS:
    n = spec["name"]
    if n not in SWEEP_CAMPAIGNS:
        continue
    scorer = C.Scorer(spec)
    print(f"\n=== SWEEP CAMPAIGN {n} ===", flush=True)

    m0 = metrics(base_valid[:N_SWEEP], scorer, "baseline")
    m0.update(campaign=n, rl_steps=0)
    rows.append(m0)
    print(f"  steps=0 score={m0['design_score']:.3f} uniq={m0['uniqueness']:.3f} "
          f"div={m0['int_diversity']:.3f} scaf={m0['n_scaffolds']}", flush=True)

    # identical RL run to stage 3, with snapshots
    C.set_seed(SEED)
    model = C.build_model()
    model.load_state_dict(torch.load(OUT / "models" / "pretrained.pt"))
    opt = torch.optim.AdamW(model.parameters(), lr=CFG["RL_LR"], weight_decay=0.0)
    ema, alpha = 0.0, 0.9
    snaps = {}
    for step in range(max(SNAPSHOTS)):
        seq = C.sample_cached(model, CFG["RL_BATCH"], temperature=1.0)
        smiles = [C.ids_to_smiles(r) or "" for r in seq.cpu().numpy()]
        rewards = np.array([scorer(s) for s in smiles], dtype=np.float32)
        ema = alpha * ema + (1 - alpha) * rewards.mean()
        adv = torch.from_numpy(rewards - ema).float()
        loss = -(adv * log_prob_of_sequence(model, seq)).mean()
        opt.zero_grad(set_to_none=True); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if (step + 1) in SNAPSHOTS:
            snaps[step + 1] = {k: v.clone() for k, v in model.state_dict().items()}
            print(f"  snapshot at {step+1}", flush=True)

    for s in SNAPSHOTS:
        model.load_state_dict(snaps[s])
        C.set_seed(SEED)
        lib = C.generate_smiles(model, N_SWEEP, CFG["TEMPERATURE"])
        mm = metrics(lib, scorer, f"rl{s}")
        mm.update(campaign=n, rl_steps=s)
        rows.append(mm)
        print(f"  steps={s} score={mm['design_score']:.3f} uniq={mm['uniqueness']:.3f} "
              f"div={mm['int_diversity']:.3f} scaf={mm['n_scaffolds']} "
              f"alert={mm['any_alert']:.3f} gate={mm['gate_pass']:.3f}", flush=True)
        pd.DataFrame({"smiles": lib}).to_csv(
            OUT / "tables" / f"sweep_library_{n}_rl{s}.csv", index=False)

df = pd.DataFrame(rows)
df.to_csv(OUT / "tables" / "intensity_sweep.csv", index=False)
print("\n" + df.round(3).to_string(index=False), flush=True)
print("STAGE 7 COMPLETE", flush=True)
