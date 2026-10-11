# vTaxi

PWA para una base de taxis empresariales. Los clientes solicitan viajes, la
central los publica y valida asignaciones, y los taxistas reportan cada etapa
en tiempo real desde el movil.

## Documentación de operación

El despliegue público actual usa **Docker Compose y Caddy** en
**https://16.58.100.160/**. AWS ECS/CloudFront y el hub Azure son alternativas
separadas, no el mecanismo de publicación de esta IP.

La [guía de operación y accesos](docs/OPERACION-Y-ACCESOS.md) reúne los paneles por
rol, la administración web/CLI, la persistencia PostgreSQL, recuperación local,
respaldo cifrado, mensaje de WhatsApp y publicación Docker, con sus límites actuales.

- [Arquitectura y contrato API](docs/ARCHITECTURE.md).
- [Sobres cifrados y bootstrap local](.vtaxi/README.md).
- [Ciclo de vida y procedimientos](docs/VTAXI-LIFECYCLE.md).
- [Alternativa AWS ECS](docs/AWS-RUNBOOK.md).

## Alcance actual

- Solicitudes de cliente con horario, origen, destino y unidades requeridas.
- Aprobacion o rechazo de solicitudes y asignaciones por la central.
- Cupos compartidos y asignacion atomica por taxista hasta cubrir la demanda.
- Ciclo operativo: solicitado, publicado, aceptado, validado, en camino, en sitio,
  en viaje y completado.
- Monitoreo central de unidades validadas, llegadas, en curso y terminadas.
- Perfil de conductor editable con permisos separados para conductor y central.
- Mapa OpenStreetMap con flota y ruta vial calculada por OSRM.
- Apertura de navegacion externa y seguimiento GPS continuo del taxista.
- Sesiones HttpOnly, roles cliente/central/taxista y autorizacion por identidad.
- Modo pasajero sin cuenta para solicitudes inmediatas desde el mapa.
- Oferta geográfica directa a conductores con GPS vigente dentro de 4 km por defecto.
- PostgreSQL transaccional en produccion; JSON solo para demo local.
- PWA instalable, API REST y WebSocket filtrado por rol.
- Administración con resumen, directorio, filtros, paginación y confirmaciones.
- Credenciales PostgreSQL con hashes, rotación/revocación en caliente y protección del último administrador.
- CLI sobre la misma API, recuperación local y generación de mensajes WhatsApp con claves verificadas.

Los viajes programados de clientes corporativos mantienen la publicación y
validación de la central. Los viajes inmediatos de pasajero se publican al crear
la solicitud y el primer conductor elegible que los acepta queda asignado sin
intervención de la central. El pasajero recibe un acceso privado temporal para
seguir o cancelar la búsqueda antes de la asignación.

No incluye pagos ni notificaciones push. Las métricas disponibles no sustituyen
una plataforma de observabilidad de producción.

## Aplicación Android híbrida

La preparación Android se encuentra en [`mobile/android`](mobile/android/README.md).
Es un shell `WebView` sin dependencia de VPN cuyo origen se configura durante la
compilación. La PWA actual está en `https://16.58.100.160/`; revisa la configuración
Gradle antes de generar el APK. Un APK anterior no cambia de origen al publicar la
web y no se debe asumir que ya usa esta IP.

## Requisitos

- Node.js 20 o posterior.
- Conexion a internet para OpenStreetMap, OSRM y las tipografias.
- Para Android: Android Studio, Android SDK 35 y JDK 17.

## Inicio rapido

En Windows, ejecutar `setup.bat` sin argumentos prepara y sirve la web con Docker:

```powershell
.\setup.bat
```

Equivale a `setup.ps1 -InstallPrerequisites -WebDocker`. Detecta o instala Docker
Desktop/WSL 2 y OpenSSL, genera `.env` con claves aleatorias y permisos restringidos
si no existe, y crea un certificado local en `.vtaxi/web-tls`. Conserva las claves,
los certificados y los datos existentes. Construye la imagen con Node.js y sus
dependencias dentro del contenedor, ejecuta migraciones y carga el catálogo; espera
a que PostgreSQL, Redis y la web estén saludables. No requiere Node.js en Windows
ni prepara Android, simuladores, secretos AWS o el proxy público.

