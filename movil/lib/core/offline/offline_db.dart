import 'dart:async';
import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';

class OfflineDb {
  static final OfflineDb instance = OfflineDb._init();
  static Database? _database;
  OfflineDb._init();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB('fashionstore_offline.db');
    return _database!;
  }

  Future<Database> _initDB(String filePath) async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, filePath);
    return await openDatabase(path, version: 1, onCreate: _createDB);
  }

  Future _createDB(Database db, int version) async {
    await db.execute('''
      CREATE TABLE operaciones_local (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid TEXT UNIQUE NOT NULL,
        tipo_operacion TEXT NOT NULL,
        sucursal_id INTEGER NOT NULL,
        usuario_id INTEGER NOT NULL,
        empresa_id INTEGER NOT NULL,
        fecha_local TEXT NOT NULL,
        cliente_id INTEGER,
        items_json TEXT NOT NULL,
        total REAL DEFAULT 0,
        forma_pago TEXT DEFAULT 'EFECTIVO',
        estado TEXT DEFAULT 'REGISTRADA_LOCAL',
        intentos INTEGER DEFAULT 0,
        payload_json TEXT
      )
    ''');

    await db.execute('''
      CREATE TABLE catalogo_local (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER,
        variante_id INTEGER,
        sku TEXT,
        nombre_producto TEXT,
        precio REAL,
        sucursal_id INTEGER,
        stock_conocido INTEGER DEFAULT 0,
        fecha_descarga TEXT
      )
    ''');
  }

  Future<int> agregarOperacion(Map<String, dynamic> op) async {
    final db = await instance.database;
    return await db.insert('operaciones_local', op);
  }

  Future<List<Map<String, dynamic>>> obtenerPendientes() async {
    final db = await instance.database;
    return await db.query('operaciones_local', where: 'estado = ?', whereArgs: ['REGISTRADA_LOCAL']);
  }

  Future<int> marcarEnviada(String uuid) async {
    final db = await instance.database;
    return await db.update('operaciones_local', {'estado': 'ENVIADA'}, where: 'uuid = ?', whereArgs: [uuid]);
  }

  Future<int> actualizarEstado(String uuid, String estado) async {
    final db = await instance.database;
    return await db.update('operaciones_local', {'estado': estado}, where: 'uuid = ?', whereArgs: [uuid]);
  }
}
