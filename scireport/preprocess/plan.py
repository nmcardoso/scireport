"""Check the steps of a data file and order them, before anything runs (ADR-0006).

:func:`plan_steps` resolves every step to a registered pre-processor, validates its parameters,
wires its input ports to value keys, checks the kinds, and sorts the steps so that a step runs
after the steps that make its inputs. Every problem of every step is collected and raised
together as one :class:`~scireport.errors.PreprocessError`; nothing has run by then.

A step *owns* the keys it lists in ``outputs``. If the manifest already holds a value at such a
key (a bundle that was written back after a run) the step replaces it; two steps that name the
same output key, or a step that reads a key that no value and no step provides, are errors.
"""

from __future__ import annotations

import difflib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from scireport.errors import Issue, PreprocessError
from scireport.preprocess.params import validate_params
from scireport.preprocess.registry import Preprocessor, get_preprocessor
from scireport.spec.keys import is_valid_key
from scireport.spec.manifest import Manifest, PreprocessStep


@dataclass(frozen=True)
class PlannedStep:
  """One step, resolved and checked.

  Parameters
  ----------
  index : int
      Position of the step in the data file's ``preprocess`` list.
  step : PreprocessStep
      The step as written.
  entry : Preprocessor
      The pre-processor it names.
  params : dict
      Validated parameters (defaults filled in), ready to pass as keyword arguments.
  inputs : dict
      Input port name to the value key it reads (only the wired ports).
  outputs : dict
      Output port name to the value key it writes.
  """

  index: int
  step: PreprocessStep
  entry: Preprocessor
  params: dict[str, Any]
  inputs: dict[str, str]
  outputs: dict[str, str]

  @property
  def label(self) -> str:
    """The step's id, or its name and position when it has none."""
    return self.step.id or f'{self.step.name}#{self.index}'


def plan_steps(manifest: Manifest, *, allow_import: bool = False) -> list[PlannedStep]:
  """Resolve, check and order the ``preprocess`` steps of a manifest.

  Parameters
  ----------
  manifest : Manifest
      The manifest whose steps are planned.
  allow_import : bool, default=False
      Let a step name ``module:function`` (imports code).

  Returns
  -------
  list of PlannedStep
      The steps in an order that runs every step after the producers of its inputs; steps with
      no dependency between them keep their written order.

  Raises
  ------
  PreprocessError
      Carrying every problem found: unknown pre-processors (``E601``), invalid parameters
      (``E602``), ports that do not fit (``E603``), duplicate output keys and cycles (``E604``)
      and imports that are not allowed (``E605``).
  """
  issues: list[Issue] = []
  resolved: list[PlannedStep] = []
  for index, step in enumerate(manifest.preprocess):
    pointer = f'/preprocess/{index}'
    try:
      entry = get_preprocessor(
        step.name, step.version, allow_import=allow_import, pointer=f'{pointer}/name'
      )
    except PreprocessError as exc:
      issues.extend(exc.issues)
      continue
    params, problems = validate_params(entry, dict(step.params), f'{pointer}/params')
    issues.extend(problems)
    inputs, outputs, port_issues = _wire(step, entry, pointer)
    issues.extend(port_issues)
    resolved.append(PlannedStep(index, step, entry, params, inputs, outputs))

  producers = _producers(resolved, issues)
  issues.extend(_check_inputs(resolved, producers, manifest))
  order = _order(resolved, producers, issues)
  if issues:
    raise PreprocessError(issues)
  return order


def _wire(
  step: PreprocessStep, entry: Preprocessor, pointer: str
) -> tuple[dict[str, str], dict[str, str], list[Issue]]:
  """Match the step's ``inputs`` and ``outputs`` to the pre-processor's ports."""
  issues: list[Issue] = []
  inputs: dict[str, str] = {}
  for port, key in step.inputs.items():
    if port not in entry.inputs:
      issues.append(_unknown_port('input', port, entry.inputs, f'{pointer}/inputs/{port}'))
    else:
      inputs[port] = key
  for port, spec in entry.inputs.items():
    if port not in step.inputs and not spec.optional:
      issues.append(
        Issue(
          'E603',
          f'{entry.ref}: input port {port!r} ({spec.kind}) is not wired',
          f'{pointer}/inputs',
          expected=f'a key for {port!r}',
          hint=f'Add inputs: {{{port}: <key of a {spec.kind}>}}.',
        )
      )
  outputs: dict[str, str] = {}
  for port, key in step.outputs.items():
    if port not in entry.outputs:
      issues.append(_unknown_port('output', port, entry.outputs, f'{pointer}/outputs/{port}'))
    elif not is_valid_key(key):
      issues.append(
        Issue('E101', f'invalid output key {key!r}', f'{pointer}/outputs/{port}', key=key)
      )
    else:
      outputs[port] = key
  for port, spec in entry.outputs.items():
    if port not in step.outputs and not spec.optional:
      issues.append(
        Issue(
          'E603',
          f'{entry.ref}: output port {port!r} ({spec.kind}) has no key to be stored under',
          f'{pointer}/outputs',
          hint=f'Add outputs: {{{port}: <new key>}}.',
        )
      )
  return inputs, outputs, issues