La configuración nueva publica solo en **https://localhost:8443/**. El certificado
es autofirmado: el navegador mostrará un aviso hasta que se confíe en él. Para
confiar en el certificado generado, de forma opcional y solo para el usuario actual:

```powershell
Import-Certificate -FilePath .\.vtaxi\web-tls\server.crt -CertStoreLocation Cert:\CurrentUser\Root
```

Reinicia el navegador después. No importes certificados de origen desconocido.
La clave de central está en `VTAXI_DISPATCHER_TOKEN` dentro de `.env`; no compartas
ni versiones ese archivo. Los accesos iniciales incluyen un conductor (`taxi-01`)
y un cliente (`customer-regal`). Una configuración `.env` existente se respeta;
también puede cambiar el puerto o la exposición de red. El certificado debe ser
válido y corresponder a la clave: el instalador no reemplaza pares incompletos ni
certificados vencidos automáticamente.

El modo web verifica la salud de los contenedores, no ejecuta la suite de desarrollo.
Para el entorno completo de desarrollo, `setup.ps1` conserva su comportamiento:
valida Node.js/npm, restaura `package-lock.json` y ejecuta la revisión y las pruebas:

```powershell
.\setup.ps1 -InstallPrerequisites
npm start
```

Opciones para instalar, reconstruir o preparar servicios locales:

| Opcion | Resultado |
| --- | --- |
| `-WebDocker` | Prepara y sirve la web en Docker sin Android ni AWS; no admite `-Clean`, `-WithPostgres`, `-ResetDatabase`, `-WithExamples` ni `-SkipDocker` |
| `-InstallPrerequisites` | Instala Node.js LTS y Android Studio/JDK mediante winget cuando falten; `setup.bat` la activa por defecto |
| `-Clean` | Elimina `node_modules` antes de ejecutar `npm ci` |
| `-WithPostgres` | Inicia PostgreSQL con Docker, migra y carga datos demo |
| `-ResetDatabase` | Con `-WithPostgres`, elimina y recrea el volumen de datos |
| `-SkipValidation` | Omite revisión, pruebas y compilación del APK debug |
| `-WithExamples` | Inicializa los submódulos de `base/` sin instalar sus dependencias |
| `-SkipMasterPin` | No solicita PIN ni cifra secretos locales; pensado para CI sin `.vtaxi` sensible |
| `-SkipPortableAccess` | No exporta `.vtaxi/aws-access.enc` desde AWS durante setup |
| `-AwsEnvironmentName`, `-AwsRegion` | Seleccionan el stack AWS para exportar el bundle; valores predeterminados `vtaxi-dev`, `us-east-1` |
| `-SkipAndroid` | Omite SDK Platform 35, Build-Tools, variables Android y compilación del APK |
| `-SkipDocker` | Omite la instalación y el arranque de Docker Desktop; no puede combinarse con `-WithPostgres` |
| `-SkipSimulation` | Omite Android Emulator, imagen API 35 y creación de AVD |
| `-SimulationProfile auto\|pilot\|current\|full` | Selecciona capacidad de la granja; `auto` es el valor predeterminado |

Docker Desktop se instala y prepara por defecto desde `setup.bat` y `setup.ps1`
en Windows 10/11 con virtualización habilitada en BIOS/UEFI o como virtualización
anidada si el equipo es una VM. Se usa `winget` cuando está disponible; si Windows
no tiene App Installer, se descarga el instalador oficial de Docker y se valida
su firma Authenticode antes de ejecutarlo. Docker Desktop no es compatible con
Windows Server: allí el setup omite Docker salvo que se solicite `-WithPostgres`,
caso en el que exige PostgreSQL nativo/remoto o ejecutar vTaxi desde Windows 10/11.
Android también se prepara por defecto cuando su JDK ya está disponible o se usa
`-InstallPrerequisites`. El instalador inicia Docker Desktop y espera hasta cuatro
minutos a que Docker Engine y Compose estén listos. La primera instalación puede
requerir aceptar la licencia de Docker, habilitar WSL 2 o reiniciar Windows.
`setup.bat`, ejecutado como administrador, detecta e instala WSL 2 cuando falta y
solicita reiniciar; después se vuelve a ejecutar el mismo BAT. El proceso es
idempotente, verifica el SHA-256 de las Command-line Tools oficiales y configura
para el usuario `JAVA_HOME`, `ANDROID_HOME`, `ANDROID_SDK_ROOT` y `Path`. Desde el
Explorador de archivos se puede hacer clic derecho sobre `setup.bat`, elegir
**Ejecutar como administrador** y aceptar el aviso de Windows.

