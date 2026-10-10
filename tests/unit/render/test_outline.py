from scireport.render.outline import INDEX_FILE, Outline


def test_anchors_are_unique_and_ordered() -> None:
  outline = Outline()
  entries = [outline.chapter('A'), outline.heading('B'), outline.heading('C', 2)]
  assert [e.anchor for e in entries] == ['a1', 'a2', 'a3']


def test_numbering_follows_chapters_and_levels() -> None:
  outline = Outline()
  outline.chapter('One')
  outline.heading('One.one')
  outline.heading('One.one.one', 2)
  outline.heading('One.two')
  outline.chapter('Two')
  outline.heading('Two.one')
  assert [e.number for e in outline.entries] == ['1', '1.1', '1.1.1', '1.2', '2', '2.1']


def test_headings_before_a_chapter_count_from_one() -> None:
  outline = Outline()
  first = outline.heading('Loose')
  assert first.number == '1'


def test_unlisted_headings_are_not_numbered_or_listed() -> None:
  outline = Outline()
  outline.chapter('One')
  hidden = outline.heading('Hidden', in_contents=False)
  shown = outline.heading('Shown')
  assert hidden.number == ''
  assert shown.number == '1.1'
  assert [e.text for e in outline.entries] == ['One', 'Shown']


def test_deep_levels_are_clamped_to_three() -> None:
  outline = Outline()
  outline.chapter('A')
  assert outline.heading('x', 9).level == 3


def test_slugs_follow_github_and_are_unique_per_file() -> None:
  outline = Outline()
  slugs = [outline.heading(t).slug for t in ('Hello, World!', 'Hello World', 'a_b c')]
  assert slugs == ['hello-world', 'hello-world-1', 'a_b-c']
  outline.chapter('Next', md_file='next.md')
  assert outline.heading('Hello World').slug == 'hello-world'


def test_markdown_files_are_tracked() -> None:
  outline = Outline()
  assert outline.current_file == INDEX_FILE
  outline.chapter('A', md_file='a.md')
  inside = outline.heading('Inside')
  outline.chapter('B')
  outline.chapter('C', md_file='c.md')
  assert inside.md_file == 'a.md'
  assert outline.files == [INDEX_FILE, 'a.md', 'c.md']
  assert outline.current_file == 'c.md'
