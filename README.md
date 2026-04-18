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

## Session logs

SWAT+ai keeps a local, append-only log of every command it runs so you can
audit what happened after the fact. The logs are **local-only**: they never
leave your machine unless you hand them over yourself with `logs export`.

### Location and format

- Logs live in `<project>/.swatplus-ai/logs/session-<uuid>.jsonl` — one file
  per session, one JSON object per line.
- Each line is a structured event: timestamp (UTC), event type
  (`file_parsed`, `rule_evaluated`, `finding_emitted`, …), and a fields map.
- Strings are passed through a redaction pass at write time: API-key
  patterns, emails, and absolute filesystem paths are collapsed before the
  event ever hits disk. The raw event objects never reach the LLM either —
  the agent reasons over structured project state, not over the log.

### Inspect and export

```bash
# index of sessions, newest first
swatplus-ai logs list

# pretty-print the newest session (or a specific one)
swatplus-ai logs show
swatplus-ai logs show --last 20
swatplus-ai logs show --session 3f4a9b2c

# byte-for-byte copy one session's JSONL somewhere you choose
swatplus-ai logs export --output ./session.jsonl
swatplus-ai logs export --session 3f4a9b2c --output ./bug-report.jsonl
```

Session prefixes passed to `--session` must be at least 4 characters and
unambiguous among the existing logs.

### Disable logging

Telemetry is on by default. To turn it off:

```bash
swatplus-ai telemetry disable    # persistent, per-user
SWATPLUS_AI_NO_LOG=1 swatplus-ai …   # one-shot, per-invocation
```

When disabled, no events are written and `logs list` simply reports that
the directory is empty.

## License

[MIT](LICENSE)
