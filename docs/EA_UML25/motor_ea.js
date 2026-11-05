// Compatible con JScript clásico (ES3): sin npm, JSON.parse ni bibliotecas externas.
var FS_CONFIG = {
    seccion: "TODO", // TODO, CASOS, PAQUETES, DOMINIO, ROBUSTEZ, SECUENCIAS, CLASES
    desdeCU: 1,
    hastaCU: 16,
    generarAlternativos: true,
    reposicionarExistentes: false,
    nombreRaiz: "FashionStore - Parcial 2 - Diagramas por CU"
};
var FS_CACHE = {}, FS_DIAGRAMS = [], FS_MODEL = {}, FS_ACTORS = {}, FS_UC = {};
var FS_CONNECTOR_CACHE={}, FS_ATTRIBUTE_CACHE={}, FS_METHOD_CACHE={};
var FS_STATS = { paquetes:0, elementos:0, diagramas:0, conectores:0 };
var FS_MARK = "FashionStore.EA.UML25.CU1_16.v3";

function fsOut(text) { Session.Output(String(text)); }
function fsCheck(object, what) {
    if (!object.Update()) throw new Error(what + ": " + object.GetLastError());
}
function fsPackage(parent, name, key) {
    var collection = parent.Packages, p = null, i;
    collection.Refresh();
    for (i=0;i<collection.Count;i++) {
        var candidate=collection.GetAt(i);
        if (candidate.Name===name) { p=candidate; break; }
    }
    if (p) {
        if (String(p.Element.Alias)!==key) throw new Error("El paquete '"+name+"' no pertenece a este generador. Cambia nombreRaiz o selecciona otro paquete.");
        return p;
    }
    p=collection.AddNew(name,""); fsCheck(p,"Crear paquete "+name);
    p.Element.Alias=key; p.Element.Notes=FS_MARK+"\nSubmodelo generado para ICONIX / UML 2.5.1.";
    fsCheck(p.Element,"Identificar paquete"); FS_STATS.paquetes++; collection.Refresh();
    return p;
}
function fsCache(packageObject) {
    var key=String(packageObject.PackageID);
    if (!FS_CACHE[key]) {
        var index={}, c=packageObject.Elements; c.Refresh();
        for (var i=0;i<c.Count;i++) {
            var e=c.GetAt(i);
            if(e.Alias) index[String(e.Alias)]=e;
            else { var marker=/^FS25Key=([^\r\n]+)/m.exec(String(e.Notes||""));if(marker) index[marker[1]]=e; }
        }
        FS_CACHE[key]=index;
    }
    return FS_CACHE[key];
}
function fsElement(pkg, name, type, key, stereotype, notes) {
    var cache=fsCache(pkg), element=cache[key],instance=type==="Object" || type==="Sequence";
    if (element) {
        if(type==="Note" || type==="Constraint") { element.Name=name;element.Notes=notes||"";fsCheck(element,"Actualizar nota"); }
        else if(instance && element.Alias) { element.Alias="";element.Notes=FS_MARK+"\nFS25Key="+key+"\n"+(notes||"");fsCheck(element,"Identificar participante sin alias visible"); }
        return element;
    }
    element=pkg.Elements.AddNew(name,type);
    element.Alias=instance?"":key;
    if (stereotype) element.Stereotype=stereotype;
    element.Notes=((type==="Note" || type==="Constraint")?"":FS_MARK+"\n"+(instance?"FS25Key="+key+"\n":""))+(notes||"");
    fsCheck(element,"Crear elemento "+name);
    cache[key]=element; FS_STATS.elementos++;
    return element;
}
function fsTag(element,name,value) {
    var tags=element.TaggedValues, tag;
    tags.Refresh();
    try { tag=tags.GetByName(name); } catch(ignore) { tag=null; }
    if (!tag) tag=tags.AddNew(name,String(value));
    tag.Value=String(value); fsCheck(tag,"Guardar etiqueta "+name);
}
function fsAttribute(element,name,type,notes,derived) {
    var attributes=element.Attributes;
    var key=String(element.ElementID),known=FS_ATTRIBUTE_CACHE[key];
    if(!known) { known={};attributes.Refresh();for(var i=0;i<attributes.Count;i++) known[String(attributes.GetAt(i).Name)]=true;FS_ATTRIBUTE_CACHE[key]=known; }
    if(known[name]) return;
    var a=attributes.AddNew(name,type); a.Visibility="Public"; a.Notes=notes||"";
    if(derived) a.IsDerived=true;
    fsCheck(a,"Agregar atributo "+name);
    known[name]=true;
}
function fsMethod(element,signature,design) {
    var match=/^([^\(]+)\((.*)\)$/.exec(signature), name=match?match[1]:signature;
    var methods=element.Methods;
    var key=String(element.ElementID),known=FS_METHOD_CACHE[key];
    if(!known) { known={};methods.Refresh();for(var i=0;i<methods.Count;i++) known[String(methods.GetAt(i).Name)]=true;FS_METHOD_CACHE[key]=known; }
    if(known[name]) return;
    var m=methods.AddNew(name,"void"); m.Visibility="Public";
    m.Notes=design?"Responsabilidad de diseño derivada de un mensaje de secuencia. Firma: "+signature:"Operación/propiedad presente en el código.";
    fsCheck(m,"Crear operación "+name);
    known[name]=true;
    if(match && match[2]) {
        var params=match[2].split(",");
        for(var j=0;j<params.length;j++) {
            var pname=params[j].replace(/^\s+|\s+$/g,"");
            var parameter=m.Parameters.AddNew(pname,"Object"); fsCheck(parameter,"Parámetro "+pname);
        }
    }
}
function fsConnector(source,target,type,name,key,stereotype,notes) {
    var connectors=source.Connectors;
    var marker=FS_MARK+":"+key;
    var sourceKey=String(source.ElementID),index=FS_CONNECTOR_CACHE[sourceKey];
    if(!index) {
        index={};connectors.Refresh();
        for(var i=0;i<connectors.Count;i++) { var old=connectors.GetAt(i);if(Number(old.ClientID)===Number(source.ElementID)) index[String(old.Notes).split("\n")[0]]=old; }
        FS_CONNECTOR_CACHE[sourceKey]=index;
    }
    if(index[marker]) return index[marker];
    var c=connectors.AddNew(name||"",type); c.SupplierID=target.ElementID;
    if(stereotype) c.Stereotype=stereotype;
    if(type==="UseCase") c.Subtype=stereotype==="include"?"Includes":"Extends";
    if(type!=="Association") c.Direction="Source -> Destination";
    c.Notes=marker+"\n"+(notes||"");
    fsCheck(c,"Crear relación "+key); index[marker]=c;FS_STATS.conectores++;
    return c;
}
function fsDiagram(pkg,name,type,notes,parentID) {
    var diagrams=pkg.Diagrams, d=null; diagrams.Refresh();
    for(var i=0;i<diagrams.Count;i++) { var item=diagrams.GetAt(i); if(item.Name===name) { d=item; break; } }
    if(!d) {
        d=diagrams.AddNew(name,type); d.Notes=FS_MARK+"\n"+notes;
        if(parentID) d.ParentID=parentID;
        fsCheck(d,"Crear diagrama "+name); diagrams.Refresh(); FS_STATS.diagramas++;
    }
    // Los diagramas deben ser hijos directos del paquete que los contiene.
    // ParentID de un CU en otro paquete los oculta/reubica en el Browser de EA.
    d.ParentID=0;
    d.HighlightImports=false;
    d.ExtendedStyle="HideRel=0;HideParents=1;UseAlias=0;ShowSN=0;HideProps=1;HideAtts=0;HideOps=0;HideStereo=0;HideEStereo=0;ShowTags=0;ShowReqs=0;ShowCons=0;OpParams=1;ShowIcons="+(type==="Analysis"?"1":"0")+";";
    d.StyleEx="HideQuals=1;ShowNotes=0;SuppConnectorLabels=0;m_bElementClassifier=0;ShowOpRetType=0;";
    fsCheck(d,"Actualizar diagrama "+name);
    var view={ diagram:d, elements:{}, positions:{}, allowed:{}, links:[], package:pkg, objectIndex:{} };
    d.DiagramObjects.Refresh();
    for(var v=0;v<d.DiagramObjects.Count;v++) { var placed=d.DiagramObjects.GetAt(v);view.objectIndex[String(placed.ElementID)]=placed; }
    FS_DIAGRAMS.push(view);
    return view;
}
function fsPlace(view,element,x,y,w,h,kind) {
    var objects=view.diagram.DiagramObjects, obj=view.objectIndex[String(element.ElementID)], existing=!!obj;
    if(!obj) { obj=objects.AddNew("l="+x+";r="+(x+w)+";t="+(-y)+";b="+(-y-h)+";",""); obj.ElementID=element.ElementID; }
    if(!existing || FS_CONFIG.reposicionarExistentes) {
        obj.Left=x;obj.Right=x+w;obj.Top=-y;obj.Bottom=-y-h;
        obj.Sequence=kind==="frame"?100:kind==="package"?60:10;
    }
    if(!existing) {
        if(kind==="class") { obj.ShowPublicAttributes=true;obj.ShowPublicOperations=true; }
        if(kind==="domain") { obj.ShowPublicAttributes=true;obj.ShowPublicOperations=false; }
        obj.ShowNotes=false; obj.ShowTags=false;
        if(kind==="control") obj.BackgroundColor=15794148;
        if(kind==="entity" || kind==="domain") obj.BackgroundColor=16512232;
        if(kind==="boundary") obj.BackgroundColor=14811125;
    }
    obj.FontName="Arial";obj.FontSize=9;obj.FontBold=false;obj.ElementDisplayMode=2;
    fsCheck(obj,"Situar "+element.Name);
    view.objectIndex[String(element.ElementID)]=obj;
    view.elements[String(element.ElementID)]=element;
    view.positions[String(element.ElementID)]={x:x,y:y,w:w,h:h};
    return obj;
}
function fsAllow(view,connector) {
    view.allowed[String(connector.ConnectorID)]=true;
    view.links.push(connector);
}
function fsFinish(view) {
    // Ocultar relaciones del modelo que no pertenecen a esta vista concreta.
    var diagram=view.diagram, links=diagram.DiagramLinks, known={}, i,key;
    links.Refresh();
    for(i=0;i<links.Count;i++) { var l=links.GetAt(i);known[String(l.ConnectorID)]=l; }
    var considered={};
    for(key in view.elements) {
        var connections=view.elements[key].Connectors;
        connections.Refresh();
        for(i=0;i<connections.Count;i++) {
            var c=connections.GetAt(i), id=String(c.ConnectorID);
            if(considered[id] || !view.elements[String(c.ClientID)] || !view.elements[String(c.SupplierID)]) continue;
            considered[id]=true;
            var link=known[id];
            if(!link) { link=links.AddNew("","");link.ConnectorID=c.ConnectorID; }
            link.IsHidden=!view.allowed[id];
            if(c.Type!=="Sequence") link.LineStyle=(diagram.Type==="Use Case" || diagram.Type==="Analysis")?1:2;
            fsCheck(link,"Visibilidad de relación en "+diagram.Name);
        }
    }
    fsCheck(diagram,"Guardar diagrama "+diagram.Name);
}
function fsArrayHas(array,item) { for(var i=0;i<array.length;i++) if(array[i]===item) return true;return false; }
function fsSection(section) { return FS_CONFIG.seccion==="TODO" || FS_CONFIG.seccion===section; }
function fsCaseSelected(c) { return c.id>=FS_CONFIG.desdeCU && c.id<=FS_CONFIG.hastaCU; }
function fsCaseNotes(c) {
    return c.code+" - "+c.name+"\nRequisitos: "+c.rf+"\nActor principal: "+c.actors[0]+"\nFuente: "+c.source+
      "\nEscenario alternativo: ["+c.guard+"]\n"+c.note+
      "\nLas operaciones de los controles son responsabilidades de diseño, realizables por módulos y funciones del código.";
}
function fsReference(ref,c) {
    if(ref==="c" || ref==="!") return {key:"control:"+c.control,name:c.control,kind:"control",package:c.package};
    if(ref==="b") return {key:"boundary:"+c.ui,name:c.ui,kind:"boundary",package:c.package};
    if(ref==="a") return {key:"actor:"+c.actors[0],name:c.actors[0],kind:"actor",actor:c.actors[0]};
    if(ref.charAt(0)==="@") return {key:"control:"+ref.substring(1),name:ref.substring(1),kind:"control",package:c.package};
    if(ref.charAt(0)==="#") return {key:"boundary:"+ref.substring(1),name:ref.substring(1),kind:"boundary",package:c.package};
    if(!FS_MODEL[ref]) throw new Error("Entidad desconocida en "+c.code+": "+ref);
    return {key:"entity:"+ref,name:FS_MODEL[ref].Name,kind:"entity",model:ref,package:c.package};
}
function fsMessages(c,alternate) {
    var result=[{from:fsReference("a",c),to:fsReference("b",c),name:"solicitar"+c.code+"()"},
        {from:fsReference("b",c),to:fsReference("c",c),name:"ejecutar"+c.code+"(datos)"}];
    var steps=alternate?c.alternate:c.steps;
    for(var i=0;i<steps.length;i++) {
        var index=steps[i].indexOf(":"), route=steps[i].substring(0,index), op=steps[i].substring(index+1);
        var ends=route.split(">");
        result.push({from:fsReference(ends.length===2?ends[0]:"c",c),to:fsReference(ends.length===2?ends[1]:ends[0],c),name:op});
    }
    result.push({from:fsReference("c",c),to:fsReference("b",c),name:alternate?"mostrarMotivoYAccionPermitida()":"mostrarResultadoDelCaso()"});
    return result;
}
var FS_DESIGN={}, FS_DESIGN_PACKAGES={};
var FS_COMMON_GROUPS={PlanGuard:"P6",TenantGuard:"P6",AutorizacionControl:"P1",InventarioControl:"P4",PagoControl:"P4",PagoSimuladoControl:"P4",SyncServidorControl:"P7",ModelosMLControl:"P8",InterpreteReporteControl:"P8"};
function fsClassifier(ref,c,classesRoot) {
    if(ref.kind==="actor") return FS_ACTORS[ref.actor];
    if(ref.kind==="entity") return FS_MODEL[ref.model];
    if(FS_DESIGN[ref.key]) return FS_DESIGN[ref.key];
    var pkg=FS_DESIGN_PACKAGES[FS_COMMON_GROUPS[ref.name]||ref.package];
    var cls=fsElement(pkg,ref.name,"Class","FS25_DESIGN_"+ref.key,ref.kind,
      "Responsabilidad lógica de diseño. Trazada desde "+c.code+".\nMódulos/funciones relacionados: "+c.source);
    FS_DESIGN[ref.key]=cls;
    return cls;
}
function fsCreateFoundation(root) {
    var generalRoot=fsPackage(root,"01 Diagramas generales","FS25_GENERALES");
    var casesRoot=fsPackage(root,"02 Diagramas por caso de uso","FS25_CASES");
    var sharedRoot=fsPackage(root,"03 Elementos compartidos","FS25_SHARED");
    var supportRoot=fsPackage(root,"04 Vistas de apoyo","FS25_SUPPORT");
    var ucRoot=fsPackage(sharedRoot,"Casos de uso y actores","FS25_UCROOT");
    var actorPkg=fsPackage(ucRoot,"Actores","FS25_ACTORS");
    var classesRoot=fsPackage(sharedRoot,"Clases de diseno","FS25_CLASSES");
    var ucPackages={}, modelPackages={},casePackages={},objectPackages={};
    for(var g=0;g<FS_DATA.packages.length;g++) {
        var group=FS_DATA.packages[g];
        ucPackages[group[0]]=fsPackage(ucRoot,group[0]+" - "+group[1],"FS25_UCPKG_"+group[0]);
        modelPackages[group[0]]=fsPackage(classesRoot,group[0]+" - "+group[1],"FS25_CLASS_PKG_"+group[0]);
        FS_DESIGN_PACKAGES[group[0]]=modelPackages[group[0]];
    }
    for(var a=0;a<FS_DATA.actors.length;a++) {
        var actor=FS_DATA.actors[a];
        var e=fsElement(actorPkg,actor[1],"Actor","FS25_ACTOR_"+actor[0],"",actor[0]==="PagoExterno"?"Contrato externo previsto; el pago ejecutado actualmente es simulado.":actor[0]==="IAExterna"?"Integración opcional; la plataforma dispone de alternativas locales.":"Actor externo al sujeto FashionStore.");
        e.Abstract=actor[2]?"1":"0";fsCheck(e,"Actor "+actor[1]); FS_ACTORS[actor[0]]=e;
    }
    for(var m=0;m<FS_DATA.models.length;m++) {
        var spec=FS_DATA.models[m];
        var model=fsElement(modelPackages[spec.package],spec.name,"Class","FS25_CLASS_"+spec.key,"entity",
            "Clase del modelo: "+spec.key+"\nTabla: "+(spec.table||"concepto de persistencia local")+"\nFuente: "+spec.source);
        FS_MODEL[spec.key]=model; fsTag(model,"Codigo",spec.key);fsTag(model,"Fuente",spec.source);
        for(var f=0;f<spec.attributes.length;f++) {
            var attr=spec.attributes[f];
            fsAttribute(model,attr.name,attr.type,(attr.pk?"Identificador. ":"")+(attr.fk?"Referencia: "+attr.fk+". ":"")+(attr.nullable?"Opcional en el esquema. ":"")+(attr.unique?"Único. ":"")+(attr.derived?"Propiedad calculada del modelo Python. ":""),attr.derived);
        }
        for(var p=0;p<spec.methods.length;p++) fsMethod(model,spec.methods[p]+"()",false);
    }
    fsOut("Entidades y atributos de implementación preparados: "+FS_DATA.models.length+".");
    for(var u=0;u<FS_DATA.cases.length;u++) {
        var c=FS_DATA.cases[u];
        casePackages[String(c.id)]=fsPackage(casesRoot,(c.id<10?"0":"")+c.id+" - "+c.code+" - "+c.name,"FS25_CASE_"+c.code);
        objectPackages[String(c.id)]=fsPackage(casePackages[String(c.id)],"Elementos de los diagramas","FS25_CASE_OBJECTS_"+c.code);
        var useCase=fsElement(ucPackages[c.package],c.code+" - "+c.name,"UseCase","FS25_"+c.code,"",fsCaseNotes(c));
        FS_UC[String(c.id)]=useCase;fsTag(useCase,"RF",c.rf);fsTag(useCase,"Fuente",c.source);
        fsTag(useCase,"NumeroEnDocumento",String(c.id));
        var messages=fsMessages(c,false).concat(fsMessages(c,true));
        for(var k=0;k<messages.length;k++) {
            fsClassifier(messages[k].from,c,classesRoot);
            var target=fsClassifier(messages[k].to,c,classesRoot);
            if(messages[k].to.kind!=="actor") fsMethod(target,messages[k].name,true);
        }
        if(c.id%10===0 || c.id===16) fsOut("Referencias de diseño preparadas hasta "+c.code+".");
    }
    return {ucRoot:ucRoot,ucPackages:ucPackages,classesRoot:classesRoot,modelPackages:modelPackages,generalRoot:generalRoot,supportRoot:supportRoot,sharedRoot:sharedRoot,casesRoot:casesRoot,casePackages:casePackages,objectPackages:objectPackages};
}
var FS_UC_REL=[];
function fsUseCaseRelations() {
    var i,j,c,a,source,target;
    for(i=0;i<FS_DATA.generalizations.length;i++) {
        var g=FS_DATA.generalizations[i];
        FS_UC_REL.push(fsConnector(FS_ACTORS[g[0]],FS_ACTORS[g[1]],"Generalization","","ACTOR_"+g.join("_"),"","La flecha apunta al actor general."));
    }
    for(i=0;i<FS_DATA.cases.length;i++) {
        c=FS_DATA.cases[i];
        if(c.id===4) continue;
        for(j=0;j<c.actors.length;j++) {
            a=c.actors[j];
            FS_UC_REL.push(fsConnector(FS_ACTORS[a],FS_UC[String(c.id)],"Association","","ACTOR_UC_"+a+"_"+c.id,"","Participación; los permisos se detallan en las notas del caso."));
        }
    }
    for(i=0;i<FS_DATA.includes.length;i++) {
        var inc=FS_DATA.includes[i];source=FS_UC[String(inc[0])];target=FS_UC[String(inc[1])];
        FS_UC_REL.push(fsConnector(source,target,"UseCase","","INCLUDE_"+inc.join("_"),"include","Dependencia desde caso base hacia comportamiento incluido."));
    }
    for(i=0;i<FS_DATA["extends"].length;i++) {
        var ext=FS_DATA["extends"][i];source=FS_UC[String(ext[0])];target=FS_UC[String(ext[1])];
        c=fsConnector(source,target,"UseCase","","EXTEND_"+ext[0]+"_"+ext[1],"extend","Condición: ["+ext[2]+"]. Flecha hacia el caso base.");
        c.TransitionGuard=ext[2];fsCheck(c,"Guarda extend");FS_UC_REL.push(c);
    }
    var optional=[["IAExterna",13]];
    for(i=0;i<optional.length;i++) FS_UC_REL.push(fsConnector(FS_ACTORS[optional[i][0]],FS_UC[String(optional[i][1])],"Association","opcional / contrato","EXTERNAL_"+optional[i].join("_"),"","No acredita una integración activa en la implementación actual."));
}
function fsUseCaseViews(root,foundation) {
    fsUseCaseRelations();
    var groups=[],seenGroups={};
    for(var n=0;n<FS_DATA.cases.length;n++) {
        var packageId=FS_DATA.cases[n].package;
        if(seenGroups[packageId]) continue;
        seenGroups[packageId]=true;
        for(var p=0;p<FS_DATA.packages.length;p++) if(FS_DATA.packages[p][0]===packageId) groups.push(FS_DATA.packages[p]);
    }
    var view=fsDiagram(foundation.generalRoot,"01 Casos de uso - General","Use Case","Vista general de objetivos CU1-CU16. Personal de empresa es un actor general: cada CU conserva sus restricciones de rol. Las relaciones include/extend y actores concretos se muestran en las cuatro vistas por módulo de 04 Vistas de apoyo.");
    var frame=fsElement(foundation.ucRoot,"FashionStore - Segundo parcial","Boundary","FS25_SYSTEM","","Sujeto del modelo; actores fuera del límite del sistema.");
    fsPlace(view,frame,220,180,1140,1390,"frame");
    var platform=[1,2,3,16];
    for(var j=0;j<platform.length;j++) fsPlace(view,FS_UC[String(platform[j])],300,250+j*165,330,90,"usecase");
    for(j=5;j<=15;j++) fsPlace(view,FS_UC[String(j)],900,250+(j-5)*115,330,90,"usecase");
    fsPlace(view,FS_UC["4"],300,1080,330,90,"usecase");
    fsPlace(view,FS_ACTORS.AdminPlataforma,20,465,150,115,"actor");
    fsPlace(view,FS_ACTORS.Empleado,1430,805,150,115,"actor");
    fsPlace(view,FS_ACTORS.IAExterna,715,25,150,115,"actor");
    for(var i=0;i<FS_DATA.cases.length;i++) {
        var c=FS_DATA.cases[i],actor=null;
        if(c.id<=3 || c.id===16) actor=FS_ACTORS.AdminPlataforma;
        else if(c.id>=5 && c.id<=15) actor=FS_ACTORS.Empleado;
        if(actor) fsAllow(view,fsConnector(actor,FS_UC[String(c.id)],"Association","","GENERAL_ACTOR_"+c.code,"","Participación resumida. Aplican los actores concretos y permisos de las notas del CU; administrador de empresa, encargado y cajero no son intercambiables."));
    }
    fsAllow(view,fsConnector(FS_ACTORS.IAExterna,FS_UC["13"],"Association","opcional","GENERAL_IA_CU13","","Proveedor externo opcional de interpretación."));
    var legend=fsElement(foundation.ucRoot,"CU4: comportamiento incluido. Roles concretos e include/extend: vistas por modulo.","Note","FS25_GENERAL_LEGEND","","Personal de empresa agrupa Administrador de empresa, Encargado y Cajero. Los permisos concretos se detallan en cada caso. CU4 se ejecuta como comportamiento incluido.");
    fsPlace(view,legend,300,1280,390,100,"note");
    fsFinish(view);
    for(var g=0;g<groups.length;g++) {
        var group=groups[g];
        var detail=fsDiagram(foundation.supportRoot,"Casos de uso - "+group[1],"Use Case","Detalle del paquete "+group[0]+". Actores concretos y relaciones include/extend.");
        var core={},extra={},actors={},list=[];
        for(j=0;j<FS_DATA.cases.length;j++) if(FS_DATA.cases[j].package===group[0]) { var selected=FS_DATA.cases[j];core[String(selected.id)]=true;list.push(selected);for(a=0;a<selected.actors.length;a++) actors[selected.actors[a]]=true; }
        var box=fsElement(foundation.ucPackages[group[0]],group[0]+" - "+group[1],"Boundary","FS25_BOX_"+group[0],"","Límite del paquete funcional.");
        fsPlace(detail,box,280,20,760,Math.max(410,Math.ceil(list.length/2)*125+100),"frame");
        for(j=0;j<list.length;j++) fsPlace(detail,FS_UC[String(list[j].id)],310+(j%2)*365,90+Math.floor(j/2)*125,330,85,"usecase");
        for(var r=0;r<FS_UC_REL.length;r++) {
            var rel=FS_UC_REL[r],sourceUC=null,targetUC=null;
            for(var id in FS_UC) { if(Number(FS_UC[id].ElementID)===Number(rel.ClientID)) sourceUC=id;if(Number(FS_UC[id].ElementID)===Number(rel.SupplierID)) targetUC=id; }
            if((sourceUC && core[sourceUC]) || (targetUC && core[targetUC])) {
                if(sourceUC && !core[sourceUC]) extra[sourceUC]=true;
                if(targetUC && !core[targetUC]) extra[targetUC]=true;
                for(var aid in FS_ACTORS) if(Number(FS_ACTORS[aid].ElementID)===Number(rel.ClientID)) actors[aid]=true;
                fsAllow(detail,rel);
            }
        }
        var row=0;for(var key in actors) { fsPlace(detail,FS_ACTORS[key],20,40+row*125,200,100,"actor");row++; }
        row=0;for(key in extra) { fsPlace(detail,FS_UC[key],1110,65+row*115,330,85,"usecase");row++; }
        fsFinish(detail);
    }
}
function fsPackageView(root,foundation) {
    var pkg=foundation.generalRoot,view=fsDiagram(pkg,"02 Paquetes - Arquitectura funcional","Package","Paquetes UML y dependencias dirigidas del consumidor hacia el proveedor. P5 conserva reportes/recomendación heredados; P8 agrupa los nuevos CU de IA y ML.");
    for(var i=0;i<FS_DATA.packages.length;i++) {
        var p=FS_DATA.packages[i][0];fsPlace(view,foundation.ucPackages[p].Element,40+(i%4)*370,55+Math.floor(i/4)*280,315,150,"package");
    }
    for(i=0;i<FS_DATA.packageDependencies.length;i++) { var dep=FS_DATA.packageDependencies[i];fsAllow(view,fsConnector(foundation.ucPackages[dep[0]].Element,foundation.ucPackages[dep[1]].Element,"Dependency","usa","PACKAGE_DEP_"+dep.join("_"),"","Dependencia funcional, no herencia ni flujo de ejecución.")); }
    fsFinish(view);
}
function fsAssociation(source,target,key,sourceCard,targetCard,label,composition,atSupplier) {
    var c=fsConnector(source,target,"Association",label,key,"","");
    c.ClientEnd.Cardinality=sourceCard;c.SupplierEnd.Cardinality=targetCard;
    if(composition) { if(atSupplier) c.SupplierEnd.Aggregation=2;else c.ClientEnd.Aggregation=2; }
    fsCheck(c.ClientEnd,"Multiplicidad origen");fsCheck(c.SupplierEnd,"Multiplicidad destino");fsCheck(c,"Asociación");return c;
}
function fsGrid(view,items,columns,kind) {
    var x=35,y=45,rowHeight=0;
    for(var i=0;i<items.length;i++) {
        if(i && i%columns===0) { y+=rowHeight+100;x=35;rowHeight=0; }
        var e=items[i];e.Attributes.Refresh();e.Methods.Refresh();
        var h=kind==="class"?Math.max(150,75+e.Attributes.Count*18+e.Methods.Count*18):135;
        fsPlace(view,e,x,y,kind==="class"?345:275,h,kind);x+=(kind==="class"?440:355);if(h>rowHeight) rowHeight=h;
    }
}
function fsDomainViews(root,foundation) {
    var pkg=fsPackage(foundation.sharedRoot,"Conceptos del dominio","FS25_DOMAIN"),concepts={},groups={},rels=[];
    for(var i=0;i<FS_DATA.domain.length;i++) {
        var spec=FS_DATA.domain[i],p=fsPackage(pkg,spec[1],"FS25_DOMAINPKG_"+spec[1]);
        var e=fsElement(p,spec[0],"Class","FS25_DOMAIN_"+spec[0],"","Concepto del negocio. Sin PK/FK ni métodos de implementación.");
        concepts[spec[0]]=e;groups[spec[0]]=spec[1];
        var fields=spec[2].split(",");for(var j=0;j<fields.length;j++) {var f=fields[j].split(":");fsAttribute(e,f[0],f[1],"Atributo conceptual.");}
    }
    for(i=0;i<FS_DATA.domainRelations.length;i++) { var relation=FS_DATA.domainRelations[i];rels.push(fsAssociation(concepts[relation[0]],concepts[relation[1]],"DOMAIN_REL_"+i,relation[2],relation[3],relation[4],relation[5],false)); }
    var view=fsDiagram(foundation.generalRoot,"03 Modelo de dominio - General","Logical","Modelo conceptual. Suscripción: máximo una vigente; la implementación actual no conserva un historial separado. ResultadoSincronizacion es un concepto, no una tabla sync_log implementada.");
    var all=[];for(var name in concepts) all.push(concepts[name]);fsGrid(view,all,6,"domain");
    for(i=0;i<rels.length;i++) fsAllow(view,rels[i]);fsFinish(view);
    for(var g=0;g<FS_DATA.packages.length;g++) {
        var group=FS_DATA.packages[g][0],detail=fsDiagram(foundation.supportRoot,"Dominio - "+FS_DATA.packages[g][1],"Logical","Vista conceptual del paquete "+group+" con conceptos vecinos para explicar las relaciones.");
        var included={},items=[];
        for(name in concepts) if(groups[name]===group) included[name]=true;
        for(i=0;i<FS_DATA.domainRelations.length;i++) { relation=FS_DATA.domainRelations[i];if(groups[relation[0]]===group || groups[relation[1]]===group) { included[relation[0]]=true;included[relation[1]]=true;fsAllow(detail,rels[i]); } }
        for(name in included) items.push(concepts[name]);fsGrid(detail,items,4,"domain");fsFinish(detail);
    }
}
function fsParticipants(c,messages,pkg,prefix,foundation) {
    var refs={},order=[],participants={};
    function register(ref) { if(!refs[ref.key]) { refs[ref.key]=ref;order.push(ref); } }
    for(var i=0;i<messages.length;i++) { register(messages[i].from);register(messages[i].to); }
    for(i=0;i<order.length;i++) {
        var ref=order[i];
        if(ref.kind==="actor") participants[ref.key]=FS_ACTORS[ref.actor];
        else {
            var classifier=fsClassifier(ref,c,foundation.classesRoot);
            var sequence=prefix.indexOf("FS25_SEQ_")===0;
            var object=fsElement(pkg,ref.name.charAt(0).toLowerCase()+ref.name.substring(1),sequence?"Sequence":"Object",prefix+"_"+ref.key,sequence?"":ref.kind,fsCaseNotes(c));
            if(sequence) { object.Type="Sequence";object.Stereotype=""; }
            object.ClassifierID=classifier.ElementID;fsCheck(object,"Clasificar participante");participants[ref.key]=object;
        }
    }
    return {refs:refs,order:order,objects:participants};
}
function fsRobustness(root,foundation,c) {
    var pkg=foundation.casePackages[String(c.id)],objectPkg=foundation.objectPackages[String(c.id)];
    var messages=fsMessages(c,false).concat(fsMessages(c,true));
    var participants=fsParticipants(c,messages,objectPkg,"FS25_ROBUST_"+c.code,foundation);
    var view=fsDiagram(pkg,"01 Robustez - "+c.code,"Analysis",fsCaseNotes(c));
    var counts={actor:0,boundary:0,control:0,entity:0},xmap={actor:20,boundary:300,control:650,entity:1030};
    var totals={actor:0,boundary:0,control:0,entity:0};
    for(var q=0;q<participants.order.length;q++) totals[participants.order[q].kind]++;
    var height=Math.max(totals.control,totals.entity,totals.boundary)*145;
    for(var i=0;i<participants.order.length;i++) {
        var ref=participants.order[i],n=counts[ref.kind]++;
        var y=65+Math.floor((height-totals[ref.kind]*145)/2)+n*145;
        fsPlace(view,participants.objects[ref.key],xmap[ref.kind],y,ref.kind==="actor"?140:125,110,ref.kind);
    }
    var pairs={};
    for(i=0;i<messages.length;i++) {
        var msg=messages[i];if(msg.from.key===msg.to.key) continue;
        var invalid=(msg.from.kind==="actor" && msg.to.kind!=="boundary") || (msg.to.kind==="actor" && msg.from.kind!=="boundary") || (msg.from.kind==="entity" && msg.to.kind!=="control") || (msg.to.kind==="entity" && msg.from.kind!=="control") || (msg.from.kind==="boundary" && msg.to.kind==="boundary");
        if(invalid) throw new Error("Relación ICONIX inválida en "+c.code+": "+msg.from.key+" -> "+msg.to.key);
        var key=msg.from.key+"->"+msg.to.key;
        if(pairs[key]) continue;pairs[key]=true;
        fsAllow(view,fsConnector(participants.objects[msg.from.key],participants.objects[msg.to.key],"Association","", "ROBUST_"+c.code+"_"+key,"","Responsabilidades: "+msg.name+". Ver secuencias para el orden temporal."));
    }
    // Otros participantes humanos comparten la frontera, con permisos en notas.
    for(i=1;i<c.actors.length;i++) {
        var actor=FS_ACTORS[c.actors[i]];
        fsPlace(view,actor,20,65+counts.actor++*140,170,95,"actor");
        fsAllow(view,fsConnector(actor,participants.objects[fsReference("b",c).key],"Association","","ROBUST_ACTOR_"+c.code+"_"+c.actors[i],"","Participación según permisos descritos en el CU."));
    }
    if(c.id===13) {
        var external=FS_ACTORS.IAExterna;
        var adapterRef=fsReference("#AdaptadorIAExterna",c);
        var adapterClass=fsClassifier(adapterRef,c,foundation.classesRoot);
        var adapter=fsElement(objectPkg,adapterRef.name,"Object","FS25_ROBUST_OPTIONAL_"+c.code,"boundary","Contrato opcional. La IA puede usar una alternativa local.");
        adapter.ClassifierID=adapterClass.ElementID;fsCheck(adapter,"Adaptador opcional");
        fsPlace(view,external,20,65+counts.actor++*140,170,95,"actor");
        fsPlace(view,adapter,300,65+counts.boundary++*140,255,95,"boundary");
        fsAllow(view,fsConnector(participants.objects[fsReference("c",c).key],adapter,"Association","[integración configurada]","ROBUST_OPTIONAL_CONTROL_"+c.code,"","Interacción prevista/opcional, sin afirmar ejecución remota actual."));
        fsAllow(view,fsConnector(adapter,external,"Association","contrato externo","ROBUST_OPTIONAL_ACTOR_"+c.code,"","Frontera de integración con un actor exterior al sujeto."));
    }
    fsFinish(view);
    fsConnector(FS_UC[String(c.id)],participants.objects[fsReference("c",c).key],"Dependency","traza","TRACE_ROBUST_"+c.code,"trace","Responsabilidad que realiza el caso de uso.");
}
function fsSequence(root,foundation,c,alternate) {
    var pkg=foundation.casePackages[String(c.id)],objectPkg=foundation.objectPackages[String(c.id)];
    var path=alternate?"Alternativo":"Principal",messages=fsMessages(c,alternate);
    var participants=fsParticipants(c,messages,objectPkg,"FS25_SEQ_"+c.code+"_"+path,foundation);
    var notes=fsCaseNotes(c)+"\nEscenario: "+path+(alternate?"\nGuarda de esta interacción: ["+c.guard+"]":"\nSe asumen las precondiciones y el camino de éxito descritos en el caso.");
    var view=fsDiagram(pkg,(alternate?"03 Secuencia alternativa - ":"02 Secuencia principal - ")+c.code,"Sequence",notes);
    for(var i=0;i<participants.order.length;i++) {
        var ref=participants.order[i];fsPlace(view,participants.objects[ref.key],40+i*220,100,175,messages.length*35+150,ref.kind);
    }
    for(i=0;i<messages.length;i++) {
        var msg=messages[i],source=participants.objects[msg.from.key],target=participants.objects[msg.to.key];
        var connector=fsConnector(source,target,"Sequence",msg.name,"SEQ_"+c.code+"_"+path+"_"+i,"","Mensaje "+(i+1)+". Escenario "+path+". Los resultados de consultas se consideran respuestas implícitas.");
        connector.DiagramID=view.diagram.DiagramID;
        connector.SequenceNo=i+1;
        var from=view.positions[String(source.ElementID)],to=view.positions[String(target.ElementID)];
        connector.StartPointX=from.x+Math.floor(from.w/2);connector.EndPointX=to.x+Math.floor(to.w/2);
        connector.StartPointY=230+i*65;connector.EndPointY=230+i*65;
        fsCheck(connector,"Orden de mensaje "+c.code);fsAllow(view,connector);
    }
    var constraint=fsElement(objectPkg,alternate?"["+c.guard+"]":"Escenario principal","Constraint","FS25_SEQ_CONSTRAINT_"+c.code+"_"+path,"","");
    fsPlace(view,constraint,40,messages.length*35+300,Math.max(600,participants.order.length*220-40),40,"constraint");
    fsFinish(view);
}
var FS_CLASS_REL=[];
function fsClassViews(root,foundation) {
    var byTable={};for(var i=0;i<FS_DATA.models.length;i++) if(FS_DATA.models[i].table) byTable[FS_DATA.models[i].table]=FS_DATA.models[i];
    for(i=0;i<FS_DATA.models.length;i++) {
        var spec=FS_DATA.models[i];
        for(var j=0;j<spec.attributes.length;j++) {
            var field=spec.attributes[j];if(!field.fk) continue;
            var target=byTable[field.fk.split(".")[0]];if(!target) throw new Error("FK no resuelta: "+field.fk);
            var composite=(spec.key==="OrderItem" && target.key==="Order") || (spec.key==="ReservationItem" && target.key==="Reservation") || (spec.key==="ChatMessage" && target.key==="ChatConversation");
            var unique=field.unique || (field.pk && spec.key==="ProviderAccount");
            FS_CLASS_REL.push(fsAssociation(FS_MODEL[spec.key],FS_MODEL[target.key],"CLASS_FK_"+spec.key+"_"+field.name,unique?"0..1":"0..*",field.nullable?"0..1":"1",field.name,composite,true));
        }
    }
    var general=fsDiagram(foundation.generalRoot,"04 Clases - General","Logical","Campos y referencias reales extraídos de modelos SQLAlchemy. Las clases locales son responsabilidades de almacenamiento JSON/Dexie/SQLite. Operaciones adicionales: diseño lógico, no métodos Python existentes.");
    var all=[];for(var key in FS_MODEL) all.push(FS_MODEL[key]);fsGrid(general,all,6,"class");
    for(i=0;i<FS_CLASS_REL.length;i++) fsAllow(general,FS_CLASS_REL[i]);fsFinish(general);
    for(var g=0;g<FS_DATA.packages.length;g++) {
        var group=FS_DATA.packages[g][0],pkg=foundation.modelPackages[group];
        var detail=fsDiagram(foundation.supportRoot,"Clases - "+FS_DATA.packages[g][1],"Logical","Clases entity de implementación y boundary/control de diseño. Consultar notas Fuente y Codigo. No se presenta una función Python como una clase física ya implementada.");
        var elements=[],ids={};
        for(i=0;i<FS_DATA.models.length;i++) if(FS_DATA.models[i].package===group) { var entity=FS_MODEL[FS_DATA.models[i].key];elements.push(entity);ids[String(entity.ElementID)]=true; }
        for(key in FS_DESIGN) if(Number(FS_DESIGN[key].PackageID)===Number(pkg.PackageID)) { elements.push(FS_DESIGN[key]);ids[String(FS_DESIGN[key].ElementID)]=true; }
        // Dependencias de responsabilidades derivadas de los mensajes reales del modelo.
        var designLinks=[],included={};
        for(i=0;i<FS_DATA.cases.length;i++) {
            var c=FS_DATA.cases[i];if(c.package!==group) continue;
            var messages=fsMessages(c,false).concat(fsMessages(c,true));
            for(j=0;j<messages.length;j++) {
                var m=messages[j];if(m.from.kind==="actor" || m.to.kind==="actor" || m.from.key===m.to.key) continue;
                var source=fsClassifier(m.from,c,foundation.classesRoot),destination=fsClassifier(m.to,c,foundation.classesRoot);
                var depKey=String(source.ElementID)+"_"+String(destination.ElementID);
                if(included[depKey]) continue;included[depKey]=true;
                if(!ids[String(source.ElementID)]) {elements.push(source);ids[String(source.ElementID)]=true;}
                if(!ids[String(destination.ElementID)]) {elements.push(destination);ids[String(destination.ElementID)]=true;}
                designLinks.push(fsConnector(source,destination,"Dependency","usa","DESIGN_DEP_"+depKey,"","Responsabilidad derivada de "+c.code+": "+m.name));
            }
        }
        fsGrid(detail,elements,4,"class");
        for(i=0;i<FS_CLASS_REL.length;i++) if(ids[String(FS_CLASS_REL[i].ClientID)] && ids[String(FS_CLASS_REL[i].SupplierID)]) fsAllow(detail,FS_CLASS_REL[i]);
        for(i=0;i<designLinks.length;i++) fsAllow(detail,designLinks[i]);fsFinish(detail);
    }
    for(i=0;i<FS_DATA.cases.length;i++) if(fsCaseSelected(FS_DATA.cases[i])) fsCaseClassView(foundation,FS_DATA.cases[i]);
    fsLayers(foundation.supportRoot);
}
function fsCaseClassView(foundation,c) {
    var pkg=foundation.casePackages[String(c.id)],view=fsDiagram(pkg,"04 Clases - "+c.code,"Logical",fsCaseNotes(c)+"\nVista específica de clases participantes en este CU. Se reutilizan los mismos clasificadores de las secuencias y de la robustez; los actores no son clases del sistema.");
    var messages=fsMessages(c,false).concat(fsMessages(c,true)),refs={},items=[],ids={},links={},models={};
    function add(ref) {
        if(ref.kind==="actor" || refs[ref.key]) return;
        refs[ref.key]=ref;
        var element=fsClassifier(ref,c,foundation.classesRoot);
        items.push({ref:ref,element:element});ids[String(element.ElementID)]=true;
        if(ref.kind==="entity") models[ref.model]=true;
    }
    for(var i=0;i<messages.length;i++) {add(messages[i].from);add(messages[i].to);}
    var buckets={boundary:[],control:[],entity:[]};
    for(i=0;i<items.length;i++) buckets[items[i].ref.kind].push(items[i]);
    for(var kind in buckets) {
        var list=buckets[kind],x=kind==="boundary"?35:kind==="control"?410:820,y=65;
        for(i=0;i<list.length;i++) {
            var e=list[i].element;e.Attributes.Refresh();e.Methods.Refresh();
            var h=70+Number(e.Attributes.Count)*18+Number(e.Methods.Count)*20;
            h=Math.max(110,h);
            fsPlace(view,e,x,y,330,h,"class");y+=h+95;
        }
    }
    for(i=0;i<messages.length;i++) {
        var m=messages[i];if(m.from.kind==="actor" || m.to.kind==="actor" || m.from.key===m.to.key) continue;
        var from=fsClassifier(m.from,c,foundation.classesRoot),to=fsClassifier(m.to,c,foundation.classesRoot),key=String(from.ElementID)+"_"+String(to.ElementID);
        if(links[key]) continue;links[key]=true;
        fsAllow(view,fsConnector(from,to,"Dependency","usa","CASE_CLASS_DEP_"+c.code+"_"+key,"","Responsabilidad de "+c.code+" derivada de: "+m.name));
    }
    for(i=0;i<FS_CLASS_REL.length;i++) { var rel=FS_CLASS_REL[i];if(ids[String(rel.ClientID)] && ids[String(rel.SupplierID)]) fsAllow(view,rel); }
    fsFinish(view);
}
function fsLayers(pkg) {
    var view=fsDiagram(pkg,"DC_Responsabilidades_por_Capas","Logical","Vista de responsabilidades. Las interfaces son abstracciones de diseño: la implementación concreta usa módulos FastAPI, SQLAlchemy, Dexie y sqflite.");
    var definitions=[['UI','PresentacionWebFlutter','boundary'],['API','API_REST_FastAPI','boundary'],['AUTH','AutorizacionTenantPlan','control'],['BUSINESS','ReglasComerciales','control'],['SYNC','CoordinacionSincronizacion','control'],['REPORT','ReportesYAnalitica','control'],['PG','PersistenciaSQLAlchemy','entity'],['LOCAL','PersistenciaDexieSqflite','entity']];
    var nodes={};for(var i=0;i<definitions.length;i++) {var d=definitions[i];nodes[d[0]]=fsElement(pkg,d[1],"Class","FS25_LAYER_"+d[0],d[2],"Responsabilidad lógica del sistema.");fsPlace(view,nodes[d[0]],50+(i%4)*365,60+Math.floor(i/4)*270,290,140,"class");}
    var dependencies=[['UI','API'],['UI','LOCAL'],['API','AUTH'],['API','BUSINESS'],['API','SYNC'],['API','REPORT'],['BUSINESS','PG'],['SYNC','BUSINESS'],['SYNC','PG'],['REPORT','PG']];
    for(i=0;i<dependencies.length;i++) {var pair=dependencies[i];fsAllow(view,fsConnector(nodes[pair[0]],nodes[pair[1]],"Dependency","usa","LAYER_DEP_"+pair.join("_"),"","Dependencia de responsabilidad."));}fsFinish(view);
}
function fsValidateData() {
    var allowed={TODO:1,CASOS:1,PAQUETES:1,DOMINIO:1,ROBUSTEZ:1,SECUENCIAS:1,CLASES:1};
    if(!allowed[FS_CONFIG.seccion]) throw new Error("Sección desconocida: "+FS_CONFIG.seccion);
    if(FS_DATA.cases.length!==16 || FS_CONFIG.desdeCU<1 || FS_CONFIG.hastaCU>16 || FS_CONFIG.desdeCU>FS_CONFIG.hastaCU) throw new Error("Rango o catálogo de CU inválido.");
    var seen={};for(var i=0;i<FS_DATA.cases.length;i++) { var c=FS_DATA.cases[i];if(c.id!==i+1 || c.code!=="CU"+c.id || seen[String(c.id)]) throw new Error("Numeración de CU inválida: "+c.id);seen[String(c.id)]=true; }
}
function fsMain() {
    var oldUI=true,oldBatch=false,changedUI=false,changedBatch=false;
    try {
        fsValidateData();
        var selected=Repository.GetTreeSelectedPackage();
        if(!selected) throw new Error("Selecciona primero un paquete del proyecto en el Browser de EA.");
        fsOut("Iniciando FashionStore UML 2.5.1. No cierres EA hasta el resumen final.");
        try { oldUI=Repository.EnableUIUpdates;Repository.EnableUIUpdates=false;changedUI=true;oldBatch=Repository.BatchAppend;Repository.BatchAppend=true;changedBatch=true; } catch(optionalFlags) { fsOut("EA no expone todos los indicadores de lote; continúa con los indicadores disponibles."); }
        var root=null,cursor=selected;
        // Los Model Root de EA tienen Element=null; son destinos válidos.
        while(cursor && cursor.Element && String(cursor.Element.Alias).indexOf("FS25_")===0) {
            if(String(cursor.Element.Alias)==="FS25_ORGANIZADO_ROOT") {root=cursor;break;}
            cursor=cursor.ParentID?Repository.GetPackageByID(cursor.ParentID):null;
        }
        if(!root) root=fsPackage(cursor||selected,FS_CONFIG.nombreRaiz,"FS25_ORGANIZADO_ROOT");
        var foundation=fsCreateFoundation(root);
        if(fsSection("CASOS")) { fsUseCaseViews(root,foundation);fsOut("Casos de uso generales y por paquete: listos."); }
        if(fsSection("PAQUETES")) { fsPackageView(root,foundation);fsOut("Diagrama de paquetes: listo."); }
        if(fsSection("DOMINIO")) { fsDomainViews(root,foundation);fsOut("Modelo de dominio y vistas por paquete: listos."); }
        for(var i=0;i<FS_DATA.cases.length;i++) {
            var c=FS_DATA.cases[i];if(!fsCaseSelected(c)) continue;
            if(fsSection("ROBUSTEZ")) fsRobustness(root,foundation,c);
            if(fsSection("SECUENCIAS")) { fsSequence(root,foundation,c,false);if(FS_CONFIG.generarAlternativos) fsSequence(root,foundation,c,true); }
            if((fsSection("ROBUSTEZ") || fsSection("SECUENCIAS")) && (c.id%5===0 || c.id===FS_CONFIG.hastaCU)) fsOut("Procesado "+c.code+": "+c.name);
        }
        if(fsSection("CLASES")) { fsClassViews(root,foundation);fsOut("Clases generales, por paquete y por capas: listas."); }
        Repository.RefreshModelView(root.PackageID);
        fsOut("TERMINADO. Nuevos paquetes="+FS_STATS.paquetes+", elementos="+FS_STATS.elementos+", diagramas="+FS_STATS.diagramas+", conectores="+FS_STATS.conectores+".");
        fsOut("En una repetición los contadores de nuevos objetos deben ser cero. Consulta las notas de cada CU y de la cabecera para las diferencias entre documento e implementación.");
    } catch(error) {
        fsOut("ERROR. El modelo puede estar incompleto. Detalle: "+(error.description||error.message||String(error)));
        throw error;
    } finally {
        if(changedBatch) Repository.BatchAppend=oldBatch;
        if(changedUI) Repository.EnableUIUpdates=oldUI;
    }
}

fsMain();
