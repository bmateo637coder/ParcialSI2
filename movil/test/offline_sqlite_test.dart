import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:fashionstore_movil/core/offline/offline_db.dart';
import 'package:fashionstore_movil/core/offline/sync_offline_service.dart';
import 'package:fashionstore_movil/src/api_client.dart';
import 'package:fashionstore_movil/src/models.dart';

final identity = User(id: 1, empresaId: 7, firstName: 'Test', lastName: 'User',
    email: 'offline@test.com', roleName: 'Cajero', isActive: true);
const availability = [
  {'branch_id': 3, 'variant_id': 11, 'product_name': 'Polera', 'price': 120, 'available': 10},
  {'branch_id': 3, 'variant_id': 12, 'product_name': 'Camisa', 'price': 20, 'available': 5},
];

class _LocalHttpOverrides extends HttpOverrides {}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;
  late Directory directory;
  late OfflineDb store;
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    directory = await Directory.systemTemp.createTemp('fashionstore_sqlite_');
    store = OfflineDb(databasePath: '${directory.path}/offline.db');
  });
  tearDown(() async {
    await store.close();
    expect(directory.parent.absolute.path, Directory.systemTemp.absolute.path);
    await directory.delete(recursive: true);
  });

  test('real SQLite preserves sales, reservations, catalog and unconfirmed sends after reopening', () async {
    var connected = true;
    var loseResponse = true;
    var syncRequests = 0;
    final accepted = <String>{};
    final transport = MockClient((request) async {
      if (!connected) throw http.ClientException('Sin conexión');
      if (request.url.path.endsWith('/auth/me')) return http.Response(jsonEncode(identity.toJson()), 200);
      if (request.url.path.endsWith('/sync')) {
        syncRequests++;
        final payload = jsonDecode(request.body) as Map;
        final operations = payload['operaciones'] as List;
        final rows = await store.obtenerOperaciones(7, 1);
        expect(rows.every((row) => row['estado'] == 'ENVIADA'), isTrue);
        expect(rows.every((row) => (row['intentos'] as int) >= 1), isTrue);
        for (final operation in operations) {
          accepted.add(operation['uuid'] as String);
        }
        if (loseResponse) throw http.ClientException('Respuesta perdida después del envío');
        return http.Response(jsonEncode({'resultados': operations.map((op) => {
          'uuid': op['uuid'], 'estado': 'CONFIRMADA', 'mensaje': 'Confirmada',
        }).toList()}), 200);
      }
      return http.Response('[]', 200);
    });
    final original = ApiClient(client: transport, baseUrl: 'http://test/api', cache: store);
    await original.saveSession('test-token', identity.roleName, identity.email, identity);
    await store.guardarCache('7:1', '/inventory/availability', availability);
    await store.guardarCache('7:1', '/products/', [{'id': 1, 'name': 'Polera', 'base_price': 120}]);
    final service = SyncOfflineService(client: original, database: store);
    final sale = await service.registrarVentaOffline(sucursalId: 3, usuarioId: 1,
      items: [{'variant_id': 11, 'quantity': 2, 'precio': 120}], total: 240);
    final reservation = await service.registrarReservaOffline(sucursalId: 3,
      items: [{'variant_id': 12, 'quantity': 1, 'precio': 20}]);
    expect(sale, isNot(reservation));
    await expectLater(service.sincronizar(), throwsA(isA<ApiError>()));
    expect((await store.obtenerOperaciones(7, 1)).every((op) => op['estado'] == 'ENVIADA'), isTrue);
    final path = (await store.database).path;
    await store.close();
    expect(await File(path).length(), greaterThan(0));

    store = OfflineDb(databasePath: path);
    connected = false;
    final restored = ApiClient(client: transport, baseUrl: 'http://test/api', cache: store);
    await restored.restoreSession();
    expect(restored.isAuthenticated, isTrue);
    expect((await restored.getProducts()).single.name, 'Polera');
    final pending = await store.obtenerPendientes(7, 1);
    expect(pending.map((op) => op['uuid']).toSet(), {sale, reservation});
    final stock = await store.leerCache('7:1', '/inventory/availability?branch_id=3') as List;
    expect(stock.map((row) => row['available']).toList(), [8, 4]);
    expect(await store.obtenerOperaciones(8, 1), isEmpty);
    expect(await store.leerCache('8:1', '/products/'), isNull);

    connected = true;
    loseResponse = false;
    final restartedService = SyncOfflineService(client: restored, database: store);
    await restartedService.sincronizar();
    expect(accepted, {sale, reservation});
    expect(syncRequests, 2);
    expect(await store.obtenerPendientes(7, 1), isEmpty);
    expect((await store.obtenerOperaciones(7, 1)).every((op) => op['estado'] == 'CONFIRMADA' && op['intentos'] == 2), isTrue);
    await restartedService.sincronizar();
    expect(syncRequests, 2, reason: 'Las confirmadas no se vuelven a enviar');
  });

  test('stock validation is atomic and rejected operations remain in history', () async {
    final client = ApiClient(baseUrl: 'http://test/api', cache: store,
      client: MockClient((request) async {
        final payload = jsonDecode(request.body) as Map;
        return http.Response(jsonEncode({'resultados': (payload['operaciones'] as List).map((op) => {
          'uuid': op['uuid'], 'estado': 'RECHAZADA', 'mensaje': 'Prenda desactivada',
        }).toList()}), 200);
      }));
    await client.saveSession('test-token', identity.roleName, identity.email, identity);
    await store.guardarCache('7:1', '/inventory/availability', availability);
    final service = SyncOfflineService(client: client, database: store);
    await expectLater(service.registrarVentaOffline(sucursalId: 3, usuarioId: 1,
      items: [{'variant_id': 11, 'quantity': 11, 'precio': 120}], total: 1320), throwsStateError);
    expect(await store.obtenerOperaciones(7, 1), isEmpty);
    expect((await store.leerCache('7:1', '/inventory/availability') as List).first['available'], 10);
    final uuid = await service.registrarVentaOffline(sucursalId: 3, usuarioId: 1,
      items: [{'variant_id': 11, 'quantity': 1, 'precio': 120}], total: 120);
    await service.sincronizar();
    expect(await store.obtenerPendientes(7, 1), isEmpty);
    final row = (await store.obtenerOperaciones(7, 1)).single;
    expect(row['uuid'], uuid);
    expect(row['estado'], 'RECHAZADA');
    expect(row['mensaje'], 'Prenda desactivada');
    final path = (await store.database).path;
    await store.close();
    store = OfflineDb(databasePath: path);
    expect((await store.obtenerOperaciones(7, 1)).single['estado'], 'RECHAZADA');
  });

  test('Flutter synchronizes reopened SQLite operations with the real API after a lost response', () async {
    final baseUrl = Platform.environment['MOBILE_E2E_API_URL']!;
    expect(Uri.parse(baseUrl).host, '127.0.0.1', reason: 'Esta prueba solo modifica un servidor temporal local');
    var connected = true;
    var loseSyncResponse = false;
    final network = HttpOverrides.runWithHttpOverrides(http.Client.new, _LocalHttpOverrides());
    addTearDown(network.close);
    final transport = MockClient((request) async {
      if (!connected) throw http.ClientException('Sin conexión de prueba');
      final actual = http.Request(request.method, request.url)
        ..headers.addAll(request.headers)
        ..bodyBytes = request.bodyBytes;
      final response = await http.Response.fromStream(await network.send(actual));
      if (request.url.path.endsWith('/sync') && loseSyncResponse) {
        expect(response.statusCode, 200);
        throw http.ClientException('El servidor procesó la operación, pero se perdió la respuesta');
      }
      return response;
    });
    final client = ApiClient(client: transport, baseUrl: baseUrl, cache: store);
    final account = await client.login('admin@fashionstore.com', 'admin123');
    await client.prepararOffline();
    final known = (await client.getAvailability()).firstWhere((row) => row.available >= 2 && (row.price ?? 0) > 0 && row.branchId != null);
    final originalStock = known.available;
    final service = SyncOfflineService(client: client, database: store);
    connected = false;
    expect(await client.getProducts(), isNotEmpty);
    final saleId = await service.registrarVentaOffline(sucursalId: known.branchId!, usuarioId: account.id,
      items: [{'variant_id': known.variantId, 'quantity': 1, 'precio': known.price}], total: known.price!);
    final reservationId = await service.registrarReservaOffline(sucursalId: known.branchId!,
      items: [{'variant_id': known.variantId, 'quantity': 1, 'precio': known.price}]);
    final path = (await store.database).path;
    await store.close();
    store = OfflineDb(databasePath: path);
    final reopened = ApiClient(client: transport, baseUrl: baseUrl, cache: store);
    await reopened.restoreSession();
    expect(reopened.currentUser?.id, account.id);
    final restarted = SyncOfflineService(client: reopened, database: store);
    expect((await restarted.operaciones()).map((row) => row['uuid']).toSet(), {saleId, reservationId});
    connected = true;
    loseSyncResponse = true;
    await expectLater(restarted.sincronizar(), throwsA(isA<ApiError>()));
    expect((await restarted.operaciones()).every((row) => row['estado'] == 'ENVIADA'), isTrue);
    loseSyncResponse = false;
    await restarted.sincronizar();
    expect((await restarted.operaciones()).every((row) => row['estado'] == 'CONFIRMADA'), isTrue);
    expect((await reopened.getOrders()).length, 1);
    expect((await reopened.request('GET', '/reservations') as List).length, 1);
    final fresh = await reopened.getAvailability(branchId: known.branchId);
    expect(fresh.firstWhere((row) => row.variantId == known.variantId).available, originalStock - 2);
    await restarted.sincronizar();
    expect((await reopened.getOrders()).length, 1);
    await reopened.login('admin@modaurbana.demo', 'admin123');
    expect(await restarted.operaciones(), isEmpty);
    expect((await reopened.getProducts()).single.name, 'Polera Urbana Exclusiva');
    expect((await store.obtenerOperaciones(account.empresaId!, account.id)).length, 2);
  }, skip: !Platform.environment.containsKey('MOBILE_E2E_API_URL'), timeout: const Timeout(Duration(minutes: 2)));
}
