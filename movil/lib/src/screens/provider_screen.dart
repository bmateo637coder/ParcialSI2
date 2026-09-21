import 'package:flutter/material.dart';

import '../models.dart';
import '../services.dart';
import '../widgets.dart';

class ProviderScreen extends StatefulWidget {
  const ProviderScreen({super.key});

  @override
  State<ProviderScreen> createState() => _ProviderScreenState();
}

class _ProviderScreenState extends State<ProviderScreen> {
  ProviderMe? _me;
  List<Product> _products = [];
  List<Proposal> _proposals = [];
  bool _loading = true;
  String? _error;
  bool _isAdmin = false;

  @override
  void initState() {
    super.initState();
    _isAdmin = api.isAdmin && !api.isProvider;
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        api.getProviderMe(),
        api.getProviderProducts(),
        api.getProposals(),
      ]);
      if (!mounted) return;
      setState(() {
        _me = results[0] as ProviderMe;
        _products = results[1] as List<Product>;
        _proposals = results[2] as List<Proposal>;
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

  Future<void> _toggleProduct(Product p) async {
    try {
      final updated = await api.updateProviderProduct(p.id, !p.isActive);
      if (!mounted) return;
      setState(() {
        _products = [
          for (final x in _products)
            if (x.id == updated.id) updated else x,
        ];
      });
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    }
  }

  Future<void> _propose() async {
    final formKey = GlobalKey<FormState>();
    final name = TextEditingController();
    final desc = TextEditingController();
    final price = TextEditingController();

    final saved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Proponer producto'),
        content: Form(
          key: formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: name,
                decoration: const InputDecoration(labelText: 'Nombre'),
                validator: (v) =>
                    (v == null || v.trim().isEmpty) ? 'Requerido' : null,
              ),
              TextFormField(
                controller: desc,
                decoration: const InputDecoration(labelText: 'Descripción'),
              ),
              TextFormField(
                controller: price,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Precio base (Bs)'),
                validator: (v) =>
                    (v == null || double.tryParse(v) == null)
                        ? 'Número válido'
                        : null,
              ),
            ],
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
              child: const Text('Enviar propuesta')),
        ],
      ),
    );

    if (saved != true) return;
    try {
      await api.proposeProduct(name.text, double.parse(price.text),
          description: desc.text.isEmpty ? null : desc.text);
      if (!mounted) return;
      showSnack(context, 'Propuesta enviada a revisión');
      _load();
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    }
  }

  Future<void> _decide(Proposal p, bool approve) async {
    try {
      final updated = approve
          ? await api.approveProposal(p.id)
          : await api.rejectProposal(p.id);
      if (!mounted) return;
      showSnack(context, approve ? 'Propuesta aprobada' : 'Propuesta rechazada');
      setState(() {
        _proposals = [
          for (final x in _proposals)
            if (x.id == updated.id) updated else x,
        ];
      });
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Portal de proveedores')),
      body: _loading
          ? const LoadingView()
          : _error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : ListView(
                  padding: const EdgeInsets.all(12),
                  children: [
                    Card(
                      color: const Color(0xFF5B2333).withValues(alpha: 0.07),
                      child: ListTile(
                        leading: const Icon(Icons.factory_outlined,
                            color: Color(0xFF5B2333)),
                        title: Text(_me?.provider?.name ?? _me?.user.email ?? 'Proveedor'),
                        subtitle: Text(
                            '${_me?.provider?.nit ?? ''} · ${_me?.provider?.phone ?? ''}\n'
                            '${_me?.provider?.address ?? _me?.user.email ?? ''}'),
                        isThreeLine: true,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Text('Mis productos',
                            style: Theme.of(context)
                                .textTheme
                                .titleMedium
                                ?.copyWith(fontWeight: FontWeight.w700)),
                        const Spacer(),
                        IconButton.filledTonal(
                          onPressed: _propose,
                          icon: const Icon(Icons.add),
                          tooltip: 'Proponer producto',
                        ),
                      ],
                    ),
                    if (_products.isEmpty)
                      const EmptyState(
                          message: 'Sin productos publicados (CU9).',
                          icon: Icons.inventory_2)
                    else
                      for (final p in _products)
                        Card(
                          child: ListTile(
                            leading: ProductImage(url: p.imageUrl, size: 48),
                            title: Text(p.name),
                            subtitle: Text(money(p.basePrice)),
                            trailing: _isAdmin
                                ? null
                                : Switch(
                                    value: p.isActive,
                                    onChanged: (_) => _toggleProduct(p),
                                  ),
                          ),
                        ),
                    const SizedBox(height: 16),
                    Text('Propuestas',
                        style: Theme.of(context)
                            .textTheme
                            .titleMedium
                            ?.copyWith(fontWeight: FontWeight.w700)),
                    for (final p in _proposals)
                      Card(
                        child: ListTile(
                          title: Text(p.name),
                          subtitle: Text(
                              '${money(p.basePrice)} · ${p.providerName ?? '-'}\n'
                              '${p.status}'),
                          isThreeLine: true,
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              if (_isAdmin && p.status == 'PENDIENTE') ...[
                                IconButton(
                                  onPressed: () => _decide(p, true),
                                  icon: const Icon(Icons.check,
                                      color: Color(0xFF2E7D32)),
                                  tooltip: 'Aprobar',
                                ),
                                IconButton(
                                  onPressed: () => _decide(p, false),
                                  icon: const Icon(Icons.close,
                                      color: Color(0xFFC62828)),
                                  tooltip: 'Rechazar',
                                ),
                              ] else
                                StatusBadge(p.status),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
    );
  }
}