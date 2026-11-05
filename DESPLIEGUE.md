# Despliegue: Vercel + Neon

Rama: `feat/parcial2-vestidor-bitacora-reembolsos-despliegue`.

Se usarán dos proyectos Vercel Hobby y un proyecto Neon Free independiente.
No se utiliza Render ni se comparten sus cuotas. El `render.yaml` anterior
se conserva como referencia y no se aplica en este despliegue.
La preparación del repositorio no significa que ya exista una URL pública:
es necesario conectar las cuentas de Vercel y Neon.

Elegir **Hobby** y **Free**, sin activar pruebas Pro ni recursos pagos.
Vercel Hobby permite uso personal no comercial: sirve para el parcial con
pagos simulados; una tienda comercial real requiere revisar el alojamiento.

## 1. Crear Neon y guardar las conexiones

Crear un proyecto dedicado a FashionStore en Neon Free. En **Connect**,
obtener dos cadenas con `sslmode=require`:

- **Direct**, sin `-pooler` en el host: migraciones y preparación del esquema.
- **Pooled**, con `-pooler`: API en Vercel.

Copiar `backend/.env.deploy.example` a `backend/.env.deploy` y guardar la
conexión directa en `NEON_DATABASE_URL_DIRECT`. Ese archivo está ignorado por
Git. No enviar credenciales por chat ni incluirlas en archivos de ejemplo.

El origen se lee del `backend/.env` local. Se puede sobrescribir con
`SOURCE_DATABASE_URL` en `.env.deploy`.

## 2. Copiar los datos locales

La migración requiere PostgreSQL en origen y destino, y las herramientas
`pg_dump` y `pg_restore`. El script detecta sus instalaciones habituales en
Windows. El cliente debe ser compatible con el servidor de origen.

Desde PowerShell, dentro de `backend`:

```powershell
.\venv\Scripts\python.exe deploy.py migrate
.\venv\Scripts\python.exe deploy.py init
.\venv\Scripts\python.exe deploy.py check
```

`migrate` comprueba que el destino esté vacío y sea distinto del origen.
Crea un respaldo y manifiesto en `%LOCALAPPDATA%/FashionStore/backups`.
El respaldo y los conteos por tabla usan el mismo snapshot. Restaura en una
sola transacción y comprueba los registros. No utiliza `DROP`, `--clean`,
ni reemplaza una base con datos.

`init` aplica las migraciones compatibles y asegura los roles base sobre la
conexión directa de Neon. No ejecuta el seed ni restablece contraseñas.
`check` muestra los conteos por tabla sin imprimir credenciales.

No registrar operaciones locales durante el traslado final: los cambios
posteriores al snapshot no estarán en la copia remota. Estos comandos no
cambian automáticamente la conexión de la aplicación local.

Si el destino ya contiene tablas, el comando se detiene. No borrar esos datos.
Después de una copia exitosa se puede repetir `init` y `check`; para repetir
el traslado completo se necesita otro destino vacío.

Para empezar con una base nueva sin datos, ejecutar solo `init`. Esto no
copia el catálogo ni crea usuarios demo. El seed es una alternativa deliberada
para datos de demostración y modifica sus usuarios; no se ejecuta automáticamente.

## 3. Crear la API en Vercel

Importar el repositorio y configurar:

| Campo | Valor |
| --- | --- |
| Proyecto sugerido | `fashionstore-api`, usando un nombre disponible |
| Root Directory | `backend` |
| Framework | FastAPI |
| Python | 3.12, fijado en `.python-version` |
| Production Branch | La rama preparada indicada arriba |
| Build / Start | Detección de FastAPI; no usar un servidor `uvicorn` permanente |

`backend/vercel.json` configura la función `main.py` con duración máxima de
60 segundos. `.vercelignore` excluye entornos, bases locales, pruebas y reportes
temporales del paquete. Las funciones tienen los límites del plan gratuito.

Configurar estas variables en **Production** antes de desplegar:

| Variable | Valor |
| --- | --- |
| `DATABASE_URL` | Conexión **pooled** de Neon con SSL |
| `SECRET_KEY` | Secreto aleatorio de al menos 32 caracteres |
| `AUTO_INIT_DB` | `false` |
| `AUTO_SEED` | `false` |
| `ALLOW_DEMO_PASSWORD_RESET` | `false` |
| `BACKEND_CORS_ORIGINS` | Lista JSON con la URL HTTPS estable de la web |
| `FRONTEND_URL` | URL HTTPS estable de la web |

Generar el secreto localmente y guardarlo directamente en el panel.
Vercel establece `VERCEL=1`: en ese entorno el código rechaza SQLite,
secretos de desarrollo y creación automática del esquema. La API no mantiene
un pool local de conexiones; Neon proporciona el pool externo.

Crear ambos proyectos antes de publicar permite obtener sus dominios
estables y configurar CORS sin adivinar URLs. Usar las URLs asignadas por
Vercel: los nombres sugeridos pueden estar ocupados. No habilitar CORS
comodín para admitir todas las URLs de preview.

## 4. Crear la web en Vercel

Importar el mismo repositorio como un segundo proyecto:

| Campo | Valor |
| --- | --- |
| Proyecto sugerido | `fashionstore-web`, usando un nombre disponible |
| Root Directory | `frontend-web` |
| Framework | Angular |
| Node.js | 24.x, fijado en `package.json` |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | `browser/browser` |
| Production Branch | La rama preparada indicada arriba |

`frontend-web/vercel.json` incluye los comandos, rutas internas de Angular
y cabeceras para actualizar la PWA.

Variable en Production:

```text
FASHIONSTORE_API_URL=https://DOMINIO-REAL-API.vercel.app/api
```

El build genera `app-config.js` con esa URL pública. Rechaza la ausencia de
la variable y las URLs relativas o sin HTTPS en Vercel. No publica secretos.
No agregar `/api` al dominio de la web; solo a la conexión del backend.

En el proyecto de la API, completar las variables con la URL real de la web:

```text
BACKEND_CORS_ORIGINS=["https://DOMINIO-REAL-WEB.vercel.app"]
FRONTEND_URL=https://DOMINIO-REAL-WEB.vercel.app
```

Publicar primero la API y después la web. Cambiar variables requiere un nuevo
despliegue; cambiar la URL de la API requiere reconstruir Angular.
Usar el dominio de producción de la API: la protección de previews puede
bloquear llamadas del navegador. Las rutas privadas de FashionStore siguen
requiriendo su token de sesión propio.

## 5. Verificar la instalación

1. Abrir `https://DOMINIO-API/api/health`: `status=ok` y `database=ok`.
2. Abrir la web, seleccionar la tienda y comprobar catálogo y sucursales.
3. Iniciar sesión con un usuario migrado y comprobar una venta y su bitácora.
4. Comprobar stock descontado, reembolso parcial/total y ventas netas.
5. Descargar PDF/Excel y abrir una ruta interna directamente.
6. Probar la cámara del vestidor en HTTPS y la instalación de la PWA.

Los reportes se generan en memoria desde PostgreSQL y no necesitan persistir
archivos en Vercel. Las funciones limitan el tamaño de las peticiones/respuestas;
reportes muy grandes pueden necesitar otro método de descarga.
Los pagos y reembolsos bancarios siguen simulados.

## Android

Desde `movil`, con el dominio real de la API publicado:

```powershell
flutter build apk --release --dart-define=API_URL=https://DOMINIO-REAL-API.vercel.app/api
```

El APK usa la misma API y base que la web; no se aloja en Vercel.

## Referencias oficiales

- [FastAPI en Vercel](https://vercel.com/docs/frameworks/backend/fastapi)
- [Configuración](https://vercel.com/docs/project-configuration/vercel-json)
- [Plan Hobby](https://vercel.com/docs/plans/hobby)
- [Límites de funciones](https://vercel.com/docs/functions/limitations)
- [Neon Free](https://neon.com/pricing)
- [Conexiones directas y pooled](https://neon.com/docs/connect/connection-pooling)
