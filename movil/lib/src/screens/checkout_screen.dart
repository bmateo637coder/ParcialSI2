import 'package:flutter/material.dart';

import '../models.dart';
import '../services.dart';
import '../theme.dart';
import '../widgets.dart';

const _paymentMethods = ['TARJETA', 'TRANSFERENCIA', 'QR', 'PAYPAL', 'STRIPE'];

class CheckoutScreen extends StatefulWidget {
  final CartSummary cart;
  final int? branchId;

  const CheckoutScreen({super.key, required this.cart, this.branchId});

  @override
  State<CheckoutScreen> createState() => _CheckoutScreenState();
}

class _CheckoutScreenState extends State<CheckoutScreen> {
  final _formKey = GlobalKey<FormState>();
  final _cardController = TextEditingController();
  final _addressController = TextEditingController();

  String _method = 'TARJETA';
  bool _loading = false;
  Order? _order;

  @override
  void dispose() {
    _cardController.dispose();
    _addressController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_method == 'TARJETA' &&
        (_cardController.text.replaceAll(' ', '').length < 12)) {
      showSnack(context, 'Ingresa una tarjeta de prueba (ej. 4242 4242 4242 4242).',
          error: true);
      return;
    }
    setState(() => _loading = true);
    try {
      final order = await api.checkout(
        paymentMethod: _method,
        cardNumber: _cardController.text,
        shippingAddress: _addressController.text,
        branchId: widget.branchId,
      );
      if (!mounted) return;
      setState(() {
        _order = order;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      showSnack(context, e.toString(), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_order != null) {
      final order = _order!;
      final paid = order.status == 'PAGADO' ||
          order.payment?.status == 'COMPLETADO';
      final declined =
          order.status == 'CANCELADO' && order.payment?.status == 'FALLIDO';
      return Scaffold(
        appBar: AppBar(title: const Text('Resultado del pago')),
        body: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              const SizedBox(height: 24),
              Icon(
                declined ? Icons.cancel : Icons.check_circle,
                size: 72,
                color: declined ? const Color(0xFFC62828) : const Color(0xFF2E7D32),
              ),
              const SizedBox(height: 16),
              Text(declined ? 'Pago rechazado' : '¡Pedido confirmado!',
                  style: Theme.of(context).textTheme.headlineSmall
                      ?.copyWith(fontWeight: FontWeight.w800)),
              const SizedBox(height: 8),
              if (declined)
                const Text('La pasarela rechazó la tarjeta de prueba. El pedido '
                    'quedó cancelado y no se hizo ningún cobro.' +
                    '\n\nRevisa tus pedidos para reintentar el pago (CU19).')
              else ...[
                Text('Pedido #${order.id} · ${order.receiptNumber ?? ''}'),
                const SizedBox(height: 8),
                Text('Total: ${money(order.total)}',
                    style: const TextStyle(
                        fontSize: 20, fontWeight: FontWeight.w800, color: Color(0xFF5B2333))),
                if (!paid)
                  const Padding(
                    padding: EdgeInsets.only(top: 8),
                    child: Text('El pago quedó pendiente; puedes completarlo desde Mis pedidos.'),
                  ),
              ],
              const SizedBox(height: 24),
              AppPrimaryButton(
                label: 'Volver al inicio',
                icon: Icons.home_outlined,
                onPressed: () => Navigator.of(context)
                    .pushNamedAndRemoveUntil('/home', (r) => false),
              ),
            ],
          ),
        ),
      );
    }

    final cart = widget.cart;
    return Scaffold(
      appBar: AppBar(title: const Text('Confirmar pago (CU17)')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text('Método de pago',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final m in _paymentMethods)
                  ChoiceChip(
                    label: Text(m),
                    selected: _method == m,
                    onSelected: (_) => setState(() => _method = m),
                    selectedColor: const Color(0xFF5B2333),
                    labelStyle: TextStyle(
                        color: _method == m ? Colors.white : null),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            if (_method == 'TARJETA') ...[
              TextFormField(
                controller: _cardController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Número de tarjeta (sandbox)',
                  hintText: '4242 4242 4242 4242',
                  prefixIcon: Icon(Icons.credit_card),
                ),
              ),
              const SizedBox(height: 6),
              const Text('Tarjetas de prueba: 4242…4242 aprueba; '
                  '4000 0000 0000 0002 declina.',
                  style: TextStyle(fontSize: 12, color: Colors.grey)),
            ],
            if (_method == 'PAYPAL' || _method == 'STRIPE' || _method == 'QR')
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 8),
                child: Text('La pasarela sandbox aprobará la transacción automáticamente.'),
              ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _addressController,
              decoration: const InputDecoration(
                labelText: 'Dirección de envío (opcional)',
                prefixIcon: Icon(Icons.home_outlined),
              ),
            ),
            const SizedBox(height: 20),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  children: [
                    _Line('Prendas (${cart.totalItems})', money(cart.totalAmount + cart.totalDiscount)),
                    if (cart.totalDiscount > 0)
                      _Line('Descuento', '-${money(cart.totalDiscount)}',
                          color: const Color(0xFF2E7D32)),
                    const Divider(),
                    _Line('Total a pagar', money(cart.totalAmount), bold: true),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            AppPrimaryButton(
              label: 'Pagar ahora',
              icon: Icons.lock,
              loading: _loading,
              onPressed: _submit,
            ),
          ],
        ),
      ),
    );
  }
}

class _Line extends StatelessWidget {
  final String label;
  final String value;
  final bool bold;
  final Color? color;

  const _Line(this.label, this.value, {this.bold = false, this.color});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Expanded(child: Text(label, style: bold ? const TextStyle(fontWeight: FontWeight.w700) : null)),
          Text(value,
              style: TextStyle(
                fontWeight: bold ? FontWeight.w800 : FontWeight.w600,
                color: color,
              )),
        ],
      ),
    );
  }
}