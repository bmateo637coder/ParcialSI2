import 'package:flutter/material.dart';

import '../services.dart';
import '../theme.dart';
import '../widgets.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _firstName = TextEditingController();
  final _lastName = TextEditingController();

  bool _registerMode = false;
  bool _loading = false;
  bool _obscure = true;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _firstName.dispose();
    _lastName.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    try {
      if (_registerMode) {
        await api.register(
          firstName: _firstName.text.trim(),
          lastName: _lastName.text.trim(),
          email: _email.text.trim(),
          password: _password.text,
        );
        if (!mounted) return;
        showSnack(context, 'Cuenta creada. Inicia sesión para continuar.');
        setState(() => _registerMode = false);
      } else {
        await api.login(_email.text.trim(), _password.text);
        if (!mounted) return;
        Navigator.of(context).pushNamedAndRemoveUntil('/home', (r) => false);
      }
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const SizedBox(height: 12),
                    const Icon(Icons.storefront, size: 64, color: AppColors.primary),
                    const SizedBox(height: 8),
                    Text(
                      'FashionStore',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.headlineMedium?.copyWith(
                        color: AppColors.primary,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    Text(
                      'Moda con vestidores virtuales',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 28),
                    AnimatedSwitcher(
                      duration: const Duration(milliseconds: 200),
                      child: _registerMode
                          ? Row(
                              key: const ValueKey('regFields'),
                              children: [
                                Expanded(
                                  child: TextFormField(
                                    controller: _firstName,
                                    decoration: const InputDecoration(
                                        labelText: 'Nombre', prefixIcon: Icon(Icons.person)),
                                    validator: (v) =>
                                        (v == null || v.trim().isEmpty) ? 'Requerido' : null,
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: TextFormField(
                                    controller: _lastName,
                                    decoration: const InputDecoration(
                                        labelText: 'Apellido', prefixIcon: Icon(Icons.person_outline)),
                                    validator: (v) =>
                                        (v == null || v.trim().isEmpty) ? 'Requerido' : null,
                                  ),
                                ),
                              ],
                            )
                          : const SizedBox.shrink(key: ValueKey('noRegFields')),
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _email,
                      keyboardType: TextInputType.emailAddress,
                      decoration: const InputDecoration(
                          labelText: 'Correo',
                          prefixIcon: Icon(Icons.mail_outline),
                          hintText: 'cliente@fashionstore.com'),
                      validator: (v) =>
                          (v == null || !v.contains('@')) ? 'Correo inválido' : null,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _password,
                      obscureText: _obscure,
                      decoration: InputDecoration(
                        labelText: 'Contraseña',
                        prefixIcon: const Icon(Icons.lock_outline),
                        suffixIcon: IconButton(
                          icon: Icon(_obscure ? Icons.visibility_off : Icons.visibility),
                          onPressed: () => setState(() => _obscure = !_obscure),
                        ),
                      ),
                      validator: (v) =>
                          (v == null || v.length < 4) ? 'Mínimo 4 caracteres' : null,
                    ),
                    const SizedBox(height: 20),
                    AppPrimaryButton(
                      label: _registerMode ? 'Crear cuenta' : 'Iniciar sesión',
                      icon: _registerMode ? Icons.person_add : Icons.login,
                      loading: _loading,
                      onPressed: _submit,
                    ),
                    const SizedBox(height: 10),
                    TextButton(
                      onPressed: _loading
                          ? null
                          : () => setState(() => _registerMode = !_registerMode),
                      child: Text(_registerMode
                          ? '¿Ya tienes cuenta? Inicia sesión'
                          : '¿Nuevo cliente? Regístrate (CU1)'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}