# Despliegue de FashionStore

Rama preparada: `feat/parcial2-vestidor-bitacora-reembolsos-despliegue`.

La aplicación web y la API están listas para configurar el alojamiento. Todavía
no se han creado servicios externos ni publicado una URL de producción.

## Arquitectura propuesta para el parcial

| Componente | Servicio | Configuración del proyecto |
| --- | --- | --- |
| Web Angular / PWA | Render Static Site | `frontend-web`, salida `browser/browser` |
| API FastAPI | Render Web Service | `backend`, Python, puerto `$PORT` |
| PostgreSQL | Neon Free | `DATABASE_URL` externa con `sslmode=require` |

Las condiciones actuales de los planes están en [Render](https://render.com/docs/free)
y [Neon](https://neon.com/pricing). El servicio web gratuito de Render se suspende
tras 15 minutos sin tráfico y puede tardar alrededor de un minuto en despertar.
Esto afecta la primera llamada a la API; la web estática permanece disponible.
La base gratuita de Render vence después de 30 días, por lo que se propone Neon
para conservar la base del parcial sin depender de ese periodo de prueba.
Los planes gratuitos tienen límites de uso; revisar los paneles de cada proveedor.

## 1. Preparar la base de datos

1. Crear una cuenta y un proyecto PostgreSQL en Neon.
2. Obtener la cadena de conexión PostgreSQL con SSL. Guardarla en el panel del
   alojamiento como `DATABASE_URL`, sin incluirla en GitHub ni enviarla por chat.
3. Elegir los datos iniciales: migrar la base local conserva catálogo, ventas,
   inventario, usuarios y bitácora. Desplegar el código por sí solo no copia esos
   datos. Guardar un respaldo antes de la migración.
4. Si se elige una base nueva con datos de demostración, ejecutar `seed.py` una
   sola vez contra esa base. El seed crea cuentas con credenciales conocidas y
   restablece usuarios demo; no debe ejecutarse en cada arranque.

## 2. Configurar API y web

El archivo [`render.yaml`](render.yaml) define ambos servicios y apunta a la rama
indicada. `autoDeployTrigger: off` deja los despliegues siguientes como manuales.
Crear un Blueprint inicia su primer despliegue al aplicarlo.

Se puede usar **New → Blueprint** en [Render Dashboard](https://dashboard.render.com/),
conectar este repositorio y seleccionar expresamente la rama preparada. Si la
pantalla abre `main`, cambiar de rama antes de continuar.

Revisar los nombres de los servicios antes de aplicar el Blueprint. Si ya existen
servicios con esos nombres, Render puede asociar la configuración con ellos.
Para una instalación separada, cambiar ambos nombres antes de crearla.

También se pueden crear primero la API y después el sitio estático desde el panel:

| Campo | API | Web |
| --- | --- | --- |
| Rama | Rama preparada | Rama preparada |
| Root Directory | `backend` | `frontend-web` |
| Build Command | `pip install -r requirements.txt` | `npm ci && npm run build` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` | No aplica |
| Publish Directory | No aplica | `browser/browser` |
| Health Check Path | `/api/health` | No aplica |
| Ruta SPA | No aplica | `/*` → `/index.html`, tipo Rewrite |

Crear los servicios por separado permite conocer la URL real de la API antes de
configurar la web. No asumir que una URL sugerida está libre: usar la URL que
Render asigne a cada servicio.

## 3. Variables necesarias

En la API:

| Variable | Valor |
| --- | --- |
| `DATABASE_URL` | Conexión privada de Neon con SSL |
| `SECRET_KEY` | Secreto aleatorio; el Blueprint lo genera automáticamente |
| `BACKEND_CORS_ORIGINS` | Lista JSON con la URL HTTPS real de la web |
| `FRONTEND_URL` | URL HTTPS real de la web, sin `/api` |
| `AUTO_SEED` | `false` |
| `ALLOW_DEMO_PASSWORD_RESET` | `false` |

Ejemplo público de CORS, reemplazando el dominio por el real:

```text
["https://mi-tienda.onrender.com"]
```

En la web:

| Variable | Valor |
| --- | --- |
| `FASHIONSTORE_API_URL` | URL HTTPS real de la API, terminada en `/api` |
| `NODE_VERSION` | Valor del Blueprint, compatible con Angular 21 |

Después de cambiar `FASHIONSTORE_API_URL`, reconstruir y desplegar la web: el
comando de build genera `app-config.js`. Después de cambiar CORS o la conexión
de la base, volver a desplegar la API.

Si se crean ambos servicios mediante Blueprint y sus URLs definitivas difieren
de las configuradas inicialmente, corregir las variables anteriores en el panel
y volver a desplegar. Los campos `sync: false` solicitan su valor al crear el
Blueprint; para servicios existentes hay que configurarlos desde el panel.

## 4. Comprobar el despliegue

1. Abrir `https://URL-API/api/health`: debe indicar API y base de datos `ok`.
2. Abrir la web desde su URL HTTPS y comprobar catálogo y sucursales.
3. Iniciar sesión y comprobar una operación de prueba, su movimiento de stock y
   su registro en la bitácora.
4. Comprobar reembolso parcial, saldo neto y reporte de devoluciones.
5. Probar el vestidor concediendo permiso de cámara. La cámara necesita HTTPS o
   localhost; el seguimiento corporal necesita descargar su modelo.

Los reportes exportados se generan desde los resultados guardados en PostgreSQL;
no necesitan conservar archivos de prueba del equipo local.
Los pagos y reembolsos bancarios siguen siendo una simulación, incluso desplegados.

## Aplicación Android

Una vez que la API esté publicada, compilar desde `movil` con su URL real:

```powershell
flutter build apk --release --dart-define=API_URL=https://URL-API/api
```

Usar HTTPS y sustituir `URL-API`; `localhost` y `10.0.2.2` son direcciones de
desarrollo. El APK se instala en el dispositivo; Render aloja la API y la web.

## Referencias verificadas

- [Blueprint YAML de Render](https://render.com/docs/blueprint-spec)
- [Variables de entorno](https://render.com/docs/configure-environment-variables)
- [Límites del plan gratuito de Render](https://render.com/docs/free)
- [Plan gratuito de Neon](https://neon.com/pricing)
- [Compatibilidad de Angular y Node.js](https://angular.dev/reference/versions)
