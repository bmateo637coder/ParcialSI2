"""Crea un índice local para las imágenes exportadas directamente por EA."""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = json.loads((HERE / 'modelo_fashionstore.json').read_text(encoding='utf-8'))
entries = ''.join(
    '<button class="case" data-id="{id}">{code} · {name}</button>'.format(
        id=c['id'], code=c['code'], name=html.escape(c['name']))
    for c in data['cases'])
page = r'''<!doctype html>
<html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FashionStore · Diagramas del parcial 2</title>
<style>
*{box-sizing:border-box}body{margin:0;font:15px Arial,sans-serif;color:#17283c;background:#f4f6fa}
header{padding:18px 24px;background:#17283c;color:white}header h1{font-size:21px;margin:0 0 5px}header p{margin:0;color:#ced9e6}
.layout{display:grid;grid-template-columns:300px minmax(0,1fr);min-height:calc(100vh - 85px)}
nav{padding:14px;background:white;border-right:1px solid #dbe2ec;max-height:calc(100vh - 85px);overflow:auto}
button,a{font:inherit}button{cursor:pointer;border:1px solid #d4deea;background:white;color:inherit;border-radius:6px;padding:9px 12px}
nav button{display:block;width:100%;text-align:left;margin:4px 0;font-size:13px;line-height:1.4}
button:hover{background:#edf3fc}button.active{background:#174e91;color:white;border-color:#174e91}
nav h2{font-size:13px;color:#62738a;margin:10px 0}main{padding:22px;min-width:0}main h2{font-size:21px;margin:0 0 14px}
.tabs{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:14px}.tools{display:flex;gap:14px;align-items:center;margin:10px 0 16px;font-size:13px}
a{color:#174e91}.canvas{overflow:auto;background:white;border:1px solid #dbe2ec;border-radius:8px;padding:12px;max-height:78vh}
.canvas img{display:block;max-width:100%;height:auto;margin:auto}.canvas.real img{max-width:none;margin:0}
.hint{color:#62738a;font-size:13px} @media(max-width:800px){.layout{grid-template-columns:1fr}nav{max-height:230px;border-bottom:1px solid #ddd}main{padding:12px}}
</style>
<header><h1>FashionStore · Parcial 2</h1><p>Casos de uso CU1–CU16: robustez, secuencias y clases</p></header>
<div class="layout"><nav><h2>DIAGRAMAS POR CASO DE USO</h2>CASE_ENTRIES
<h2>DIAGRAMAS GENERALES</h2>
<button class="general" data-key="Casos_de_uso">Casos de uso general</button>
<button class="general" data-key="Paquetes">Paquetes</button>
<button class="general" data-key="Modelo_dominio">Modelo de dominio</button>
<button class="general" data-key="Clases_general">Clases general</button></nav>
<main><h2 id="title"></h2><div class="tabs" id="tabs">
<button data-kind="Robustez">Robustez</button><button data-kind="Secuencia_principal">Secuencia principal</button>
<button data-kind="Secuencia_alternativa">Secuencia alternativa</button><button data-kind="Clases">Clases</button>
</div><div class="tools"><label><input id="size" type="checkbox"> Tamaño real</label>
<a id="open" target="_blank" rel="noopener">Abrir imagen completa</a></div>
<div class="canvas" id="canvas"><img id="diagram" alt="Diagrama seleccionado"></div>
<p class="hint">En Enterprise Architect: 02 Diagramas por caso de uso → carpeta del CU → diagrama. Las imágenes proceden de EA.</p>
</main></div>
<script>
const cases=CASE_DATA;let selected=1,kind='Robustez',general=null;
function render(){const item=cases.find(c=>c.id===selected);const path=general?'Generales/'+general+'.png':'CU'+selected+'/'+kind+'.png';
document.getElementById('title').textContent=general?document.querySelector('[data-key="'+general+'"]').textContent:item.code+' · '+item.name;
document.getElementById('diagram').src=path;document.getElementById('diagram').alt=document.getElementById('title').textContent+' — '+kind;
document.getElementById('open').href=path;document.getElementById('tabs').hidden=!!general;
document.querySelectorAll('.case').forEach(b=>b.classList.toggle('active',!general&&Number(b.dataset.id)===selected));
document.querySelectorAll('.general').forEach(b=>b.classList.toggle('active',b.dataset.key===general));
document.querySelectorAll('[data-kind]').forEach(b=>b.classList.toggle('active',b.dataset.kind===kind));}
document.querySelectorAll('.case').forEach(b=>b.onclick=()=>{selected=Number(b.dataset.id);general=null;render()});
document.querySelectorAll('[data-kind]').forEach(b=>b.onclick=()=>{kind=b.dataset.kind;render()});
document.querySelectorAll('.general').forEach(b=>b.onclick=()=>{general=b.dataset.key;render()});
document.getElementById('size').onchange=e=>document.getElementById('canvas').classList.toggle('real',e.target.checked);render();
</script></html>'''
page = page.replace('CASE_ENTRIES', entries).replace('CASE_DATA', json.dumps([
    {'id': c['id'], 'code': c['code'], 'name': c['name']} for c in data['cases']], ensure_ascii=False))
target = HERE / 'Diagramas_Ordenados' / 'index.html'
target.parent.mkdir(exist_ok=True)
target.write_text(page, encoding='utf-8')
print(target)
