"""Cambios aditivos compatibles con las bases del primer parcial."""
from sqlalchemy import inspect, text, Table, MetaData, UniqueConstraint
from sqlalchemy.schema import CreateTable


def migrate_compatible_schema(engine):
    tenant_tables = ("users", "roles", "branches", "categories", "providers", "products", "promotions", "seasons", "collections")
    columns = {table: {"empresa_id": "INTEGER REFERENCES empresas(id)"} for table in tenant_tables}
    columns["orders"] = {
        "empresa_id": "INTEGER REFERENCES empresas(id)", "user_id": "INTEGER REFERENCES users(id)",
        "es_offline": "BOOLEAN NOT NULL DEFAULT FALSE", "origen": "VARCHAR(20) DEFAULT 'ONLINE'",
        "order_number": "VARCHAR(30)", "payment_method": "VARCHAR(30)", "subtotal": "FLOAT",
        "shipping_address": "VARCHAR(255)",
        "request_id": "VARCHAR(36)", "request_fingerprint": "VARCHAR(64)",
        "stock_deducted": "BOOLEAN NOT NULL DEFAULT FALSE",
    }
    columns['payments'] = {'cash_received': 'FLOAT', 'change_amount': 'FLOAT NOT NULL DEFAULT 0'}
    columns['refund_items'] = {'restocked_quantity':'INTEGER NOT NULL DEFAULT 0'}
    columns["order_items"] = {"discount": "FLOAT NOT NULL DEFAULT 0", "promotion_id": "INTEGER REFERENCES promotions(id)"}
    columns["cambios_prenda"] = {"detalle_json": "TEXT", "monto_diferencia": "FLOAT NOT NULL DEFAULT 0"}
    existing_tables = set(inspect(engine).get_table_names())
    migrate_stock = 'orders' in existing_tables and 'stock_deducted' not in {c['name'] for c in inspect(engine).get_columns('orders')}
    with engine.connect() as connection:
        sqlite = engine.dialect.name == "sqlite"
        foreign_keys = connection.exec_driver_sql("PRAGMA foreign_keys").scalar() if sqlite else False
        if sqlite:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
        try:
            with connection.begin():
                if sqlite:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                _apply_columns(connection, columns, existing_tables)
                if migrate_stock:
                    connection.execute(text("UPDATE orders SET stock_deducted=TRUE WHERE status IN ('PAGADO','ENVIADO','ENTREGADO')"))
                if 'orders' in existing_tables:
                    connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_request_id ON orders (request_id)'))
                _scope_unique_constraints(connection, existing_tables)
        finally:
            if sqlite and foreign_keys:
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
                connection.commit()


def _apply_columns(connection, columns, existing_tables):
    for table, definitions in columns.items():
        if table not in existing_tables:
            continue
        existing = {column["name"] for column in inspect(connection).get_columns(table)}
        for name, ddl in definitions.items():
            if name not in existing:
                connection.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {ddl}'))
        if "empresa_id" in definitions:
            connection.execute(text(f'CREATE INDEX IF NOT EXISTS "ix_{table}_empresa_id" ON "{table}" (empresa_id)'))


def _scope_unique_constraints(connection, existing_tables):
    quote = connection.dialect.identifier_preparer.quote
    for table_name, field in (("seasons", "name"), ("collections", "name"), ("providers", "nit")):
        if table_name not in existing_tables:
            continue
        constraints = inspect(connection).get_unique_constraints(table_name)
        legacy = [constraint for constraint in constraints if constraint["column_names"] == [field]]
        if not legacy:
            continue
        unique_name = f"uq_{table_name}_empresa_{field}"
        if connection.dialect.name == "sqlite":
            # Se copia la tabla completa dentro de la transacción, preservando
            # columnas, claves foráneas y registros de las bases anteriores.
            reflected = Table(table_name, MetaData(), autoload_with=connection)
            indexes = [index for index in reflected.indexes if not index.unique]
            reflected.constraints = {constraint for constraint in reflected.constraints
                if not isinstance(constraint, UniqueConstraint) or list(constraint.columns.keys()) != [field]}
            UniqueConstraint(reflected.c.empresa_id, reflected.c[field], name=unique_name)
            temporary = f"{table_name}__tenant_migration"
            reflected.name = temporary
            connection.execute(CreateTable(reflected))
            column_names = ", ".join(quote(column.name) for column in reflected.columns)
            connection.execute(text(f"INSERT INTO {quote(temporary)} ({column_names}) SELECT {column_names} FROM {quote(table_name)}"))
            before = connection.exec_driver_sql(f"SELECT COUNT(*) FROM {quote(table_name)}").scalar()
            after = connection.exec_driver_sql(f"SELECT COUNT(*) FROM {quote(temporary)}").scalar()
            if before != after:
                raise RuntimeError("La migración no conserva el número de registros")
            connection.exec_driver_sql(f"DROP TABLE {quote(table_name)}")
            connection.exec_driver_sql(f"ALTER TABLE {quote(temporary)} RENAME TO {quote(table_name)}")
            for index in indexes:
                cols = ", ".join(quote(column.name) for column in index.columns)
                connection.exec_driver_sql(f"CREATE INDEX IF NOT EXISTS {quote(index.name)} ON {quote(table_name)} ({cols})")
        else:
            for constraint in legacy:
                connection.exec_driver_sql(f"ALTER TABLE {quote(table_name)} DROP CONSTRAINT {quote(constraint['name'])}")
            connection.exec_driver_sql(f"ALTER TABLE {quote(table_name)} ADD CONSTRAINT {quote(unique_name)} UNIQUE (empresa_id, {quote(field)})")
