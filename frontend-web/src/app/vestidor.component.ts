import { Component, ElementRef, NgZone, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Product } from './api.service';

export const FALLBACK_GARMENT = '/img/garment.svg';

export function buildOverlayTransform(scale: number, offsetX: number, offsetY: number, rotation: number): string {
  const s = (scale || 100) / 100;
  return `translate(-50%, -50%) translate(${offsetX || 0}px, ${offsetY || 0}px) scale(${s.toFixed(2)}) rotate(${rotation || 0}deg)`;
}

interface Tien {
  name: string;
  hex: string | null;
}

const TINTS: Tien[] = [
  { name: 'Original', hex: null },
  { name: 'Rojo', hex: '#c0392b' },
  { name: 'Azul', hex: '#2c6fbb' },
  { name: 'Verde', hex: '#2e7d32' },
  { name: 'Amarillo', hex: '#d4a017' },
  { name: 'Rosa', hex: '#d15c8d' },
  { name: 'Negro', hex: '#232830' },
];

const SIZE_PRESETS = [
  { name: 'S', scale: 90 },
  { name: 'M', scale: 100 },
  { name: 'L', scale: 115 },
  { name: 'XL', scale: 130 },
];

const POSE_CDN = 'https://cdn.jsdelivr.net/npm/@mediapipe/pose/pose.js';

const SILHOUETTE_SVG = `
<svg viewBox="0 0 260 520" xmlns="http://www.w3.org/2000/svg" class="silhouette">
  <defs>
    <linearGradient id="sil" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#dfe6ee"/>
      <stop offset="1" stop-color="#b9c4d0"/>
    </linearGradient>
  </defs>
  <g fill="url(#sil)">
    <ellipse cx="130" cy="46" rx="30" ry="36"/>
    <path d="M95 86 L70 92 L64 108 L84 106 L92 150 L112 152 L112 132 L116 132 L116 176 L108 176 L106 192 L90 208 L66 360 L84 372 L102 226 L112 216 L112 178 L148 178 L148 216 L158 226 L176 372 L194 360 L170 208 L154 192 L152 176 L144 176 L144 132 L148 132 L148 152 L168 150 L176 106 L196 108 L190 92 L165 86 L150 70 L130 66 L110 70 Z"/>
  </g>
</svg>`;

