import 'dart:async';

import 'package:flutter/material.dart';

import '../models.dart';
import '../services.dart';
import '../widgets.dart';
import 'product_detail_screen.dart';

class CatalogScreen extends StatefulWidget {
  const CatalogScreen({super.key});

  @override
  State<CatalogScreen> createState() => _CatalogScreenState();
}

class _CatalogScreenState extends State<CatalogScreen> {
  final _searchController = TextEditingController();
  Timer? _debounce;

  List<Product> _products = [];
  List<CategoryItem> _categories = [];
  List<IdName> _seasons = [];
  int? _selectedCategory;
  int? _selectedSeason;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        api.getProducts(),
        api.getCategories(),
        api.getSeasons(),
      ]);
      if (!mounted) return;
      setState(() {
        _products = results[0] as List<Product>;
        _categories = results[1] as List<CategoryItem>;
        _seasons = results[2] as List<IdName>;
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

  Future<void> _search(String q) async {
    try {
      final list = await api.getProducts(
          q: q, categoryId: _selectedCategory, seasonId: _selectedSeason);
      if (!mounted) return;
      setState(() => _products = list);
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    }
  }

  void _onQueryChanged(String q) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 450), () => _search(q));
  }

  Future<void> _applyFilters() async {
    try {
      final list = await api.getProducts(
          q: _searchController.text, categoryId: _selectedCategory, seasonId: _selectedSeason);
      if (!mounted) return;
      setState(() => _products = list);
    } catch (e) {
      if (mounted) showSnack(context, e.toString(), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Catálogo')),
      body: _loading
          ? const LoadingView()
          : _error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(12, 10, 12, 0),
                      child: TextField(
                        controller: _searchController,
                        onChanged: _onQueryChanged,
                        decoration: const InputDecoration(
                          hintText: 'Buscar prendas (CU10)…',
                          prefixIcon: Icon(Icons.search),
                        ),
                      ),
                    ),
                    if (_categories.isNotEmpty)
                      SizedBox(
                        height: 46,
                        child: ListView(
                          scrollDirection: Axis.horizontal,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          children: [
                            _FilterChip(
                              label: 'Todas',
                              selected: _selectedCategory == null,
                              onTap: () {
                                setState(() => _selectedCategory = null);
                                _applyFilters();
                              },
                            ),
                            for (final c in _categories)
                              _FilterChip(
                                label: c.name,
                                selected: _selectedCategory == c.id,
                                onTap: () {
                                  setState(() => _selectedCategory = c.id);
                                  _applyFilters();
                                },
                              ),
                            const SizedBox(width: 8),
                            if (_seasons.isNotEmpty)
                              DropdownButton<int?>(
                                value: _selectedSeason,
                                hint: const Text('Temporada'),
                                items: [
                                  const DropdownMenuItem<int?>(
                                      value: null, child: Text('Todas las temporadas')),
                                  for (final s in _seasons)
                                    DropdownMenuItem<int?>(
                                        value: s.id, child: Text(s.name)),
                                ],
                                onChanged: (v) {
                                  setState(() => _selectedSeason = v);
                                  _applyFilters();
                                },
                              ),
                          ],
                        ),
                      ),
                    Expanded(
                      child: _products.isEmpty
                          ? const EmptyState(
                              message: 'No hay prendas que coincidan con la búsqueda.',
                              icon: Icons.search_off)
                          : GridView.builder(
                              padding: const EdgeInsets.all(12),
                              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                                crossAxisCount: 2,
                                childAspectRatio: 0.72,
                                crossAxisSpacing: 10,
                                mainAxisSpacing: 10,
                              ),
                              itemCount: _products.length,
                              itemBuilder: (context, i) =>
                                  _ProductCard(product: _products[i]),
                            ),
                    ),
                  ],
                ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _FilterChip(
      {required this.label, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 6),
      child: FilterChip(
        label: Text(label),
        selected: selected,
        onSelected: (_) => onTap(),
        selectedColor: const Color(0xFF5B2333),
        checkmarkColor: Colors.white,
        labelStyle: TextStyle(color: selected ? Colors.white : null),
      ),
    );
  }
}

class _ProductCard extends StatelessWidget {
  final Product product;

  const _ProductCard({required this.product});

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => ProductDetailScreen(productId: product.id)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              height: 130,
              width: double.infinity,
              child: ProductImage(url: product.imageUrl, size: 130),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      product.name,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const Spacer(),
                    if (product.category != null)
                      Text(
                        product.category!.name,
                        style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                      ),
                    const SizedBox(height: 2),
                    PriceText(product.basePrice),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}