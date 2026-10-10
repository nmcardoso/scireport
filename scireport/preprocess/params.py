"""Parameter validation: a pydantic model built from the signature of a pre-processor (ADR-0006).

The parameters of a pre-processor are the keyword arguments of its function that are not its
context and not an input port. Their annotations and defaults are the schema: a wrong type, an
unknown name or a missing required parameter is reported with a pointer into the data file, the
expected type and a "did you mean" hint, together with every other problem of the step.
"""

from __future__ import annotations

import difflib
import inspect
import typing
from functools import cache
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, create_model

from scireport.errors import Issue
from scireport.preprocess.registry import Preprocessor

_MAX_FOUND_CHARS = 80


@cache
def params_model(entry: Preprocessor) -> type[BaseModel]:
  """Build the model that validates the parameters of a pre-processor.

  Parameters
  ----------
  entry : Preprocessor
      The registered pre-processor.

  Returns
  -------
  type of pydantic.BaseModel
      A model with one field per parameter, forbidding unknown names.

  Raises
  ------
  TypeError
      When a parameter is positional-only, variadic, or annotated with a type pydantic cannot
      validate (a programming error in the pre-processor).
  """
  signature = inspect.signature(entry.func)
  hints = typing.get_type_hints(entry.func, include_extras=True)
  fields: dict[str, Any] = {}
  for index, parameter in enumerate(signature.parameters.values()):
    if index == 0 or parameter.name in entry.inputs:
      continue
    if parameter.kind not in (parameter.KEYWORD_ONLY, parameter.POSITIONAL_OR_KEYWORD):
      raise TypeError(f'{entry.ref}: parameter {parameter.name!r} must be a named parameter')
    default = ... if parameter.default is parameter.empty else parameter.default
    fields[parameter.name] = (hints.get(parameter.name, Any), default)
  return create_model(
    f'Params[{entry.ref}]', __config__=ConfigDict(extra='forbid', frozen=True), **fields
  )


def validate_params(
  entry: Preprocessor, raw: dict[str, Any], pointer: str
) -> tuple[dict[str, Any], list[Issue]]:
  """Validate the parameters of one step.

  Parameters
  ----------
  entry : Preprocessor
      The pre-processor the step names.
  raw : dict
      The ``params`` object of the step (JSON values).
  pointer : str
      JSON pointer of the step's ``params``, for the issues.

  Returns
  -------
  tuple
      The validated parameters as keyword arguments (defaults filled in), and the issues found.
      The parameters are empty when there are issues.
  """
  model = params_model(entry)
  try:
    checked = model.model_validate(raw)
  except ValidationError as exc:
    return {}, _issues(entry, exc, raw, pointer, sorted(model.model_fields))
  return {name: getattr(checked, name) for name in model.model_fields}, []


def canonical_params(entry: Preprocessor, params: dict[str, Any]) -> dict[str, Any]:
  """Return the validated parameters as JSON values, for the cache key.

  Parameters
  ----------
  entry : Preprocessor
      The pre-processor.
  params : dict
      Validated parameters, as returned by :func:`validate_params`.

  Returns
  -------
  dict
      The same parameters in JSON form, sorted by name.
  """
  model = params_model(entry)
  dumped: dict[str, Any] = model.model_validate(params).model_dump(mode='json')
  return {name: dumped[name] for name in sorted(dumped)}


def params_schema(entry: Preprocessor) -> dict[str, Any]:
  """Return the JSON Schema of the parameters of a pre-processor, for agents and docs.

  Parameters
  ----------
  entry : Preprocessor
      The pre-processor.

  Returns
  -------
  dict
      A JSON Schema object with one property per parameter.
  """
  schema: dict[str, Any] = params_model(entry).model_json_schema()
  schema.pop('title', None)
  return schema


def _issues(
  entry: Preprocessor, error: ValidationError, raw: dict[str, Any], pointer: str, names: list[str]
) -> list[Issue]:
  """Turn a pydantic error into one ``E602`` issue per problem."""
  issues: list[Issue] = []
  for item in error.errors(include_url=False):
    location = [str(part) for part in item['loc']]
    where = '/'.join([pointer, *(part.replace('~', '~0').replace('/', '~1') for part in location)])
    hint = None
    expected: str | None = None
    found: str | None = None
    if item['type'] == 'extra_forbidden':
      close = difflib.get_close_matches(location[0], names, n=1)
      hint = (
        f'Did you mean {close[0]!r}?'
        if close
        else f'{entry.ref} takes: {", ".join(names) or "none"}.'
      )
    elif item['type'] != 'missing':
      expected = item['msg']
      found = _short(item.get('input'))
    issues.append(
      Issue(
        'E602',
        f'{entry.ref}: parameter {".".join(location)}: {item["msg"]}',
        where,
        expected=expected,
        found=found,
        hint=hint,
      )
    )
  return issues


def _short(value: object) -> str:
  """Render an input value briefly."""
  text = repr(value)
  return text if len(text) <= _MAX_FOUND_CHARS else text[: _MAX_FOUND_CHARS - 1] + '…'