@Component({
  selector: 'app-vestidor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
  <div class="page-head">
    <span class="eyebrow">Vestidor virtual · CU12 · AR avanzado</span>
    <h1>Prueba antes de comprar</h1>
    <p class="lead" *ngIf="product">
      Mostramos <strong>{{ product.name }}</strong> sobre tu cámara (o sobre una silueta demo).
      Activa <em>Auto-ancla</em> para que la prenda se ajuste solo a tus hombros.
    </p>
    <p class="lead" *ngIf="!product">No recibimos la prenda seleccionada. Vuelve al catálogo y elige una.</p>
  </div>

  <div class="stages" *ngIf="product">
    <div class="stage-wrap" #stage (pointerdown)="dragStart($event)" (pointermove)="dragMove($event)" (pointerup)="dragEnd()" (pointerleave)="dragEnd()">
      <video #video autoplay playsinline muted *ngIf="mode === 'camera'"></video>
      <div class="mode-demo" *ngIf="mode === 'demo'">
        <div [innerHTML]="silhouette"></div>
        <span class="mode-tag">Silueta demo (sin cámara)</span>
      </div>

      <div class="stage-frame" *ngIf="!capturing" [style.transform]="overlayTransform">
        <div class="tint" [hidden]="!activeTint.hex" [style.background]="activeTint.hex"></div>
        <span class="frame-tint-label" *ngIf="activeTint.hex">{{ activeTint.name }}</span>
        <img [src]="overlayImgSrc" [alt]="product!.name" [style.opacity]="opacityPct" [style.transform]="flip ? 'scaleX(-1)' : 'none'"
          (error)="onImgError($event)">
      </div>

      <div class="pose-state" *ngIf="poseLoading"><div class="spinner"></div><span>Detectando postura…</span></div>
      <div class="pose-state warn" *ngIf="poseError">
        <span>{{ poseError }}</span>
      </div>

      <div class="cam-state" *ngIf="loadingCam || camError">
        <div class="spinner" *ngIf="loadingCam"></div>
        <span>{{ camError || 'Activando cámara…' }}</span>
        <div class="cam-actions" *ngIf="!loadingCam">
          <button class="btn btn-accent btn-sm" (click)="startCam()">Reintentar cámara</button>
          <button class="btn btn-outline btn-sm" (click)="useDemo()">Usar silueta demo</button>
        </div>
      </div>
    </div>

    <aside class="stage-controls card">
      <h4 style="margin-bottom:.75rem;">Ajustes</h4>

      <label class="switch-row">
        <span>Auto-ancla a hombros</span>
        <input type="checkbox" [(ngModel)]="autoFit" (ngModelChange)="toggleAutoFit()">
      </label>
      <label class="switch-row">
        <span>Espejo</span>
        <input type="checkbox" [(ngModel)]="flip">
      </label>

      <div class="group">
        <span class="group-label">Talla</span>
        <div class="chip-row">
          <button *ngFor="let p of sizePresets" class="chip" [class.on]="selectedSize === p.name"
            (click)="applySize(p)">{{ p.name }}</button>
        </div>
      </div>

      <div class="group">
        <span class="group-label">Color / tinte</span>
        <div class="chip-row">
          <button *ngFor="let c of tints" class="chip" [class.on]="activeTint === c"
            (click)="applyTint(c)">{{ c.name }}</button>
        </div>
      </div>

      <label class="slider-row">Tamaño <span class="slider-val">{{ scale }}%</span>
        <input type="range" min="30" max="180" [(ngModel)]="scale">
      </label>
      <label class="slider-row">Horizontal <span class="slider-val">{{ offsetX }}px</span>
        <input type="range" min="-160" max="160" [(ngModel)]="offsetX">
      </label>
      <label class="slider-row">Vertical <span class="slider-val">{{ offsetY }}px</span>
        <input type="range" min="-160" max="160" [(ngModel)]="offsetY">
      </label>
      <label class="slider-row">Rotación <span class="slider-val">{{ rotation }}°</span>
        <input type="range" min="-45" max="45" [(ngModel)]="rotation">
      </label>
      <label class="slider-row">Opacidad <span class="slider-val">{{ opacity }}%</span>
        <input type="range" min="20" max="100" [(ngModel)]="opacity">
      </label>

      <p class="form-hint" style="margin-top:.35rem;">Consejo: también puedes arrastrar la prenda con el mouse sobre el lienzo. Con Auto-ancla activo, la prenda sigue a tus hombros.</p>

      <div class="controls-actions">
        <button class="btn btn-accent" (click)="capture()" [disabled]="capturing">📷 Capturar foto</button>
        <button class="btn btn-outline" (click)="goCatalog()">Volver al catálogo</button>
      </div>
      <div class="controls-actions" style="margin-top:.5rem;">
        <button class="btn btn-accent" (click)="keepShopping()" [disabled]="!product">Elegir talla / reservar</button>
        <button class="btn btn-outline" (click)="useDemo()" *ngIf="mode === 'camera'">Silueta demo</button>
      </div>
      <a class="download-link" *ngIf="shotUrl" [href]="shotUrl" [download]="'vestidor-' + (product.name || 'prenda').replace(/\\s+/g,'-').toLowerCase() + '.png'">
        ⬇ Descargar mi prueba ({{ shotUrl.length < 100000 ? 'imagen ligera' : 'imagen completa' }})
      </a>
    </aside>
  </div>
  `,
  styles: [`
    :host { display: block; padding-bottom: 2rem; }
    .stages { display: flex; flex-wrap: wrap; gap: 1.5rem; align-items: flex-start; max-width: 1020px; margin: 1rem auto 0; }
    .stage-wrap { position: relative; flex: 1 1 500px; min-height: 340px; background:
      radial-gradient(circle at 30% 20%, #24303f, #0d1117); border-radius: 16px;
      overflow: hidden; cursor: grab; touch-action: none; aspect-ratio: 4 / 5; }
    .stage-wrap:active { cursor: grabbing; }
    .stage-wrap video { width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); display: block; }
    .mode-demo { position: absolute; inset: 0; display: flex; align-items: flex-end; justify-content: center; padding-bottom: 1rem; color:#cbd5e1; }
    .mode-demo .silhouette { height: 100%; filter: brightness(.85); }
    .mode-tag { position: absolute; top: .75rem; left: .75rem; background: rgba(0,0,0,.55); color:#fff; font-size:.72rem; padding:.3rem .6rem; border-radius: 999px; }
    .stage-frame { position: absolute; left: 50%; top: 50%; width: 210px; will-change: transform; pointer-events: none;
      clip-path: polygon(26% 0%, 40% 6%, 60% 6%, 74% 0%, 100% 0%, 100% 18%, 86% 24%, 86% 78%, 100% 84%, 100% 100%,
        0% 100%, 0% 84%, 14% 78%, 14% 24%, 0% 18%, 0% 0%);
      filter: drop-shadow(0 12px 18px rgba(0,0,0,.4)); }
    .stage-frame img { width: 100%; display: block; }
    .tint { position: absolute; inset: -1px; pointer-events: none; mix-blend-mode: color; opacity: .72; }
    .frame-tint-label { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
      text-shadow: 0 1px 3px rgba(0,0,0,.7); color: #fff; font-size: .8rem; font-weight: 700; letter-spacing: .04em;
      text-transform: uppercase; opacity: .85; }
    .pose-state { position: absolute; left: .75rem; bottom: .75rem; display:flex; gap:.4rem; align-items:center;
      color:#fff; background: rgba(0,0,0,.55); font-size:.75rem; padding:.35rem .7rem; border-radius:999px; }
    .pose-state .spinner { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,.3); border-top-color:#fff; border-radius:50%; animation: spin 1s linear infinite; }
    .pose-state.warn { color:#ffd166; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .cam-actions { display:flex; gap:.5rem; align-items:center; justify-content:center; flex-wrap:wrap; }
    .cam-state { position: absolute; inset: 0; display: flex; flex-direction: column; gap: .6rem; align-items: center; justify-content: center; color: #fff; background: rgba(0,0,0,.45); text-align: center; padding: 1rem; }
    .cam-state .spinner { width: 26px; height: 26px; border: 3px solid rgba(255,255,255,.3); border-top-color:#fff; border-radius: 50%; animation: spin 1s linear infinite; }
    .stage-controls { flex: 0 1 330px; }
    .switch-row { display: flex; justify-content: space-between; align-items: center; font-size: .9rem; margin-bottom: .6rem; color: var(--text, #222); }
    .switch-row input { accent-color: var(--accent, #e63946); }
    .group { margin-bottom: .8rem; }
    .group-label { display:block; font-size:.8rem; color: var(--muted,#666); margin-bottom:.3rem; }
    .chip-row { display:flex; flex-wrap:wrap; gap:.4rem; }
    .chip { border:1px solid var(--line,#ddd); background:#fff; color:var(--text,#222); border-radius:999px; padding:.25rem .7rem; font-size:.8rem; cursor:pointer; }
    .chip.on { background: var(--accent,#e63946); border-color: var(--accent,#e63946); color:#fff; }
    .slider-row { display: block; font-size: .9rem; margin-bottom: .8rem; color: var(--muted, #666); }
    .slider-row .slider-val { float: right; font-weight: 600; color: var(--text, #222); }
    .slider-row input[type=range] { width: 100%; margin-top: .25rem; accent-color: var(--accent, #e63946); }
    .controls-actions { display: flex; gap: .5rem; margin-top: .25rem; flex-wrap: wrap; }
    .download-link { display: block; margin-top: .8rem; font-size: .85rem; color: var(--accent,#e63946); font-weight: 600; }
  `],
})
export class VestidorComponent implements OnInit, OnDestroy {
  product: Product | null = null;
  fallbackImg = FALLBACK_GARMENT;
  silhouette = SILHOUETTE_SVG;
  tints = TINTS;
  sizePresets = SIZE_PRESETS;

  mode: 'camera' | 'demo' = 'camera';
  loadingCam = false;
  streaming = false;
  starting = false;
  camError = '';
  capturing = false;
  shotUrl = '';

  scale = 100;
  offsetX = 0;
  offsetY = 0;
  rotation = 0;
  opacity = 100;
  flip = false;
  autoFit = true;
  selectedSize = 'M';
  activeTint = TINTS[0];

  poseLoading = false;
  poseError = '';
  private poseReady = false;
  private detector: any = null;
  private rafId: number | null = null;
  private anchorUpdate: { x: number; y: number; fit: number } | null = null;

  private stream: MediaStream | null = null;
  private dragging = false;
  private dragStartX = 0;
  private dragStartY = 0;
  private dragOffsetX = 0;
  private dragOffsetY = 0;

  @ViewChild('video') video!: ElementRef<HTMLVideoElement>;
  @ViewChild('stage') stage!: ElementRef<HTMLElement>;

  constructor(private router: Router, private ngZone: NgZone) {}

  get opacityPct(): number {
    return (this.opacity || 100) / 100;
  }

  get overlayImgSrc(): string {
    const src = this.product?.image_url;
    return src && src.trim() ? src : this.fallbackImg;
  }

  get tintColor(): string | null {
    return this.activeTint?.hex || null;
  }

  get overlayTransform(): string {
    const s = ((this.scale || 100) / 100) * this.fitFactor;
    const dx = (this.offsetX || 0) + (this.autoFit && this.anchorUpdate ? this.anchorUpdate.x : 0);
    const dy = (this.offsetY || 0) + (this.autoFit && this.anchorUpdate ? this.anchorUpdate.y : 0);
    return `translate(-50%, -50%) translate(${dx.toFixed(1)}px, ${dy.toFixed(1)}px) scale(${s.toFixed(2)}) rotate(${this.rotation || 0}deg)`;
  }

  private get fitFactor(): number {
    return this.autoFit && this.anchorUpdate ? this.anchorUpdate.fit : 1;
  }

  ngOnInit(): void {
    const st = history.state as { product?: Product } | null;
    if (st?.product?.id) {
      this.product = st.product;
      this.startCam();
    }
  }

  // ----------------------------------------------------------------
  // Cámara / silueta demo
  // ----------------------------------------------------------------
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
        this.stopDetector();
        this.stream = stream;
        this.mode = 'camera';
        const v = this.video?.nativeElement;
        if (v) {
          v.srcObject = stream;
          v.play().catch(() => {});
        }
        this.ngZone.run(() => {
          this.streaming = true;
          this.loadingCam = false;
          this.starting = false;
          this.camError = '';
          this.spinDetector();
        });
      })
      .catch((err: unknown) => {
        const name = (err as { name?: string })?.name;
        this.camError =
          name === 'NotAllowedError' || name === 'PermissionDeniedError'
            ? 'No diste permiso a la cámara. Puedes usar la silueta demo o reintentar.'
            : 'No pudimos acceder a la cámara aquí. Usa la silueta demo sin problema.';
        this.ngZone.run(() => {
          this.loadingCam = false;
          this.starting = false;
        });
      });
  }

  useDemo(): void {
    this.stopCam();
    this.stopDetector();
    this.mode = 'demo';
    this.streaming = false;
    this.camError = '';
    this.resetCrop();
  }

  private resetCrop(): void {
    this.anchorUpdate = { x: 0, y: 35, fit: 1 };
  }

  // ----------------------------------------------------------------
  // Pose detection (lazy, con degradación a manual)
  // ----------------------------------------------------------------
  toggleAutoFit(): void {
    if (this.autoFit) {
      this.spinDetector();
    } else {
      this.stopDetector();
    }
  }

  private spinDetector(): void {
    if (!this.autoFit || this.mode !== 'camera') return;
    if (this.poseReady) {
      this.poseLoading = false;
      this.runPose();
      return;
    }
    if (this.poseError) return;
    if (this.poseLoading) return;
    this.poseLoading = true;
    this.ngZone.runOutsideAngular(() => {
      this.loadPose().then(() => {
        this.ngZone.run(() => {
          this.poseLoading = false;
          if (this.autoFit && this.mode === 'camera' && this.streaming) {
            this.poseReady = true;
            this.runPose();
          }
        });
      }).catch((err) => {
        this.ngZone.run(() => {
          this.poseLoading = false;
          this.autoFit = false;
          this.poseError = 'No se pudo activar la detección de pose (requiere internet). Mantienes el ajuste manual.';
          console.warn('pose:', err);
        });
      });
    });
  }

  private loadPose(): Promise<void> {
    const anyWin = window as any;
    if (anyWin.Pose) return Promise.resolve();
    return new Promise<void>((resolve, reject) => {
      const script = document.createElement('script');
      script.src = POSE_CDN;
      script.async = true;
      script.onload = () => (anyWin.Pose ? resolve() : reject(new Error('Pose undefined')));
      script.onerror = () => reject(new Error('No se pudo descargar' + POSE_CDN));
      document.head.appendChild(script);
    });
  }

  private runPose(): void {
    if (!this.detector && this.poseReady && (window as any).Pose) {
      const win = window as any;
      this.detector = new win.Pose({
        locateFile: (f: string) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${f}`,
      });
      this.detector.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5,
      });
      this.detector.onResults((res: any) => this.onResults(res));
      this.detector.initialize().then(() => this.loopPose());
      return;
    }
    this.loopPose();
  }

  private loopPose(): void {
    if (!this.autoFit || this.mode !== 'camera' || this.dragging || !this.detector) {
      this.stopDetectorLoop();
      return;
    }
    const v = this.video?.nativeElement;
    if (this.streaming && this.detector && v && v.readyState >= 2) {
      try {
        this.detector.send({ image: v });
      } catch { /* ignorado */ }
    }
    this.rafId = requestAnimationFrame(() => this.loopPose());
  }

  private onResults(res: any): void {
    const lm = res?.poseLandmarks;
    if (!lm || lm.length < 20) return;
    const left = lm[11];
    const right = lm[12];
    if (!left || !right) return;
    const stage = this.stage?.nativeElement;
    const w = stage?.clientWidth ?? 500;
    const h = stage?.clientHeight ?? 625;
    // El video se renderiza espejado: la coordenada X de MediaPipe va invertida.
    const cx = (1 - (left.x + right.x) / 2) * w;
    const cy = (left.y + right.y) / 2 * h;
    const shoulderW = Math.max(180, Math.abs(left.x - right.x) * w);
    const anchorDx = cx - w / 2;
    const anchorDy = cy - h * 0.42;
    const fit = shoulderW / 300;
    this.ngZone.run(() => {
      this.anchorUpdate = { x: anchorDx, y: Math.max(-h, Math.min(h, anchorDy)), fit: Math.min(3, fit) };
    });
  }

  private stopDetectorLoop(): void {
    if (this.rafId != null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
  }

  private stopDetector(): void {
    this.stopDetectorLoop();
    if (this.detector) {
      try { this.detector.close?.(); } catch { /* ignorado */ }
      this.detector = null;
    }
    if (this.poseReady) {
      this.poseReady = false;
      this.poseError = '';
    }
    this.anchorUpdate = null;
  }

  // ----------------------------------------------------------------
  // Drag con mouse sobre el lienzo
  // ----------------------------------------------------------------
  dragStart(e: PointerEvent): void {
    if (this.mode !== 'camera' && this.mode !== 'demo') return;
    this.dragging = true;
    this.dragStartX = e.clientX;
    this.dragStartY = e.clientY;
    this.dragOffsetX = this.offsetX;
    this.dragOffsetY = this.offsetY;
  }

  dragMove(e: PointerEvent): void {
    if (!this.dragging) return;
    e.preventDefault();
    const dx = e.clientX - this.dragStartX;
    const dy = e.clientY - this.dragStartY;
    // Si hay auto-ancla activo, el arrastre refina la posición; si no, mueve el overlay directamente.
    this.offsetX = this.dragOffsetX + dx;
    this.offsetY = this.dragOffsetY + dy;
  }

  dragEnd(): void {
    this.dragging = false;
  }

  // ----------------------------------------------------------------
  // Talla, tinte, filtros
  // ----------------------------------------------------------------
  applySize(p: { name: string; scale: number }): void {
    this.selectedSize = p.name;
    this.scale = p.scale;
  }

  applyTint(c: Tien): void {
    this.activeTint = c;
  }

  // ----------------------------------------------------------------
  // Captura de foto
  // ----------------------------------------------------------------
  capture(): void {
    if (this.capturing) return;
    this.capturing = true;
    const stage = this.stage?.nativeElement;
    if (!stage) {
      this.capturing = false;
      return;
    }
    const canvas = document.createElement('canvas');
    canvas.width = stage.clientWidth;
    canvas.height = stage.clientHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      this.capturing = false;
      return;
    }

    if (this.mode === 'camera' && this.video?.nativeElement) {
      ctx.save();
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
      ctx.drawImage(this.video.nativeElement, 0, 0, canvas.width, canvas.height);
      ctx.restore();
    } else {
      ctx.fillStyle = '#141a21';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#5b6674';
      ctx.beginPath();
      ctx.ellipse(canvas.width / 2, canvas.height * 0.2, 46, 56, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.moveTo(canvas.width / 2 - 4, canvas.height * 0.42);
      ctx.lineTo(canvas.width / 2 - 34, canvas.height * 0.58);
      ctx.lineTo(canvas.width / 2 + 34, canvas.height * 0.58);
      ctx.lineTo(canvas.width / 2 + 4, canvas.height * 0.42);
      ctx.closePath();
      ctx.fill();
    }

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      this.paintOverlay(ctx, canvas, img);
      this.snapshot(canvas);
    };
    img.onerror = () => {
      // Sin red para la imagen remota: capturamos la escena igualmente con la silueta.
      this.snapshot(canvas);
    };
    img.src = this.product?.image_url || this.fallbackImg;
  }

  private paintOverlay(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, img: HTMLImageElement): void {
    ctx.save();
    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.rotate(((this.rotation || 0) * Math.PI) / 180);
    const s = ((this.scale || 100) / 100) * this.fitFactor;
    ctx.scale(s, s);
    if (this.flip) ctx.scale(-1, 1);
    const dx = (this.offsetX || 0) + (this.autoFit && this.anchorUpdate ? this.anchorUpdate.x : 0);
    const dy = (this.offsetY || 0) + (this.autoFit && this.anchorUpdate ? this.anchorUpdate.y : 0);
    ctx.translate(dx, dy);
    ctx.globalAlpha = this.opacityPct;
    const iw = 210;
    const ih = iw * (img.height / Math.max(1, img.width));
    this.traceGarment(ctx, iw, ih);
    ctx.clip();
    ctx.drawImage(img, -iw / 2, -ih / 2, iw, ih);
    const tint = this.tintColor;
    if (tint) {
      ctx.globalCompositeOperation = 'color';
      ctx.globalAlpha = this.opacityPct * 0.6;
      ctx.fillStyle = tint;
      ctx.fillRect(-iw / 2, -ih / 2, iw, ih);
      ctx.globalCompositeOperation = 'source-over';
    }
    ctx.restore();
  }

  private traceGarment(ctx: CanvasRenderingContext2D, w: number, h: number): void {
    // T-shirt silhouette (coincide con el clip-path del CSS).
    const p = (x: number, y: number) => [(-w / 2) + (x / 100) * w, (-h / 2) + (y / 100) * h];
    const pts: Array<[number, number]> = [
      [26, 0], [40, 6], [60, 6], [74, 0], [100, 0], [100, 18], [86, 24], [86, 78],
      [100, 84], [100, 100], [0, 100], [0, 84], [14, 78], [14, 24], [0, 18], [0, 0],
    ];
    ctx.beginPath();
    pts.forEach(([x, y], i) => {
      const [px, py] = p(x, y);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    });
    ctx.closePath();
  }

  private snapshot(canvas: HTMLCanvasElement): void {
    try {
      const url = canvas.toDataURL('image/png');
      this.ngZone.run(() => {
        this.shotUrl = url;
        this.capturing = false;
      });
    } catch (e) {
      this.ngZone.run(() => {
        this.capturing = false;
      });
      console.warn('captura:', e);
    }
  }

  // ----------------------------------------------------------------
  // Navegación / ciclo de vida
  // ----------------------------------------------------------------
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
    this.stopDetectorLoop();
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
    this.streaming = false;
  }

  ngOnDestroy(): void {
    this.stopCam();
    this.stopDetectorLoop();
  }
}