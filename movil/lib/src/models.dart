import 'package:intl/intl.dart';

T? _g<T>(Map<String, dynamic> json, String key, [T? fallback]) {
  final v = json[key];
  if (v == null) return fallback;
  return v as T;
}

double _num(Map<String, dynamic> json, String key) {
  final v = json[key];
  if (v is num) return v.toDouble();
  return 0;
}

List<String> _listStrings(Map<String, dynamic> json, String key) {
  final v = json[key];
  if (v is List) return v.whereType<String>().toList();
  return const [];
}

class User {
  final int id;
  final String firstName;
  final String lastName;
  final String email;
  final String roleName;
  final bool isActive;
  final String? phone;
  final String? createdAt;

  User({
    required this.id,
    required this.firstName,
    required this.lastName,
    required this.email,
    required this.roleName,
    required this.isActive,
    this.phone,
    this.createdAt,
  });

  factory User.fromJson(Map<String, dynamic> j) => User(
        id: _g<int>(j, 'id', 0) ?? 0,
        firstName: _g<String>(j, 'first_name', '') ?? '',
        lastName: _g<String>(j, 'last_name', '') ?? '',
        email: _g<String>(j, 'email', '') ?? '',
        roleName: _g<String>(j, 'role_name', '') ?? '',
        isActive: _g<bool>(j, 'is_active', true) ?? true,
        phone: _g<String>(j, 'phone'),
        createdAt: _g<String>(j, 'created_at'),
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'first_name': firstName,
        'last_name': lastName,
        'email': email,
        'role_name': roleName,
        'is_active': isActive,
        'phone': phone,
        'created_at': createdAt,
      };

  String get fullName => '$firstName $lastName'.trim();
}

class Branch {
  final int id;
  final String name;
  final String city;
  final String? address;
  final String? phone;
  final bool isActive;

  Branch({
    required this.id,
    required this.name,
    required this.city,
    this.address,
    this.phone,
    this.isActive = true,
  });

  factory Branch.fromJson(Map<String, dynamic> j) => Branch(
        id: _g<int>(j, 'id', 0) ?? 0,
        name: _g<String>(j, 'name', '') ?? '',
        city: _g<String>(j, 'city', '') ?? '',
        address: _g<String>(j, 'address'),
        phone: _g<String>(j, 'phone'),
        isActive: _g<bool>(j, 'is_active', true) ?? true,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'city': city,
        'address': address,
        'phone': phone,
        'is_active': isActive,
      };
}

class IdName {
  final int id;
  final String name;

  IdName({required this.id, required this.name});

  factory IdName.fromJson(Map<String, dynamic> j) =>
      IdName(id: _g<int>(j, 'id', 0) ?? 0, name: _g<String>(j, 'name', '') ?? '');
}

class CategoryItem extends IdName {
  final int? productsCount;

  CategoryItem({required super.id, required super.name, this.productsCount});

  factory CategoryItem.fromJson(Map<String, dynamic> j) => CategoryItem(
        id: _g<int>(j, 'id', 0) ?? 0,
        name: _g<String>(j, 'name', '') ?? '',
        productsCount: _g<int>(j, 'products_count'),
      );
}

class Product {
  final int id;
  final String name;
  final String? description;
  final double basePrice;
  final String? imageUrl;
  final IdName? category;
  final IdName? season;
  final IdName? provider;
  final int? providerId;
  final bool isActive;

  Product({
    required this.id,
    required this.name,
    this.description,
    required this.basePrice,
    this.imageUrl,
    this.category,
    this.season,
    this.provider,
    this.providerId,
    this.isActive = true,
  });

