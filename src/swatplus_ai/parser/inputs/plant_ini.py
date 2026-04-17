"""Parser for ``plant.ini`` — SWAT+ initial plant-community definitions.

Unlike the other per-row files, ``plant.ini`` is **nested**: each entry is
one community-header line followed by ``plt_cnt`` member lines. The file-
level header (line 2) lists the 11 column names of the two levels fused
together: 3 community columns + 8 member columns.

Grammar::

    title
    header              (11 column names)
    <community row>     (3 tokens)
    <member row> ...    (plt_cnt of them, 8 tokens each)
    <community row>     (next community)
    ...

Each community is referenced by ``landuse.lum.plnt_com``.
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
    parse_yn,
)
from swatplus_ai.parser.models import ParsedFile

_HEADER: tuple[str, ...] = (
    "pcom_name",
    "plt_cnt",
    "rot_yr_ini",
    "plt_name",
    "lc_status",
    "lai_init",
    "bm_init",
    "phu_init",
    "plnt_pop",
    "yrs_init",
    "rsd_init",
)

_COMMUNITY_COL_COUNT = 3
_MEMBER_COL_COUNT = 8


class PlantMember(BaseModel):
    """A single plant within a :class:`PlantCommunity`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    plt_name: str
    lc_status: bool  # y/n — land-cover present at simulation start
    lai_init: float
    bm_init: float  # initial biomass [kg/ha]
    phu_init: float  # initial potential heat units fraction
    plnt_pop: float
    yrs_init: float  # years since planting (for perennials)
    rsd_init: float  # initial residue [kg/ha]


class PlantCommunity(BaseModel):
    """A named plant community (one logical entry in plant.ini)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pcom_name: str
    plt_cnt: int = Field(ge=0, description="Number of plant members in this community")
    rot_yr_ini: int = Field(ge=0)
    members: tuple[PlantMember, ...]


class PlantIni(ParsedFile):
    """Contents of ``plant.ini``: one or more named plant communities."""

    communities: tuple[PlantCommunity, ...]

    def by_name(self, name: str) -> PlantCommunity | None:
        for c in self.communities:
            if c.pcom_name == name:
                return c
        return None


def parse_plant_ini(path: Path) -> PlantIni:
    """Parse a ``plant.ini`` file into a :class:`PlantIni` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    communities: list[PlantCommunity] = []
    while not reader.eof():
        com_line = reader.next()
        if len(com_line.tokens) != _COMMUNITY_COL_COUNT:
            raise ParseError(
                path,
                com_line.line_no,
                f"expected {_COMMUNITY_COL_COUNT} tokens in community row "
                f"(pcom_name plt_cnt rot_yr_ini), got {len(com_line.tokens)}",
            )
        pcom_name = com_line.tokens[0]
        plt_cnt = parse_int(
            com_line.tokens[1], path=path, line_no=com_line.line_no, field="plt_cnt"
        )
        rot_yr_ini = parse_int(
            com_line.tokens[2], path=path, line_no=com_line.line_no, field="rot_yr_ini"
        )

        members: list[PlantMember] = []
        for i in range(plt_cnt):
            if reader.eof():
                raise ParseError(
                    path,
                    com_line.line_no,
                    f"community {pcom_name!r} declares plt_cnt={plt_cnt} but only "
                    f"{i} member row(s) were available before end of file",
                )
            mem_line = reader.next()
            if len(mem_line.tokens) != _MEMBER_COL_COUNT:
                raise ParseError(
                    path,
                    mem_line.line_no,
                    f"expected {_MEMBER_COL_COUNT} tokens in plant member row for "
                    f"community {pcom_name!r}, got {len(mem_line.tokens)}",
                )
            plt_name, lc_s, lai, bm, phu, pop, yrs, rsd = mem_line.tokens
            ln = mem_line.line_no
            members.append(
                PlantMember(
                    plt_name=plt_name,
                    lc_status=parse_yn(lc_s, path=path, line_no=ln, field="lc_status"),
                    lai_init=parse_float(lai, path=path, line_no=ln, field="lai_init"),
                    bm_init=parse_float(bm, path=path, line_no=ln, field="bm_init"),
                    phu_init=parse_float(phu, path=path, line_no=ln, field="phu_init"),
                    plnt_pop=parse_float(pop, path=path, line_no=ln, field="plnt_pop"),
                    yrs_init=parse_float(yrs, path=path, line_no=ln, field="yrs_init"),
                    rsd_init=parse_float(rsd, path=path, line_no=ln, field="rsd_init"),
                )
            )

        communities.append(
            PlantCommunity(
                pcom_name=pcom_name,
                plt_cnt=plt_cnt,
                rot_yr_ini=rot_yr_ini,
                members=tuple(members),
            )
        )

    return PlantIni(source_path=path, title=title, communities=tuple(communities))
