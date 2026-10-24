"""DeNovoComp stage 3: feasibility preview, goal-directed RL, designed library,
target validation -- for each of the four declared campaigns.

Port of notebook Cells 6.1-6.7.
"""
import json, sys, time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from rdkit import Chem

import dnc_core as C
from campaigns import SPECS

OUT, CFG = C.OUT, C.CFG

baseline = pd.read_csv(OUT / "tables" / "baseline_generated.csv")["smiles"].tolist()
base_valid = [s for s in baseline if Chem.MolFromSmiles(s) is not None]
print(f"Baseline molecules: {len(base_valid)}", flush=True)

only = sys.argv[1] if len(sys.argv) > 1 else None


def log_prob_of_sequence(model, seq):
    model.train()
    x, y = seq[:, :-1], seq[:, 1:]
    logits = model(x)
    lp = F.log_softmax(logits, dim=-1)
    y_lp = lp.gather(-1, y.unsqueeze(-1)).squeeze(-1)
    mask = (y != C.PAD_ID).float()
    return (y_lp * mask).sum(dim=1)


def profile_df(smiles):
    rows = []
    for s in smiles:
        m = Chem.MolFromSmiles(s)
        if m:
            rows.append(C.mol_property_vector(m))
    return pd.DataFrame(rows)


for spec in SPECS:
    name = spec["name"]
    if only and name != only:
        continue
    t0 = time.time()
    print(f"\n=== CAMPAIGN {name}: {spec['title']} ===", flush=True)
    scorer = C.Scorer(spec)

    # ------------------------------------------------ feasibility preview
    pre_scores, pre_brk = [], []
    for s in base_valid:
        tot, brk = scorer(s, return_breakdown=True)
        pre_scores.append(tot); pre_brk.append(brk)
    pre_scores = np.array(pre_scores)
    gate_pass = float(np.mean([not ("forbidden" in b or "required" in b)
                               for b in pre_brk]))
    obj_keys = scorer.objective_keys()
    obj_means = {k: (float(np.mean([b[k] for b in pre_brk if k in b]))
                     if any(k in b for b in pre_brk) else 0.0) for k in obj_keys}
    feas = dict(campaign=name, title=spec["title"],
                median=float(np.median(pre_scores)),
                mean=float(pre_scores.mean()),
                q95=float(np.quantile(pre_scores, 0.95)),
                maximum=float(pre_scores.max()),
                frac_above_0p5=float(np.mean(pre_scores > 0.5)),
                gate_pass_fraction=gate_pass,
                per_objective_mean_desirability=obj_means)
    print("feasibility:", json.dumps(feas, indent=2), flush=True)
    np.save(OUT / "npz" / f"pre_scores_{name}.npy", pre_scores)
    (OUT / "tables" / f"feasibility_{name}.json").write_text(json.dumps(feas, indent=2))

    # ---------------------------------------------------- goal-directed RL
    C.set_seed(CFG["SEED"])
    model = C.build_model()
    model.load_state_dict(torch.load(OUT / "models" / "pretrained.pt"))
    rl_optim = torch.optim.AdamW(model.parameters(), lr=CFG["RL_LR"], weight_decay=0.0)
    reward_history, best_history = [], []
    ema_baseline, ema_alpha = 0.0, 0.9

    for step in range(CFG["RL_STEPS"]):
        seq = C.sample_cached(model, CFG["RL_BATCH"], temperature=1.0)
        smiles = [C.ids_to_smiles(r) or "" for r in seq.cpu().numpy()]
        rewards = np.array([scorer(s) for s in smiles], dtype=np.float32)
        ema_baseline = ema_alpha * ema_baseline + (1 - ema_alpha) * rewards.mean()
        advantages = torch.from_numpy(rewards - ema_baseline).float()
        logp = log_prob_of_sequence(model, seq)
        loss = -(advantages * logp).mean()
        rl_optim.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        rl_optim.step()
        reward_history.append(float(rewards.mean()))
        best_history.append(float(rewards.max()))
        if (step + 1) % 10 == 0:
            print(f"  RL {step+1}/{CFG['RL_STEPS']} mean={rewards.mean():.4f} "
                  f"max={rewards.max():.4f} ({(time.time()-t0)/60:.1f} min)", flush=True)

    torch.save(model.state_dict(), OUT / "models" / f"designed_{name}.pt")
    np.save(OUT / "npz" / f"rl_mean_{name}.npy", np.array(reward_history))
    np.save(OUT / "npz" / f"rl_best_{name}.npy", np.array(best_history))

    # ------------------------------------------------- designed library
    C.set_seed(CFG["SEED"])
    designed = C.generate_smiles(model, CFG["N_SAMPLES"], CFG["TEMPERATURE"],
                                 log=f"designed-{name}")
    pd.DataFrame({"smiles": designed}).to_csv(
        OUT / "tables" / f"designed_generated_{name}.csv", index=False)
    designed_valid = [s for s in designed if Chem.MolFromSmiles(s) is not None]

    # ------------------------------------------------- target validation
    prof_base, prof_des = profile_df(base_valid), profile_df(designed_valid)
    rows = []
    for prop in [k for k in spec["properties"] if k in prof_des.columns]:
        rows.append(dict(objective=prop,
                         baseline_in_spec=float(np.mean([scorer.in_spec(prop, v)
                                                         for v in prof_base[prop]])),
                         designed_in_spec=float(np.mean([scorer.in_spec(prop, v)
                                                         for v in prof_des[prop]]))))
    inspec = pd.DataFrame(rows)
    inspec["change"] = inspec["designed_in_spec"] - inspec["baseline_in_spec"]
    inspec.to_csv(OUT / "tables" / f"target_inspec_fractions_{name}.csv", index=False)
    print(inspec.round(3).to_string(index=False), flush=True)

    des_scores = np.array([scorer(s) for s in designed_valid])
    base_mean = float(np.mean([scorer(s) for s in base_valid]))

    ranked = pd.DataFrame({"smiles": designed_valid, "design_score": des_scores}) \
        .sort_values("design_score", ascending=False).reset_index(drop=True)
    ranked.to_csv(OUT / "tables" / f"designed_ranked_{name}.csv", index=False)

    # hard-gate verification in the designed set
    des_brk = [scorer(s, return_breakdown=True)[1] for s in designed_valid]
    des_gate = float(np.mean([not ("forbidden" in b or "required" in b) for b in des_brk]))

    summary = dict(
        campaign=name, title=spec["title"],
        baseline_mean=base_mean, designed_mean=float(des_scores.mean()),
        baseline_median=float(np.median(pre_scores)),
        designed_median=float(np.median(des_scores)),
        designed_max=float(des_scores.max()),
        rl_first=reward_history[0], rl_last=reward_history[-1],
        rl_best_overall=float(max(best_history)),
        n_designed=len(designed), n_designed_valid=len(designed_valid),
        baseline_gate_pass=gate_pass, designed_gate_pass=des_gate,
        minutes=float((time.time() - t0) / 60))
    (OUT / "tables" / f"campaign_summary_{name}.json").write_text(
        json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)
    print(f"CAMPAIGN {name} COMPLETE", flush=True)

print("STAGE 3 COMPLETE", flush=True)