Los mismos parámetros funcionan con ambos lanzadores. Con argumentos explícitos,
el BAT los transmite sin añadir opciones; usa `-WebDocker -InstallPrerequisites`
para solicitar el modo web con instalación. Por ejemplo:

```powershell
.\setup.ps1 -InstallPrerequisites -Clean
.\setup.bat -InstallPrerequisites -WithPostgres
.\setup.ps1 -WithPostgres -ResetDatabase
.\setup.ps1 -WithExamples
.\setup.ps1 -SkipAndroid
.\setup.ps1 -SimulationProfile current
.\setup.ps1 -SimulationProfile standard
.\setup.ps1 -SimulationProfile full
```

La granja de emuladores, sus perfiles y recorridos están documentados en
[`simulation/README.md`](simulation/README.md). El setup crea los AVD pero no los
arranca, evitando consumir recursos al iniciar el equipo.

### Proyectos de referencia

Los proyectos externos de `base/` se fijan como submódulos Git cuando existe un
upstream verificable. No son dependencias de producción de vTaxi. Para una
clonación existente, inicialízalos y valida su estado con:

```powershell
npm run base:init
npm run base:status
npm run base:validate
```

Consulta [el catálogo y flujo de trabajo de los proyectos base](docs/BASE-PROJECTS.md)
antes de ejecutar o adaptar funcionalidades.

### PIN maestro para secretos locales

Al ejecutar `setup.bat` o `setup.ps1`, el instalador revisa tanto la variable
`VTAXI_MASTER_PIN` como los sobres `.vtaxi/*.enc`. Si cualquiera indica que ya
existe un PIN, pregunta primero si se desea conservarlo o crear uno nuevo; solo
después solicita el PIN actual para validarlo cuando no está cargado en el entorno.
Si no existe variable ni sobre cifrado, solicita dos veces el PIN inicial sin
mostrarlo. Debe tener al menos 12 caracteres. Al cambiarlo, los archivos `.enc` se
recifran de forma transaccional antes de continuar. En el mismo proceso, si AWS
CLI está disponible y el stack existe, setup exporta central, conductores y
clientes a `.vtaxi/aws-access.enc`; por eso no se necesita repetir el PIN en otra
terminal. El PIN protege las copias locales. En el despliegue actual, PostgreSQL
es la autoridad de las credenciales vigentes; entorno y Secrets Manager sirven
para bootstrap, no para sobrescribir una tabla de accesos inicializada.

Para solicitarlo sin que aparezca en pantalla ni en el historial:

```powershell
$securePin = Read-Host 'VTAXI_MASTER_PIN' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePin)
try { $env:VTAXI_MASTER_PIN = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
.\setup.ps1
```

No usar `setx`: persistiría el PIN en el perfil del usuario y no actualizaría la
terminal actual. Para CI o una inicialización sin secretos locales, usar
`-SkipMasterPin`. El valor vive en memoria del proceso y puede ser visible para
procesos con permisos equivalentes; no sustituye un gestor de secretos.

Los archivos locales se cifran como `.enc` con PBKDF2-SHA256 (210.000
iteraciones), AES-256-CBC y HMAC-SHA256. Ejemplos:

