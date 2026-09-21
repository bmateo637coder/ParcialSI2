import 'package:flutter/material.dart';

import '../services.dart';
import '../theme.dart';
import '../widgets.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _firstName = TextEditingController();
  final _lastName = TextEditingController();
  final _email = TextEditingController();
  final _phone = TextEditingController();
  bool _loading = true;
  String? _error;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _firstName.dispose();
    _lastName.dispose();
    _email.dispose();
    _phone.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final user = await api.getProfile();
      if (!mounted) return;
      _firstName.text = user.firstName;
      _lastName.text = user.lastName;
      _email.text = user.email;
      _phone.text = user.phone ?? '';
      setState(() => _loading = false);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.toString();
      });
    }
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await api.updateProfile(
        firstName: _firstName.text.trim(),
        lastName: _lastName.text.trim(),
        email: _email.text.trim(),
        phone: _phone.text.trim(),
      );
      if (!mounted) return;
      setState(() => _saving = false);
      showSnack(context, 'Perfil actualizado ✓ (CU3)');
    } catch (e) {
      if (!mounted) return;
      setState(() => _saving = false);
      showSnack(context, e.toString(), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = api.currentUser;
    return Scaffold(
      appBar: AppBar(title: const Text('Mi perfil (CU3)')),
      body: _loading
          ? const LoadingView()
          : _error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    Center(
                      child: CircleAvatar(
                        radius: 44,
                        backgroundColor:
                            const Color(0xFF5B2333).withValues(alpha: 0.12),
                        child: const Icon(Icons.person,
                            size: 52, color: Color(0xFF5B2333)),
                      ),
                    ),
                    const SizedBox(height: 10),
                    if (user != null) ...[
                      Center(
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: const Color(0xFFC9A227).withValues(alpha: 0.2),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(
                            user.roleName,
                            style: const TextStyle(
                                fontWeight: FontWeight.w700,
                                color: Color(0xFF5B2333)),
                          ),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Center(
                        child: Text(user.email,
                            style: const TextStyle(color: Colors.grey)),
                      ),
                    ],
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _firstName,
                      decoration: const InputDecoration(labelText: 'Nombre'),
                    ),
                    const SizedBox(height: 10),
                    TextFormField(
                      controller: _lastName,
                      decoration: const InputDecoration(labelText: 'Apellido'),
                    ),
                    const SizedBox(height: 10),
                    TextFormField(
                      controller: _email,
                      keyboardType: TextInputType.emailAddress,
                      decoration: const InputDecoration(labelText: 'Email'),
                    ),
                    const SizedBox(height: 10),
                    TextFormField(
                      controller: _phone,
                      keyboardType: TextInputType.phone,
                      decoration: const InputDecoration(labelText: 'Teléfono'),
                    ),
                    const SizedBox(height: 20),
                    AppPrimaryButton(
                      label: 'Guardar cambios',
                      icon: Icons.save_outlined,
                      loading: _saving,
                      onPressed: _save,
                    ),
                  ],
                ),
    );
  }
}