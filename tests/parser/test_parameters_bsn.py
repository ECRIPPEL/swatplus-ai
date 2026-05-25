"""Tests for ``swatplus_ai.parser.inputs.parameters_bsn``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.diagnostics.drift import DriftRegistry
from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.parameters_bsn import ParametersBsn, parse_parameters_bsn


def test_parse_minimal(minimal_project: Path) -> None:
    p = parse_parameters_bsn(minimal_project / "parameters.bsn")
    assert isinstance(p, ParametersBsn)
    assert p.lai_noevap == pytest.approx(3.0)
    assert p.surq_lag == pytest.approx(4.0)
    assert p.adj_pkrt_sed == pytest.approx(484.0)
    assert p.msk_co1 == pytest.approx(0.75)
    assert p.co2 == pytest.approx(400.0)
    assert p.day_lag_max == 0
    assert p.igen == 0


def test_parse_uru(uru_project: Path) -> None:
    p = parse_parameters_bsn(uru_project / "parameters.bsn")
    # Basic domain sanity: CO2 concentration in the atmosphere is a
    # positive float of realistic magnitude.
    assert p.co2 > 0.0


def test_null_sediment_coefficients_accepted(tmp_path: Path) -> None:
    """SWAT+ editor v3.0+ writes literal ``null`` for ``lin_sed`` /
    ``exp_sed`` when the user hasn't customised the sediment model; the
    parser must accept the literal and surface ``None``."""
    p = tmp_path / "parameters.bsn"
    p.write_text(
        "parameters.bsn: synthetic\n"
        "lai_noevap sw_init surq_lag adj_pkrt adj_pkrt_sed lin_sed exp_sed "
        "orgn_min n_uptake p_uptake n_perc p_perc p_soil p_avail rsd_decomp "
        "pest_perc msk_co1 msk_co2 msk_x nperco_lchtile evap_adj scoef "
        "denit_exp denit_frac man_bact adj_uhyd cn_froz dorm_hr plaps tlaps "
        "n_fix_max rsd_decay rsd_cover urb_init_abst petco_pmpt uhyd_alpha "
        "splash rill surq_exp cov_mgt cha_d50 co2 day_lag_max igen\n"
        "3.0 0.0 4.0 1.0 484.0 null null 0.0 20.0 20.0 0.1 10.0 175.0 0.4 0.05 "
        "0.5 0.75 0.25 0.2 0.5 0.6 1.0 1.4 1.3 0.15 0.0 0.0 0.0 0.0 0.0 20.0 "
        "0.01 0.3 1.0 1.0 5.0 1.0 0.7 1.2 0.03 50.0 400.0 0 0\n"
    )
    parsed = parse_parameters_bsn(p)
    assert parsed.lin_sed is None
    assert parsed.exp_sed is None
    assert parsed.adj_pkrt_sed == pytest.approx(484.0)


def test_missing_required_column_raises(tmp_path: Path) -> None:
    p = tmp_path / "parameters.bsn"
    p.write_text(
        "parameters.bsn: synthetic\n"
        "lai_noevap sw_init NOPE\n"  # header too short / wrong
        "3.0 0.0 0.0\n"
    )
    with pytest.raises(ParseError, match="missing expected column"):
        parse_parameters_bsn(p)


def test_wrong_column_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "parameters.bsn"
    p.write_text(
        "parameters.bsn: synthetic\n"
        "lai_noevap sw_init surq_lag adj_pkrt adj_pkrt_sed lin_sed exp_sed "
        "orgn_min n_uptake p_uptake n_perc p_perc p_soil p_avail rsd_decomp "
        "pest_perc msk_co1 msk_co2 msk_x nperco_lchtile evap_adj scoef "
        "denit_exp denit_frac man_bact adj_uhyd cn_froz dorm_hr plaps tlaps "
        "n_fix_max rsd_decay rsd_cover urb_init_abst petco_pmpt uhyd_alpha "
        "splash rill surq_exp cov_mgt cha_d50 co2 day_lag_max igen\n"
        "3.0 0.0\n"  # way too few values
    )
    with pytest.raises(ParseError, match=r"expected 44 values"):
        parse_parameters_bsn(p)


def test_day_lag_max_as_float_accepted_and_drift_recorded(tmp_path: Path) -> None:
    """Editor < v3.1.0 writes ``day_lag_max`` as ``0.00000`` — parser accepts
    (Fortran list-directed read tolerates it silently) and records a
    ``tool_bug`` drift with ``fixed_in_version='3.1.0'`` so the setup rule
    can surface an upgrade hint."""
    p = tmp_path / "parameters.bsn"
    p.write_text(
        "parameters.bsn: synthetic pre-v3.1.0 Editor\n"
        "lai_noevap sw_init surq_lag adj_pkrt adj_pkrt_sed lin_sed exp_sed "
        "orgn_min n_uptake p_uptake n_perc p_perc p_soil p_avail rsd_decomp "
        "pest_perc msk_co1 msk_co2 msk_x nperco_lchtile evap_adj scoef "
        "denit_exp denit_frac man_bact adj_uhyd cn_froz dorm_hr plaps tlaps "
        "n_fix_max rsd_decay rsd_cover urb_init_abst petco_pmpt uhyd_alpha "
        "splash rill surq_exp cov_mgt cha_d50 co2 day_lag_max igen\n"
        "3.0 0.0 4.0 1.0 484.0 0.0 0.0 0.0 20.0 20.0 0.1 10.0 175.0 0.4 0.05 "
        "0.5 0.75 0.25 0.2 0.5 0.6 1.0 1.4 1.3 0.15 0.0 0.0 0.0 0.0 0.0 20.0 "
        "0.01 0.3 1.0 1.0 5.0 1.0 0.7 1.2 0.03 50.0 400.0 0.00000 0\n"
    )
    with DriftRegistry() as reg:
        parsed = parse_parameters_bsn(p)
    assert parsed.day_lag_max == 0
    drifts = reg.by_file("parameters.bsn")
    assert len(drifts) == 1
    d = drifts[0]
    assert d.column == "day_lag_max"
    assert d.observed == "0.00000"
    assert d.category == "tool_bug"
    assert d.fixed_in_version == "3.1.0"
    assert d.source_ref.startswith("https://github.com/swat-model/swatplus/")


def test_day_lag_max_as_fractional_float_still_raises(tmp_path: Path) -> None:
    """``0.5`` must still raise — that's a genuine spec violation, not the
    known ``0.00000`` writer bug. The tolerant path only covers whole-number
    floats."""
    p = tmp_path / "parameters.bsn"
    p.write_text(
        "parameters.bsn: synthetic\n"
        "lai_noevap sw_init surq_lag adj_pkrt adj_pkrt_sed lin_sed exp_sed "
        "orgn_min n_uptake p_uptake n_perc p_perc p_soil p_avail rsd_decomp "
        "pest_perc msk_co1 msk_co2 msk_x nperco_lchtile evap_adj scoef "
        "denit_exp denit_frac man_bact adj_uhyd cn_froz dorm_hr plaps tlaps "
        "n_fix_max rsd_decay rsd_cover urb_init_abst petco_pmpt uhyd_alpha "
        "splash rill surq_exp cov_mgt cha_d50 co2 day_lag_max igen\n"
        "3.0 0.0 4.0 1.0 484.0 0.0 0.0 0.0 20.0 20.0 0.1 10.0 175.0 0.4 0.05 "
        "0.5 0.75 0.25 0.2 0.5 0.6 1.0 1.4 1.3 0.15 0.0 0.0 0.0 0.0 0.0 20.0 "
        "0.01 0.3 1.0 1.0 5.0 1.0 0.7 1.2 0.03 50.0 400.0 0.5 0\n"
    )
    with pytest.raises(ParseError, match="expected integer for 'day_lag_max'"):
        parse_parameters_bsn(p)


def test_day_lag_max_as_clean_int_records_no_drift(tmp_path: Path) -> None:
    """Editor v3.1.0+ writes ``0`` (int) — the control case. No drift
    emitted."""
    p = tmp_path / "parameters.bsn"
    p.write_text(
        "parameters.bsn: synthetic post-v3.1.0 Editor\n"
        "lai_noevap sw_init surq_lag adj_pkrt adj_pkrt_sed lin_sed exp_sed "
        "orgn_min n_uptake p_uptake n_perc p_perc p_soil p_avail rsd_decomp "
        "pest_perc msk_co1 msk_co2 msk_x nperco_lchtile evap_adj scoef "
        "denit_exp denit_frac man_bact adj_uhyd cn_froz dorm_hr plaps tlaps "
        "n_fix_max rsd_decay rsd_cover urb_init_abst petco_pmpt uhyd_alpha "
        "splash rill surq_exp cov_mgt cha_d50 co2 day_lag_max igen\n"
        "3.0 0.0 4.0 1.0 484.0 0.0 0.0 0.0 20.0 20.0 0.1 10.0 175.0 0.4 0.05 "
        "0.5 0.75 0.25 0.2 0.5 0.6 1.0 1.4 1.3 0.15 0.0 0.0 0.0 0.0 0.0 20.0 "
        "0.01 0.3 1.0 1.0 5.0 1.0 0.7 1.2 0.03 50.0 400.0 0 0\n"
    )
    with DriftRegistry() as reg:
        parsed = parse_parameters_bsn(p)
    assert parsed.day_lag_max == 0
    assert reg.by_file("parameters.bsn") == ()


def test_non_float_value_raises(tmp_path: Path) -> None:
    p = tmp_path / "parameters.bsn"
    p.write_text(
        "parameters.bsn: synthetic\n"
        "lai_noevap sw_init surq_lag adj_pkrt adj_pkrt_sed lin_sed exp_sed "
        "orgn_min n_uptake p_uptake n_perc p_perc p_soil p_avail rsd_decomp "
        "pest_perc msk_co1 msk_co2 msk_x nperco_lchtile evap_adj scoef "
        "denit_exp denit_frac man_bact adj_uhyd cn_froz dorm_hr plaps tlaps "
        "n_fix_max rsd_decay rsd_cover urb_init_abst petco_pmpt uhyd_alpha "
        "splash rill surq_exp cov_mgt cha_d50 co2 day_lag_max igen\n"
        "XXX 0.0 4.0 1.0 484.0 0.0 0.0 0.0 20.0 20.0 0.1 10.0 175.0 0.4 0.05 "
        "0.5 0.75 0.25 0.2 0.5 0.6 1.0 1.4 1.3 0.15 0.0 0.0 0.0 0.0 0.0 20.0 "
        "0.01 0.3 1.0 1.0 5.0 1.0 0.7 1.2 0.03 50.0 400.0 0 0\n"
    )
    with pytest.raises(ParseError, match="expected float for 'lai_noevap'"):
        parse_parameters_bsn(p)
