# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial repository scaffold: `pyproject.toml`, `src/` layout, MIT license, CI workflow, pre-commit hooks.
- `swatplus-ai version` CLI command as a first end-to-end smoke check.
- Parser slice 1 — control & inventory: `time.sim`, `print.prt`, `file.cio`, `codes.bsn`, `parameters.bsn`, `object.cnt`.
- Parser slice 2 — HRU core: `hydrology.hyd`, `hru-data.hru`, `landuse.lum`, `plant.ini`, `soils.sol`, `topography.hyd`, `nutrients.sol`.
- Parser slice 3 — weather: `weather-sta.cli`, `weather-wgn.cli`, generic `pcp/tmp/slr/hmd/wnd.cli`.
- Parser slice 4 — management & lookups: `management.sch`, `fertilizer.frt`, `tillage.til`, `pesticide.pes`, `harv/graze/irr/fire/sweep/chem_app.ops`, `cntable.lum`, `cons_practice.lum`, `ovn_table.lum`.
- Parser slice 5 — connectivity / topology: `hru.con`, `aquifer.con`, `chandeg.con`, `reservoir.con`, `rout_unit.con`, `ls_unit.def`/`.ele`, `rout_unit.def`/`.ele`/`.rtu`, `aqu_catunit.ele`.
- Parser slice 6 — routing bodies: `aquifer.aqu`, `initial.aqu`, `channel-lte.cha`, `hyd-sed-lte.cha`, `nutrients.cha`, `initial.cha`, `reservoir.res`, `hydrology.res`, `nutrients.res`, `sediment.res`, `initial.res`, `wetland.wet`, `hydrology.wet`. Shared `parse_initial_any` backs the three `initial.{aqu,cha,res}` files.
- Parser slice 7 (partial) — HRU initial / chemistry: `soil_plant.ini`, `om_water.ini`.
- Parser slice 8 (partial) — calibration / change: `cal_parms.cal`, `codes.sft`, `wb_parms.sft`, `water_balance.sft`, `plant_gro.sft`, `plant_parms.sft`.
- Parser slice 9 — decision tables: `lum.dtl`, `res_rel.dtl`, backed by a shared `_decision_table.py` helper. Table count on line 2 is informational; tables are read until EOF so hand-edited files parse correctly.
- `TxtInOutProject.read()` orchestrator covering slices 1–9; every optional file is tolerated when absent.
- Output parsers slice A — annual-average / yearly summaries as pandas DataFrames: `basin_wb_aa`, `basin_pw_aa`, `basin_ls_aa`, `basin_nb_aa`, `hru_wb_aa`, `hru_pw_aa`, `hru_ls_aa`, `hru_nb_aa`, `channel_sd_aa`, `channel_sdmorph_aa`, `aquifer_aa`, `reservoir_aa`, `wetland_aa`. Shared `read_aa_output` reader handles title/header/units preambles, multi-word text columns (`plant_cov`), duplicate header names (`null` separators, repeated `deg_btm`/`deg_bank`), and short rows. Wired into `TxtInOutProject.outputs`; every DataFrame is optional so un-run projects still parse.
- `TxtInOutProject.topology.outfall_channels()` returns names of channels with `out_tot == 0` from the already-parsed `chandeg.con`.
- New runtime dependencies: `pandas>=2.2`, `pyarrow>=16`.
