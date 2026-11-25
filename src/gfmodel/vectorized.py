"""A second, independent implementation with numpy, for large Monte Carlo runs and exact sums.

``model.py`` and ``experience.py`` are the reference (pure Python, line-by-line comparable with the
JavaScript port).  This module computes the same quantities with numpy arrays, much faster, using
numpy's own random generator.  It exists for two reasons: to check the reference by a different
route (``tests/test_vectorized.py``), and to run the large simulations that reproduce the numbers in
the paper (``scripts/reproduce_paper.py``).
"""

from __future__ import annotations

import numpy as np

from .experience import DEFAULT_SHOWN_LENGTH, shown_sequences
from .model import CLASS_NAMES, HIT_RATE, HypothesisSpace, log_likelihood, p_continue


def _log_tables(space: HypothesisSpace, max_len: int) -> tuple[np.ndarray, np.ndarray]:
    nh = len(space.chains)
    lc = np.zeros((nh, max_len + 1))
    ls = np.zeros((nh, max_len + 1))
    for h, c in enumerate(space.chains):
        for k in range(max_len + 1):
            pc = p_continue(c, max(k, 1))
            lc[h, k] = np.log(pc)
            ls[h, k] = np.log(1.0 - pc)
    return lc, ls


def loglik_matrix(space: HypothesisSpace, seqs: np.ndarray) -> np.ndarray:
    """log P(seq | hypothesis) for each row of ``seqs`` (shape (M, n), entries 0/1).

    Returns an array of shape (M, H).  Same convention as ``model.log_likelihood``.
    """
    m, n = seqs.shape
    nh = len(space.chains)
    ll = np.zeros((m, nh))
    if n == 0:
        return ll
    lc, ls = _log_tables(space, n + 1)
    ll += np.log(HIT_RATE)
    streak = np.ones(m, dtype=int)
    for t in range(1, n):
        cont = seqs[:, t] == seqs[:, t - 1]
        for h in range(nh):
            ll[:, h] += np.where(cont, lc[h, streak], ls[h, streak])
        streak = np.where(cont, streak + 1, 1)
    return ll


def simulate_loglik(
    space: HypothesisSpace, ns: list[int], m: int, seed: int
) -> dict[int, np.ndarray]:
    """Log-likelihood matrices of ``m`` simulated Steady learners at each experience level in ns.

    Learner a has one path of max(ns) flips; its experience at level N is the first N flips.
    """
    ns = sorted(set(ns))
    nmax = ns[-1]
    rng = np.random.default_rng(seed)
    paths = rng.integers(0, 2, size=(m, nmax))
    nh = len(space.chains)
    lc, ls = _log_tables(space, nmax + 1)
    out: dict[int, np.ndarray] = {}
    ll = np.zeros((m, nh))
    streak = np.ones(m, dtype=int)
    if 0 in ns:
        out[0] = ll.copy()
    for t in range(1, nmax + 1):
        if t == 1:
            ll += np.log(HIT_RATE)
        else:
            cont = paths[:, t - 1] == paths[:, t - 2]
            for h in range(nh):
                ll[:, h] += np.where(cont, lc[h, streak], ls[h, streak])
            streak = np.where(cont, streak + 1, 1)
        if t in ns:
            out[t] = ll.copy()
    return out


def posteriors(space: HypothesisSpace, ll: np.ndarray) -> np.ndarray:
    """Posterior over hypotheses for each row of a log-likelihood matrix."""
    prior = np.array(space.prior)
    z = ll - ll.max(axis=1, keepdims=True)
    w = prior[None, :] * np.exp(z)
    return w / w.sum(axis=1, keepdims=True)


def class_means(space: HypothesisSpace, ll: np.ndarray) -> dict[str, float]:
    """Mean posterior of the Switchy, Steady and Sticky classes."""
    post = posteriors(space, ll).mean(axis=0)
    out = {"switchy": 0.0, "steady": 0.0, "sticky": 0.0}
    for h, c in enumerate(space.chains):
        out[CLASS_NAMES[c.kind]] += float(post[h])
    return out


def pcont_by_streak(
    space: HypothesisSpace,
    ll: np.ndarray,
    shown_mode: str = "iid8",
    length: int = DEFAULT_SHOWN_LENGTH,
    chunk: int = 4000,
) -> list[float]:
    """Mean P(streak continues) after the shown sequences, for s = 1..length (see experience.py)."""
    groups = shown_sequences(shown_mode, length)
    prior = np.array(space.prior)
    chains = space.chains
    out = []
    # per-group: exp(loglik of shown sequence) and p_continue at the end streak
    prepared = []
    for s_idx, group in enumerate(groups):
        arr = np.array(group)
        e = np.exp(
            np.stack([np.array([log_likelihood(c, q) for q in group]) for c in chains], axis=1)
        )
        pcs = np.array([p_continue(c, s_idx + 1) for c in chains])
        prepared.append((arr, e, pcs))
    sums = np.zeros(len(groups))
    m = ll.shape[0]
    for a in range(0, m, chunk):
        part = ll[a : a + chunk]
        w = prior[None, :] * np.exp(part - part.max(axis=1, keepdims=True))
        for s_idx, (_, e, pcs) in enumerate(prepared):
            ww = w[:, None, :] * e[None, :, :]
            pc = (ww * pcs[None, None, :]).sum(axis=2) / ww.sum(axis=2)
            sums[s_idx] += pc.mean(axis=1).sum()
    out = [float(x) / m for x in sums]
    return out


def exact_loglik(space: HypothesisSpace, n: int) -> np.ndarray:
    """Log-likelihood matrix for all 2**n sequences of length n (n <= 22)."""
    if n > 22:
        raise ValueError("n too large for exact enumeration")
    v = np.arange(2**n)
    seqs = (v[:, None] >> np.arange(n)[None, :]) & 1
    return loglik_matrix(space, seqs)


def pcont_per_sequence(
    space: HypothesisSpace, ll: np.ndarray, seqs: list[list[int]], chunk: int = 4000
) -> np.ndarray:
    """Mean P(the final streak continues) after each given shown sequence (averaged over learners)."""
    from .model import end_streak

    prior = np.array(space.prior)
    e = np.exp(np.stack([np.array([log_likelihood(c, q) for q in seqs]) for c in space.chains], 1))
    pcs = np.stack([np.array([p_continue(c, end_streak(q)) for c in space.chains]) for q in seqs])
    tot = np.zeros(len(seqs))
    for a in range(0, ll.shape[0], chunk):
        part = ll[a : a + chunk]
        w = prior[None, :] * np.exp(part - part.max(axis=1, keepdims=True))
        ww = w[:, None, :] * e[None, :, :]
        tot += ((ww * pcs[None]).sum(axis=2) / ww.sum(axis=2)).sum(axis=0)
    return tot / ll.shape[0]
