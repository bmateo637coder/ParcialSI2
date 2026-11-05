import 'dart:async';
import 'dart:convert';
import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';

abstract interface class OfflineCache {
  Future<void> guardarCache(String scope, String path, dynamic data);
  Future<dynamic> leerCache(String scope, String path);
}

class OfflineDb implements OfflineCache {
  static final OfflineDb instance = OfflineDb();
  Database? _database;
  Future<Database>? _opening;
  final String? databasePath;
  OfflineDb({this.databasePath});

  Future<Database> get database async {
    if (_database != null) return _database!;
    try {
      _database = await (_opening ??= _initDB());
      return _database!;
    } catch (_) {
      _opening = null;
      rethrow;
    }
  }

  Future<Database> _initDB() async {
    final path = databasePath ?? join(await getDatabasesPath(), 'fashionstore_offline.db');
    return await openDatabase(path, version: 2, onCreate: _createDB,
      onUpgrade: (db, oldVersion, newVersion) async {
        if (oldVersion < 2) await _createCache(db);
      });
  }

  Future<void> close() async {
    final opened = _database ?? await _opening;
    await opened?.close();
    _database = null;
    _opening = null;
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
    await _createCache(db);
  }

  Future<void> _createCache(Database db) async {
    await db.execute('CREATE TABLE api_cache (cache_key TEXT PRIMARY KEY, scope TEXT NOT NULL, path TEXT NOT NULL, data_json TEXT NOT NULL, fecha_descarga TEXT NOT NULL)');
    await db.execute('ALTER TABLE operaciones_local ADD COLUMN mensaje TEXT');
    await db.execute('ALTER TABLE operaciones_local ADD COLUMN resultado_json TEXT');
    await db.execute('CREATE INDEX ix_operaciones_tenant_user ON operaciones_local (empresa_id, usuario_id)');
  }

  @override
  Future<void> guardarCache(String scope, String path, dynamic data) async {
    final db = await database;
    await db.transaction((txn) async {
      final copied = jsonDecode(jsonEncode(data));
      final ids = scope.split(':').map(int.tryParse).toList();
      if (path.startsWith('/inventory/availability') && copied is List && ids.length == 2 && ids.every((id) => id != null)) {
        final operations = await txn.query('operaciones_local', where: 'empresa_id = ? AND usuario_id = ? AND estado IN (?, ?, ?, ?)',
          whereArgs: [ids[0], ids[1], 'REGISTRADA_LOCAL', 'ENVIADA', 'EN_CONFLICTO', 'CONFLICTO']);
        for (final operation in operations) {
          for (final item in jsonDecode(operation['items_json'] as String) as List) {
            for (final row in copied) {
              if (row['branch_id'] == operation['sucursal_id'] && row['variant_id'] == item['variant_id']) {
                row['available'] = ((row['available'] as num) - (item['quantity'] as num)).clamp(0, 1000000000);
              }
            }
          }
        }
      }
      await txn.insert('api_cache', {'cache_key': '$scope:$path', 'scope': scope, 'path': path,
        'data_json': jsonEncode(copied), 'fecha_descarga': DateTime.now().toUtc().toIso8601String()}, conflictAlgorithm: ConflictAlgorithm.replace);
    });
  }

  @override
  Future<dynamic> leerCache(String scope, String path) async {
    final db = await database;
    final rows = await db.query('api_cache', where: 'cache_key = ?', whereArgs: ['$scope:$path']);
    if (rows.isNotEmpty) return jsonDecode(rows.first['data_json'] as String);
    final uri = Uri.parse(path);
    if (uri.query.isEmpty || !{'/products/', '/inventory/availability'}.contains(uri.path)) return null;
    final all = await db.query('api_cache', where: 'cache_key = ?', whereArgs: ['$scope:${uri.path}']);
    if (all.isEmpty) return null;
    final data = jsonDecode(all.first['data_json'] as String) as List;
    return data.where((row) {
      final query = uri.queryParameters['q']?.toLowerCase() ?? '';
      if (query.isNotEmpty && !'${row['name'] ?? row['product_name']} ${row['description'] ?? ''} ${row['sku'] ?? ''}'.toLowerCase().contains(query)) return false;
      for (final key in ['category_id', 'season_id', 'product_id', 'branch_id']) {
        final filter = uri.queryParameters[key];
        if (filter != null && int.tryParse(filter) != (row[key] ?? row[key.replaceAll('_id', '')]?['id'])) return false;
      }
      return true;
    }).toList();
  }

