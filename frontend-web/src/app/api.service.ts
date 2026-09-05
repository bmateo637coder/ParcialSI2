
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { BehaviorSubject } from 'rxjs';
@Injectable({ providedIn: 'root' })
export class ApiService {
  private baseUrl = 'http://127.0.0.1:8000/api';
  currentUser = new BehaviorSubject<any>(null);
  constructor(private http: HttpClient) {
     const token = localStorage.getItem('token');
     const role = localStorage.getItem('role');
     const email = localStorage.getItem('email');
     if(token) this.currentUser.next({token, role, email});
  }
  getHeaders() { return new HttpHeaders().set('Authorization', `Bearer ${localStorage.getItem('token')}`); }
  login(data: any) { return this.http.post(`${this.baseUrl}/auth/login`, data); }
  register(data: any) { return this.http.post(`${this.baseUrl}/auth/register`, data); }
  getProfile(email: string) { return this.http.get(`${this.baseUrl}/auth/profile?email=${email}`, {headers: this.getHeaders()}); }
  getBranches(city: string = '') { return this.http.get(`${this.baseUrl}/branches/${city ? '?city='+city : ''}`); }
  createBranch(data: any) { return this.http.post(`${this.baseUrl}/branches/`, data, {headers: this.getHeaders()}); }
  getProducts(q: string = '') { return this.http.get(`${this.baseUrl}/products/${q ? '?q='+q : ''}`); }
  createProduct(data: any) { return this.http.post(`${this.baseUrl}/products/`, data, {headers: this.getHeaders()}); }
  logout() { localStorage.clear(); this.currentUser.next(null); }
}
