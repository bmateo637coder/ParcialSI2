from sqlalchemy import create_engine, inspect
from app.core.migrations import migrate_compatible_schema


def test_legacy_unique_constraints_are_migrated_without_losing_rows_or_references():
    engine = create_engine('sqlite://')
    with engine.connect() as connection:
        connection.exec_driver_sql('PRAGMA foreign_keys=ON')
        connection.exec_driver_sql('CREATE TABLE empresas (id INTEGER PRIMARY KEY)')
        connection.exec_driver_sql('INSERT INTO empresas VALUES (1), (2)')
        connection.exec_driver_sql('CREATE TABLE seasons (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)')
        connection.exec_driver_sql("INSERT INTO seasons VALUES (1, 'Verano')")
        connection.exec_driver_sql('CREATE TABLE collections (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, season_id INTEGER REFERENCES seasons(id))')
        connection.exec_driver_sql("INSERT INTO collections VALUES (1, 'Coleccion', 1)")
        connection.exec_driver_sql('CREATE TABLE providers (id INTEGER PRIMARY KEY, nit TEXT UNIQUE)')
        connection.exec_driver_sql("INSERT INTO providers VALUES (1, '123')")
        connection.commit()
        migrate_compatible_schema(engine)
        migrate_compatible_schema(engine)
        assert connection.exec_driver_sql('SELECT name FROM seasons WHERE id=1').scalar() == 'Verano'
        assert connection.exec_driver_sql('SELECT season_id FROM collections WHERE id=1').scalar() == 1
        connection.exec_driver_sql("INSERT INTO seasons (id,name,empresa_id) VALUES (2,'Verano',1), (3,'Verano',2)")
        assert connection.exec_driver_sql('PRAGMA foreign_key_check').all() == []
        assert connection.exec_driver_sql('PRAGMA foreign_keys').scalar() == 1
        constraints = inspect(connection).get_unique_constraints('seasons')
        assert any(c['column_names'] == ['empresa_id', 'name'] for c in constraints)
    engine.dispose()
