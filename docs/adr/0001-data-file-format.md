# ADR-0001: Data-file format is a report bundle (ZIP + JSON manifest + native assets)

- Status: Accepted (HG-S0, 2026-10-09)
- Date: 2026-10-09

## Context

A report needs structure (text, numbers, metadata) and binary artifacts (tables, figures, images). The file must
be compact, inspectable by humans and coding agents, safe to open, deterministic to write, and readable by every
later version of the package.

## Decision

A **report bundle** is either `<name>.scireport.zip` or a `<name>.scireport/` directory with the same layout:

- `scireport.json` is the manifest and single source of truth. YAML (`scireport.yaml`) is accepted only for
  hand-authored directories; `scireport pack` converts it to JSON.
- `assets/{tables,figures,images,text,attachments}/...` holds each artifact in its native format: tables as
  Parquet (zstd) or CSV; figures as PNG, PDF and optional SVG with sidecar data in Parquet; long text as
  Markdown; attachments as CSV.
- Every asset carries `sha256` and `bytes` in the manifest.
- A bare `.json` or `.yaml` file with relative asset paths is also accepted, for text-only reports.

Rules: a bundle holds **summaries, not raw catalogues** (aggregate first, for example HEALPix counts instead of
1.3 M positions). ZIPs are byte-reproducible (sorted entries, fixed 1980 timestamps, STORED for media that is
already compressed). The reader rejects zip-slip paths and enforces a size cap.

## Alternatives considered

| Format | Verdict |
|---|---|
| YAML / JSON alone | Fine for structure, but binary data needs base64 (+33 %). YAML adds typing ambiguity. |
| Pickle | Rejected: executes arbitrary code on load and is tied to Python versions. |
| HDF5 | Rejected: needs the heavy C library h5py; figures and tables become opaque blobs that agents and git diffs cannot read; corrupts on interrupted writes. Its strength, large numeric arrays, is not what a report carries. |
| **ZIP + JSON manifest + native assets** (like OOXML, EPUB, Frictionless Data Package) | Chosen: standard library only, each asset in its best format, inspectable, lazy reads, the unpacked directory diffs in git, integrity from hashes. |

## Consequences

Producers must aggregate before packing. Consumers can inspect a bundle with `unzip`. Integrity is verifiable
without trusting the producer's Python version.
