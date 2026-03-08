import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def pytest_collection_modifyitems(config, items):
    run_integration = os.getenv("RUN_INTEGRATION_TESTS", "").lower() in {"1", "true", "yes"}
    run_parity = os.getenv("RUN_PARITY_TESTS", "").lower() in {"1", "true", "yes"}
    run_exhaustive = os.getenv("RUN_EXHAUSTIVE_TESTS", "").lower() in {"1", "true", "yes"}
    has_node = shutil.which("node") is not None

    skip_integration = pytest.mark.skip(reason="integration test; set RUN_INTEGRATION_TESTS=1 to run")
    skip_parity = pytest.mark.skip(reason="parity test; requires RUN_PARITY_TESTS=1 and node")
    skip_exhaustive = pytest.mark.skip(reason="exhaustive test; set RUN_EXHAUSTIVE_TESTS=1 to run")

    for item in items:
        if "integration" in item.keywords and not run_integration:
            item.add_marker(skip_integration)
        if "parity" in item.keywords and (not run_parity or not has_node):
            item.add_marker(skip_parity)
        if "exhaustive" in item.keywords and not run_exhaustive:
            item.add_marker(skip_exhaustive)