```powershell
# Cifrar manualmente
.\scripts\secret-vault.ps1 -Command Encrypt `
  -InputPath .\.vtaxi\central-access-aws.txt `
  -OutputPath .\.vtaxi\central-access-aws.txt.enc

# Descifrar temporalmente; eliminar el texto plano al terminar
.\scripts\secret-vault.ps1 -Command Decrypt `
  -InputPath .\.vtaxi\central-access-aws.txt.enc `
  -OutputPath .\.vtaxi\central-access-aws.txt
```

Perder el PIN hace irrecuperables los `.enc`. Cambiarlo requiere descifrar con el
PIN anterior y volver a cifrar con el nuevo. Nunca enviar el PIN junto con los
archivos cifrados.

Solo `.vtaxi/*.enc` puede versionarse. `.gitignore` mantiene bloqueados los
`.txt`, JSON, scripts de diagnóstico y cualquier otro contenido de `.vtaxi/`.
Antes de `git add`, verifica que el archivo termine en `.enc`, que el PIN tenga
alta entropía y al menos 12 caracteres, y que el PIN se conserve por un canal
separado. Un PIN corto como cuatro dígitos no es seguro frente a ataques offline.

Para portabilidad de la alternativa AWS se utiliza un sobre con las claves de
bootstrap de central, conductores y clientes. No reemplaza un backup PostgreSQL
ni incluye automáticamente claves emitidas desde la PWA:

```powershell
# Recomendado: solicita el PIN oculto, exporta desde AWS y cifra el bundle
.\scripts\aws\initialize-portable-access.ps1 -EnvironmentName vtaxi-dev -Region us-east-1
git add .vtaxi\README.md .vtaxi\aws-access.enc

# Alternativa si VTAXI_MASTER_PIN ya está definido
.\scripts\aws\export-access.ps1 -EnvironmentName vtaxi-dev -Region us-east-1

# En otra clonación, después de crear el stack, restaurar y reiniciar ECS
.\scripts\aws\import-access.ps1 -EnvironmentName vtaxi-dev -Region us-east-1
```

Para cambiar el PIN y recifrar atómicamente todos los `.enc`, el script solicita
el PIN actual y el nuevo sin mostrarlos:

```powershell
.\scripts\change-master-pin.ps1
```

No se pasa ningún PIN como argumento porque quedaría expuesto en historial y
lista de procesos. Tras cambiarlo, configura el nuevo valor en la terminal que
usarás y confirma que puedes descifrar antes de hacer commit.

Los archivos versionables de `.vtaxi` son `README.md` y los sobres `.enc`
necesarios, como `local-access.enc` y `aws-access.enc`. En el host también puede
existir `tls-runtime/`, ignorado pero necesario para Docker. No borrarlo ni
eliminar el respaldo local al limpiar los artefactos AWS. Revisar siempre la
previsualización antes de aplicar la limpieza:

```powershell
.\scripts\clean-vtaxi-local.ps1 -WhatIf
.\scripts\clean-vtaxi-local.ps1 -Confirm
# Solo después de generar y validar aws-access.enc:
.\scripts\clean-vtaxi-local.ps1 -IncludePlaintextSecrets -Confirm
```

Consulta [el ciclo de vida de `.vtaxi`](docs/VTAXI-LIFECYCLE.md) para la
clasificación de archivos permanentes, operativos y temporales.

Después de instalar Docker Desktop por primera vez, ábrelo, completa su
configuración y repite el último comando. También se puede preparar manualmente
con `npm ci`, `npm test` y `npm start`.
Abre `http://127.0.0.1:4173`. Para probar desde otro dispositivo de la LAN:

```powershell
$env:VTAXI_BIND='0.0.0.0'
npm start
```

## Control de versión local y publicada

La única fuente de versión es `package.json`. La interfaz muestra la versión del
shell web y el build que responde desde `/api/info`; si no coinciden aparece
`Desfase`. Antes de publicar una versión nueva:

1. Actualiza SemVer con `npm version <patch|minor|major> --no-git-tag-version`.
2. Ejecuta `npm run version:sync` para regenerar `web/version.js`.
3. Ejecuta `npm run check` y `npm test`.
4. Publica por Docker y comprueba `/api/info` y `/api/health` en la IP pública.
  El script Docker verifica salud y versión; el desplegador alternativo ECS
  verifica además el build esperado en CloudFront.

