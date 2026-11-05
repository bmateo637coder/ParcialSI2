"""La migración no sobrescribe destinos y conserva los datos y secuencias."""
import os
from pathlib import Path
import subprocess
import sys
import uuid

import pytest
from sqlalchemy import create_engine, text

from deploy import migrate, postgres_url, target_url, pg_environment


def test_neon_migration_requires_explicit_direct_postgres_destination():
    for value in (None, "sqlite:///fashionstore.db"):
        with pytest.raises(ValueError):
            postgres_url(value)
    with pytest.raises(ValueError, match="DIRECTA"):
        target_url({"NEON_DATABASE_URL_DIRECT": "postgresql://demo:demo@ep-demo-pooler.neon.tech/db"})
    with pytest.raises(ValueError, match="misma base"):
        url = postgres_url("postgresql://demo:demo@localhost/db")
        migrate(url, url, Path("unused-backup"))


def test_pg_credentials_are_environment_values_not_command_arguments():
    url = postgres_url("postgresql://demo:private%40password@ep-demo.neon.tech/neondb?sslmode=require&channel_binding=require")
    environment = pg_environment(url)
    assert environment["PGPASSWORD"] == "private@password"
    assert environment["PGSSLMODE"] == "require"
    assert environment["PGCHANNELBINDING"] == "require"


def test_postgres_backup_restore_keeps_records_and_sequences(client, catalog, tmp_path):
    from app.core.database import engine
    source = engine.url
    if engine.dialect.name != "postgresql":
        pytest.skip("Verificación real de pg_dump y pg_restore en PostgreSQL local")
    if source.host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.skip("La prueba solo crea bases temporales en PostgreSQL local")
    database = "fashionstore_migration_check_" + uuid.uuid4().hex
    admin = create_engine(source.set(database="postgres"), isolation_level="AUTOCOMMIT")
    target = source.set(database=database)
    target_engine = create_engine(target)
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database}"'))
    try:
        with engine.connect() as connection:
            original_password = connection.execute(text("SELECT hashed_password FROM users WHERE email='admin@test.com'")).scalar_one()
        counts = migrate(source, target, tmp_path)
        assert counts["inventory"] > 0
        assert len(list(tmp_path.glob("*.dump"))) == 1
        with target_engine.begin() as connection:
            assert connection.execute(text("SELECT hashed_password FROM users WHERE email='admin@test.com'")).scalar_one() == original_password
            previous = connection.execute(text("SELECT MAX(id) FROM colors")).scalar_one()
            inserted = connection.execute(text("INSERT INTO colors (name) VALUES (:name) RETURNING id"),
                {"name": "After restore " + uuid.uuid4().hex}).scalar_one()
            assert inserted > previous
        with pytest.raises(ValueError, match="ya contiene"):
            migrate(source, target, tmp_path)
        environment = dict(os.environ, NEON_DATABASE_URL_DIRECT=target.render_as_string(hide_password=False))
        result = subprocess.run([sys.executable, "deploy.py", "init"],
            cwd=Path(__file__).resolve().parents[1], env=environment, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
        with target_engine.connect() as connection:
            assert connection.execute(text("SELECT hashed_password FROM users WHERE email='admin@test.com'")).scalar_one() == original_password
    finally:
        target_engine.dispose()
        with admin.connect() as connection:
            connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:name AND pid<>pg_backend_pid()"), {"name": database})
            connection.execute(text(f'DROP DATABASE "{database}"'))
        admin.dispose()
