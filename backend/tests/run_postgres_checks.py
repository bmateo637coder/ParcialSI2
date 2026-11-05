"""Pruebas de concurrencia en una base LOCAL desechable, separada del proyecto."""
import os
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from app.core.config import settings

url = make_url(settings.sqlalchemy_database_url)
if not url.drivername.startswith('postgresql') or url.host not in {'localhost', '127.0.0.1', '::1'}:
    raise SystemExit('Esta comprobación solo usa PostgreSQL local.')
database = 'fashionstore_check_' + uuid.uuid4().hex
admin = create_engine(url.set(database='postgres'), isolation_level='AUTOCOMMIT')
with admin.connect() as connection:
    connection.execute(text(f'CREATE DATABASE "{database}"'))
try:
    environment = dict(os.environ, TEST_DATABASE_URL=url.set(database=database).render_as_string(hide_password=False))
    result = subprocess.run([sys.executable, '-m', 'pytest',
        'tests/test_sales_audit.py', 'tests/test_business_integrity.py', 'tests/test_refunds.py',
        'tests/test_deploy.py', 'tests/test_serverless.py', '-q', '--tb=short'], env=environment)
finally:
    with admin.connect() as connection:
        connection.execute(text('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:name AND pid<>pg_backend_pid()'), {'name':database})
        connection.execute(text(f'DROP DATABASE "{database}"'))
    admin.dispose()
sys.exit(result.returncode)
