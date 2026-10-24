"""DeNovoComp stage 4: generative benchmarks, drug-likeness, synthesizability,
scaffolds, functional groups, chemical space, alerts, applicability domain, triage.

Port of notebook Parts 7-13. Baseline audited once; each campaign's designed
library audited against it.
"""
import json, random, time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from rdkit import Chem, DataStructs
from rdkit.Chem import Descriptors, Crippen, Lipinski, QED, rdMolDescriptors, FilterCatalog
from rdkit.Chem.Scaffolds import MurckoScaffold
from sklearn.decomposition import PCA

import dnc_core as C
from campaigns import SPECS

OUT, CFG = C.OUT, C.CFG
SEED = CFG["SEED"]
random.seed(SEED); np.random.seed(SEED)

train_smiles = pd.read_csv(OUT / "tables" / "training_set.csv")["smiles"].tolist()
train_set = set(train_smiles)
sample_train = pd.read_csv(OUT / "tables" / "training_sample.csv")["smiles"].tolist()
train_desc = pd.read_csv(OUT / "tables" / "training_descriptors.csv")

baseline = pd.read_csv(OUT / "tables" / "baseline_generated.csv")["smiles"].tolist()
base_valid = [s for s in baseline if Chem.MolFromSmiles(s) is not None]

CAMPAIGNS = [s["name"] for s in SPECS]
designed = {n: pd.read_csv(OUT / "tables" / f"designed_generated_{n}.csv")["smiles"].tolist()
            for n in CAMPAIGNS}
designed_valid = {n: [s for s in v if Chem.MolFromSmiles(s) is not None]
                  for n, v in designed.items()}


# ===================================================== generative metrics
def uniqueness(valid): return len(set(valid)) / max(1, len(valid))
def novelty(valid, ref): return sum(1 for s in valid if s not in ref) / max(1, len(valid))


def internal_diversity(valid, n_samples=1000):
    if len(valid) < 2:
        return 0.0
    pool = random.Random(SEED).sample(valid, min(n_samples, len(valid)))
    fps = [f for f in (C.morgan_fp(s) for s in pool) if f is not None]
    dists = []
    for i in range(len(fps)):
        sims = DataStructs.BulkTanimotoSimilarity(fps[i], fps[i + 1:])
        dists.extend([1.0 - s for s in sims])
    return float(np.mean(dists))


def raw_validity(ckpt, n=1000, seed_off=7):
    C.set_seed(SEED + seed_off)
    m = C.build_model(); m.load_state_dict(torch.load(OUT / "models" / ckpt))
    raw = C.sample_cached(m, n, CFG["TEMPERATURE"]).cpu().numpy()
    return float(sum(1 for r in raw if C.ids_to_smiles(r) is not None) / n)


bench_rows = [dict(set="baseline", n=len(baseline), validity=raw_validity("pretrained.pt"),
                   uniqueness=uniqueness(base_valid), novelty=novelty(base_valid, train_set),
                   int_diversity=internal_diversity(base_valid))]
for n in CAMPAIGNS:
    v = designed_valid[n]
    bench_rows.append(dict(set=f"designed_{n}", n=len(designed[n]),
                           validity=raw_validity(f"designed_{n}.pt", seed_off=7),
                           uniqueness=uniqueness(v), novelty=novelty(v, train_set),
                           int_diversity=internal_diversity(v)))
bench_df = pd.DataFrame(bench_rows)
bench_df.to_csv(OUT / "tables" / "generative_benchmarks.csv", index=False)
print(bench_df.round(4).to_string(index=False), flush=True)


# ===================================================== descriptors + KL
def compute_descriptors(smiles_list):
    rows = []
    for s in smiles_list:
        m = Chem.MolFromSmiles(s)
        if m is None:
            continue
        rows.append(dict(smiles=s, MW=Descriptors.MolWt(m), LogP=Crippen.MolLogP(m),
                         TPSA=Descriptors.TPSA(m), HBD=Lipinski.NumHDonors(m),
                         HBA=Lipinski.NumHAcceptors(m),
                         RotB=Lipinski.NumRotatableBonds(m),
                         Rings=rdMolDescriptors.CalcNumRings(m),
                         HAtoms=m.GetNumHeavyAtoms(), QED=QED.qed(m)))
    return pd.DataFrame(rows)


