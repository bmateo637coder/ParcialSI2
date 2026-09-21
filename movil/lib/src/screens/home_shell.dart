import 'package:flutter/material.dart';

import '../services.dart';
import 'menu_screen.dart';
import 'catalog_screen.dart';
import 'branches_screen.dart';
import 'cart_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;
  int _cartBadge = 0;

  @override
  void initState() {
    super.initState();
    if (api.isAuthenticated && !api.isStaff && !api.isProvider) {
      _loadCartBadge();
    }
  }

  Future<void> _loadCartBadge() async {
    try {
      final cart = await api.getCart();
      if (mounted) setState(() => _cartBadge = cart.totalItems);
    } catch (_) {
      // El badge es opcional.
    }
  }

  @override
  Widget build(BuildContext context) {
    final pages = <Widget>[
      const CatalogScreen(),
      const BranchesScreen(),
      CartScreen(refreshBadge: (c) {
        if (mounted) setState(() => _cartBadge = c);
      }),
      MenuScreen(onLogout: () {
        api.logout();
        Navigator.of(context).pushNamedAndRemoveUntil('/login', (r) => false);
      }),
    ];

    return Scaffold(
      body: IndexedStack(index: _index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) {
          setState(() => _index = i);
          if (i == 2 && api.isAuthenticated && !api.isStaff && !api.isProvider) {
            _loadCartBadge();
          }
        },
        destinations: [
          const NavigationDestination(
            icon: Icon(Icons.checkroom_outlined),
            selectedIcon: Icon(Icons.checkroom),
            label: 'Catálogo',
          ),
          const NavigationDestination(
            icon: Icon(Icons.storefront_outlined),
            selectedIcon: Icon(Icons.storefront),
            label: 'Sucursales',
          ),
          NavigationDestination(
            icon: Badge(
              isLabelVisible: _cartBadge > 0,
              label: Text('$_cartBadge'),
              child: const Icon(Icons.shopping_cart_outlined),
            ),
            selectedIcon: Badge(
              isLabelVisible: _cartBadge > 0,
              label: Text('$_cartBadge'),
              child: const Icon(Icons.shopping_cart),
            ),
            label: 'Carrito',
          ),
          const NavigationDestination(
            icon: Icon(Icons.menu),
            selectedIcon: Icon(Icons.menu_open),
            label: 'Menú',
          ),
        ],
      ),
    );
  }
}