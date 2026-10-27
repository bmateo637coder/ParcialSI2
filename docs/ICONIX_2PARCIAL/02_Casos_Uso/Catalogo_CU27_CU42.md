# CATÁLOGO DE CASOS DE USO - NUEVOS Y MODIFICADOS (2DO PARCIAL)

> Se conservan **CU1 - CU26** del 1er parcial. Se agregan **CU27 - CU42**.

## PAQUETE P6 - PLATAFORMA SAAS Y SUSCRIPCIONES

| CU | Nombre | Actor Principal | Descripción | Prioridad |
|---|---|---|---|---|
| **CU27** | Registrar Empresa Contratante | Administrador de Plataforma | Registrar una nueva empresa (tenant), crear su administrador de empresa y asignarle un plan inicial. | **ALTA** |
| **CU28** | Gestionar Planes de Suscripción | Administrador de Plataforma | Crear, editar, activar/desactivar planes (Básico/Profesional) con sus límites y funcionalidades habilitadas. | **ALTA** |
| **CU29** | Gestionar Suscripción de Empresa | Administrador de Plataforma / Administrador de Empresa | Asignar, cambiar o consultar la suscripción. Registrar fecha de inicio/vencimiento y estado. | **ALTA** |
| **CU30** | Verificar Límites y Restricciones por Plan | Sistema | Validar límites (máx. sucursales) y funcionalidades (reportes con IA/ML) según el plan contratado. | **ALTA** |

## PAQUETE P1 - USUARIOS Y ROLES (MODIFICADO)

| CU | Nombre | Actor Principal | Descripción | Prioridad |
|---|---|---|---|---|
| **CU4 (MOD)** | Gestionar Usuarios y Roles por Empresa | Administrador de Empresa | Gestionar usuarios y roles **únicamente** de su propia empresa. No puede acceder a usuarios de otras empresas. | **ALTA** |
| **CU5 (MOD)** | Gestionar Sucursales por Empresa | Administrador de Empresa | Gestionar sucursales de su empresa, respetando el límite máximo según su plan. | **ALTA** |

## PAQUETE P7 - OPERACIÓN OFFLINE Y SINCRONIZACIÓN

| CU | Nombre | Actor Principal | Descripción | Prioridad |
|---|---|---|---|---|
| **CU31** | Instalar PWA y Descargar Catálogo Offline | Cajero / Encargado | Instalar la PWA, descargar subconjunto del catálogo (productos, variantes, precios, tallas, colores) y almacenarlo en IndexedDB. | **ALTA** |
| **CU32** | Consultar Catálogo en Modo Offline | Cajero / Encargado | Consultar productos/precios/existencias conocidas con aviso de "información puede estar desactualizada". | **ALTA** |
| **CU33** | Registrar Reserva Sin Conexión | Encargado | Registrar una reserva localmente (UUID) con datos mínimos del cliente. Se guarda en IndexedDB/SQLite sin llamar al backend. | **ALTA** |
| **CU34** | Registrar Venta de Contado Sin Conexión | Cajero | Registrar venta de contado offline. Se almacena localmente con estado `REGISTRADA_LOCAL`. Solo contado mientras no hay conexión. | **ALTA** |
| **CU35** | Consultar Operaciones Pendientes | Cajero / Encargado | Visualizar lista de reservas/ventas pendientes de sincronización con su UUID, tipo, fecha local, estado e intentos. | **ALTA** |
| **CU36** | Sincronizar Operaciones Pendientes | Cajero / Encargado / Sistema | Al recuperar conexión, enviar operaciones pendientes al backend (`POST /sync`). Aplicar idempotencia, validar inventario, confirmar/rechazar/en conflicto. | **ALTA** |
| **CU37** | Gestionar Conflictos de Sincronización | Encargado | Revisar operaciones en estado `EN_CONFLICTO`, ver stock disponible vs solicitado, resolver ajustando cantidad o rechazando con motivo. | **ALTA** |
| **CU38** | Registrar Cambio de Prenda | Cajero | Registrar cambio de prenda sobre una venta confirmada, validando plazo permitido por la empresa. Generar movimientos de inventario correspondientes. | **ALTA** |

## PAQUETE P8 - REPORTES GENERATIVOS CON IA Y ANALÍTICA ML

| CU | Nombre | Actor Principal | Descripción | Prioridad |
|---|---|---|---|---|
| **CU39** | Generar Reporte con Lenguaje Natural | Administrador de Empresa / Encargado | Solicitar reporte en lenguaje natural (texto o voz). El sistema interpreta, valida filtros, ejecuta consulta controlada por tenant, muestra tabla/gráfico y permite exportar PDF/Excel. **Requiere plan Profesional**. | **ALTA** |
| **CU40** | Exportar Reporte Generativo | Administrador de Empresa / Encargado | Exportar el reporte generado a formato PDF o Excel con título, filtros aplicados, tabla y gráfico. | **ALTA** |
| **CU41** | Visualizar Dashboard Analítico con ML | Administrador de Empresa | Visualizar dashboard con indicadores, predicciones del modelo supervisado, segmentación del modelo no supervisado y métricas de evaluación. | **ALTA** |
| **CU42** | Entrenar Modelos de ML | Administrador de Plataforma | Generar datos sintéticos, entrenar modelo supervisado y no supervisado, validar métricas (MAE, R², Silhouette), guardar `.joblib`. | **ALTA** |