  factory Product.fromJson(Map<String, dynamic> j) => Product(
        id: _g<int>(j, 'id', 0) ?? 0,
        name: _g<String>(j, 'name', '') ?? '',
        description: _g<String>(j, 'description'),
        basePrice: _num(j, 'base_price'),
        imageUrl: _g<String>(j, 'image_url'),
        category: j['category'] is Map
            ? IdName.fromJson(j['category'] as Map<String, dynamic>)
            : null,
        season: j['season'] is Map
            ? IdName.fromJson(j['season'] as Map<String, dynamic>)
            : null,
        provider: j['provider'] is Map
            ? IdName.fromJson(j['provider'] as Map<String, dynamic>)
            : null,
        providerId: _g<int>(j, 'provider_id'),
        isActive: _g<bool>(j, 'is_active', true) ?? true,
      );
}

class ProductVariant {
  final int id;
  final int productId;
  final int? sizeId;
  final int? colorId;
  final String? sizeName;
  final String? colorName;
  final String sku;
  final int stock;
  final double? price;
  final double? effectivePrice;

  ProductVariant({
    required this.id,
    required this.productId,
    this.sizeId,
    this.colorId,
    this.sizeName,
    this.colorName,
    this.sku = '',
    this.stock = 0,
    this.price,
    this.effectivePrice,
  });

  factory ProductVariant.fromJson(Map<String, dynamic> j) => ProductVariant(
        id: _g<int>(j, 'id', 0) ?? 0,
        productId: _g<int>(j, 'product_id', 0) ?? 0,
        sizeId: _g<int>(j, 'size_id'),
        colorId: _g<int>(j, 'color_id'),
        sizeName: _g<String>(j, 'size_name'),
        colorName: _g<String>(j, 'color_name'),
        sku: _g<String>(j, 'sku', '') ?? '',
        stock: _g<int>(j, 'stock', 0) ?? 0,
        price: j['price'] is num ? (j['price'] as num).toDouble() : null,
        effectivePrice: j['effective_price'] is num
            ? (j['effective_price'] as num).toDouble()
            : null,
      );

  String get label =>
      '${sizeName ?? 'N/D'} / ${colorName ?? 'N/D'} · ${sku.isEmpty ? '' : sku}';
}

class AvailabilityItem {
  final int variantId;
  final int productId;
  final String productName;
  final String? imageUrl;
  final String? sizeName;
  final String? colorName;
  final String? sku;
  final int? branchId;
  final String? branchName;
  final String? city;
  final int available;
  final double? price;

  AvailabilityItem({
    required this.variantId,
    required this.productId,
    required this.productName,
    this.imageUrl,
    this.sizeName,
    this.colorName,
    this.sku,
    this.branchId,
    this.branchName,
    this.city,
    this.available = 0,
    this.price,
  });

  factory AvailabilityItem.fromJson(Map<String, dynamic> j) => AvailabilityItem(
        variantId: _g<int>(j, 'variant_id', 0) ?? 0,
        productId: _g<int>(j, 'product_id', 0) ?? 0,
        productName: _g<String>(j, 'product_name', '') ?? '',
        imageUrl: _g<String>(j, 'image_url'),
        sizeName: _g<String>(j, 'size_name'),
        colorName: _g<String>(j, 'color_name'),
        sku: _g<String>(j, 'sku'),
        branchId: _g<int>(j, 'branch_id'),
        branchName: _g<String>(j, 'branch_name'),
        city: _g<String>(j, 'city'),
        available: _g<int>(j, 'available', 0) ?? 0,
        price: j['price'] is num ? (j['price'] as num).toDouble() : null,
      );
}

class CartItem {
  final int id;
  final int variantId;
  final int quantity;
  final int? productId;
  final String? productName;
  final String? imageUrl;
  final String? sizeName;
  final String? colorName;
  final String? sku;
  final double unitPrice;
  final double discount;
  final double subtotal;

  CartItem({
    required this.id,
    required this.variantId,
    required this.quantity,
    this.productId,
    this.productName,
    this.imageUrl,
    this.sizeName,
    this.colorName,
    this.sku,
    this.unitPrice = 0,
    this.discount = 0,
    this.subtotal = 0,
  });

