import 'package:flutter/material.dart';

import '../models.dart';
import '../services.dart';
import '../widgets.dart';

class OrdersScreen extends StatefulWidget {
  const OrdersScreen({super.key});

  @override
  State<OrdersScreen> createState() => _OrdersScreenState();
}

class _OrdersScreenState extends State<OrdersScreen> {
  List<Order> _orders = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final list = await api.getOrders();
      if (!mounted) return;
      setState(() {
        _orders = list;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.toString();
      });
    }
  }

  Future<void> _pay(Order order) async {
    try {
      final updated =
          await api.payOrder(order.id, order.payment?.method ?? 'TARJETA');
      if (!mounted) return;
      showSnack(context, 'Pago completado (CU19)');
      setState(() {
        _orders = [
          for (final o in _orders)
            if (o.id == updated.id) updated else o,
        ];
      });
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    }
  }

  Future<void> _cancel(Order order) async {
    try {
      final updated = await api.updateOrderStatus(order.id, 'CANCELADO');
      if (!mounted) return;
      showSnack(context, 'Pedido cancelado');
      setState(() {
        _orders = [
          for (final o in _orders)
            if (o.id == updated.id) updated else o,
        ];
      });
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mis pedidos (CU26)')),
      body: _loading
          ? const LoadingView()
          : _error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : _orders.isEmpty
                  ? const EmptyState(
                      message: 'Todavía no tienes pedidos.',
                      icon: Icons.receipt_long)
                  : ListView.builder(
                      padding: const EdgeInsets.only(bottom: 16),
                      itemCount: _orders.length,
                      itemBuilder: (context, i) {
                        final o = _orders[i];
                        return Card(
                          child: ExpansionTile(
                            leading: const Icon(Icons.receipt_outlined,
                                color: Color(0xFF5B2333)),
                            title: Text('Pedido #${o.id} · ${o.receiptNumber ?? ''}',
                                style: const TextStyle(fontWeight: FontWeight.w600)),
                            subtitle: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                    '${fmtDate(o.createdAt)} · ${o.orderType} · ${money(o.total)}'),
                                const SizedBox(height: 2),
                                StatusBadge(o.status),
                              ],
                            ),
                            children: [
                              for (final it in o.items)
                                ListTile(
                                  dense: true,
                                  leading: ProductImage(url: it.imageUrl, size: 40),
                                  title: Text(it.productName ?? ''),
                                  subtitle: Text('${it.sizeName ?? ''} ${it.colorName ?? ''}'
                                      ' × ${it.quantity}'),
                                  trailing: Text(money(it.unitPrice * it.quantity)),
                                ),
                              if (o.payment != null)
                                ListTile(
                                  dense: true,
                                  leading: const Icon(Icons.credit_card),
                                  title: Text('Pago (${o.payment!.method})'),
                                  trailing: StatusBadge(o.payment!.status),
                                ),
                              Padding(
                                padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.end,
                                  children: [
                                    if (o.payment != null &&
                                        o.payment!.status == 'PENDIENTE')
                                      TextButton.icon(
                                        onPressed: () => _pay(o),
                                        icon: const Icon(Icons.payment),
                                        label: const Text('Pagar ahora'),
                                      ),
                                    if (o.status != 'CANCELADO' &&
                                        o.status != 'COMPLETADO' &&
                                        o.status != 'ENTREGADO')
                                      TextButton.icon(
                                        onPressed: () => _cancel(o),
                                        icon: const Icon(Icons.cancel_outlined),
                                        label: const Text('Cancelar'),
                                      ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
    );
  }
}