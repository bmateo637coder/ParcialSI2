# FICHA DE CASO DE USO - CU39

**Código:** CU39  
**Nombre:** Generar Reporte con Lenguaje Natural  
**Paquete:** P8 - Analítica, Reportes Generativos e IA/ML  
**Prioridad:** ALTA  
**Tipo:** Nuevo  

## Actores

- **Actor Principal:** Administrador de Empresa / Encargado de Sucursal
- **Actores Secundarios:** Servicio de IA (LLM), Backend (ReporteIAService)

## Objetivo

Permitir al usuario solicitar un reporte empresarial en lenguaje natural (texto o voz). El sistema debe interpretar la solicitud, validar filtros, ejecutar **consultas controladas** sobre datos reales del **tenant** autenticado, presentar resultados en tabla o gráfico y habilitar exportación a PDF/Excel. **Requiere plan Profesional.**

## Precondiciones

- Usuario autenticado, perteneciente a una empresa con **plan Profesional** y suscripción **ACTIVA**.
- Existen datos reales de ventas/reservas/inventario para esa empresa.
- Existe catálogo de reportes permitidos configurado en backend.
- Servicio de IA disponible o configurado.

## Postcondiciones

- Se crea registro en `SolicitudReporteIA` con `pregunta_natural`, `filtros_json`, `parametros_json`, `estado`.
- Se ejecuta consulta SQL **parametrizada** validada por el backend.
- Se muestra resultado en tabla/gráfico según el tipo detectado.
- Se puede exportar a PDF/Excel.

## Reglas de Negocio

- **RN-IA-01:** El backend **NUNCA** ejecuta SQL generado directamente por el LLM. Solo parámetros validados.
- **RN-IA-02:** El acceso a datos debe estar **SIEMPRE** limitado por `empresa_id`. No se permite cruzar información entre empresas.
- **RN-IA-03:** Solo empresas con **plan Profesional** pueden usar esta funcionalidad.
- **RN-IA-04:** Deben existir al menos **4 tipos distintos** de reportes funcionales con datos reales.
- **RN-IA-05:** Ante solicitudes ambiguas/incompletas, el sistema debe pedir aclaración o aplicar valores por defecto mostrando qué filtros se usarán.
- **RN-IA-06:** Solicitudes maliciosas o fuera del catálogo permitido deben ser **rechazadas** sin ejecutar consulta.
- **RN-IA-07:** Se admite entrada por **texto** o **voz** (extensión).

## Flujo Normal

1. **Validar acceso.** Se verifica plan Profesional y suscripción activa con `PlanGuard`.
2. **Ingresar solicitud.** El usuario escribe o dicta su pregunta en lenguaje natural.
3. **Enviar al backend.** Se envía `POST /reportes/ia` con `{pregunta_natural, empresa_id, usuario_id}`.
4. **Interpretar.** `ReporteIAService` envía la pregunta + **catálogo de reportes permitidos** al LLM solicitando **únicamente un JSON de parámetros** válido.
5. **Validar parámetros.** El backend valida tipo de reporte, filtros (fechas/sucursal/categoría/producto), agrupación contra esquema permitido.
6. **Consultar BD.** Se construye consulta **parametrizada** filtrando por `empresa_id` y ejecuta contra PostgreSQL.
7. **Formatear.** Se transforma el resultado a estructura para tabla/gráfico.
8. **Mostrar.** Se presenta al usuario con opción "Exportar a PDF/Excel".
9. **Guardar.** Se actualiza `SolicitudReporteIA` con resultado, estado `COMPLETADO`.

## Flujos Alternativos

| Código | Descripción | Acción |
|---|---|---|
| **FA-01** | Empresa con plan Básico | `PlanGuard` rechaza con `403 "Requiere plan Profesional"`. |
| **FA-02** | Solicitud ambigua o incompleta | El sistema solicita aclaración: "¿Para qué periodo deseas el reporte? ¿Todas las sucursales o alguna en particular?" |
| **FA-03** | Tipo de reporte no soportado | Rechazado. Se muestran ejemplos válidos al usuario. |
| **FA-04** | Intento de acceder a datos de otra empresa | Rechazado por `TenantGuard`. No se retorna información. |
| **FA-05** | Solicitud maliciosa (intento de SQL/borra datos) | Rechazado. Se registra en `SolicitudReporteIA` con estado `RECHAZADO`. |

## Trazabilidad ICONIX

| Elemento | Referencia |
|---|---|
| **Requisito(s)** | RF36, RF37, RF38, RF39 |
| **Diagrama de Robustez** | `04_Diagramas_Robustez/CU39_Robustez.puml` |
| **Diagrama de Secuencia** | `05_Diagramas_Secuencia/CU39_Secuencia.puml` |
| **Clases involucradas** | `SolicitudReporteIA`, `ReporteIAService`, `CatalogoReportes`, `LLMClient`, `PlanGuard`, `TenantGuard`, `Empresa` |
| **Pruebas** | CP-41, CP-42, CP-43, CP-44 |
