# FICHA DE CASO DE USO - CU27

**Código:** CU27  
**Nombre:** Registrar Empresa Contratante  
**Paquete:** P6 - Plataforma SaaS y Suscripciones  
**Prioridad:** ALTA  
**Tipo:** Nuevo

## Actores

- **Actor Principal:** Administrador de Plataforma
- **Actores Secundarios:** Sistema

## Objetivo

Registrar una nueva empresa contratante (tenant), crear su usuario administrador, asociar un plan y generar su suscripción activa.

## Precondiciones

- Existe al menos un plan registrado (Básico/Profesional).
- El Administrador de Plataforma está autenticado con rol `ADMIN_PLATAFORMA`.
- No existe otra empresa con el mismo NIT.

## Postcondiciones

- Se crea registro en `Empresa` con `empresa_id` único.
- Se crea usuario con rol `ADMIN_EMPRESA` vinculado a esa empresa.
- Se crea `Suscripcion` con estado `ACTIVA`, fechas de inicio/vencimiento.
- La empresa queda habilitada para operar con límites de su plan.

## Reglas de Negocio

- **RN-TENANT-01:** Cada empresa debe tener un **NIT único**.
- **RN-TENANT-02:** Todo registro comercial posterior debe ir asociado a `empresa_id`.
- **RN-TENANT-03:** El primer usuario creado será el **Administrador de Empresa**.
- **RN-TENANT-04:** La suscripción se crea obligatoriamente al registrar la empresa.

## Flujo Normal

1. **Ingresar datos.** El Administrador de Plataforma registra: razón social, NIT, contacto, plan a asignar.
2. **Validar.** Se verifica que no exista NIT duplicado y que el plan esté activo.
3. **Crear empresa.** Se crea la entidad `Empresa`.
4. **Crear administrador.** Se crea el usuario `ADMIN_EMPRESA` con credenciales iniciales.
5. **Crear suscripción.** Se crea `Suscripcion` con `fecha_inicio = hoy`, `fecha_vencimiento = hoy + 30 días` (o según configuración), `estado = ACTIVA`.
6. **Confirmar.** Se muestra mensaje de éxito con datos de la empresa creada.

## Flujos Alternativos

| Código | Descripción | Acción |
|---|---|---|
| **FA-01** | NIT ya registrado | Mostrar error "Ya existe una empresa con ese NIT". |
| **FA-02** | Plan inexistente o inactivo | Mostrar error "Plan no válido o inactivo". |

## Trazabilidad ICONIX

| Elemento | Referencia |
|---|---|
| **Requisito(s)** | RF15 |
| **Diagrama de Robustez** | `04_Diagramas_Robustez/CU27_Robustez.puml` |
| **Diagrama de Secuencia** | `05_Diagramas_Secuencia/CU27_Secuencia.puml` |
| **Clases involucradas** | `Empresa`, `Usuario`, `Role`, `Plan`, `Suscripcion` |
| **Pruebas** | CP-25 |
