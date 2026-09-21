import 'package:flutter/material.dart';

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
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait([api.getBranches(), api.getAvailability()]);
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
    double s = 0;
    _qty.forEach((variantId, q) {
      for (final a in _stock) {
        if (a.variantId == variantId) {
          s += (a.price ?? 0) * q;
          break;
        }
      }
    });
    return s;
  }

  List<AvailabilityItem> get _selectedItems => _stock
      .where((a) => _qty.containsKey(a.variantId) && (_qty[a.variantId] ?? 0) > 0)
      .toList();

  Future<void> _sale() async {
    final items = _selectedItems;
    if (items.isEmpty) {
      showSnack(context, 'Agrega prendas a la venta (CU18).', error: true);
      return;
    }
    setState(() => _saleLoading = true);
    try {
      await api.posSale(
        branchId: _branchId!,
        items: [
          for (final a in items)
            {'variant_id': a.variantId, 'quantity': _qty[a.variantId]!}
        ],
        paymentMethod: 'EFECTIVO',
      );
      if (!mounted) return;
      setState(() {
        _qty.clear();
        _saleLoading = false;
      });
      showSnack(context, 'Venta registrada ✓ (CU18)');
    } catch (e) {
      if (!mounted) return;
      setState(() => _saleLoading = false);
      showSnack(context, e.toString(), error: true);
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
                              contentPadding:
                                  EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            ),
                            child: DropdownButtonHideUnderline(
                              child: DropdownButton<int>(
                                value: _branchId,
                                items: [
                                  for (final b in _branches)
                                    DropdownMenuItem(
                                        value: b.id, child: Text(b.city)),
                                ],
                                onChanged: (v) => setState(() => _branchId = v),
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
                              icon: Icons.inventory)
                          : ListView.builder(
                              itemCount: _stock.length,
                              itemBuilder: (context, i) {
                                final a = _stock[i];
                                final q =
                                    _qty[a.variantId] ?? 0;
                                final visible = _searchController.text
                                        .isEmpty ||
                                    a.productName
                                        .toLowerCase()
                                        .contains(_searchController.text
                                            .toLowerCase());
                                if (!visible) return const SizedBox.shrink();
                                return Card(
                                  child: ListTile(
                                    leading:
                                        ProductImage(url: a.imageUrl, size: 48),
                                    title: Text(a.productName,
                                        style: const TextStyle(
                                            fontWeight: FontWeight.w600)),
                                    subtitle: Text(
                                        '${a.sizeName ?? ''} ${a.colorName ?? ''} · '
                                        '${money(a.price ?? 0)} · disp: ${a.available}'),
                                    trailing: Column(
                                      mainAxisAlignment:
                                          MainAxisAlignment.center,
                                      children: [
                                        Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            IconButton(
                                              visualDensity: VisualDensity
                                                  .compact,
                                              onPressed: q > 0
                                                  ? () => setState(() =>
                                                      _qty[a.variantId] =
                                                          q - 1)
                                                  : null,
                                              icon: const Icon(
                                                  Icons.remove_circle_outline),
                                            ),
                                            Text('$q'),
                                            IconButton(
                                              visualDensity: VisualDensity
                                                  .compact,
                                              onPressed: q >= a.available
                                                  ? null
                                                  : () => setState(() =>
                                                      _qty[a.variantId] =
                                                          q + 1),
                                              icon: const Icon(
                                                  Icons.add_circle_outline),
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
                          border: Border(
                              top: BorderSide(color: Color(0xFFE8DED3))),
                        ),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            for (final a in _selectedItems)
                              Row(
                                children: [
                                  Text('${a.productName} '
                                      '${a.sizeName}/${a.colorName}'),
                                  const Spacer(),
                                  Text('${_qty[a.variantId]} × '
                                      '${money(a.price ?? 0)}'),
                                ],
                              ),
                            const Divider(),
                            Row(
                              children: [
                                const Text('Total',
                                    style: TextStyle(fontWeight: FontWeight.w800)),
                                const Spacer(),
                                Text(money(_subtotal),
                                    style: const TextStyle(
                                        fontWeight: FontWeight.w800,
                                        fontSize: 20,
                                        color: Color(0xFF5B2333))),
                              ],
                            ),
                            const SizedBox(height: 8),
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