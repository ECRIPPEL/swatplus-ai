"""Unit tests for swatplus_ai.metrics.

Test strategy: pin each metric against a hand-computed reference value
on small arrays, plus boundary cases (perfect fit, mean baseline,
zero variance, NaN pairs, length mismatch). Moriasi classification is
parameterised across the boundary values of each published threshold.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from swatplus_ai.metrics import (
    classify,
    kling_gupta,
    nash_sutcliffe,
    p_factor,
    pbias,
    r_factor,
    r_squared,
)

# --- NSE ---------------------------------------------------------------------


def test_nse_perfect_match_is_one() -> None:
    obs = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert nash_sutcliffe(obs, obs) == 1.0


def test_nse_predicting_the_mean_is_zero() -> None:
    obs = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    sim = np.full_like(obs, obs.mean())
    assert nash_sutcliffe(obs, sim) == pytest.approx(0.0)


def test_nse_worse_than_mean_is_negative() -> None:
    obs = [1.0, 2.0, 3.0, 4.0, 5.0]
    sim = [5.0, 4.0, 3.0, 2.0, 1.0]
    assert nash_sutcliffe(obs, sim) < 0.0


def test_nse_hand_computed() -> None:
    # obs mean = 3; denom = (2² + 1² + 0 + 1² + 2²) = 10
    # sim residuals (obs-sim) = [0.5, -0.5, 0, 0.5, -0.5]; num = 1.0
    obs = [1.0, 2.0, 3.0, 4.0, 5.0]
    sim = [0.5, 2.5, 3.0, 3.5, 5.5]
    assert nash_sutcliffe(obs, sim) == pytest.approx(1.0 - 1.0 / 10.0)


def test_nse_zero_variance_obs_raises() -> None:
    with pytest.raises(ValueError, match="zero variance"):
        nash_sutcliffe([5.0, 5.0, 5.0], [1.0, 2.0, 3.0])


# --- KGE ---------------------------------------------------------------------


def test_kge_perfect_match_is_one() -> None:
    obs = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert kling_gupta(obs, obs) == pytest.approx(1.0)


def test_kge_2009_vs_2012_differ_on_biased_sim() -> None:
    # sim has same shape as obs but scaled/shifted, so mean bias ≠ 1 and
    # variance bias ≠ 1 — the two formulations diverge.
    obs = [1.0, 2.0, 3.0, 4.0, 5.0]
    sim = [2.0, 3.0, 5.0, 6.0, 9.0]
    kge_2009 = kling_gupta(obs, sim, variant="2009")
    kge_2012 = kling_gupta(obs, sim, variant="2012")
    assert kge_2009 != pytest.approx(kge_2012)


def test_kge_zero_obs_variance_raises() -> None:
    with pytest.raises(ValueError, match="zero variance"):
        kling_gupta([5.0, 5.0, 5.0], [1.0, 2.0, 3.0])


def test_kge_zero_obs_mean_raises() -> None:
    with pytest.raises(ValueError, match="zero mean"):
        kling_gupta([-1.0, 0.0, 1.0], [1.0, 2.0, 3.0])


def test_kge2012_zero_sim_mean_raises() -> None:
    with pytest.raises(ValueError, match="zero mean"):
        kling_gupta([1.0, 2.0, 3.0], [-1.0, 0.0, 1.0], variant="2012")


# --- PBIAS -------------------------------------------------------------------


def test_pbias_perfect_match_is_zero() -> None:
    obs = [10.0, 20.0, 30.0]
    assert pbias(obs, obs) == pytest.approx(0.0)


def test_pbias_positive_when_sim_underestimates() -> None:
    # sim = 0.5 × obs  ⇒  Σ(obs - sim) = 0.5·Σobs  ⇒  PBIAS = 50
    obs = [10.0, 20.0, 30.0]
    sim = [5.0, 10.0, 15.0]
    assert pbias(obs, sim) == pytest.approx(50.0)


def test_pbias_negative_when_sim_overestimates() -> None:
    obs = [10.0, 20.0, 30.0]
    sim = [15.0, 30.0, 45.0]
    assert pbias(obs, sim) == pytest.approx(-50.0)


def test_pbias_zero_sum_obs_raises() -> None:
    with pytest.raises(ValueError, match="Σ\\(obs\\) is zero"):
        pbias([1.0, -1.0], [0.0, 0.0])


# --- R² ----------------------------------------------------------------------


def test_r_squared_perfect_linear_transform_is_one() -> None:
    obs = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    sim = 2.0 * obs + 3.0
    assert r_squared(obs, sim) == pytest.approx(1.0)


def test_r_squared_independent_inputs_is_low() -> None:
    rng = np.random.default_rng(seed=42)
    obs = rng.standard_normal(500)
    sim = rng.standard_normal(500)
    assert r_squared(obs, sim) < 0.05


def test_r_squared_zero_variance_raises() -> None:
    with pytest.raises(ValueError, match="zero variance"):
        r_squared([5.0, 5.0, 5.0], [1.0, 2.0, 3.0])


# --- P-factor / R-factor -----------------------------------------------------


def test_p_factor_all_inside_is_one() -> None:
    obs = [1.0, 2.0, 3.0]
    lo = [0.0, 1.0, 2.0]
    up = [2.0, 3.0, 4.0]
    assert p_factor(obs, lo, up) == 1.0


def test_p_factor_all_outside_is_zero() -> None:
    obs = [5.0, 5.0, 5.0]
    lo = [0.0, 0.0, 0.0]
    up = [1.0, 1.0, 1.0]
    assert p_factor(obs, lo, up) == 0.0


def test_p_factor_partial() -> None:
    obs = [1.0, 5.0, 2.0, 10.0]
    lo = [0.0, 0.0, 0.0, 0.0]
    up = [2.0, 2.0, 2.0, 2.0]
    assert p_factor(obs, lo, up) == pytest.approx(0.5)


def test_p_factor_boundary_inclusive() -> None:
    # obs values sitting exactly on the band edges count as inside.
    obs = [0.0, 2.0]
    lo = [0.0, 0.0]
    up = [2.0, 2.0]
    assert p_factor(obs, lo, up) == 1.0


def test_r_factor_band_width_over_obs_std() -> None:
    obs = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    # constant band width = 2 everywhere
    lo = obs - 1.0
    up = obs + 1.0
    expected = 2.0 / float(obs.std(ddof=0))
    assert r_factor(obs, lo, up) == pytest.approx(expected)


def test_r_factor_zero_obs_variance_raises() -> None:
    with pytest.raises(ValueError, match="zero variance"):
        r_factor([5.0, 5.0], [4.0, 4.0], [6.0, 6.0])


# --- Alignment guardrails ----------------------------------------------------


def test_length_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="same shape"):
        nash_sutcliffe([1.0, 2.0, 3.0], [1.0, 2.0])


def test_nan_pairs_are_dropped() -> None:
    # A NaN at index i in either series should drop the pair entirely,
    # so NSE on [1,2,3] vs [1,2,3] (after drop) is 1.0.
    obs = [1.0, 2.0, float("nan"), 3.0]
    sim = [1.0, float("nan"), 100.0, 3.0]
    assert nash_sutcliffe(obs, sim) == 1.0


def test_empty_after_nan_drop_raises() -> None:
    with pytest.raises(ValueError, match="no valid"):
        nash_sutcliffe([float("nan"), float("nan")], [1.0, 2.0])


def test_non_1d_raises() -> None:
    obs = np.ones((3, 3))
    sim = np.ones((3, 3))
    with pytest.raises(ValueError, match="1-D"):
        nash_sutcliffe(obs, sim)


def test_accepts_pandas_series() -> None:
    pd = pytest.importorskip("pandas")
    obs = pd.Series([1.0, 2.0, 3.0])
    sim = pd.Series([1.0, 2.0, 3.0])
    assert nash_sutcliffe(obs, sim) == 1.0


def test_p_factor_shape_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="same shape"):
        p_factor([1.0, 2.0], [0.0, 0.0, 0.0], [2.0, 2.0, 2.0])


# --- Moriasi classification --------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        (0.81, "very_good"),
        (0.80, "good"),  # boundary: strictly above goes to VG
        (0.75, "good"),
        (0.70, "satisfactory"),
        (0.55, "satisfactory"),
        (0.50, "unsatisfactory"),
        (0.40, "unsatisfactory"),
        (-0.5, "unsatisfactory"),
    ],
)
def test_classify_streamflow_nse(value: float, expected: str) -> None:
    assert classify("NSE", value, constituent="streamflow") == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (0.86, "very_good"),
        (0.80, "good"),
        (0.75, "satisfactory"),
        (0.65, "satisfactory"),
        (0.60, "unsatisfactory"),
        (0.30, "unsatisfactory"),
    ],
)
def test_classify_streamflow_r2(value: float, expected: str) -> None:
    assert classify("R2", value, constituent="streamflow") == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (2.0, "very_good"),
        (-2.0, "very_good"),  # sign-insensitive
        (5.0, "good"),
        (-9.9, "good"),
        (10.0, "satisfactory"),
        (14.9, "satisfactory"),
        (15.0, "unsatisfactory"),
        (-50.0, "unsatisfactory"),
    ],
)
def test_classify_streamflow_pbias(value: float, expected: str) -> None:
    assert classify("PBIAS", value, constituent="streamflow") == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (0.85, "very_good"),
        (0.70, "good"),
        (0.50, "satisfactory"),
        (0.40, "unsatisfactory"),
    ],
)
def test_classify_sediment_r2(value: float, expected: str) -> None:
    assert classify("R2", value, constituent="sediment") == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (5.0, "very_good"),
        (12.0, "good"),
        (18.0, "satisfactory"),
        (25.0, "unsatisfactory"),
    ],
)
def test_classify_sediment_pbias(value: float, expected: str) -> None:
    assert classify("PBIAS", value, constituent="sediment") == expected


def test_classify_kge_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="KGE"):
        classify("KGE", 0.9, constituent="streamflow")


def test_classify_nitrogen_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="nitrogen"):
        classify("NSE", 0.8, constituent="nitrogen")


def test_classify_phosphorus_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="phosphorus"):
        classify("NSE", 0.8, constituent="phosphorus")


def test_classify_unsupported_version_raises() -> None:
    with pytest.raises(ValueError, match="unsupported Moriasi version"):
        classify("NSE", 0.8, version="2007")  # type: ignore[arg-type]


# --- Sanity: module exports what __init__ declares ---------------------------


def test_public_api_is_importable() -> None:
    import swatplus_ai.metrics as m

    for name in m.__all__:
        assert hasattr(m, name), f"metrics.__all__ lists {name!r} but it's not exported"


def test_kge_perfect_is_one_not_inf() -> None:
    # Regression: if the zero-variance branch fires on a perfect match,
    # we'd raise instead of returning 1.0. Guard the happy path.
    obs = np.array([1.0, 2.0, 3.0, 4.0])
    assert math.isfinite(kling_gupta(obs, obs))
