import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { BehaviorSubject, Observable, throwError } from 'rxjs';
import { catchError, tap, timeout } from 'rxjs/operators';
import { environment } from '../environments/environment';
import { ToastService } from './toast.service';

export interface User {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  role_name: string;
  is_active: boolean;
  phone?: string | null;
  created_at?: string;
  full_name?: string;
}

export interface Branch {
  id: number;
  name: string;
  city: string;
  address?: string;
  phone?: string;
  is_active?: boolean;
}

export interface Product {
  id: number;
  name: string;
  description?: string;
  base_price: number;
  image_url?: string;
  category?: { id: number; name: string } | null;
  season?: { id: number; name: string } | null;
  provider?: { id: number; name: string } | null;
  provider_id?: number | null;
  is_active?: boolean;
  created_at?: string;
}

export interface ProductVariant {
  id: number;
  product_id: number;
  size_id: number;
  color_id: number;
  size_name?: string;
  color_name?: string;
  sku: string;
  stock: number;
  price?: number | null;
  effective_price?: number;
}

export interface MetadataItem {
  id: number;
  name: string;
}

export interface CategoryItem extends MetadataItem {
  products_count?: number;
}

export interface ProductInput {
  name: string;
  description?: string | null;
  base_price: number;
  image_url?: string | null;
  category_id?: number | null;
  season_id?: number | null;
  provider_id?: number | null;
}

// ------------------------------------------------------------------
// Ciclo 2 — Venta y operaciones (CU11, CU13-16)
// ------------------------------------------------------------------

export interface AvailabilityItem {
  variant_id: number;
  product_id: number;
  product_name: string;
  image_url?: string | null;
  size_name?: string | null;
  color_name?: string | null;
  sku?: string | null;
  branch_id?: number | null;
  branch_name?: string | null;
  city?: string | null;
  available: number;
  price?: number | null;
}

export interface CartItem {
  id: number;
  variant_id: number;
  quantity: number;
  product_id?: number | null;
  product_name?: string | null;
  image_url?: string | null;
  size_name?: string | null;
  color_name?: string | null;
  sku?: string | null;
  unit_price: number;
  discount?: number | null;
  subtotal: number;
  added_at?: string | null;
}

export interface CartSummary {
  items: CartItem[];
  total_items: number;
  total_amount: number;
  total_discount?: number;
}

export interface ReservationItem {
  id: number;
  variant_id: number;
  quantity: number;
  unit_price: number;
  subtotal: number;
  product_id?: number | null;
  product_name?: string | null;
  image_url?: string | null;
  size_name?: string | null;
  color_name?: string | null;
  sku?: string | null;
}

export interface Reservation {
  id: number;
  code: string;
  client_id: number;
  client_name?: string | null;
  branch_id: number;
  branch_name?: string | null;
  status: string;
  reservation_date?: string | null;
  expiration_date?: string | null;
  attend_date?: string | null;
  items: ReservationItem[];
  total: number;
  item_count: number;
}

export interface ReservationInput {
  branch_id: number;
  items: { variant_id: number; quantity: number }[];
  expiration_hours?: number;
}

export interface OrderItem {
  id: number;
  variant_id: number;
  quantity: number;
  unit_price: number;
  discount?: number | null;
  subtotal: number;
  product_id?: number | null;
  product_name?: string | null;
  image_url?: string | null;
  size_name?: string | null;
  color_name?: string | null;
  sku?: string | null;
}

export interface PaymentBrief {
  id: number;
  method: string;
  amount: number;
  status: string;
  stripe_payment_id?: string | null;
  created_at?: string | null;
  paid_at?: string | null;
}

export interface Order {
  id: number;
  client_id: number;
  client_name?: string | null;
  branch_id?: number | null;
  branch_name?: string | null;
  order_type: string;
  status: string;
  total: number;
  shipping_address?: string | null;
  receipt_number?: string | null;
  created_at?: string | null;
  items: OrderItem[];
  payment?: PaymentBrief | null;
}

