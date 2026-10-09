"""Validation: everything that can be known before rendering, reported at once (ADR-0005)."""

from __future__ import annotations

from scireport.bundle.reader import Bundle
from scireport.errors import Issue, TemplateError
from scireport.render.components import COMPONENT_MACROS
from scireport.render.definition import Format, spec_in_range
from scireport.render.environment import EnvKind
from scireport.render.layout import Layout
from scireport.render.template import Template
from scireport.validate.checks import check_fields, check_values
from scireport.validate.lint import KeyUse, LintResult, lint_files, macro_names, suggest
from scireport.validate.report import ValidationReport, dedupe

__all__ = ['ValidationReport', 'validate_bundle', 'validate_definitions']


def validate_bundle(
  bundle: Bundle,
  template: Template,
  layout: Layout,
  formats: list[Format],
  *,
  options: dict[str, object] | None = None,
  strict: bool = False,
) -> ValidationReport:
  """Validate a bundle for a template, a layout and the formats to write.

  Parameters
  ----------
  bundle : Bundle
      The opened bundle.
  template : Template
      The template.
  layout : Layout
      The layout.
  formats : list of {'md', 'html', 'tex'}
      The formats about to be written.
  options : dict or None, default=None
      Layout options given by the caller; checked against the layout (``E806``).
  strict : bool, default=False
      Make warnings fail the validation.

  Returns
  -------
  ValidationReport
      Every problem found: asset integrity (``E401`` to ``E403``), the spec range and formats
      the template and layout support, the layout options, template syntax and the keys it
      reads (``E106``), the values it declares (``E105``, ``E207``, ``E303`` to ``E305``),
      number formats, raw LaTeX, figures and math.
  """
  issues: list[Issue] = [i for i in bundle.verify() if i.severity == 'error' or i.code == 'W402']
  issues.extend(validate_definitions(template, layout, formats, bundle.manifest.scireport))
  try:
    layout.resolve_options({k: v for k, v in (options or {}).items()})
  except TemplateError as exc:
    issues.extend(exc.issues)
  lint = _lint_template(template, formats)
  issues.extend(lint.issues)
  issues.extend(_unknown_keys(lint, bundle))
  issues.extend(check_fields(template, bundle))
  issues.extend(check_values(bundle, formats))
  return ValidationReport(tuple(dedupe(issues)), strict)


def validate_definitions(
  template: Template, layout: Layout, formats: list[Format], spec_version: str
) -> list[Issue]:
  """Check that a template and a layout can render the formats for a bundle's spec version.

  Parameters
  ----------
  template : Template
      The template.
  layout : Layout
      The layout.
  formats : list of {'md', 'html', 'tex'}
      The formats about to be written.
  spec_version : str
      The spec version of the bundle, for example ``'1.0'``.

  Returns
  -------
  list of Issue
      ``E505`` (spec range), ``E706`` (format), ``E703`` / ``E704`` (layout files that are
      missing or do not parse) and ``E707`` (a component macro the layout does not define).
  """
  issues: list[Issue] = []
  for what, ref, spec in (
    ('template', template.ref, template.definition.spec),
    ('layout', layout.ref, layout.definition.spec),
  ):
    if not spec_in_range(spec, spec_version):
      issues.append(
        Issue(
          'E505',
          f'{what} {ref} supports data-file spec {spec}, but the bundle uses {spec_version}',
          expected=spec,
          found=spec_version,
          hint='Use a template or layout version that supports this spec.',
        )
      )
  for fmt in formats:
    if fmt not in template.definition.formats:
      issues.append(
        Issue('E706', f'template {template.ref} does not support the {fmt} format', found=fmt)
      )
    if fmt not in layout.definition.formats:
      issues.append(
        Issue('E706', f'layout {layout.ref} does not support the {fmt} format', found=fmt)
      )
      continue
    files = layout.files(fmt)
    result = lint_files(layout.root, [files.document, files.components], fmt)
    issues.extend(i for i in result.issues if i.code != 'W403')
    defined = macro_names(layout.root, files.components, fmt)
    if defined is not None:
      issues.extend(
        Issue(
          'E707',
          f'layout {layout.ref} does not define the {name!r} component for {fmt}',
          location=files.components,
        )
        for name in COMPONENT_MACROS
        if name not in defined
      )
  return issues


def _lint_template(template: Template, formats: list[Format]) -> LintResult:
  """Lint the template body of every format (the neutral body once)."""
  uses: list[KeyUse] = []
  issues: list[Issue] = []
  neutral_done = False
  for fmt in formats:
    kind: EnvKind
    if template.is_neutral(fmt):
      if neutral_done:
        continue
      neutral_done = True
      kind = 'neutral'
    else:
      kind = fmt
    result = lint_files(template.root, [template.entry_for(fmt)], kind)
    uses.extend(result.uses)
    issues.extend(result.issues)
  if template.definition.dynamic_keys:
    issues = [issue for issue in issues if issue.code != 'W403']
  return LintResult(tuple(uses), tuple(dedupe(issues)))


def _unknown_keys(lint: LintResult, bundle: Bundle) -> list[Issue]:
  """Report ``E106`` for every key the template reads that the bundle does not have."""
  keys = set(bundle.manifest.values)
  prefixes = {'.'.join(k.split('.')[:n]) for k in keys for n in range(1, len(k.split('.')))}
  issues = []
  for use in lint.uses:
    walked = ''
    for segment in use.segments:
      walked = f'{walked}.{segment}' if walked else segment
      if walked in keys or (use.dynamic and walked in prefixes):
        break
      if walked in prefixes:
        continue
      issues.append(
        Issue(
          'E106',
          f'the template reads key {walked!r}, which the bundle does not have',
          pointer='/values',
          key=walked,
          hint=suggest(walked, sorted(keys)),
          location=use.location,
        )
      )
      break
  return issues
