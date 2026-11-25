"""Reference implementation of the causal-uncertainty model of Dorst (2026)."""

from .experience import (
    Mulberry32,
    crossing_streak,
    exact_experience,
    run_agents,
    shown_sequences,
    steady_sequence,
)
from .model import (
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

__all__ = [
    "Chain",
    "HypothesisSpace",
    "Mulberry32",
    "build_space",
    "class_totals",
    "crossing_streak",
    "end_streak",
    "exact_experience",
    "log_likelihood",
    "p_continue",
    "posterior",
    "predict_after",
    "predict_continue",
    "run_agents",
    "steady_sequence",
    "streak_chain_matrix",
    "shown_sequences",
]
