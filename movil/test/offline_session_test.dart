import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:fashionstore_movil/core/offline/offline_db.dart';
import 'package:fashionstore_movil/src/api_client.dart';
import 'package:fashionstore_movil/src/models.dart';

class MemoryCache implements OfflineCache {
  final rows = <String, String>{};
  @override
  Future<void> guardarCache(String scope, String path, dynamic data) async { rows['$scope:$path'] = jsonEncode(data); }
  @override
  Future<dynamic> leerCache(String scope, String path) async {
    final value = rows['$scope:$path'];
    return value == null ? null : jsonDecode(value);
  }
}

User user(int id, int company) => User(id: id, empresaId: company, firstName: 'Test', lastName: 'User',
  email: 'user$id@test.com', roleName: 'Cajero', isActive: true);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => SharedPreferences.setMockInitialValues({}));

  test('restoring while offline retains session and cached catalog without leaking to another company', () async {
    var connected = true;
    final cache = MemoryCache();
    final transport = MockClient((request) async {
      if (!connected) throw http.ClientException('offline');
      return http.Response(jsonEncode([{'id': 1, 'name': 'Prenda A', 'base_price': 120}]), 200);
    });
    final original = ApiClient(client: transport, baseUrl: 'http://test/api', cache: cache);
    await original.saveSession('token', 'Cajero', user(1, 7).email, user(1, 7));
    expect((await original.getProducts()).single.name, 'Prenda A');
    connected = false;
    final restored = ApiClient(client: transport, baseUrl: 'http://test/api', cache: cache);
    await restored.restoreSession();
    expect(restored.isAuthenticated, isTrue);
    expect(restored.currentUser?.empresaId, 7);
    expect((await restored.getProducts()).single.basePrice, 120);
    restored.currentUser = user(2, 8);
    await expectLater(restored.getProducts(), throwsA(isA<ApiError>()));
  });

  test('an expired server session is cleared instead of reused offline', () async {
    final transport = MockClient((request) async => http.Response('{"detail":"No autenticado"}', 401));
    final api = ApiClient(client: transport, baseUrl: 'http://test/api', cache: MemoryCache());
    await api.saveSession('expired', 'Cajero', user(1, 7).email, user(1, 7));
    await api.restoreSession();
    expect(api.isAuthenticated, isFalse);
    expect(api.currentUser, isNull);
    expect((await SharedPreferences.getInstance()).getString('fs_token'), isNull);
  });
}
