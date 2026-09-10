import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { BehaviorSubject, Observable, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { environment } from '../environments/environment';
import { ToastService } from './toast.service';

export interface User {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  role_name: string;
  is_active: boolean;
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
        catchError((err: HttpErrorResponse) => {
          if (err.status === 401 && !url.includes('/auth/login')) {
            this.logout();
            this.toast.error('Tu sesión expiró. Vuelve a iniciar sesión.');
          } else {
            this.toast.error(this.errorMessage(err));
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
}