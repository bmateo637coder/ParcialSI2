import 'package:flutter/material.dart';

import '../models.dart';
import '../services.dart';
import '../widgets.dart';
import 'availability_screen.dart';

class BranchesScreen extends StatefulWidget {
  const BranchesScreen({super.key});

  @override
  State<BranchesScreen> createState() => _BranchesScreenState();
}

class _BranchesScreenState extends State<BranchesScreen> {
  List<Branch> _branches = [];
  bool _loading = true;
  String? _error;
  String _city = '';

  List<String> get _cities =>
      _branches.map((b) => b.city).toSet().toList()..sort();

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
      final list = await api.getBranches(city: _city);
      if (!mounted) return;
      setState(() {
        _branches = list;
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Sucursales')),
      body: _loading
          ? const LoadingView()
          : _error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(12, 10, 12, 0),
                      child: InputDecorator(
                        decoration: const InputDecoration(
                          labelText: 'Consultar por ciudad (CU6)',
                          prefixIcon: Icon(Icons.location_city),
                        ),
                        child: DropdownButtonHideUnderline(
                          child: DropdownButton<String>(
                            isExpanded: true,
                            value: _city.isEmpty ? null : _city,
                            hint: const Text('Todas las ciudades'),
                            items: [
                              for (final c in _cities)
                                DropdownMenuItem(value: c, child: Text(c)),
                            ],
                            onChanged: (v) {
                              setState(() => _city = v ?? '');
                              _load();
                            },
                          ),
                        ),
                      ),
                    ),
                    Expanded(
                      child: _branches.isEmpty
                          ? const EmptyState(
                              message: 'No hay sucursales en esa ciudad.',
                              icon: Icons.store_mall_directory)
                          : ListView.builder(
                              padding: const EdgeInsets.only(bottom: 16),
                              itemCount: _branches.length,
                              itemBuilder: (context, i) {
                                final b = _branches[i];
                                return Card(
                                  child: ListTile(
                                    leading: CircleAvatar(
                                      backgroundColor:
                                          const Color(0xFF5B2333).withValues(alpha: 0.1),
                                      child: const Icon(Icons.storefront,
                                          color: Color(0xFF5B2333)),
                                    ),
                                    title: Text(b.name,
                                        style: const TextStyle(fontWeight: FontWeight.w600)),
                                    subtitle: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text('${b.city}${b.address != null ? ' · ${b.address}' : ''}'),
                                        if (b.phone != null && b.phone!.isNotEmpty)
                                          Text('Tel: ${b.phone}'),
                                      ],
                                    ),
                                    isThreeLine: true,
                                    trailing:
                                        const Icon(Icons.chevron_right),
                                    onTap: () => Navigator.of(context).push(
                                      MaterialPageRoute(
                                          builder: (_) =>
                                              AvailabilityScreen(branchId: b.id)),
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