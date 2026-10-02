"""Write sample messy papers to backend/tests/fixtures/ for manual testing."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.samples import messy_paper  # noqa: E402

out = ROOT / "tests" / "fixtures" / "messy_paper.docx"
out.write_bytes(messy_paper())
print(f"wrote {out}")
