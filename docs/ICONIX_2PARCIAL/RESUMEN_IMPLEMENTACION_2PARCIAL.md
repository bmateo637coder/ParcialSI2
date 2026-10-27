# SINCRONIZACIÓN OFFLINE - RESUMEN DE IMPLEMENTACIÓN

## Backend (FastAPI)
- **Modelos:** `Empresa`, `Plan`, `Suscripcion`, `OperacionSync`, `ConflictoSync`, `CambioPrenda` con `empresa_id` en entidades clave
- **Guards:** `TenantGuard` (`get_current_empresa`), `PlanGuard` (`require_plan_profesional`, `require_suscripcion_activa`)
- **Endpoints Plataforma SaaS:** `POST /api/plataforma/planes`, `GET /api/plataforma/planes`, `POST /api/plataforma/empresas`, `GET /api/plataforma/empresas`, `GET /api/plataforma/empresas/{id}/suscripcion` (CU27-CU30 base)
- **Endpoint Sync:** `POST /api/sync` con **idempotencia por UUID**, validación de inventario por tenant/sucursal, crea venta `PAGADO` con `es_offline=true`, genera conflicto `EN_CONFLICTO` si falta stock (CU36)
- **Conflictos:** `GET /api/sync/conflictos`, `POST /api/sync/conflictos/{id}/resolver` (AJUSTAR_CANTIDAD | RECHAZAR) (CU37)

## PWA Angular
- `manifest.webmanifest` creado
- `ngsw-config.json` creado (assetGroups + dataGroups para catálogo offline)
- Preparado para IndexedDB + cola de operaciones pendientes

## Flutter
- Pendiente: agregar `sqflite`, `path`, `uuid`, `connectivity_plus`. Crear tablas locales `operaciones_local`, `catalogo_local`, servicio de cola + sync
