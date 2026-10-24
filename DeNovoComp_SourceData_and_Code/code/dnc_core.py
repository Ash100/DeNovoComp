"""DeNovoComp core: model, sampling, desirability scoring, descriptors.

Faithful port of the notebook's algorithms. The only functional addition is a
key/value cache for autoregressive sampling (`sample_cached`), which is
mathematically identical to the notebook's re-forward-the-whole-prefix loop but
O(T) rather than O(T^2) -- required to make the run tractable without a GPU.
"""
import json, math, os, random, sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import (Descriptors, Crippen, Lipinski, QED, rdMolDescriptors,
                        rdFingerprintGenerator, GraphDescriptors)
import selfies as sf

RDLogger.DisableLog("rdApp.*")

ROOT = Path("/home/claude/dnc")
OUT = ROOT / "out"
CFG = json.loads((ROOT / "config.json").read_text())
DEVICE = torch.device("cpu")
torch.set_num_threads(2)

BOS, EOS, PAD = "[BOS]", "[EOS]", "[PAD]"
_v = json.loads((OUT / "models" / "vocab.json").read_text())
VOCAB = _v["vocab"]
SEQ_LEN = _v["seq_len"]
TOK2ID = {t: i for i, t in enumerate(VOCAB)}
ID2TOK = {i: t for t, i in TOK2ID.items()}
VOCAB_SIZE = len(VOCAB)
PAD_ID, BOS_ID, EOS_ID = TOK2ID[PAD], TOK2ID[BOS], TOK2ID[EOS]


def set_seed(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)


# ============================================================== model
class CausalSelfAttention(nn.Module):
    def __init__(self, d_model, n_heads, dropout):
        super().__init__()
        assert d_model % n_heads == 0
        self.n_heads, self.head_dim = n_heads, d_model // n_heads
        self.qkv = nn.Linear(d_model, d_model * 3)
        self.proj = nn.Linear(d_model, d_model)
        self.drop = nn.Dropout(dropout)

    def _split(self, x):
        B, T, C = x.shape
        qkv = self.qkv(x).reshape(B, T, 3, self.n_heads, self.head_dim).permute(2, 0, 3, 1, 4)
        return qkv[0], qkv[1], qkv[2]

    def forward(self, x, mask):
        B, T, C = x.shape
        q, k, v = self._split(x)
        att = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_dim)
        att = att.masked_fill(mask[None, None, :, :] == 0, float("-inf"))
        att = self.drop(F.softmax(att, dim=-1))
        y = (att @ v).transpose(1, 2).contiguous().view(B, T, C)
        return self.proj(y)

    def step(self, x, cache):
        """x: (B,1,C). cache: dict with 'k','v' of (B,H,t,hd) or None."""
        B, T, C = x.shape
        q, k, v = self._split(x)                       # (B,H,1,hd)
        if cache.get("k") is not None:
            k = torch.cat([cache["k"], k], dim=2)
            v = torch.cat([cache["v"], v], dim=2)
        cache["k"], cache["v"] = k, v
        att = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_dim)
        att = F.softmax(att, dim=-1)
        y = (att @ v).transpose(1, 2).contiguous().view(B, 1, C)
        return self.proj(y)


class TransformerBlock(nn.Module):
    def __init__(self, d_model, n_heads, dropout):
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.ln2 = nn.LayerNorm(d_model)
        self.attn = CausalSelfAttention(d_model, n_heads, dropout)
        self.ff = nn.Sequential(nn.Linear(d_model, 4 * d_model), nn.GELU(),
                                nn.Linear(4 * d_model, d_model), nn.Dropout(dropout))

    def forward(self, x, mask):
        x = x + self.attn(self.ln1(x), mask)
        return x + self.ff(self.ln2(x))

    def step(self, x, cache):
        x = x + self.attn.step(self.ln1(x), cache)
        return x + self.ff(self.ln2(x))


class MolForgeTransformer(nn.Module):
    def __init__(self, vocab_size, d_model, n_heads, n_layers, seq_len, dropout):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab_size, d_model)
        self.pos_emb = nn.Embedding(seq_len, d_model)
        self.drop = nn.Dropout(dropout)
        self.blocks = nn.ModuleList([TransformerBlock(d_model, n_heads, dropout)
                                     for _ in range(n_layers)])
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)
        self.head.weight = self.tok_emb.weight
        self.seq_len = seq_len
        self.register_buffer("mask", torch.tril(torch.ones(seq_len, seq_len)))
        self.apply(self._init)

    @staticmethod
    def _init(m):
        if isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, std=0.02)
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Embedding):
            nn.init.normal_(m.weight, std=0.02)

    def forward(self, x):
        B, T = x.shape
        pos = torch.arange(T, device=x.device)
        h = self.drop(self.tok_emb(x) + self.pos_emb(pos)[None, :, :])
        for blk in self.blocks:
            h = blk(h, self.mask[:T, :T])
        return self.head(self.ln_f(h))

    @torch.no_grad()
    def step(self, tok, pos, caches):
        h = self.tok_emb(tok) + self.pos_emb(torch.tensor([pos], device=tok.device))[None, :, :]
        for blk, c in zip(self.blocks, caches):
            h = blk.step(h, c)
        return self.head(self.ln_f(h))[:, -1, :]


