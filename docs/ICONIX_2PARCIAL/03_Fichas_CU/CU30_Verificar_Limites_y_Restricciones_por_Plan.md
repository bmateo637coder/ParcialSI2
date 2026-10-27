# FICHA DE CASO DE USO - CU30

**Código:** CU30  
**Nombre:** Verificar Límites y Restricciones por Plan  
**Paquete:** P6 - Plataforma SaaS y Suscripciones  
**Prioridad:** ALTA  
**Tipo:** Nuevo (Soporte transversal)

## Actores

- **Actor Principal:** Sistema
- **Actores Secundarios:** Backend, Base de Datos

## Objetivo

Validar que la empresa contratante respete los límites y funcionalidades habilitadas por su plan de suscripción antes de ejecutar operaciones críticas.

## Precondiciones

- La empresa tiene una suscripción activa (`estado = ACTIVA`).
- Existe un plan asociado con sus límites y flags de funcionalidades.
- La solicitud proviene de un usuario autenticado perteneciente a dicha empresa.

## Postcondiciones

- Si cumple con límites y funcionalidades → Se permite continuar con la operación.
- Si no cumple → Se rechaza la operación con código `403` y mensaje descriptivo.
- La validación queda registrada para trazabilidad.

## Reglas de Negocio

- **RN-PLAN-01:** **Plan Básico** → Máximo **2** sucursales activas. **NO** permite reportes con IA ni módulo ML.
- **RN-PLAN-02:** **Plan Profesional** → Máximo **10** sucursales activas. **SÍ** permite reportes con IA y módulo ML.
- **RN-PLAN-03:** Los límites deben ser **configurables** desde el backend (no hardcodeados).
- **RN-PLAN-04:** Toda validación debe realizarse **en el backend**. No confiar solo en ocultar botones en el frontend.
- **RN-PLAN-05:** Si la suscripción está **VENCIDA/SUSPENDIDA/CANCELADA**, solo se permite **consulta en modo lectura limitada** o se bloquea la operación según corresponda.

## Flujo Normal

1. **Interceptar solicitud.** El `PlanGuard` intercepta la solicitud que requiere validación (crear sucursal, generar reporte IA, acceder a dashboard ML).
2. **Obtener contexto.** Se obtiene `empresa_id` del token JWT y se consulta su suscripción activa con su plan.
3. **Validar límites.** Según la operación, se cuenta cuántas sucursales activas tiene la empresa y se compara con `max_sucursales`.
4. **Validar funcionalidades.** Si la operación requiere `permite_reportes_ia` o `permite_analitica_ml`, se verifica el flag del plan.
5. **Autorizar.** Si pasa todas las validaciones, se continúa con el flujo normal.
6. **Denegar.** Si falla, se retorna `403 Forbidden` con mensaje claro.

## Flujos Alternativos

| Código | Descripción | Acción |
|---|---|---|
| **FA-01** | Empresa Básico intenta crear 3ª sucursal (ya tiene 2 activas) | Rechazar con `"Límite de sucursales alcanzado para el plan Básico (máximo 2)"`. |
| **FA-02** | Empresa Básico solicita reporte con IA | Rechazar con `"Esta funcionalidad requiere plan Profesional"`. |
| **FA-03** | Empresa Básico intenta acceder al dashboard ML | Rechazar con `"Módulo de analítica ML disponible solo para plan Profesional"`. |
| **FA-04** | Suscripción vencida | Restringir operaciones de escritura. Permitir solo consultas mínimas o denegar según endpoint. |

## Trazabilidad ICONIX

| Elemento | Referencia |
|---|---|
| **Requisito(s)** | RF18, RF19, RF20, RF21 |
| **Diagrama de Robustez** | `04_Diagramas_Robustez/CU30_Robustez.puml` |
| **Diagrama de Secuencia** | `05_Diagramas_Secuencia/CU30_Secuencia.puml` |
| **Clases involucradas** | `Empresa`, `Plan`, `Suscripcion`, `Sucursal`, `PlanGuard`, `TenantGuard` |
| **Pruebas** | CP-27, CP-28, CP-47 |
