"""Pre-processors: registered, typed, cached functions that turn tables into figures (ADR-0006).

A data file lists *steps* by registered name; :func:`preprocess_bundle` runs them and returns the
bundle with their figures and tables added. ``scireport.preprocess.core`` and ``.astro`` hold the
built-in catalogue, ported from the MOSAICS report plots.
"""

from __future__ import annotations

from scireport.preprocess.context import Context
from scireport.preprocess.look import Look
from scireport.preprocess.params import params_schema
from scireport.preprocess.plan import PlannedStep, plan_steps
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import (
  Preprocessor,
  get_preprocessor,
  list_preprocessors,
  preprocessor,
  register_preprocessor,
)
from scireport.preprocess.runner import (
  PreprocessResult,
  StepRecord,
  preprocess_bundle,
  write_back,
)

__all__ = [
  'Context',
  'Look',
  'PlannedStep',
  'Port',
  'PreprocessResult',
  'Preprocessor',
  'StepRecord',
  'get_preprocessor',
  'list_preprocessors',
  'params_schema',
  'plan_steps',
  'preprocess_bundle',
  'preprocessor',
  'register_preprocessor',
  'write_back',
]