  factory CartItem.fromJson(Map<String, dynamic> j) => CartItem(
        id: _g<int>(j, 'id', 0) ?? 0,
        variantId: _g<int>(j, 'variant_id', 0) ?? 0,
        quantity: _g<int>(j, 'quantity', 0) ?? 0,
        productId: _g<int>(j, 'product_id'),
        productName: _g<String>(j, 'product_name'),
        imageUrl: _g<String>(j, 'image_url'),
        sizeName: _g<String>(j, 'size_name'),
        colorName: _g<String>(j, 'color_name'),
        sku: _g<String>(j, 'sku'),
        unitPrice: _num(j, 'unit_price'),
        discount: _num(j, 'discount'),
        subtotal: _num(j, 'subtotal'),
      );
}

class CartSummary {
  final List<CartItem> items;
  final int totalItems;
  final double totalAmount;
  final double totalDiscount;

  CartSummary({
    this.items = const [],
    this.totalItems = 0,
    this.totalAmount = 0,
    this.totalDiscount = 0,
  });

  factory CartSummary.fromJson(Map<String, dynamic> j) {
    final raw = j['items'];
    final list = <CartItem>[];
    if (raw is List) {
      for (final e in raw) {
        if (e is Map<String, dynamic>) list.add(CartItem.fromJson(e));
      }
    }
    return CartSummary(
      items: list,
      totalItems: _g<int>(j, 'total_items', 0) ?? 0,
      totalAmount: _num(j, 'total_amount'),
      totalDiscount: _num(j, 'total_discount'),
    );
  }
}

class ReservationItem {
  final int id;
  final int variantId;
  final int quantity;
  final double unitPrice;
  final double subtotal;
  final int? productId;
  final String? productName;
  final String? imageUrl;
  final String? sizeName;
  final String? colorName;
  final String? sku;

  ReservationItem({
    required this.id,
    required this.variantId,
    required this.quantity,
    this.unitPrice = 0,
    this.subtotal = 0,
    this.productId,
    this.productName,
    this.imageUrl,
    this.sizeName,
    this.colorName,
    this.sku,
  });

  factory ReservationItem.fromJson(Map<String, dynamic> j) => ReservationItem(
        id: _g<int>(j, 'id', 0) ?? 0,
        variantId: _g<int>(j, 'variant_id', 0) ?? 0,
        quantity: _g<int>(j, 'quantity', 0) ?? 0,
        unitPrice: _num(j, 'unit_price'),
        subtotal: _num(j, 'subtotal'),
        productId: _g<int>(j, 'product_id'),
        productName: _g<String>(j, 'product_name'),
        imageUrl: _g<String>(j, 'image_url'),
        sizeName: _g<String>(j, 'size_name'),
        colorName: _g<String>(j, 'color_name'),
        sku: _g<String>(j, 'sku'),
      );
}

class Reservation {
  final int id;
  final String code;
  final int clientId;
  final String? clientName;
  final int branchId;
  final String? branchName;
  final String status;
  final String? reservationDate;
  final String? expirationDate;
  final String? attendDate;
  final List<ReservationItem> items;
  final double total;
  final int itemCount;

  Reservation({
    required this.id,
    this.code = '',
    required this.clientId,
    this.clientName,
    required this.branchId,
    this.branchName,
    this.status = '',
    this.reservationDate,
    this.expirationDate,
    this.attendDate,
    this.items = const [],
    this.total = 0,
    this.itemCount = 0,
  });