base_desc = compute_descriptors(base_valid)
des_desc = {n: compute_descriptors(designed_valid[n]) for n in CAMPAIGNS}
base_desc.to_csv(OUT / "tables" / "baseline_descriptors.csv", index=False)
for n in CAMPAIGNS:
    des_desc[n].to_csv(OUT / "tables" / f"designed_descriptors_{n}.csv", index=False)


def kl_descriptors(gen, train, cols=("MW", "LogP", "TPSA", "QED"), bins=40):
    kls = {}
    for c in cols:
        lo = min(train[c].min(), gen[c].min()); hi = max(train[c].max(), gen[c].max())
        edges = np.linspace(lo, hi, bins + 1)
        p, _ = np.histogram(train[c], bins=edges, density=True)
        q, _ = np.histogram(gen[c], bins=edges, density=True)
        p = p + 1e-8; q = q + 1e-8; p /= p.sum(); q /= q.sum()
        kls[c] = float(0.5 * (np.sum(p * np.log(p / q)) + np.sum(q * np.log(q / p))))
    return kls


kl = {"baseline": kl_descriptors(base_desc, train_desc)}
for n in CAMPAIGNS:
    kl[f"designed_{n}"] = kl_descriptors(des_desc[n], train_desc)
kl_df = pd.DataFrame(kl)
kl_df.to_csv(OUT / "tables" / "kl_divergence.csv")
print(kl_df.round(4), flush=True)


# ===================================================== drug-likeness
def drug_like_flags(smiles, label):
    rows = []
    for s in smiles:
        m = Chem.MolFromSmiles(s)
        if m is None:
            continue
        mw = Descriptors.MolWt(m); logp = Crippen.MolLogP(m)
        hbd = Lipinski.NumHDonors(m); hba = Lipinski.NumHAcceptors(m)
        tpsa = Descriptors.TPSA(m); rotb = Lipinski.NumRotatableBonds(m)
        qed = QED.qed(m)
        viol = int(mw > 500) + int(logp > 5) + int(hbd > 5) + int(hba > 10)
        rows.append(dict(smiles=s, set=label, MW=mw, LogP=logp, HBD=hbd, HBA=hba,
                         TPSA=tpsa, RotB=rotb, QED=qed, ro5_violations=viol,
                         passes_ro5=viol <= 1,
                         passes_veber=(tpsa <= 140 and rotb <= 10)))
    return pd.DataFrame(rows)


all_flags = pd.concat([drug_like_flags(base_valid, "baseline")] +
                      [drug_like_flags(designed_valid[n], f"designed_{n}")
                       for n in CAMPAIGNS], ignore_index=True)
all_flags.to_csv(OUT / "tables" / "druglike_flags.csv", index=False)
print(all_flags.groupby("set")[["passes_ro5", "passes_veber", "QED"]].mean().round(4),
      flush=True)


# ===================================================== synthesizability
ALLOWED_ATOMS = {"H", "C", "N", "O", "F", "P", "S", "Cl", "Br", "I"}


def sa_normalized(sa): return max(0.0, min(1.0, (10.0 - sa) / 9.0))


def _minmax_norm(series, invert=False, lo_q=0.05, hi_q=0.95):
    vals = pd.to_numeric(series, errors="coerce")
    lo, hi = np.nanquantile(vals, lo_q), np.nanquantile(vals, hi_q)
    if not np.isfinite(lo) or not np.isfinite(hi) or (hi - lo) < 1e-9:
        return pd.Series(np.full(len(vals), 0.5), index=series.index)
    out = ((vals - lo) / (hi - lo)).clip(0, 1)
    return (1.0 - out if invert else out).fillna(0.5)


def synth_batch(smiles, label):
    rows = []
    for s in smiles:
        m = Chem.MolFromSmiles(s)
        if m is None:
            continue
        sa = C.sa_score(m)
        rows.append(dict(smiles=s, set=label, SAscore=sa, SA_norm=sa_normalized(sa),
                         BertzCT=C.bertz_score(m),
                         atoms_ok=all(a.GetSymbol() in ALLOWED_ATOMS
                                      for a in m.GetAtoms())))
    return pd.DataFrame(rows)


