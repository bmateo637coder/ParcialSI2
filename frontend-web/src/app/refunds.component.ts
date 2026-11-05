import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { ApiService, Order, Refund, RefundInput } from './api.service';

@Component({selector:'app-refunds',standalone:true,imports:[CommonModule,FormsModule],template:`
  <div class="page-head"><span class="eyebrow">Devoluciones y saldo de la compra</span><h1>Reembolsos</h1>
  <p class="lead">{{ manager ? 'Revisa la compra y registra la devolución del dinero y de las prendas recibidas.' : 'Solicita la devolución de tu compra y consulta su estado.' }}</p></div>
  <p class="notice">Tarjetas y transferencias están en modo de simulación. Al confirmar un reembolso en efectivo, registra el dinero que realmente entregas al cliente.</p>
  <p role="alert" class="error" *ngIf="error">{{ error }}</p><p role="status" *ngIf="message">{{ message }}</p>
  <div class="refund-layout"><section class="card"><label>Compra<select class="form-control" [(ngModel)]="order" (ngModelChange)="select()" [disabled]="busy"><option [ngValue]="null">Selecciona una compra pagada</option><option *ngFor="let sale of orders" [ngValue]="sale">{{ sale.receipt_number }} · {{ sale.client_name }} · {{ sale.status }} · Neto Bs. {{ sale.net_total | number:'1.2-2' }}{{ sale.refund_pending ? ' · Devolución pendiente' : '' }}</option></select></label>
  <ng-container *ngIf="order"><div class="totals"><div>Cobros y cambios<strong>Bs. {{ order.collected_total | number:'1.2-2' }}</strong></div><div>Dinero devuelto<strong>Bs. {{ order.refunded_total | number:'1.2-2' }}</strong></div><div>Saldo neto<strong>Bs. {{ order.net_total | number:'1.2-2' }}</strong></div></div>
    <p *ngIf="order.refund_pending">Pendiente de devolver: <strong>Bs. {{ order.refund_pending | number:'1.2-2' }}</strong>. Este importe todavía no se resta de los cobros.</p>
    <form (ngSubmit)="submit()" *ngIf="canAct && !hasPending && order.returnable_items.length">
      <label>Tipo de devolución<select class="form-control" name="kind" [(ngModel)]="kind" (ngModelChange)="resetDraft()" [disabled]="busy"><option value="full">Devolución total del saldo restante</option><option value="items">Devolución de prendas seleccionadas</option><option value="amount">Ajuste de importe sin devolución de prendas</option></select></label>
      <div *ngIf="kind === 'items'" class="table-wrap"><table class="table"><thead><tr><th>Prenda</th><th>Restantes</th><th>Valor restante</th><th>A devolver</th></tr></thead><tbody><tr *ngFor="let lot of order.returnable_items"><td>{{ lot.product_name }} · {{ lot.size_name }} / {{ lot.color_name }}<small *ngIf="lot.key.startsWith('exchange:')">Prenda recibida por cambio</small></td><td>{{ lot.quantity }}</td><td>Bs. {{ lot.amount | number:'1.2-2' }}</td><td><input type="number" min="0" [max]="lot.quantity" step="1" [(ngModel)]="quantities[lot.key]" [name]="lot.key" [disabled]="busy" aria-label="Cantidad a devolver"></td></tr></tbody></table></div>
      <label *ngIf="kind === 'amount'">Importe a devolver (Bs.)<input class="form-control" type="number" min="0.01" step="0.01" name="amount" [(ngModel)]="amount" [disabled]="busy"></label>
      <label>Motivo<textarea class="form-control" name="reason" [(ngModel)]="reason" minlength="5" maxlength="500" rows="3" [disabled]="busy" placeholder="Explica el motivo de la devolución"></textarea></label>
      <label class="check" *ngIf="manager && kind !== 'amount' && order.stock_deducted"><input type="checkbox" name="restock" [(ngModel)]="restock" [disabled]="busy"> Recibí las prendas y están en condiciones de volver al inventario</label>
      <p *ngIf="manager && !restock">El reembolso por sí solo no aumenta el inventario. Puedes registrar una devolución posterior de prendas sin devolver dinero otra vez.</p>
      <p>Importe calculado: <strong>Bs. {{ estimated | number:'1.2-2' }}</strong></p>
      <button class="btn btn-primary" [disabled]="busy || reason.trim().length < 5">{{ busy ? 'Procesando…' : manager ? 'Confirmar devolución de dinero' : 'Enviar solicitud al encargado' }}</button>
    </form>
    <p *ngIf="hasPending">Resuelve la solicitud o el reembolso pendiente antes de iniciar otra devolución.</p>
  </ng-container></section>
  <section class="card" *ngIf="order"><h2>Historial de devoluciones</h2><p *ngIf="!order.refunds.length">Esta compra todavía no tiene devoluciones.</p>
    <article *ngFor="let refund of order.refunds" class="refund-record"><strong>{{ refund.receipt_number }} · Bs. {{ refund.amount | number:'1.2-2' }}</strong><p><span class="badge">{{ refund.status }}</span> · {{ refund.created_at | date:'dd/MM/yyyy HH:mm' }}</p><p>{{ refund.reason }}</p><p *ngIf="refund.reference">Referencia: {{ refund.reference }}</p><p *ngIf="refund.error" class="error">{{ refund.error }}</p>
    <p *ngFor="let payout of refund.payouts">{{ payout.method }}: Bs. {{ payout.amount | number:'1.2-2' }} {{ refund.status === 'COMPLETADO' ? 'devueltos' : 'por confirmar' }}</p>
    <p *ngIf="restocked(refund)">Prendas repuestas: {{ restocked(refund) }}</p>
    <div *ngIf="manager && order.stock_deducted && refund.status === 'COMPLETADO'"><div *ngFor="let item of refund.items"><ng-container *ngIf="item.pending_return"><p>Recepción posterior: {{ item.pending_return }} unidad(es) pendientes de reponer. No genera otro reembolso.</p><input type="number" min="1" [max]="item.pending_return" [(ngModel)]="returnQty[item.id]" aria-label="Unidades recibidas posteriormente"><button class="btn btn-outline btn-sm" [disabled]="busy" (click)="receive(refund,item.id)">Recibí prendas aptas para inventario</button></ng-container></div></div>
    <button *ngIf="manager && refund.status === 'PENDIENTE'" class="btn btn-outline" [disabled]="busy" (click)="retry(refund)">Reintentar devolución pendiente</button>
    <button *ngIf="!manager && refund.status === 'SOLICITADO'" class="btn btn-outline" [disabled]="busy" (click)="withdraw(refund)">Cancelar mi solicitud</button>
    <div *ngIf="manager && refund.status === 'SOLICITADO'"><label class="check" *ngIf="order.stock_deducted"><input type="checkbox" [(ngModel)]="approvalRestock[refund.id]"> Recibí las prendas en condiciones de volver al inventario</label><div class="actions"><button class="btn btn-primary" [disabled]="busy" (click)="decide(refund,true)">Aprobar y devolver dinero</button><button class="btn btn-outline" [disabled]="busy" (click)="decide(refund,false)">Rechazar solicitud</button></div></div></article>
  </section></div>`,styles:[`.refund-layout{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:1.2rem;align-items:start}label{display:block;margin-bottom:1rem}.totals{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0}.totals div{background:#f4f2ed;border-radius:10px;padding:.8rem;flex:1}.totals strong,small{display:block}.notice{background:#fff5db;padding:1rem;border-radius:12px;margin-bottom:1rem}.error{color:#b42318;overflow-wrap:anywhere}.check{display:flex;gap:.6rem;align-items:center;font-size:.85rem}.refund-record{padding:1rem 0;border-bottom:1px solid #ddd}.refund-record p{margin:.5rem 0}.refund-record strong{overflow-wrap:anywhere}.actions{display:flex;flex-wrap:wrap;gap:.5rem}.table-wrap{overflow:auto}.table input{max-width:75px}.card p{font-size:.88rem;line-height:1.6}@media(max-width:900px){.refund-layout{grid-template-columns:1fr}}`]})