  factory Reservation.fromJson(Map<String, dynamic> j) {
    var items = <ReservationItem>[];
    final raw = j['items'];
    if (raw is List) {
      items = raw
          .whereType<Map<String, dynamic>>()
          .map(ReservationItem.fromJson)
          .toList();
    }
    return Reservation(
      id: _g<int>(j, 'id', 0) ?? 0,
      code: _g<String>(j, 'code', '') ?? '',
      clientId: _g<int>(j, 'client_id', 0) ?? 0,
      clientName: _g<String>(j, 'client_name'),
      branchId: _g<int>(j, 'branch_id', 0) ?? 0,
      branchName: _g<String>(j, 'branch_name'),
      status: _g<String>(j, 'status', '') ?? '',
      reservationDate: _g<String>(j, 'reservation_date'),
      expirationDate: _g<String>(j, 'expiration_date'),
      attendDate: _g<String>(j, 'attend_date'),
      items: items,
      total: _num(j, 'total'),
      itemCount: _g<int>(j, 'item_count', 0) ?? 0,
    );
  }
}

class OrderItem {
  final int id;
  final int variantId;
  final int quantity;
  final double unitPrice;
  final double discount;
  final double subtotal;
  final int? productId;
  final String? productName;
  final String? imageUrl;
  final String? sizeName;
  final String? colorName;
  final String? sku;

  OrderItem({
    required this.id,
    required this.variantId,
    required this.quantity,
    this.unitPrice = 0,
    this.discount = 0,
    this.subtotal = 0,
    this.productId,
    this.productName,
    this.imageUrl,
    this.sizeName,
    this.colorName,
    this.sku,
  });

  factory OrderItem.fromJson(Map<String, dynamic> j) => OrderItem(
        id: _g<int>(j, 'id', 0) ?? 0,
        variantId: _g<int>(j, 'variant_id', 0) ?? 0,
        quantity: _g<int>(j, 'quantity', 0) ?? 0,
        unitPrice: _num(j, 'unit_price'),
        discount: _num(j, 'discount'),
        subtotal: _num(j, 'subtotal'),
        productId: _g<int>(j, 'product_id'),
        productName: _g<String>(j, 'product_name'),
        imageUrl: _g<String>(j, 'image_url'),
        sizeName: _g<String>(j, 'size_name'),
        colorName: _g<String>(j, 'color_name'),
        sku: _g<String>(j, 'sku'),
      );
}

class PaymentBrief {
  final int id;
  final String method;
  final double amount;
  final String status;
  final String? stripePaymentId;
  final String? createdAt;
  final String? paidAt;

  PaymentBrief({
    required this.id,
    this.method = '',
    this.amount = 0,
    this.status = '',
    this.stripePaymentId,
    this.createdAt,
    this.paidAt,
  });

  factory PaymentBrief.fromJson(Map<String, dynamic> j) => PaymentBrief(
        id: _g<int>(j, 'id', 0) ?? 0,
        method: _g<String>(j, 'method', '') ?? '',
        amount: _num(j, 'amount'),
        status: _g<String>(j, 'status', '') ?? '',
        stripePaymentId: _g<String>(j, 'stripe_payment_id'),
        createdAt: _g<String>(j, 'created_at'),
        paidAt: _g<String>(j, 'paid_at'),
      );
}

class Order {
  final int id;
  final int clientId;
  final String? clientName;
  final int? branchId;
  final String? branchName;
  final String orderType;
  final String status;
  final double total;
  final String? shippingAddress;
  final String? receiptNumber;
  final String? createdAt;
  final List<OrderItem> items;
  final PaymentBrief? payment;

  Order({
    required this.id,
    required this.clientId,
    this.clientName,
    this.branchId,
    this.branchName,
    this.orderType = '',
    this.status = '',
    this.total = 0,
    this.shippingAddress,
    this.receiptNumber,
    this.createdAt,
    this.items = const [],
    this.payment,
  });

