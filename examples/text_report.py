"""Example 3, a text-only report: prose, lists, math and code, with no data and no figures."""

from __future__ import annotations

from scireport import Report


def build(layout: str = 'default') -> Report:
  """Build the report.

  Parameters
  ----------
  layout : str, default='default'
      The layout the bundle names.

  Returns
  -------
  Report
      The report.
  """
  report = Report(
    'Design notes: a reproducible pipeline',
    subtitle='Why the report is built from a data file',
    authors=['N. Cardoso'],
    date='2026-10-09',
    version='0.3',
    abstract=(
      'Notes on keeping numbers, tables and figures **regenerable**: one data file in, '
      'Markdown, HTML, LaTeX and PDF out.'
    ),
    keywords=['reproducibility', 'notes'],
  )
  report.add_text(
    'motivation.text',
    'A report that is typed by hand drifts from the analysis that produced it. A number in a '
    'sentence is copied once and then stays when the analysis moves on.\n\n'
    'The cure is to make the report a function of its inputs:\n\n'
    '1. the analysis writes **values** (numbers, tables, figures) to a data file;\n'
    '2. a **template** says in what order they appear;\n'
    '3. a **layout** says what they look like.\n\n'
    'Changing the look then never touches the content, and changing the content never touches '
    'the look.',
    format='markdown',
  )
  report.add_text(
    'principles.text',
    'Three rules follow from this.\n\n'
    '- **No number is typed.** Every figure in the text is read from the data file.\n'
    '- **Output is deterministic.** The same inputs give the same bytes, so a diff of two '
    'reports is a diff of two analyses.\n'
    '- **Failure is loud.** A missing value is an error with a code, never an empty cell.\n\n'
    '> A report is evidence. Evidence that changes when you look at it twice is not evidence.',
    format='markdown',
  )
  report.add_math(
    'principles.error',
    r'\sigma_{\bar x} = \frac{\sigma}{\sqrt{N}}',
    numbered=True,
    caption='The uncertainty of a mean falls as the square root of the sample size.',
  )
  report.add_code(
    'usage.code',
    'from scireport import Report\n\n'
    "report = Report('A title')\n"
    "report.add_number('result.n', 3061, format='int')\n"
    "report.write('run.scireport.zip')\n",
    language='python',
    caption='The whole workflow in four lines.',
  )
  report.add_text(
    'usage.text',
    'Rendering is one command: `scireport render run.scireport.zip -o out`. Add `-f pdf` for a '
    'PDF, `-l modern` for the other look.',
    format='markdown',
  )
  report.set_outline(
    [
      {'title': 'Motivation', 'children': ['motivation.text']},
      {
        'title': 'Principles',
        'children': ['principles.text', 'principles.error'],
      },
      {'title': 'Usage', 'children': ['usage.text', 'usage.code']},
    ]
  )
  report.set_render(template='generic@1', layout=f'{layout}@1')
  return report