Para comparar la versión del workspace con la publicada:

```bash
node scripts/check-version.js https://16.58.100.160
```

URL local: `http://127.0.0.1:4173`. URL pública activa:
`https://16.58.100.160/`. `npm run version:compare` y la tarea `vTaxi: Estado AWS`
mantienen referencias a la alternativa CloudFront; no usarlos como comprobación
autoritaria de la IP Docker.

## Alternativa: despliegue AWS ECS Fargate

La aplicación puede desplegarse en AWS sin Docker local: AWS CodeBuild valida,
construye el contenedor y lo publica en ECR; CloudFormation crea CloudFront,
ALB, ECS Fargate, RDS PostgreSQL, Secrets Manager y CloudWatch.

```powershell
.\scripts\deploy-aws-fargate.ps1 -EnvironmentName vtaxi-dev -Region us-east-1
# En actualizaciones ordinarias, evita volver a cargar los datos demo:
.\scripts\deploy-aws-fargate.ps1 -EnvironmentName vtaxi-dev -Region us-east-1 -SkipSeed
```

En Linux, el flujo equivalente no requiere PowerShell:

```bash
./scripts/deploy-aws-fargate.sh --environment-name vtaxi-dev --region us-east-1 --skip-seed
```

Requiere AWS CLI v2 autenticado, Node.js 20+, `zip`, `unzip`, `openssl` y
`curl`. Si existe `.vtaxi/aws-access.enc`, requiere el PIN por entorno y Python 3
con `cryptography` para restaurar los secretos de bootstrap antes de las
migraciones. No es el publicador usado para `16.58.100.160`.

Consulta [la arquitectura AWS](docs/AWS-ARCHITECTURE.md) y
[el runbook completo](docs/AWS-RUNBOOK.md) antes de crear, modificar, recuperar o
eliminar recursos. Secrets Manager conserva secretos de infraestructura y
bootstrap; PostgreSQL conserva las credenciales vigentes una vez inicializado.
En `.vtaxi/` solo `README.md` y sobres autenticados `.enc` pueden versionarse.

Credenciales exclusivas del demo local:

- Central: `central-demo`
- Cliente: `cliente-demo`
- Unidad MTY-001: `MTY-001-demo` (el mismo patrón aplica hasta MTY-031)

Estos valores son únicamente del fallback de desarrollo sin producción. No son
credenciales de la IP pública ni defaults de bootstrap del Compose actual.

El GPS del navegador funciona en localhost o mediante HTTPS. No expongas el
servidor a la LAN por HTTP: configura `VTAXI_TLS_CERT`, `VTAXI_TLS_KEY`, tokens
propios y cookies seguras.

### HTTPS temporal por IP

El procedimiento PowerShell de esta sección corresponde a HTTPS directo temporal,
no al certificado público de Caddy en la IP actual. Espera `server.crt` y
`server.key` en el directorio TLS configurado; la utilidad Windows utiliza
`C:\ProgramData\vTaxi\tls`. Para generar un certificado autofirmado:

```powershell
.\scripts\configure-ip-tls.ps1 -PublicIp 172.174.242.218 -Port 8443
```

La URL resultante es `https://172.174.242.218:8443/`. El certificado temporal cifra
el tránsito, pero el navegador y Android no confiarán en él hasta instalar
`server.crt` explícitamente. Para operación real debe sustituirse por un
certificado público, preferentemente asociado a un dominio. El puerto también
debe autorizarse en Windows Firewall y en el Security Group de AWS; PostgreSQL y
Redis deben permanecer en loopback.

## Ejecución local autocontenida

El perfil `docker-compose.yml` ejecuta la plataforma en el host Docker:

- aplicación Node.js: límite de 2 CPU y 11 GB;
- PostgreSQL: 1 CPU y 4 GB, con volumen persistente;
- Redis: 0,5 CPU y 1 GB, con persistencia AOF;
- Caddy: 0,25 CPU y 512 MB. Las tareas transitorias de migración y catálogo son adicionales.

