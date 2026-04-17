"""Parser for ``parameters.bsn`` — SWAT+ basin-wide numerical parameters.

Single-row file (like ``codes.bsn``): title, 44-column header, one
value row. 42 columns are floats; the last two (``day_lag_max``,
``igen``) are integers.

These are the global calibration knobs — the knobs a user tunes
against observed discharge/WB data — so the parser exposes them as
individual typed fields rather than a bag of values.
"""

from __future__ import annotations

from pathlib import Path

from swatplus_ai.parser._base import LineReader, ParseError, expect_tokens, parse_float, parse_int
from swatplus_ai.parser.models import ParsedFile

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

_HEADER: tuple[str, ...] = _FLOAT_FIELDS + _INT_FIELDS
_COL_COUNT = len(_HEADER)


class ParametersBsn(ParsedFile):
    """Contents of ``parameters.bsn``: one record of basin-wide parameters."""

    lai_noevap: float
    sw_init: float
    surq_lag: float
    adj_pkrt: float
    adj_pkrt_sed: float
    lin_sed: float
    exp_sed: float
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
    expect_tokens(reader.next(), _HEADER, path=path)

    value_line = reader.next()
    if len(value_line.tokens) != _COL_COUNT:
        raise ParseError(
            path,
            value_line.line_no,
            f"expected {_COL_COUNT} tokens in parameters.bsn value row, "
            f"got {len(value_line.tokens)}",
        )

    by_name = dict(zip(_HEADER, value_line.tokens, strict=True))
    ln = value_line.line_no

    float_values = {
        name: parse_float(by_name[name], path=path, line_no=ln, field=name)
        for name in _FLOAT_FIELDS
    }
    int_values = {
        name: parse_int(by_name[name], path=path, line_no=ln, field=name) for name in _INT_FIELDS
    }

    return ParametersBsn(source_path=path, title=title, **float_values, **int_values)