  factory Order.fromJson(Map<String, dynamic> j) {
    var items = <OrderItem>[];
    final raw = j['items'];
    if (raw is List) {
      items = raw
          .whereType<Map<String, dynamic>>()
          .map(OrderItem.fromJson)
          .toList();
    }
    return Order(
      id: _g<int>(j, 'id', 0) ?? 0,
      clientId: _g<int>(j, 'client_id', 0) ?? 0,
      clientName: _g<String>(j, 'client_name'),
      branchId: _g<int>(j, 'branch_id'),
      branchName: _g<String>(j, 'branch_name'),
      orderType: _g<String>(j, 'order_type', '') ?? '',
      status: _g<String>(j, 'status', '') ?? '',
      total: _num(j, 'total'),
      shippingAddress: _g<String>(j, 'shipping_address'),
      receiptNumber: _g<String>(j, 'receipt_number'),
      createdAt: _g<String>(j, 'created_at'),
      items: items,
      payment: j['payment'] is Map
          ? PaymentBrief.fromJson(j['payment'] as Map<String, dynamic>)
          : null,
    );
  }
}

class RecommendedItem {
  final int productId;
  final String name;
  final String category;
  final double basePrice;
  final bool inStock;
  final String reason;
  final double score;

  RecommendedItem({
    required this.productId,
    this.name = '',
    this.category = '',
    this.basePrice = 0,
    this.inStock = false,
    this.reason = '',
    this.score = 0,
  });

  factory RecommendedItem.fromJson(Map<String, dynamic> j) => RecommendedItem(
        productId: _g<int>(j, 'product_id', 0) ?? 0,
        name: _g<String>(j, 'name', '') ?? '',
        category: _g<String>(j, 'category', '') ?? '',
        basePrice: _num(j, 'base_price'),
        inStock: _g<bool>(j, 'in_stock', false) ?? false,
        reason: _g<String>(j, 'reason', '') ?? '',
        score: _num(j, 'score'),
      );
}

class Recommendation {
  final String source;
  final List<RecommendedItem> items;

  Recommendation({this.source = '', this.items = const []});

  factory Recommendation.fromJson(Map<String, dynamic> j) {
    var items = <RecommendedItem>[];
    final raw = j['items'];
    if (raw is List) {
      items = raw
          .whereType<Map<String, dynamic>>()
          .map(RecommendedItem.fromJson)
          .toList();
    }
    return Recommendation(
      source: _g<String>(j, 'source', '') ?? '',
      items: items,
    );
  }
}

class ChatMessage {
  final String role;
  final String content;
  final String? createdAt;

  ChatMessage({required this.role, required this.content, this.createdAt});

  factory ChatMessage.fromJson(Map<String, dynamic> j) => ChatMessage(
        role: _g<String>(j, 'role', '') ?? '',
        content: _g<String>(j, 'content', '') ?? '',
        createdAt: _g<String>(j, 'created_at'),
      );
}

class ChatConversation {
  final int id;
  final String? createdAt;
  final List<ChatMessage> messages;

  ChatConversation({required this.id, this.createdAt, this.messages = const []});

  factory ChatConversation.fromJson(Map<String, dynamic> j) {
    var messages = <ChatMessage>[];
    final raw = j['messages'];
    if (raw is List) {
      messages = raw
          .whereType<Map<String, dynamic>>()
          .map(ChatMessage.fromJson)
          .toList();
    }
    return ChatConversation(
      id: _g<int>(j, 'id', 0) ?? 0,
      createdAt: _g<String>(j, 'created_at'),
      messages: messages,
    );
  }
}

class ChatReply {
  final int conversationId;
  final String reply;
  final List<String> suggestions;

  ChatReply({required this.conversationId, this.reply = '', this.suggestions = const []});

  factory ChatReply.fromJson(Map<String, dynamic> j) => ChatReply(
        conversationId: _g<int>(j, 'conversation_id', 0) ?? 0,
        reply: _g<String>(j, 'reply', '') ?? '',
        suggestions: _listStrings(j, 'suggestions'),
      );
}

class ReportKpis {
  final double totalSales;
  final int totalOrders;
  final double avgOrder;
  final int reservations;
  final int totalUnitsAvailable;
  final int lowStockVariants;
  final int activePromotions;
  final double discountAmount;

