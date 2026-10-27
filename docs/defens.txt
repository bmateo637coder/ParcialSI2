# FashionStore — Guía de defensa del proyecto

Resumen técnico del sistema SI2 Parcial 1 (ciclo de desarrollo: segunda entrega).
Documento de apoyo para exponer la arquitectura, decisiones de diseño y despliegue
ante el docente.

---

## 1. Qué es el proyecto

E-commerce de moda multi-plataforma llamado **FashionStore**: un catálogo en línea con
carrito, caja registradora (POS), probador virtual, reportes por voz y exportables,
promociones, reservas, portal de proveedor, panel de administración y chatbot con
memoria. Disponible como **web** (Angular) y como **app móvil** (mismo frontend), ambas
alimentadas por una única **API REST** (FastAPI).

## 2. Arquitectura general (cliente–servidor)

```
proyecto C/
├── backend/          → API REST (Python / FastAPI) — Railway
├── frontend-web/     → Tienda web (Angular) — Railway
└── movil/            → App móvil (Ionic/Capacitor)
```

Principio rector: **una sola API, muchos consumidores**. El frontend web y la app móvil
consumen exactamente los mismos endpoints; toda la lógica de negocio y la persistencia
viven en el backend. El cliente jamás accede a la base de datos directamente.

## 3. Backend (FastAPI)

### Stack y capas

```
backend/app/
├── api/        → routers (endpoints HTTP por dominio)
├── models/     → modelos SQLAlchemy (tablas)
├── schemas/    → validación de entrada/salida (Pydantic)
├── services/   → lógica de negocio (capa de servicios)
├── core/       → configuración, base de datos, seguridad
└── utils/      → helpers
```

### Números reales (verificados en el código)

- **87 endpoints** en 9 routers:
  - `products` (27), `commerce` (19), `auth` (6), `inventory` (6), `users` (6),
    `branches` (5), `promotions` (4), `assistant` (4), `providers` (8), `reports` (2).
- **26 modelos** de base de datos: `User`, `Role`, `Product`, `ProductVariant`,
  `Inventory`, `Order`, `CartItem`, `Reservation`, `Promotion`, `Branch`, `Provider`,
  `Category`, `Season`, `Collection`, `ChatConversation`, `ChatMessage`, `Size`,
  `Color`, `Payment`, `Notification`, etc.
- **5 roles** sembrados: Administrador, Cliente, Cajero, Encargado de Sucursal,
  Proveedor.

### Patrones que se pueden defender

1. **Separación por capas**: los routers no contienen lógica de negocio; solo validan
   con Pydantic y delegan en `app/services/`, que orquesta los modelos. Es el patrón
   *repositorio + capa de servicios*.
2. **Respuesta uniforme**: todos los endpoints devuelven el mismo sobre JSON
   `{ success, data, error }`.
3. **Autorización por rol**: JWT en login, guards por rol en el frontend y verificación
   de permisos en el backend (solo el rol correcto alcanza ciertas rutas).

### Base de datos

- **SQLite en volumen persistente** (`/var/lib/postgresql/data/fashionstore.db`).
- Decisión deliberada: el plan gratuito de Railway no permite Postgres sin costo, así
  que el archivo SQLite vive en un volumen que **no se pierde entre despliegues**.
- Como se usa SQLAlchemy, migrar a Postgres en el futuro es solo cambiar la URL de
  conexión (`DATABASE_URL`), sin tocar el código.
- **Seed idempotente**: al arrancar, se crean tablas y se siembran roles, categorías,
  temporadas, 10 productos y 6 usuarios solo si la base está vacía. El login de demo del
  admin es `admin@fashionstore.com` / `admin123`.

## 4. Frontend web (Angular)

- **Standalone components** (Angular moderno, sin NgModules).
- **Routing con guards por rol**: `AuthGuard`, `StaffGuard`, `AdminGuard`,
  `ReportsGuard`, `ProviderGuard`. Cada tipo de usuario ve solo lo que su rol permite.
- Módulos/features: catálogo, detalle de producto, carrito, POS (caja), vestidor
  virtual (probador con overlay de tinte sobre una prenda), sucursales, reportes
  (KPI, exportación CSV con BOM, impresión PDF, lectura por voz), promociones,
  reservas, portal de proveedor, dashboard admin, chatbot con memoria.
- Configuración por entorno: `environment.prod.ts` apunta a la API real desplegada.

## 5. App móvil (`movil/`)

- Ionic/Capacitor sobre el mismo código Angular, reutilizando el catálogo, el vestidor
  y el POS desde un dispositivo.
- Reutiliza la misma API del backend (no hay lógica duplicada).

## 6. Despliegue en Railway (en línea)

| Servicio | URL | Estado |
|---|---|---|
| Web | https://web-production-df007d.up.railway.app | 200, responsive |
| API | https://api-production-a70b.up.railway.app | `/api/health` 200, catálogo con 10 productos |

- Desplegado con **Infraestructura como Código** (`railway.json` + `.railwayignore`),
  en la rama `parcial-21/09`.
- El backend automáticamente crea tablas y ejecuta el seed al iniciar.
- La web es **responsive**: verificada a 375 px (viewport móvil) sin desbordes
  horizontales en catalogo, detalle, auth, carrito y POS (fix en `styles.css` con
  media query `<= 640px` que hace wrap a los enlaces del navbar).
- **Railway corre en la nube**: el sitio sigue en línea aunque se apague la PC; solo se
  detienen los dev-servers locales (`:8001` backend, `:4200` web).

## 7. Seguridad

- Autenticación con **JWT** y passwords con **bcrypt** (nunca en texto plano).
- **CORS** restringido a los orígenes permitidos (web desplegada + localhost).
- **Validación de entrada** con schemas Pydantic en cada endpoint (no se confía en la
  entrada del cliente).
- **Secretos en variables de entorno** (`SECRET_KEY`, `DATABASE_URL`,
  `BACKEND_CORS_ORIGINS`), nunca hardcodeados ni commiteados.
- La URL de la API y el origen CORS vienen de configuración de despliegue, no del
  código fuente.

## 8. Preguntas frecuentes del docente (con respuesta)

**¿Por qué 3 frentes?**
Porque el enunciado pide multi-plataforma. Un backend central alimenta la web de cliente
y la app móvil de tienda; es el argumento central del modelo cliente–servidor.

**¿Dónde está la lógica de negocio?**
En `backend/app/services/`, separada de routers y modelos. Se puede señalar en el código.

**¿Cómo se controla el acceso?**
JWT después del login, guards por rol en el frontend y verificación de permisos en el
backend. Solo el rol correcto ve ciertas rutas.

**¿Por qué SQLite y no Postgres?**
El plan gratuito de Railway no incluye Postgres sin pagar. SQLite en volumen persistente
resuelve la persistencia sin costo, y gracias a SQLAlchemy migrar es solo cambiar la URL.

**¿Cómo se aseguran los datos?**
Validación Pydantic en cada entrada, bcrypt para contraseñas, CORS restringido y
secretos en variables de entorno.

---

*Archivo generado para apoyo en la exposición. No contiene datos sensibles.*
