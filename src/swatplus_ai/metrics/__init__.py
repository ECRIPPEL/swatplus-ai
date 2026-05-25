"""Goodness-of-fit metrics for hydrologic model evaluation.

Public surface is a handful of pure functions over ``(obs, sim)`` arrays
plus a ``classify()`` entry point that maps a metric value to the
Moriasi et al. 2015 performance rating.

All metric functions accept any :class:`numpy.typing.ArrayLike` (lists,
tuples, :class:`numpy.ndarray`, :class:`pandas.Series`). Inputs are cast
to ``float`` and aligned pairwise — a NaN at index ``i`` in either
series drops the pair. Callers are responsible for temporal alignment
before calling; this module does not interpret indices.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from numpy.typing import ArrayLike

__all__ = [
    "Classification",
    "Constituent",
    "MetricName",
    "classify",
    "kling_gupta",
    "nash_sutcliffe",
    "p_factor",
    "pbias",
    "r_factor",
    "r_squared",
]

MetricName = Literal["NSE", "KGE", "PBIAS", "R2"]
Constituent = Literal["streamflow", "sediment", "nitrogen", "phosphorus"]
Classification = Literal["unsatisfactory", "satisfactory", "good", "very_good"]


def _align(obs: ArrayLike, sim: ArrayLike) -> tuple[np.ndarray, np.ndarray]:
    obs_arr = np.asarray(obs, dtype=float)
    sim_arr = np.asarray(sim, dtype=float)
    if obs_arr.shape != sim_arr.shape:
        raise ValueError(
            f"obs and sim must have the same shape; got {obs_arr.shape} vs {sim_arr.shape}"
        )
    if obs_arr.ndim != 1:
        raise ValueError(f"obs and sim must be 1-D arrays; got {obs_arr.ndim}-D")
    valid = ~(np.isnan(obs_arr) | np.isnan(sim_arr))
    obs_clean = obs_arr[valid]
    sim_clean = sim_arr[valid]
    if obs_clean.size == 0:
        raise ValueError("no valid obs/sim pairs after dropping NaNs")
    return obs_clean, sim_clean


def _align3(
    obs: ArrayLike, lower: ArrayLike, upper: ArrayLike
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    obs_arr = np.asarray(obs, dtype=float)
    lo_arr = np.asarray(lower, dtype=float)
    up_arr = np.asarray(upper, dtype=float)
    if not (obs_arr.shape == lo_arr.shape == up_arr.shape):
        raise ValueError(
            "obs, sim_lower, sim_upper must share the same shape; "
            f"got {obs_arr.shape}, {lo_arr.shape}, {up_arr.shape}"
        )
    if obs_arr.ndim != 1:
        raise ValueError(f"inputs must be 1-D arrays; got {obs_arr.ndim}-D")
    valid = ~(np.isnan(obs_arr) | np.isnan(lo_arr) | np.isnan(up_arr))
    obs_clean = obs_arr[valid]
    lo_clean = lo_arr[valid]
    up_clean = up_arr[valid]
    if obs_clean.size == 0:
        raise ValueError("no valid obs/lower/upper triples after dropping NaNs")
    return obs_clean, lo_clean, up_clean


def nash_sutcliffe(obs: ArrayLike, sim: ArrayLike) -> float:
    """Nash-Sutcliffe efficiency.

    ``NSE = 1 - Σ(obs - sim)² / Σ(obs - mean(obs))²``

    Range: ``(-∞, 1]``. 1 = perfect fit; 0 = model as good as predicting
    the mean of observations; negative = worse than the mean.
    """
    obs_a, sim_a = _align(obs, sim)
    denom = float(np.sum((obs_a - obs_a.mean()) ** 2))
    if denom == 0.0:
        raise ValueError("obs has zero variance; NSE is undefined")
    num = float(np.sum((obs_a - sim_a) ** 2))
    return 1.0 - num / denom


def kling_gupta(
    obs: ArrayLike,
    sim: ArrayLike,
    *,
    variant: Literal["2009", "2012"] = "2009",
) -> float:
    """Kling-Gupta efficiency.

    ``variant="2009"`` — Gupta et al. 2009:
        ``KGE = 1 - √((r-1)² + (α-1)² + (β-1)²)``
        where ``α = σ(sim)/σ(obs)`` and ``β = μ(sim)/μ(obs)``.

    ``variant="2012"`` — Kling et al. 2012, a.k.a. KGE':
        ``γ = CV(sim)/CV(obs)`` replaces ``α`` (CV = σ/μ), which
        decouples variability bias from mean bias.

    Range: ``(-∞, 1]``. 1 = perfect.
    """
    obs_a, sim_a = _align(obs, sim)
    obs_mean = float(obs_a.mean())
    sim_mean = float(sim_a.mean())
    obs_std = float(obs_a.std(ddof=0))
    sim_std = float(sim_a.std(ddof=0))
    if obs_std == 0.0:
        raise ValueError("obs has zero variance; KGE is undefined")
    if obs_mean == 0.0:
        raise ValueError("obs has zero mean; KGE is undefined")
    # Pearson correlation
    obs_c = obs_a - obs_mean
    sim_c = sim_a - sim_mean
    denom_r = float(np.sqrt(np.sum(obs_c**2) * np.sum(sim_c**2)))
    if denom_r == 0.0:
        raise ValueError("sim has zero variance; KGE correlation is undefined")
    r = float(np.sum(obs_c * sim_c) / denom_r)
    beta = sim_mean / obs_mean
    if variant == "2009":
        alpha = sim_std / obs_std
        term = (r - 1.0) ** 2 + (alpha - 1.0) ** 2 + (beta - 1.0) ** 2
    else:
        if sim_mean == 0.0:
            raise ValueError("sim has zero mean; KGE' (2012) gamma is undefined")
        cv_obs = obs_std / obs_mean
        cv_sim = sim_std / sim_mean
        gamma = cv_sim / cv_obs
        term = (r - 1.0) ** 2 + (gamma - 1.0) ** 2 + (beta - 1.0) ** 2
    return 1.0 - float(np.sqrt(term))


def pbias(obs: ArrayLike, sim: ArrayLike) -> float:
    """Percent bias.

    ``PBIAS = 100 · Σ(obs - sim) / Σ(obs)``  (percent, signed)

    0 = no bias. Positive = model underestimates. Negative = model
    overestimates. Moriasi 2015 classifies by absolute value.
    """
    obs_a, sim_a = _align(obs, sim)
    denom = float(np.sum(obs_a))
    if denom == 0.0:
        raise ValueError("Σ(obs) is zero; PBIAS is undefined")
    return 100.0 * float(np.sum(obs_a - sim_a)) / denom


def r_squared(obs: ArrayLike, sim: ArrayLike) -> float:
    """Coefficient of determination (squared Pearson correlation).

    Range: ``[0, 1]``. 1 = obs and sim are perfectly linearly related
    (including affine transforms). R² = 1 does not imply unbiased sim —
    pair with NSE or PBIAS for completeness.
    """
    obs_a, sim_a = _align(obs, sim)
    obs_c = obs_a - obs_a.mean()
    sim_c = sim_a - sim_a.mean()
    denom = float(np.sqrt(np.sum(obs_c**2) * np.sum(sim_c**2)))
    if denom == 0.0:
        raise ValueError("obs or sim has zero variance; R² is undefined")
    r = float(np.sum(obs_c * sim_c) / denom)
    return r * r


def p_factor(obs: ArrayLike, sim_lower: ArrayLike, sim_upper: ArrayLike) -> float:
    """Fraction of observations bracketed by an uncertainty band.

    ``P-factor = #{obs_i ∈ [lower_i, upper_i]} / N``

    Range: ``[0, 1]``. SWAT-CUP convention targets ``≥ 0.7`` for flow,
    ``≥ 0.6`` for sediment/nutrients. Pair with :func:`r_factor` — a
    high P-factor with a wide band is not evidence of skill.
    """
    obs_a, lo_a, up_a = _align3(obs, sim_lower, sim_upper)
    inside = (obs_a >= lo_a) & (obs_a <= up_a)
    return float(inside.sum()) / float(obs_a.size)


def r_factor(obs: ArrayLike, sim_lower: ArrayLike, sim_upper: ArrayLike) -> float:
    """Average uncertainty band width normalized by σ(obs).

    ``R-factor = mean(upper - lower) / σ(obs)``

    Range: ``[0, ∞)``. SWAT-CUP convention targets ``≤ 1.5``. Lower =
    tighter bands. Diverges when obs has zero variance.
    """
    obs_a, lo_a, up_a = _align3(obs, sim_lower, sim_upper)
    obs_std = float(obs_a.std(ddof=0))
    if obs_std == 0.0:
        raise ValueError("obs has zero variance; R-factor is undefined")
    return float(np.mean(up_a - lo_a)) / obs_std


# --- Moriasi 2015 classification ---------------------------------------------
#
# Thresholds per Moriasi et al. 2015 (Transactions of the ASABE 58(6):
# 1763–1785), Table 6. Each entry is a (very_good_min, good_min,
# satisfactory_min) triple applied to the metric; values strictly below
# satisfactory_min are "unsatisfactory". PBIAS is classified on |PBIAS|.
#
# Only streamflow and sediment are shipped in this slice. Nitrogen,
# phosphorus, and the KGE metric are intentionally deferred — their
# thresholds vary by constituent and by publication, and promoting them
# should happen alongside the rule port that consumes them, not here.

_THRESHOLDS_MORIASI_2015: dict[tuple[MetricName, Constituent], tuple[float, float, float]] = {
    # streamflow
    ("NSE", "streamflow"): (0.80, 0.70, 0.50),
    ("R2", "streamflow"): (0.85, 0.75, 0.60),
    ("PBIAS", "streamflow"): (5.0, 10.0, 15.0),
    # sediment
    ("NSE", "sediment"): (0.80, 0.70, 0.50),
    ("R2", "sediment"): (0.80, 0.65, 0.40),
    ("PBIAS", "sediment"): (10.0, 15.0, 20.0),
}


def classify(
    metric: MetricName,
    value: float,
    *,
    constituent: Constituent = "streamflow",
    version: Literal["2015"] = "2015",
) -> Classification:
    """Map a metric value to a Moriasi performance rating.

    Parameters
    ----------
    metric
        One of ``"NSE"``, ``"KGE"``, ``"PBIAS"``, ``"R2"``.
    value
        The computed metric value. For PBIAS, the sign is ignored
        (classification is on absolute value).
    constituent
        ``"streamflow"`` (default) or ``"sediment"``. Nitrogen and
        phosphorus are not yet implemented — add them alongside the
        rule port that cites them.
    version
        Only ``"2015"`` is supported in this release.

    Raises
    ------
    NotImplementedError
        For KGE (no canonical threshold table) or for nitrogen /
        phosphorus constituents.
    ValueError
        For unknown metric / constituent / version labels.
    """
    if version != "2015":
        raise ValueError(f"unsupported Moriasi version: {version!r} (expected '2015')")
    if metric == "KGE":
        raise NotImplementedError(
            "Moriasi 2015 does not tabulate KGE thresholds; classify KGE against "
            "a source-cited rule in the consumer slice rather than here"
        )
    if constituent in ("nitrogen", "phosphorus"):
        raise NotImplementedError(
            f"constituent={constituent!r} thresholds are deferred until the N/P "
            "rule port slice verifies values against Moriasi 2015 Table 6"
        )
    key = (metric, constituent)
    if key not in _THRESHOLDS_MORIASI_2015:
        raise ValueError(
            f"no Moriasi 2015 threshold for metric={metric!r}, constituent={constituent!r}"
        )
    vg_min, good_min, sat_min = _THRESHOLDS_MORIASI_2015[key]
    compare = abs(value) if metric == "PBIAS" else value
    if metric == "PBIAS":
        # PBIAS: smaller |value| is better; boundaries are upper exclusive.
        if compare < vg_min:
            return "very_good"
        if compare < good_min:
            return "good"
        if compare < sat_min:
            return "satisfactory"
        return "unsatisfactory"
    # NSE, R²: larger value is better; boundaries are lower exclusive.
    if compare > vg_min:
        return "very_good"
    if compare > good_min:
        return "good"
    if compare > sat_min:
        return "satisfactory"
    return "unsatisfactory"