export interface OrderInput {
  order_type?: 'DIGITAL' | 'PRESENCIAL';
  branch_id?: number | null;
  items?: { variant_id: number; quantity: number }[] | null;
  payment_method?: string;
  shipping_address?: string | null;
  card_number?: string | null;
}

export interface PosSaleInput {
  branch_id: number;
  items: { variant_id: number; quantity: number }[];
  client_id?: number | null;
  payment_method?: string;
  card_number?: string | null;
}

export interface PayInput {
  payment_method: string;
  card_number?: string | null;
}

export interface RecommendedItem {
  product_id: number;
  name: string;
  category: string;
  base_price: number;
  in_stock: boolean;
  reason: string;
  score: number;
}

export interface Recommendation {
  source: string;
  items: RecommendedItem[];
}

export interface ChatMessage {
  role: string;
  content: string;
  created_at?: string | null;
}

export interface ChatConversation {
  id: number;
  created_at?: string | null;
  messages: ChatMessage[];
}

export interface ChatReply {
  conversation_id: number;
  reply: string;
}

export interface NotificationItem {
  id: number;
  user_id: number;
  title: string;
  message?: string | null;
  is_read: boolean;
  created_at?: string | null;
}

// ------------------------------------------------------------------
// Ciclo 4 — Reportes y dashboards (CU24, CU25)
// ------------------------------------------------------------------

export interface ReportKpis {
  total_sales: number;
  total_orders: number;
  avg_order: number;
  reservations: number;
  total_units_available: number;
  low_stock_variants: number;
  active_promotions: number;
  discount_amount: number;
}

export interface SalesPoint {
  date: string;
  amount: number;
  orders: number;
}

export interface CategoryReport {
  category_id: number | null;
  category_name: string;
  sales: number;
  units: number;
}

export interface TopProductReport {
  product_id: number;
  name: string;
  units: number;
  revenue: number;
}

export interface DashboardReport {
  empty: boolean;
  date_from: string;
  date_to: string;
  kpis: ReportKpis;
  sales_series: SalesPoint[];
  by_category: CategoryReport[];
  top_products: TopProductReport[];
  narrative?: string | null;
}

export interface VoiceReportIntent {
  recognized: boolean;
  report_type?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  branch_id?: number | null;
  category_id?: number | null;
}

export interface VoiceReportResponse {
  recognized: boolean;
  message: string;
  intent: VoiceReportIntent;
  data?: DashboardReport | null;
}

// ------------------------------------------------------------------
// Ciclo 5 — Promociones (CU27) y Portal Proveedor
// ------------------------------------------------------------------

export interface Promotion {
  id: number;
  name: string;
  description?: string | null;
  discount_type: 'PERCENTAGE' | 'FIXED';
  value: number;
  target_type: 'GLOBAL' | 'CATEGORY' | 'PRODUCT';
  target_id?: number | null;
  start_date?: string | null;
  end_date?: string | null;
  is_active: boolean;
  created_at?: string | null;
}

export interface PromotionInput {
  name: string;
  description?: string | null;
  discount_type: 'PERCENTAGE' | 'FIXED';
  value: number;
  target_type: 'GLOBAL' | 'CATEGORY' | 'PRODUCT';
  target_id?: number | null;
  start_date?: string | null;
  end_date?: string | null;
}

export interface ProviderInfo {
  id: number;
  name: string;
  contact_email?: string | null;
  nit?: string | null;
  phone?: string | null;
  address?: string | null;
  is_active?: boolean;
}

export interface ProviderMe {
  user: User;
  role: string;
  provider: ProviderInfo | null;
}

export interface ProposalInput {
  name: string;
  description?: string | null;
  base_price: number;
}

export interface Proposal {
  id: number;
  provider_id: number;
  provider_name?: string | null;
  name: string;
  description?: string | null;
  base_price: number;
  status: 'PENDIENTE' | 'APROBADA' | 'RECHAZADA';
  admin_comment?: string | null;
  created_at?: string | null;
  processed_at?: string | null;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private baseUrl = environment.apiUrl;
  currentUser = new BehaviorSubject<User | null>(null);