def build_model():
    return MolForgeTransformer(VOCAB_SIZE, CFG["D_MODEL"], CFG["N_HEADS"],
                               CFG["N_LAYERS"], SEQ_LEN, CFG["DROPOUT"]).to(DEVICE)


# ============================================================ sampling
@torch.no_grad()
def sample_cached(model, n, temperature=1.0):
    """Returns LongTensor (n, <=SEQ_LEN) of token ids including BOS."""
    model.eval()
    caches = [dict() for _ in model.blocks]
    tok = torch.full((n, 1), BOS_ID, dtype=torch.long, device=DEVICE)
    seq = [tok]
    finished = torch.zeros(n, dtype=torch.bool, device=DEVICE)
    for t in range(SEQ_LEN - 1):
        logits = model.step(tok, t, caches) / max(1e-6, temperature)
        probs = F.softmax(logits, dim=-1)
        nxt = torch.multinomial(probs, 1)
        nxt = torch.where(finished.unsqueeze(1), torch.full_like(nxt, PAD_ID), nxt)
        seq.append(nxt)
        finished |= nxt.squeeze(-1) == EOS_ID
        if finished.all():
            break
        tok = nxt
    return torch.cat(seq, dim=1)


def decode_ids(ids):
    out = []
    for i in ids:
        t = ID2TOK[int(i)]
        if t == EOS:
            break
        if t in (BOS, PAD):
            continue
        out.append(t)
    return "".join(out)


def ids_to_smiles(ids):
    try:
        smi = sf.decoder(decode_ids(ids))
        if not smi:
            return None
        m = Chem.MolFromSmiles(smi)
        if m is None or m.GetNumHeavyAtoms() < 5:
            return None
        return Chem.MolToSmiles(m, canonical=True)
    except Exception:
        return None


def generate_smiles(model, n_total, temperature=1.0, batch=500, log=None):
    """Collect n_total valid, parseable molecules (duplicates retained)."""
    out, attempts = [], 0
    while len(out) < n_total and attempts < 40:
        got = sample_cached(model, min(batch, max(64, n_total - len(out))), temperature)
        for row in got.cpu().numpy():
            s = ids_to_smiles(row)
            if s:
                out.append(s)
        attempts += 1
        if log:
            print(f"  {log}: {len(out)}/{n_total}", flush=True)
    return out[:n_total]


# ========================================================= descriptors
_mfpgen = rdFingerprintGenerator.GetMorganGenerator(radius=CFG["FP_RADIUS"],
                                                    fpSize=CFG["FP_BITS"])


def morgan_fp(x):
    m = x if isinstance(x, Chem.Mol) else Chem.MolFromSmiles(x)
    return None if m is None else _mfpgen.GetFingerprint(m)


def morgan_bits(x):
    fp = morgan_fp(x)
    if fp is None:
        return None
    arr = np.zeros((CFG["FP_BITS"],), dtype=np.int8)
    DataStructs.ConvertToNumpyArray(fp, arr)
    return arr


def mol_property_vector(m):
    return dict(MW=Descriptors.MolWt(m), LogP=Crippen.MolLogP(m),
                TPSA=Descriptors.TPSA(m), HBD=Lipinski.NumHDonors(m),
                HBA=Lipinski.NumHAcceptors(m), RotB=Lipinski.NumRotatableBonds(m),
                AromaticRings=rdMolDescriptors.CalcNumAromaticRings(m),
                QED=QED.qed(m))


# SAscore from RDKit contrib
try:
    from rdkit.Chem import RDConfig
    _sa_path = os.path.join(RDConfig.RDContribDir, "SA_Score")
    if _sa_path not in sys.path:
        sys.path.append(_sa_path)
    import sascorer
    SA_SOURCE = "rdkit_contrib"

    def sa_score(mol):
        return float(sascorer.calculateScore(mol))
except Exception as _e:                                     # pragma: no cover
    SA_SOURCE = "heuristic_fallback"

    def sa_score(mol):
        n_ha = mol.GetNumHeavyAtoms(); n_r = rdMolDescriptors.CalcNumRings(mol)
        n_st = rdMolDescriptors.CalcNumAtomStereoCenters(mol)
        return float(min(10.0, max(1.0, 1 + 0.05 * n_ha + 0.5 * n_r + 0.8 * n_st)))


def bertz_score(m):
    try:
        return float(GraphDescriptors.BertzCT(m))
    except Exception:
        return float("nan")