  const ReportKpis({
    this.totalSales = 0,
    this.totalOrders = 0,
    this.avgOrder = 0,
    this.reservations = 0,
    this.totalUnitsAvailable = 0,
    this.lowStockVariants = 0,
    this.activePromotions = 0,
    this.discountAmount = 0,
  });

  factory ReportKpis.fromJson(Map<String, dynamic> j) => ReportKpis(
        totalSales: _num(j, 'total_sales'),
        totalOrders: _g<int>(j, 'total_orders') ?? 0,
        avgOrder: _num(j, 'avg_order'),
        reservations: _g<int>(j, 'reservations') ?? 0,
        totalUnitsAvailable: _g<int>(j, 'total_units_available') ?? 0,
        lowStockVariants: _g<int>(j, 'low_stock_variants') ?? 0,
        activePromotions: _g<int>(j, 'active_promotions') ?? 0,
        discountAmount: _num(j, 'discount_amount'),
      );
}

class SalesPoint {
  final String date;
  final double amount;
  final int orders;

  SalesPoint({this.date = '', this.amount = 0, this.orders = 0});

  factory SalesPoint.fromJson(Map<String, dynamic> j) => SalesPoint(
        date: _g<String>(j, 'date', '') ?? '',
        amount: _num(j, 'amount'),
        orders: _g<int>(j, 'orders', 0) ?? 0,
      );
}

class CategoryReport {
  final int? categoryId;
  final String categoryName;
  final double sales;
  final int units;

  CategoryReport({this.categoryId, this.categoryName = '', this.sales = 0, this.units = 0});

  factory CategoryReport.fromJson(Map<String, dynamic> j) => CategoryReport(
        categoryId: _g<int>(j, 'category_id'),
        categoryName: _g<String>(j, 'category_name', '') ?? '',
        sales: _num(j, 'sales'),
        units: _g<int>(j, 'units', 0) ?? 0,
      );
}

class TopProductReport {
  final int productId;
  final String name;
  final int units;
  final double revenue;

  TopProductReport({required this.productId, this.name = '', this.units = 0, this.revenue = 0});

  factory TopProductReport.fromJson(Map<String, dynamic> j) => TopProductReport(
        productId: _g<int>(j, 'product_id', 0) ?? 0,
        name: _g<String>(j, 'name', '') ?? '',
        units: _g<int>(j, 'units', 0) ?? 0,
        revenue: _num(j, 'revenue'),
      );
}

class DashboardReport {
  final bool empty;
  final String dateFrom;
  final String dateTo;
  final ReportKpis kpis;
  final List<SalesPoint> salesSeries;
  final List<CategoryReport> byCategory;
  final List<TopProductReport> topProducts;
  final String? narrative;

  DashboardReport({
    this.empty = false,
    this.dateFrom = '',
    this.dateTo = '',
    this.kpis = const ReportKpis(),
    this.salesSeries = const [],
    this.byCategory = const [],
    this.topProducts = const [],
    this.narrative,
  });

  factory DashboardReport.fromJson(Map<String, dynamic> j) {
    List<SalesPoint> sales = [];
    List<CategoryReport> cats = [];
    List<TopProductReport> tops = [];
    final rawSales = j['sales_series'];
    if (rawSales is List) {
      sales = rawSales
          .whereType<Map<String, dynamic>>()
          .map(SalesPoint.fromJson)
          .toList();
    }
    final rawCats = j['by_category'];
    if (rawCats is List) {
      cats = rawCats
          .whereType<Map<String, dynamic>>()
          .map(CategoryReport.fromJson)
          .toList();
    }
    final rawTops = j['top_products'];
    if (rawTops is List) {
      tops = rawTops
          .whereType<Map<String, dynamic>>()
          .map(TopProductReport.fromJson)
          .toList();
    }
    return DashboardReport(
      empty: _g<bool>(j, 'empty', false) ?? false,
      dateFrom: _g<String>(j, 'date_from', '') ?? '',
      dateTo: _g<String>(j, 'date_to', '') ?? '',
      kpis: j['kpis'] is Map
          ? ReportKpis.fromJson(j['kpis'] as Map<String, dynamic>)
          : const ReportKpis(),
      salesSeries: sales,
      byCategory: cats,
      topProducts: tops,
      narrative: _g<String>(j, 'narrative'),
    );
  }
}

