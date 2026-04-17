"""Parser for ``soils.sol`` — SWAT+ soil profile definitions.

Like ``plant.ini``, this file has a **nested** grammar: each entry is one
soil-header line followed by ``nly`` layer lines. The file-level header
(line 2) concatenates the 7 soil columns and the 14 layer columns.

Grammar::

    title
    header                  (7 soil columns + 14 layer columns = 21)
    <soil row>              (7 tokens)
    <layer row> ...         (nly of them, 14 tokens each)
    <soil row>              (next soil)
    ...

Each soil is referenced by ``hru-data.hru.soil``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from swatplus_ai.parser._base import (
    LineReader,
    ParseError,
    expect_tokens,
    parse_float,
    parse_int,
)
from swatplus_ai.parser.models import ParsedFile

_HEADER: tuple[str, ...] = (
    "name",
    "nly",
    "hyd_grp",
    "dp_tot",
    "anion_excl",
    "perc_crk",
    "texture",
    "dp",
    "bd",
    "awc",
    "soil_k",
    "carbon",
    "clay",
    "silt",
    "sand",
    "rock",
    "alb",
    "usle_k",
    "ec",
    "caco3",
    "ph",
)

_SOIL_COL_COUNT = 7
_LAYER_COL_COUNT = 14


class SoilLayer(BaseModel):
    """A single soil layer within a :class:`Soil`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dp: float  # layer bottom depth [mm]
    bd: float  # bulk density [g/cm3]
    awc: float  # available water capacity [mm/mm]
    soil_k: float  # saturated hydraulic conductivity [mm/hr]
    carbon: float  # organic carbon [%]
    clay: float
    silt: float
    sand: float
    rock: float
    alb: float  # moist-soil albedo
    usle_k: float  # USLE erodibility factor
    ec: float  # electrical conductivity [dS/m]
    caco3: float
    ph: float


class Soil(BaseModel):
    """A named soil profile (one logical entry in soils.sol)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    nly: int = Field(ge=1, description="Number of soil layers")
    hyd_grp: str  # hydrologic group: A, B, C, or D
    dp_tot: float  # total profile depth [mm]
    anion_excl: float
    perc_crk: float
    texture: str
    layers: tuple[SoilLayer, ...]


class SoilsSol(ParsedFile):
    """Contents of ``soils.sol``: one or more named soil profiles."""

    soils: tuple[Soil, ...]

    def by_name(self, name: str) -> Soil | None:
        for s in self.soils:
            if s.name == name:
                return s
        return None


def parse_soils_sol(path: Path) -> SoilsSol:
    """Parse a ``soils.sol`` file into a :class:`SoilsSol` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    soils: list[Soil] = []
    while not reader.eof():
        soil_line = reader.next()
        if len(soil_line.tokens) != _SOIL_COL_COUNT:
            raise ParseError(
                path,
                soil_line.line_no,
                f"expected {_SOIL_COL_COUNT} tokens in soil row "
                f"(name nly hyd_grp dp_tot anion_excl perc_crk texture), "
                f"got {len(soil_line.tokens)}",
            )
        name, nly_s, hyd_grp, dp_tot_s, anion_excl_s, perc_crk_s, texture = soil_line.tokens
        ln = soil_line.line_no
        nly = parse_int(nly_s, path=path, line_no=ln, field="nly")

        layers: list[SoilLayer] = []
        for i in range(nly):
            if reader.eof():
                raise ParseError(
                    path,
                    soil_line.line_no,
                    f"soil {name!r} declares nly={nly} but only {i} layer row(s) "
                    f"were available before end of file",
                )
            layer_line = reader.next()
            if len(layer_line.tokens) != _LAYER_COL_COUNT:
                raise ParseError(
                    path,
                    layer_line.line_no,
                    f"expected {_LAYER_COL_COUNT} tokens in soil layer row for "
                    f"{name!r}, got {len(layer_line.tokens)}",
                )
            dp, bd, awc, soil_k, carbon, clay, silt, sand, rock, alb, usle_k, ec, caco3, ph = (
                layer_line.tokens
            )
            lln = layer_line.line_no
            layers.append(
                SoilLayer(
                    dp=parse_float(dp, path=path, line_no=lln, field="dp"),
                    bd=parse_float(bd, path=path, line_no=lln, field="bd"),
                    awc=parse_float(awc, path=path, line_no=lln, field="awc"),
                    soil_k=parse_float(soil_k, path=path, line_no=lln, field="soil_k"),
                    carbon=parse_float(carbon, path=path, line_no=lln, field="carbon"),
                    clay=parse_float(clay, path=path, line_no=lln, field="clay"),
                    silt=parse_float(silt, path=path, line_no=lln, field="silt"),
                    sand=parse_float(sand, path=path, line_no=lln, field="sand"),
                    rock=parse_float(rock, path=path, line_no=lln, field="rock"),
                    alb=parse_float(alb, path=path, line_no=lln, field="alb"),
                    usle_k=parse_float(usle_k, path=path, line_no=lln, field="usle_k"),
                    ec=parse_float(ec, path=path, line_no=lln, field="ec"),
                    caco3=parse_float(caco3, path=path, line_no=lln, field="caco3"),
                    ph=parse_float(ph, path=path, line_no=lln, field="ph"),
                )
            )

        soils.append(
            Soil(
                name=name,
                nly=nly,
                hyd_grp=hyd_grp,
                dp_tot=parse_float(dp_tot_s, path=path, line_no=ln, field="dp_tot"),
                anion_excl=parse_float(anion_excl_s, path=path, line_no=ln, field="anion_excl"),
                perc_crk=parse_float(perc_crk_s, path=path, line_no=ln, field="perc_crk"),
                texture=texture,
                layers=tuple(layers),
            )
        )

    return SoilsSol(source_path=path, title=title, soils=tuple(soils))
