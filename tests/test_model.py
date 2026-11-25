"""Tests of the model definitions against the paper's own numbers (Dorst 2026, Sections 2-4)."""

import itertools
import math
import random

import pytest

from gfmodel import (
    Chain,
    HypothesisSpace,
    build_space,
    class_totals,
    end_streak,
    log_likelihood,
    p_continue,
    posterior,
    predict_after,
    predict_continue,
    streak_chain_matrix,
)
from gfmodel.model import sequence_probability_via_matrix, shift

SWI = Chain(-1, 4, 0.9)
STE = Chain(0)
STI = Chain(1, 4, 0.9)


def assert_matrix_close(actual, expected):
    assert len(actual) == len(expected)
    for row_a, row_e in zip(actual, expected, strict=True):
        assert row_a == pytest.approx(row_e, abs=1e-12)


def space_with_prior(prior):
    return HypothesisSpace((SWI, STE, STI), tuple(prior))


def test_shift_for_4_step_90_chains():
    # Section 3.1: "with a streak of 1, c = 0.1; with 2, c = 0.2, etc."; 90% is reached at 4.
    assert [shift(SWI, k) for k in (1, 2, 3, 4, 5, 9)] == pytest.approx(
        [0.1, 0.2, 0.3, 0.4, 0.4, 0.4]
    )
    assert shift(STE, 7) == 0.0


def test_p_continue_signs():
    assert p_continue(SWI, 3) == pytest.approx(0.2)
    assert p_continue(STI, 3) == pytest.approx(0.8)
    assert p_continue(STE, 3) == 0.5


# Fig. 3 of the paper, copied from the printed matrices.  States are ordered
# (0000, 1000, _100, __10, __01, _011, 0111, 1111).
FIG3_SWITCHY = [
    [0.1, 0, 0, 0, 0.9, 0, 0, 0],
    [0.2, 0, 0, 0, 0.8, 0, 0, 0],
    [0, 0.3, 0, 0, 0.7, 0, 0, 0],
    [0, 0, 0.4, 0, 0.6, 0, 0, 0],
    [0, 0, 0, 0.6, 0, 0.4, 0, 0],
    [0, 0, 0, 0.7, 0, 0, 0.3, 0],
    [0, 0, 0, 0.8, 0, 0, 0, 0.2],
    [0, 0, 0, 0.9, 0, 0, 0, 0.1],
]
FIG3_STICKY = [
    [0.9, 0, 0, 0, 0.1, 0, 0, 0],
    [0.8, 0, 0, 0, 0.2, 0, 0, 0],
    [0, 0.7, 0, 0, 0.3, 0, 0, 0],
    [0, 0, 0.6, 0, 0.4, 0, 0, 0],
    [0, 0, 0, 0.4, 0, 0.6, 0, 0],
    [0, 0, 0, 0.3, 0, 0, 0.7, 0],
    [0, 0, 0, 0.2, 0, 0, 0, 0.8],
    [0, 0, 0, 0.1, 0, 0, 0, 0.9],
]


def test_matrices_equal_fig3():
    assert_matrix_close(streak_chain_matrix(SWI), FIG3_SWITCHY)
    assert_matrix_close(streak_chain_matrix(STI), FIG3_STICKY)


def test_two_step_matrix_equals_dorst_blog_comment():
    # Dorst's own 2-step 60% example (greaterwrong.com comment, 9 Jan 2024), states (00,10,01,11):
    switchy60 = [[0.4, 0, 0.6, 0], [0.45, 0, 0.55, 0], [0, 0.55, 0, 0.45], [0, 0.6, 0, 0.4]]
    sticky60 = [[0.6, 0, 0.4, 0], [0.55, 0, 0.45, 0], [0, 0.45, 0, 0.55], [0, 0.4, 0, 0.6]]
    assert_matrix_close(streak_chain_matrix(Chain(-1, 2, 0.6)), switchy60)
    assert_matrix_close(streak_chain_matrix(Chain(1, 2, 0.6)), sticky60)