synth_all = pd.concat([synth_batch(base_valid, "baseline")] +
                      [synth_batch(designed_valid[n], f"designed_{n}")
                       for n in CAMPAIGNS], ignore_index=True)
synth_all["Bertz_norm"] = _minmax_norm(synth_all["BertzCT"], invert=True)
# SCScore unavailable in this environment -> weights renormalised over SA + Bertz
w = np.array([0.5, 0.3]); w = w / w.sum()
synth_all["synth_score"] = np.clip(
    np.vstack([synth_all["SA_norm"].fillna(0.5).values,
               synth_all["Bertz_norm"].fillna(0.5).values]).T @ w, 0, 1)
synth_all.to_csv(OUT / "tables" / "synth_composite.csv", index=False)
print(synth_all.groupby("set")[["SAscore", "BertzCT", "atoms_ok", "synth_score"]]
      .mean().round(4), flush=True)


# ===================================================== scaffolds
def get_scaffold(smi):
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return None
    try:
        sc = MurckoScaffold.GetScaffoldForMol(m)
        return Chem.MolToSmiles(sc, canonical=True) if sc else None
    except Exception:
        return None


def scaffold_stats(smiles, name):
    scs = [x for x in (get_scaffold(s) for s in smiles) if x]
    counts = Counter(scs); total = sum(counts.values())
    probs = np.array([c / total for c in counts.values()])
    return dict(set=name, n_valid=len(scs), n_scaffolds=len(counts),
                scaffold_entropy=float(-(probs * np.log(probs + 1e-12)).sum()),
                top10_share=sum(c for _, c in counts.most_common(10)) / total), counts


scaf_rows, scaf_counts = [], {}
for label, sm in [("training", sample_train), ("baseline", base_valid)] + \
                 [(f"designed_{n}", designed_valid[n]) for n in CAMPAIGNS]:
    st, cnt = scaffold_stats(sm, label)
    scaf_rows.append(st); scaf_counts[label] = cnt
scaf_df = pd.DataFrame(scaf_rows)
scaf_df.to_csv(OUT / "tables" / "scaffold_stats.csv", index=False)
json.dump({k: v.most_common(12) for k, v in scaf_counts.items()},
          open(OUT / "tables" / "top_scaffolds.json", "w"), indent=2)
print(scaf_df.round(4).to_string(index=False), flush=True)


# ============================================== functional groups
FGROUPS = {
    "carboxyl": "C(=O)[OH]", "amide": "C(=O)N", "ester": "C(=O)O[C;!$(C=O)]",
    "amine_1": "[NX3;H2]", "amine_2": "[NX3;H1]", "aromatic_N": "n", "aromatic_O": "o",
    "aromatic_S": "s", "halogen": "[F,Cl,Br,I]", "sulfonamide": "S(=O)(=O)N",
    "nitrile": "C#N", "aldehyde": "[CX3H1](=O)", "ketone": "[CX3](=O)[#6]",
    "ether": "[OD2]([#6])[#6]", "hydroxyl": "[OX2H]", "phenyl": "c1ccccc1",
    "pyridine": "n1ccccc1", "trifluoromethyl": "C(F)(F)F",
}
FPATTS = {k: Chem.MolFromSmarts(v) for k, v in FGROUPS.items()}


def fg_freq(smiles):
    counts = {k: 0 for k in FGROUPS}; n_ok = 0
    for s in smiles:
        m = Chem.MolFromSmiles(s)
        if m is None:
            continue
        n_ok += 1
        for k, pat in FPATTS.items():
            if m.HasSubstructMatch(pat):
                counts[k] += 1
    return {k: v / max(1, n_ok) for k, v in counts.items()}


freq_df = pd.DataFrame({"training": fg_freq(sample_train),
                        "baseline": fg_freq(base_valid),
                        **{f"designed_{n}": fg_freq(designed_valid[n]) for n in CAMPAIGNS}})
freq_df.to_csv(OUT / "tables" / "functional_group_freq.csv")
print(freq_df.round(3), flush=True)


# ============================================== chemical space
def fp_matrix(smiles_list, n_max=800):
    if len(smiles_list) > n_max:
        smiles_list = random.Random(SEED).sample(smiles_list, n_max)
    rows = [a for a in (C.morgan_bits(s) for s in smiles_list) if a is not None]
    return np.array(rows, dtype=np.int8)


