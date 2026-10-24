"""DeNovoComp stage 2: train the generative prior, sample the unsteered baseline.

Port of notebook Cells 4.1, 4.2, 5.1.
"""
import json, math, time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

import dnc_core as C

OUT = C.OUT
CFG = C.CFG
C.set_seed(CFG["SEED"])

train_ids = np.load(OUT / "npz" / "train_ids.npy")
print(f"Training tensor: {train_ids.shape}", flush=True)

model = C.build_model()
n_params = sum(p.numel() for p in model.parameters())
print(f"Model parameters: {n_params:,}", flush=True)


class SelfiesDataset(Dataset):
    def __init__(self, arr): self.arr = torch.from_numpy(arr).long()
    def __len__(self): return len(self.arr)
    def __getitem__(self, i): return self.arr[i]


dl = DataLoader(SelfiesDataset(train_ids), batch_size=CFG["BATCH_SIZE"],
                shuffle=True, num_workers=0, drop_last=True)

optim = torch.optim.AdamW(model.parameters(), lr=CFG["LR"], weight_decay=0.01)
total_steps = len(dl) * CFG["EPOCHS"]
warmup = min(500, total_steps // 20)
print(f"Steps/epoch {len(dl)}  total {total_steps}  warmup {warmup}", flush=True)


def lr_at(step):
    if step < warmup:
        return step / max(1, warmup)
    progress = (step - warmup) / max(1, total_steps - warmup)
    return 0.5 * (1 + math.cos(math.pi * progress))


losses, epoch_loss, step = [], [], 0
running = 0.0
model.train()
t0 = time.time()
for epoch in range(CFG["EPOCHS"]):
    ep_losses = []
    for batch in dl:
        x, y = batch[:, :-1], batch[:, 1:]
        logits = model(x)
        loss = F.cross_entropy(logits.reshape(-1, C.VOCAB_SIZE), y.reshape(-1),
                               ignore_index=C.PAD_ID)
        for g in optim.param_groups:
            g["lr"] = CFG["LR"] * lr_at(step)
        optim.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optim.step(); step += 1
        running = 0.9 * running + 0.1 * loss.item() if running else loss.item()
        losses.append(running); ep_losses.append(loss.item())
        if step % 25 == 0:
            el = time.time() - t0
            print(f"  step {step}/{total_steps} loss={running:.4f} "
                  f"elapsed={el/60:.1f}min eta={el/step*(total_steps-step)/60:.1f}min",
                  flush=True)
    epoch_loss.append(float(np.mean(ep_losses)))
    print(f"epoch {epoch+1}/{CFG['EPOCHS']} mean_loss={epoch_loss[-1]:.4f}", flush=True)

train_minutes = (time.time() - t0) / 60
torch.save(model.state_dict(), OUT / "models" / "pretrained.pt")
np.save(OUT / "npz" / "prior_loss.npy", np.array(losses))
print(f"Prior trained in {train_minutes:.1f} min", flush=True)

# ---------------------------------------------------------- baseline
C.set_seed(CFG["SEED"])
t1 = time.time()
baseline = C.generate_smiles(model, CFG["N_SAMPLES"], CFG["TEMPERATURE"],
                             log="baseline")
pd.DataFrame({"smiles": baseline}).to_csv(OUT / "tables" / "baseline_generated.csv",
                                          index=False)
print(f"Baseline: {len(baseline)} molecules in {(time.time()-t1)/60:.1f} min", flush=True)

# raw sampling validity (fraction of raw draws that decoded to a usable mol)
C.set_seed(CFG["SEED"] + 1)
raw = C.sample_cached(model, 1000, CFG["TEMPERATURE"]).cpu().numpy()
ok = sum(1 for r in raw if C.ids_to_smiles(r) is not None)
raw_validity = ok / len(raw)
print(f"Raw decode validity over 1000 draws: {raw_validity:.4f}", flush=True)

meta = dict(n_params=int(n_params), epochs=CFG["EPOCHS"], steps=int(step),
            steps_per_epoch=len(dl), train_minutes=float(train_minutes),
            epoch_mean_loss=epoch_loss, final_smoothed_loss=float(losses[-1]),
            initial_smoothed_loss=float(losses[0]),
            raw_decode_validity=float(raw_validity),
            sa_source=C.SA_SOURCE)
(OUT / "tables" / "prior_meta.json").write_text(json.dumps(meta, indent=2))
print(json.dumps(meta, indent=2), flush=True)
print("STAGE 2 COMPLETE", flush=True)