def _unknown_port(direction: str, port: str, ports: Any, pointer: str) -> Issue:
  """Build the ``E603`` issue for a port the pre-processor does not have."""
  names = sorted(ports)
  close = difflib.get_close_matches(port, names, n=1)
  hint = f'Did you mean {close[0]!r}?' if close else f'Its {direction} ports: {", ".join(names)}.'
  return Issue('E603', f'unknown {direction} port {port!r}', pointer, hint=hint)


def _producers(resolved: Sequence[PlannedStep], issues: list[Issue]) -> dict[str, PlannedStep]:
  """Map each output key to the step that writes it; report keys written twice."""
  producers: dict[str, PlannedStep] = {}
  for planned in resolved:
    for port, key in planned.outputs.items():
      other = producers.get(key)
      if other is not None:
        issues.append(
          Issue(
            'E604',
            f'steps {other.label!r} and {planned.label!r} both write the key {key!r}',
            f'/preprocess/{planned.index}/outputs/{port}',
            key=key,
          )
        )
      else:
        producers[key] = planned
  return producers


def _check_inputs(
  resolved: Sequence[PlannedStep], producers: dict[str, PlannedStep], manifest: Manifest
) -> list[Issue]:
  """Check that every wired input exists and has the kind its port wants."""
  issues: list[Issue] = []
  known = sorted({*manifest.values, *producers})
  for planned in resolved:
    for port, key in planned.inputs.items():
      pointer = f'/preprocess/{planned.index}/inputs/{port}'
      want = planned.entry.inputs[port]
      producer = producers.get(key)
      if producer is not None:
        found = _output_kind(producer, key)
      elif key in manifest.values:
        found = manifest.values[key].kind
      else:
        close = difflib.get_close_matches(key, known, n=1)
        issues.append(
          Issue(
            'E603',
            f'{planned.entry.ref}: input {port!r} reads {key!r}, which no value or step provides',
            pointer,
            key=key,
            hint=f'Did you mean {close[0]!r}?' if close else None,
          )
        )
        continue
      if found is not None and not want.accepts(found):
        issues.append(
          Issue(
            'E603',
            f'{planned.entry.ref}: input {port!r} wants a {want.kind}, but {key!r} is a {found}',
            pointer,
            key=key,
            expected=want.kind,
            found=found,
          )
        )
  return issues


def _output_kind(producer: PlannedStep, key: str) -> str | None:
  """Return the kind of the port of ``producer`` that writes ``key``."""
  for port, written in producer.outputs.items():
    if written == key:
      return (
        producer.entry.outputs[port].kind if producer.entry.outputs[port].kind != 'any' else None
      )
  return None


def _order(
  resolved: list[PlannedStep], producers: dict[str, PlannedStep], issues: list[Issue]
) -> list[PlannedStep]:
  """Sort the steps so producers come first (Kahn's algorithm, ties in written order)."""
  needs: dict[int, set[int]] = {planned.index: set() for planned in resolved}
  for planned in resolved:
    for key in planned.inputs.values():
      producer = producers.get(key)
      if producer is not None and producer.index != planned.index:
        needs[planned.index].add(producer.index)
      elif producer is not None:
        issues.append(
          Issue(
            'E604',
            f'step {planned.label!r} reads the key {key!r} that it writes itself',
            f'/preprocess/{planned.index}',
            key=key,
          )
        )
  by_index = {planned.index: planned for planned in resolved}
  done: list[PlannedStep] = []
  waiting = dict(needs)
  while waiting:
    ready = sorted(index for index, deps in waiting.items() if not deps)
    if not ready:
      cycle = ', '.join(repr(by_index[index].label) for index in sorted(waiting))
      issues.append(
        Issue('E604', f'the steps {cycle} depend on each other in a cycle', '/preprocess')
      )
      break
    index = ready[0]
    done.append(by_index[index])
    del waiting[index]
    for deps in waiting.values():
      deps.discard(index)
  return done
