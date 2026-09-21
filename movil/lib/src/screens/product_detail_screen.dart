import 'package:flutter/material.dart';

import '../models.dart';
import '../services.dart';
import '../theme.dart';
import '../widgets.dart';
import 'availability_screen.dart';
import 'fitting_room_screen.dart';
import 'reservation_create_screen.dart';

class ProductDetailScreen extends StatefulWidget {
  final int productId;

  const ProductDetailScreen({super.key, required this.productId});

  @override
  State<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends State<ProductDetailScreen> {
  Product? _product;
  List<ProductVariant> _variants = [];
  List<AvailabilityItem> _availability = [];
  bool _loading = true;
  String? _error;

  int _quantity = 1;

  String? _sizeFilter;
  String? _colorFilter;

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
      final results = await Future.wait([
        api.getProduct(widget.productId),
        api.getVariants(widget.productId),
        api.getAvailability(productId: widget.productId),
      ]);
      if (!mounted) return;
      final variants = results[1] as List<ProductVariant>;
      setState(() {
        _product = results[0] as Product;
        _variants = variants;
        _availability = results[2] as List<AvailabilityItem>;
        if (variants.isNotEmpty) {
          _sizeFilter = variants.first.sizeName;
          _colorFilter = variants.first.colorName;
        }
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

  List<String> get _sizes => _variants
      .where((v) => v.sizeName != null && v.sizeName!.isNotEmpty)
      .map((v) => v.sizeName!)
      .toSet()
      .toList();

  List<String> get _colors => _variants
      .where((v) => v.colorName != null && v.colorName!.isNotEmpty)
      .map((v) => v.colorName!)
      .toSet()
      .toList();

  ProductVariant? get _selectedVariant {
    for (final v in _variants) {
      if (v.sizeName == _sizeFilter && v.colorName == _colorFilter) return v;
    }
    return null;
  }

  int _availableFor(ProductVariant v) {
    int total = 0;
    for (final a in _availability) {
      if (a.variantId == v.id) total += a.available;
    }
    return total;
  }

  Future<void> _addToCart() async {
    final v = _selectedVariant;
    if (v == null) {
      showSnack(context, 'Selecciona talla y color (CU10).', error: true);
      return;
    }
    try {
      await api.addToCart(v.id, quantity: _quantity);
      if (!mounted) return;
      showSnack(context, 'Agregado al carrito ✓');
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Scaffold(body: LoadingView());
    if (_error != null) {
      return Scaffold(body: ErrorView(message: _error!, onRetry: _load));
    }
    final product = _product!;
    final variant = _selectedVariant;

    return Scaffold(
      appBar: AppBar(title: const Text('Detalle')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Center(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: ProductImage(url: product.imageUrl, size: 240),
            ),
          ),
          const SizedBox(height: 12),
          Text(product.name,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700)),
          if (product.category != null || product.season != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                [
                  if (product.category != null) product.category!.name,
                  if (product.season != null) product.season!.name,
                ].join(' · '),
                style: TextStyle(color: Colors.grey.shade600),
              ),
            ),
          const SizedBox(height: 6),
          PriceText(product.basePrice),
          if (product.description != null && product.description!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(product.description!),
          ],
          const SizedBox(height: 16),

          // Talla y color (variantes)
          Text('Talla', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 6),
          Wrap(
            spacing: 8,
            children: [
              for (final s in _sizes)
                ChoiceChip(
                  label: Text(s),
                  selected: _sizeFilter == s,
                  onSelected: (_) => setState(() => _sizeFilter = s),
                ),
            ],
          ),
          const SizedBox(height: 12),
          Text('Color', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 6),
          Wrap(
            spacing: 8,
            children: [
              for (final c in _colors)
                ChoiceChip(
                  label: Text(c),
                  selected: _colorFilter == c,
                  onSelected: (_) => setState(() => _colorFilter = c),
                ),
            ],
          ),
          const SizedBox(height: 12),
          if (variant != null)
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: const Color(0xFF5B2333).withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                children: [
                  const Icon(Icons.inventory_2_outlined, size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'SKU ${variant.sku} · Stock total: ${_availableFor(variant)} unidades',
                      style: const TextStyle(fontWeight: FontWeight.w500),
                    ),
                  ),
                ],
              ),
            ),

          const SizedBox(height: 16),
          Text('Cantidad', style: Theme.of(context).textTheme.titleSmall),
          Row(
            children: [
              IconButton.outlined(
                onPressed: _quantity > 1
                    ? () => setState(() => _quantity--)
                    : null,
                icon: const Icon(Icons.remove),
              ),
              Text('$_quantity', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
              IconButton.outlined(
                onPressed: () => setState(() => _quantity++),
                icon: const Icon(Icons.add),
              ),
              const Spacer(),
              OutlinedButton.icon(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => AvailabilityScreen(productId: product.id))),
                icon: const Icon(Icons.storefront_outlined),
                label: const Text('Disponibilidad'),
              ),
            ],
          ),

          const SizedBox(height: 18),
          AppPrimaryButton(
            label: 'Agregar al carrito',
            icon: Icons.add_shopping_cart,
            onPressed: _addToCart,
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: variant == null
                      ? null
                      : () => Navigator.of(context).push(MaterialPageRoute(
                            builder: (_) => FittingRoomScreen(
                              productName: product.name,
                              initialColor: variant.colorName,
                              imageUrl: product.imageUrl,
                            ),
                          )),
                  icon: const Icon(Icons.face_retouching_natural),
                  label: const Text('Vestidor AR'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: variant == null
                      ? null
                      : () => Navigator.of(context).push(MaterialPageRoute(
                            builder: (_) => ReservationCreateScreen(
                              initialVariantId: variant.id,
                              initialLabel: '${product.name} '
                                  '${variant.sizeName}/${variant.colorName}',
                            ),
                          )),
                  icon: const Icon(Icons.event_seat_outlined),
                  label: const Text('Reservar'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}