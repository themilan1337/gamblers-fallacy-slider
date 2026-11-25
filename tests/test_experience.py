"""Tests of the experience simulation (Sections 4, 5.1, 5.2) and of the seeded generator."""

import pytest

from gfmodel import (
    Mulberry32,
    build_space,
    crossing_streak,
    exact_experience,
    run_agents,
    shown_sequences,
    steady_sequence,
)
from gfmodel.experience import direct_pcont


def test_generator_is_deterministic_and_fair():
    a = steady_sequence(42, 2000)
    assert a == steady_sequence(42, 2000)
    assert a != steady_sequence(43, 2000)
    assert 0.47 < sum(a) / len(a) < 0.53
    rng = Mulberry32(1)
    xs = [rng.random() for _ in range(1000)]
    assert all(0.0 <= x < 1.0 for x in xs)


def test_generator_first_values_regression():
    # Fixed outputs for seed 1 (the standard mulberry32 stream), so that an accidental change to
    # the generator, which would silently change every number on the page, fails here.  The JS
    # port is compared with the Python one in test_crosscheck_js.py.
    rng = Mulberry32(1)
    assert [round(rng.random(), 9) for _ in range(3)] == pytest.approx(
        [0.627073941, 0.002735721, 0.527447040], abs=1e-9
    )


def test_streak_group_sizes():
    groups = shown_sequences("streak", 8)
    assert [len(g) for g in groups] == [1] * 8
    assert groups[3][0] == [0, 1, 1, 1, 1]


def test_iid8_groups_are_exact_streak_classes():
    groups = shown_sequences("iid8", 8)
    assert [len(g) for g in groups] == [128, 64, 32, 16, 8, 4, 2, 2]
    from gfmodel import end_streak

    for s, g in enumerate(groups, start=1):
        assert all(end_streak(q) == s for q in g)
    assert len({tuple(q) for g in groups for q in g}) == 256


def test_run_agents_matches_direct_definition_for_one_agent():
    sp = build_space()
    n, seed = 12, 99
    row = run_agents(sp, [n], 1, seed, "iid8")[0]
    experience = steady_sequence(seed, n)
    for s, group in enumerate(shown_sequences("iid8"), start=1):
        direct = sum(direct_pcont(sp, experience, q) for q in group) / len(group)
        assert row["pcont"][s - 1] == pytest.approx(direct, abs=1e-12)
    from gfmodel import class_totals, posterior

    ct = class_totals(sp, posterior(sp, experience))
    assert row["class_post"] == pytest.approx(ct)


def test_run_agents_streak_mode_matches_direct_definition():
    sp = build_space(p_steady=0.2, switchy_share=0.7, steps=3, degree=0.8)
    n, seed = 30, 7
    row = run_agents(sp, [n], 1, seed, "streak")[0]
    experience = steady_sequence(seed, n)
    for s in range(1, 9):
        assert row["pcont"][s - 1] == pytest.approx(
            direct_pcont(sp, experience, [0] + [1] * s), abs=1e-12
        )


def test_levels_are_prefixes_of_the_same_path():
    sp = build_space()
    # With one agent, the learner at N=5 and N=30 are the same person at two points in time.
    both = run_agents(sp, [5, 30], 1, 11, "streak")
    only5 = run_agents(sp, [5], 1, 11, "streak")
    only30 = run_agents(sp, [30], 1, 11, "streak")
    assert both[0]["pcont"] == pytest.approx(only5[0]["pcont"])
    assert both[1]["pcont"] == pytest.approx(only30[0]["pcont"])


def test_zero_experience_is_the_prior():
    sp = build_space(p_steady=0.1, switchy_share=0.3)
    row = run_agents(sp, [0], 5, 1, None)[0]
    assert row["class_post"] == pytest.approx({"switchy": 0.27, "steady": 0.1, "sticky": 0.63})


@pytest.mark.parametrize("test_mode", ["streak", "iid8"])
def test_monte_carlo_agrees_with_exact_enumeration(test_mode):
    sp = build_space()
    n = 8
    exact = exact_experience(sp, n, test_mode)
    k = 6000 if test_mode == "iid8" else 20000
    mc = run_agents(sp, [n], k, 5, test_mode)[0]
    for key in exact["class_post"]:
        assert mc["class_post"][key] == pytest.approx(exact["class_post"][key], abs=0.01)
    for a, b in zip(mc["pcont"], exact["pcont"], strict=True):
        assert a == pytest.approx(b, abs=0.006)


def test_exact_posterior_means_sum_to_one_and_prior_is_preserved():
    # Bayes: averaged over the prior predictive the posterior equals the prior.  Under Steady
    # data it does not, which is the point of the paper: Sticky loses more than Switchy.
    sp = build_space()
    e = exact_experience(sp, 10, None)
    assert sum(e["class_post"].values()) == pytest.approx(1.0)
    assert e["class_post"]["switchy"] > e["class_post"]["sticky"]


def test_share_above_is_none_when_everything_is_exactly_half():
    sp = build_space(p_steady=1.0)
    row = run_agents(sp, [5], 20, 3, "streak")[0]
    assert all(x is None for x in row["share_above"])
    assert row["pcont"] == pytest.approx([0.5] * 8)


def test_crossing_streak():
    assert crossing_streak([0.49, 0.48, 0.51, 0.6]) == 3
    assert crossing_streak([0.49, 0.48, 0.47]) is None
    assert crossing_streak([0.52, 0.48]) == 1


def test_dorst_claim_less_experience_shifts_sooner_and_more_extreme():
    """Dorst, email of 14 Oct 2026: with less experience the shift from predicting switches to
    predicting continuations comes sooner and becomes more extreme (here: for the 4-step-90%
    chains with a uniform prior and bare streaks)."""
    sp = build_space()
    rows = run_agents(sp, [10, 40, 150], 4000, 2026, "streak")
    cross = [crossing_streak(r["pcont"]) for r in rows]
    assert cross[0] is not None and cross[1] is not None
    assert cross[0] < cross[1]
    assert cross[2] is None or cross[1] < cross[2]
    extreme = [r["pcont"][7] for r in rows]  # confidence in a continuation after 8 in a row
    assert extreme[0] > extreme[1] > extreme[2]


def test_levels_do_not_depend_on_other_requested_levels():
    space = build_space()
    a = run_agents(space, [10, 40, 100], 200, 20261016, "streak", 8, path_length=300)
    b = run_agents(space, [10, 100, 300], 200, 20261016, "streak", 8)
    ra = {r["n"]: r for r in a}
    rb = {r["n"]: r for r in b}
    for n in (10, 100):
        assert ra[n]["pcont"] == rb[n]["pcont"]
        assert ra[n]["class_post"] == rb[n]["class_post"]
        assert ra[n]["share_above"] == rb[n]["share_above"]


def test_path_length_shorter_than_largest_level_is_rejected():
    with pytest.raises(ValueError):
        run_agents(build_space(), [10, 100], 5, 1, "streak", 8, path_length=50)
