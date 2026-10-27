# FICHA DE CASO DE USO - CU36

**Código:** CU36  
**Nombre:** Sincronizar Operaciones Pendientes  
**Paquete:** P7 - Operación Offline y Sincronización  
**Prioridad:** ALTA  
**Tipo:** Nuevo  

## Actores

- **Actor Principal:** Cajero / Encargado de Sucursal
- **Actores Secundarios:** Sistema (Detección de conectividad), Backend (SyncService)

## Objetivo

Enviar al backend las operaciones (reservas y ventas de contado) registradas localmente sin conexión, aplicando **idempotencia**, validando inventario por sucursal, evitando duplicados y gestionando posibles conflictos.

## Precondiciones

- El usuario se encuentra autenticado y pertenece a una empresa y sucursal activas.
- Existe conexión a Internet.
- Existen operaciones en la cola local con estado `REGISTRADA_LOCAL` o `ENVIADA`.
- La aplicación tiene permisos para acceder a la cola local (IndexedDB / SQLite).
- La empresa tiene suscripción activa.

## Postcondiciones

- Las operaciones validadas con stock suficiente pasan a `CONFIRMADA` y generan los movimientos de inventario correspondientes.
- Las operaciones con stock insuficiente pasan a `EN_CONFLICTO` y se crea un registro en `ConflictoSync`.
- Las operaciones ya existentes con el mismo `UUID` no generan duplicados (**idempotencia**).
- Se actualiza el estado local en IndexedDB/SQLite.
- Queda registro en `OperacionSync` para trazabilidad.

## Reglas de Negocio

- **RN-OFF-01:** Cada operación offline debe tener un `UUID` v4 generado en el cliente.
- **RN-OFF-02:** El backend debe identificar operaciones por `uuid`. Si ya existe y está `CONFIRMADA`, **NO** se duplica.
- **RN-OFF-03:** La validación de inventario se realiza **exclusivamente** en el servidor con el stock real por `(empresa_id, sucursal_id, variante_id)`.
- **RN-OFF-04:** Solo se permiten **ventas de contado** en modo offline. No se procesan pagos electrónicos sin conexión.
- **RN-OFF-05:** Toda operación debe estar asociada a `empresa_id`, `sucursal_id`, `usuario_id`.
- **RN-OFF-06:** Las operaciones rechazadas o en conflicto **NO** se eliminan de la cola local.

## Flujo Normal

1. **Detectar conectividad.** El cliente detecta que se restableció la conexión o el usuario presiona "Sincronizar".
2. **Obtener cola.** Se obtiene la lista de operaciones pendientes desde IndexedDB (PWA) o SQLite (Flutter).
3. **Construir payload.** Por cada operación se envía: `uuid`, `tipo_operacion`, `empresa_id`, `sucursal_id`, `usuario_id`, `fecha_local`, `cliente_id`, `items[]`, `total`, `forma_pago`, `origen: "OFFLINE"`.
4. **Enviar.** Se realiza `POST /sync` con el arreglo de operaciones pendientes.
5. **Validar en backend.** El `SyncService` valida pertenencia al tenant, verifica existencia por `uuid`, valida stock disponible.
6. **Procesar.** Si hay stock suficiente: crea `Venta`/`Reserva`, actualiza `Inventario`, registra `MovimientoInventario`, marca `CONFIRMADA`.
7. **Responder.** El backend retorna por cada `uuid` su estado: `CONFIRMADA`, `RECHAZADA` o `EN_CONFLICTO` con motivo.
8. **Actualizar local.** El cliente actualiza el estado de cada operación en su almacenamiento local y muestra el resultado al usuario.

## Flujos Alternativos / Excepciones

| Código | Descripción | Acción |
|---|---|---|
| **FA-01** | Operación con mismo `uuid` ya registrada y `CONFIRMADA` | El backend retorna `CONFIRMADA` sin crear nuevos registros (Idempotencia). No se descuenta inventario nuevamente. |
| **FA-02** | Stock insuficiente para alguna variante | El backend marca la operación como `EN_CONFLICTO`, crea registro en `ConflictoSync` con `stock_disponible`, `cantidad_solicitada` y motivo. |
| **FA-03** | Operación mal formada o con datos incompletos | El backend marca como `RECHAZADA` con motivo. La operación permanece en cola local para revisión. |
| **FA-04** | Pérdida de conexión durante el envío | El cliente mantiene las operaciones en `REGISTRADA_LOCAL`. Al volver conexión se reintenta automáticamente. |
| **FA-05** | Reintentos agotados o error persistente | Se incrementa `intentos`. El usuario puede reintentar manualmente desde "Operaciones Pendientes". |

## Trazabilidad ICONIX

| Elemento | Referencia |
|---|---|
| **Requisito(s)** | RF29, RF30, RF31, RF32 |
| **Diagrama de Robustez** | `04_Diagramas_Robustez/CU36_Robustez.puml` |
| **Diagrama de Secuencia** | `05_Diagramas_Secuencia/CU36_Secuencia.puml` |
| **Clases involucradas** | `OperacionSync`, `ConflictoSync`, `Venta`, `ItemVenta`, `Inventario`, `MovimientoInventario`, `SyncService`, `TenantGuard` |
| **Pruebas** | CP-35, CP-36, CP-37, CP-38 |
