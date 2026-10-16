import shutil
import sys
from pathlib import Path

import pytest

STARTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STARTER))

from agentic import config  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_dbs(tmp_path, monkeypatch):
    """Run every test against fresh copies of the databases built by notebooks 01 and 02."""
    for name, path in [("UDAHUB_DB_PATH", config.UDAHUB_DB_PATH), ("CULTPASS_DB_PATH", config.CULTPASS_DB_PATH)]:
        if not path.exists():
            pytest.skip(f"{path} missing: run 01_external_db_setup and 02_core_db_setup first")
        copy = tmp_path / path.name
        shutil.copy(path, copy)
        monkeypatch.setattr(config, name, copy)
    yield
