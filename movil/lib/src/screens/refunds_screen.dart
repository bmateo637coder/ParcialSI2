import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../models.dart';
import '../services.dart';
import '../widgets.dart';

class RefundsScreen extends StatefulWidget {
  final Order order;
  const RefundsScreen({super.key, required this.order});
  @override
  State<RefundsScreen> createState() => _RefundsScreenState();
}

class _RefundsScreenState extends State<RefundsScreen> {
  late Order _order;
  final _reason = TextEditingController(), _amount = TextEditingController();
  final _quantities = <String, int>{};
  final _approval = <int, bool>{};
  final _keys = <String, String>{};
  String _kind = 'full';
  bool _restock = false, _busy = false;
  bool get _manager => api.isAdmin || api.isRole('Encargado de Sucursal');
  bool get _pending => _order.refunds.any(
    (r) => ['PENDIENTE', 'SOLICITADO'].contains(r['status']),
  );
  @override
  void initState() {
    super.initState();
    _order = widget.order;
  }

  @override
  void dispose() {
    _reason.dispose();
    _amount.dispose();
    super.dispose();
  }

  Future<void> _operate(String suffix, Map<String, dynamic> body) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final data = await api.request(
        'POST',
        '/orders/${_order.id}/$suffix',
        body: body,
      );
      if (!mounted) return;
      setState(() => _order = Order.fromJson(data as Map<String, dynamic>));
      _keys.clear();
      _reason.clear();
      showSnack(
        context,
        'Operación registrada. Revisa su estado en el historial.',
      );
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _submit() {
    if (_reason.text.trim().length < 5) {
      showSnack(
        context,
        'Explica el motivo con al menos cinco caracteres.',
        error: true,
      );
      return;
    }
    final items = [
      for (final entry in _quantities.entries)
        if (entry.value > 0) {'lot_key': entry.key, 'quantity': entry.value},
    ];
    if (_kind == 'items' && items.isEmpty) {
      showSnack(context, 'Selecciona al menos una prenda.', error: true);
      return;
    }
    final value = double.tryParse(_amount.text.replaceAll(',', '.'));
    if (_kind == 'amount' && (value == null || !value.isFinite || value <= 0)) {
      showSnack(context, 'Ingresa un importe válido.', error: true);
      return;
    }
    final body = <String, dynamic>{
      'reason': _reason.text.trim(),
      'restock': _manager && _kind != 'amount' && _restock,
      'items': _kind == 'items' ? items : [],
      if (_kind == 'amount') 'amount': value,
    };
    final key = jsonEncode(body);
    body['request_id'] = _keys.putIfAbsent(key, () => const Uuid().v4());
    _operate(_manager ? 'refunds' : 'refund-requests', body);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Reembolsos y devoluciones')),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          'Pedido #${_order.id}',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const Text(
          'Tarjetas y transferencias en modo de simulación. El encargado confirma la entrega de efectivo.',
        ),
        const SizedBox(height: 12),
        Text(
          'Cobros y cambios: ${money(_order.collectedTotal)}\nDevuelto: ${money(_order.refundedTotal)}\nSaldo neto: ${money(_order.netTotal)}\nPendiente de devolver: ${money(_order.refundPending)}',
        ),
        if (!_pending &&
            _order.returnableItems.isNotEmpty &&
            (_manager || api.isRole('Cliente'))) ...[
          DropdownButtonFormField<String>(
            initialValue: _kind,
            decoration: const InputDecoration(labelText: 'Tipo de devolución'),
            items: const [
              DropdownMenuItem(
                value: 'full',
                child: Text('Saldo restante completo'),
              ),
              DropdownMenuItem(
                value: 'items',
                child: Text('Prendas seleccionadas'),
              ),
              DropdownMenuItem(
                value: 'amount',
                child: Text('Ajuste de importe'),
              ),
            ],
            onChanged: _busy ? null : (v) => setState(() => _kind = v!),
          ),
          if (_kind == 'items')
            for (final lot in _order.returnableItems) ...[
              Text(
                '${lot['product_name']} · ${lot['size_name']} / ${lot['color_name']} · ${lot['quantity']} pendientes',
              ),
              TextFormField(
                initialValue: '0',
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Unidades a devolver',
                ),
                onChanged: (value) => _quantities[lot['key'] as String] =
                    int.tryParse(value) ?? 0,
              ),
            ],
          if (_kind == 'amount')
            TextField(
              controller: _amount,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: const InputDecoration(
                labelText: 'Importe a devolver (Bs.)',
              ),
            ),
          TextField(
            controller: _reason,
            maxLength: 500,
            maxLines: 3,
            decoration: const InputDecoration(labelText: 'Motivo'),
          ),
          if (_manager && _kind != 'amount' && _order.stockDeducted)
            CheckboxListTile(
              value: _restock,
              onChanged: _busy ? null : (v) => setState(() => _restock = v!),
              title: const Text(
                'Recibí las prendas aptas para volver al inventario',
              ),
            ),
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: Text(
              _manager ? 'Confirmar devolución' : 'Solicitar al encargado',
            ),
          ),
        ],
        if (_pending)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: Text(
              'Hay una solicitud o devolución pendiente. Debe resolverse antes de iniciar otra.',
            ),
          ),
        const Divider(),
        const Text('Historial', style: TextStyle(fontWeight: FontWeight.bold)),
        for (final refund in _order.refunds)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${refund['receipt_number']} · ${money((refund['amount'] as num).toDouble())}',
                  ),
                  StatusBadge(refund['status'] as String),
                  Text(refund['reason'] as String),
                  if (refund['reference'] != null)
                    Text('Referencia: ${refund['reference']}'),
                  if (refund['error'] != null) Text(refund['error'] as String),
                  if (_manager && refund['status'] == 'PENDIENTE')
                    OutlinedButton(
                      onPressed: _busy
                          ? null
                          : () => _operate("refunds/${refund['id']}/retry", {}),
                      child: const Text('Reintentar devolución pendiente'),
                    ),
                  if (!_manager && refund['status'] == 'SOLICITADO')
                    OutlinedButton(
                      onPressed: _busy
                          ? null
                          : () => _operate(
                              "refunds/${refund['id']}/withdraw",
                              {},
                            ),
                      child: const Text('Cancelar solicitud'),
                    ),
                  if (_manager && refund['status'] == 'SOLICITADO') ...[
                    if (_order.stockDeducted)
                      CheckboxListTile(
                        value: _approval[refund['id']] ?? false,
                        onChanged: _busy
                            ? null
                            : (v) => setState(
                                () => _approval[refund['id'] as int] = v!,
                              ),
                        title: const Text(
                          'Recibí las prendas aptas para inventario',
                        ),
                      ),
                    FilledButton(
                      onPressed: _busy
                          ? null
                          : () => _operate("refunds/${refund['id']}/decision", {
                              'approve': true,
                              'restock': _approval[refund['id']] ?? false,
                            }),
                      child: const Text('Aprobar y devolver dinero'),
                    ),
                    TextButton(
                      onPressed: _busy
                          ? null
                          : () => _operate("refunds/${refund['id']}/decision", {
                              'approve': false,
                            }),
                      child: const Text('Rechazar solicitud'),
                    ),
                  ],
                  if (_manager &&
                      _order.stockDeducted &&
                      refund['status'] == 'COMPLETADO')
                    for (final item in (refund['items'] as List))
                      if ((item['pending_return'] as num) > 0)
                        OutlinedButton(
                          onPressed: _busy
                              ? null
                              : () {
                                  final key =
                                      "stock:${item['id']}:${item['pending_return']}";
                                  _operate("refunds/${refund['id']}/restock", {
                                    'request_id': _keys.putIfAbsent(
                                      key,
                                      () => const Uuid().v4(),
                                    ),
                                    'refund_item_id': item['id'],
                                    'quantity': item['pending_return'],
                                  });
                                },
                          child: Text(
                            "Recibí ${item['pending_return']} prendas aptas: reponer sin otro pago",
                          ),
                        ),
                ],
              ),
            ),
          ),
      ],
    ),
  );
}
