import os
from pathlib import Path

TEST_DB = Path("/tmp/orderyourself_smoke.db")
TEST_DB.unlink(missing_ok=True)
os.environ["DATABASE_PATH"] = str(TEST_DB)

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def test_core_pages_start():
    with TestClient(app) as client:
        for path in ["/health/live", "/health/ready", "/", "/recipes", "/recipes/book", "/shopping", "/household"]:
            response = client.get(path)
            assert response.status_code == 200, (path, response.text[:300])


def test_post_requires_csrf():
    with TestClient(app) as client:
        client.get("/shopping")
        response = client.post("/shopping/manual", data={"name": "Milch"}, follow_redirects=False)
        assert response.status_code == 403