export class RefundsComponent implements OnInit {
  orders:Order[]=[];order:Order|null=null;kind='full';reason='';amount:number|null=null;restock=false;
  quantities:Record<string,number>={};approvalRestock:Record<number,boolean>={};busy=false;error='';message='';
  returnQty:Record<number,number>={};private returnKeys:Record<string,string>={};
  private requestId='';private fingerprint='';
  private get retryStorage(){return 'refund-draft-'+(this.api.currentUser.value?.id||'none');}
  constructor(public api:ApiService,private route:ActivatedRoute){}
  get manager(){return ['Administrador','Encargado de Sucursal'].includes(this.api.currentUser.value?.role_name||'');}
  get canAct(){return this.manager || this.api.currentUser.value?.role_name==='Cliente';}
  get hasPending(){return this.order?.refunds.some(r=>['SOLICITADO','PENDIENTE'].includes(r.status))??false;}
  get estimated():number {
    if(!this.order) return 0;
    if(this.kind==='full') return this.order.net_total;
    if(this.kind==='amount') return Number(this.amount)||0;
    return this.order.returnable_items.reduce((sum,lot)=>sum+Math.round(lot.amount/Math.max(1,lot.quantity)*(this.quantities[lot.key]||0)*100),0)/100;
  }
  ngOnInit(){this.load();}
  load(){this.api.getOrders().subscribe({next:orders=>{this.orders=orders.filter(o=>!!o.payment?.paid_at);const id=Number(this.route.snapshot.queryParamMap.get('pedido'));this.order=this.orders.find(o=>o.id===(this.order?.id||id))||this.orders[0]||null;this.select();},error:e=>this.fail(e)});}
  select(){this.resetDraft();this.error='';this.message='';}
  resetDraft(){this.quantities={};this.amount=null;this.restock=false;this.requestId='';this.fingerprint='';}
  submit(){
    if(this.busy || !this.order || this.hasPending) return;
    if(!navigator.onLine){this.error='Necesitas conexión para confirmar o solicitar un reembolso.';return;}
    const items=this.kind==='items'?Object.entries(this.quantities).filter(([,q])=>q>0).map(([lot_key,quantity])=>({lot_key,quantity})):[];
    if(this.kind==='items' && !items.length){this.error='Selecciona al menos una unidad.';return;}
    if(items.some(i=>!Number.isInteger(i.quantity))){this.error='Las cantidades deben ser enteras.';return;}
    if(this.kind==='amount' && (!this.amount || this.amount<=0)){this.error='Ingresa un importe mayor que cero.';return;}
    const value={reason:this.reason.trim(),restock:this.manager && this.kind!=='amount' && this.restock,items,...(this.kind==='amount'?{amount:Number(this.amount)}:{})};
    const content=JSON.stringify({order:this.order.id,...value});
    if(this.fingerprint!==content || !this.requestId){let old:{content?:string;id?:string}={};try{old=JSON.parse(sessionStorage.getItem(this.retryStorage)||'{}');}catch{}this.fingerprint=content;this.requestId=old.content===content&&old.id?old.id:crypto.randomUUID();try{sessionStorage.setItem(this.retryStorage,JSON.stringify({content,id:this.requestId}));}catch{}}
    const payload:RefundInput={...value,request_id:this.requestId};this.busy=true;this.error='';
    this.api.refundOrder(this.order.id,payload,!this.manager).subscribe({next:order=>this.updated(order),error:e=>this.fail(e)});
  }
  retry(refund:Refund){if(this.busy || !this.order) return;this.busy=true;this.api.retryRefund(this.order.id,refund.id).subscribe({next:o=>this.updated(o),error:e=>this.fail(e)});}
  withdraw(refund:Refund){if(this.busy||!this.order)return;this.busy=true;this.api.withdrawRefund(this.order.id,refund.id).subscribe({next:o=>this.updated(o),error:e=>this.fail(e)});}
  decide(refund:Refund,approve:boolean){if(this.busy || !this.order) return;this.busy=true;this.api.decideRefund(this.order.id,refund.id,approve,!!this.approvalRestock[refund.id]).subscribe({next:o=>this.updated(o),error:e=>this.fail(e)});}
  restocked(refund:Refund){return refund.status==='COMPLETADO'?refund.items.reduce((sum,i)=>sum+i.restocked_quantity,0):0;}
  receive(refund:Refund,itemId:number){if(this.busy || !this.order) return;const qty=this.returnQty[itemId];if(!Number.isInteger(qty)||qty<1){this.error='Indica cuántas prendas recibiste.';return;}const key=this.order.id+':'+itemId+':'+qty;this.returnKeys[key]??=crypto.randomUUID();this.busy=true;this.api.restockRefund(this.order.id,refund.id,itemId,qty,this.returnKeys[key]).subscribe({next:o=>{delete this.returnKeys[key];this.returnQty[itemId]=0;this.updated(o);},error:e=>this.fail(e)});}
  private updated(order:Order){try{sessionStorage.removeItem(this.retryStorage);}catch{}this.order=order;this.orders=this.orders.map(o=>o.id===order.id?order:o);this.busy=false;this.resetDraft();this.reason='';this.error='';this.message='Operación registrada. Revisa el estado y el comprobante en el historial.';}
  private fail(e:any){this.busy=false;this.error=typeof e?.error?.detail==='string'?e.error.detail:'No se pudo confirmar la operación. Consulta el estado antes de repetirla.';}
}
