"""Learners with a given amount of past experience (Dorst 2026, Sections 4, 5.1 and 5.2).

A "learner with N outcomes of experience" is a Bayesian (``model.py``) that has conditioned on one
sequence of N outcomes from a Steady process (a fair coin).  This is the paper's "limited data"
agent: "Bayesians who have conditioned on sequences of lengths 25, 40, 75, or 100" (Section 5).
Experience-dependence (Section 5.2) is the comparison between agents with less and more data.

Everything here uses only the standard library and a tiny seeded generator (mulberry32), so that
the JavaScript port in ``docs/model.js`` draws exactly the same coin flips and gives the same
numbers to floating-point precision.

The averages are Monte Carlo averages over ``k_agents`` simulated learners.  The paper also
simulates (Section 5: "I had to write my own" Bayesian-statistics code); no closed form exists.
``exact_experience`` enumerates all 2**N sequences for small N and is used to check the Monte
Carlo code.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from itertools import product

from .model import (
    CLASS_NAMES,
    HIT_RATE,
    Chain,
    HypothesisSpace,
    end_streak,
    log_likelihood,
    p_continue,
)

# Section 4 and 5.3: the sequences shown to subjects have 8 outcomes (Bloomfield & Hales design).
DEFAULT_SHOWN_LENGTH = 8
TIE_TOLERANCE = 1e-12
_MASK = 0xFFFFFFFF


class Mulberry32:
    """The 32-bit generator mulberry32 (public domain), written so that JS and Python agree."""

    def __init__(self, seed: int):
        self.state = seed & _MASK

    def random(self) -> float:
        self.state = (self.state + 0x6D2B79F5) & _MASK
        a = self.state
        t = ((a ^ (a >> 15)) * (a | 1)) & _MASK
        t = (t ^ ((t + (((t ^ (t >> 7)) * (t | 61)) & _MASK)) & _MASK)) & _MASK
        return ((t ^ (t >> 14)) & _MASK) / 4294967296.0

    def flip(self) -> int:
        """One fair coin flip: 1 (hit) or 0 (miss).  A Steady process (Section 2)."""
        return 1 if self.random() < HIT_RATE else 0


def steady_sequence(seed: int, n: int) -> list[int]:
    """n flips of the page's pseudo-random fair coin."""
    rng = Mulberry32(seed)
    return [rng.flip() for _ in range(n)]


def shown_sequences(mode: str, length: int = DEFAULT_SHOWN_LENGTH) -> list[list[list[int]]]:
    """What the learner is shown, grouped by the length s of the final streak (s = 1..length).

    mode "streak": the learner is shown one miss followed by s hits, so the streak has length
        exactly s and its start is marked by a switch.  Section 5.1: "present our Bayesians ...
        with streaks of varying lengths".  CHOICE: the paper does not say how the streak is
        presented.  This reading reproduces the curves of Fig. 6 (top middle) for 25- and
        40-outcome learners to within 0.004 read by eye, accuracy about 0.01 (results/reproduction.csv); showing the
        bare s hits with no preceding switch is about 0.01-0.02 higher for streaks of 4 or more.
    mode "iid8": the learner is shown every one of the 2**length equally likely IID sequences of
        ``length`` outcomes whose final streak has length exactly s (Section 4 and 5.3: IID
        sequences of 8 outcomes, as in Bloomfield & Hales; Section 5.5).  CHOICE: the paper does
        not say which streak-length sequences it used for Fig. 6; with this reading the text's
        numbers for 40-outcome learners (48.5%, 47.5%, 55%) are reproduced.
    Returns a list indexed by s-1 of lists of sequences.  Sequences are enumerated in the order of
    the integer v = 0 .. 2**length - 1, with outcome t equal to bit t of v (the JS port does
    the same).
    """
    if mode == "streak":
        return [[[0] + [1] * s] for s in range(1, length + 1)]
    if mode != "iid8":
        raise ValueError(f"unknown shown mode {mode!r}")
    groups: list[list[list[int]]] = [[] for _ in range(length)]
    for v in range(2**length):
        seq = [(v >> t) & 1 for t in range(length)]
        groups[end_streak(seq) - 1].append(seq)
    return groups


