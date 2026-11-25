"""The numpy implementation (used for the large reproduction runs) against the pure-Python reference."""

import numpy as np
import pytest

from gfmodel import build_space, exact_experience, run_agents
from gfmodel import vectorized as V
from gfmodel.model import log_likelihood


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"p_steady": 0.1, "switchy_share": 0.8, "steps": 2, "degree": 0.7}],
)
def test_loglik_matrix_matches_reference(kwargs):
    sp = build_space(**kwargs)
    rng = np.random.default_rng(0)
    seqs = rng.integers(0, 2, (50, 17))
    ll = V.loglik_matrix(sp, seqs)
    for i in range(50):
        for h, c in enumerate(sp.chains):
            assert ll[i, h] == pytest.approx(log_likelihood(c, list(seqs[i])), abs=1e-12)


@pytest.mark.parametrize("mode", ["streak", "iid8"])
def test_exact_sum_matches_reference_exact_sum(mode):
    sp = build_space()
    n = 9
    ref = exact_experience(sp, n, mode)
    ll = V.exact_loglik(sp, n)
    assert V.class_means(sp, ll) == pytest.approx(ref["class_post"], abs=1e-12)
    assert V.pcont_by_streak(sp, ll, mode, 8) == pytest.approx(ref["pcont"], abs=1e-12)


def test_monte_carlo_of_both_implementations_agree():
    sp = build_space()
    ref = run_agents(sp, [25], 6000, 3, "streak")[0]
    ll = V.simulate_loglik(sp, [25], 60000, 3)[25]
    assert V.pcont_by_streak(sp, ll, "streak", 8) == pytest.approx(ref["pcont"], abs=0.006)
    assert V.class_means(sp, ll) == pytest.approx(ref["class_post"], abs=0.01)


def test_pcont_per_sequence_consistent_with_group_means():
    sp = build_space()
    ll = V.exact_loglik(sp, 8)
    from gfmodel import shown_sequences

    groups = shown_sequences("iid8", 8)
    flat = [q for g in groups for q in g]
    per = V.pcont_per_sequence(sp, ll, flat)
    by_group = V.pcont_by_streak(sp, ll, "iid8", 8)
    start = 0
    for g, expected in zip(groups, by_group, strict=True):
        assert per[start : start + len(g)].mean() == pytest.approx(expected, abs=1e-12)
        start += len(g)
