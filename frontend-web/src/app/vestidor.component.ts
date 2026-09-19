import { Component, ElementRef, NgZone, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Product } from './api.service';

export const FALLBACK_GARMENT = 'https://images.unsplash.com/photo-1591047139829-d91aecb6caea?auto=format&fit=crop&q=80&w=600';

export function buildOverlayTransform(scale: number, offsetX: number, offsetY: number, rotation: number): string {
  const s = (scale || 100) / 100;
  return `translate(-50%, -50%) translate(${offsetX || 0}px, ${offsetY || 0}px) scale(${s.toFixed(2)}) rotate(${rotation || 0}deg)`;
}

@Component({
  selector: 'app-vestidor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
  <div class="page-head">
    <span class="eyebrow">Vestidor virtual · CU12 · MVP AR</span>
    <h1>Prueba antes de comprar</h1>
    <p class="lead" *ngIf="product">
      Mostramos <strong>{{ product.name }}</strong> superpuesto sobre tu cámara en tiempo real.
      Ajusta tamaño, posición y rotación con los controles laterales.
    </p>
    <p class="lead" *ngIf="!product">No recibimos la prenda seleccionada. Vuelve al catálogo y elige una.</p>
  </div>

  <div class="stages" *ngIf="product">
    <div class="stage-wrap">
      <video #video autoplay playsinline muted></video>
      <div class="stage-frame" *ngIf="streaming" [style.transform]="overlayTransform">
        <img [src]="product!.image_url || fallbackImg" [alt]="product!.name" (error)="onImgError($event)">
      </div>

      <div class="cam-state" *ngIf="loadingCam || !streaming">
        <div class="spinner" *ngIf="loadingCam"></div>
        <span>{{ camError || 'Activando cámara…' }}</span>
        <button class="btn btn-accent btn-sm" (click)="startCam()" *ngIf="!loadingCam && camError" [disabled]="starting">
          Reintentar con cámara
        </button>
      </div>
    </div>

    <aside class="stage-controls card">
      <h4 style="margin-bottom:.75rem;">Ajustes</h4>

      <label class="slider-row">Tamaño <span class="slider-val">{{ scale }}%</span>
        <input type="range" min="30" max="180" [(ngModel)]="scale">
      </label>
      <label class="slider-row">Horizontal <span class="slider-val">{{ offsetX }}px</span>
        <input type="range" min="-120" max="120" [(ngModel)]="offsetX">
      </label>
      <label class="slider-row">Vertical <span class="slider-val">{{ offsetY }}px</span>
        <input type="range" min="-120" max="120" [(ngModel)]="offsetY">
      </label>
      <label class="slider-row">Rotación <span class="slider-val">{{ rotation }}°</span>
        <input type="range" min="-45" max="45" [(ngModel)]="rotation">
      </label>

      <div class="controls-actions">
        <button class="btn btn-outline" (click)="goCatalog()">Volver al catálogo</button>
        <button class="btn btn-accent" (click)="keepShopping()" [disabled]="!product">Elegir talla / reservar</button>
      </div>
      <p class="form-hint" style="margin-top:.9rem;">
        Superposición en tiempo real (Producto Mínimo Viable). Si el navegador no permite la cámara,
        seguimos en el catálogo sin activar el vestidor.
      </p>
    </aside>
  </div>
  `,
  styles: [`
    :host { display: block; padding-bottom: 2rem; }
    .stages { display: flex; flex-wrap: wrap; gap: 1.5rem; align-items: flex-start; max-width: 980px; margin: 1rem auto 0; }
    .stage-wrap { position: relative; flex: 1 1 480px; min-height: 320px; background: #000; border-radius: 16px; overflow: hidden; }
    .stage-wrap video { width: 100%; height: 100%; min-height: 320px; max-height: 62vh; object-fit: cover; transform: scaleX(-1); display: block; }
    .stage-frame { position: absolute; left: 50%; top: 50%; width: 210px; will-change: transform; pointer-events: none; }
    .stage-frame img { width: 100%; display: block; }
    .cam-state { position: absolute; inset: 0; display: flex; flex-direction: column; gap: .6rem; align-items: center; justify-content: center; color: #fff; background: rgba(0,0,0,.45); text-align: center; padding: 1rem; }
    .stage-controls { flex: 0 1 300px; }
    .slider-row { display: block; font-size: .9rem; margin-bottom: .85rem; color: var(--muted, #666); }
    .slider-row .slider-val { float: right; font-weight: 600; color: var(--text, #222); }
    .slider-row input[type=range] { width: 100%; margin-top: .25rem; accent-color: var(--accent, #e63946); }
    .controls-actions { display: flex; gap: .5rem; margin-top: .25rem; }
  `],
})
export class VestidorComponent implements OnInit, OnDestroy {
  product: Product | null = null;
  fallbackImg = FALLBACK_GARMENT;

  loadingCam = false;
  streaming = false;
  starting = false;
  camError = '';

  scale = 100;
  offsetX = 0;
  offsetY = 0;
  rotation = 0;

  private stream: MediaStream | null = null;

  @ViewChild('video') video!: ElementRef<HTMLVideoElement>;

  constructor(private router: Router, private ngZone: NgZone) {}

  get overlayTransform(): string {
    return buildOverlayTransform(this.scale, this.offsetX, this.offsetY, this.rotation);
  }

  ngOnInit(): void {
    const st = history.state as { product?: Product } | null;
    if (st?.product?.id) {
      this.product = st.product;
      this.startCam();
    }
  }

  startCam(): void {
    if (this.streaming || this.starting) return;
    if (!navigator.mediaDevices?.getUserMedia) {
      this.camError = 'Tu navegador no permite acceder a la cámara en este contexto.';
      return;
    }
    this.starting = true;
    this.loadingCam = true;
    this.camError = '';
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: 'user', width: { ideal: 1280 } }, audio: false })
      .then((stream) => {
        this.stream = stream;
        const v = this.video?.nativeElement;
        if (v) {
          v.srcObject = stream;
          v.play().catch(() => {});
        }
        this.ngZone.run(() => {
          this.streaming = true;
          this.loadingCam = false;
          this.starting = false;
        });
      })
      .catch((err: unknown) => {
        const name = (err as { name?: string })?.name;
        this.camError =
          name === 'NotAllowedError' || name === 'PermissionDeniedError'
            ? 'No diste permiso a la cámara. Puedes reintentarlo desde el botón inferior.'
            : 'No pudimos acceder a la cámara en este dispositivo o navegador.';
        this.ngZone.run(() => {
          this.loadingCam = false;
          this.starting = false;
        });
      });
  }

  goCatalog(): void {
    this.stopCam();
    this.router.navigate(['/']);
  }

  keepShopping(): void {
    if (!this.product) return;
    const id = this.product.id;
    this.stopCam();
    this.router.navigate(['/'], { state: { openProductId: id } });
  }

  onImgError(event: Event): void {
    (event.target as HTMLImageElement).src = this.fallbackImg;
  }

  stopCam(): void {
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
    this.streaming = false;
  }

  ngOnDestroy(): void {
    this.stopCam();
  }
}