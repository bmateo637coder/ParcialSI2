import { AfterViewInit, Component, ElementRef, NgZone, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService, Product } from './api.service';
import { alphaBounds, coverGeometry, removeEdgeBackground } from './garment-image';

@Component({
  selector: 'app-vestidor', standalone: true, imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <header class="fitting-head"><div><span class="eyebrow">Tu espacio para probar</span><h1>Vestidor virtual</h1><p>{{ product?.name || 'Prueba una prenda a tu manera' }}</p></div><a routerLink="/" class="btn btn-outline">Volver al catálogo</a></header>
    <div class="fitting-layout">
      <section class="preview-panel" aria-label="Vista previa del vestidor">
        <div class="preview-bar"><span class="mode-badge">{{ streaming ? 'Cámara en vivo' : 'Maniquí de referencia' }}</span><span>{{ autoFit && streaming ? 'Seguimiento activado' : 'Ajuste manual' }}</span></div>
        <div class="stage"><canvas #stage width="640" height="800" aria-label="Prenda sobre el cuerpo. Arrastra para moverla." (pointerdown)="startDrag($event)" (pointermove)="drag($event)" (pointerup)="stopDrag()" (pointercancel)="stopDrag()"></canvas>
          <p class="stage-empty" *ngIf="!garmentReady && !processing">Carga la imagen de una prenda para comenzar.</p><span class="processing" *ngIf="processing">Preparando la prenda…</span>
        </div>
        <video #video muted playsinline class="source-video"></video>
        <div class="preview-actions"><button class="btn btn-primary" (click)="startCamera()" [disabled]="starting || streaming">{{ starting ? 'Abriendo cámara…' : 'Usar mi cámara' }}</button><button class="btn btn-outline" (click)="useDemo()" [disabled]="!streaming && !starting">Usar maniquí</button><button class="btn btn-accent" (click)="capture()" [disabled]="!garmentReady || processing">Descargar foto</button></div>
        <p class="hint">Arrastra la prenda sobre la vista previa. La imagen se procesa en tu dispositivo; las capturas se descargan únicamente cuando tú lo indicas.</p>
        <p class="notice" role="status" *ngIf="cameraMessage">{{ cameraMessage }}</p>
      </section>
      <aside class="controls-panel">
        <section class="control-section"><span class="step">01</span><h2>Prepara la prenda</h2>
          <label class="upload-button" for="garment-upload">Cargar foto de una prenda<input id="garment-upload" type="file" accept="image/png,image/jpeg,image/webp" (change)="upload($event)"></label>
          <p class="hint">Mejor resultado: prenda sola sobre fondo liso o PNG transparente. Una foto sobre una persona necesita corrección manual.</p>
          <div class="editor checker"><canvas #editor width="480" height="480" aria-label="Editor de recorte de la prenda" (pointerdown)="editStart($event)" (pointermove)="editMove($event)" (pointerup)="editEnd($event)" (pointercancel)="cancelEdit()"></canvas></div>
          <div class="editor-tools" role="group" aria-label="Herramientas de recorte"><button *ngFor="let tool of tools" class="tool" [class.selected]="editTool === tool.id" [attr.aria-pressed]="editTool === tool.id" (click)="editTool = tool.id">{{ tool.label }}</button></div>
          <label class="range-label">Tamaño del pincel <span>{{ brush }} px</span><input type="range" min="4" max="90" [(ngModel)]="brush"></label>
          <label class="range-label">Tolerancia del fondo <span>{{ tolerance }}</span><input type="range" min="8" max="85" [(ngModel)]="tolerance"></label>
          <div class="button-row"><button class="btn btn-outline btn-sm" (click)="removeBackground()" [disabled]="!garmentReady">Quitar fondo</button><button class="btn btn-outline btn-sm" (click)="undo()" [disabled]="!undoStack.length">Deshacer</button><button class="btn btn-outline btn-sm" (click)="restoreOriginal()" [disabled]="!garmentReady">Original</button></div>
          <p class="hint">Borrar elimina restos del fondo; restaurar recupera partes de la foto original. Recortar conserva solo el rectángulo que dibujes. Quitar fondo vuelve a partir de la foto original.</p>
        </section>
        <section class="control-section"><span class="step">02</span><h2>Ajusta sobre el cuerpo</h2>
          <label class="range-label">Tipo de prenda<select class="form-control" [(ngModel)]="kind" (ngModelChange)="resetPosition()"><option value="top">Parte superior</option><option value="bottom">Pantalón o falda</option><option value="dress">Vestido o prenda completa</option></select></label>
          <label class="range-label">Tamaño visual <span>{{ scale }} %</span><input type="range" min="30" max="220" [(ngModel)]="scale"></label>
          <label class="range-label">Giro <span>{{ rotation }}°</span><input type="range" min="-90" max="90" [(ngModel)]="rotation"></label>
          <label class="range-label">Opacidad <span>{{ opacity }} %</span><input type="range" min="20" max="100" [(ngModel)]="opacity"></label>
          <label class="check-label"><input type="checkbox" [(ngModel)]="mirrorGarment"> Voltear la prenda horizontalmente</label>
          <label class="check-label"><input type="checkbox" [(ngModel)]="autoFit" (ngModelChange)="toggleTracking()" [disabled]="!streaming"> Seguir hombros y cadera</label>
          <button class="btn btn-outline btn-sm" (click)="resetPosition()">Centrar y restablecer ajuste</button>
          <p class="hint">El tamaño es una referencia visual. Revisa las medidas y la talla de la variante antes de comprar. El seguimiento corporal requiere internet.</p>
        </section>
        <p class="notice" role="alert" *ngIf="imageMessage">{{ imageMessage }}</p>
      </aside>
    </div>`,
  styles: [`
    :host{display:block;color:var(--text,#1e293b)}.fitting-head{display:flex;justify-content:space-between;align-items:center;gap:1rem;margin:1rem 0 1.5rem}.fitting-head h1{margin:.3rem 0;font-size:2rem}.fitting-head p{color:var(--muted)}
    .fitting-layout{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(300px,1fr);gap:1.5rem;align-items:start}.preview-panel{position:sticky;top:1rem;background:#fff;border:1px solid #e2e8f0;border-radius:20px;overflow:hidden}.preview-bar{padding:.9rem 1rem;display:flex;justify-content:space-between;gap:.5rem;font-size:.78rem;color:#64748b}.mode-badge{color:#16655b;background:#e0f1ec;border-radius:20px;padding:.25rem .65rem}.stage{position:relative;background:#eef2f6;display:flex;justify-content:center}.stage canvas{display:block;width:100%;max-height:68vh;object-fit:contain;touch-action:none;cursor:grab}.stage canvas:active{cursor:grabbing}.stage-empty,.processing{position:absolute;top:42%;left:12%;right:12%;text-align:center;padding:1rem;background:#ffffffed;border-radius:12px;color:#334155}.source-video{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none}.preview-actions{display:flex;gap:.5rem;flex-wrap:wrap;padding:1rem}.preview-panel>.hint,.preview-panel>.notice{margin:0 1rem 1rem}.controls-panel{display:grid;gap:1rem}.control-section{background:#fff;border:1px solid #e2e8f0;border-radius:18px;padding:1.2rem}.control-section h2{font-size:1.1rem;display:inline;margin-left:.5rem}.step{font-size:.8rem;border-radius:50%;padding:.4rem;background:#eef2f6;color:#64748b}.upload-button{display:block;margin:1.2rem 0 .6rem;border:1px dashed #9baebd;border-radius:10px;padding:.7rem;cursor:pointer;font-size:.9rem}.upload-button input{display:block;font-size:.75rem;max-width:100%;margin-top:.4rem}.hint{font-size:.78rem;line-height:1.6;color:#64748b;margin:.7rem 0}.editor{margin-top:.8rem;border:1px solid #cbd5e1;border-radius:10px;overflow:hidden;line-height:0}.checker{background-color:#fff;background-image:linear-gradient(45deg,#e5e7eb 25%,transparent 25%),linear-gradient(-45deg,#e5e7eb 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#e5e7eb 75%),linear-gradient(-45deg,transparent 75%,#e5e7eb 75%);background-size:20px 20px;background-position:0 0,0 10px,10px -10px,-10px 0}.editor canvas{width:100%;max-height:300px;object-fit:contain;touch-action:none;cursor:crosshair}.editor-tools,.button-row{display:flex;gap:.4rem;flex-wrap:wrap;margin-top:.65rem}.tool{background:#f8fafc;border:1px solid #cbd5e1;border-radius:8px;padding:.4rem .7rem;cursor:pointer;color:#334155}.tool.selected{background:#164e63;border-color:#164e63;color:white}.range-label{display:block;font-size:.82rem;margin:.9rem 0;color:#475569}.range-label span{float:right;font-variant-numeric:tabular-nums}.range-label input[type=range]{display:block;width:100%;margin-top:.4rem;accent-color:#16655b}.range-label select{margin-top:.5rem}.check-label{display:flex;gap:.6rem;align-items:center;font-size:.84rem;margin:1rem 0}.notice{background:#fff7e5;border:1px solid #f0d9a6;border-radius:10px;padding:.75rem;font-size:.84rem;color:#78551a}.btn:disabled{opacity:.5}
    @media(max-width:850px){.fitting-layout{grid-template-columns:1fr}.preview-panel{position:static}.stage canvas{max-height:60vh}.fitting-head{align-items:flex-start}.fitting-head h1{font-size:1.6rem}.preview-bar{font-size:.7rem}.controls-panel{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}}
  `]
})
export class VestidorComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('stage') stage!: ElementRef<HTMLCanvasElement>;
  @ViewChild('editor') editor!: ElementRef<HTMLCanvasElement>;
  @ViewChild('video') video!: ElementRef<HTMLVideoElement>;
  product: Product | null = null;
  garmentReady = false; processing = false; starting = false; streaming = false;
  cameraMessage = ''; imageMessage = ''; scale = 100; rotation = 0; opacity = 95;
  kind = 'top'; mirrorGarment = false; autoFit = false; tolerance = 32; brush = 28;
  editTool = 'erase'; tools = [{id:'erase',label:'Borrar'},{id:'restore',label:'Restaurar'},{id:'crop',label:'Recortar'}];
  undoStack: ImageData[] = [];
  private source = document.createElement('canvas');
  private masked = document.createElement('canvas');
  private garment = document.createElement('canvas');
  private stream: MediaStream | null = null;
  private disposed = false; private cameraGeneration = 0; private imageGeneration = 0;
  private raf = 0; private poseTimer = 0; private detector: any = null; private poseBusy = false;
  private offset = {x:0,y:0}; private anchor: {x:number;y:number;width:number}|null = null;
  private dragOrigin: {x:number;y:number;ox:number;oy:number}|null = null;
  private editOrigin: {x:number;y:number}|null = null;
  private editPrevious: {x:number;y:number}|null = null;
  private editRect = {x:0,y:0,width:480,height:480};
  private lastFrame = 0;
  private imageRevision = 0;
  private renderedState = '';
  constructor(private api: ApiService, private route: ActivatedRoute, private zone: NgZone) {}

  ngOnInit(): void {
    const product = history.state?.product as Product | undefined;
    const id = Number(this.route.snapshot.queryParamMap.get('producto'));
    if (product && (!id || product.id === id)) this.selectProduct(product);
    else if (Number.isInteger(id) && id > 0) this.api.getProduct(id).subscribe({
      next: p => { if (!this.disposed) this.selectProduct(p); }, error: () => { this.imageMessage = 'No se pudo cargar la prenda. Vuelve al catálogo o carga una imagen.'; }
    });
  }
  ngAfterViewInit(): void {
    this.zone.runOutsideAngular(() => { const loop = (time: number) => {
      if (this.disposed) return;
      if (time - this.lastFrame > 32) { this.render(); this.lastFrame = time; }
      this.raf = requestAnimationFrame(loop);
    }; this.raf = requestAnimationFrame(loop); });
  }
  ngOnDestroy(): void {
    this.disposed = true; this.imageGeneration++; this.useDemo(); cancelAnimationFrame(this.raf);
    const detector = this.detector; this.detector = null;
    if (detector) void Promise.resolve(detector.close()).catch(() => {});
  }
  private selectProduct(product: Product): void {
    this.product = product;
    const name = (product.category?.name ?? product.name).toLowerCase();
    this.kind = /pantal|falda|short|jean/.test(name) ? 'bottom' : /vestido|enterizo/.test(name) ? 'dress' : 'top';
    if (product.image_url) void this.loadImage(product.image_url);
  }
  upload(event: Event): void {
    const input = event.target as HTMLInputElement; const file = input.files?.[0];
    if (!file) return;
    if (!['image/png','image/jpeg','image/webp'].includes(file.type) || file.size > 10 * 1024 * 1024) { this.imageMessage = 'Usa una imagen PNG, JPEG o WebP de hasta 10 MB.'; input.value = ''; return; }
    const url = URL.createObjectURL(file);
    void this.loadImage(url).finally(() => URL.revokeObjectURL(url)); input.value = '';
  }
  private async loadImage(url: string): Promise<void> {
    const generation = ++this.imageGeneration; this.processing = true; this.imageMessage = '';
    try {
      const image = new Image(); image.crossOrigin = 'anonymous'; image.src = url;
      await image.decode();
      if (this.disposed || generation !== this.imageGeneration) return;
      const scale = Math.min(1, 800 / Math.max(image.width, image.height));
      const work = document.createElement('canvas'); work.width = Math.max(1, Math.round(image.width * scale)); work.height = Math.max(1, Math.round(image.height * scale));
      const ctx = work.getContext('2d', {willReadFrequently:true})!; ctx.drawImage(image, 0, 0, work.width, work.height);
      ctx.getImageData(0, 0, work.width, work.height);
      this.source = work; this.masked.width = work.width; this.masked.height = work.height;
      this.masked.getContext('2d')!.drawImage(work, 0, 0); this.undoStack = [];
      this.garmentReady = true; this.removeBackground(false); this.resetPosition();
    } catch {
      if (!this.disposed && generation === this.imageGeneration) this.imageMessage = 'No se pudo preparar esa imagen. Si el servidor de imágenes impide el acceso, descarga la foto y cárgala desde tu dispositivo.';
    } finally { if (!this.disposed && generation === this.imageGeneration) this.processing = false; }
  }
  private saveUndo(): void {
    this.undoStack = [...this.undoStack.slice(-4), this.masked.getContext('2d')!.getImageData(0, 0, this.masked.width, this.masked.height)];
  }
  removeBackground(save = true): void {
    if (!this.garmentReady) return;
    if (save) this.saveUndo();
    const data = this.source.getContext('2d')!.getImageData(0, 0, this.source.width, this.source.height);
    data.data.set(removeEdgeBackground(data.data, data.width, data.height, Number(this.tolerance)));
    this.masked.getContext('2d')!.putImageData(data, 0, 0); this.updateGarment();
  }
  restoreOriginal(): void { if (this.garmentReady) { this.saveUndo(); const ctx = this.masked.getContext('2d')!; ctx.clearRect(0,0,this.masked.width,this.masked.height); ctx.drawImage(this.source,0,0); this.updateGarment(); } }
  undo(): void { const last = this.undoStack.pop(); if (last) { this.masked.getContext('2d')!.putImageData(last,0,0); this.updateGarment(); } }
  private updateGarment(): void {
    this.imageRevision++;
    const data = this.masked.getContext('2d')!.getImageData(0,0,this.masked.width,this.masked.height);
    const bounds = alphaBounds(data.data, data.width, data.height);
    this.garment.width = bounds?.width ?? 1; this.garment.height = bounds?.height ?? 1;
    if (bounds) this.garment.getContext('2d')!.drawImage(this.masked,bounds.x,bounds.y,bounds.width,bounds.height,0,0,bounds.width,bounds.height);
    this.drawEditor();
  }
  private drawEditor(crop?: {x:number;y:number}): void {
    if (!this.editor) return;
    const c = this.editor.nativeElement, ctx = c.getContext('2d')!;
    ctx.clearRect(0,0,c.width,c.height);
    const scale = Math.min(460 / this.masked.width,460 / this.masked.height);
    this.editRect = {x:(480-this.masked.width*scale)/2,y:(480-this.masked.height*scale)/2,width:this.masked.width*scale,height:this.masked.height*scale};
    const r = this.editRect; ctx.drawImage(this.masked,r.x,r.y,r.width,r.height);
    if (crop && this.editOrigin) { ctx.strokeStyle='#0284c7'; ctx.lineWidth=2;ctx.setLineDash([7,4]);ctx.strokeRect(this.editOrigin.x,this.editOrigin.y,crop.x-this.editOrigin.x,crop.y-this.editOrigin.y);ctx.setLineDash([]); }
  }
  private point(event: PointerEvent, canvas: HTMLCanvasElement): {x:number;y:number} {
    const rect = canvas.getBoundingClientRect();
    const factor = Math.min(rect.width/canvas.width,rect.height/canvas.height);
    return {x:(event.clientX-rect.left-(rect.width-canvas.width*factor)/2)/factor,y:(event.clientY-rect.top-(rect.height-canvas.height*factor)/2)/factor};
  }
  editStart(event: PointerEvent): void {
    if (!this.garmentReady || this.processing) return;
    event.preventDefault(); this.editor.nativeElement.setPointerCapture(event.pointerId);
    this.saveUndo(); this.editOrigin = this.point(event,this.editor.nativeElement); this.editPrevious = null;
    if (this.editTool !== 'crop') this.paint(this.editOrigin);
  }
  editMove(event: PointerEvent): void {
    if (!this.editOrigin) return;
    const p = this.point(event,this.editor.nativeElement);
    if (this.editTool === 'crop') this.drawEditor(p); else this.paint(p);
  }
  editEnd(event: PointerEvent): void {
    if (!this.editOrigin) return;
    if (this.editTool === 'crop') {
      const p = this.point(event,this.editor.nativeElement), r = this.editRect;
      const x = Math.max(0,(Math.min(p.x,this.editOrigin.x)-r.x)*this.masked.width/r.width);
      const y = Math.max(0,(Math.min(p.y,this.editOrigin.y)-r.y)*this.masked.height/r.height);
      const right = Math.min(this.masked.width,(Math.max(p.x,this.editOrigin.x)-r.x)*this.masked.width/r.width);
      const bottom = Math.min(this.masked.height,(Math.max(p.y,this.editOrigin.y)-r.y)*this.masked.height/r.height);
      if (right-x > 5 && bottom-y > 5) {
        const ctx = this.masked.getContext('2d')!;
        ctx.clearRect(0,0,this.masked.width,y); ctx.clearRect(0,bottom,this.masked.width,this.masked.height-bottom);
        ctx.clearRect(0,0,x,this.masked.height); ctx.clearRect(right,0,this.masked.width-right,this.masked.height);
      }
    }
    this.editOrigin = null; this.editPrevious = null; this.updateGarment();
  }
  cancelEdit(): void { this.editOrigin=null;this.editPrevious=null;this.updateGarment(); }
  private paint(point: {x:number;y:number}): void {
    const r = this.editRect, factor = this.masked.width/r.width;
    const p = {x:(point.x-r.x)*factor,y:(point.y-r.y)*factor};
    const last = this.editPrevious ?? p;
    const radius = Number(this.brush)*factor/2;
    const count = Math.max(1,Math.ceil(Math.hypot(p.x-last.x,p.y-last.y)/Math.max(1,radius/2)));
    const ctx = this.masked.getContext('2d')!;
    for (let step=0;step<=count;step++) {
      ctx.save();ctx.beginPath();ctx.arc(last.x+(p.x-last.x)*step/count,last.y+(p.y-last.y)*step/count,radius,0,Math.PI*2);
      if (this.editTool === 'erase') { ctx.globalCompositeOperation='destination-out';ctx.fill(); }
      else { ctx.clip();ctx.drawImage(this.source,0,0); }
      ctx.restore();
    }
    this.editPrevious = p; this.updateGarment();
  }
  startDrag(event: PointerEvent): void {
    if (!this.garmentReady) return;
    event.preventDefault();this.stage.nativeElement.setPointerCapture(event.pointerId);
    const p=this.point(event,this.stage.nativeElement);this.dragOrigin={...p,ox:this.offset.x,oy:this.offset.y};
  }
  drag(event: PointerEvent): void {
    if (!this.dragOrigin) return;
    const p=this.point(event,this.stage.nativeElement), d=this.dragOrigin;
    this.offset={x:Math.max(-500,Math.min(500,d.ox+p.x-d.x)),y:Math.max(-650,Math.min(650,d.oy+p.y-d.y))};
  }
  stopDrag(): void { this.dragOrigin=null; }
  resetPosition(): void { this.scale=100;this.rotation=0;this.opacity=95;this.offset={x:0,y:0};this.anchor=null;this.mirrorGarment=false; }
  async startCamera(): Promise<void> {
    if (this.starting || this.streaming) return;
    const generation=++this.cameraGeneration;this.starting=true;this.cameraMessage='';
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error('unavailable');
      const stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user',width:{ideal:1280},height:{ideal:960}},audio:false});
      if (this.disposed || generation!==this.cameraGeneration) {stream.getTracks().forEach(t=>t.stop());return;}
      this.stream=stream;this.video.nativeElement.srcObject=stream;await this.video.nativeElement.play();
      if (this.disposed || generation!==this.cameraGeneration) {stream.getTracks().forEach(t=>t.stop());return;}
      this.streaming=true;this.resetPosition();
    } catch (error) {
      if (!this.disposed && generation===this.cameraGeneration) {this.useDemo();this.cameraMessage=(error as DOMException)?.name==='NotAllowedError'?'Permite el acceso a la cámara para usarla. Puedes continuar con el maniquí.':'No se pudo abrir la cámara. Usa localhost o HTTPS y comprueba que esté disponible.';}
    } finally {if (generation===this.cameraGeneration) this.starting=false;}
  }
  useDemo(): void {
    this.cameraGeneration++;this.starting=false;this.streaming=false;this.autoFit=false;this.anchor=null;
    clearTimeout(this.poseTimer);this.stream?.getTracks().forEach(t=>t.stop());this.stream=null;
    if(this.video) {this.video.nativeElement.pause();this.video.nativeElement.srcObject=null;}
  }
  async toggleTracking(): Promise<void> {
    clearTimeout(this.poseTimer);
    if (!this.autoFit || !this.streaming) {this.anchor=null;return;}
    try {
      if (!(window as any).Pose) await new Promise<void>((resolve,reject)=>{
        const script=document.createElement('script');script.src='https://cdn.jsdelivr.net/npm/@mediapipe/pose/pose.js';script.async=true;
        script.onload=()=>resolve();script.onerror=()=>reject(new Error('pose'));document.head.appendChild(script);
      });
      if(this.disposed || !this.streaming || !this.autoFit) return;
      if(!this.detector) {
        this.detector=new (window as any).Pose({locateFile:(file:string)=>'https://cdn.jsdelivr.net/npm/@mediapipe/pose/'+file});
        this.detector.setOptions({modelComplexity:0,smoothLandmarks:true,enableSegmentation:false,minDetectionConfidence:.6,minTrackingConfidence:.6});
        this.detector.onResults((result:any)=>this.onPose(result));await this.detector.initialize();
      }
      await this.track();
    } catch { if (!this.disposed) {this.autoFit=false;this.anchor=null;this.cameraMessage='El seguimiento no está disponible. Puedes ajustar la prenda arrastrando y usando los controles.';} }
  }
  private async track(): Promise<void> {
    if(this.disposed || !this.autoFit || !this.streaming || this.poseBusy || !this.detector) return;
    this.poseBusy=true;
    try {if(this.video.nativeElement.readyState>=2) await this.detector.send({image:this.video.nativeElement});}
    catch {this.zone.run(()=>{this.autoFit=false;this.anchor=null;this.cameraMessage='El seguimiento se interrumpió. Puedes continuar con el ajuste manual.';});}
    finally {this.poseBusy=false; if(!this.disposed && this.autoFit && this.streaming) this.zone.runOutsideAngular(()=>{this.poseTimer=window.setTimeout(()=>void this.track(),100);});}
  }
  private onPose(result:any): void {
    const landmarks=result?.poseLandmarks;
    if(!this.autoFit || !this.streaming || !landmarks) {this.anchor=null;return;}
    const left=landmarks[this.kind==='bottom'?23:11],right=landmarks[this.kind==='bottom'?24:12];
    if(!left || !right || (left.visibility??0)<.6 || (right.visibility??0)<.6) {this.anchor=null;return;}
    const video=this.video.nativeElement;const g=coverGeometry(video.videoWidth,video.videoHeight,640,800);
    const x=640-(((left.x+right.x)/2)*video.videoWidth*g.scale+g.x);
    const shoulderY=((left.y+right.y)/2)*video.videoHeight*g.scale+g.y;
    const width=Math.max(70,Math.min(600,Math.abs(left.x-right.x)*video.videoWidth*g.scale*(this.kind==='bottom'?1.3:1.65)));
    const y=shoulderY+(this.garment.height/Math.max(1,this.garment.width))*width*.42;
    const previous=this.anchor;
    this.anchor=previous?{x:previous.x*.75+x*.25,y:previous.y*.75+y*.25,width:previous.width*.75+width*.25}:{x,y,width};
  }
  private render(): void {
    const canvas=this.stage?.nativeElement;if(!canvas) return;
    const state=JSON.stringify([this.imageRevision,this.garmentReady,this.kind,this.scale,this.rotation,this.opacity,this.mirrorGarment,this.offset,this.anchor,this.streaming]);
    if (!this.streaming && state===this.renderedState) return;
    this.renderedState=state;
    const ctx=canvas.getContext('2d')!;ctx.clearRect(0,0,640,800);
    const gradient=ctx.createLinearGradient(0,0,0,800);gradient.addColorStop(0,'#eef3f8');gradient.addColorStop(1,'#dfe7ed');ctx.fillStyle=gradient;ctx.fillRect(0,0,640,800);
    const video=this.video?.nativeElement;
    if(this.streaming && video?.readyState>=2 && video.videoWidth) {
      const g=coverGeometry(video.videoWidth,video.videoHeight,640,800);ctx.save();ctx.translate(640,0);ctx.scale(-1,1);ctx.drawImage(video,g.x,g.y,video.videoWidth*g.scale,video.videoHeight*g.scale);ctx.restore();
    } else this.drawMannequin(ctx);
    if(!this.garmentReady) return;
    const width=(this.anchor?.width??(this.kind==='bottom'?190:300))*Number(this.scale)/100;
    const height=width*this.garment.height/Math.max(1,this.garment.width);
    const center=this.anchor??{x:320,y:this.kind==='bottom'?570:this.kind==='dress'?440:335};
    ctx.save();ctx.translate(center.x+this.offset.x,center.y+this.offset.y);ctx.rotate(Number(this.rotation)*Math.PI/180);ctx.scale(this.mirrorGarment?-1:1,1);ctx.globalAlpha=Number(this.opacity)/100;
    ctx.drawImage(this.garment,-width/2,-height/2,width,height);ctx.restore();
  }
  private drawMannequin(ctx:CanvasRenderingContext2D): void {
    ctx.fillStyle='#bfcdd6';ctx.strokeStyle='#a4b6c3';ctx.lineWidth=2;
    ctx.beginPath();ctx.ellipse(320,118,43,55,0,0,Math.PI*2);ctx.fill();ctx.stroke();
    const body=new Path2D('M300 168 L300 190 Q253 194 225 217 L179 385 Q174 404 190 410 Q205 414 212 394 L253 282 L267 409 L250 697 Q249 721 270 724 Q289 726 293 704 L320 482 L347 704 Q351 726 370 724 Q391 721 390 697 L373 409 L387 282 L428 394 Q435 414 450 410 Q466 404 461 385 L415 217 Q387 194 340 190 L340 168 Z');ctx.fill(body);ctx.stroke(body);
    ctx.setLineDash([5,7]);ctx.strokeStyle='#c7d3dc';ctx.beginPath();ctx.moveTo(110,214);ctx.lineTo(530,214);ctx.moveTo(110,427);ctx.lineTo(530,427);ctx.stroke();ctx.setLineDash([]);
    ctx.fillStyle='#71869a';ctx.font='13px sans-serif';ctx.textAlign='center';ctx.fillText('Referencia visual · ajusta según tu prenda',320,770);
  }
  capture(): void {
    if(!this.garmentReady || this.processing) return;
    this.render();this.stage.nativeElement.toBlob(blob=>{if(!blob) return;const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='fashionstore-vestidor.png';link.click();window.setTimeout(()=>URL.revokeObjectURL(url),1000);},'image/png');
  }
}
