# `swatplus_ai.retrieval` — retrieval API contract

First slice (R1, 2026-04-21): SWAT+ I/O spec corpus only, BM25 only,
no embeddings, no integration with Module 1's prompt builder. The
prompt chat consumes `retrieve()` in its own slice.

## TL;DR

```python
from swatplus_ai.retrieval import retrieve

passages = retrieve("day_lag_max surface runoff lag", k=5)
for p in passages:
    print(p.handle, round(p.score, 3))
    print(p.text[:200])
```

First call from a cold cache performs one HTTPS GET to
`https://swatplus.gitbook.io/io-docs/llms-full.txt`, chunks the dump,
and builds a BM25 index under `./data/retrieval/io_docs/`. Subsequent
calls reuse the cache. Override the location with the `cache_dir`
keyword argument.

## Public surface

```python
def retrieve(
    query: str,
    k: int = 5,
    filters: Mapping[str, Any] | None = None,
    *,
    cache_dir: Path | None = None,
) -> tuple[RetrievedPassage, ...]:
    ...


class RetrievedPassage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    handle: str             # stable citation token — see "Handles" below
    text: str               # chunk body, including its markdown header
    score: float            # BM25 score, descending across the returned tuple
    source_ref: str         # canonical URL of the underlying document
    metadata: Mapping[str, Any]  # {"file": "<swatplus-file>", "section": "<title>", ...}
```

Those two names — `retrieve` and `RetrievedPassage` — are the entire
contract. Everything else (the chunker, the BM25 wrapper, the fetcher)
is implementation detail and may change without a contract bump.

## Handles

Every passage carries a deterministic `handle` of the form:

```
doc:io:<swatplus-file>:<section-slug>              # single-section chunk
doc:io:<swatplus-file>:<section-slug>:<sub-slug>   # sub-chunk of a large section
doc:io:_general:<section-slug>                     # pre-file / general doc sections
```

Examples:

- `doc:io:time.sim:day-start`
- `doc:io:parameters.bsn:day-lag-max`
- `doc:io:file.cio:master-file-file-cio`
- `doc:io:_general:introduction-to-swat`

Rules:

- **Deterministic.** Same corpus bytes in → same handles out, same
  order. Pinned by a test; changing the chunker is a contract change.
- **Slug convention.** Lowercase, dash-separated. Markdown escapes
  (`day\_start`) and HTML entities (`&#x20;`) are stripped before
  slugifying. Dots in filenames are preserved in the `<file>` segment
  but act as separators inside a slug.
- **Source-prefixed.** The `<source>` segment is `io` for I/O docs.
  Future sources will use their own prefix (`litdb`, etc.) and the
  Module 1 allowlist is keyed off the prefix.
- **Never invented.** The chunker only emits handles it derived from
  the corpus. Downstream code (e.g. Module 1's response formatter)
  validates every `[doc:<id>]` citation against the handles present
  in the passages it was given.

## Filters

R1 supports metadata-equality filtering. The only documented key is
`file`:

```python
retrieve("nutrients", filters={"file": "nutrients.sol"})
```

Filtering happens *before* BM25 ranking so a narrow filter still
returns up to `k` hits.

## Failure modes

- **Network error on first call.** Raises
  `swatplus_ai.retrieval.sources.io_docs.IODocsFetchError`. Callers
  that must not fail on network outages should catch it and fall back
  to an empty passage list — the retrieval layer never invents content.
- **Empty or whitespace-only query.** Returns `()` without touching
  the index.
- **No term overlap.** Returns `()` (BM25 scores of zero are dropped
  deliberately; they would be noise, not signal).
- **Corrupt index pickle.** Silently rebuilds from the cached corpus.

## What this slice does *not* do

- No embeddings, no hybrid rerank, no semantic search. Comes in R3+.
- No SWAT+ Literature Database. Phase 2, slice R2+.
- No calibration-tool profiles, no Moriasi papers. Later phases.
- No integration with Module 1's prompt builder. The prompt chat
  consumes `retrieve()` against this contract in a separate slice.
- No `filters` predicates beyond metadata equality on `file`. Keyed
  filtering by category / rev / tool is tracked for a future slice.
