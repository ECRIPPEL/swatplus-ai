# SWAT+ai

![Status](https://img.shields.io/badge/status-alpha-orange) ![License](https://img.shields.io/badge/license-MIT-green)

> Open-source AI assistant for SWAT+ model setup, calibration, and evaluation.

**Early alpha. Most of the planned functionality is not implemented yet.**

Only Module 1 (setup check) is usable end-to-end. Modules 2 (calibration) and 3 (evaluation) are planned but not yet built. The UI is a placeholder-heavy prototype. Expect breaking changes throughout the `0.1.x` series.

## What's being developed

SWAT+ projects involve hundreds of input files, dozens of physical parameters, and a calibration workflow that rewards experience. SWAT+ai is an experiment in using LLMs grounded in the SWAT+ I/O documentation to help interpret what a project is doing and flag obvious setup issues — a tool to assist, not replace, the modeller's judgement.

Planned scope:

- **Setup check** — parse a TxtInOut folder, run diagnostic rules, explain the findings (working today, with caveats).
- **Calibration assistant** — tool-agnostic helper for the iteration loop (not started).
- **Evaluation** — goodness-of-fit metrics + results interpretation against literature (math layer shipped, no consumer wired yet).

Everything runs locally. Only the LLM call leaves your machine, and only when you ask for it.

## Quick start

Requires Python 3.11+ and a SWAT+ project saved from Editor v3.0 or newer.

```bash
git clone https://github.com/ECRIPPEL/swatplus-ai
cd swatplus-ai
uv sync --extra dev          # or: pip install -e ".[dev]"

# parsing + rules only, no LLM
swatplus-ai check /path/to/TxtInOut --skip-llm

# with LLM (needs Anthropic or OpenAI key)
swatplus-ai config set-key anthropic
swatplus-ai check /path/to/TxtInOut
```

Use `swatplus-ai --help` for the full command surface.

## Known limitations

- Modules 2 and 3 not implemented
- SWAT+ Editor < v3.0 (format `rev.60.x`) is rejected at the version gate
- Retrieval grounding covers the SWAT+ I/O documentation only
- UI is experimental; most endpoints return HTTP 501 with a placeholder
- CI validates Linux only; Windows works locally but isn't yet part of the CI matrix

## License

[MIT](LICENSE)
