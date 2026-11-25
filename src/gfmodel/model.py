"""The causal-uncertainty model of Dorst (2026), "Bayesians Commit the Gambler's Fallacy".

Paper: Cognitive Science 50(1): e70171, https://doi.org/10.1111/cogs.70171 (CC BY).
Section numbers below refer to that paper.  This file is pure Python (standard library only) so
that the JavaScript port in ``docs/model.js`` can be compared with it line by line.

The model in one paragraph (Sections 2-3).  A learner watches a binary process (hit = 1,
miss = 0) whose long-run hit rate is known to be 50%.  It is unsure which of three kinds of
process it is facing:

* Steady: every outcome is a 50% chance, independent of the past.
* Switchy: the longer the current streak, the more likely it is to switch.
* Sticky: the longer the current streak, the more likely it is to continue.

Switchy and Sticky are "streak chains" (Section 3, Fig. 2 and Fig. 3): the probability of the
next outcome depends only on the length k of the current streak, and the probability of a
continuation moves away from 50% by ``(degree - 0.5) / steps`` per step of streak, up to
``steps`` steps.  The paper's main simulations use steps = 4 and degree = 0.9 ("4-step-90%").
The learner updates by Bayes' rule on the sequence it has seen (Section 4, the formula for
P(Ste | sigma)) and predicts by total probability (Section 3.1).

Choices the paper leaves open, and what is done here, are marked CHOICE.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Section 3: the long-run hit rate is known to be 50% (Section 6.1 relaxes this; not implemented).
HIT_RATE = 0.5

# Section 3 and Fig. 3: the main simulations use 4-step-90% chains.
DEFAULT_STEPS = 4
DEFAULT_DEGREE = 0.9

# Section 6.3 / Fig. 4 (bottom right): speeds x = 1..10 for the "unsure about the speed" prior.
DEFAULT_MAX_STEPS = 10

SWITCHY = -1
STEADY = 0
STICKY = 1
CLASS_NAMES = {SWITCHY: "switchy", STEADY: "steady", STICKY: "sticky"}


@dataclass(frozen=True)
class Chain:
    """One causal hypothesis: a symmetric streak chain (Section 3).

    kind: -1 Switchy, 0 Steady, +1 Sticky.
    steps: number of streak steps over which the shift builds up (the paper's "x-step").
    degree: the extreme continuation/switch probability reached after ``steps`` steps
        (the paper's "90%" in "4-step-Switchy90%").
    """

    kind: int
    steps: int = DEFAULT_STEPS
    degree: float = DEFAULT_DEGREE

    @property
    def label(self) -> str:
        if self.kind == STEADY:
            return "steady"
        return f"{self.steps}-step-{CLASS_NAMES[self.kind]}-{round(self.degree * 100)}%"


def shift(chain: Chain, k: int) -> float:
    """The deviation c from 50% after a streak of length k (Section 3.1).

    For the 4-step-90% chains: k=1 gives 0.1, k=2 gives 0.2, k=3 gives 0.3, k>=4 gives 0.4.
    """
    if chain.kind == STEADY:
        return 0.0
    return (chain.degree - HIT_RATE) / chain.steps * min(k, chain.steps)


def p_continue(chain: Chain, k: int) -> float:
    """P(the current streak of length k continues | chain).

    Sticky: 0.5 + c.  Switchy: 0.5 - c.  Steady: 0.5 (Section 3.1, first displayed equation).
    """
    return HIT_RATE + chain.kind * shift(chain, k)


def log_likelihood(chain: Chain, seq: list[int] | tuple[int, ...]) -> float:
    """log P(seq | chain) for a sequence of 0/1 outcomes.

    CHOICE (the paper does not say how a sequence starts): the first outcome has probability 0.5
    under every hypothesis, and the streak counter starts at 1 after it.  So the second outcome
    already uses the streak-1 probability.  Each sequence the learner sees (its past experience,
    and later the sequence it is shown) is treated as a fresh run of the chain.
    The first-outcome term is the same for every hypothesis, so it cancels in the posterior.
    """
    if len(seq) == 0:
        return 0.0
    total = math.log(HIT_RATE)
    streak = 1
    for t in range(1, len(seq)):
        pc = p_continue(chain, streak)
        if seq[t] == seq[t - 1]:
            total += math.log(pc)
            streak += 1
        else:
            total += math.log(1.0 - pc)
            streak = 1
    return total


def end_streak(seq: list[int] | tuple[int, ...]) -> int:
    """Length of the final run of identical outcomes."""
    if len(seq) == 0:
        return 0
    k = 1
    for t in range(len(seq) - 1, 0, -1):
        if seq[t] == seq[t - 1]:
            k += 1
        else:
            break
    return k


def streak_chain_matrix(chain: Chain) -> list[list[float]]:
    """The row-stochastic matrix of Fig. 2 / Fig. 3 for a streak chain.

    States are ordered from the longest miss-streak to the longest hit-streak:
    miss streak ``steps`` .. 1, then hit streak 1 .. ``steps``.  For steps = 4 these are the
    paper's states (0000, 1000, _100, __10, __01, _011, 0111, 1111).  Row i, column j is the
    probability of moving from state i to state j.  The last state in each direction (streak
    ``steps`` or longer) stays put when the streak continues.
    """
    s = chain.steps
    n = 2 * s
    # index of "miss streak k" is s-k ; index of "hit streak k" is s+k-1
    miss = {k: s - k for k in range(1, s + 1)}
    hit = {k: s + k - 1 for k in range(1, s + 1)}
    m = [[0.0] * n for _ in range(n)]
    for k in range(1, s + 1):
        pc = p_continue(chain, k)
        nxt = min(k + 1, s)
        # after a miss streak of length k: miss again (continue) or hit (switch)
        m[miss[k]][miss[nxt]] += pc
        m[miss[k]][hit[1]] += 1.0 - pc
        # after a hit streak of length k: hit again (continue) or miss (switch)
        m[hit[k]][hit[nxt]] += pc
        m[hit[k]][miss[1]] += 1.0 - pc
    return m


def sequence_probability_via_matrix(chain: Chain, seq: list[int] | tuple[int, ...]) -> float:
    """P(seq | chain) computed by walking the Fig. 3 matrix (independent of ``log_likelihood``).

    Same CHOICE as ``log_likelihood``: the first outcome has probability 0.5.
    """
    if len(seq) == 0:
        return 1.0
    s = chain.steps
    m = streak_chain_matrix(chain)
    miss = {k: s - k for k in range(1, s + 1)}
    hit = {k: s + k - 1 for k in range(1, s + 1)}
    state = hit[1] if seq[0] == 1 else miss[1]
    prob = HIT_RATE
    for t in range(1, len(seq)):
        cur = seq[t - 1]
        # candidate next states: continue the streak, or switch to a streak of length 1
        if seq[t] == cur:
            k = (state - s + 1) if cur == 1 else (s - state)
            nxt = hit[min(k + 1, s)] if cur == 1 else miss[min(k + 1, s)]
        else:
            nxt = miss[1] if cur == 1 else hit[1]
        prob *= m[state][nxt]
        state = nxt
    return prob


@dataclass(frozen=True)
class HypothesisSpace:
    """The learner's hypotheses and prior (Section 4: "uniform (1/3, 1/3, 1/3)" by default)."""

    chains: tuple[Chain, ...]
    prior: tuple[float, ...]

    @property
    def classes(self) -> tuple[int, ...]:
        return tuple(c.kind for c in self.chains)


def build_space(
    p_steady: float = 1.0 / 3.0,
    switchy_share: float = 0.5,
    steps: int = DEFAULT_STEPS,
    degree: float = DEFAULT_DEGREE,
    speed_mixture: bool = False,
    max_steps: int = DEFAULT_MAX_STEPS,
) -> HypothesisSpace:
    """Build the hypothesis space and prior.

    p_steady: prior probability of Steady.  The rest, ``1 - p_steady``, is split between the
        Switchy and Sticky classes with ``switchy_share`` going to Switchy.
        Defaults give the paper's uniform (1/3, 1/3, 1/3) (Section 4).
    speed_mixture: if False, one Switchy and one Sticky chain with the given ``steps``.
        If True, the Switchy and the Sticky classes are each spread evenly over chains with
        steps = 1..max_steps (Section 4, Fig. 4 bottom right and Section 6.3).  With
        p_steady = 1/21 and switchy_share = 0.5 this is the paper's "uniform over the 21
        hypotheses" prior (CHOICE: the paper says "uniformly unsure"; the 1/21 reading is the one
        that reproduces its 17% and 8% figures, see results/reproduction.csv).
    """
    if not 0.0 <= p_steady <= 1.0:
        raise ValueError("p_steady must be in [0, 1]")
    if not 0.0 <= switchy_share <= 1.0:
        raise ValueError("switchy_share must be in [0, 1]")
    p_swi = (1.0 - p_steady) * switchy_share
    p_sti = (1.0 - p_steady) * (1.0 - switchy_share)
    if speed_mixture:
        xs = list(range(1, max_steps + 1))
        chains = [Chain(STEADY)]
        prior = [p_steady]
        chains += [Chain(SWITCHY, x, degree) for x in xs]
        prior += [p_swi / len(xs)] * len(xs)
        chains += [Chain(STICKY, x, degree) for x in xs]
        prior += [p_sti / len(xs)] * len(xs)
    else:
        chains = [Chain(SWITCHY, steps, degree), Chain(STEADY), Chain(STICKY, steps, degree)]
        prior = [p_swi, p_steady, p_sti]
    return HypothesisSpace(tuple(chains), tuple(prior))


def posterior_from_loglik(prior: tuple[float, ...], logliks: list[float]) -> list[float]:
    """Bayes' rule (Section 4): P(h | data) proportional to P(h) P(data | h)."""
    m = max(logliks)
    w = [p * math.exp(ll - m) for p, ll in zip(prior, logliks, strict=True)]
    z = sum(w)
    return [x / z for x in w]


def posterior(space: HypothesisSpace, seq: list[int] | tuple[int, ...]) -> list[float]:
    """Posterior over ``space.chains`` after seeing ``seq``."""
    return posterior_from_loglik(space.prior, [log_likelihood(c, seq) for c in space.chains])


def predict_continue(
    space: HypothesisSpace, post: list[float] | tuple[float, ...], k: int
) -> float:
    """P(a streak of length k continues) by total probability (Section 3.1).

    = sum over hypotheses of P(h) * P(continue | h, streak k).
    """
    return sum(p * p_continue(c, k) for p, c in zip(post, space.chains, strict=True))


def class_totals(space: HypothesisSpace, post: list[float] | tuple[float, ...]) -> dict[str, float]:
    """Posterior probability of the Switchy, Steady and Sticky classes."""
    out = {"switchy": 0.0, "steady": 0.0, "sticky": 0.0}
    for p, c in zip(post, space.chains, strict=True):
        out[CLASS_NAMES[c.kind]] += p
    return out


def predict_after(space: HypothesisSpace, experience: list[int], shown: list[int]) -> dict:
    """A single learner: update on ``experience``, then on ``shown``, then predict.

    The learner has seen ``experience`` (its past), and is now shown ``shown`` (for example a
    streak, or an 8-outcome sequence ending in a streak).  The reported probability is that the
    streak at the end of ``shown`` continues.  Each sequence is a fresh run of the chain (CHOICE,
    see ``log_likelihood``).
    """
    post_exp = posterior(space, experience)
    ll = [log_likelihood(c, experience) + log_likelihood(c, shown) for c in space.chains]
    post_all = posterior_from_loglik(space.prior, ll)
    k = end_streak(shown)
    return {
        "prior": list(space.prior),
        "after_experience": post_exp,
        "after_experience_classes": class_totals(space, post_exp),
        "after_shown": post_all,
        "after_shown_classes": class_totals(space, post_all),
        "streak": k,
        "p_continue": predict_continue(space, post_all, k),
    }