def test_fig2_two_step_70_state_00():
    # Fig. 2 caption: in state 00 the 2-step-Switchy70% chain misses again with 30%, hits with 70%.
    m = streak_chain_matrix(Chain(-1, 2, 0.7))
    assert m[0] == pytest.approx([0.3, 0, 0.7, 0])


@pytest.mark.parametrize("chain", [SWI, STE, STI, Chain(-1, 2, 0.7), Chain(1, 7, 0.6)])
def test_matrix_rows_sum_to_one_and_hit_rate_is_half(chain):
    # Section 3: Switchy, Steady and Sticky all have a long-run hit rate of 50%.
    steps = chain.steps if chain.kind else 1
    m = streak_chain_matrix(Chain(chain.kind, steps, chain.degree))
    n = len(m)
    assert all(sum(row) == pytest.approx(1.0) for row in m)
    pi = [1.0 / n] * n
    for _ in range(4000):
        pi = [sum(pi[i] * m[i][j] for i in range(n)) for j in range(n)]
    hit_mass = sum(pi[j] for j in range(n // 2, n))  # states ending in a hit
    assert hit_mass == pytest.approx(0.5, abs=1e-9)


def test_likelihood_agrees_with_matrix_walk():
    rng = random.Random(1)
    for chain in (SWI, STI, STE, Chain(-1, 2, 0.7), Chain(1, 6, 0.8)):
        for _ in range(30):
            seq = [rng.randint(0, 1) for _ in range(rng.randint(1, 25))]
            direct = math.exp(log_likelihood(chain, seq))
            via_matrix = sequence_probability_via_matrix(chain, seq)
            assert direct == pytest.approx(via_matrix, rel=1e-12)


def test_likelihoods_of_all_sequences_sum_to_one():
    for chain in (SWI, STI, STE):
        total = sum(
            math.exp(log_likelihood(chain, seq)) for seq in itertools.product((0, 1), repeat=10)
        )
        assert total == pytest.approx(1.0)


def test_steady_likelihood_is_half_to_the_n():
    assert math.exp(log_likelihood(STE, [1, 0, 0, 1, 1])) == pytest.approx(0.5**5)


def test_section_3_1_worked_examples():
    # P(continue) = 0.4(0.2) + 0.4(0.5) + 0.2(0.8) = 0.44 after a streak of 3 with (0.4, 0.4, 0.2).
    sp = space_with_prior((0.4, 0.4, 0.2))
    assert predict_continue(sp, sp.prior, 3) == pytest.approx(0.44)
    # With (0.1, 0.85, 0.05) the paper gives 0.485.
    sp = space_with_prior((0.1, 0.85, 0.05))
    assert predict_continue(sp, sp.prior, 3) == pytest.approx(0.485)


def test_section_2_balance_of_uncertainty():
    # (0.2, 0.6, 0.2): balanced, neither; (0.3, 0.6, 0.1): switch; (0.1, 0.6, 0.3): continuation.
    for k in (1, 2, 3, 6):
        bal = space_with_prior((0.2, 0.6, 0.2))
        assert predict_continue(bal, bal.prior, k) == pytest.approx(0.5)
        gam = space_with_prior((0.3, 0.6, 0.1))
        assert predict_continue(gam, gam.prior, k) < 0.5
        hot = space_with_prior((0.1, 0.6, 0.3))
        assert predict_continue(hot, hot.prior, k) > 0.5


def test_bayes_update_by_hand():
    # After 1,1,1 (one run of three) the likelihoods are
    # Switchy 0.5*0.4*0.3 = 0.06, Steady 0.125, Sticky 0.5*0.6*0.7 = 0.21.
    sp = build_space()
    post = posterior(sp, [1, 1, 1])
    z = 0.06 + 0.125 + 0.21
    assert post == pytest.approx([0.06 / z, 0.125 / z, 0.21 / z])


def test_no_data_posterior_is_the_prior():
    sp = build_space(p_steady=0.2, switchy_share=0.25)
    assert posterior(sp, []) == pytest.approx(list(sp.prior))


def test_sequence_dependence_qualitatively():
    # Section 5.3: many switches favour Switchy, few switches favour Sticky.
    sp = build_space()
    many = class_totals(sp, posterior(sp, [1, 0, 1, 0, 1, 1, 0, 1]))
    few = class_totals(sp, posterior(sp, [1, 1, 1, 1, 1, 0, 0, 0]))
    assert many["switchy"] > many["sticky"]
    assert few["sticky"] > few["switchy"]


def test_end_streak():
    assert end_streak([]) == 0
    assert end_streak([1]) == 1
    assert end_streak([0, 1, 1, 1]) == 3
    assert end_streak([1, 1, 0]) == 1
    assert end_streak([0, 0, 0, 0]) == 4


def test_build_space_defaults_are_uniform():
    sp = build_space()
    assert sp.prior == pytest.approx((1 / 3, 1 / 3, 1 / 3))
    assert [c.kind for c in sp.chains] == [-1, 0, 1]
    assert (sp.chains[0].steps, sp.chains[0].degree) == (4, 0.9)


def test_build_space_speed_mixture_is_uniform_over_21():
    sp = build_space(p_steady=1 / 21, speed_mixture=True)
    assert len(sp.chains) == 21
    assert sp.prior == pytest.approx([1 / 21] * 21)
    assert sorted(c.steps for c in sp.chains if c.kind == -1) == list(range(1, 11))


def test_build_space_prior_controls():
    sp = build_space(p_steady=0.4, switchy_share=0.75)
    assert sp.prior == pytest.approx((0.45, 0.4, 0.15))
    with pytest.raises(ValueError):
        build_space(p_steady=1.5)


def test_predict_after_matches_manual_chain_of_steps():
    sp = build_space()
    experience = [1, 0, 0, 1, 0, 1, 1, 0, 1, 0]
    shown = [1, 1, 1, 1]
    r = predict_after(sp, experience, shown)
    ll = [log_likelihood(c, experience) + log_likelihood(c, shown) for c in sp.chains]
    z = sum(math.exp(x) for x in ll) / 3
    manual = [math.exp(x) / 3 / z for x in ll]
    assert r["after_shown"] == pytest.approx(manual)
    assert r["streak"] == 4
    assert r["p_continue"] == pytest.approx(
        sum(m * p_continue(c, 4) for m, c in zip(manual, sp.chains, strict=True))
    )
    assert sum(r["after_experience"]) == pytest.approx(1.0)


def test_more_switchy_experience_means_more_gambler_reasoning():
    sp = build_space()
    switchy_past = [1, 0] * 10
    sticky_past = [1] * 6 + [0] * 7 + [1] * 7
    a = predict_after(sp, switchy_past, [1, 1, 1])["p_continue"]
    b = predict_after(sp, sticky_past, [1, 1, 1])["p_continue"]
    assert a < 0.5 < b


def test_posterior_with_unequal_prior_and_data_matches_bayes_by_hand():
    """Prior (0.2, 0.5, 0.3), 4-step 90% chains, data 1,0,1,0,1 (Section 4, Bayes' rule).

    The first outcome has probability 0.5 under every chain; the four later outcomes are
    switches after a streak of length 1.  Fig. 3: Switchy switches with probability 0.6 there
    (0.5 + 0.4/4), Sticky with 0.4, Steady with 0.5.
    """
    prior = (0.2, 0.5, 0.3)
    like_switchy = 0.5 * 0.6 * 0.6 * 0.6 * 0.6
    like_steady = 0.5 * 0.5 * 0.5 * 0.5 * 0.5
    like_sticky = 0.5 * 0.4 * 0.4 * 0.4 * 0.4
    joint = [
        prior[0] * like_switchy,
        prior[1] * like_steady,
        prior[2] * like_sticky,
    ]
    z = sum(joint)
    expected = [j / z for j in joint]
    assert posterior(space_with_prior(prior), [1, 0, 1, 0, 1]) == pytest.approx(expected, abs=1e-12)