class VoiceIntent {
  final bool recognized;
  final String? reportType;
  final String? dateFrom;
  final String? dateTo;
  final int? branchId;
  final int? categoryId;

  const VoiceIntent({
    this.recognized = false,
    this.reportType,
    this.dateFrom,
    this.dateTo,
    this.branchId,
    this.categoryId,
  });

  factory VoiceIntent.fromJson(Map<String, dynamic> j) => VoiceIntent(
        recognized: _g<bool>(j, 'recognized', false) ?? false,
        reportType: _g<String>(j, 'report_type'),
        dateFrom: _g<String>(j, 'date_from'),
        dateTo: _g<String>(j, 'date_to'),
        branchId: _g<int>(j, 'branch_id'),
        categoryId: _g<int>(j, 'category_id'),
      );
}

class VoiceReport {
  final bool recognized;
  final String message;
  final VoiceIntent intent;
  final DashboardReport? data;

  VoiceReport({
    this.recognized = false,
    this.message = '',
    this.intent = const VoiceIntent(),
    this.data,
  });

  factory VoiceReport.fromJson(Map<String, dynamic> j) => VoiceReport(
        recognized: _g<bool>(j, 'recognized', false) ?? false,
        message: _g<String>(j, 'message', '') ?? '',
        intent: j['intent'] is Map
            ? VoiceIntent.fromJson(j['intent'] as Map<String, dynamic>)
            : const VoiceIntent(),
        data: j['data'] is Map
            ? DashboardReport.fromJson(j['data'] as Map<String, dynamic>)
            : null,
      );
}

class Promotion {
  final int id;
  final String name;
  final String? description;
  final String discountType;
  final double value;
  final String targetType;
  final int? targetId;
  final String? startDate;
  final String? endDate;
  final bool isActive;

  Promotion({
    required this.id,
    this.name = '',
    this.description,
    this.discountType = 'PERCENTAGE',
    this.value = 0,
    this.targetType = 'GLOBAL',
    this.targetId,
    this.startDate,
    this.endDate,
    this.isActive = true,
  });

  factory Promotion.fromJson(Map<String, dynamic> j) => Promotion(
        id: _g<int>(j, 'id', 0) ?? 0,
        name: _g<String>(j, 'name', '') ?? '',
        description: _g<String>(j, 'description'),
        discountType: _g<String>(j, 'discount_type', 'PERCENTAGE') ?? 'PERCENTAGE',
        value: _num(j, 'value'),
        targetType: _g<String>(j, 'target_type', 'GLOBAL') ?? 'GLOBAL',
        targetId: _g<int>(j, 'target_id'),
        startDate: _g<String>(j, 'start_date'),
        endDate: _g<String>(j, 'end_date'),
        isActive: _g<bool>(j, 'is_active', true) ?? true,
      );
}

class Proposal {
  final int id;
  final int providerId;
  final String? providerName;
  final String name;
  final String? description;
  final double basePrice;
  final String status;
  final String? adminComment;
  final String? createdAt;
  final String? processedAt;

  Proposal({
    required this.id,
    required this.providerId,
    this.providerName,
    this.name = '',
    this.description,
    this.basePrice = 0,
    this.status = 'PENDIENTE',
    this.adminComment,
    this.createdAt,
    this.processedAt,
  });