Requiere Docker Engine y Compose v2 en Linux, o Docker Desktop activo en un
Windows compatible. Los comandos siguientes usan utilidades PowerShell:

```powershell
npm run local:up
npm run local:status
npm run local:test
```

La aplicación queda en `https://127.0.0.1:8443` cuando existen los archivos TLS.
Las migraciones se ejecutan antes del arranque y las sesiones/eventos usan Redis.
Comandos adicionales:

```powershell
npm run local:logs
npm run local:down
.\scripts\local-container.ps1 reset  # borra volúmenes y reconstruye
.\scripts\local-container.ps1 seed   # carga datos demo una vez
```

Para cambiar las credenciales locales define `VTAXI_LOCAL_DB_PASSWORD`,
`VTAXI_DISPATCHER_TOKEN`, `VTAXI_DRIVER_TOKENS_JSON` y
`VTAXI_CUSTOMER_TOKENS_JSON` antes del primer inicio sobre una base vacía. El
servicio las importa con hash a PostgreSQL una sola vez; después se administran
desde **Administración** en la web y no se requieren para reinicios. Los límites
son máximos, no reservas obligatorias: Docker solo consume lo necesario hasta
alcanzarlos.

### Operación híbrida de administración

El administrador entra en **Administración**, con apartados de Resumen,
Personas y empresas, Accesos y Auditoría. Despacho y Flota conservan el mapa y
las acciones operativas. El directorio reúne los conductores registrados y las
cuentas vinculadas a accesos o viajes; no sustituye un catálogo completo de empresas.

Los accesos se buscan por nombre o identificador y se filtran por rol y estado,
con páginas de diez registros. En la PWA, emisión, rotación y revocación requieren
confirmación. El backend bloquea la revocación del último administrador activo
en una transacción. La clave nueva se borra de la pantalla al cerrar su diálogo.

La PWA publicada es la consola principal para emitir, rotar y revocar accesos.
Para automatización controlada o sesiones de soporte existe una CLI que usa la
misma API HTTPS y no accede directamente a PostgreSQL:

```bash
npm run admin -- access list
npm run admin -- access issue --role driver --subject taxi-01
npm run admin -- access rotate ID_CREDENCIAL
npm run admin -- access revoke ID_CREDENCIAL
npm run admin -- audit list --limit 100
```

La CLI solicita la clave de administrador sin eco; para un proceso no
interactivo puede recibirla por stdin. Ejecuta un comando cada vez. La CLI aplica
mutaciones sin una confirmación adicional. Los secretos emitidos se muestran una
sola vez y no deben añadirse a scripts, historial de shell ni archivos de configuración.

Recuperación administrativa local y mensaje para copiar a WhatsApp:

```bash
bash scripts/set-admin-from-master-pin.sh
python3 scripts/whatsapp_message.py
```

Son operaciones distintas: la primera sustituye una clave administrativa activa;
la segunda verifica claves del respaldo y solo imprime un mensaje con las cinco
primeras unidades y los clientes, excluyendo la clave central. No escribas el PIN
en el chat. Los requisitos y límites están en la
[guía de operación y accesos](docs/OPERACION-Y-ACCESOS.md).

### Publicar Docker en una IP pública Linux

Para publicar el stack Docker en una VM Linux con Caddy en `80/443`, usa:

```bash
bash ./scripts/deploy-docker-public.sh --public-ip 16.58.100.160
```

El script valida y prueba la aplicación, genera el certificado TLS interno de
30 días si falta, reconstruye el stack y verifica salud y versión a través de
Caddy usando loopback. Comprueba también la IP desde otra red. Autoriza `80/tcp`
y `443/tcp`; `443/udp` permite HTTP/3. Revisa el firewall de Linux y las reglas de
red de la VM: el script no las cambia.

