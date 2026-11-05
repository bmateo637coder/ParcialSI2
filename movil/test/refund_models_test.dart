import 'package:flutter_test/flutter_test.dart';
import 'package:fashionstore_movil/src/models.dart';

void main() {
  test(
    'El pedido conserva cobro, reembolso, saldo y prendas recibidas por cambio',
    () {
      final order = Order.fromJson({
        'id': 1,
        'client_id': 2,
        'total': 120,
        'collected_total': 150,
        'refunded_total': 50,
        'net_total': 100,
        'refund_pending': 20,
        'stock_deducted': true,
        'refunds': [
          {'id': 4, 'status': 'COMPLETADO', 'amount': 50},
        ],
        'returnable_items': [
          {'key': 'exchange:3', 'variant_id': 8, 'quantity': 1, 'amount': 100},
        ],
      });
      expect(order.total, 120);
      expect(order.collectedTotal, 150);
      expect(order.refundedTotal, 50);
      expect(order.netTotal, 100);
      expect(order.refundPending, 20);
      expect(order.stockDeducted, true);
      expect(order.returnableItems.single['variant_id'], 8);
    },
  );
  test('Un periodo con solo devoluciones conserva ventas netas negativas', () {
    final kpis = ReportKpis.fromJson({
      'gross_sales': 0,
      'refund_amount': 120,
      'refund_pending': 30,
      'total_sales': -120,
    });
    expect(kpis.totalSales, -120);
    expect(kpis.refundAmount, 120);
    expect(kpis.refundPending, 30);
    expect(kpis.grossSales, 0);
  });
}
