import 'package:flutter/material.dart';

import 'dart:convert';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:uuid/uuid.dart';

import '../../core/offline/sync_offline_service.dart';
import '../models.dart';
import '../services.dart';
import '../theme.dart';
import '../widgets.dart';

class PosScreen extends StatefulWidget {
  const PosScreen({super.key});

  @override
  State<PosScreen> createState() => _PosScreenState();
}

class _PosScreenState extends State<PosScreen> {
  List<Branch> _branches = [];
  List<AvailabilityItem> _stock = [];
  int? _branchId;
  final Map<int, int> _qty = {}; // variantId -> cantidad
  final _searchController = TextEditingController();
  final _cashController = TextEditingController();
  String? _requestId;
  String? _requestContent;
  bool _loading = true;
  String? _error;
  bool _saleLoading = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    _cashController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        api.getBranches(),
        api.getAvailability(),
      ]);
      if (!mounted) return;
      setState(() {
        _branches = results[0] as List<Branch>;
        _stock = results[1] as List<AvailabilityItem>;
        if (_branches.isNotEmpty) _branchId = _branches.first.id;
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

  double get _subtotal {
    return _selectedItems.fold<int>(
          0,
          (sum, item) =>
              sum +
              ((item.price ?? 0) * 100).round() * (_qty[item.variantId] ?? 0),
        ) /
        100;
  }

  List<AvailabilityItem> get _selectedItems => _stock
      .where((a) => a.branchId == _branchId && (_qty[a.variantId] ?? 0) > 0)
      .toList();

  Future<void> _sale() async {
    if (_saleLoading) return;
    final items = _selectedItems;
    if (items.isEmpty || _branchId == null) {
      showSnack(
        context,
        'Agrega prendas de la sucursal a la venta.',
        error: true,
      );
      return;
    }
    final received = double.tryParse(_cashController.text.replaceAll(',', '.'));
    if (received == null ||
        !received.isFinite ||
        (received * 100).round() < (_subtotal * 100).round()) {
      showSnack(
        context,
        'El efectivo recibido debe cubrir el total.',
        error: true,
      );
      return;
    }
    setState(() => _saleLoading = true);
    try {
      final connection = await Connectivity().checkConnectivity();
      if (connection.contains(ConnectivityResult.none) &&
          api.currentUser?.empresaId != null) {
        final offline = SyncOfflineService();
        await offline.registrarVentaOffline(
          sucursalId: _branchId!,
          usuarioId: api.currentUser!.id,
          items: [
            for (final a in items)
              {
                'variant_id': a.variantId,
                'quantity': _qty[a.variantId]!,
                'precio': a.price,
                'nombre': a.productName,
              },
          ],
          total: _subtotal,
        );
        if (!mounted) return;
        setState(() {
          _qty.clear();
          _cashController.clear();
        });
        showSnack(
          context,
          'Venta guardada en el dispositivo. Necesita confirmación del servidor en Operaciones locales.',
        );
      } else {
        final lines = [
          for (final a in items)
            {'variant_id': a.variantId, 'quantity': _qty[a.variantId]!},
        ];
        final content = jsonEncode({
          'branch': _branchId,
          'items': lines,
          'cash': received,
        });
        if (_requestContent != content || _requestId == null) {
          _requestContent = content;
          _requestId = const Uuid().v4();
        }
        final order = await api.posSale(
          branchId: _branchId!,
          items: lines,
          paymentMethod: 'EFECTIVO',
          requestId: _requestId,
          cashReceived: received,
        );
        if (!mounted) return;
        setState(() {
          _qty.clear();
          _cashController.clear();
          _requestId = null;
          _requestContent = null;
        });
        try {
          final stock = await api.getAvailability();
          if (mounted) setState(() => _stock = stock);
        } catch (_) {}
        if (!mounted) return;
        await showDialog<void>(
          context: context,
          builder: (context) => AlertDialog(
            title: Text(
              order.status == 'PAGADO'
                  ? 'Venta confirmada'
                  : 'Compra cancelada',
            ),
            content: Text(
              'Pedido #${order.id}\nComprobante: ${order.receiptNumber ?? "—"}\nTotal: ${money(order.total)}\nRecibido: ${money(order.payment?.cashReceived ?? received)}\nCambio: ${money(order.payment?.changeAmount ?? 0)}\nReembolsado: ${money(order.refundedTotal)}\nPendiente de devolver: ${money(order.refundPending)}',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Cerrar'),
              ),
            ],
          ),
        );
      }
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    } finally {
      if (mounted) setState(() => _saleLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Punto de venta (CU18)')),
      body: _loading
          ? const LoadingView()
          : _error != null
          ? ErrorView(message: _error!, onRetry: _load)
          : Column(
              children: [
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _searchController,
                          onChanged: (_) => setState(() {}),
                          decoration: const InputDecoration(
                            hintText: 'Buscar prenda…',
                            prefixIcon: Icon(Icons.search),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      InputDecorator(
                        decoration: const InputDecoration(
                          contentPadding: EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 4,
                          ),
                        ),
                        child: DropdownButtonHideUnderline(
                          child: DropdownButton<int>(
                            value: _branchId,
                            items: [
                              for (final b in _branches)
                                DropdownMenuItem(
                                  value: b.id,
                                  child: Text(b.city),
                                ),
                            ],
                            onChanged: _saleLoading
                                ? null
                                : (v) => setState(() {
                                    _branchId = v;
                                    _qty.clear();
                                    _cashController.clear();
                                  }),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: _stock.isEmpty
                      ? const EmptyState(
                          message: 'Sin stock disponible para vender.',
                          icon: Icons.inventory,
                        )
                      : ListView.builder(
                          itemCount: _stock.length,
                          itemBuilder: (context, i) {
                            final a = _stock[i];
                            final q = _qty[a.variantId] ?? 0;
                            final visible =
                                _searchController.text.isEmpty ||
                                a.productName.toLowerCase().contains(
                                  _searchController.text.toLowerCase(),
                                );
                            if (!visible || a.branchId != _branchId) {
                              return const SizedBox.shrink();
                            }
                            return Card(
                              child: ListTile(
                                leading: ProductImage(
                                  url: a.imageUrl,
                                  size: 48,
                                ),
                                title: Text(
                                  a.productName,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                subtitle: Text(
                                  '${a.sizeName ?? ''} ${a.colorName ?? ''} · '
                                  '${money(a.price ?? 0)} · disp: ${a.available}',
                                ),
                                trailing: Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        IconButton(
                                          visualDensity: VisualDensity.compact,
                                          onPressed: q > 0 && !_saleLoading
                                              ? () => setState(
                                                  () =>
                                                      _qty[a.variantId] = q - 1,
                                                )
                                              : null,
                                          icon: const Icon(
                                            Icons.remove_circle_outline,
                                          ),
                                        ),
                                        Text('$q'),
                                        IconButton(
                                          visualDensity: VisualDensity.compact,
                                          onPressed:
                                              q >= a.available || _saleLoading
                                              ? null
                                              : () => setState(
                                                  () =>
                                                      _qty[a.variantId] = q + 1,
                                                ),
                                          icon: const Icon(
                                            Icons.add_circle_outline,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                ),
                if (_selectedItems.isNotEmpty)
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: const BoxDecoration(
                      color: Colors.white,
                      border: Border(top: BorderSide(color: Color(0xFFE8DED3))),
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        for (final a in _selectedItems)
                          Row(
                            children: [
                              Text(
                                '${a.productName} '
                                '${a.sizeName}/${a.colorName}',
                              ),
                              const Spacer(),
                              Text(
                                '${_qty[a.variantId]} × '
                                '${money(a.price ?? 0)}',
                              ),
                            ],
                          ),
                        const Divider(),
                        Row(
                          children: [
                            const Text(
                              'Total',
                              style: TextStyle(fontWeight: FontWeight.w800),
                            ),
                            const Spacer(),
                            Text(
                              money(_subtotal),
                              style: const TextStyle(
                                fontWeight: FontWeight.w800,
                                fontSize: 20,
                                color: Color(0xFF5B2333),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          controller: _cashController,
                          enabled: !_saleLoading,
                          keyboardType: const TextInputType.numberWithOptions(
                            decimal: true,
                          ),
                          onChanged: (_) => setState(() {}),
                          decoration: const InputDecoration(
                            labelText: 'Efectivo recibido (Bs.)',
                          ),
                        ),
                        Text(
                          'Cambio: ${money(((double.tryParse(_cashController.text.replaceAll(",", ".")) ?? 0) - _subtotal).clamp(0, double.infinity).toDouble())}',
                        ),
                        AppPrimaryButton(
                          label: 'Registrar venta (efectivo)',
                          icon: Icons.point_of_sale,
                          loading: _saleLoading,
                          onPressed: _sale,
                        ),
                      ],
                    ),
                  ),
              ],
            ),
    );
  }
}