PostgreSQL y Redis están limitados a loopback. **El puerto directo `8443` se
publica en todas las interfaces por defecto**; para limitarlo también, antepón
`VTAXI_HTTPS_BIND=127.0.0.1` al comando de publicación. No expongas externamente
`5432`, `6379` ni `8443`.

## PostgreSQL local sin contenerizar la aplicación

```powershell
docker-compose up -d postgres
$env:DATABASE_URL='postgresql://vtaxi:vtaxi_local_only@127.0.0.1:5432/vtaxi'
npm run db:migrate
npm run db:seed
npm start
```

En `NODE_ENV=production` se requiere `DATABASE_URL` o la configuración `PGHOST`.
Los secretos iniciales de autenticación se requieren para bootstrap de una tabla
de accesos vacía, no para cada reinicio de una base inicializada. Las aceptaciones
usan transacciones, bloqueo de fila y restricciones únicas por viaje/conductor.

## Despacho inmediato de pasajero

En la pantalla inicial, **Pedir un taxi** no requiere una clave de operador. El
pasajero obtiene su origen por GPS y puede ajustar origen y destino tocando el
mapa. El servidor fija una unidad, salida inmediata y un radio máximo predeterminado de 4 km;
no acepta que el navegador amplíe el radio ni cambie el estado. Solo reciben la
oferta conductores disponibles con GPS real de hasta 120 segundos y precisión
máxima de 200 metros. Estas políticas pueden ajustarse con
`VTAXI_IMMEDIATE_RADIUS_METERS`, `VTAXI_DRIVER_LOCATION_MAX_AGE_MS` y
`VTAXI_DRIVER_LOCATION_MAX_ACCURACY_METERS`.

Al solicitar por primera vez, el servidor crea una identidad anónima para ese
navegador mediante la cookie `vtaxi_passenger`, con `HttpOnly`, `SameSite=Strict`
y duración predeterminada de 30 días. No pide usuario, contraseña ni clave y el
JavaScript no puede leer el valor privado. PostgreSQL y el almacén JSON guardan
únicamente su hash. Al volver desde el mismo navegador se restaura la solicitud
más reciente; otro navegador no puede consultarla. La duración se configura con
`VTAXI_PASSENGER_SESSION_TTL_MS`.

La cancelación se permite mientras el viaje siga publicado y sin asignación. El
pasajero usa consultas HTTP y el canal específico `/passenger-events`, no el
WebSocket operativo: solo recibe la proyección limitada de su propio viaje.

## Ubicacion GPS

El taxista activa y detiene el seguimiento desde el boton GPS. La PWA usa
`watchPosition`, publica como maximo cada 10 segundos o tras 25 metros, y envia
precision, rumbo, velocidad y hora de captura. La central distingue ubicaciones
demo, en vivo, retrasadas y vencidas. Los navegadores pueden suspender el GPS
cuando la PWA queda en segundo plano; un piloto debe probar cada modelo de movil.

## Mapas y navegacion

- **Leaflet** renderiza el mapa en la PWA.
- **OpenStreetMap** entrega los mosaicos cartograficos.
- **OSRM** calcula geometria vial, distancia y duracion mediante `/api/route`.
- **Google Maps Directions URL** abre la navegacion giro a giro en el telefono;
  no requiere una API key porque es un enlace externo, no el SDK de Google Maps.

El servidor publico de OSRM es apropiado solo para desarrollo. En operacion,
configura `VTAXI_ROUTING_URL` con una instancia administrada o propia. El punto
demo de Regal Rexnord Planta 2 debe sustituirse por la coordenada validada del
acceso vehicular antes del piloto.

## Alternativa histórica: hub Azure

Este flujo corresponde al hub Windows/Azure y no publica el Docker de la IP
actual. `scripts/deploy-hub.ps1` publica en ese hub de WireGuard:

```powershell
.\scripts\deploy-hub.ps1 -WhatIf
.\scripts\deploy-hub.ps1
.\scripts\deploy-hub.ps1 -Public
```

La fuente permanece en `Documents\vTaxi`. El script sincroniza servidor, PWA,
migraciones y dependencias hacia `E:\vTaxi`, preserva `data/runtime.json` y
reinicia la tarea `vTaxi Web`. Las credenciales se generan una sola vez en
`.vtaxi/deployment-secrets.json`, que está ignorado por Git.

