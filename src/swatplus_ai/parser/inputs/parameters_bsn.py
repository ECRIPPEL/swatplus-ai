"""Parser for ``parameters.bsn`` — SWAT+ basin-wide numerical parameters.

Single-row file (like ``codes.bsn``): title, 44-column header, one
value row. 42 columns are floats; the last two (``day_lag_max``,
``igen``) are integers.

These are the global calibration knobs — the knobs a user tunes
against observed discharge/WB data — so the parser exposes them as
individual typed fields rather than a bag of values.

``lin_sed`` / ``exp_sed`` can be written as literal ``null`` by
SWAT+ editor v3.0+ when the user leaves the sediment model at defaults;
both fields are therefore typed ``float | None``.
"""

from __future__ import annotations

from pathlib import Path

from swatplus_ai.diagnostics.drift import DriftRecord, record_drift
from swatplus_ai.parser._base import (
    LineReader,
    ParseError,
    expect_header_permissive,
    parse_float,
    parse_int,
    parse_int_tolerant,
    parse_nullable_float,
    record_unknown_columns,
    validate_or_raise,
)
from swatplus_ai.parser.models import ParsedFile

# Editor < v3.1.0 wrote ``day_lag_max`` as ``0.00000`` (float), fixed in
# v3.1.0 per the SWAT+ Editor changelog. Fortran list-directed read
# tolerates this silently, so the bug is observable only on the Python
# side. Permalink to the canonical Fortran type (``day_lag_mx`` is the
# Fortran-internal name — same column, shortened).
_DAY_LAG_MAX_SOURCE_REF = "https://github.com/swat-model/swatplus/blob/main/src/basin_module.f90"
_DAY_LAG_MAX_FIXED_IN = "3.1.0"

_FLOAT_FIELDS: tuple[str, ...] = (
    "lai_noevap",
    "sw_init",
    "surq_lag",
    "adj_pkrt",
    "adj_pkrt_sed",
    "lin_sed",
    "exp_sed",
    "orgn_min",
    "n_uptake",
    "p_uptake",
    "n_perc",
    "p_perc",
    "p_soil",
    "p_avail",
    "rsd_decomp",
    "pest_perc",
    "msk_co1",
    "msk_co2",
    "msk_x",
    "nperco_lchtile",
    "evap_adj",
    "scoef",
    "denit_exp",
    "denit_frac",
    "man_bact",
    "adj_uhyd",
    "cn_froz",
    "dorm_hr",
    "plaps",
    "tlaps",
    "n_fix_max",
    "rsd_decay",
    "rsd_cover",
    "urb_init_abst",
    "petco_pmpt",
    "uhyd_alpha",
    "splash",
    "rill",
    "surq_exp",
    "cov_mgt",
    "cha_d50",
    "co2",
)

_INT_FIELDS: tuple[str, ...] = ("day_lag_max", "igen")

# SWAT+ editor v3.0+ writes these as literal ``null`` when the sediment
# submodel is at defaults (observed in rev.61.0.1 projects).
_NULLABLE_FLOAT_FIELDS: frozenset[str] = frozenset({"lin_sed", "exp_sed"})

_HEADER: tuple[str, ...] = _FLOAT_FIELDS + _INT_FIELDS
_FILE = "parameters.bsn"


class ParametersBsn(ParsedFile):
    """Contents of ``parameters.bsn``: one record of basin-wide parameters."""

    lai_noevap: float
    sw_init: float
    surq_lag: float
    adj_pkrt: float
    adj_pkrt_sed: float
    lin_sed: float | None
    exp_sed: float | None
    orgn_min: float
    n_uptake: float
    p_uptake: float
    n_perc: float
    p_perc: float
    p_soil: float
    p_avail: float
    rsd_decomp: float
    pest_perc: float
    msk_co1: float
    msk_co2: float
    msk_x: float
    nperco_lchtile: float
    evap_adj: float
    scoef: float
    denit_exp: float
    denit_frac: float
    man_bact: float
    adj_uhyd: float
    cn_froz: float
    dorm_hr: float
    plaps: float
    tlaps: float
    n_fix_max: float
    rsd_decay: float
    rsd_cover: float
    urb_init_abst: float
    petco_pmpt: float
    uhyd_alpha: float
    splash: float
    rill: float
    surq_exp: float
    cov_mgt: float
    cha_d50: float
    co2: float
    day_lag_max: int
    igen: int


def parse_parameters_bsn(path: Path) -> ParametersBsn:
    """Parse a ``parameters.bsn`` file into a :class:`ParametersBsn` model."""
    reader = LineReader(path)
    title = reader.next().text
    header_line = reader.next()
    idx_map, unknowns = expect_header_permissive(header_line, _HEADER, path=path)

    value_line = reader.next()
    if len(value_line.tokens) != len(header_line.tokens):
        raise ParseError(
            path,
            value_line.line_no,
            f"expected {len(header_line.tokens)} values (one per header column), "
            f"got {len(value_line.tokens)}",
        )

    by_name = {name: value_line.tokens[idx_map[name]] for name in _HEADER}
    ln = value_line.line_no

    float_values: dict[str, float | None] = {}
    for name in _FLOAT_FIELDS:
        if name in _NULLABLE_FLOAT_FIELDS:
            float_values[name] = parse_nullable_float(
                by_name[name], path=path, line_no=ln, field=name
            )
        else:
            float_values[name] = parse_float(by_name[name], path=path, line_no=ln, field=name)

    int_values: dict[str, int] = {}
    # ``day_lag_max`` routes through the tolerant parser because
    # Editor < v3.1.0 serialises it as ``0.00000``; ``igen`` stays strict
    # (no evidence it shares the bug, so a stray float there is a real
    # problem worth raising on).
    day_lag_raw = by_name["day_lag_max"]
    day_lag_value, day_lag_tolerant = parse_int_tolerant(
        day_lag_raw, path=path, line_no=ln, field="day_lag_max"
    )
    int_values["day_lag_max"] = day_lag_value
    if day_lag_tolerant:
        record_drift(
            DriftRecord(
                file="parameters.bsn",
                column="day_lag_max",
                observed=day_lag_raw,
                expected_by_fortran="integer (basin_parms%day_lag_mx)",
                category="tool_bug",
                source_ref=_DAY_LAG_MAX_SOURCE_REF,
                fixed_in_version=_DAY_LAG_MAX_FIXED_IN,
            )
        )
    int_values["igen"] = parse_int(by_name["igen"], path=path, line_no=ln, field="igen")

    record_unknown_columns(unknowns, value_line, file=_FILE)

    return validate_or_raise(
        ParametersBsn,
        {"source_path": path, "title": title, **float_values, **int_values},
        path=path,
        line_no=ln,
    )
