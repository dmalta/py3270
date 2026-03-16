from __future__ import annotations

import pytest


pytestmark = pytest.mark.integration


def test_s3270_binary_available(s3270_path: str) -> None:
    assert s3270_path