Antes de cada actualización, si existen datos locales, se guarda una copia en
`E:\vTaxi\data\backups` y se conservan las 20 más recientes. Al abrir vTaxi como
workspace en VS Code también están disponibles las tareas **vTaxi: Validar**,
**vTaxi: Probar** y **vTaxi: Publicar en Azure**.

La tarea **vTaxi: Vigilar y publicar** es opcional. Mientras esté activa agrupa
los cambios de `server/`, `web/`, `db/`, `data/demo.json` y los manifiestos;
ejecuta revisión y pruebas, y solo publica si ambas pasan. Se detiene con
`Ctrl+C`. Para comprobar el mismo pipeline una sola vez:

```powershell
.\scripts\watch-deploy.ps1 -Once
```

URL de staging: `https://redvpn-consola.eastus.cloudapp.azure.com:4173`.
Reutiliza el certificado de consola redvpn y el firewall acepta únicamente la
malla `10.10.0.0/24`.

El modo `-Public` reutiliza el FQDN e IP pública de la VM, escucha en HTTPS 443
y configura Windows Firewall para acceso externo:
`https://redvpn-consola.eastus.cloudapp.azure.com`. La regla NSG `HTTPS` ya
permite 443 en Azure. El script usa Azure CLI con la suscripción y NSG del hub
para verificar ese requisito y crea `vTaxi-HTTPS` si falta. Esta etapa sigue
usando el almacén JSON de demostración; antes de operación formal debe migrarse
a PostgreSQL administrado.

## Comandos

| Comando | Uso |
| --- | --- |
| `npm run dev` | Servidor con reinicio al cambiar archivos |
| `npm start` | Servidor normal |
| `npm test` | Pruebas del dominio |
| `npm run check` | Revision sintactica de cliente y servidor |
| `npm run admin -- access list` | Metadatos de accesos por API HTTPS; no devuelve claves |
| `npm run admin -- audit list --limit 100` | Consulta auditoría de accesos |
| `bash scripts/set-admin-from-master-pin.sh` | Recuperación local: sustituye la clave de un administrador activo |
| `python3 scripts/access_keys.py show --role drivers` | Muestra secretos del respaldo local; pueden estar desactualizados |
| `python3 scripts/whatsapp_message.py` | Verifica claves del respaldo e imprime el mensaje; no envía WhatsApp |
| `bash scripts/deploy-docker-public.sh --public-ip 16.58.100.160` | Valida, reconstruye y publica por Docker |
| `npm run db:migrate` | Aplica migraciones PostgreSQL |
| `npm run db:seed` | Carga el demo en PostgreSQL |
| `npm run simulate:rexnord:inbound` | Publica una ruta no destructiva con dos recogidas en Apodaca y llegada a Rexnord Planta 2 a las 06:00 |

La simulación de entrada requiere `VTAXI_SIM_URL` y `VTAXI_SIM_SECRETS`. El archivo
de secretos debe ser local e ignorado por Git. Calcula el orden vial y las horas
de recogida hacia atrás desde las 06:00, reservando diez minutos de llegada.

## Estructura

```text
data/       Datos demo y fallback JSON no versionado
db/         Migraciones PostgreSQL
docs/       Arquitectura y hoja de ruta
infra/      Reserva para despliegue e infraestructura
scripts/    Preparacion local reproducible
server/     API, WebSocket y reglas del dominio
tests/      Pruebas node:test
web/        PWA mobile-first
base/       Referencias locales, excluidas de Git
```

Consulta [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) y
[docs/ROADMAP.md](docs/ROADMAP.md) para las decisiones y siguientes etapas.

## Datos locales

Sin `DATABASE_URL` ni `PGHOST`, fuera de producción el arranque lee `data/demo.json` y guarda cambios en
`data/runtime.json`. Este modo existe solo para demostracion local. Para volver
a los datos iniciales, detiene el servidor y elimina `data/runtime.json`.
