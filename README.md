# SWAT+ai

> Open-source AI assistant for SWAT+ model setup, calibration, and evaluation.

**Status:** pre-alpha · not yet usable · under active construction.

SWAT+ai helps SWAT+ modelers diagnose input problems, set up calibration
experiments with their tool of choice, and evaluate results against the
scientific literature — all grounded in the official [SWAT Literature
Database](https://litdb.swat.tamu.edu/) and SWAT+ I/O documentation.

## Design principles

- **Local-first.** Your SWAT+ project stays on your machine; no SaaS.
- **Retrieval-grounded.** Answers cite sources from the SWAT literature.
- **Standalone.** No runtime coupling to other community tools (SWATdoctR,
  pySWATPlus, SWAT+ Toolbox, R-SWAT). Ideas may be borrowed; code is not.
- **SWAT+ only.** Legacy SWAT2012 is out of scope.

## Install

Not yet published. Development install:

```bash
git clone https://github.com/ECRIPPEL/swatplus-ai
cd swatplus-ai
uv sync --extra dev
```

## License

[MIT](LICENSE)
