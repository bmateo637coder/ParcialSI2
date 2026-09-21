import 'package:flutter/material.dart';

import '../models.dart';
import '../services.dart';
import '../widgets.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  List<AppNotification> _notifications = [];
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
      final list = await api.getNotifications();
      if (!mounted) return;
      setState(() {
        _notifications = list;
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

  Future<void> _markRead(AppNotification n) async {
    if (n.isRead) return;
    try {
      final updated = await api.markNotificationRead(n.id);
      if (!mounted) return;
      setState(() {
        _notifications = [
          for (final x in _notifications)
            if (x.id == updated.id) updated else x,
        ];
      });
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Notificaciones')),
      body: _loading
          ? const LoadingView()
          : _error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : _notifications.isEmpty
                  ? const EmptyState(
                      message: 'Sin notificaciones.',
                      icon: Icons.notifications_none)
                  : ListView.builder(
                      itemCount: _notifications.length,
                      itemBuilder: (context, i) {
                        final n = _notifications[i];
                        return Card(
                          child: ListTile(
                            leading: Icon(
                              n.isRead
                                  ? Icons.mark_email_read_outlined
                                  : Icons.notifications_active_outlined,
                              color: n.isRead
                                  ? Colors.grey
                                  : const Color(0xFF5B2333),
                            ),
                            title: Text(n.title,
                                style: n.isRead
                                    ? null
                                    : const TextStyle(
                                        fontWeight: FontWeight.w700)),
                            subtitle: Text(n.message ?? ''),
                            isThreeLine: true,
                            trailing: n.isRead
                                ? null
                                : TextButton(
                                    onPressed: () => _markRead(n),
                                    child: const Text('Leer'),
                                  ),
                          ),
                        );
                      },
                    ),
    );
  }
}