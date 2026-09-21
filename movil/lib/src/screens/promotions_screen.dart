import 'package:flutter/material.dart';

import '../models.dart';
import '../services.dart';
import '../widgets.dart';

class PromotionsScreen extends StatefulWidget {
  final bool adminMode;

  const PromotionsScreen({super.key, this.adminMode = true});

  @override
  State<PromotionsScreen> createState() => _PromotionsScreenState();
}

class _PromotionsScreenState extends State<PromotionsScreen> {
  List<Promotion> _promotions = [];
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
      final list = await api.getPromotions();
      if (!mounted) return;
      setState(() {
        _promotions = list;
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

  Future<void> _toggle(Promotion p) async {
    try {
      final updated = p.isActive
          ? await api.deactivatePromotion(p.id)
          : await api.activatePromotion(p.id);
      if (!mounted) return;
      setState(() {
        _promotions = [
          for (final x in _promotions)
            if (x.id == updated.id) updated else x,
        ];
      });
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    }
  }

  Future<void> _create() async {
    final formKey = GlobalKey<FormState>();
    final name = TextEditingController();
    final desc = TextEditingController();
    final value = TextEditingController();
    var type = 'PERCENTAGE';
    var targetType = 'GLOBAL';
    final end = TextEditingController(text: '2026-12-31');

    final saved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Nueva promoción'),
        content: StatefulBuilder(
          builder: (context, setDialogState) => Form(
            key: formKey,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  DropdownButtonFormField<String>(
                    value: targetType,
                    decoration: const InputDecoration(labelText: 'Ámbito'),
                    items: const [
                      DropdownMenuItem(value: 'GLOBAL', child: Text('Global')),
                      DropdownMenuItem(
                          value: 'CATEGORIA', child: Text('Categoría')),
                      DropdownMenuItem(
                          value: 'PRODUCTO', child: Text('Producto')),
                    ],
                    onChanged: (v) =>
                        setDialogState(() => targetType = v ?? 'GLOBAL'),
                  ),
                  TextFormField(
                    controller: name,
                    decoration: const InputDecoration(labelText: 'Nombre'),
                    validator: (v) => (v == null || v.trim().isEmpty)
                        ? 'Requerido'
                        : null,
                  ),
                  TextFormField(
                    controller: desc,
                    decoration: const InputDecoration(labelText: 'Descripción'),
                  ),
                  DropdownButtonFormField<String>(
                    value: type,
                    decoration: const InputDecoration(labelText: 'Tipo'),
                    items: const [
                      DropdownMenuItem(value: 'PERCENTAGE', child: Text('Porcentaje %')),
                      DropdownMenuItem(
                          value: 'FIXED', child: Text('Monto fijo')),
                    ],
                    onChanged: (v) => setDialogState(() => type = v ?? 'PERCENTAGE'),
                  ),
                  TextFormField(
                    controller: value,
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(
                        labelText: type == 'PERCENTAGE' ? 'Valor (%)' : 'Monto (Bs)'),
                    validator: (v) =>
                        (v == null || double.tryParse(v) == null)
                            ? 'Número válido'
                            : null,
                  ),
                  TextFormField(
                    controller: end,
                    decoration:
                        const InputDecoration(labelText: 'Fecha fin (AAAA-MM-DD)'),
                  ),
                ],
              ),
            ),
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancelar')),
          FilledButton(
              onPressed: () {
                if (formKey.currentState!.validate()) {
                  Navigator.pop(context, true);
                }
              },
              child: const Text('Guardar')),
        ],
      ),
    );

    if (saved != true) return;
    try {
      await api.createPromotion({
        'name': name.text,
        'description': desc.text.isEmpty ? null : desc.text,
        'target_type': targetType,
        'discount_type': type,
        'value': double.parse(value.text),
        'start_date': end.text,
        'end_date': end.text,
      });
      if (!mounted) return;
      showSnack(context, 'Promoción creada (CU27)');
      _load();
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Promociones (CU27)')),
      floatingActionButton: widget.adminMode
          ? FloatingActionButton.extended(
              onPressed: _create,
              icon: const Icon(Icons.add),
              label: const Text('Nueva'),
            )
          : null,
      body: _loading
          ? const LoadingView()
          : _error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : _promotions.isEmpty
                  ? const EmptyState(
                      message: 'No hay promociones.',
                      icon: Icons.percent)
                  : ListView.builder(
                      padding: const EdgeInsets.only(bottom: 72),
                      itemCount: _promotions.length,
                      itemBuilder: (context, i) {
                        final p = _promotions[i];
                        final label = p.discountType == 'PERCENTAGE'
                            ? '${p.value.toStringAsFixed(0)}%'
                            : money(p.value);
                        return Card(
                          child: ListTile(
                            leading: CircleAvatar(
                              backgroundColor: p.isActive
                                  ? const Color(0xFF5B2333).withValues(alpha: 0.1)
                                  : Colors.grey.shade300,
                              child: Icon(Icons.local_offer,
                                  color: p.isActive
                                      ? const Color(0xFF5B2333)
                                      : Colors.grey),
                            ),
                            title: Text('$label dcto · ${p.name}',
                                style: const TextStyle(
                                    fontWeight: FontWeight.w600)),
                            subtitle: Text(
                                '${p.targetType} · ${p.endDate ?? ''}\n'
                                '${p.description ?? ''}'),
                            isThreeLine: true,
                            trailing: widget.adminMode
                                ? Switch(
                                    value: p.isActive,
                                    onChanged: (_) => _toggle(p),
                                  )
                                : StatusBadge(p.isActive ? 'ACTIVA' : 'INACTIVA'),
                          ),
                        );
                      },
                    ),
    );
  }
}