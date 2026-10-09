---
name: python-logging
description: Standard Python logging for TUPAN code. Uses stdlib logging with readable logger names (never __main__), timestamps, level icons, colour-coded module names and messages, rules and sections for visual structure, and plain plus JSON-lines file logs. Use for any script, pipeline, analysis or training code. For experiment tracking see the wandb-logging skill.
---

# Python logging (TUPAN)

## Setup
Copy `logging_utils.py` into the subproject package. Configure logging **once**, in the entry point (the CLI command),
never at import time:
```python
from tupan_review.logging_utils import setup_logging, get_logger, log_rule, log_section, log_kv

setup_logging(
    level="INFO", log_file=f"logs/{run_id}/run.log", jsonl_file=f"logs/{run_id}/run.jsonl"
)
log = get_logger(__name__)
```
In every other module, put `log = get_logger(__name__)` at the top. Never use `print()` for diagnostics; `typer.echo`
is only for output that is the command's result.

## Line format (console)
`2026-11-03 14:22:05.123 │ ℹ INFO     │ ▌review.an01_bibliometrics │ Fetched 1,234 records (query=Q1, years=2015–2026)`

- **Fields.** Timestamp; level icon and name; the **high-level module name** (package prefix shortened; `__main__`
  resolved to the real module path or the script name); the message.
- **Colours.** The module name and the message share a colour, derived from a stable hash of the module name. Levels
  have their own colours and icons: · DEBUG, ℹ INFO, ⚠ WARNING, ✖ ERROR, ‼ CRITICAL.
- **Structure helpers.**
  - `log_rule(log, "Phase 2 · Screening")` draws a coloured horizontal rule.
  - `log_section(log, "…")` brackets a block with ▶ start, then ✔ done with elapsed time, or ✖ failed with traceback.
  - `log_kv(log, title, mapping)` prints an aligned key = value block and attaches it as structured fields in the JSON log.
- **Outputs.** Colours switch off automatically for non-TTY streams and when `NO_COLOR=1`. Files are always plain text
  (`run.log`) and JSON lines (`run.jsonl`).

## What to log
- **At the start of a command:** a `log_rule` with the command name, then a `log_kv` of the resolved configuration
  (paths, dates, seeds, package versions, git commit).
- **For each step:** what is done, on what (counts, ids, paths) and with which parameters. At the end, the outputs
  written (paths, row counts, checksums) and the elapsed time.
- **For every external call:** endpoint (without secrets), query, page or offset, HTTP status, retries, rows returned,
  cache hit or miss.
- **For every filter that drops data:** how many records were removed and why (criterion code).
- **Problems.**
  - WARNING for anomalies that do not stop the run (missing fields, fallbacks, rate limits).
  - ERROR for a failed unit of work, with its identifier.
  - `log.exception(...)` inside `except` blocks.
- **Never log** secrets, tokens, personal e-mail addresses or long copyrighted text.
- Use lazy formatting: `log.info("Fetched %d records for %s", n, query)`.

Levels:
- DEBUG: internals for debugging.
- INFO: milestones, counts and outputs.
- WARNING: a recoverable anomaly.
- ERROR: a unit of work failed.
- CRITICAL: the run must abort.
