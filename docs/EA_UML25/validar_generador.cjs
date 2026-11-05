/* Verificación del generador sin abrir ni modificar un proyecto de EA.
   Simula colecciones COM que solo incorporan AddNew al llamar Update/Refresh. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const file = path.join(__dirname, 'FashionStore_UML25.js');
const source = fs.readFileSync(file, 'utf8');
// Node acepta palabras reservadas tras un punto; JScript de Windows las rechaza.
// Compilar el archivo completo con el motor real, sin acceder a un modelo de EA.
let nativeJScript=false;
if(process.platform==='win32') {
  const temp=fs.mkdtempSync(path.join(require('node:os').tmpdir(),'fashionstore-jscript-'));
  const probe=path.join(temp,'syntax.js');
  try {
    const stub='var Repository={GetTreeSelectedPackage:function(){WScript.Echo("JSCRIPT_SYNTAX_OK");WScript.Quit(0);}};var Session={Output:function(s){WScript.Echo(s);}};\n';
    fs.writeFileSync(probe,'\uFEFF'+stub+source.replace(/^\uFEFF/,''),'utf16le');
    const output=require('node:child_process').execFileSync('cscript.exe',['//Nologo','//E:JScript',probe],{encoding:'utf8',timeout:15000});
    assert(output.includes('JSCRIPT_SYNTAX_OK'),'Sintaxis aceptada por JScript de Windows');
    nativeJScript=true;
  } finally { if(fs.existsSync(probe)) fs.unlinkSync(probe);fs.rmdirSync(temp); }
}

class Collection {
  constructor(read, create) { this.read=read; this.create=create; this.snapshot=[]; }
  Refresh() { this.snapshot=this.read().slice(); }
  get Count() { return this.snapshot.length; }
  GetAt(index) { assert(index>=0 && index<this.Count); return this.snapshot[index]; }
  GetByName(name) { const found=this.snapshot.find(item=>item.Name===name); if (!found) throw Error('No encontrado: '+name); return found; }
  AddNew(name,type) { return this.create(name,type); }
}

function fixture() {
  let nextId=1;
  const model={ packages:[], elements:[], connectors:[], diagrams:[], output:[] };
  function base(name,type,commit) {
    let saved=false;
    return { Name:name, Type:type, Notes:'', Alias:'',
      Update() { if(!saved) { saved=true;commit(this); } return true; },
      GetLastError() { return 'Fallo simulado'; } };
  }
  function features(owner,property,kind) {
    owner['list_'+property]=[];
    owner[property]=new Collection(()=>owner['list_'+property],(name,type)=>{
      const result=base(name,type,item=>owner['list_'+property].push(item));
      if(kind==='method') features(result,'Parameters','parameter');
      if(kind==='tag') result.Value=type;
      return result;
    });
  }
  function element(name,type,packageId) {
    assert(['Package','Actor','Class','Boundary','Object','Constraint','UseCase','Note','Sequence'].includes(type),'Tipo de elemento válido: '+type);
    const result=base(name,type,item=>model.elements.push(item));
    Object.assign(result,{ElementID:nextId++,PackageID:packageId,ParentID:0,Stereotype:'',ClassifierID:0});
    features(result,'Attributes','attribute');features(result,'Methods','method');features(result,'TaggedValues','tag');
    result.Connectors=new Collection(()=>model.connectors.filter(c=>c.ClientID===result.ElementID || c.SupplierID===result.ElementID),(connectorName,connectorType)=>{
      assert(['Association','Generalization','UseCase','Dependency','Sequence'].includes(connectorType));
      const c=base(connectorName,connectorType,item=>model.connectors.push(item));
      Object.assign(c,{ClientID:result.ElementID,SupplierID:0,ConnectorID:nextId++,DiagramID:0});
      c.ClientEnd=base('','',()=>{});c.SupplierEnd=base('','',()=>{});
      return c;
    });
    return result;
  }
  function diagram(name,type,packageId) {
    assert(['Use Case','Logical','Analysis','Sequence','Package'].includes(type));
    const result=base(name,type,item=>model.diagrams.push(item));
    Object.assign(result,{DiagramID:nextId++,PackageID:packageId,ParentID:0,objects:[],links:[]});
    result.DiagramObjects=new Collection(()=>result.objects,()=>base('','',item=>result.objects.push(item)));
    result.DiagramLinks=new Collection(()=>result.links,()=>base('','',item=>result.links.push(item)));
    return result;
  }
  function pkg(name,parentId) {
    const result=base(name,'Package',item=>model.packages.push(item));
    result.PackageID=nextId++;result.ParentID=parentId;
    result.Element=element(name,'Package',parentId);result.Element.Update();
    result.Packages=new Collection(()=>model.packages.filter(p=>p.ParentID===result.PackageID),(n)=>pkg(n,result.PackageID));
    result.Elements=new Collection(()=>model.elements.filter(e=>e.PackageID===result.PackageID && e.Type!=='Package'),(n,t)=>element(n,t,result.PackageID));
    result.Diagrams=new Collection(()=>model.diagrams.filter(d=>d.PackageID===result.PackageID),(n,t)=>diagram(n,t,result.PackageID));
    return result;
  }
  const selected=pkg('Modelo del usuario',0);selected.Update();
  const repository={ EnableUIUpdates:true, BatchAppend:false,
    GetTreeSelectedPackage:()=>repository.selected,
    GetPackageByID:id=>model.packages.find(p=>p.PackageID===id),
    RefreshModelView:id=>assert(model.packages.some(p=>p.PackageID===id)),
    selected };
  const counts=()=>({packages:model.packages.length,elements:model.elements.length,connectors:model.connectors.length,diagrams:model.diagrams.length,
    placements:model.diagrams.reduce((n,d)=>n+d.objects.length,0),attributes:model.elements.reduce((n,e)=>n+e.list_Attributes.length,0),methods:model.elements.reduce((n,e)=>n+e.list_Methods.length,0),tags:model.elements.reduce((n,e)=>n+e.list_TaggedValues.length,0)});
  return {model,repository,counts};
}

function run(test,configure='') {
  const context={Repository:test.repository,Session:{Output:line=>test.model.output.push(line)}};
  const code=source.replace(/fsMain\(\);\s*$/,configure+'\nfsMain();');
  vm.runInNewContext(code,context,{timeout:30000});return context;
}

const test=fixture();
const ctx=run(test);
assert.equal(test.model.diagrams.length,89);
assert.equal(test.model.elements.filter(e=>e.Type==='UseCase').length,16);
assert.equal(test.model.diagrams.filter(d=>d.Type==='Sequence').length,32);
assert.equal(test.model.diagrams.filter(d=>d.Type==='Analysis').length,16);
assert.deepEqual(Array.from(ctx.FS_DATA.cases,c=>c.id),Array.from({length:16},(_,i)=>i+1));
assert(ctx.FS_DATA.cases.every(c=>c.code==='CU'+c.id));
assert.equal(ctx.FS_DATA.cases[0].name,'Gestionar empresas (tenants)');
assert.equal(ctx.FS_DATA.cases[15].name,'Entrenar y evaluar modelos de ML');
assert(ctx.FS_DATA.includes.concat(ctx.FS_DATA.extends).every(r=>r[0]>=1&&r[0]<=16&&r[1]>=1&&r[1]<=16));
assert(!/\bCU(?:0\d|1[7-9]|[2-9]\d)\b/.test(source),'Sin numeración antigua en el entregable');
assert.equal(test.repository.EnableUIUpdates,true);assert.equal(test.repository.BatchAppend,false);
for(const d of test.model.diagrams) {
  assert(d.objects.length>0,d.Name+' contiene elementos');
  assert.equal(new Set(d.objects.map(o=>o.ElementID)).size,d.objects.length,'Sin posiciones duplicadas: '+d.Name);
  assert.equal(new Set(d.links.map(o=>o.ConnectorID)).size,d.links.length,'Sin enlaces duplicados: '+d.Name);
  const visible=new Set(d.objects.map(o=>o.ElementID));
  for(const object of d.objects) { assert(object.Left<object.Right);assert(object.Top>=0?false:true);assert(object.Bottom<object.Top); }
  for(const link of d.links.filter(l=>!l.IsHidden)) {
    const c=test.model.connectors.find(item=>item.ConnectorID===link.ConnectorID);
    assert(visible.has(c.ClientID)&&visible.has(c.SupplierID),'Extremos visibles: '+d.Name);
  }
  if(d.Type==='Sequence') {
    const messages=test.model.connectors.filter(c=>c.Type==='Sequence'&&c.DiagramID===d.DiagramID);
    assert(messages.length>=5,d.Name+' tiene un flujo específico');
    const ordered=messages.slice().sort((a,b)=>a.SequenceNo-b.SequenceNo);
    assert.deepEqual(ordered.map(c=>c.SequenceNo),ordered.map((_,i)=>i+1));
    for(let i=1;i<ordered.length;i++) assert(ordered[i].StartPointY>ordered[i-1].StartPointY);
    assert.equal(d.ParentID,0,'Secuencia visible directamente en su paquete');
    assert(test.model.packages.some(p=>p.PackageID===d.PackageID && p.Element.Alias.startsWith('FS25_CASE_CU')));
  }
}
for(const c of test.model.connectors.filter(c=>c.Type==='UseCase')) {
  assert(['Includes','Extends'].includes(c.Subtype));
  assert.equal(c.Stereotype,c.Subtype==='Includes'?'include':'extend');
}
for(let id=1;id<=16;id++) {
  const pkg=test.model.packages.find(p=>p.Element.Alias==='FS25_CASE_CU'+id);
  assert(pkg,'Paquete individual CU'+id);
  const diagrams=test.model.diagrams.filter(d=>d.PackageID===pkg.PackageID);
  assert.equal(diagrams.length,4,'Robustez, dos secuencias y clases de CU'+id);
  assert(diagrams.some(d=>d.Name==='04 Clases - CU'+id));
  assert(diagrams.every(d=>d.ParentID===0));
}
const before=test.counts();
const root=test.model.packages.find(p=>p.Element.Alias==='FS25_ORGANIZADO_ROOT');
test.repository.selected=root;
const repeated=run(test);
assert.deepEqual(test.counts(),before,'Repetir desde el submodelo no duplica objetos ni anida otro modelo');
assert.deepEqual(JSON.parse(JSON.stringify(repeated.FS_STATS)),{paquetes:0,elementos:0,diagramas:0,conectores:0});

const partial=fixture();
run(partial,'FS_CONFIG.seccion="SECUENCIAS";FS_CONFIG.desdeCU=7;FS_CONFIG.hastaCU=10;FS_CONFIG.generarAlternativos=false;');
assert.equal(partial.model.diagrams.length,4,'Generación por rango y sección');
assert(partial.model.diagrams.every(d=>d.Type==='Sequence'));

const failed=fixture();
failed.repository.RefreshModelView=()=>{throw Error('Error COM simulado');};
assert.throws(()=>run(failed),/Error COM simulado/);
assert.equal(failed.repository.EnableUIUpdates,true);assert.equal(failed.repository.BatchAppend,false);
assert(failed.model.output.some(line=>line.startsWith('ERROR.')));
assert(!failed.model.output.some(line=>line.startsWith('TERMINADO.')));

const missing=fixture();missing.repository.selected=null;
assert.throws(()=>run(missing),/Selecciona primero/);
assert.equal(missing.model.diagrams.length,0);

// En EA el Model Root es un paquete válido que no tiene elemento asociado.
const modelRoot=fixture();modelRoot.repository.selected.Element=null;
run(modelRoot);
assert.equal(modelRoot.model.diagrams.length,89,'Generación desde Model Root con Element=null');

const collision=fixture();
const unrelated=collision.repository.selected.Packages.AddNew('FashionStore - Parcial 2 - Diagramas por CU','');
unrelated.Update();
const collisionBefore=collision.counts();
assert.throws(()=>run(collision),/no pertenece a este generador/);
assert.deepEqual(collision.counts(),collisionBefore,'No modificar un paquete ajeno con el mismo nombre');

const report={resultado:'OK',entorno:'Simulación de la API COM; no se ejecutó dentro de un repositorio de Enterprise Architect.',
  sintaxisJScriptWindows:nativeJScript,
  sha256:require('node:crypto').createHash('sha256').update(source).digest('hex'),
  diagramas:test.model.diagrams.length,casos:16,robustez:16,secuencias:32,modelo:before,
  comprobaciones:['sintaxis','numeración exclusiva CU1-CU16','colecciones COM con Refresh','referencias de entidades','reglas de robustez ICONIX','extremos y multiplicidades','orden de mensajes','repetición idempotente','rango parcial','restauración tras error','protección de paquetes ajenos']};
fs.writeFileSync(path.join(__dirname,'validacion_generador.json'),JSON.stringify(report,null,2)+'\n','utf8');
console.log(JSON.stringify(report,null,2));
