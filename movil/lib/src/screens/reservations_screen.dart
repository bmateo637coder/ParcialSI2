import 'package:flutter/material.dart';

import '../models.dart';
import '../services.dart';
import '../widgets.dart';
import 'reservation_create_screen.dart';

class ReservationsScreen extends StatefulWidget {
  const ReservationsScreen({super.key});

  @override
  State<ReservationsScreen> createState() => _ReservationsScreenState();
}

class _ReservationsScreenState extends State<ReservationsScreen> {
  List<Reservation> _reservations = [];
  bool _loading = true;
  String? _error;
  bool _staffMode = false;

  @override
  void initState() {
    super.initState();
    _staffMode = api.isStaff;
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final list = await api.getReservations(allReservations: _staffMode);
      if (!mounted) return;
      setState(() {
        _reservations = list;
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

  Future<void> _action(Reservation r, String kind) async {
    try {
      final updated = kind == 'cancel'
          ? await api.cancelReservation(r.id)
          : await api.attendReservation(r.id);
      if (!mounted) return;
      showSnack(context,
          kind == 'cancel' ? 'Reserva cancelada' : 'Reserva atendida ✓ (CU15)');
      setState(() {
        _reservations = [
          for (final x in _reservations)
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
      appBar: AppBar(title: const Text('Reservas (CU14)')),
      body: _loading
          ? const LoadingView()
          : _error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : _reservations.isEmpty
                  ? const EmptyState(
                      message: 'No hay reservas.',
                      icon: Icons.event_seat)
                  : ListView.builder(
                      padding: const EdgeInsets.only(bottom: 16),
                      itemCount: _reservations.length,
                      itemBuilder: (context, i) {
                        final r = _reservations[i];
                        return Card(
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    StatusBadge(r.status),
                                    const Spacer(),
                                    if (r.branchName != null)
                                      Text(r.branchName!,
                                          style: const TextStyle(
                                              fontSize: 12,
                                              color: Color(0xFF5B2333))),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                for (final it in r.items)
                                  Row(
                                    children: [
                                      ProductImage(url: it.imageUrl, size: 46),
                                      const SizedBox(width: 10),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Text(it.productName ?? '',
                                                style: const TextStyle(
                                                    fontWeight: FontWeight.w600)),
                                            Text(
                                                '${it.sizeName ?? ''} ${it.colorName ?? ''} · ${money(it.unitPrice)}'
                                                ' × ${it.quantity}'),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                if (r.reservationDate != null)
                                  Padding(
                                    padding: const EdgeInsets.only(top: 6),
                                    child: Text(
                                      'Fecha: ${fmtDate(r.reservationDate!)} · '
                                      'Código: ${r.code == '' ? '-' : r.code}',
                                      style: const TextStyle(fontSize: 12),
                                    ),
                                  ),
                                const SizedBox(height: 4),
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.end,
                                  children: [
                                    if (r.status == 'PENDIENTE') ...[
                                      if (_staffMode)
                                        FilledButton.icon(
                                          onPressed: () => _action(r, 'attend'),
                                          icon: const Icon(Icons.verified_outlined),
                                          label: const Text('Atender (CU15)'),
                                        )
                                      else
                                        TextButton.icon(
                                          onPressed: () => _action(r, 'cancel'),
                                          icon: const Icon(Icons.cancel_outlined),
                                          label: const Text('Cancelar'),
                                        ),
                                    ] else if (!_staffMode)
                                      TextButton.icon(
                                        onPressed: () => _action(r, 'cancel'),
                                        icon: const Icon(Icons.delete_outline),
                                        label: const Text('Eliminar'),
                                      ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
      floatingActionButton: _staffMode
          ? null
          : FloatingActionButton.extended(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(
                    builder: (_) => const ReservationCreateScreen()),
              ),
              icon: const Icon(Icons.add),
              label: const Text('Nueva reserva'),
            ),
    );
  }
}