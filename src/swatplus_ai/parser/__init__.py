"""Typed parsers for SWAT+ TxtInOut files."""

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.aqu_catunit_ele import (
    AquCatunitEle,
    AquCatunitEleRow,
    parse_aqu_catunit_ele,
)
from swatplus_ai.parser.inputs.aquifer_con import AquiferCon, AquiferConRow, parse_aquifer_con
from swatplus_ai.parser.inputs.chandeg_con import ChandegCon, ChandegConRow, parse_chandeg_con
from swatplus_ai.parser.inputs.chem_app_ops import (
    ChemAppOps,
    ChemAppOpsRow,
    parse_chem_app_ops,
)
from swatplus_ai.parser.inputs.cntable_lum import CnTableLum, CnTableLumRow, parse_cntable_lum
from swatplus_ai.parser.inputs.codes_bsn import CodesBsn, parse_codes_bsn
from swatplus_ai.parser.inputs.cons_practice_lum import (
    ConsPracticeLum,
    ConsPracticeLumRow,
    parse_cons_practice_lum,
)
from swatplus_ai.parser.inputs.fertilizer_frt import (
    FertilizerFrt,
    FertilizerFrtRow,
    parse_fertilizer_frt,
)
from swatplus_ai.parser.inputs.file_cio import FileCio, FileCioSection, parse_file_cio
from swatplus_ai.parser.inputs.fire_ops import FireOps, FireOpsRow, parse_fire_ops
from swatplus_ai.parser.inputs.graze_ops import GrazeOps, GrazeOpsRow, parse_graze_ops
from swatplus_ai.parser.inputs.harv_ops import HarvOps, HarvOpsRow, parse_harv_ops
from swatplus_ai.parser.inputs.hru_con import HruCon, HruConRow, parse_hru_con
from swatplus_ai.parser.inputs.hru_data import HruData, HruDataRow, parse_hru_data
from swatplus_ai.parser.inputs.hydrology_hyd import (
    HydrologyHyd,
    HydrologyHydRow,
    parse_hydrology_hyd,
)
from swatplus_ai.parser.inputs.irr_ops import IrrOps, IrrOpsRow, parse_irr_ops
from swatplus_ai.parser.inputs.landuse_lum import LanduseLum, LanduseLumRow, parse_landuse_lum
from swatplus_ai.parser.inputs.ls_unit_def import LsUnitDef, LsUnitDefRow, parse_ls_unit_def
from swatplus_ai.parser.inputs.ls_unit_ele import LsUnitEle, LsUnitEleRow, parse_ls_unit_ele
from swatplus_ai.parser.inputs.management_sch import (
    AutoOp,
    ManagementSch,
    ManagementSchedule,
    ScheduledOp,
    parse_management_sch,
)
from swatplus_ai.parser.inputs.nutrients_sol import (
    NutrientsSol,
    NutrientsSolRow,
    parse_nutrients_sol,
)
from swatplus_ai.parser.inputs.object_cnt import ObjectCnt, parse_object_cnt
from swatplus_ai.parser.inputs.ovn_table_lum import (
    OvnTableLum,
    OvnTableLumRow,
    parse_ovn_table_lum,
)
from swatplus_ai.parser.inputs.parameters_bsn import ParametersBsn, parse_parameters_bsn
from swatplus_ai.parser.inputs.pesticide_pes import (
    PesticidePes,
    PesticidePesRow,
    parse_pesticide_pes,
)
from swatplus_ai.parser.inputs.plant_ini import (
    PlantCommunity,
    PlantIni,
    PlantMember,
    parse_plant_ini,
)
from swatplus_ai.parser.inputs.print_prt import ObjectPrintFlags, PrintPrt, parse_print_prt
from swatplus_ai.parser.inputs.reservoir_con import (
    ReservoirCon,
    ReservoirConRow,
    parse_reservoir_con,
)
from swatplus_ai.parser.inputs.rout_unit_con import (
    RoutUnitCon,
    RoutUnitConRow,
    parse_rout_unit_con,
)
from swatplus_ai.parser.inputs.rout_unit_def import (
    RoutUnitDef,
    RoutUnitDefRow,
    parse_rout_unit_def,
)
from swatplus_ai.parser.inputs.rout_unit_ele import (
    RoutUnitEle,
    RoutUnitEleRow,
    parse_rout_unit_ele,
)
from swatplus_ai.parser.inputs.rout_unit_rtu import (
    RoutUnitRtu,
    RoutUnitRtuRow,
    parse_rout_unit_rtu,
)
from swatplus_ai.parser.inputs.soils_sol import Soil, SoilLayer, SoilsSol, parse_soils_sol
from swatplus_ai.parser.inputs.sweep_ops import SweepOps, SweepOpsRow, parse_sweep_ops
from swatplus_ai.parser.inputs.tillage_til import TillageTil, TillageTilRow, parse_tillage_til
from swatplus_ai.parser.inputs.time_sim import TimeSim, parse_time_sim
from swatplus_ai.parser.inputs.topography_hyd import (
    TopographyHyd,
    TopographyHydRow,
    parse_topography_hyd,
)
from swatplus_ai.parser.inputs.weather_cli import WeatherCli, parse_weather_cli
from swatplus_ai.parser.inputs.weather_sta_cli import (
    WeatherStaCli,
    WeatherStaCliRow,
    parse_weather_sta_cli,
)
from swatplus_ai.parser.inputs.weather_wgn_cli import (
    WeatherWgnCli,
    WgnMonth,
    WgnStation,
    parse_weather_wgn_cli,
)
from swatplus_ai.parser.models import ConConnection, ParsedFile
from swatplus_ai.parser.txtinout import TxtInOutProject

