import 'package:flutter_test/flutter_test.dart';

import 'package:fashionstore_movil/src/models.dart';

void main() {
  test('money formatea en Bs con 2 decimales', () {
    expect(money(1234.5), contains('Bs'));
    expect(money(0), contains('0'));
    expect(money(-1), contains('-'));
  });

  test('fmtDate devuelve guion para nulos o vacio', () {
    expect(fmtDate(null), '—');
    expect(fmtDate(''), '—');
  });

  test('fmtDate formatea fechas ISO', () {
    expect(fmtDate('2025-01-15T10:30:00Z'), contains('2025'));
  });

  test('Product.fromJson tolera valores faltantes', () {
    final p = Product.fromJson({'id': 7, 'name': 'Blazer'});
    expect(p.id, 7);
    expect(p.name, 'Blazer');
    expect(p.basePrice, 0);
  });

  test('Reservation.fromJson parsea items (regresion whereType)', () {
    final r = Reservation.fromJson({
      'id': 1,
      'code': 'R-001',
      'client_id': 2,
      'branch_id': 1,
      'items': [
        {'id': 9, 'variant_id': 3, 'quantity': 2, 'product_name': 'Camisa'},
      ],
    });
    expect(r.items, hasLength(1));
    expect(r.items.first.productName, 'Camisa');
    expect(r.total, 0);
  });

  test('Order.fromJson parsea items y payment', () {
    final o = Order.fromJson({
      'id': 1,
      'client_id': 1,
      'order_type': 'TIENDA',
      'items': [
        {'id': 1, 'variant_id': 1, 'quantity': 1},
      ],
      'payment': {
        'id': 5,
        'method': 'TARJETA',
        'amount': 100,
        'status': 'APROBADO',
      },
    });
    expect(o.items, hasLength(1));
    expect(o.payment?.method, 'TARJETA');
  });

  test('DashboardReport.fromJson parsea series (regresion casts)', () {
    final d = DashboardReport.fromJson({
      'sales_series': [
        {'date': '2025-01-01', 'amount': 10, 'orders': 1},
      ],
      'by_category': [
        {'category_name': 'Ropa', 'sales': 5, 'units': 2},
      ],
      'top_products': [
        {'product_id': 1, 'name': 'Abrigo', 'units': 1, 'revenue': 9},
      ],
      'kpis': {'total_sales': 123},
    });
    expect(d.salesSeries, hasLength(1));
    expect(d.byCategory.first.categoryName, 'Ropa');
    expect(d.topProducts.first.name, 'Abrigo');
    expect(d.kpis.totalSales, 123);
  });

  test('CartSummary.fromJson castea items', () {
    final c = CartSummary.fromJson({
      'items': [
        {
          'id': 1,
          'variant_id': 1,
          'quantity': 2,
          'unit_price': 10,
          'discount': 0,
          'subtotal': 20,
        },
      ],
      'total_items': 2,
      'total_amount': 20,
      'total_discount': 0,
    });
    expect(c.items, hasLength(1));
    expect(c.totalItems, 2);
  });
}