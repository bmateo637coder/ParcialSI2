"""El arranque serverless no modifica el esquema ni necesita una conexión."""
import os
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def hosted_settings(**overrides):
    values = dict(VERCEL=True, AUTO_INIT_DB=None,
        DATABASE_URL="postgresql://demo:demo@localhost/fashionstore",
        SECRET_KEY="serverless-test-secret-32-characters")
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_hosted_configuration_uses_external_database_and_explicit_driver():
    config = hosted_settings()
    assert not config.auto_init_db
    assert config.sqlalchemy_database_url.startswith("postgresql+psycopg2://")
    assert Settings(_env_file=None, VERCEL=False).auto_init_db


@pytest.mark.parametrize("overrides", [
    {"DATABASE_URL": "sqlite:///./fashionstore.db"},
    {"SECRET_KEY": "dev-secret-key-no-usar-en-produccion"},
    {"AUTO_INIT_DB": True},
])
def test_hosted_configuration_rejects_unsafe_defaults(overrides):
    with pytest.raises(ValidationError):
        hosted_settings(**overrides)


def test_serverless_import_and_startup_never_connect_or_seed():
    environment = dict(os.environ, VERCEL="1", AUTO_INIT_DB="false", AUTO_SEED="true",
        DATABASE_URL="postgresql://unused:unused@127.0.0.1:1/unused",
        SECRET_KEY="serverless-test-secret-32-characters")
    code = '''
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.pool import NullPool
with patch("sqlalchemy.engine.Engine.connect", side_effect=AssertionError("Unexpected database access")):
    from main import app
    from app.core.database import engine
    assert isinstance(engine.pool, NullPool)
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["version"] == "2.0.0"
'''
    result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
        env=environment, text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