X_parts, lbls = [], []
for label, sm in [("training", sample_train), ("baseline", base_valid)] + \
                 [(f"designed_{n}", designed_valid[n]) for n in CAMPAIGNS]:
    X = fp_matrix(sm); X_parts.append(X); lbls += [label] * len(X)
X_all = np.vstack(X_parts)
print(f"Fingerprint matrix: {X_all.shape}", flush=True)

pca_xy = PCA(n_components=2, random_state=SEED).fit_transform(X_all.astype(np.float32))
try:
    import umap
    emb_xy = umap.UMAP(n_components=2, n_neighbors=15, min_dist=0.1,
                       random_state=SEED, metric="jaccard").fit_transform(X_all)
    emb_name = "UMAP"
except Exception as e:
    print(f"UMAP unavailable ({e}) -> t-SNE", flush=True)
    from sklearn.manifold import TSNE
    emb_xy = TSNE(n_components=2, random_state=SEED, perplexity=30,
                  metric="jaccard", init="random").fit_transform(X_all.astype(np.float32))
    emb_name = "t-SNE"
pd.DataFrame({"pca1": pca_xy[:, 0], "pca2": pca_xy[:, 1],
              "emb1": emb_xy[:, 0], "emb2": emb_xy[:, 1], "set": lbls}) \
    .to_csv(OUT / "tables" / "chemical_space.csv", index=False)
(OUT / "tables" / "embedding_method.json").write_text(json.dumps({"method": emb_name}))


# ============================================== structural alerts
params = FilterCatalog.FilterCatalogParams()
for cat in (FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS,
            FilterCatalog.FilterCatalogParams.FilterCatalogs.BRENK,
            FilterCatalog.FilterCatalogParams.FilterCatalogs.NIH):
    params.AddCatalog(cat)
alert_catalog = FilterCatalog.FilterCatalog(params)


def alert_flags(smi):
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return dict(pains=False, brenk=False, nih=False, any_alert=False)
    tags = [e.GetProp("FilterSet") for e in alert_catalog.GetMatches(m)]
    return dict(pains=any("PAINS" in t for t in tags),
                brenk=any("Brenk" in t for t in tags),
                nih=any("NIH" in t for t in tags), any_alert=len(tags) > 0)


alerts_all = pd.concat(
    [pd.DataFrame([dict(smiles=s, set=label, **alert_flags(s)) for s in sm])
     for label, sm in [("baseline", base_valid)] +
     [(f"designed_{n}", designed_valid[n]) for n in CAMPAIGNS]], ignore_index=True)
alerts_all.to_csv(OUT / "tables" / "structural_alerts.csv", index=False)
print(alerts_all.groupby("set")[["pains", "brenk", "nih", "any_alert"]].mean().round(4),
      flush=True)


# ============================================== applicability domain
AD_BASIS_MAX = CFG["AD_BASIS_MAX"]
basis_smiles = (sample_train if len(sample_train) <= AD_BASIS_MAX
                else random.Random(SEED).sample(sample_train, AD_BASIS_MAX))


def _fp_mat_keep(smiles):
    mat, kept = [], []
    for s in smiles:
        a = C.morgan_bits(s)
        if a is not None:
            mat.append(a); kept.append(s)
    X = (np.asarray(mat, dtype=np.float32) if mat
         else np.zeros((0, CFG["FP_BITS"]), dtype=np.float32))
    return X, kept


X_basis, _ = _fp_mat_keep(basis_smiles)
k = int(min(CFG["AD_COMPONENTS"], max(1, X_basis.shape[0] - 1), X_basis.shape[1] - 1))
ad_pca = PCA(n_components=k, svd_solver="randomized", random_state=SEED)
Z_tr = ad_pca.fit_transform(X_basis).astype(np.float32)
del X_basis
ZtZ = Z_tr.T @ Z_tr
ZtZ_inv = np.linalg.pinv(ZtZ + 1e-6 * np.eye(ZtZ.shape[0], dtype=np.float32))
p, n_basis = Z_tr.shape[1], Z_tr.shape[0]
h_star = 3.0 * p / n_basis
print(f"AD basis {n_basis} mols, {p} PCs, h*={h_star:.4f}", flush=True)


