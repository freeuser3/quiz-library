import os

import pytest

GEO_DIGEST_PATH = os.environ.get("GEO_DIGEST_PATH", "")


@pytest.fixture()
def geo_digest_path() -> str:
    if not GEO_DIGEST_PATH:
        pytest.skip("GEO_DIGEST_PATH not set")
    return GEO_DIGEST_PATH