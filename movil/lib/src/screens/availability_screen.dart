import 'package:flutter/material.dart';

import '../models.dart';
import '../services.dart';
import '../widgets.dart';

class AvailabilityScreen extends StatefulWidget {
  final int? productId;
  final int? branchId;

  const AvailabilityScreen({super.key, this.productId, this.branchId});

  @override
  State<AvailabilityScreen> createState() => _AvailabilityScreenState();
}

class _AvailabilityScreenState extends State<AvailabilityScreen> {
  List<AvailabilityItem> _items = [];
  List<Branch> _branches = [];
  int? _branchFilter;
  bool _loading = true;
  String? _error;
  String _q = '';

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        api.getAvailability(productId: widget.productId, branchId: widget.branchId),
        api.getBranches(),
      ]);
      if (!mounted) return;
      setState(() {
        _items = results[0] as List<AvailabilityItem>;
        _branches = results[1] as List<Branch>;
        _branchFilter = widget.branchId;
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

  Future<void> _refresh() async {
    try {
      final list = await api.getAvailability(
          productId: widget.productId,
          branchId: _branchFilter,
          q: _q);
      if (!mounted) return;
      setState(() => _items = list);
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Disponibilidad (CU11)')),
      body: _loading
          ? const LoadingView()
          : _error != null
              ? ErrorView(message: _error!, onRetry: _init)
              : Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(12),
                      child: Row(
                        children: [
                          Expanded(
                            child: TextField(
                              onChanged: (v) {
                                _q = v;
                                _refresh();
                              },
                              decoration: const InputDecoration(
                                hintText: 'Buscar en sucursal…',
                                prefixIcon: Icon(Icons.search),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          InputDecorator(
                            decoration: const InputDecoration(
                              contentPadding: EdgeInsets.symmetric(horizontal: 10),
                            ),
                            child: DropdownButtonHideUnderline(
                              child: DropdownButton<int?>(
                                value: _branchFilter,
                                items: [
                                  const DropdownMenuItem<int?>(
                                      value: null, child: Text('Todas')),
                                  for (final b in _branches)
                                    DropdownMenuItem<int?>(
                                        value: b.id, child: Text(b.city)),
                                ],
                                onChanged: (v) {
                                  setState(() => _branchFilter = v);
                                  _refresh();
                                },
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    Expanded(
                      child: _items.isEmpty
                          ? const EmptyState(
                              message: 'Sin existencias publicadas.',
                              icon: Icons.inventory_2)
                          : ListView.builder(
                              itemCount: _items.length,
                              itemBuilder: (context, i) {
                                final a = _items[i];
                                return Card(
                                  child: ListTile(
                                    leading: ProductImage(url: a.imageUrl, size: 52),
                                    title: Text(a.productName,
                                        style: const TextStyle(fontWeight: FontWeight.w600)),
                                    subtitle: Text(
                                        '${a.sizeName ?? 'N/D'} / ${a.colorName ?? 'N/D'} · ${a.sku ?? ''}'),
                                    isThreeLine: true,
                                    trailing: Column(
                                      mainAxisAlignment: MainAxisAlignment.center,
                                      children: [
                                        Text('$a.available',
                                            style: const TextStyle(
                                                fontSize: 18,
                                                fontWeight: FontWeight.w800,
                                                color: Color(0xFF5B2333))),
                                        const Text('uds.',
                                            style: TextStyle(fontSize: 11)),
                                      ],
                                    ),
                                  ),
                                );
                              },
                            ),
                    ),
                  ],
                ),
    );
  }
}