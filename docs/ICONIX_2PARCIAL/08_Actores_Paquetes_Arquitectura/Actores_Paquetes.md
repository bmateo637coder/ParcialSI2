# ACTORES - FashionStore SaaS Multitenant

| Actor | Tipo | Descripción | Cambio respecto al 1er Parcial |
|---|---|---|---|
| **Administrador de Plataforma** | Humano - Interno | Personal de FashionStore SaaS. Registra empresas, gestiona planes y suscripciones, supervisa el módulo ML. No opera datos comerciales de las empresas. | **NUEVO** |
| **Administrador de Empresa** | Humano | Administrador de una empresa contratante (tenant). Gestiona usuarios, roles, sucursales, catálogo, proveedores, inventario, reportes y su suscripción. Solo ve información de su propia empresa. | **MODIFICADO** (antes era "Administrador" global, ahora restringido por `empresa_id`) |
| **Encargado de Sucursal** | Humano | Gestiona la operación de su sucursal: reservas, inventario local, reservas/ventas offline, sincronización y resolución de conflictos. | **MODIFICADO** (agrega operación offline y sincronización) |
| **Cajero** | Humano | Atiende el punto de venta. Registra ventas presenciales y ventas de contado offline, gestiona cambios de prenda y sincronización. | **MODIFICADO** (agrega operación offline) |
| **Cliente** | Humano | Cliente de una empresa. Navega catálogo, usa vestidor virtual, reserva y compra. Pertenece a una empresa. | **MODIFICADO** (ahora pertenece a un tenant) |
| **Proveedor** | Externo | Suministra productos a una empresa contratante. | **MODIFICADO** (pertenece a una empresa) |
| **Sistema de Pagos (Stripe Sandbox)** | Sistema Externo | Procesa pagos electrónicos. | **SIN CAMBIO** |
| **Servicio de IA (LLM)** | Sistema Externo | Interpreta solicitudes en lenguaje natural para reportes generativos. Solo recibe parámetros validados por el backend. | **MODIFICADO** (agrega interpretación de reportes) |
| **Sistema (Temporizador)** | Interno | Dispara procesos automáticos: sincronización, actualización de inventario, vencimiento de suscripciones. | **AMPLIADO** |

# PAQUETES ICONIX - 2DO PARCIAL

| Paquete | Nombre | Descripción | Dependencias |
|---|---|---|---|
| **P1** | Autenticación, Usuarios y Roles | Login, roles, permisos. Se mantiene con restricción por empresa. | P6 |
| **P2** | Catálogo, Productos y Proveedores | Gestión de productos, variantes, tallas, colores, categorías, temporadas. | P6 |
| **P3** | Ventas, Reservas, Pagos e Inventario | Ventas presenciales/digitales, reservas, pagos, movimientos de inventario. | P2, P6 |
| **P4** | AR, Recomendaciones y Asistente IA | Vestidor virtual, recomendaciones y asistente. Se conserva. | P2, P6 |
| **P5** | Reportes Convencionales | Reportes y dashboards del 1er parcial. | P3, P6 |
| **P6** | Plataforma SaaS y Suscripciones | **NUEVO**. Empresas (Tenant), Planes, Suscripciones, `TenantGuard`, `PlanGuard`. Todo lo demás depende de este paquete. | - |
| **P7** | Operación Offline y Sincronización | **NUEVO**. PWA (IndexedDB), Flutter (SQLite), cola de operaciones, `SyncService`, detección y gestión de conflictos. | P2, P3, P6 |
| **P8** | Analítica, Reportes Generativos e IA/ML | **NUEVO**. Reportes en lenguaje natural, validación de parámetros, exportación PDF/Excel, datos sintéticos, ML Supervisado/No Supervisado, Dashboard Analítico. | P3, P5, P6 |
