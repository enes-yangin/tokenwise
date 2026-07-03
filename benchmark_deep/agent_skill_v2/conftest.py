import importlib
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("DB_PATH", ":memory:")
    import main
    importlib.reload(main)  # rebuild app + fresh in-memory DB per test
    with TestClient(main.app) as c:
        yield c
