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
- `TxtInOutProject.read()` orchestrator covering slices 1–5; missing optional databases are tolerated.
