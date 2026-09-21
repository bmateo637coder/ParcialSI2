import 'package:flutter/material.dart';

import 'src/screens/home_shell.dart';
import 'src/screens/login_screen.dart';
import 'src/services.dart';
import 'src/theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await api.restoreSession();
  runApp(const FashionStoreApp());
}

class FashionStoreApp extends StatelessWidget {
  const FashionStoreApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FashionStore',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(),
      initialRoute: '/',
      routes: {
        '/': (_) => _AuthGate(),
        '/login': (_) => const LoginScreen(),
        '/home': (_) => const HomeShell(),
      },
    );
  }
}

class _AuthGate extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    if (api.isAuthenticated) return const HomeShell();
    return const LoginScreen();
  }
}