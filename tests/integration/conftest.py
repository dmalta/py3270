from __future__ import annotations

import shutil

import pytest


@pytest.fixture(scope="session")
def s3270_path() -> str:
    path = shutil.which("s3270")
    if path is None:
        pytest.skip("s3270 binary not found on PATH; skipping integration tests")
    return path
