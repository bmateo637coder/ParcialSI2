import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'models.dart';

const _kToken = 'fs_token';
const _kRole = 'fs_role';
const _kEmail = 'fs_email';
const _kUser = 'fs_user';

class ApiError implements Exception {
  final int status;
  final String message;

  ApiError(this.status, this.message);

  @override
  String toString() => message;
}

String defaultBaseUrl() {
  const defined = String.fromEnvironment('API_URL');
  if (defined.isNotEmpty) return defined;
  if (!kIsWeb) {
    // Android emulator reaches the host through 10.0.2.2.
    return 'http://10.0.2.2:8001/api';
  }
  return 'http://127.0.0.1:8001/api';
}

class ApiClient {
  final String baseUrl;
  final http.Client _client;

  ApiClient({http.Client? client, String? baseUrl})
      : baseUrl = baseUrl ?? defaultBaseUrl(),
        _client = client ?? http.Client();

  String? _token;
  User? currentUser;

  bool get isAuthenticated => _token != null;

  bool isRole(String role) => currentUser?.roleName == role;

  bool get isAdmin => isRole('Administrador');
  bool get isStaff =>
      const {'Administrador', 'Encargado de Sucursal', 'Cajero'}
          .contains(currentUser?.roleName);
  bool get isProvider => isRole('Proveedor');