# ================================================= desirability scorer
def _d_range(x, lo, hi):
    margin = max(1e-6, 0.30 * (hi - lo))
    if lo <= x <= hi:
        return 1.0
    d = (lo - x) / margin if x < lo else (x - hi) / margin
    return float(max(0.0, 1.0 - d))


def _d_max_cap(x, cap):
    margin = max(1e-6, 0.30 * abs(cap) + 1.0)
    return 1.0 if x <= cap else float(max(0.0, 1.0 - (x - cap) / margin))


def _d_min_floor(x, floor):
    margin = max(1e-6, 0.30 * abs(floor) + 1.0)
    return 1.0 if x >= floor else float(max(0.0, 1.0 - (floor - x) / margin))


def _d_maximize(x, lo, hi):
    if x <= lo:
        return 0.0
    if x >= hi:
        return 1.0
    return float((x - lo) / (hi - lo))


def _d_minimize(x, lo, hi):
    if x <= lo:
        return 1.0
    if x >= hi:
        return 0.0
    return float((hi - x) / (hi - lo))


def _d_target(x, target, tol):
    return float(math.exp(-0.5 * ((x - target) / max(1e-6, tol)) ** 2))


def _desirability(mode, val, cfg):
    if mode == "range":     return _d_range(val, cfg["min"], cfg["max"])
    if mode == "max_cap":   return _d_max_cap(val, cfg["cap"])
    if mode == "min_floor": return _d_min_floor(val, cfg["floor"])
    if mode == "maximize":  return _d_maximize(val, cfg["lo"], cfg["hi"])
    if mode == "minimize":  return _d_minimize(val, cfg["lo"], cfg["hi"])
    if mode == "target":    return _d_target(val, cfg["target"], cfg.get("tol", 1.0))
    return 1.0


class Scorer:
    """Compiles a DESIGN_SPEC into design_score(smiles)."""

    def __init__(self, spec):
        self.spec = spec
        self.req = [Chem.MolFromSmarts(s) for s in spec.get("required_smarts", [])]
        self.frb = [Chem.MolFromSmarts(s) for s in spec.get("forbidden_smarts", [])]
        ref = spec.get("reference_smiles")
        self.ref_fp = morgan_fp(ref) if ref else None

    def objective_keys(self):
        keys = list(self.spec["properties"].keys())
        if self.ref_fp is not None:
            keys.append("similarity")
        if self.spec.get("include_sa", False):
            keys.append("SA")
        return keys

    def __call__(self, smiles, return_breakdown=False):
        m = Chem.MolFromSmiles(smiles) if smiles else None
        if m is None:
            return (0.0, {}) if return_breakdown else 0.0
        for patt in self.frb:
            if patt is not None and m.HasSubstructMatch(patt):
                return (0.0, {"forbidden": 0.0}) if return_breakdown else 0.0
        for patt in self.req:
            if patt is not None and not m.HasSubstructMatch(patt):
                return (0.0, {"required": 0.0}) if return_breakdown else 0.0

        props = mol_property_vector(m)
        ds, ws, brk = [], [], {}
        for name, cfg in self.spec["properties"].items():
            if name not in props:
                continue
            d = _desirability(cfg["mode"], props[name], cfg)
            ds.append(d); ws.append(cfg.get("weight", 1.0)); brk[name] = d
        if self.ref_fp is not None:
            sim = DataStructs.TanimotoSimilarity(self.ref_fp, morgan_fp(m))
            scfg = self.spec["similarity"]
            d = _d_range(sim, scfg["min"], scfg["max"])
            ds.append(d); ws.append(scfg.get("weight", 1.0)); brk["similarity"] = d
        if self.spec.get("include_sa", False):
            d = _d_target(sa_score(m), self.spec["sa_target"], tol=2.0)
            ds.append(d); ws.append(self.spec.get("sa_weight", 0.5)); brk["SA"] = d

        ds = np.clip(np.array(ds, dtype=float), 1e-6, 1.0)
        ws = np.array(ws, dtype=float); ws = ws / ws.sum()
        if self.spec.get("aggregation", "geometric") == "geometric":
            total = float(np.exp(np.sum(ws * np.log(ds))))
        else:
            total = float(np.sum(ws * ds))
        return (total, brk) if return_breakdown else total

    def in_spec(self, prop, val):
        cfg = self.spec["properties"][prop]
        mode = cfg["mode"]
        if mode == "range":     return cfg["min"] <= val <= cfg["max"]
        if mode == "max_cap":   return val <= cfg["cap"]
        if mode == "min_floor": return val >= cfg["floor"]
        if mode == "maximize":  return val >= cfg["lo"]
        if mode == "minimize":  return val <= cfg["hi"]
        if mode == "target":    return abs(val - cfg["target"]) <= cfg.get("tol", 1.0)
        return True
