"""Construye el script autónomo de Enterprise Architect a partir del proyecto."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

PACKAGES = [
    ['P1', 'Gestión de Identidad y Acceso'], ['P2', 'Gestión de Catálogo y Sucursales'],
    ['P3', 'Gestión de Operaciones de Compra'], ['P4', 'Pagos e Inventario'],
    ['P5', 'Inteligencia y Analítica heredada'], ['P6', 'Plataforma SaaS'],
    ['P7', 'Offline y Sincronización'], ['P8', 'Analítica e IA del segundo parcial'],
]
ACTORS = [
    ['Usuario', 'Usuario', True],
    ['Empleado', 'Personal de empresa', True],
    ['AdminEmpresa', 'Administrador de empresa', False], ['Encargado', 'Encargado de sucursal', False],
    ['Cajero', 'Cajero', False],
    ['AdminPlataforma', 'Administrador de plataforma', False],
    ['IAExterna', 'Servicio de IA (opcional)', False],
]
GENERALIZATIONS = [
    ['Empleado', 'Usuario'],
    ['AdminEmpresa', 'Empleado'], ['Encargado', 'Empleado'], ['Cajero', 'Empleado'],
    ['AdminPlataforma', 'Usuario'],
]

CASES = []


def uc(number, name, package, actors, ui, control, steps, guard, alternate, rf, source, note=''):
    CASES.append(dict(id=number, code=f'CU{number}', name=name, package=package,
        actors=actors.split(','), ui=ui, control=control, steps=steps.split('|'),
        guard=guard, alternate=alternate.split('|'), rf=rf, source=source, note=note))


uc(1, 'Gestionar empresas (tenants)', 'P6', 'AdminPlataforma', 'PantallaEmpresas', 'EmpresasControl',
   '@AutorizacionControl:validarAdministradorPlataforma()|Empresa:comprobarNITUnico(nit)|Plan:consultarPlanActivo(plan)|Empresa:registrarEmpresa(datos)|User:crearAdministradorDeEmpresa(datos)|Suscripcion:asignarPlanInicial(fechas)|!:confirmarAltaAtomica()',
   'NIT duplicado o error durante el alta', 'Empresa:comprobarNITUnico(nit)|!:revertirAltaCompleta()', 'RF15,RF16,RF17', 'backend/app/api/v1/endpoints/plataforma.py')
uc(2, 'Gestionar planes de suscripción', 'P6', 'AdminPlataforma', 'PantallaPlanes', 'PlanesControl',
   '@AutorizacionControl:validarAdministradorPlataforma()|Plan:listarPlanes()|!:validarLimitesYFunciones(datos)|Plan:guardarPlan(datos)|!:aplicarLimitesEnProximasOperaciones()',
   'límites inválidos', '!:validarLimitesYFunciones(datos)|!:rechazarPlanSinGuardar()', 'RF18,RF21', 'backend/app/api/v1/endpoints/plataforma.py:crear_plan,actualizar_plan')
uc(3, 'Gestionar suscripción de empresa', 'P6', 'AdminPlataforma,AdminEmpresa', 'PantallaSuscripcion', 'SuscripcionesControl',
   '@AutorizacionControl:autorizarGestionOConsulta()|Empresa:consultarEmpresa()|Suscripcion:consultarSuscripcionActual()|Plan:consultarPlanDestino()|Branch:contarSucursalesActivas()|!:validarFechasYCompatibilidad()|Suscripcion:asignarORenovarPlan()|!:confirmarSuscripcion()',
   'uso actual supera el plan destino', 'Branch:contarSucursalesActivas()|Plan:consultarLimiteDestino()|!:rechazarCambioDePlan()', 'RF19,RF20,RF21', 'backend/app/api/v1/endpoints/plataforma.py', 'Administrador de empresa solo consulta. El esquema actual mantiene una suscripción por empresa y la actualiza; no contiene historial de renovaciones.')
uc(4, 'Verificar límites del plan', 'P6', 'Empleado', 'SolicitudOperacionProtegida', 'PlanGuard',
   '@TenantGuard:obtenerEmpresaDeSesion()|Empresa:comprobarEstadoActivo()|Suscripcion:comprobarEstadoYVigencia()|Plan:consultarFuncionesYLimites()|Branch:contarSucursalesActivasSiCorresponde()|!:autorizarOperacionSolicitada()',
   'suscripción no vigente o función no incluida', 'Suscripcion:comprobarEstadoYVigencia()|Plan:consultarFuncionesYLimites()|!:denegarOperacionConMotivo()', 'RF21,RF17', 'backend/app/core/tenant.py:validate_subscription,require_plan_profesional,enforce_branch_limit', 'Es comportamiento incluido; no se crea un actor llamado Sistema. Offline se valida una copia local y el servidor revalida al sincronizar.')
uc(5, 'Preparar dispositivo para uso offline', 'P7', 'Cajero,Encargado', 'PantallaPrepararOffline', 'PreparacionOfflineControl',
   '@PlanGuard:validarPlanConConexion()|@TenantGuard:obtenerContextoEmpresaSucursal()|Product:descargarProductosEmpresa()|ProductVariant:descargarVariantesYPrecios()|Branch:descargarSucursalesAutorizadas()|Inventory:descargarExistenciasConocidas()|CatalogoLocal:guardarCatalogoSinReemplazoParcial()|SesionLocal:guardarContextoYFechaActualizacion()|!:confirmarPreparacion()',
   'pérdida de conexión durante la descarga', 'CatalogoLocal:consultarVersionAnterior()|!:conservarCatalogoAnteriorYAdvertir()', 'RF22,RF23,RF28', 'frontend-web/src/app/api.service.ts:prepararOffline; movil/lib/core/offline/offline_db.dart')
uc(6, 'Consultar catálogo sin conexión', 'P7', 'Cajero,Encargado', 'PantallaCatalogoOffline', 'CatalogoOfflineControl',
   'SesionLocal:restaurarContextoEmpresaUsuario()|CatalogoLocal:buscarProductosYVariantes(filtros)|CatalogoLocal:consultarFechaActualizacion()|OperacionLocal:considerarExistenciasPendientes()|!:mostrarDatosComoExistenciaConocida()',
   'no existe catálogo descargado', 'CatalogoLocal:comprobarCatalogoDisponible()|!:solicitarDescargaConConexion()', 'RF24,RF28', 'frontend-web/src/app/core/offline; movil/lib/core/offline', 'La existencia local es informativa; se advierte si está desactualizada y nunca equivale a confirmación central.')
uc(7, 'Registrar reserva sin conexión', 'P7', 'Encargado', 'PantallaReservaOffline', 'ReservaOfflineControl',
   'SesionLocal:validarContextoYPlanGuardado()|CatalogoLocal:consultarVariantesYExistencias()|!:validarCantidadesYCliente()|!:generarUUID()|OperacionLocal:guardarReservaYPayloadEnTransaccion()|CatalogoLocal:actualizarExistenciaLocalConocida()|!:mostrarReservaPendiente()',
   'error al guardar la operación local', 'OperacionLocal:iniciarGuardadoAtomico()|!:revertirPersistenciaLocalSinConfirmar()', 'RF25,RF28,RF30', 'frontend-web/src/app/core/offline/offline-db.service.ts; movil/lib/core/offline/offline_db.dart', 'La copia del plan permite control local; la vigencia y la pertenencia se revalidan en CU10.')
uc(8, 'Registrar venta de contado sin conexión', 'P7', 'Cajero', 'PantallaPOSOffline', 'VentaOfflineControl',
   'SesionLocal:validarContextoYPlanGuardado()|CatalogoLocal:consultarPreciosYExistencias()|!:validarSoloEfectivoYCalcularTotal()|!:generarUUID()|OperacionLocal:guardarVentaYDetalleEnTransaccion()|CatalogoLocal:descontarExistenciaLocalConocida()|!:emitirComprobanteProvisional()',
   'se selecciona pago electrónico sin conexión', '!:validarMetodoSoloEfectivo()|!:impedirPagoElectronicoSinGuardar()', 'RF26,RF28,RF30', 'frontend-web/src/app/pos.component.ts; movil/lib/src/screens/pos_screen.dart')
uc(9, 'Consultar operaciones pendientes', 'P7', 'Cajero,Encargado', 'PantallaOperacionesPendientes', 'PendientesControl',
   'SesionLocal:restaurarEmpresaYUsuario()|OperacionLocal:listarOperacionesDelContexto()|OperacionLocal:consultarDetalleYUltimoResultado(uuid)|!:ordenarPorFechaYEstado()|!:presentarHistorialSinBorrarlo()',
   'no hay operaciones en ese contexto', 'OperacionLocal:listarOperacionesDelContexto()|!:mostrarColaVacia()', 'RF27,RF28', 'frontend-web/src/app/features/offline/sync; movil/lib/src/screens/offline_screen.dart')
uc(10, 'Sincronizar operaciones pendientes', 'P7', 'Cajero,Encargado', 'PantallaSincronizacion', 'SyncClienteControl',
   'OperacionLocal:seleccionarPendientesYReintentables()|OperacionLocal:marcarENVIADAAntesDeEnviar()|#ApiSync:enviarLoteConJWT(lote)|#ApiSync>@SyncServidorControl:sincronizarLote(lote,token)|@SyncServidorControl>@TenantGuard:validarEmpresaUsuarioYSucursal()|@SyncServidorControl>OperacionSync:buscarUUIDConResultadoPrevio(uuid)|@SyncServidorControl>@PlanGuard:revalidarSuscripcion()|@SyncServidorControl>Inventory:bloquearYValidarStockCentral()|@SyncServidorControl>Order:registrarVentaOReservaSinDuplicar()|@SyncServidorControl>InventoryMovement:registrarDescuentoAtomico()|@SyncServidorControl>OperacionSync:guardarResultadoPorUUID()|@SyncServidorControl>#ApiSync:responderPorUUID(resultados)|#ApiSync>c:recibirResultados(resultados)|OperacionLocal:confirmarOConservarSegunRespuesta()|CatalogoLocal:actualizarExistenciasConfirmadas()',
   'el servidor confirma pero se pierde la respuesta', 'OperacionLocal:marcarENVIADAAntesDeEnviar()|#ApiSync:enviarLoteConJWT(lote)|#ApiSync>c:notificarFalloComunicacion()|OperacionLocal:conservarENVIADAConMismoUUID()|!:programarReintentoIdempotente()', 'RF29,RF30,RF31,RF32,RF34', 'backend/app/api/v1/endpoints/sync.py; frontend-web/src/app/core/offline/sync-offline.service.ts; movil/lib/core/offline/sync_offline_service.dart', 'Los reintentos conservan UUID y ENVIADA ante respuesta perdida. Un UUID confirmado retorna el resultado original. Stock insuficiente produce conflicto sin descuento parcial.')
uc(11, 'Gestionar conflictos y operaciones rechazadas', 'P7', 'Encargado,AdminEmpresa', 'PantallaConflictos', 'ConflictosControl',
   '@TenantGuard:validarResponsableEmpresa()|ConflictoSync:listarConflictosNoResueltos()|OperacionSync:consultarPayloadYMotivo(uuid)|Inventory:consultarStockCentralActual()|!:validarAccionYJustificacion(accion)|@SyncServidorControl:reintentarOAnularOperacion(accion)|ConflictoSync:registrarResponsableYResultado()|!:confirmarResolucion()',
   'el stock cambió durante el reintento', 'Inventory:bloquearYRevalidarStock()|ConflictoSync:actualizarMotivoDelConflicto()|!:mantenerOperacionSinConfirmar()', 'RF33,RF34,RF32', 'backend/app/api/v1/endpoints/sync.py:resolver_conflicto')
uc(12, 'Gestionar cambio de prendas', 'P3', 'Cajero,Encargado', 'PantallaCambiosPrenda', 'CambiosControl',
   '@TenantGuard:validarVentaEmpresa()|Order:consultarVentaOriginalConfirmada()|OrderItem:validarCantidadAunNoCambiada()|!:comprobarPlazoConfigurado()|Inventory:bloquearStockPrendaNueva()|!:calcularDiferenciaYCobro()|CambioPrenda:guardarCambioConVentaOriginal()|Inventory:registrarEntradaYSalida()|InventoryMovement:guardarMovimientosCambio()|!:confirmarCambioAtomico()',
   'cambio fuera del plazo o sin stock', 'Order:consultarFechaVenta()|!:verificarPlazoYDisponibilidad()|!:rechazarSinModificarInventario()', 'RF35,RF12,RF17', 'backend/app/api/commerce.py:exchange_garment; backend/app/core/config.py:EXCHANGE_WINDOW_DAYS', 'Se modela plazoConfigurado: el PDF dice 7 días y el código usa 15 por defecto. No se afirma que el saldo a favor/reembolso descrito esté implementado.')
uc(13, 'Solicitar reporte generativo (texto o voz)', 'P8', 'AdminEmpresa,Encargado', 'PantallaReporteGenerativo', 'ReporteIAControl',
   '@TenantGuard:obtenerEmpresaDeSesion()|@PlanGuard:autorizarReportesIA()|!:normalizarTextoOTranscripcion()|@InterpreteReporteControl:clasificarIntencionYExtraerFiltros(texto)|!:validarCatalogoPermitidoYAmbiguedades()|Order:consultarVentasConFiltrosEmpresa()|Inventory:consultarExistenciasConFiltrosEmpresa()|GeneratedReport:guardarResultadoRealJSON()|!:construirTablaGraficoYNarrativa()',
   'solicitud ambigua o intenta consultar otra empresa', '@InterpreteReporteControl:detectarAmbiguedad(texto)|!:solicitarAclaracionSinEjecutarSQLLibre()', 'RF36,RF37,RF38,RF39,RF17', 'backend/app/api/ia_reportes.py; backend/app/services/report_intent.py; backend/app/services/report_language.py; backend/app/services/report_builder.py', 'La IA local clasifica y extrae filtros. Consultas controladas y tenant obligatorios; no se entrega SQL generado por el usuario a la base.')
uc(14, 'Exportar reporte (PDF / Excel)', 'P8', 'AdminEmpresa,Encargado', 'PantallaExportarReporte', 'ExportacionControl',
   '@TenantGuard:validarReporteEmpresa()|GeneratedReport:consultarResultadoAutorizado(reporte)|!:validarFormatoPermitido(formato)|!:renderizarPDFOExcelConEncabezado()|!:entregarArchivoAutenticado()',
   'reporte de otra empresa o identificador inexistente', 'GeneratedReport:buscarReporteEmpresa(reporte)|!:denegarDescargaAjena()', 'RF40,RF17', 'backend/app/api/ia_reportes.py:exportar_reporte,download_report', 'La extensión se elige después de generar el reporte; no se hace include obligatorio de exportación.')
uc(15, 'Consultar dashboard analítico', 'P8', 'AdminEmpresa,Encargado', 'PantallaAnaliticaML', 'DashboardMLControl',
   '@TenantGuard:obtenerEmpresaDeSesion()|@PlanGuard:autorizarAnaliticaML()|AnalyticsRun:consultarModeloMasRecienteEmpresa()|Inventory:consultarStockRealPorVarianteYSucursal()|ProductVariant:consultarPreciosYVariables()|@ModelosMLControl:predecirDemandaYAsignarGrupo()|!:mostrarGraficosMetricasYFiltros()',
   'no hay modelo entrenado para la empresa', 'AnalyticsRun:consultarModeloMasRecienteEmpresa()|!:mostrarAvisoSinPrediccionesInventadas()', 'RF42,RF17', 'backend/app/api/analitica_ml.py:dashboard_analitico; frontend-web/src/app/analytics.component.ts')
uc(16, 'Entrenar y evaluar modelos de ML', 'P8', 'AdminPlataforma', 'PantallaEntrenamientoML', 'EntrenamientoMLControl',
   '@AutorizacionControl:validarResponsableEntrenamiento()|@ModelosMLControl:generarDatosSinteticosConSemilla()|@ModelosMLControl:separarEntrenamientoYValidacion()|@ModelosMLControl:normalizarSoloConEntrenamiento()|@ModelosMLControl:entrenarRegresionLinealYKMeans()|@ModelosMLControl:evaluarMAERMSER2YSilueta()|AnalyticsRun:guardarParametrosMetricasYFecha()|!:presentarMetricasYLimitaciones()',
   'datos insuficientes o error de entrenamiento', '@ModelosMLControl:validarConjuntoEntrenamiento()|!:conservarModeloAnteriorYNotificarError()', 'RF41', 'backend/app/api/analitica_ml.py:entrenar_modelos; backend/app/services/analytics.py:train', 'Actor normativo del PDF: Administrador de plataforma. El endpoint actual autoriza Administrador de empresa/Encargado con plan ML y guarda un AnalyticsRun por empresa. No existe publicación/versionado independiente; diferencia a conciliar.')

MODEL_NAMES = {
    'User':('Usuario','P1'), 'Role':('Rol','P1'), 'Branch':('Sucursal','P2'),
    'Category':('Categoria','P2'), 'Provider':('Proveedor','P2'), 'Season':('Temporada','P2'),
    'Collection':('Coleccion','P2'), 'Size':('Talla','P2'), 'Color':('Color','P2'),
    'Product':('Producto','P2'), 'ProductVariant':('VarianteProducto','P2'),
    'ProviderAccount':('CuentaProveedor','P2'), 'ProductProposal':('PropuestaProducto','P2'),
    'CartItem':('ItemCarrito','P3'), 'Reservation':('Reserva','P3'), 'ReservationItem':('DetalleReserva','P3'),
    'Order':('VentaPedido','P3'), 'OrderItem':('DetalleVenta','P3'), 'Payment':('Pago','P4'),
    'Inventory':('Inventario','P4'), 'InventoryMovement':('MovimientoInventario','P4'),
    'Promotion':('Promocion','P2'), 'Notification':('Notificacion','P3'),
    'ChatConversation':('Conversacion','P5'), 'ChatMessage':('MensajeChat','P5'),
    'Empresa':('Empresa','P6'), 'Plan':('Plan','P6'), 'Suscripcion':('Suscripcion','P6'),
    'OperacionSync':('OperacionSync','P7'), 'ConflictoSync':('ConflictoSync','P7'), 'CambioPrenda':('CambioPrenda','P3'),
    'GeneratedReport':('ReporteGenerado','P8'), 'AnalyticsRun':('EjecucionModeloML','P8'),
}


def parse_models():
    result = []
    types = {'Integer':'Integer','String':'String','Text':'String','Float':'Real','Numeric':'Decimal','Date':'Date','DateTime':'DateTime','Boolean':'Boolean'}
    for path in sorted((ROOT/'backend/app/models').glob('*.py')):
        for cls in (n for n in ast.parse(path.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.ClassDef)):
            if cls.name not in MODEL_NAMES:
                continue
            name, package = MODEL_NAMES[cls.name]
            record = dict(key=cls.name, name=name, package=package, source=str(path.relative_to(ROOT)).replace('\\','/'), attributes=[], methods=[], table='')
            for stmt in cls.body:
                if isinstance(stmt,ast.Assign) and isinstance(stmt.targets[0],ast.Name):
                    field = stmt.targets[0].id
                    if field=='__tablename__': record['table']=ast.literal_eval(stmt.value)
                    if isinstance(stmt.value,ast.Call) and ast.unparse(stmt.value.func)=='Column':
                        args=stmt.value.args
                        dtype = ast.unparse(args[0].func if isinstance(args[0],ast.Call) else args[0])
                        options={kw.arg:ast.literal_eval(kw.value) for kw in stmt.value.keywords if isinstance(kw.value,ast.Constant)}
                        fk=next((ast.literal_eval(a.args[0]) for a in args if isinstance(a,ast.Call) and ast.unparse(a.func)=='ForeignKey'),None)
                        record['attributes'].append(dict(name=field, type=types.get(dtype,dtype), nullable=options.get('nullable',not options.get('primary_key',False)), pk=options.get('primary_key',False), unique=options.get('unique',False), fk=fk))
                if isinstance(stmt,ast.FunctionDef):
                    if any(isinstance(decorator,ast.Name) and decorator.id=='property' for decorator in stmt.decorator_list):
                        annotation=ast.unparse(stmt.returns) if stmt.returns else 'Object'
                        dtype={'str':'String','int':'Integer','float':'Real','bool':'Boolean'}.get(annotation,annotation)
                        record['attributes'].append(dict(name=stmt.name,type=dtype,derived=True))
                    else:
                        record['methods'].append(stmt.name)
            result.append(record)
    result.extend([
        dict(key='OperacionLocal',name='OperacionLocal',package='P7',source='IndexedDB (Dexie) / SQLite (sqflite): operación y payload JSON; no son tablas comerciales duplicadas del servidor.',table='',attributes=[dict(name=n,type=t) for n,t in [('uuid','String'),('empresaId','Integer'),('usuarioId','Integer'),('sucursalId','Integer'),('tipo','String'),('payload','JSON'),('estado','String'),('intentos','Integer'),('ultimoMensaje','String'),('fechaLocal','DateTime')]],methods=[]),
        dict(key='CatalogoLocal',name='CatalogoLocal',package='P7',source='frontend-web/src/app/core/offline/offline-db.service.ts; movil/lib/core/offline/offline_db.dart',table='',attributes=[dict(name=n,type=t) for n,t in [('contexto','String'),('productosVariantes','JSON'),('sucursales','JSON'),('existenciasConocidas','JSON'),('actualizadoEn','DateTime')]],methods=[]),
        dict(key='SesionLocal',name='SesionLocal',package='P7',source='Sesión y contexto guardados; los permisos definitivos se validan en el servidor.',table='',attributes=[dict(name=n,type=t) for n,t in [('empresaId','Integer'),('usuarioId','Integer'),('rol','String'),('actualizadaEn','DateTime')]],methods=[]),
    ])
    return result


DOMAIN = [
    ['Empresa','P6','razonSocial:String,nit:String,activa:Boolean'], ['Plan','P6','nombre:String,maxSucursales:Integer,permiteIA:Boolean'],
    ['Suscripcion','P6','inicio:Date,vencimiento:Date,estado:String'], ['Usuario','P1','nombre:String,correo:String,activo:Boolean'],
    ['Rol','P1','nombre:String'], ['Sucursal','P2','nombre:String,ciudad:String,direccion:String'],
    ['Producto','P2','nombre:String,descripcion:String,precioBase:Real'], ['Categoria','P2','nombre:String'],
    ['Temporada','P2','nombre:String,inicio:Date,fin:Date'], ['Coleccion','P2','nombre:String'],
    ['Proveedor','P2','nombre:String,nit:String'], ['VarianteProducto','P2','sku:String,precio:Real'],
    ['Talla','P2','nombre:String'], ['Color','P2','nombre:String'], ['Inventario','P4','cantidadDisponible:Integer'],
    ['MovimientoInventario','P4','tipo:String,cantidad:Integer,motivo:String,fecha:DateTime'],
    ['ItemCarrito','P3','cantidad:Integer'], ['Reserva','P3','codigo:String,estado:String,vencimiento:DateTime'],
    ['DetalleReserva','P3','cantidad:Integer,precioUnitario:Real'], ['VentaPedido','P3','tipo:String,estado:String,total:Real,fecha:DateTime'],
    ['DetalleVenta','P3','cantidad:Integer,precioUnitario:Real,descuento:Real'], ['Pago','P4','metodo:String,importe:Real,estado:String'],
    ['CambioPrenda','P3','fecha:DateTime,diferencia:Real,estado:String'], ['Promocion','P2','nombre:String,tipo:String,valor:Real'],
    ['Notificacion','P3','titulo:String,mensaje:String,leida:Boolean'], ['Conversacion','P5','inicio:DateTime'],
    ['MensajeChat','P5','rol:String,contenido:String,fecha:DateTime'], ['OperacionOffline','P7','uuid:String,tipo:String,estado:String,fecha:DateTime'],
    ['ResultadoSincronizacion','P7','estado:String,motivo:String,fecha:DateTime'], ['ConflictoSync','P7','motivo:String,resuelto:Boolean'],
    ['SolicitudReporte','P8','texto:String,filtros:String,estado:String,fecha:DateTime'],
    ['ReporteGenerado','P8','resultado:String,fecha:DateTime'], ['ModeloML','P8','tipo:String,parametros:String,metricas:String,fecha:DateTime'],
]
# [origen, destino, multiplicidad en origen, multiplicidad en destino, rol, composición]
DOMAIN_RELATIONS = [
    ['Empresa','Suscripcion','1','0..*','contrata (máximo una vigente)',False], ['Plan','Suscripcion','1','0..*','define condiciones',False],
    *[['Empresa',name,'1','0..*','administra',False] for name in ['Sucursal','Producto','Proveedor','Categoria','Temporada','Promocion','OperacionOffline','ReporteGenerado','ModeloML']],
    ['Empresa','Usuario','0..1','0..*','cuentas de empresa; plataforma sin empresa',False],
    ['Rol','Usuario','0..1','0..*','autoriza',False], ['Temporada','Coleccion','0..1','0..*','agrupa',False],
    ['Categoria','Producto','0..1','0..*','clasifica',False], ['Proveedor','Producto','0..1','0..*','suministra',False],
    ['Temporada','Producto','0..1','0..*','organiza',False], ['Coleccion','Producto','0..1','0..*','reúne',False],
    ['Producto','VarianteProducto','1','0..*','variantes',True], ['Talla','VarianteProducto','1','0..*','talla',False],
    ['Color','VarianteProducto','1','0..*','color',False], ['Sucursal','Inventario','1','0..*','existencias',False],
    ['VarianteProducto','Inventario','1','0..*','stock por sucursal',False], ['Inventario','MovimientoInventario','1','0..*','historial',False],
    ['Usuario','ItemCarrito','1','0..*','carrito',True], ['VarianteProducto','ItemCarrito','1','0..*','selección',False],
    ['Usuario','Reserva','1','0..*','reserva',False], ['Sucursal','Reserva','1','0..*','atiende',False],
    ['Reserva','DetalleReserva','1','1..*','detalles',True], ['VarianteProducto','DetalleReserva','1','0..*','reservada',False],
    ['Empresa','VentaPedido','1','0..*','registra',False], ['Usuario','VentaPedido','0..1','0..*','cliente',False],
    ['Sucursal','VentaPedido','0..1','0..*','vende',False], ['VentaPedido','DetalleVenta','1','1..*','detalles',True],
    ['VarianteProducto','DetalleVenta','1','0..*','vendida',False], ['VentaPedido','Pago','1','0..1','cobro',False],
    ['VentaPedido','CambioPrenda','1','0..*','cambios',False], ['Usuario','Notificacion','1','0..*','recibe',False],
    ['Usuario','Conversacion','1','0..*','inicia',False], ['Conversacion','MensajeChat','1','0..*','mensajes',True],
    ['OperacionOffline','ResultadoSincronizacion','1','0..*','resultados conceptuales',False], ['OperacionOffline','ConflictoSync','1','0..1','conflicto',False],
    ['OperacionOffline','VentaPedido','0..1','0..1','origina si tipo VENTA',False], ['OperacionOffline','Reserva','0..1','0..1','origina si tipo RESERVA (xor)',False],
    ['Usuario','SolicitudReporte','1','0..*','solicita',False], ['SolicitudReporte','ReporteGenerado','1','0..1','produce',False],
]
INCLUDES = [[1,3],[5,4],[7,4],[8,4],[10,4],[13,4],[15,4]]
# Se usa extend solo para comportamientos opcionales del caso base.
EXTENDS = [[14,13,'usuario elige exportar']]
PACKAGE_DEPS = [['P2','P1'],['P3','P1'],['P3','P2'],['P3','P4'],['P4','P2'],['P5','P2'],['P5','P3'],['P6','P1'],['P1','P6'],['P7','P6'],['P7','P2'],['P7','P3'],['P7','P4'],['P8','P6'],['P8','P3'],['P8','P4']]


def main():
    assert len(CASES)==16 and {case['id'] for case in CASES}==set(range(1,17))
    data=dict(packages=PACKAGES,actors=ACTORS,generalizations=GENERALIZATIONS,cases=CASES,models=parse_models(),domain=DOMAIN,domainRelations=DOMAIN_RELATIONS,includes=INCLUDES,extends=EXTENDS,packageDependencies=PACKAGE_DEPS)
    (HERE/'modelo_fashionstore.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    engine=(HERE/'motor_ea.js').read_text(encoding='utf-8')
    header=(HERE/'instrucciones_cabecera.txt').read_text(encoding='utf-8')
    content=header+'\nvar FS_DATA = '+json.dumps(data,ensure_ascii=False,indent=2)+';\n\n'+engine
    target=ROOT/'Scripts_Enterprise_Architect_FashionStore_UML25.txt'
    target.write_text(content,encoding='utf-8-sig')
    (ROOT/'Scripts_EA_Parcial2_Ordenado.txt').write_text(content,encoding='utf-8-sig')
    (HERE/'FashionStore_UML25.js').write_text(content,encoding='utf-8-sig')
    print('Archivo:',target)
    print('Casos de uso:',len(CASES),'Clases de implementación:',len(data['models']),'Conceptos:',len(DOMAIN))


if __name__=='__main__':
    main()
