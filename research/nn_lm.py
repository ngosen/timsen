"""A small LSTM that ranks the next syllable, trained on the CPU, over a table's vocabulary.

usage: python -m research.nn_lm data TABLE.timsen OUT.npy MAX_TOKENS
       python -m research.nn_lm train TABLE.timsen DATA.npy OUT.pt [--hours H] [--emb N] [--hidden N]
       python -m research.nn_lm score TABLE.timsen MODEL.pt TESTFILE... [--k 3]
Words are the table's ids, so the model and the table predict from the same vocabulary; other words
are <unk>. Each run starts with <s>, as in restore, and a line's earlier runs stay in the context.
Needs torch, which CI does not install.
"""

import argparse
import gzip
import itertools
import time

import numpy as np
import torch
from torch import nn

from . import paths, table
from .model import BOS, EOS, UNK
from .text import segments

CORPORA = ["wiki", "subs", "forum-1", "forum-2", "forum-3", "forum-4"]
# Common words get the full output layer; rarer ones share smaller ones, which keeps training fast.
CUTOFFS = [2000, 10000]
SEQ = 64
BATCH = 64
LOG_EVERY = 200


def line_ids(m, line):
    """Ids of a line: <s> before each run, then its words."""
    out = []
    for run in segments(line, tone_style=True):
        out += [BOS, *[m.id.get(w, UNK) for w in run]]
    return out


def build_data(m, out, max_tokens):
    """Lines taken in turn from each corpus, so no single corpus fills the budget."""
    files = [gzip.open(paths.DATA / f"{c}.txt.gz", "rt", encoding="utf-8", errors="replace") for c in CORPORA]
    ids, n = [], 0
    for line in itertools.chain.from_iterable(zip(*files)):
        a = line_ids(m, line)
        ids.append(np.array(a, dtype=np.int32))
        n += len(a)
        if n >= max_tokens:
            break
    data = np.concatenate(ids)
    np.save(out, data)
    print(f"{out}: {len(data):,} tokens, <unk> {np.mean(data == UNK):.2%}")


class LM(nn.Module):
    def __init__(self, vocab, emb, hidden):
        super().__init__()
        self.emb = nn.Embedding(vocab, emb)
        self.rnn = nn.LSTM(emb, hidden, batch_first=True)
        cutoffs = [c for c in CUTOFFS if c < vocab - 1] or [vocab // 2]
        self.out = nn.AdaptiveLogSoftmaxWithLoss(hidden, vocab, cutoffs, div_value=4.0)

    def hidden_states(self, x, state=None):
        h, state = self.rnn(self.emb(x), state)
        return h, state


def batches(data, rng):
    while True:
        starts = rng.integers(0, len(data) - SEQ - 1, BATCH)
        chunk = np.stack([data[s : s + SEQ + 1] for s in starts]).astype(np.int64)
        yield torch.from_numpy(chunk[:, :-1]), torch.from_numpy(chunk[:, 1:])


def train(m, data_path, out, hours, emb, hidden):
    data = np.load(data_path)
    lm = LM(len(m.words), emb, hidden)
    opt = torch.optim.Adam(lm.parameters(), lr=2e-3)
    rng = np.random.default_rng(5)
    start, seen, loss_sum = time.time(), 0, 0.0
    for step, (x, y) in enumerate(batches(data, rng), 1):
        h, _ = lm.hidden_states(x)
        loss = lm.out(h.reshape(-1, h.shape[-1]), y.reshape(-1)).loss
        opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(lm.parameters(), 1.0)
        opt.step()
        seen += x.numel()
        loss_sum += loss.item()
        if step % LOG_EVERY == 0:
            spent = time.time() - start
            print(f"step {step} tokens {seen:,} loss {loss_sum / LOG_EVERY:.3f} {seen / spent:,.0f} tok/s", flush=True)
            loss_sum = 0.0
            if spent > hours * 3600:
                break
    torch.save({"state": lm.state_dict(), "emb": emb, "hidden": hidden}, out)
    print(f"{out}: {sum(p.numel() for p in lm.parameters()):,} parameters, {seen:,} tokens seen")


def load(m, path):
    ck = torch.load(path, weights_only=True)
    lm = LM(len(m.words), ck["emb"], ck["hidden"])
    lm.load_state_dict(ck["state"])
    return lm.eval()


@torch.no_grad()
def measure(m, lm, path, k):
    """Same counts as research.next_word: every word of every run, <unk> always a miss."""
    r = dict(words=0, known=0, top1=0, topk=0)
    banned = torch.tensor([BOS, EOS, UNK])
    for line in open(path, encoding="utf-8"):
        ids = line_ids(m, line)
        if len(ids) < 2:
            continue
        x = torch.tensor([ids], dtype=torch.int64)
        h, _ = lm.hidden_states(x)
        logp = lm.out.log_prob(h[0])
        logp[:, banned] = -torch.inf
        top = logp.topk(k, dim=1).indices
        for i in range(1, len(ids)):
            w = ids[i]
            if w == BOS:
                continue
            r["words"] += 1
            r["known"] += w != UNK
            r["top1"] += w != UNK and top[i - 1, 0].item() == w
            r["topk"] += w != UNK and w in top[i - 1].tolist()
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["data", "train", "score"])
    ap.add_argument("table")
    ap.add_argument("args", nargs="+")
    ap.add_argument("--hours", type=float, default=1.0)
    ap.add_argument("--emb", type=int, default=128)
    ap.add_argument("--hidden", type=int, default=256)
    ap.add_argument("--k", type=int, default=3)
    a = ap.parse_args()
    m = table.read(a.table)
    if a.cmd == "data":
        build_data(m, a.args[0], int(a.args[1]))
    elif a.cmd == "train":
        train(m, a.args[0], a.args[1], a.hours, a.emb, a.hidden)
    else:
        lm = load(m, a.args[0])
        for test in a.args[1:]:
            r = measure(m, lm, test, a.k)
            n = r["words"]
            print(
                f"{test.rsplit('/', 1)[-1]:12} words {n:6} in-vocab {r['known'] / n:.2%} "
                f"top1 {r['top1'] / n:.2%} top{a.k} {r['topk'] / n:.2%}",
                flush=True,
            )


if __name__ == "__main__":
    main()