def _tables(space: HypothesisSpace, max_len: int) -> tuple[list[list[float]], list[list[float]]]:
    """log P(continue) and log P(switch) for streak k = 0..max_len, per hypothesis."""
    lc, ls = [], []
    for c in space.chains:
        rc, rs = [], []
        for k in range(max_len + 1):
            kk = max(k, 1)
            pc = p_continue(c, kk)
            rc.append(math.log(pc))
            rs.append(math.log(1.0 - pc))
        lc.append(rc)
        ls.append(rs)
    return lc, ls


def run_agents(
    space: HypothesisSpace,
    ns: Sequence[int],
    k_agents: int,
    seed: int,
    shown_mode: str | None = "iid8",
    shown_length: int = DEFAULT_SHOWN_LENGTH,
    *,
    path_length: int | None = None,
) -> list[dict]:
    """Average over ``k_agents`` simulated learners at each experience level in ``ns``.

    Learner a draws one long path of Steady flips (the generator is consumed agent by agent, each
    agent drawing ``path_length`` flips, default max(ns)).  Its experience at level N is the first
    N flips of its path, so the same learner has "seen more" at larger N and the curves are smooth.
    A fixed ``path_length`` (the page uses 300) makes the row for a given N independent of the
    other levels requested; it must be at least max(ns).

    For each N returns:
      n: N
      class_post: mean posterior of Switchy / Steady / Sticky (Section 4, Fig. 4 top right)
      pcont: for s = 1..shown_length, the mean over learners (and over the shown sequences with a
          final streak of s) of P(the streak continues) after also seeing the shown sequence.
          Empty if ``shown_mode`` is None.
      share_above: for each s, the share of (learner, shown sequence) pairs whose probability is
          above 50%, among the pairs that are not exactly 50% (Section 5.5, dichotomised
          binary predictions).  None where every pair is exactly 50%.
    """
    ns_sorted = sorted(set(ns))
    nmax = ns_sorted[-1] if ns_sorted else 0
    if path_length is not None and path_length < nmax:
        raise ValueError(f"path_length {path_length} is shorter than the largest level {nmax}")
    extra_draws = 0 if path_length is None else path_length - nmax
    chains = space.chains
    nh = len(chains)
    prior = space.prior
    lc, ls = _tables(space, nmax + shown_length + 1)

    if shown_mode is not None:
        groups = shown_sequences(shown_mode, shown_length)
        # per shown sequence: log-likelihood under each hypothesis, and the final streak
        shown_exp = []  # exp(log-lik of shown seq) per hypothesis, times p_continue at its end
        for g_idx, group in enumerate(groups):
            s = g_idx + 1
            rows = []
            for seq in group:
                e = [math.exp(log_likelihood(c, seq)) for c in chains]
                pcs = [p_continue(c, s) for c in chains]
                rows.append((e, pcs))
            shown_exp.append(rows)

    rng = Mulberry32(seed)
    sums_post = {n: [0.0] * nh for n in ns_sorted}
    sums_pc = {n: [0.0] * shown_length for n in ns_sorted}
    cnt_above = {n: [0] * shown_length for n in ns_sorted}
    cnt_below = {n: [0] * shown_length for n in ns_sorted}

    for _ in range(k_agents):
        ll = [0.0] * nh
        streak = 0
        prev = -1
        ni = 0
        # level N = 0 is the prior (no experience)
        if ns_sorted and ns_sorted[0] == 0:
            _accumulate(
                0,
                ll,
                prior,
                sums_post,
                sums_pc,
                cnt_above,
                cnt_below,
                shown_exp if shown_mode is not None else None,
            )
            ni = 1
        for t in range(1, nmax + 1):
            x = rng.flip()
            if t == 1:
                for h in range(nh):
                    ll[h] += math.log(HIT_RATE)
                streak = 1
            elif x == prev:
                for h in range(nh):
                    ll[h] += lc[h][streak]
                streak += 1
            else:
                for h in range(nh):
                    ll[h] += ls[h][streak]
                streak = 1
            prev = x
            if ni < len(ns_sorted) and ns_sorted[ni] == t:
                _accumulate(
                    t,
                    ll,
                    prior,
                    sums_post,
                    sums_pc,
                    cnt_above,
                    cnt_below,
                    shown_exp if shown_mode is not None else None,
                )
                ni += 1
        for _ in range(extra_draws):  # draw and discard, so the next learner's path is fixed
            rng.flip()

    out = []
    for n in ns_sorted:
        class_post = {"switchy": 0.0, "steady": 0.0, "sticky": 0.0}
        for h, c in enumerate(chains):
            class_post[CLASS_NAMES[c.kind]] += sums_post[n][h] / k_agents
        row = {"n": n, "class_post": class_post, "pcont": [], "share_above": []}
        if shown_mode is not None:
            for s_idx in range(shown_length):
                n_seq = len(shown_exp[s_idx])
                row["pcont"].append(sums_pc[n][s_idx] / (k_agents * n_seq))
                a, b = cnt_above[n][s_idx], cnt_below[n][s_idx]
                row["share_above"].append(a / (a + b) if a + b > 0 else None)
        out.append(row)
    return out