__all__ = [
    "AquCatunitEle",
    "AquCatunitEleRow",
    "AquiferCon",
    "AquiferConRow",
    "AutoOp",
    "ChandegCon",
    "ChandegConRow",
    "ChemAppOps",
    "ChemAppOpsRow",
    "CnTableLum",
    "CnTableLumRow",
    "CodesBsn",
    "ConConnection",
    "ConsPracticeLum",
    "ConsPracticeLumRow",
    "FertilizerFrt",
    "FertilizerFrtRow",
    "FileCio",
    "FileCioSection",
    "FireOps",
    "FireOpsRow",
    "GrazeOps",
    "GrazeOpsRow",
    "HarvOps",
    "HarvOpsRow",
    "HruCon",
    "HruConRow",
    "HruData",
    "HruDataRow",
    "HydrologyHyd",
    "HydrologyHydRow",
    "IrrOps",
    "IrrOpsRow",
    "LanduseLum",
    "LanduseLumRow",
    "LsUnitDef",
    "LsUnitDefRow",
    "LsUnitEle",
    "LsUnitEleRow",
    "ManagementSch",
    "ManagementSchedule",
    "NutrientsSol",
    "NutrientsSolRow",
    "ObjectCnt",
    "ObjectPrintFlags",
    "OvnTableLum",
    "OvnTableLumRow",
    "ParametersBsn",
    "ParseError",
    "ParsedFile",
    "PesticidePes",
    "PesticidePesRow",
    "PlantCommunity",
    "PlantIni",
    "PlantMember",
    "PrintPrt",
    "ReservoirCon",
    "ReservoirConRow",
    "RoutUnitCon",
    "RoutUnitConRow",
    "RoutUnitDef",
    "RoutUnitDefRow",
    "RoutUnitEle",
    "RoutUnitEleRow",
    "RoutUnitRtu",
    "RoutUnitRtuRow",
    "ScheduledOp",
    "Soil",
    "SoilLayer",
    "SoilsSol",
    "SweepOps",
    "SweepOpsRow",
    "TillageTil",
    "TillageTilRow",
    "TimeSim",
    "TopographyHyd",
    "TopographyHydRow",
    "TxtInOutProject",
    "WeatherCli",
    "WeatherStaCli",
    "WeatherStaCliRow",
    "WeatherWgnCli",
    "WgnMonth",
    "WgnStation",
    "parse_aqu_catunit_ele",
    "parse_aquifer_con",
    "parse_chandeg_con",
    "parse_chem_app_ops",
    "parse_cntable_lum",
    "parse_codes_bsn",
    "parse_cons_practice_lum",
    "parse_fertilizer_frt",
    "parse_file_cio",
    "parse_fire_ops",
    "parse_graze_ops",
    "parse_harv_ops",
    "parse_hru_con",
    "parse_hru_data",
    "parse_hydrology_hyd",
    "parse_irr_ops",
    "parse_landuse_lum",
    "parse_ls_unit_def",
    "parse_ls_unit_ele",
    "parse_management_sch",
    "parse_nutrients_sol",
    "parse_object_cnt",
    "parse_ovn_table_lum",
    "parse_parameters_bsn",
    "parse_pesticide_pes",
    "parse_plant_ini",
    "parse_print_prt",
    "parse_reservoir_con",
    "parse_rout_unit_con",
    "parse_rout_unit_def",
    "parse_rout_unit_ele",
    "parse_rout_unit_rtu",
    "parse_soils_sol",
    "parse_sweep_ops",
    "parse_tillage_til",
    "parse_time_sim",
    "parse_topography_hyd",
    "parse_weather_cli",
    "parse_weather_sta_cli",
    "parse_weather_wgn_cli",
]
