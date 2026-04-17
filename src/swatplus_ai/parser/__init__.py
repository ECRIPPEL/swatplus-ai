"""Typed parsers for SWAT+ TxtInOut files."""

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.file_cio import FileCio, FileCioSection, parse_file_cio
from swatplus_ai.parser.inputs.hru_data import HruData, HruDataRow, parse_hru_data
from swatplus_ai.parser.inputs.hydrology_hyd import (
    HydrologyHyd,
    HydrologyHydRow,
    parse_hydrology_hyd,
)
from swatplus_ai.parser.inputs.landuse_lum import LanduseLum, LanduseLumRow, parse_landuse_lum
from swatplus_ai.parser.inputs.management_sch import (
    AutoOp,
    ManagementSch,
    ManagementSchedule,
    ScheduledOp,
    parse_management_sch,
)
from swatplus_ai.parser.inputs.plant_ini import (
    PlantCommunity,
    PlantIni,
    PlantMember,
    parse_plant_ini,
)
from swatplus_ai.parser.inputs.print_prt import ObjectPrintFlags, PrintPrt, parse_print_prt
from swatplus_ai.parser.inputs.soils_sol import Soil, SoilLayer, SoilsSol, parse_soils_sol
from swatplus_ai.parser.inputs.time_sim import TimeSim, parse_time_sim
from swatplus_ai.parser.models import ParsedFile

__all__ = [
    "AutoOp",
    "FileCio",
    "FileCioSection",
    "HruData",
    "HruDataRow",
    "HydrologyHyd",
    "HydrologyHydRow",
    "LanduseLum",
    "LanduseLumRow",
    "ManagementSch",
    "ManagementSchedule",
    "ObjectPrintFlags",
    "ParseError",
    "ParsedFile",
    "PlantCommunity",
    "PlantIni",
    "PlantMember",
    "PrintPrt",
    "ScheduledOp",
    "Soil",
    "SoilLayer",
    "SoilsSol",
    "TimeSim",
    "parse_file_cio",
    "parse_hru_data",
    "parse_hydrology_hyd",
    "parse_landuse_lum",
    "parse_management_sch",
    "parse_plant_ini",
    "parse_print_prt",
    "parse_soils_sol",
    "parse_time_sim",
]
