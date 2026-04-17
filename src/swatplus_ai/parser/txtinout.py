"""Top-level orchestrator for a SWAT+ ``TxtInOut/`` project directory.

Reading every input file we care about through the individual per-file
parsers is fine for focused tests, but downstream code (calibration,
what-if analysis, reporting) wants a single typed object that holds
the entire project. :class:`TxtInOutProject` is that object, and
:meth:`TxtInOutProject.read` is the one-shot constructor.

Required files are always parsed; the five per-variable observed-weather
index files (``pcp.cli``, ``tmp.cli``, ``slr.cli``, ``hmd.cli``,
``wnd.cli``) are optional because real projects only ship the ones
they actually use — a WGN-only or reanalysis-driven project may have
none of them. Slice 4 parameter / operation / lookup databases
(``fertilizer.frt``, ``tillage.til``, ``pesticide.pes``, ``*.ops``,
``cntable.lum``, ``cons_practice.lum``, ``ovn_table.lum``) are also
optional because trimmed-down projects often omit DBs whose entries
aren't actually referenced. Slice 6 routing-body files (``aquifer.aqu``,
``channel-lte.cha``, ``hyd-sed-lte.cha``, ``nutrients.cha``, the
``*.res`` set, ``wetland.wet``, ``hydrology.wet``, and the three
``initial.{aqu,cha,res}`` files) are likewise optional — a channels-only
project has no reservoirs; an HRU-only sketch has no routing bodies
at all. Slice 7 HRU initial / chemistry files (``soil_plant.ini``,
``om_water.ini``) are optional for the same reason: projects that
don't use HRU soil/plant initial-condition sets or organic-matter
water states simply don't ship them.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.aqu_catunit_ele import AquCatunitEle, parse_aqu_catunit_ele
from swatplus_ai.parser.inputs.aquifer_aqu import AquiferAqu, parse_aquifer_aqu
from swatplus_ai.parser.inputs.aquifer_con import AquiferCon, parse_aquifer_con
from swatplus_ai.parser.inputs.chandeg_con import ChandegCon, parse_chandeg_con
from swatplus_ai.parser.inputs.channel_lte_cha import ChannelLteCha, parse_channel_lte_cha
from swatplus_ai.parser.inputs.chem_app_ops import ChemAppOps, parse_chem_app_ops
from swatplus_ai.parser.inputs.cntable_lum import CnTableLum, parse_cntable_lum
from swatplus_ai.parser.inputs.codes_bsn import CodesBsn, parse_codes_bsn
from swatplus_ai.parser.inputs.cons_practice_lum import ConsPracticeLum, parse_cons_practice_lum
from swatplus_ai.parser.inputs.fertilizer_frt import FertilizerFrt, parse_fertilizer_frt
from swatplus_ai.parser.inputs.file_cio import FileCio, parse_file_cio
from swatplus_ai.parser.inputs.fire_ops import FireOps, parse_fire_ops
from swatplus_ai.parser.inputs.graze_ops import GrazeOps, parse_graze_ops
from swatplus_ai.parser.inputs.harv_ops import HarvOps, parse_harv_ops
from swatplus_ai.parser.inputs.hru_con import HruCon, parse_hru_con
from swatplus_ai.parser.inputs.hru_data import HruData, parse_hru_data
from swatplus_ai.parser.inputs.hyd_sed_lte_cha import HydSedLteCha, parse_hyd_sed_lte_cha
from swatplus_ai.parser.inputs.hydrology_hyd import HydrologyHyd, parse_hydrology_hyd
from swatplus_ai.parser.inputs.hydrology_res import HydrologyRes, parse_hydrology_res
from swatplus_ai.parser.inputs.hydrology_wet import HydrologyWet, parse_hydrology_wet
from swatplus_ai.parser.inputs.initial_any import InitialAny, parse_initial_any
from swatplus_ai.parser.inputs.irr_ops import IrrOps, parse_irr_ops
from swatplus_ai.parser.inputs.landuse_lum import LanduseLum, parse_landuse_lum
from swatplus_ai.parser.inputs.ls_unit_def import LsUnitDef, parse_ls_unit_def
from swatplus_ai.parser.inputs.ls_unit_ele import LsUnitEle, parse_ls_unit_ele
from swatplus_ai.parser.inputs.management_sch import ManagementSch, parse_management_sch
from swatplus_ai.parser.inputs.nutrients_cha import NutrientsCha, parse_nutrients_cha
from swatplus_ai.parser.inputs.nutrients_res import NutrientsRes, parse_nutrients_res
from swatplus_ai.parser.inputs.nutrients_sol import NutrientsSol, parse_nutrients_sol
from swatplus_ai.parser.inputs.object_cnt import ObjectCnt, parse_object_cnt
from swatplus_ai.parser.inputs.om_water_ini import OmWaterIni, parse_om_water_ini
from swatplus_ai.parser.inputs.ovn_table_lum import OvnTableLum, parse_ovn_table_lum
from swatplus_ai.parser.inputs.parameters_bsn import ParametersBsn, parse_parameters_bsn
from swatplus_ai.parser.inputs.pesticide_pes import PesticidePes, parse_pesticide_pes
from swatplus_ai.parser.inputs.plant_ini import PlantIni, parse_plant_ini
from swatplus_ai.parser.inputs.print_prt import PrintPrt, parse_print_prt
from swatplus_ai.parser.inputs.reservoir_con import ReservoirCon, parse_reservoir_con
from swatplus_ai.parser.inputs.reservoir_res import ReservoirRes, parse_reservoir_res
from swatplus_ai.parser.inputs.rout_unit_con import RoutUnitCon, parse_rout_unit_con
from swatplus_ai.parser.inputs.rout_unit_def import RoutUnitDef, parse_rout_unit_def
from swatplus_ai.parser.inputs.rout_unit_ele import RoutUnitEle, parse_rout_unit_ele
from swatplus_ai.parser.inputs.rout_unit_rtu import RoutUnitRtu, parse_rout_unit_rtu
from swatplus_ai.parser.inputs.sediment_res import SedimentRes, parse_sediment_res
from swatplus_ai.parser.inputs.soil_plant_ini import SoilPlantIni, parse_soil_plant_ini
from swatplus_ai.parser.inputs.soils_sol import SoilsSol, parse_soils_sol
from swatplus_ai.parser.inputs.sweep_ops import SweepOps, parse_sweep_ops
from swatplus_ai.parser.inputs.tillage_til import TillageTil, parse_tillage_til
from swatplus_ai.parser.inputs.time_sim import TimeSim, parse_time_sim
from swatplus_ai.parser.inputs.topography_hyd import TopographyHyd, parse_topography_hyd
from swatplus_ai.parser.inputs.weather_cli import WeatherCli, parse_weather_cli
from swatplus_ai.parser.inputs.weather_sta_cli import WeatherStaCli, parse_weather_sta_cli
from swatplus_ai.parser.inputs.weather_wgn_cli import WeatherWgnCli, parse_weather_wgn_cli
from swatplus_ai.parser.inputs.wetland_wet import WetlandWet, parse_wetland_wet
from swatplus_ai.parser.models import ParsedFile

_T = TypeVar("_T", bound=ParsedFile)


def _optional(folder: Path, name: str, parser: Callable[[Path], _T]) -> _T | None:
    """Parse ``folder / name`` if it exists, else return ``None``."""
    p = folder / name
    return parser(p) if p.is_file() else None


class TxtInOutProject(BaseModel):
    """A fully-parsed SWAT+ ``TxtInOut/`` project."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    folder: Path

    # Simulation / print control
    time_sim: TimeSim
    print_prt: PrintPrt
    file_cio: FileCio
    object_cnt: ObjectCnt | None

    # Basin setup (calibration-relevant)
    codes_bsn: CodesBsn
    parameters_bsn: ParametersBsn

    # HRU-level definitions
    hydrology_hyd: HydrologyHyd
    topography_hyd: TopographyHyd
    hru_data: HruData
    landuse_lum: LanduseLum
    plant_ini: PlantIni
    soils_sol: SoilsSol
    nutrients_sol: NutrientsSol | None
    management_sch: ManagementSch

    # Operation / parameter databases referenced from management.sch + landuse.lum
    fertilizer_frt: FertilizerFrt | None
    tillage_til: TillageTil | None
    pesticide_pes: PesticidePes | None
    harv_ops: HarvOps | None
    graze_ops: GrazeOps | None
    irr_ops: IrrOps | None
    fire_ops: FireOps | None
    sweep_ops: SweepOps | None
    chem_app_ops: ChemAppOps | None

    # Land-use lookup tables
    cntable_lum: CnTableLum | None
    cons_practice_lum: ConsPracticeLum | None
    ovn_table_lum: OvnTableLum | None

    # Connectivity / topology (slice 5) — spatial graph tying HRUs to
    # routing units, channels, aquifers and reservoirs.
    hru_con: HruCon | None
    aquifer_con: AquiferCon | None
    chandeg_con: ChandegCon | None
    reservoir_con: ReservoirCon | None
    rout_unit_con: RoutUnitCon | None
    ls_unit_def: LsUnitDef | None
    ls_unit_ele: LsUnitEle | None
    rout_unit_def: RoutUnitDef | None
    rout_unit_ele: RoutUnitEle | None
    rout_unit_rtu: RoutUnitRtu | None
    aqu_catunit_ele: AquCatunitEle | None

    # Routing bodies (slice 6) — physical aquifer / channel / reservoir /
    # wetland parameters plus their initial conditions.
    aquifer_aqu: AquiferAqu | None
    initial_aqu: InitialAny | None
    channel_lte_cha: ChannelLteCha | None
    hyd_sed_lte_cha: HydSedLteCha | None
    nutrients_cha: NutrientsCha | None
    initial_cha: InitialAny | None
    reservoir_res: ReservoirRes | None
    hydrology_res: HydrologyRes | None
    nutrients_res: NutrientsRes | None
    sediment_res: SedimentRes | None
    initial_res: InitialAny | None
    wetland_wet: WetlandWet | None
    hydrology_wet: HydrologyWet | None

    # HRU initial / chemistry (slice 7) — soil/plant initial-condition
    # sets referenced from hru-data.hru, and organic-matter/water
    # initial states referenced from the initial.* files.
    soil_plant_ini: SoilPlantIni | None
    om_water_ini: OmWaterIni | None

    # Weather wiring
    weather_sta: WeatherStaCli
    weather_wgn: WeatherWgnCli

    # Per-variable observed-weather indices (only present when the project
    # ships real observations for that variable; absent when WGN or
    # reanalysis drives that variable instead).
    pcp_cli: WeatherCli | None
    tmp_cli: WeatherCli | None
    slr_cli: WeatherCli | None
    hmd_cli: WeatherCli | None
    wnd_cli: WeatherCli | None

    @classmethod
    def read(cls, folder: Path) -> TxtInOutProject:
        """Parse every known SWAT+ input file in ``folder``."""
        folder = Path(folder)
        if not folder.is_dir():
            raise NotADirectoryError(f"TxtInOut folder not found: {folder}")

        return cls(
            folder=folder,
            time_sim=parse_time_sim(folder / "time.sim"),
            print_prt=parse_print_prt(folder / "print.prt"),
            file_cio=parse_file_cio(folder / "file.cio"),
            object_cnt=_optional(folder, "object.cnt", parse_object_cnt),
            codes_bsn=parse_codes_bsn(folder / "codes.bsn"),
            parameters_bsn=parse_parameters_bsn(folder / "parameters.bsn"),
            hydrology_hyd=parse_hydrology_hyd(folder / "hydrology.hyd"),
            topography_hyd=parse_topography_hyd(folder / "topography.hyd"),
            hru_data=parse_hru_data(folder / "hru-data.hru"),
            landuse_lum=parse_landuse_lum(folder / "landuse.lum"),
            plant_ini=parse_plant_ini(folder / "plant.ini"),
            soils_sol=parse_soils_sol(folder / "soils.sol"),
            nutrients_sol=_optional(folder, "nutrients.sol", parse_nutrients_sol),
            management_sch=parse_management_sch(folder / "management.sch"),
            fertilizer_frt=_optional(folder, "fertilizer.frt", parse_fertilizer_frt),
            tillage_til=_optional(folder, "tillage.til", parse_tillage_til),
            pesticide_pes=_optional(folder, "pesticide.pes", parse_pesticide_pes),
            harv_ops=_optional(folder, "harv.ops", parse_harv_ops),
            graze_ops=_optional(folder, "graze.ops", parse_graze_ops),
            irr_ops=_optional(folder, "irr.ops", parse_irr_ops),
            fire_ops=_optional(folder, "fire.ops", parse_fire_ops),
            sweep_ops=_optional(folder, "sweep.ops", parse_sweep_ops),
            chem_app_ops=_optional(folder, "chem_app.ops", parse_chem_app_ops),
            cntable_lum=_optional(folder, "cntable.lum", parse_cntable_lum),
            cons_practice_lum=_optional(folder, "cons_practice.lum", parse_cons_practice_lum),
            ovn_table_lum=_optional(folder, "ovn_table.lum", parse_ovn_table_lum),
            hru_con=_optional(folder, "hru.con", parse_hru_con),
            aquifer_con=_optional(folder, "aquifer.con", parse_aquifer_con),
            chandeg_con=_optional(folder, "chandeg.con", parse_chandeg_con),
            reservoir_con=_optional(folder, "reservoir.con", parse_reservoir_con),
            rout_unit_con=_optional(folder, "rout_unit.con", parse_rout_unit_con),
            ls_unit_def=_optional(folder, "ls_unit.def", parse_ls_unit_def),
            ls_unit_ele=_optional(folder, "ls_unit.ele", parse_ls_unit_ele),
            rout_unit_def=_optional(folder, "rout_unit.def", parse_rout_unit_def),
            rout_unit_ele=_optional(folder, "rout_unit.ele", parse_rout_unit_ele),
            rout_unit_rtu=_optional(folder, "rout_unit.rtu", parse_rout_unit_rtu),
            aqu_catunit_ele=_optional(folder, "aqu_catunit.ele", parse_aqu_catunit_ele),
            aquifer_aqu=_optional(folder, "aquifer.aqu", parse_aquifer_aqu),
            initial_aqu=_optional(folder, "initial.aqu", parse_initial_any),
            channel_lte_cha=_optional(folder, "channel-lte.cha", parse_channel_lte_cha),
            hyd_sed_lte_cha=_optional(folder, "hyd-sed-lte.cha", parse_hyd_sed_lte_cha),
            nutrients_cha=_optional(folder, "nutrients.cha", parse_nutrients_cha),
            initial_cha=_optional(folder, "initial.cha", parse_initial_any),
            reservoir_res=_optional(folder, "reservoir.res", parse_reservoir_res),
            hydrology_res=_optional(folder, "hydrology.res", parse_hydrology_res),
            nutrients_res=_optional(folder, "nutrients.res", parse_nutrients_res),
            sediment_res=_optional(folder, "sediment.res", parse_sediment_res),
            initial_res=_optional(folder, "initial.res", parse_initial_any),
            wetland_wet=_optional(folder, "wetland.wet", parse_wetland_wet),
            hydrology_wet=_optional(folder, "hydrology.wet", parse_hydrology_wet),
            soil_plant_ini=_optional(folder, "soil_plant.ini", parse_soil_plant_ini),
            om_water_ini=_optional(folder, "om_water.ini", parse_om_water_ini),
            weather_sta=parse_weather_sta_cli(folder / "weather-sta.cli"),
            weather_wgn=parse_weather_wgn_cli(folder / "weather-wgn.cli"),
            pcp_cli=_optional(folder, "pcp.cli", parse_weather_cli),
            tmp_cli=_optional(folder, "tmp.cli", parse_weather_cli),
            slr_cli=_optional(folder, "slr.cli", parse_weather_cli),
            hmd_cli=_optional(folder, "hmd.cli", parse_weather_cli),
            wnd_cli=_optional(folder, "wnd.cli", parse_weather_cli),
        )


__all__ = ["ParseError", "TxtInOutProject"]
