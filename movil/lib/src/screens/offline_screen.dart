import 'dart:convert';
import 'package:flutter/material.dart';
import '../../core/offline/sync_offline_service.dart';
import '../services.dart';
import '../widgets.dart';

class OfflineScreen extends StatefulWidget {
  const OfflineScreen({super.key});
  @override
  State<OfflineScreen> createState() => _OfflineScreenState();
}

class _OfflineScreenState extends State<OfflineScreen> {
  final _service = SyncOfflineService();
  List<Map<String, dynamic>> _operations = [];
  bool _busy = false;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final operations = await _service.operaciones();
      if (mounted) setState(() => _operations = operations);
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    }
  }

  Future<void> _run(bool download) async {
    setState(() => _busy = true);
    try {
      if (download) {
        await api.prepararOffline();
        if (mounted) showSnack(context, 'Catálogo, variantes y sucursales descargados.');
      } else {
        await _service.sincronizar();
      }
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    } finally {
      await _load();
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Operaciones locales')),
    body: RefreshIndicator(onRefresh: _load, child: ListView(padding: const EdgeInsets.all(16), children: [
      const Text('Las existencias descargadas pueden cambiar. Recibir efectivo localmente requiere confirmación posterior del servidor.'),
      const SizedBox(height: 12),
      FilledButton(onPressed: _busy ? null : () => _run(true), child: const Text('Descargar catálogo para trabajar sin conexión')),
      OutlinedButton(onPressed: _busy ? null : () => _run(false), child: const Text('Sincronizar y consultar resultados')),
      if (_busy) const LinearProgressIndicator(),
      if (_operations.isEmpty) const Padding(padding: EdgeInsets.all(24), child: Text('No hay operaciones de este usuario y empresa.')),
      for (final operation in _operations)
        Card(child: ExpansionTile(
          title: Text('${operation['tipo_operacion']} · ${operation['estado']}'),
          subtitle: Text('${operation['fecha_local']}\n${operation['mensaje'] ?? 'Pendiente de confirmación'}'),
          childrenPadding: const EdgeInsets.all(12), children: [
            Text('Referencia: ${operation['uuid']}\nSucursal: ${operation['sucursal_id']}\nIntentos: ${operation['intentos']}\nTotal: ${operation['total']}'),
            for (final item in jsonDecode(operation['items_json'] as String) as List)
              ListTile(title: Text('${item['nombre'] ?? item['variant_id']} × ${item['quantity']}'), subtitle: Text('Precio: ${item['precio']}')),
          ],
        )),
    ])),
  );
}
