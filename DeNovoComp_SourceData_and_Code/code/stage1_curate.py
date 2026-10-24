"""DeNovoComp stage 1: corpus curation, standardisation, SELFIES conversion, vocabulary.

Faithful port of notebook Cells 2.1-2.3 and 3.1.
"""
import json, random, sys
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, Crippen, Lipinski, QED, rdMolDescriptors
import selfies as sf

RDLogger.DisableLog("rdApp.*")

ROOT = Path("/home/claude/dnc")
OUT = ROOT / "out"
for d in ("tables", "models", "figures", "npz"):
    (OUT / d).mkdir(parents=True, exist_ok=True)

CFG = json.loads((ROOT / "config.json").read_text())
SEED = CFG["SEED"]
random.seed(SEED); np.random.seed(SEED)

# ---------------------------------------------------------------- load
df = pd.read_csv(ROOT / "data" / "zinc250k.csv")
raw_smiles = [s.strip() for s in df["smiles"].astype(str).tolist()]
print(f"Raw SMILES loaded: {len(raw_smiles):,}", flush=True)


# ------------------------------------------------- canonicalise + filter
def _canon(smi):
    try:
        m = Chem.MolFromSmiles(smi)
        if m is None or m.GetNumHeavyAtoms() < 5 or m.GetNumHeavyAtoms() > 50:
            return None
        return Chem.MolToSmiles(m, canonical=True)
    except Exception:
        return None


canon = [_canon(s) for s in raw_smiles]
n_parse_fail = sum(1 for c in canon if c is None)
canon = [s for s in canon if s]
n_before_dedup = len(canon)
canon = list(dict.fromkeys(canon))
print(f"Parsed/size-filtered: {n_before_dedup:,} (dropped {n_parse_fail:,})", flush=True)
print(f"After dedup:          {len(canon):,}", flush=True)

# ------------------------------------------------------------- SELFIES
tok_lens = []
pairs = []
for s in canon:
    try:
        ss = sf.encoder(s)
    except Exception:
        ss = None
    if not ss:
        continue
    L = sf.len_selfies(ss)
    tok_lens.append(L)
    pairs.append((s, ss, L))

tok_lens = np.array(tok_lens)
print(f"SELFIES-encoded:      {len(pairs):,}", flush=True)
print("SELFIES token-length percentiles: "
      + ", ".join(f"p{q}={np.percentile(tok_lens, q):.0f}" for q in (50, 90, 99, 99.9))
      + f", max={tok_lens.max()}", flush=True)

MAX_LEN = CFG["MAX_LEN"]
kept = [(s, ss) for s, ss, L in pairs if L <= MAX_LEN]
print(f"After MAX_LEN<={MAX_LEN}:  {len(kept):,} "
      f"({100*len(kept)/len(pairs):.2f}% of encodable)", flush=True)

train_smiles = [a for a, _ in kept]
train_selfies = [b for _, b in kept]

N_MAX = CFG["N_TRAIN_MAX"]
if len(train_smiles) > N_MAX:
    idx = np.random.RandomState(SEED).choice(len(train_smiles), N_MAX, replace=False)
    train_smiles = [train_smiles[i] for i in idx]
    train_selfies = [train_selfies[i] for i in idx]
print(f"Final training set:   {len(train_smiles):,}", flush=True)

pd.DataFrame({"smiles": train_smiles, "selfies": train_selfies}).to_csv(
    OUT / "tables" / "training_set.csv", index=False)

# ---------------------------------------------------------- vocabulary
BOS, EOS, PAD = "[BOS]", "[EOS]", "[PAD]"
vocab_set = set()
for s in train_selfies:
    vocab_set.update(sf.split_selfies(s))
vocab = [PAD, BOS, EOS] + sorted(vocab_set)
tok2id = {t: i for i, t in enumerate(vocab)}
SEQ_LEN = MAX_LEN + 2
print(f"Vocab size: {len(vocab)}   seq_len: {SEQ_LEN}", flush=True)


def encode(selfies_str):
    toks = [BOS] + list(sf.split_selfies(selfies_str)) + [EOS]
    ids = [tok2id[t] for t in toks]
    ids += [tok2id[PAD]] * (SEQ_LEN - len(ids))
    return ids[:SEQ_LEN]


train_ids = np.array([encode(s) for s in train_selfies], dtype=np.int64)
np.save(OUT / "npz" / "train_ids.npy", train_ids)
with open(OUT / "models" / "vocab.json", "w") as f:
    json.dump({"vocab": vocab, "seq_len": SEQ_LEN}, f, indent=2)
print(f"Encoded tensor: {train_ids.shape}", flush=True)

# ------------------------------------------------- descriptor profile
def compute_descriptors(smiles_list):
    rows = []
    for s in smiles_list:
        m = Chem.MolFromSmiles(s)
        if m is None:
            continue
        rows.append(dict(
            smiles=s,
            MW=Descriptors.MolWt(m), LogP=Crippen.MolLogP(m),
            TPSA=Descriptors.TPSA(m), HBD=Lipinski.NumHDonors(m),
            HBA=Lipinski.NumHAcceptors(m), RotB=Lipinski.NumRotatableBonds(m),
            Rings=rdMolDescriptors.CalcNumRings(m), HAtoms=m.GetNumHeavyAtoms(),
            QED=QED.qed(m)))
    return pd.DataFrame(rows)


sample_train = (train_smiles if len(train_smiles) <= 5000
                else random.Random(SEED).sample(train_smiles, 5000))
train_desc = compute_descriptors(sample_train)
train_desc.to_csv(OUT / "tables" / "training_descriptors.csv", index=False)
pd.Series(sample_train).to_csv(OUT / "tables" / "training_sample.csv",
                               index=False, header=["smiles"])

prov = dict(
    raw_smiles=len(raw_smiles), parse_or_size_dropped=int(n_parse_fail),
    after_canon=int(n_before_dedup), after_dedup=len(canon),
    selfies_encodable=len(pairs), after_maxlen=len(kept),
    final_training=len(train_smiles), vocab_size=len(vocab), seq_len=SEQ_LEN,
    selfies_len_p50=float(np.percentile(tok_lens, 50)),
    selfies_len_p99=float(np.percentile(tok_lens, 99)),
    selfies_len_max=int(tok_lens.max()),
    train_desc_means={c: float(train_desc[c].mean())
                      for c in ("MW", "LogP", "TPSA", "HBD", "HBA", "QED")},
)
(OUT / "tables" / "curation_provenance.json").write_text(json.dumps(prov, indent=2))
print(json.dumps(prov, indent=2), flush=True)
print("STAGE 1 COMPLETE", flush=True)
