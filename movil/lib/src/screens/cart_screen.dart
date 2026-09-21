import 'package:flutter/material.dart';

import '../models.dart';
import '../services.dart';
import '../theme.dart';
import '../widgets.dart';
import 'checkout_screen.dart';

class CartScreen extends StatefulWidget {
  final ValueChanged<int>? refreshBadge;

  const CartScreen({super.key, this.refreshBadge});

  @override
  State<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends State<CartScreen> {
  CartSummary? _cart;
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
      final cart = await api.getCart();
      if (!mounted) return;
      setState(() {
        _cart = cart;
        _loading = false;
      });
      widget.refreshBadge?.call(cart.totalItems);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.toString();
      });
    }
  }

  Future<void> _update(CartItem item, int quantity) async {
    if (quantity < 1) return;
    try {
      final cart = await api.updateCartItem(item.id, quantity);
      if (!mounted) return;
      setState(() => _cart = cart);
      widget.refreshBadge?.call(cart.totalItems);
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    }
  }

  Future<void> _remove(CartItem item) async {
    try {
      final cart = await api.removeCartItem(item.id);
      if (!mounted) return;
      setState(() => _cart = cart);
      widget.refreshBadge?.call(cart.totalItems);
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    }
  }

  Future<void> _clear() async {
    try {
      final cart = await api.clearCart();
      if (!mounted) return;
      setState(() => _cart = cart);
      widget.refreshBadge?.call(0);
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cart = _cart;
    return Scaffold(
      appBar: AppBar(title: const Text('Mi carrito')),
      body: _loading
          ? const LoadingView()
          : _error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : cart == null || cart.items.isEmpty
                  ? const EmptyState(
                      message: 'Tu carrito está vacío. Explora el catálogo.',
                      icon: Icons.shopping_cart_outlined)
                  : Column(
                      children: [
                        Expanded(
                          child: ListView.builder(
                            padding: const EdgeInsets.only(bottom: 8),
                            itemCount: cart.items.length,
                            itemBuilder: (context, i) {
                              final item = cart.items[i];
                              return Card(
                                child: Padding(
                                  padding: const EdgeInsets.all(10),
                                  child: Row(
                                    children: [
                                      ProductImage(url: item.imageUrl, size: 60),
                                      const SizedBox(width: 10),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Text(item.productName ?? '',
                                                style: const TextStyle(
                                                    fontWeight: FontWeight.w600),
                                                maxLines: 1,
                                                overflow: TextOverflow.ellipsis),
                                            Text(
                                                '${item.sizeName ?? ''} / ${item.colorName ?? ''}'),
                                            Row(
                                              children: [
                                                if (item.discount > 0) ...[
                                                  Text('${item.unitPrice.toStringAsFixed(2)}→',
                                                      style: TextStyle(
                                                          color: Colors.grey,
                                                          decoration: TextDecoration
                                                              .lineThrough)),
                                                  const SizedBox(width: 4),
                                                  Text(
                                                    money(item.unitPrice),
                                                    style: const TextStyle(
                                                        color: Color(0xFFC62828),
                                                        fontWeight: FontWeight.w700),
                                                  ),
                                                ] else
                                                  PriceText(item.unitPrice),
                                                const Spacer(),
                                                _QtyStepper(
                                                  qty: item.quantity,
                                                  onMinus: () => _update(item, item.quantity - 1),
                                                  onPlus: () => _update(item, item.quantity + 1),
                                                ),
                                              ],
                                            ),
                                          ],
                                        ),
                                      ),
                                      IconButton(
                                        onPressed: () => _remove(item),
                                        icon: const Icon(Icons.delete_outline,
                                            color: Color(0xFFC62828)),
                                      ),
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: const BoxDecoration(
                            color: Colors.white,
                            border: Border(top: BorderSide(color: Color(0xFFE8DED3))),
                          ),
                          child: Column(
                            children: [
                              _TotalRow(label: 'Subtotal',
                                  value: cart.totalAmount + cart.totalDiscount),
                              if (cart.totalDiscount > 0) ...[
                                _TotalRow(
                                    label: 'Descuento (promociones)',
                                    value: -cart.totalDiscount,
                                    valueColor: const Color(0xFF2E7D32)),
                              ],
                              _TotalRow(label: 'Total', value: cart.totalAmount, bold: true),
                              const SizedBox(height: 8),
                              Row(
                                children: [
                                  Expanded(
                                    child: OutlinedButton(
                                      style: OutlinedButton.styleFrom(
                                          minimumSize: const Size.fromHeight(48)),
                                      onPressed: _clear,
                                      child: const Text('Vaciar'),
                                    ),
                                  ),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    flex: 2,
                                    child: AppPrimaryButton(
                                      label: 'Tramitar compra',
                                      icon: Icons.payment,
                                      onPressed: () async {
                                        await Navigator.of(context).push(
                                          MaterialPageRoute(
                                              builder: (_) => CheckoutScreen(
                                                  cart: cart)),
                                        );
                                        _load();
                                      },
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
    );
  }
}

class _QtyStepper extends StatelessWidget {
  final int qty;
  final VoidCallback onMinus;
  final VoidCallback onPlus;

  const _QtyStepper(
      {required this.qty, required this.onMinus, required this.onPlus});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        IconButton(
          onPressed: qty > 1 ? onMinus : null,
          icon: const Icon(Icons.remove_circle_outline),
          visualDensity: VisualDensity.compact,
        ),
        Text('$qty'),
        IconButton(
          onPressed: onPlus,
          icon: const Icon(Icons.add_circle_outline),
          visualDensity: VisualDensity.compact,
        ),
      ],
    );
  }
}

class _TotalRow extends StatelessWidget {
  final String label;
  final double value;
  final bool bold;
  final Color? valueColor;

  const _TotalRow({
    required this.label,
    required this.value,
    this.bold = false,
    this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    final sign = value < 0 ? '-' : '';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Expanded(child: Text(label, style: bold ? const TextStyle(fontWeight: FontWeight.w700) : null)),
          Text('$sign${money(value.abs())}',
              style: TextStyle(
                fontWeight: bold ? FontWeight.w800 : FontWeight.w600,
                fontSize: bold ? 18 : 14,
                color: valueColor ?? (bold ? const Color(0xFF5B2333) : null),
              )),
        ],
      ),
    );
  }
}