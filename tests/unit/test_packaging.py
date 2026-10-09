import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILL = 'scireport/agent/skill/scireport/SKILL.md'
SCHEMA = 'scireport/spec/schemas/data-1.0.schema.json'


@pytest.mark.skipif(
  shutil.which('uv') is None or not (ROOT / '.git').exists(), reason='needs uv and a git checkout'
)
def test_wheel_and_sdist_ship_the_packaged_skill(tmp_path: Path) -> None:
  """Guards against hatch dropping the skill because of the ``.agents/skills`` symlink."""
  subprocess.run(
    ['uv', 'build', '--out-dir', str(tmp_path)],
    cwd=ROOT,
    check=True,
    capture_output=True,
    timeout=300,
  )
  wheel = next(tmp_path.glob('*.whl'))
  sdist = next(tmp_path.glob('*.tar.gz'))
  with zipfile.ZipFile(wheel) as zf:
    assert SKILL in zf.namelist()
    assert SCHEMA in zf.namelist()
  with tarfile.open(sdist) as tf:
    assert any(name.endswith(SKILL) for name in tf.getnames())
    assert any(name.endswith(SCHEMA) for name in tf.getnames())
