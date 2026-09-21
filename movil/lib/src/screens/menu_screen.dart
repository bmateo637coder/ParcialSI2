import 'package:flutter/material.dart';

import '../services.dart';
import 'assistant_screen.dart';
import 'notifications_screen.dart';
import 'orders_screen.dart';
import 'profile_screen.dart';
import 'promotions_screen.dart';
import 'provider_screen.dart';
import 'pos_screen.dart';
import 'reports_screen.dart';
import 'reservations_screen.dart';

class MenuScreen extends StatelessWidget {
  final VoidCallback onLogout;

  const MenuScreen({super.key, required this.onLogout});

  void _push(BuildContext context, Widget screen) {
    Navigator.of(context)
        .push(MaterialPageRoute(builder: (_) => screen));
  }

  @override
  Widget build(BuildContext context) {
    final isStaff = api.isStaff;
    final isAdmin = api.isAdmin;
    final isProvider = api.isProvider;
    final user = api.currentUser;

    final List<Widget Function()> sections = [];

    // Cliente
    sections.add(() => _Section(
          title: 'Cliente',
          children: [
            _Item(
              icon: Icons.receipt_long,
              label: 'Mis pedidos (CU26)',
              onTap: () => _push(context, const OrdersScreen()),
            ),
            _Item(
              icon: Icons.event_seat_outlined,
              label: 'Mis reservas (CU13/14)',
              onTap: () => _push(context, const ReservationsScreen()),
            ),
            _Item(
              icon: Icons.auto_awesome,
              label: 'Asistente y recomendaciones (CU22/23)',
              onTap: () => _push(context, const AssistantScreen()),
            ),
            _Item(
              icon: Icons.percent,
              label: 'Promociones activas (CU27)',
              onTap: () =>
                  _push(context, const PromotionsScreen(adminMode: false)),
            ),
          ],
        ));

    // Staff
    if (isStaff) {
      sections.add(() => _Section(
            title: 'Sucursal (staff)',
            children: [
              _Item(
                icon: Icons.point_of_sale,
                label: 'Venta presencial (CU18)',
                onTap: () => _push(context, const PosScreen()),
              ),
              _Item(
                icon: Icons.event_available,
                label: 'Atender reservas (CU15)',
                onTap: () => _push(context, const ReservationsScreen()),
              ),
            ],
          ));
    }

    // Admin
    if (isAdmin) {
      sections.add(() => _Section(
            title: 'Administración',
            children: [
              _Item(
                icon: Icons.query_stats,
                label: 'Reportes y voz (CU24/25)',
                onTap: () => _push(context, const ReportsScreen()),
              ),
              _Item(
                icon: Icons.percent,
                label: 'Promociones (CU27)',
                onTap: () =>
                    _push(context, const PromotionsScreen(adminMode: true)),
              ),
            ],
          ));
    } else if (isStaff) {
      sections.add(() => _Section(
            title: 'Administración',
            children: [
              _Item(
                icon: Icons.query_stats,
                label: 'Reportes y voz (CU24/25)',
                onTap: () => _push(context, const ReportsScreen()),
              ),
            ],
          ));
    }

    // Proveedor
    if (isProvider || isAdmin) {
      sections.add(() => _Section(
            title: 'Proveedores (CU9)',
            children: [
              _Item(
                icon: Icons.factory_outlined,
                label: 'Portal de proveedores',
                onTap: () => _push(context, const ProviderScreen()),
              ),
            ],
          ));
    }

    // Comunes
    sections.add(() => _Section(
          title: 'Cuenta',
          children: [
            _Item(
              icon: Icons.person_outline,
              label: 'Mi perfil (CU3)',
              onTap: () => _push(context, const ProfileScreen()),
            ),
            _Item(
              icon: Icons.notifications_outlined,
              label: 'Notificaciones',
              onTap: () => _push(context, const NotificationsScreen()),
            ),
          ],
        ));

    return Scaffold(
      appBar: AppBar(title: const Text('Menú')),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          Card(
            color: const Color(0xFF5B2333).withValues(alpha: 0.07),
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: const Color(0xFF5B2333),
                child: const Icon(Icons.person, color: Colors.white),
              ),
              title: Text(user?.fullName ?? 'Usuario',
                  style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text(user?.email ?? ''),
            ),
          ),
          const SizedBox(height: 8),
          for (final section in sections) section(),
          const SizedBox(height: 8),
          Card(
            child: ListTile(
              leading: const Icon(Icons.logout, color: Color(0xFFC62828)),
              title: const Text('Cerrar sesión',
                  style: TextStyle(color: Color(0xFFC62828))),
              onTap: onLogout,
            ),
          ),
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  final String title;
  final List<Widget> children;

  const _Section({required this.title, required this.children});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
            child: Text(title,
                style: TextStyle(
                  fontSize: 12,
                  letterSpacing: 0.5,
                  fontWeight: FontWeight.w700,
                  color: Colors.grey.shade700,
                )),
          ),
          ...children,
          const SizedBox(height: 4),
        ],
      ),
    );
  }
}

class _Item extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _Item({required this.icon, required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: const Color(0xFF5B2333)),
      title: Text(label),
      trailing: const Icon(Icons.chevron_right, size: 20),
      onTap: onTap,
    );
  }
}