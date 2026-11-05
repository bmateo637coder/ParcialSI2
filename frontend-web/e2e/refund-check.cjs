const assert=require('node:assert/strict');
const path=require('node:path');
const {chromium}=require(path.resolve(__dirname,'../../node_modules/playwright'));
const web=process.env.E2E_WEB_URL,api=process.env.E2E_API_URL;
if(!web||!api||new URL(api).hostname!=='127.0.0.1')throw new Error('Usa el ejecutor con una base temporal.');
(async()=>{
 const browser=await chromium.launch();const context=await browser.newContext();const page=await context.newPage();
 page.setDefaultTimeout(30000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 let loseRefund=true,loseStock=true;const refundRequests=[],stockRequests=[];
 await context.route(/https?:\/\/[^/]+\/api(?:\/|$)/,async route=>{
   const req=route.request(),url=new URL(req.url());
   const response=await route.fetch({url:api+url.pathname.slice(4)+url.search});
   if(req.method()==='POST' && /\/refunds$/.test(url.pathname)){
     refundRequests.push(req.postDataJSON());
     if(loseRefund && response.status()===201){loseRefund=false;return route.fulfill({status:503,contentType:'application/json',body:'{"detail":"Respuesta de reembolso perdida para prueba"}'});}
   }
   if(req.method()==='POST' && /\/restock$/.test(url.pathname)){
     stockRequests.push(req.postDataJSON());
     if(loseStock && response.status()===200){loseStock=false;return route.fulfill({status:503,contentType:'application/json',body:'{"detail":"Respuesta de recepción perdida para prueba"}'});}
   }
   return route.fulfill({response});
 });
 async function login(email,password){await page.goto(web+'/auth');await page.locator('input[name="loginEmail"]').fill(email);await page.locator('input[name="loginPassword"]').fill(password);await page.getByRole('button',{name:'Acceder a mi cuenta',exact:true}).click();await page.waitForURL(web+'/');}
 async function token(){return page.evaluate(()=>localStorage.getItem('token'));}
 async function read(url,t){const r=await fetch(api+url,{headers:{Authorization:'Bearer '+t}});assert.equal(r.status,200);return r.json();}
 try{
   await login('admin@fashionstore.com','admin123');const adminToken=await token();
   const availability=await read('/inventory/availability',adminToken);const item=availability[0];
   const saleResponse=await fetch(api+'/pos/sale',{method:'POST',headers:{Authorization:'Bearer '+adminToken,'Content-Type':'application/json'},body:JSON.stringify({branch_id:item.branch_id,items:[{variant_id:item.variant_id,quantity:3}],payment_method:'EFECTIVO'})});
   assert.equal(saleResponse.status,201);const sale=await saleResponse.json();
   await page.goto(web+'/reembolsos?pedido='+sale.id);
   await page.getByRole('combobox',{name:'Tipo de devolución',exact:true}).selectOption('items');
   await page.getByRole('spinbutton',{name:'Cantidad a devolver',exact:true}).fill('1');
   await page.getByRole('textbox',{name:'Motivo',exact:true}).fill('El cliente devuelve una de las tres prendas');
   await page.getByRole('checkbox',{name:'Recibí las prendas y están en condiciones de volver al inventario',exact:true}).check();
   await page.getByRole('button',{name:'Confirmar devolución de dinero',exact:true}).click();
   await page.locator('app-refunds > .error').filter({hasText:'Respuesta de reembolso perdida para prueba'}).waitFor();
   await page.getByRole('button',{name:'Confirmar devolución de dinero',exact:true}).click();
   await page.locator('app-refunds article .badge').filter({hasText:'COMPLETADO'}).waitFor();
   assert.equal(refundRequests[0].request_id,refundRequests[1].request_id);
   let current=await read('/orders/'+sale.id,adminToken);assert.equal(current.refunds.length,1);assert.equal(current.refunded_total,item.price);
   let stock=await read('/inventory/availability?branch_id='+item.branch_id,adminToken);assert.equal(stock.find(i=>i.variant_id===item.variant_id).available,item.available-2);
   await page.getByRole('combobox',{name:'Tipo de devolución',exact:true}).selectOption('full');
   await page.getByRole('textbox',{name:'Motivo',exact:true}).fill('Reembolso restante, prendas por recibir después');
   await page.getByRole('button',{name:'Confirmar devolución de dinero',exact:true}).click();
   await page.waitForFunction(()=>document.querySelectorAll('app-refunds article').length===2);
   await page.getByRole('spinbutton',{name:'Unidades recibidas posteriormente',exact:true}).fill('2');
   await page.getByRole('button',{name:'Recibí prendas aptas para inventario',exact:true}).click();
   await page.locator('app-refunds > .error').filter({hasText:'Respuesta de recepción perdida para prueba'}).waitFor();
   await page.getByRole('button',{name:'Recibí prendas aptas para inventario',exact:true}).click();
   await page.getByRole('button',{name:'Recibí prendas aptas para inventario',exact:true}).waitFor({state:'detached'});
   assert.equal(stockRequests[0].request_id,stockRequests[1].request_id);
   current=await read('/orders/'+sale.id,adminToken);assert.equal(current.refunded_total,sale.total);assert.equal(current.net_total,0);
   stock=await read('/inventory/availability?branch_id='+item.branch_id,adminToken);assert.equal(stock.find(i=>i.variant_id===item.variant_id).available,item.available);
   const dashboard=await read('/reports/dashboard?branch_id='+item.branch_id,adminToken);assert.equal(dashboard.kpis.total_sales,0);assert.equal(dashboard.kpis.gross_sales,dashboard.kpis.refund_amount);
   console.log('PASS: reembolso parcial y total, respuestas perdidas sin duplicados, recepción posterior sin otro pago, neto e inventario conciliados.');
   await page.getByRole('button',{name:'Salir',exact:true}).click();await login('cliente@fashionstore.com','cliente123');
   const customerToken=await token();
   const cart=await fetch(api+'/cart',{method:'POST',headers:{Authorization:'Bearer '+customerToken,'Content-Type':'application/json'},body:JSON.stringify({variant_id:item.variant_id,quantity:1})});assert.equal(cart.status,201);
   const checkout=await fetch(api+'/orders/checkout',{method:'POST',headers:{Authorization:'Bearer '+customerToken,'Content-Type':'application/json'},body:JSON.stringify({branch_id:item.branch_id,payment_method:'TARJETA'})});assert.equal(checkout.status,201);const customerOrder=await checkout.json();
   await page.goto(web+'/reembolsos?pedido='+customerOrder.id);
   await page.getByRole('textbox',{name:'Motivo',exact:true}).fill('El cliente solicita devolver su compra');
   await page.getByRole('button',{name:'Enviar solicitud al encargado',exact:true}).click();
   await page.locator('app-refunds article .badge').filter({hasText:'SOLICITADO'}).waitFor();
   assert.equal((await read('/orders/'+customerOrder.id,customerToken)).refunded_total,0);
   await page.getByRole('button',{name:'Salir',exact:true}).click();await login('admin@fashionstore.com','admin123');
   await page.goto(web+'/reembolsos?pedido='+customerOrder.id);
   await page.getByRole('checkbox',{name:'Recibí las prendas en condiciones de volver al inventario',exact:true}).check();
   await page.getByRole('button',{name:'Aprobar y devolver dinero',exact:true}).click();
   await page.locator('app-refunds article .badge').filter({hasText:'COMPLETADO'}).waitFor();
   const approved=await read('/orders/'+customerOrder.id,adminToken);assert.equal(approved.net_total,0);
   assert.deepEqual(errors,[]);console.log('PASS: solicitud del cliente, aprobación del encargado, comprobante y devolución al medio de pago.');
 }finally{await context.close();await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