  constructor(private http: HttpClient, private toast: ToastService) {
    const stored = localStorage.getItem('user');
    if (stored) {
      try {
        this.currentUser.next(JSON.parse(stored) as User);
      } catch {
        localStorage.removeItem('user');
      }
    }
    if (this.currentUser.value) {
      this.getProfile().subscribe({ error: () => this.logout() });
    }
  }

  get token(): string | null {
    return localStorage.getItem('token');
  }

  get isAuthenticated(): boolean {
    return !!this.currentUser.value;
  }

  get isAdmin(): boolean {
    return this.currentUser.value?.role_name === 'Administrador';
  }

  private headers(): Record<string, string> {
    const h: Record<string, string> = { 'Content-Type': 'application/json' };
    const t = this.token;
    if (t) {
      h['Authorization'] = `Bearer ${t}`;
    }
    return h;
  }

  private request<T>(method: string, url: string, body?: unknown): Observable<T> {
    return this.http
      .request<T>(method, `${this.baseUrl}${url}`, {
        body,
        headers: this.headers(),
      })
      .pipe(
        timeout(20000),
        catchError((err: unknown) => {
          if (err instanceof HttpErrorResponse) {
            if (err.status === 401 && !url.includes('/auth/login')) {
              this.logout();
              this.toast.error('Tu sesión expiró. Vuelve a iniciar sesión.');
            } else {
              this.toast.error(this.errorMessage(err));
            }
          } else {
            this.toast.error('El servidor tardó demasiado en responder. Reintenta.');
          }
          return throwError(() => err);
        })
      );
  }

