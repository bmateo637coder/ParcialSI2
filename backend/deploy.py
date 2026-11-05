"""Prepara Neon sin borrar datos: respaldo, restauración en vacío y verificación.

Las credenciales se leen del entorno o de .env.deploy; nunca de argumentos CLI.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from dotenv import dotenv_values
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

BACKEND = Path(__file__).resolve().parent


def postgres_url(value):
    if not value:
        raise ValueError("Falta la conexión de PostgreSQL en el archivo de entorno.")
    url = make_url(value)
    if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg2"}:
        raise ValueError("Esta migración necesita PostgreSQL en origen y destino.")
    return url.set(drivername="postgresql+psycopg2")


def target_url(environment):
    url = postgres_url(environment.get("NEON_DATABASE_URL_DIRECT"))
    if "-pooler." in (url.host or ""):
        raise ValueError("Usa la conexión DIRECTA de Neon para migraciones, sin -pooler.")
    return url


def pg_environment(url):
    # No pasar contraseñas ni cadenas de conexión en la línea de comandos.
    environment = {key: value for key, value in os.environ.items() if not key.startswith("PG")}
    environment.update(PGHOST=url.host or "localhost", PGPORT=str(url.port or 5432),
        PGDATABASE=url.database or "", PGUSER=url.username or "", PGPASSWORD=url.password or "",
        PGCONNECT_TIMEOUT="15", PGAPPNAME="fashionstore-migration")
    for key, value in url.query.items():
        if key in {"sslmode", "sslrootcert", "channel_binding"}:
            environment["PG" + key.replace("_", "").upper()] = value
    return environment


def pg_tool(name):
    executable = shutil.which(name)
    if executable:
        return executable
    if os.name == "nt":
        install_root = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "PostgreSQL"
        versions = sorted(install_root.glob(f"*/bin/{name}.exe"), reverse=True)
        if versions:
            return str(versions[0])
    raise ValueError(f"No se encontró {name}. Instala las herramientas cliente de PostgreSQL.")


def run_pg(command, url):
    result = subprocess.run(command, env=pg_environment(url), capture_output=True, text=True)
    if result.returncode:
        detail = result.stderr[-4000:]
        for private in (url.render_as_string(hide_password=False), url.password):
            if private:
                detail = detail.replace(private, "[oculto]")
        raise RuntimeError(f"Falló {Path(command[0]).stem}. Conserva el respaldo. {detail}")
    return result.stdout


def table_counts(connection):
    quote = connection.dialect.identifier_preparer.quote
    return {name: connection.execute(text(f"SELECT COUNT(*) FROM public.{quote(name)}")).scalar_one()
        for name in sorted(inspect(connection).get_table_names(schema="public"))}


def assert_empty(connection):
    count = connection.execute(text("""
        SELECT COUNT(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S','f')
    """)).scalar_one()
    if count:
        raise ValueError("El destino ya contiene objetos. Se cancela para no sobrescribir datos; usa una base nueva y vacía.")


def migrate(source, target, backup_dir):
    identity = lambda url: (url.host or "localhost", url.port or 5432, url.database)
    if identity(source) == identity(target):
        raise ValueError("Origen y destino son la misma base. No se realizará la migración.")
    backup_dir = Path(backup_dir).expanduser().resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    dump = backup_dir / f"fashionstore-{stamp}.dump"
    source_engine = create_engine(source, poolclass=NullPool, connect_args={"connect_timeout": 15})
    target_engine = create_engine(target, poolclass=NullPool, connect_args={"connect_timeout": 15})
    try:
        with target_engine.connect() as connection:
            assert_empty(connection)
        with source_engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
            with connection.begin():
                # El respaldo y los conteos observan exactamente la misma versión.
                snapshot = connection.execute(text("SELECT pg_export_snapshot()")).scalar_one()
                counts = table_counts(connection)
                run_pg([pg_tool("pg_dump"), "--format=custom", "--no-owner", "--no-privileges",
                    "--schema=public", f"--snapshot={snapshot}", f"--file={dump}"], source)
        dump.chmod(0o600)
        manifest = dump.with_suffix(".counts.json")
        manifest.write_text(json.dumps(counts, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Respaldo guardado: {dump}", flush=True)
        # PostgreSQL ya crea public en una base vacía. Conservar ese esquema
        # evita recrearlo o cambiar su propietario en el proveedor de destino.
        contents = run_pg([pg_tool("pg_restore"), "--list", str(dump)], target)
        entries = [line for line in contents.splitlines()
            if not (" SCHEMA - public " in line or " COMMENT - SCHEMA public " in line)]
        restore_list = dump.with_suffix(".restore.list")
        restore_list.write_text("\n".join(entries) + "\n", encoding="utf-8")
        # Sin --clean ni DROP. Si falla una instrucción se revierte la restauración.
        run_pg([pg_tool("pg_restore"), "--no-owner", "--no-privileges", "--single-transaction",
            "--exit-on-error", f"--use-list={restore_list}", "--dbname", target.database, str(dump)], target)
        with target_engine.connect() as connection:
            actual = table_counts(connection)
        if actual != counts:
            raise RuntimeError("Los conteos no coinciden con el respaldo. No publiques la API hasta revisar el destino.")
        print(f"Migración verificada: {len(counts)} tablas, {sum(counts.values())} registros.")
        return counts
    finally:
        source_engine.dispose()
        target_engine.dispose()


def initialize(target):
    os.environ.update(DATABASE_URL=target.render_as_string(hide_password=False),
        AUTO_INIT_DB="false", AUTO_SEED="false", VERCEL="false")
    # Importación tardía: nunca utilizar accidentalmente la base local del .env.
    from main import Base, engine, _ensure_roles
    Base.metadata.create_all(bind=engine)
    _ensure_roles()
    engine.dispose()
    print("Esquema y roles preparados. No se ejecutó seed ni se restablecieron contraseñas.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("migrate", "init", "check"))
    parser.add_argument("--env-file", type=Path, default=BACKEND / ".env.deploy")
    parser.add_argument("--backup-dir", type=Path,
        default=Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "FashionStore" / "backups")
    args = parser.parse_args()
    environment = {**dotenv_values(args.env_file), **os.environ}
    try:
        target = target_url(environment)
        if args.command == "migrate":
            local = dotenv_values(BACKEND / ".env")
            source = postgres_url(environment.get("SOURCE_DATABASE_URL") or environment.get("DATABASE_URL") or local.get("DATABASE_URL"))
            migrate(source, target, args.backup_dir)
        elif args.command == "init":
            initialize(target)
        else:
            engine = create_engine(target, poolclass=NullPool, connect_args={"connect_timeout": 15})
            try:
                with engine.connect() as connection:
                    print(json.dumps(table_counts(connection), indent=2))
            finally:
                engine.dispose()
        return 0
    except Exception as exc:
        if isinstance(exc, ValueError):
            print(str(exc), file=sys.stderr)
        else:
            print(f"La operación no terminó ({type(exc).__name__}). No se publicará automáticamente ningún servicio.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
