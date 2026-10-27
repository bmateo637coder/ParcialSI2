import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:uuid/uuid.dart';
import 'offline_db.dart';

class SyncOfflineService {
  final Dio _dio = Dio(BaseOptions(baseUrl: 'http://127.0.0.1:8001/api'));
  final _uuid = const Uuid();

  Future<String> registrarVentaOffline({
    required int sucursalId,
    required int usuarioId,
    required int empresaId,
    required List items,
    double total = 0,
    String formaPago = 'EFECTIVO',
    int? clienteId,
  }) async {
    final uuid = _uuid.v4();
    await OfflineDb.instance.agregarOperacion({
      'uuid': uuid,
      'tipo_operacion': 'VENTA_CONTADO',
      'sucursal_id': sucursalId,
      'usuario_id': usuarioId,
      'empresa_id': empresaId,
      'fecha_local': DateTime.now().toIso8601String(),
      'cliente_id': clienteId,
      'items_json': jsonEncode(items),
      'total': total,
      'forma_pago': formaPago,
      'estado': 'REGISTRADA_LOCAL',
      'intentos': 0,
    });
    return uuid;
  }

  Future<Map<String, dynamic>> sincronizar() async {
    final pendientes = await OfflineDb.instance.obtenerPendientes();
    if (pendientes.isEmpty) {
      return {'mensaje': 'Sin operaciones pendientes'};
    }

    final operaciones = pendientes.map((p) {
      return {
        'uuid': p['uuid'],
        'tipo_operacion': p['tipo_operacion'],
        'sucursal_id': p['sucursal_id'],
        'usuario_id': p['usuario_id'],
        'fecha_local': p['fecha_local'],
        'cliente_id': p['cliente_id'],
        'items': jsonDecode(p['items_json'] ?? '[]'),
        'total': p['total'],
        'forma_pago': p['forma_pago'],
        'origen': 'OFFLINE',
      };
    }).toList();

    for (final p in pendientes) {
      await OfflineDb.instance.marcarEnviada(p['uuid']);
    }

    final resp = await _dio.post('/sync', data: {'operaciones': operaciones});
    return resp.data;
  }
}