  private errorMessage(err: HttpErrorResponse): string {
    const detail = err.error?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      return detail[0]?.msg || 'Datos inválidos. Revisa el formulario.';
    }
    if (err.error?.message) return err.error.message;
    if (err.status === 0) return 'No se pudo conectar con el servidor.';
    return `Error del servidor (${err.status}).`;
  }

  // ------------------------------------------------------------------
  // Autenticación
  // ------------------------------------------------------------------
  login(data: { email: string; password: string }): Observable<{
    access_token: string;
    token_type: string;
    role: string;
    email: string;
    user_id: number;
  }> {
    return this.request('POST', '/auth/login', data);
  }

  register(data: {
    first_name: string;
    last_name: string;
    email: string;
    password: string;
  }): Observable<User> {
    return this.request('POST', '/auth/register', data);
  }

  getProfile(): Observable<User> {
    return this.request<User>('GET', '/auth/me').pipe(
      tap((user) => this.setUser(user))
    );
  }

  updateProfile(data: { first_name?: string; last_name?: string }): Observable<User> {
    return this.request<User>('PATCH', '/auth/me', data).pipe(
      tap((user) => this.setUser(user))
    );
  }

  /** Guarda la sesión tras el login y refresca el perfil completo. */
  establishSession(data: { access_token: string; role: string; email: string }): Observable<User> {
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('role', data.role);
    localStorage.setItem('email', data.email);
    return this.getProfile();
  }

  logout(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('email');
    localStorage.removeItem('user');
    this.currentUser.next(null);
  }

  private setUser(user: User): void {
    localStorage.setItem('user', JSON.stringify(user));
    this.currentUser.next(user);
  }

  // ------------------------------------------------------------------
  // Sucursales
  // ------------------------------------------------------------------
  getBranches(city = ''): Observable<Branch[]> {
    const q = city.trim() ? `?city=${encodeURIComponent(city.trim())}` : '';
    return this.request<Branch[]>('GET', `/branches/${q}`);
  }

  getBranch(id: number): Observable<Branch> {
    return this.request<Branch>('GET', `/branches/${id}`);
  }

  createBranch(data: Partial<Branch>): Observable<Branch> {
    return this.request<Branch>('POST', '/branches/', data);
  }

  updateBranch(id: number, data: Partial<Branch>): Observable<Branch> {
    return this.request<Branch>('PATCH', `/branches/${id}`, data);
  }

  deleteBranch(id: number): Observable<void> {
    return this.request<void>('DELETE', `/branches/${id}`);
  }

  // ------------------------------------------------------------------
  // Productos
  // ------------------------------------------------------------------
  getProducts(q = '', categoryId?: number, seasonId?: number): Observable<Product[]> {
    const params: string[] = [];
    if (q.trim()) params.push(`q=${encodeURIComponent(q.trim())}`);
    if (categoryId) params.push(`category_id=${categoryId}`);
    if (seasonId) params.push(`season_id=${seasonId}`);
    const qs = params.length ? `?${params.join('&')}` : '';
    return this.request<Product[]>('GET', `/products/${qs}`);
  }

  getProduct(id: number): Observable<Product> {
    return this.request<Product>('GET', `/products/${id}`);
  }

  createProduct(data: ProductInput): Observable<Product> {
    return this.request<Product>('POST', '/products/', data);
  }

  updateProduct(id: number, data: Partial<ProductInput>): Observable<Product> {
    return this.request<Product>('PATCH', `/products/${id}`, data);
  }

  deleteProduct(id: number): Observable<void> {
    return this.request<void>('DELETE', `/products/${id}`);
  }

  // ------------------------------------------------------------------
  // Variantes
  // ------------------------------------------------------------------
  getVariants(productId: number): Observable<ProductVariant[]> {
    return this.request<ProductVariant[]>('GET', `/products/${productId}/variants`);
  }

  createVariant(productId: number, data: { size_id: number; color_id: number; sku: string; stock?: number; price?: number | null }): Observable<ProductVariant> {
    return this.request<ProductVariant>('POST', `/products/${productId}/variants`, data);
  }

  updateVariant(id: number, data: Partial<ProductVariant>): Observable<ProductVariant> {
    return this.request<ProductVariant>('PATCH', `/products/variants/${id}`, data);
  }

  deleteVariant(id: number): Observable<void> {
    return this.request<void>('DELETE', `/products/variants/${id}`);
  }

  // ------------------------------------------------------------------
  // Catálogo (referencias)
  // ------------------------------------------------------------------
  getCategories(): Observable<CategoryItem[]> {
    return this.request<CategoryItem[]>('GET', '/products/metadata/categories');
  }

  getSeasons(): Observable<MetadataItem[]> {
    return this.request<MetadataItem[]>('GET', '/products/metadata/seasons');
  }

  getSizes(): Observable<MetadataItem[]> {
    return this.request<MetadataItem[]>('GET', '/products/metadata/sizes');
  }

  getColors(): Observable<MetadataItem[]> {
    return this.request<MetadataItem[]>('GET', '/products/metadata/colors');
  }

  getProviders(): Observable<MetadataItem[]> {
    return this.request<MetadataItem[]>('GET', '/products/metadata/providers');
  }

  createCategory(name: string): Observable<CategoryItem> {
    return this.request<CategoryItem>('POST', '/products/catalog/categories', { name });
  }

  createSeason(name: string): Observable<MetadataItem> {
    return this.request<MetadataItem>('POST', '/products/catalog/seasons', { name });
  }

  createSize(name: string): Observable<MetadataItem> {
    return this.request<MetadataItem>('POST', '/products/catalog/sizes', { name });
  }

  createColor(name: string): Observable<MetadataItem> {
    return this.request<MetadataItem>('POST', '/products/catalog/colors', { name });
  }

  createProvider(name: string, contact_email?: string): Observable<MetadataItem> {
    return this.request<MetadataItem>('POST', '/products/catalog/providers', { name, contact_email });
  }

  // ------------------------------------------------------------------
  // Disponibilidad (CU11)
  // ------------------------------------------------------------------
  getAvailability(params: {
    product_id?: number;
    branch_id?: number;
    q?: string;
  }): Observable<AvailabilityItem[]> {
    const p: string[] = [];
    if (params.product_id) p.push(`product_id=${params.product_id}`);
    if (params.branch_id) p.push(`branch_id=${params.branch_id}`);
    if (params.q?.trim()) p.push(`q=${encodeURIComponent(params.q.trim())}`);
    const qs = p.length ? `?${p.join('&')}` : '';
    return this.request<AvailabilityItem[]>('GET', `/inventory/availability${qs}`);
  }

  // ------------------------------------------------------------------
  // Carrito (CU16)
  // ------------------------------------------------------------------
  getCart(): Observable<CartSummary> {
    return this.request<CartSummary>('GET', '/cart');
  }

  addToCart(variant_id: number, quantity = 1): Observable<CartSummary> {
    return this.request<CartSummary>('POST', '/cart', { variant_id, quantity });
  }

  updateCartItem(itemId: number, quantity: number): Observable<CartSummary> {
    return this.request<CartSummary>('PATCH', `/cart/${itemId}`, { quantity });
  }

  removeCartItem(itemId: number): Observable<CartSummary> {
    return this.request<CartSummary>('DELETE', `/cart/${itemId}`);
  }

  clearCart(): Observable<CartSummary> {
    return this.request<CartSummary>('DELETE', '/cart');
  }

  // ------------------------------------------------------------------
  // Reservas (CU13, CU14, CU15)
  // ------------------------------------------------------------------
  createReservation(data: ReservationInput): Observable<Reservation> {
    return this.request<Reservation>('POST', '/reservations', data);
  }

  getReservations(statusFilter = '', allReservations = false): Observable<Reservation[]> {
    const p: string[] = [];
    if (statusFilter) p.push(`status_filter=${encodeURIComponent(statusFilter)}`);
    if (allReservations) p.push('all_reservations=true');
    const qs = p.length ? `?${p.join('&')}` : '';
    return this.request<Reservation[]>('GET', `/reservations${qs}`);
  }

  cancelReservation(id: number): Observable<Reservation> {
    return this.request<Reservation>('PATCH', `/reservations/${id}/cancel`);
  }

  attendReservation(id: number): Observable<Reservation> {
    return this.request<Reservation>('PATCH', `/reservations/${id}/attend`);
  }

  reserveExpireStale(): Observable<{ expired: number }> {
    return this.request<{ expired: number }>('POST', '/reservations/expire-stale');
  }

  // ------------------------------------------------------------------
  // Pedidos y pagos (CU16)
  // ------------------------------------------------------------------
  checkout(data: OrderInput): Observable<Order> {
    return this.request<Order>('POST', '/orders/checkout', data);
  }

  getOrders(): Observable<Order[]> {
    return this.request<Order[]>('GET', '/orders');
  }

  /** Venta presencial en caja (CU18, cajero/encargado). */
  posSale(data: PosSaleInput): Observable<Order> {
    return this.request<Order>('POST', '/pos/sale', data);
  }

  /** Completar o reintentar el pago de un pedido pendiente (CU19). */
  payOrder(orderId: number, data: PayInput): Observable<Order> {
    return this.request<Order>('POST', `/orders/${orderId}/pay`, data);
  }

  // ------------------------------------------------------------------
  // Recomendaciones (CU22)
  // ------------------------------------------------------------------
  getRecommendations(limit = 8): Observable<Recommendation> {
    return this.request<Recommendation>('GET', `/recommendations?limit=${limit}`);
  }

  // ------------------------------------------------------------------
  // Asistente virtual / chatbot (CU23)
  // ------------------------------------------------------------------
  sendChatMessage(message: string, conversationId?: number | null): Observable<ChatReply> {
    return this.request<ChatReply>('POST', '/assistant/chat', {
      message,
      conversation_id: conversationId ?? null,
    });
  }

  getConversations(): Observable<ChatConversation[]> {
    return this.request<ChatConversation[]>('GET', '/assistant/conversations');
  }

  getConversation(id: number): Observable<ChatConversation> {
    return this.request<ChatConversation>('GET', `/assistant/conversations/${id}`);
  }

  updateOrderStatus(orderId: number, status: string): Observable<Order> {
    return this.request<Order>('PATCH', `/orders/${orderId}/status`, { status });
  }

  // ------------------------------------------------------------------
  // Notificaciones
  // ------------------------------------------------------------------
  getNotifications(): Observable<NotificationItem[]> {
    return this.request<NotificationItem[]>('GET', '/notifications');
  }

  markNotificationRead(id: number): Observable<NotificationItem> {
    return this.request<NotificationItem>('PATCH', `/notifications/${id}/read`);
  }

  // ------------------------------------------------------------------
  // Auth — Olvidé mi contraseña
  // ------------------------------------------------------------------
  forgotPassword(email: string): Observable<{ message: string; reset_token: string }> {
    return this.request('POST', '/auth/forgot-password', { email });
  }

  resetPassword(token: string, new_password: string): Observable<{ message: string }> {
    return this.request('POST', '/auth/reset-password', { token, new_password });
  }

  // ------------------------------------------------------------------
  // Perfil extendido (CU3) — phone + email editables
  // ------------------------------------------------------------------
  updateProfileFull(data: { first_name?: string; last_name?: string; email?: string; phone?: string; password?: string }): Observable<User> {
    return this.request<User>('PATCH', '/auth/me', data).pipe(
      tap((user) => this.setUser(user))
    );
  }

  // ------------------------------------------------------------------
  // Usuarios y roles (CU4) — admin
  // ------------------------------------------------------------------
  getUsers(params: { q?: string; role_id?: number; is_active?: boolean } = {}): Observable<User[]> {
    const p: string[] = [];
    if (params.q?.trim()) p.push(`q=${encodeURIComponent(params.q.trim())}`);
    if (params.role_id) p.push(`role_id=${params.role_id}`);
    if (params.is_active !== undefined) p.push(`is_active=${params.is_active}`);
    const qs = p.length ? `?${p.join('&')}` : '';
    return this.request<User[]>('GET', `/users/${qs}`);
  }

  getUser(id: number): Observable<User> {
    return this.request<User>('GET', `/users/${id}`);
  }

  createUser(data: { first_name: string; last_name: string; email: string; password: string; phone?: string; role_id: number }): Observable<User> {
    return this.request<User>('POST', '/users/', data);
  }

  updateUser(id: number, data: { first_name?: string; last_name?: string; email?: string; phone?: string; password?: string; role_id?: number; is_active?: boolean }): Observable<User> {
    return this.request<User>('PATCH', `/users/${id}`, data);
  }

  deactivateUser(id: number): Observable<void> {
    return this.request<void>('DELETE', `/users/${id}`);
  }

  getRoles(): Observable<{ id: number; name: string; description?: string }[]> {
    return this.request<{ id: number; name: string; description?: string }[]>('GET', '/users/roles');
  }

  // ------------------------------------------------------------------
  // Inventario y movimientos (CU21) — admin / encargado
  // ------------------------------------------------------------------
  getInventory(params: { branch_id?: number; product_id?: number; low_stock_only?: boolean } = {}): Observable<any[]> {
    const p: string[] = [];
    if (params.branch_id) p.push(`branch_id=${params.branch_id}`);
    if (params.product_id) p.push(`product_id=${params.product_id}`);
    if (params.low_stock_only) p.push('low_stock_only=true');
    const qs = p.length ? `?${p.join('&')}` : '';
    return this.request<any[]>('GET', `/inventory/${qs}`);
  }

  createInventory(data: { variant_id: number; branch_id: number; available: number }): Observable<any> {
    return this.request('POST', '/inventory/', data);
  }

  updateInventory(id: number, data: { available: number }): Observable<any> {
    return this.request('PATCH', `/inventory/${id}`, data);
  }

  getInventoryMovements(params: { inventory_id?: number; movement_type?: string } = {}): Observable<any[]> {
    const p: string[] = [];
    if (params.inventory_id) p.push(`inventory_id=${params.inventory_id}`);
    if (params.movement_type) p.push(`movement_type=${encodeURIComponent(params.movement_type)}`);
    const qs = p.length ? `?${p.join('&')}` : '';
    return this.request<any[]>('GET', `/inventory/movements${qs}`);
  }

  createInventoryMovement(data: { inventory_id: number; movement_type: string; quantity: number; reason?: string }): Observable<any> {
    return this.request('POST', '/inventory/movements', data);
  }

  // ------------------------------------------------------------------
  // Temporadas y colecciones (CU8) — CRUD
  // ------------------------------------------------------------------
  updateSeason(id: number, data: { name: string; description?: string }): Observable<any> {
    return this.request('PATCH', `/products/catalog/seasons/${id}`, data);
  }

  deleteSeason(id: number): Observable<void> {
    return this.request<void>('DELETE', `/products/catalog/seasons/${id}`);
  }

  getCollections(): Observable<any[]> {
    return this.request<any[]>('GET', '/products/metadata/collections');
  }

  createCollection(data: { name: string; season_id?: number }): Observable<any> {
    return this.request('POST', '/products/catalog/collections', data);
  }

  // ------------------------------------------------------------------
  // Proveedores (CU9)
  // ------------------------------------------------------------------
  updateProvider(id: number, data: { name?: string; contact_email?: string }): Observable<any> {
    return this.request('PATCH', `/products/catalog/providers/${id}`, data);
  }

  deleteProvider(id: number): Observable<void> {
    return this.request<void>('DELETE', `/products/catalog/providers/${id}`);
  }

  // ------------------------------------------------------------------
  // Reportes y dashboards (CU25)
  // ------------------------------------------------------------------
  getDashboardReport(params: {
    desde?: string;
    hasta?: string;
    branch_id?: number;
    category_id?: number;
  } = {}): Observable<DashboardReport> {
    const p: string[] = [];
    if (params.desde) p.push(`desde=${encodeURIComponent(params.desde)}`);
    if (params.hasta) p.push(`hasta=${encodeURIComponent(params.hasta)}`);
    if (params.branch_id) p.push(`branch_id=${params.branch_id}`);
    if (params.category_id) p.push(`category_id=${params.category_id}`);
    const qs = p.length ? `?${p.join('&')}` : '';
    return this.request<DashboardReport>('GET', `/reports/dashboard${qs}`);
  }

  /** Reporte por comando de voz (CU24, admin/encargado). */
  voiceReport(command: string): Observable<VoiceReportResponse> {
    return this.request<VoiceReportResponse>('POST', '/reports/voice', { command });
  }

  // ------------------------------------------------------------------
  // Promociones (CU27) — administración
  // ------------------------------------------------------------------
  getPromotions(includeInactive = true): Observable<Promotion[]> {
    const q = includeInactive ? '?include_inactive=true' : '';
    return this.request<Promotion[]>('GET', `/promotions/${q}`);
  }

  createPromotion(data: PromotionInput): Observable<Promotion> {
    return this.request<Promotion>('POST', '/promotions/', data);
  }

  updatePromotion(id: number, data: Partial<PromotionInput>): Observable<Promotion> {
    return this.request<Promotion>('PATCH', `/promotions/${id}`, data);
  }

  deactivatePromotion(id: number): Observable<Promotion> {
    return this.request<Promotion>('DELETE', `/promotions/${id}`);
  }

  // ------------------------------------------------------------------
  // Portal proveedor
  // ------------------------------------------------------------------
  getProviderMe(): Observable<ProviderMe> {
    return this.request<ProviderMe>('GET', '/providers/me');
  }

  getProviderProducts(): Observable<Product[]> {
    return this.request<Product[]>('GET', '/providers/products');
  }

  updateProviderProduct(id: number, isActive: boolean): Observable<Product> {
    return this.request<Product>('PATCH', `/providers/products/${id}`, { is_active: isActive });
  }

  proposeProduct(data: ProposalInput): Observable<Proposal> {
    return this.request<Proposal>('POST', '/providers/products', data);
  }

  /** Propuestas (proveedor: las suyas; administrador: todas). */
  getProposals(): Observable<Proposal[]> {
    return this.request<Proposal[]>('GET', '/providers/proposals');
  }

  approveProposal(id: number, comment?: string): Observable<Proposal> {
    return this.request<Proposal>('PATCH', `/providers/proposals/${id}/approve`, { admin_comment: comment || null });
  }

  rejectProposal(id: number, comment?: string): Observable<Proposal> {
    return this.request<Proposal>('PATCH', `/providers/proposals/${id}/reject`, { admin_comment: comment || null });
  }

  /** Vincular un usuario con rol Proveedor a una empresa (admin). */
  linkProviderAccount(data: { user_id: number; provider_id: number }): Observable<{ user_id: number; provider_id: number }> {
    return this.request('POST', '/providers/accounts', data);
  }
}