  factory Proposal.fromJson(Map<String, dynamic> j) => Proposal(
        id: _g<int>(j, 'id', 0) ?? 0,
        providerId: _g<int>(j, 'provider_id', 0) ?? 0,
        providerName: _g<String>(j, 'provider_name'),
        name: _g<String>(j, 'name', '') ?? '',
        description: _g<String>(j, 'description'),
        basePrice: _num(j, 'base_price'),
        status: _g<String>(j, 'status', 'PENDIENTE') ?? 'PENDIENTE',
        adminComment: _g<String>(j, 'admin_comment'),
        createdAt: _g<String>(j, 'created_at'),
        processedAt: _g<String>(j, 'processed_at'),
      );
}

class ProviderInfo {
  final int id;
  final String name;
  final String? contactEmail;
  final String? nit;
  final String? phone;
  final String? address;
  final bool isActive;

  ProviderInfo({
    required this.id,
    this.name = '',
    this.contactEmail,
    this.nit,
    this.phone,
    this.address,
    this.isActive = true,
  });

  factory ProviderInfo.fromJson(Map<String, dynamic> j) => ProviderInfo(
        id: _g<int>(j, 'id', 0) ?? 0,
        name: _g<String>(j, 'name', '') ?? '',
        contactEmail: _g<String>(j, 'contact_email'),
        nit: _g<String>(j, 'nit'),
        phone: _g<String>(j, 'phone'),
        address: _g<String>(j, 'address'),
        isActive: _g<bool>(j, 'is_active', true) ?? true,
      );
}

class ProviderMe {
  final User user;
  final String role;
  final ProviderInfo? provider;

  ProviderMe({required this.user, this.role = '', this.provider});

  factory ProviderMe.fromJson(Map<String, dynamic> j) => ProviderMe(
        user: j['user'] is Map ? User.fromJson(j['user'] as Map<String, dynamic>) : User(id: 0, firstName: '', lastName: '', email: '', roleName: '', isActive: true),
        role: _g<String>(j, 'role', '') ?? '',
        provider: j['provider'] is Map
            ? ProviderInfo.fromJson(j['provider'] as Map<String, dynamic>)
            : null,
      );
}

class AppNotification {
  final int id;
  final int userId;
  final String title;
  final String? message;
  final bool isRead;
  final String? createdAt;

  AppNotification({
    required this.id,
    required this.userId,
    this.title = '',
    this.message,
    this.isRead = false,
    this.createdAt,
  });

  factory AppNotification.fromJson(Map<String, dynamic> j) => AppNotification(
        id: _g<int>(j, 'id', 0) ?? 0,
        userId: _g<int>(j, 'user_id', 0) ?? 0,
        title: _g<String>(j, 'title', '') ?? '',
        message: _g<String>(j, 'message'),
        isRead: _g<bool>(j, 'is_read', false) ?? false,
        createdAt: _g<String>(j, 'created_at'),
      );
}

class AuthResult {
  final String accessToken;
  final String role;
  final String email;
  final int userId;

  AuthResult({
    required this.accessToken,
    required this.role,
    required this.email,
    required this.userId,
  });

  factory AuthResult.fromJson(Map<String, dynamic> j) => AuthResult(
        accessToken: _g<String>(j, 'access_token', '') ?? '',
        role: _g<String>(j, 'role', '') ?? '',
        email: _g<String>(j, 'email', '') ?? '',
        userId: _g<int>(j, 'user_id', 0) ?? 0,
      );
}

String money(double value) {
  try {
    return NumberFormat.currency(locale: 'es_BO', symbol: 'Bs').format(value);
  } catch (_) {
    return 'Bs ${value.toStringAsFixed(2)}';
  }
}

String fmtDate(String? iso) {
  if (iso == null || iso.isEmpty) return '—';
  final dt = DateTime.tryParse(iso.replaceFirst('Z', ''));
  if (dt == null) return iso;
  return DateFormat('dd/MM/yyyy HH:mm').format(dt.toLocal());
}