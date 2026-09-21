import 'package:flutter/material.dart';

import '../models.dart';
import '../services.dart';
import '../theme.dart';
import '../widgets.dart';

class ReservationCreateScreen extends StatefulWidget {
  final int? initialVariantId;
  final String? initialLabel;

  const ReservationCreateScreen(
      {super.key, this.initialVariantId, this.initialLabel});

  @override
  State<ReservationCreateScreen> createState() =>
      _ReservationCreateScreenState();
}

class _ReservationCreateScreenState extends State<ReservationCreateScreen> {
  List<AvailabilityItem> _items = [];
  AvailabilityItem? _selected;
  int? _branchId;
  int _quantity = 1;
  bool _loading = true;
  String? _error;
  bool _submitting = false;

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
      final list = await api.getAvailability();
      if (!mounted) return;
      setState(() {
        _items = list;
        if (widget.initialVariantId != null) {
          AvailabilityItem? preselected;
          for (final a in list) {
            if (a.variantId == widget.initialVariantId) {
              preselected = a;
              break;
            }
          }
          _selected = preselected;
        }
        if (_selected != null) {
          _branchId = _selected!.branchId;
          _quantity = 1;
        }
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

  List<AvailabilityItem> get _filtered {
    if (_selected == null) return _items;
    return _items
        .where((a) =>
            a.variantId == _selected!.variantId &&
            (a.available > 0 || a.branchId == _branchId))
        .toList();
  }

  Future<void> _submit() async {
    if (_selected == null || _branchId == null) {
      showSnack(context, 'Selecciona prenda, talla/color y sucursal (CU13).',
          error: true);
      return;
    }
    setState(() => _submitting = true);
    try {
      await api.createReservation(
        branchId: _branchId!,
        items: [
          {'variant_id': _selected!.variantId, 'quantity': _quantity}
        ],
      );
      if (!mounted) return;
      showSnack(context, 'Reserva creada ✓ (CU13)');
      Navigator.of(context).pushNamedAndRemoveUntil('/home', (r) => false);
    } catch (e) {
      if (!mounted) return;
      setState(() => _submitting = false);
      showSnack(context, e.toString(), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Reservar prenda (CU13)')),
      body: _loading
          ? const LoadingView()
          : _error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    if (widget.initialLabel != null) ...[
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: const Color(0xFF5B2333).withValues(alpha: 0.06),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.style_outlined),
                            const SizedBox(width: 8),
                            Expanded(
                                child: Text(widget.initialLabel!,
                                    style:
                                        const TextStyle(fontWeight: FontWeight.w600))),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                    Text('Prenda y variante',
                        style: Theme.of(context).textTheme.titleSmall),
                    const SizedBox(height: 6),
                    DropdownButtonFormField<AvailabilityItem>(
                      value: _selected,
                      isExpanded: true,
                      items: [
                        for (final a in _items)
                          DropdownMenuItem(
                            value: a,
                            child: Text(
                              '${a.productName} · ${a.sizeName ?? ''} ${a.colorName ?? ''}'
                              ' (${a.available} uds.)',
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                      ],
                      onChanged: (v) => setState(() {
                        _selected = v;
                        if (v != null) _branchId = v.branchId;
                      }),
                    ),
                    const SizedBox(height: 16),
                    Text('Sucursal',
                        style: Theme.of(context).textTheme.titleSmall),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        for (final a in _filtered)
                          ChoiceChip(
                            label: Text('${a.branchName ?? a.city} '
                                '(${a.available})'),
                            selected: _branchId == a.branchId,
                            onSelected: (_) =>
                                setState(() => _branchId = a.branchId),
                          ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Text('Cantidad',
                        style: Theme.of(context).textTheme.titleSmall),
                    Row(
                      children: [
                        IconButton.outlined(
                          onPressed: _quantity > 1
                              ? () => setState(() => _quantity--)
                              : null,
                          icon: const Icon(Icons.remove),
                        ),
                        Text('$_quantity',
                            style: const TextStyle(
                                fontSize: 18, fontWeight: FontWeight.w700)),
                        IconButton.outlined(
                          onPressed: () => setState(() => _quantity++),
                          icon: const Icon(Icons.add),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    AppPrimaryButton(
                      label: 'Confirmar reserva',
                      icon: Icons.check_circle_outline,
                      loading: _submitting,
                      onPressed: _submit,
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'La reserva expira en 24 horas si no se atiende (CU15).',
                      style: TextStyle(fontSize: 12, color: Colors.grey),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
    );
  }
}