  Future<int> agregarOperacion(Map<String, dynamic> op) async {
    final db = await database;
    return db.transaction((txn) async {
      final scope = '${op['empresa_id']}:${op['usuario_id']}';
      final rows = await txn.query('api_cache', where: 'scope = ? AND path LIKE ?', whereArgs: [scope, '/inventory/availability%']);
      final quantities = <int, int>{};
      for (final raw in jsonDecode(op['items_json'] as String) as List) {
        final item = raw as Map;
        final vid = item['variant_id'] as int;
        final qty = item['quantity'] as int;
        final price = item['precio'] as num;
        if (qty <= 0 || !price.isFinite || price < 0) throw StateError('La cantidad debe ser positiva y el precio no negativo.');
        quantities[vid] = (quantities[vid] ?? 0) + qty;
      }
      final known = rows.expand((r) => jsonDecode(r['data_json'] as String) as List).toList();
      for (final entry in quantities.entries) {
        final stock = known.where((r) => r['variant_id'] == entry.key && r['branch_id'] == op['sucursal_id']);
        if (stock.isEmpty || (stock.first['available'] as num) < entry.value) {
          throw StateError('La cantidad supera las existencias locales conocidas.');
        }
      }
      for (final row in rows) {
        final list = jsonDecode(row['data_json'] as String) as List;
        for (final item in list) {
          if (item['branch_id'] == op['sucursal_id']) item['available'] = (item['available'] as num) - (quantities[item['variant_id']] ?? 0);
        }
        await txn.update('api_cache', {'data_json': jsonEncode(list)}, where: 'cache_key = ?', whereArgs: [row['cache_key']]);
      }
      return txn.insert('operaciones_local', op);
    });
  }

  Future<List<Map<String, dynamic>>> obtenerPendientes(int empresaId, int usuarioId) async {
    final db = await database;
    return db.query('operaciones_local', where: 'empresa_id = ? AND usuario_id = ? AND estado IN (?, ?, ?, ?)',
      whereArgs: [empresaId, usuarioId, 'REGISTRADA_LOCAL', 'ENVIADA', 'EN_CONFLICTO', 'CONFLICTO'], orderBy: 'id');
  }

  Future<List<Map<String, dynamic>>> obtenerOperaciones(int empresaId, int usuarioId) async {
    final db = await database;
    return db.query('operaciones_local', where: 'empresa_id = ? AND usuario_id = ?', whereArgs: [empresaId, usuarioId], orderBy: 'id DESC');
  }

  Future<void> registrarIntento(String uuid) async {
    final db = await database;
    await db.rawUpdate('UPDATE operaciones_local SET intentos = intentos + 1, estado = ?, mensaje = ? WHERE uuid = ? AND estado IN (?, ?, ?, ?)',
      ['ENVIADA', 'Enviada. Falta confirmar con el servidor; puedes reintentar sin duplicar la operación.', uuid,
        'REGISTRADA_LOCAL', 'ENVIADA', 'EN_CONFLICTO', 'CONFLICTO']);
  }

  Future<int> marcarEnviada(String uuid) async {
    final db = await database;
    return await db.update('operaciones_local', {'estado': 'ENVIADA'}, where: 'uuid = ?', whereArgs: [uuid]);
  }

  Future<int> actualizarEstado(String uuid, String estado, {String? mensaje, Object? resultado}) async {
    final db = await database;
    return await db.update('operaciones_local', {'estado': estado, 'mensaje': mensaje, 'resultado_json': jsonEncode(resultado)}, where: 'uuid = ?', whereArgs: [uuid]);
  }
}
