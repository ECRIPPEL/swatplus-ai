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
- LLM gateway (Phase 1 Step 5):
  - `swatplus_ai.llm.interface` — `Message`, `LLMResponse`, `LLMBackend` Protocol, `LLMError` / `AuthError` / `RateLimitError`.
  - API-key backends for Anthropic (`x-api-key`) and OpenAI (`Bearer`) speaking raw HTTP via `httpx` (no vendor SDKs), with streaming SSE support.
  - `MockBackend` for deterministic tests.
  - Token storage: in-memory default plus an optional OS-keyring store (install with the new `secrets` extra: `pip install 'swatplus-ai[secrets]'`).
  - **Experimental, opt-in** OAuth passthrough backends for Anthropic and OpenAI using the Authorization Code + PKCE flow that Claude Code and OpenAI Codex CLI use. Subscription-bound; disabled by default until the upstream client IDs are pinned.
- Diagnostic rule engine infrastructure (Phase 1 Step 4 slice 4.1): `swatplus_ai.diagnostics` exposes `Finding`, `Rule`, `CheckResult`, `DiagnosticEngine`, and the `register_check` decorator. YAML-loaded rules reference Python check functions by name via a registry; `DiagnosticEngine.from_builtin_rules()` loads every `*.yaml` shipped under `swatplus_ai/diagnostics/rules/` and fails loudly at construction time if a rule references an unregistered check or duplicates an id across files. `.run(project, stage=...)` filters rules by lifecycle stage and skips rules whose `requires` attrs are absent on the project. No rules bundled yet — ships in slices 4.2 and 4.3.
- Diagnostic rules slice 4.2 — five pre-run `setup.*` rules bundled with `DiagnosticEngine.from_builtin_rules()`: `setup.files_present`, `setup.sim_period_sanity`, `setup.warmup_ratio`, `setup.mgt_date_order`, `setup.object_count_consistency`. Covers the structural input-side problems (missing control files, inverted / zero-length / too-short simulation windows, implausible warm-up ratios, out-of-order management schedules, `object.cnt` vs `.con` count mismatches) that SWAT+ either crashes on or silently runs through. `CheckResult` gains an optional `severity` override so a single rule can emit findings at different severities (used by `setup.sim_period_sanity`). Check functions live under `swatplus_ai/diagnostics/checks/` and are auto-registered on package import.
- Diagnostic rules slice 4.3 — five new rules close the Module-1 (pre-run + first-pass evaluation) set, bringing `DiagnosticEngine.from_builtin_rules()` to ten rule ids: `hru.fk_consistency` (setup, error) guards the four FKs on every `hru-data.hru` row; `chan.routing_topology` (setup, error/warning) covers outfall existence, `out_tot` consistency, `frac` sums, downstream range, and cycle detection in `chandeg.con`; `setup.pet_method_vs_climate` (setup, warning) branches on `codes.bsn.pet` against `weather-sta.cli` sources; `wx.source_consistency` (setup, error) cross-checks `weather-sta.cli` against the per-variable `.cli` indices and their on-disk files; `wb.et_precip_ratio` (evaluation, warning) flags implausible basin-scale ET/precipitation ratios on `basin_wb_aa`. `DiagnosticEngine` now resolves dotted `requires` paths (`outputs.basin_wb_aa`) attribute-by-attribute.