def leverage_and_ad(smiles, label):
    X, kept = _fp_mat_keep(smiles)
    Z = ad_pca.transform(X).astype(np.float32)
    h = np.einsum("ij,jk,ik->i", Z, ZtZ_inv, Z)
    return pd.DataFrame({"smiles": kept, "set": label, "leverage": h.astype(float),
                         "in_AD": h <= h_star})


ad_all = pd.concat([leverage_and_ad(base_valid, "baseline")] +
                   [leverage_and_ad(designed_valid[n], f"designed_{n}")
                    for n in CAMPAIGNS], ignore_index=True)
ad_all.to_csv(OUT / "tables" / "applicability_domain.csv", index=False)
(OUT / "tables" / "ad_meta.json").write_text(json.dumps(
    dict(basis=n_basis, components=p, h_star=float(h_star))))
print(ad_all.groupby("set")[["leverage", "in_AD"]].mean().round(4), flush=True)


# ============================================== triage
def _dedup(df): return df.drop_duplicates(subset=["smiles", "set"],
                                          keep="first").reset_index(drop=True)


f = _dedup(all_flags[["smiles", "set", "QED", "passes_ro5", "passes_veber",
                      "MW", "LogP", "TPSA"]])
s_ = _dedup(synth_all[["smiles", "set", "SAscore", "synth_score"]])
a = _dedup(alerts_all[["smiles", "set", "pains", "brenk", "nih", "any_alert"]])
d = _dedup(ad_all[["smiles", "set", "leverage", "in_AD"]])
master = (f.merge(s_, on=["smiles", "set"]).merge(a, on=["smiles", "set"])
          .merge(d, on=["smiles", "set"]))
master["alert_count"] = master[["pains", "brenk", "nih"]].sum(axis=1)
master["composite"] = (0.4 * master["QED"] + 0.4 * master["synth_score"]
                       + 0.1 * (1 - master["alert_count"] / 3)
                       + 0.1 * master["in_AD"].astype(int))


def triage(r):
    if (r["QED"] >= CFG["GO_QED"] and r["SAscore"] <= CFG["GO_SA"]
            and not r["any_alert"] and r["in_AD"]):
        return "GO"
    if (r["QED"] >= CFG["CAUTION_QED"] and r["SAscore"] <= CFG["CAUTION_SA"]
            and r["alert_count"] <= 1):
        return "CAUTION"
    return "NO-GO"


master["triage"] = master.apply(triage, axis=1)
master = master.sort_values("composite", ascending=False).reset_index(drop=True)
master.to_csv(OUT / "tables" / "master_triage.csv", index=False)
tri = master.groupby(["set", "triage"]).size().unstack(fill_value=0)
print(tri, flush=True)
tri.to_csv(OUT / "tables" / "triage_distribution.csv")

# GO scaffold diversity + shortlist
go_rows = []
for label in ["baseline"] + [f"designed_{n}" for n in CAMPAIGNS]:
    g = master[(master["set"] == label) & (master["triage"] == "GO")]
    scs = {get_scaffold(x) for x in g["smiles"]}
    go_rows.append(dict(set=label, n_GO=len(g),
                        n_CAUTION=int((master["set"] == label).sum() and
                                      ((master["set"] == label) &
                                       (master["triage"] == "CAUTION")).sum()),
                        n_NOGO=int(((master["set"] == label) &
                                    (master["triage"] == "NO-GO")).sum()),
                        n_total=int((master["set"] == label).sum()),
                        go_scaffolds=len({x for x in scs if x})))
pd.DataFrame(go_rows).to_csv(OUT / "tables" / "triage_summary.csv", index=False)
print(pd.DataFrame(go_rows).to_string(index=False), flush=True)

for n in CAMPAIGNS:
    ranked = pd.read_csv(OUT / "tables" / f"designed_ranked_{n}.csv")
    g = master[(master["set"] == f"designed_{n}") & (master["triage"] == "GO")]
    g = g.merge(ranked, on="smiles", how="left")
    g.sort_values("composite", ascending=False).head(20).to_csv(
        OUT / "tables" / f"top_candidates_{n}.csv", index=False)

print("STAGE 4 COMPLETE", flush=True)