  Future<void> restoreSession() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString(_kToken);
    final rawUser = prefs.getString(_kUser);
    if (rawUser != null && rawUser.isNotEmpty) {
      try {
        currentUser =
            User.fromJson(jsonDecode(rawUser) as Map<String, dynamic>);
      } catch (_) {
        currentUser = null;
      }
    }
    if (_token != null && currentUser != null) {
      try {
        currentUser = await getProfile();
      } catch (_) {
        await logout();
      }
    }
  }

  Future<void> saveSession(
      String token, String role, String email, User user) async {
    _token = token;
    currentUser = user;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kToken, token);
    await prefs.setString(_kRole, role);
    await prefs.setString(_kEmail, email);
    await prefs.setString(_kUser, jsonEncode(user.toJson()));
  }

  Future<void> logout() async {
    _token = null;
    currentUser = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kToken);
    await prefs.remove(_kRole);
    await prefs.remove(_kEmail);
    await prefs.remove(_kUser);
  }

  Map<String, String> _headers({bool json = true}) => {
        if (json) 'Content-Type': 'application/json',
        if (_token != null) 'Authorization': 'Bearer $_token',
      };

  dynamic _decode(http.Response res) {
    if (res.body.isEmpty) return null;
    return jsonDecode(utf8.decode(res.bodyBytes));
  }

  Future<dynamic> request(String method, String path,
      {Object? body, bool auth = true}) async {
    final uri = Uri.parse('$baseUrl$path');
    final headers = _headers();
    if (!auth) headers.remove('Authorization');

    http.Response res;
    try {
      final req = http.Request(method, uri)..headers.addAll(headers);
      if (body != null) req.body = jsonEncode(body);
      final streamed = await _client.send(req).timeout(const Duration(seconds: 25));
      res = await http.Response.fromStream(streamed);
    } on Exception catch (e) {
      throw ApiError(0, 'No se pudo conectar con el servidor ($e). Revisa tu conexión.');
    }

    dynamic data;
    try {
      data = _decode(res);
    } catch (_) {
      data = null;
    }

    if (res.statusCode >= 200 && res.statusCode < 300) {
      return data;
    }

    final message = _extractError(data, res.statusCode);
    if (res.statusCode == 401 && !path.contains('/auth/login') && auth) {
      await logout();
      throw ApiError(401, 'Tu sesión expiró. Vuelve a iniciar sesión.');
    }
    throw ApiError(res.statusCode, message);
  }

  String _extractError(dynamic data, int status) {
    String detail = '';
    if (data is Map) {
      var d = data['detail'];
      if (d is String) {
        detail = d;
      } else if (d is List && d.isNotEmpty) {
        detail = (d.first is Map && (d.first as Map)['msg'] != null)
            ? (d.first as Map)['msg'].toString()
            : d.first.toString();
      } else if (data['message'] is String) {
        detail = data['message'] as String;
      }
    }
    if (detail.isNotEmpty) return detail;
    if (status == 0) return 'No se pudo conectar con el servidor.';
    return 'Error del servidor ($status).';
  }

  // ------------------------------------------------------------------
  // Autenticación (CU1, CU2)
  // ------------------------------------------------------------------
  Future<User> login(String email, String password) async {
    final data = await request('POST', '/auth/login',
        body: {'email': email, 'password': password}, auth: false);
    final result = AuthResult.fromJson(data as Map<String, dynamic>);
    final user = await getProfile();
    await saveSession(result.accessToken, result.role, result.email, user);
    return user;
  }

  Future<User> register({
    required String firstName,
    required String lastName,
    required String email,
    required String password,
  }) async {
    final data = await request('POST', '/auth/register', auth: false, body: {
      'first_name': firstName,
      'last_name': lastName,
      'email': email,
      'password': password,
    });
    return User.fromJson(data as Map<String, dynamic>);
  }

  Future<User> getProfile() async {
    final data = await request('GET', '/auth/me');
    currentUser = User.fromJson(data as Map<String, dynamic>);
    return currentUser!;
  }

  Future<User> updateProfile(
      {String? firstName, String? lastName, String? email, String? phone}) async {
    final data = await request('PATCH', '/auth/me', body: {
      if (firstName != null) 'first_name': firstName,
      if (lastName != null) 'last_name': lastName,
      if (email != null) 'email': email,
      if (phone != null) 'phone': phone,
    });
    currentUser = User.fromJson(data as Map<String, dynamic>);
    return currentUser!;
  }

  Future<void> forgotPassword(String email) async {
    await request('POST', '/auth/forgot-password',
        body: {'email': email}, auth: false);
  }

  Future<void> resetPassword(String token, String newPassword) async {
    await request('POST', '/auth/reset-password', auth: false,
        body: {'token': token, 'new_password': newPassword});
  }

  // ------------------------------------------------------------------
  // Sucursales (CU6)
  // ------------------------------------------------------------------
  Future<List<Branch>> getBranches({String city = ''}) async {
    final path = city.trim().isEmpty ? '/branches/' : '/branches/?city=${Uri.encodeQueryComponent(city.trim())}';
    final data = await request('GET', path, auth: false);
    return (data as List).map((e) => Branch.fromJson(e)).toList();
  }

  // ------------------------------------------------------------------
  // Catálogo (CU10)
  // ------------------------------------------------------------------
  Future<List<Product>> getProducts(
      {String q = '', int? categoryId, int? seasonId}) async {
    final params = <String>[];
    if (q.trim().isNotEmpty) params.add('q=${Uri.encodeQueryComponent(q.trim())}');
    if (categoryId != null) params.add('category_id=$categoryId');
    if (seasonId != null) params.add('season_id=$seasonId');
    final qs = params.isEmpty ? '' : '?${params.join('&')}';
    final data = await request('GET', '/products/$qs', auth: false);
    return (data as List).map((e) => Product.fromJson(e)).toList();
  }

  Future<Product> getProduct(int id) async {
    final data = await request('GET', '/products/$id', auth: false);
    return Product.fromJson(data as Map<String, dynamic>);
  }

  Future<List<ProductVariant>> getVariants(int productId) async {
    final data = await request('GET', '/products/$productId/variants', auth: false);
    return (data as List).map((e) => ProductVariant.fromJson(e)).toList();
  }

  Future<List<CategoryItem>> getCategories() async {
    final data = await request('GET', '/products/metadata/categories', auth: false);
    return (data as List).map((e) => CategoryItem.fromJson(e)).toList();
  }

  Future<List<IdName>> getSeasons() async {
    final data = await request('GET', '/products/metadata/seasons', auth: false);
    return (data as List).map((e) => IdName.fromJson(e)).toList();
  }

  Future<List<IdName>> getSizes() async {
    final data = await request('GET', '/products/metadata/sizes', auth: false);
    return (data as List).map((e) => IdName.fromJson(e)).toList();
  }

  Future<List<IdName>> getColors() async {
    final data = await request('GET', '/products/metadata/colors', auth: false);
    return (data as List).map((e) => IdName.fromJson(e)).toList();
  }

  // ------------------------------------------------------------------
  // Disponibilidad (CU11)
  // ------------------------------------------------------------------
  Future<List<AvailabilityItem>> getAvailability(
      {int? productId, int? branchId, String q = ''}) async {
    final params = <String>[];
    if (productId != null) params.add('product_id=$productId');
    if (branchId != null) params.add('branch_id=$branchId');
    if (q.trim().isNotEmpty) params.add('q=${Uri.encodeQueryComponent(q.trim())}');
    final qs = params.isEmpty ? '' : '?${params.join('&')}';
    final data = await request('GET', '/inventory/availability$qs', auth: false);
    return (data as List).map((e) => AvailabilityItem.fromJson(e)).toList();
  }

  // ------------------------------------------------------------------
  // Carrito (CU16)
  // ------------------------------------------------------------------
  Future<CartSummary> getCart() async {
    final data = await request('GET', '/cart');
    return CartSummary.fromJson(data as Map<String, dynamic>);
  }

  Future<CartSummary> addToCart(int variantId, {int quantity = 1}) async {
    final data = await request('POST', '/cart',
        body: {'variant_id': variantId, 'quantity': quantity});
    return CartSummary.fromJson(data as Map<String, dynamic>);
  }

  Future<CartSummary> updateCartItem(int itemId, int quantity) async {
    final data = await request('PATCH', '/cart/$itemId', body: {'quantity': quantity});
    return CartSummary.fromJson(data as Map<String, dynamic>);
  }

  Future<CartSummary> removeCartItem(int itemId) async {
    final data = await request('DELETE', '/cart/$itemId');
    return CartSummary.fromJson(data as Map<String, dynamic>);
  }

  Future<CartSummary> clearCart() async {
    final data = await request('DELETE', '/cart');
    return CartSummary.fromJson(data as Map<String, dynamic>);
  }

  // ------------------------------------------------------------------
  // Reservas (CU13, CU14, CU15)
  // ------------------------------------------------------------------
  Future<Reservation> createReservation({
    required int branchId,
    required List<Map<String, int>> items,
    int expirationHours = 24,
  }) async {
    final data = await request('POST', '/reservations', body: {
      'branch_id': branchId,
      'items': items,
      'expiration_hours': expirationHours,
    });
    return Reservation.fromJson(data as Map<String, dynamic>);
  }

  Future<List<Reservation>> getReservations(
      {String statusFilter = '', bool allReservations = false}) async {
    final params = <String>[];
    if (statusFilter.isNotEmpty) {
      params.add('status_filter=${Uri.encodeQueryComponent(statusFilter)}');
    }
    if (allReservations) params.add('all_reservations=true');
    final qs = params.isEmpty ? '' : '?${params.join('&')}';
    final data = await request('GET', '/reservations$qs');
    return (data as List).map((e) => Reservation.fromJson(e)).toList();
  }

  Future<Reservation> cancelReservation(int id) async {
    final data = await request('PATCH', '/reservations/$id/cancel');
    return Reservation.fromJson(data as Map<String, dynamic>);
  }

  Future<Reservation> attendReservation(int id) async {
    final data = await request('PATCH', '/reservations/$id/attend');
    return Reservation.fromJson(data as Map<String, dynamic>);
  }

  Future<Reservation> expireReservation(int id) async {
    final data = await request('POST', '/reservations/$id/expire');
    return Reservation.fromJson(data as Map<String, dynamic>);
  }

  Future<Reservation> deleteReservation(int id) async {
    final data = await request('DELETE', '/reservations/$id');
    return Reservation.fromJson(data as Map<String, dynamic>);
  }

  Future<int> expireStaleReservations() async {
    final data = await request('POST', '/reservations/expire-stale');
    return (data as Map)['expired'] as int? ?? 0;
  }

  // ------------------------------------------------------------------
  // Pedidos y pagos (CU17, CU18, CU19, CU26)
  // ------------------------------------------------------------------
  Future<Order> checkout({
    String orderType = 'DIGITAL',
    int? branchId,
    List<Map<String, int>>? items,
    required String paymentMethod,
    String? cardNumber,
    String? shippingAddress,
  }) async {
    final data = await request('POST', '/orders/checkout', body: {
      'order_type': orderType,
      if (branchId != null) 'branch_id': branchId,
      if (items != null) 'items': items,
      'payment_method': paymentMethod,
      if (cardNumber != null && cardNumber.isNotEmpty) 'card_number': cardNumber,
      if (shippingAddress != null && shippingAddress.isNotEmpty)
        'shipping_address': shippingAddress,
    });
    return Order.fromJson(data as Map<String, dynamic>);
  }

  Future<Order> posSale({
    required int branchId,
    required List<Map<String, int>> items,
    String? clientId,
    required String paymentMethod,
    String? cardNumber,
  }) async {
    final data = await request('POST', '/pos/sale', body: {
      'branch_id': branchId,
      'items': items,
      if (clientId != null && clientId.isNotEmpty) 'client_id': int.parse(clientId),
      'payment_method': paymentMethod,
      if (cardNumber != null && cardNumber.isNotEmpty) 'card_number': cardNumber,
    });
    return Order.fromJson(data as Map<String, dynamic>);
  }

  Future<Order> payOrder(int orderId, String paymentMethod, {String? cardNumber}) async {
    final data = await request('POST', '/orders/$orderId/pay', body: {
      'payment_method': paymentMethod,
      if (cardNumber != null && cardNumber.isNotEmpty) 'card_number': cardNumber,
    });
    return Order.fromJson(data as Map<String, dynamic>);
  }

  Future<List<Order>> getOrders() async {
    final data = await request('GET', '/orders');
    return (data as List).map((e) => Order.fromJson(e)).toList();
  }

  Future<Order> updateOrderStatus(int orderId, String status) async {
    final data = await request('PATCH', '/orders/$orderId/status', body: {'status': status});
    return Order.fromJson(data as Map<String, dynamic>);
  }

  // ------------------------------------------------------------------
  // IA: recomendaciones (CU22)
  // ------------------------------------------------------------------
  Future<Recommendation> getRecommendations({int limit = 8}) async {
    final data = await request('GET', '/recommendations?limit=$limit');
    return Recommendation.fromJson(data as Map<String, dynamic>);
  }

  // ------------------------------------------------------------------
  // IA: asistente (CU23)
  // ------------------------------------------------------------------
  Future<ChatReply> sendChat(String message, {int? conversationId}) async {
    final data = await request('POST', '/assistant/chat',
        body: {'message': message, 'conversation_id': conversationId});
    return ChatReply.fromJson(data as Map<String, dynamic>);
  }

  Future<List<ChatConversation>> getConversations() async {
    final data = await request('GET', '/assistant/conversations');
    return (data as List).map((e) => ChatConversation.fromJson(e)).toList();
  }

  Future<ChatConversation> getConversation(int id) async {
    final data = await request('GET', '/assistant/conversations/$id');
    return ChatConversation.fromJson(data as Map<String, dynamic>);
  }

  // ------------------------------------------------------------------
  // Reportes (CU24, CU25)
  // ------------------------------------------------------------------
  Future<DashboardReport> getDashboard(
      {String? desde, String? hasta, int? branchId, int? categoryId}) async {
    final params = <String>[];
    if (desde != null) params.add('desde=${Uri.encodeQueryComponent(desde)}');
    if (hasta != null) params.add('hasta=${Uri.encodeQueryComponent(hasta)}');
    if (branchId != null) params.add('branch_id=$branchId');
    if (categoryId != null) params.add('category_id=$categoryId');
    final qs = params.isEmpty ? '' : '?${params.join('&')}';
    final data = await request('GET', '/reports/dashboard$qs');
    return DashboardReport.fromJson(data as Map<String, dynamic>);
  }

  Future<VoiceReport> voiceReport(String command) async {
    final data = await request('POST', '/reports/voice', body: {'command': command});
    return VoiceReport.fromJson(data as Map<String, dynamic>);
  }

  // ------------------------------------------------------------------
  // Promociones (CU27)
  // ------------------------------------------------------------------
  Future<List<Promotion>> getPromotions({bool includeInactive = true}) async {
    final q = includeInactive ? '?include_inactive=true' : '';
    final data = await request('GET', '/promotions/$q');
    return (data as List).map((e) => Promotion.fromJson(e)).toList();
  }

  Future<Promotion> createPromotion(Map<String, dynamic> input) async {
    final data = await request('POST', '/promotions/', body: input);
    return Promotion.fromJson(data as Map<String, dynamic>);
  }

  Future<Promotion> updatePromotion(int id, Map<String, dynamic> input) async {
    final data = await request('PATCH', '/promotions/$id', body: input);
    return Promotion.fromJson(data as Map<String, dynamic>);
  }

  Future<Promotion> deactivatePromotion(int id) async {
    final data = await request('DELETE', '/promotions/$id');
    return Promotion.fromJson(data as Map<String, dynamic>);
  }

  Future<Promotion> activatePromotion(int id) async {
    final data =
        await request('PATCH', '/promotions/$id', body: {'is_active': true});
    return Promotion.fromJson(data as Map<String, dynamic>);
  }

  // ------------------------------------------------------------------
  // Portal proveedor
  // ------------------------------------------------------------------
  Future<ProviderMe> getProviderMe() async {
    final data = await request('GET', '/providers/me');
    return ProviderMe.fromJson(data as Map<String, dynamic>);
  }

  Future<List<Product>> getProviderProducts() async {
    final data = await request('GET', '/providers/products');
    return (data as List).map((e) => Product.fromJson(e)).toList();
  }

  Future<Product> updateProviderProduct(int id, bool isActive) async {
    final data = await request('PATCH', '/providers/products/$id',
        body: {'is_active': isActive});
    return Product.fromJson(data as Map<String, dynamic>);
  }

  Future<Proposal> proposeProduct(
      String name, double basePrice, {String? description}) async {
    final data = await request('POST', '/providers/products', body: {
      'name': name,
      'base_price': basePrice,
      if (description != null) 'description': description,
    });
    return Proposal.fromJson(data as Map<String, dynamic>);
  }

  Future<List<Proposal>> getProposals() async {
    final data = await request('GET', '/providers/proposals');
    return (data as List).map((e) => Proposal.fromJson(e)).toList();
  }

  Future<Proposal> approveProposal(int id, {String? comment}) async {
    final data = await request('PATCH', '/providers/proposals/$id/approve',
        body: {'admin_comment': comment ?? null});
    return Proposal.fromJson(data as Map<String, dynamic>);
  }

  Future<Proposal> rejectProposal(int id, {String? comment}) async {
    final data = await request('PATCH', '/providers/proposals/$id/reject',
        body: {'admin_comment': comment ?? null});
    return Proposal.fromJson(data as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> linkProvider(
      int userId, int providerId) async {
    final data = await request('POST', '/providers/accounts',
        body: {'user_id': userId, 'provider_id': providerId});
    return (data as Map).cast<String, dynamic>();
  }

  // ------------------------------------------------------------------
  // Notificaciones
  // ------------------------------------------------------------------
  Future<List<AppNotification>> getNotifications() async {
    final data = await request('GET', '/notifications');
    return (data as List).map((e) => AppNotification.fromJson(e)).toList();
  }

  Future<AppNotification> markNotificationRead(int id) async {
    final data = await request('PATCH', '/notifications/$id/read');
    return AppNotification.fromJson(data as Map<String, dynamic>);
  }

  // ------------------------------------------------------------------
  // Inventario y movimientos (CU21)
  // ------------------------------------------------------------------
  Future<List<dynamic>> getInventory(
      {int? branchId, int? productId, bool lowStockOnly = false}) async {
    final params = <String>[];
    if (branchId != null) params.add('branch_id=$branchId');
    if (productId != null) params.add('product_id=$productId');
    if (lowStockOnly) params.add('low_stock_only=true');
    final qs = params.isEmpty ? '' : '?${params.join('&')}';
    return (await request('GET', '/inventory/$qs')) as List;
  }

  Future<List<dynamic>> getInventoryMovements(
      {int? inventoryId, String? movementType}) async {
    final params = <String>[];
    if (inventoryId != null) params.add('inventory_id=$inventoryId');
    if (movementType != null) params.add('movement_type=${Uri.encodeQueryComponent(movementType)}');
    final qs = params.isEmpty ? '' : '?${params.join('&')}';
    return (await request('GET', '/inventory/movements$qs')) as List;
  }

  Future<dynamic> createInventoryMovement(
      int inventoryId, String movementType, int quantity,
      {String? reason}) async {
    return request('POST', '/inventory/movements', body: {
      'inventory_id': inventoryId,
      'movement_type': movementType,
      'quantity': quantity,
      if (reason != null) 'reason': reason,
    });
  }
}