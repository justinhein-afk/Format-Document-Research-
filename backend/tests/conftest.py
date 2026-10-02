import pytest

from tests.samples import messy_paper


@pytest.fixture(scope="session")
def paper_bytes() -> bytes:
    return messy_paper()