def _accumulate(n, ll, prior, sums_post, sums_pc, cnt_above, cnt_below, shown_exp):
    nh = len(ll)
    m = max(ll)
    a = [prior[h] * math.exp(ll[h] - m) for h in range(nh)]
    z = sum(a)
    for h in range(nh):
        sums_post[n][h] += a[h] / z
    if shown_exp is None:
        return
    for s_idx, rows in enumerate(shown_exp):
        for e, pcs in rows:
            num = 0.0
            den = 0.0
            for h in range(nh):
                w = a[h] * e[h]
                num += w * pcs[h]
                den += w
            pc = num / den
            sums_pc[n][s_idx] += pc
            if pc > HIT_RATE + TIE_TOLERANCE:
                cnt_above[n][s_idx] += 1
            elif pc < HIT_RATE - TIE_TOLERANCE:
                cnt_below[n][s_idx] += 1


def direct_pcont(space: HypothesisSpace, experience: Sequence[int], shown: Sequence[int]) -> float:
    """The same quantity for one learner, from the definitions (no shortcuts).

    Used to test ``run_agents``: update on experience, update on the shown sequence, then total
    probability for the final streak.
    """
    ll = [log_likelihood(c, experience) + log_likelihood(c, shown) for c in space.chains]
    m = max(ll)
    w = [p * math.exp(x - m) for p, x in zip(space.prior, ll, strict=True)]
    z = sum(w)
    k = end_streak(shown)
    return sum(wi / z * p_continue(c, k) for wi, c in zip(w, space.chains, strict=True))


def exact_experience(
    space: HypothesisSpace,
    n: int,
    shown_mode: str | None = "iid8",
    shown_length: int = DEFAULT_SHOWN_LENGTH,
) -> dict:
    """Exact average over all 2**n equally likely Steady sequences (small n only).

    Returns the same fields as one row of ``run_agents`` (without the share).
    """
    if n > 16:
        raise ValueError("exact enumeration is only meant for n <= 16")
    nh = len(space.chains)
    post_sum = [0.0] * nh
    groups = shown_sequences(shown_mode, shown_length) if shown_mode is not None else []
    pc_sum = [0.0] * shown_length
    count = 0
    for seq in product((0, 1), repeat=n):
        count += 1
        ll = [log_likelihood(c, seq) for c in space.chains]
        m = max(ll)
        w = [p * math.exp(x - m) for p, x in zip(space.prior, ll, strict=True)]
        z = sum(w)
        for h in range(nh):
            post_sum[h] += w[h] / z
        for s_idx, group in enumerate(groups):
            acc = 0.0
            for q in group:
                acc += direct_pcont(space, seq, q)
            pc_sum[s_idx] += acc / len(group)
    class_post = {"switchy": 0.0, "steady": 0.0, "sticky": 0.0}
    for h, c in enumerate(space.chains):
        class_post[CLASS_NAMES[c.kind]] += post_sum[h] / count
    return {
        "n": n,
        "class_post": class_post,
        "pcont": [x / count for x in pc_sum] if groups else [],
    }


def crossing_streak(pcont: Sequence[float]) -> int | None:
    """The first streak length s (1-based) at which the average learner expects a continuation.

    That is the first s with mean P(continue) above 50% (the end of "predicting switches" and the
    start of "predicting continuations").  Returns None if the curve is never above 50%.  If it is
    above 50% already at s = 1 the answer is 1.
    """
    for i, p in enumerate(pcont):
        if p > HIT_RATE + TIE_TOLERANCE:
            return i + 1
    return None


def make_chain_from_paper() -> Chain:
    """Convenience: the paper's 4-step-Switchy90% chain."""
    return Chain(-1, 4, 0.9)
