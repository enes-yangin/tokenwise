"""Test fixture'ları — her test için temiz :memory: DB."""
import os

import pytest

os.environ["APP_DB"] = ":memory:"


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app import db

    db.reset_for_tests()
    from app.main import app

    with TestClient(app) as c:
        yield c
    db.reset_for_tests()
