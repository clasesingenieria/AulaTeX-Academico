**Ficha Técnica — Plataforma `vTaxi` (taxis concesionados) — borrador rellenado**

1. Identificación
- Nombre de la aplicación: vTaxi
- Versión: 0.3.5
- Entidad legal: [Razón Social de la empresa] (ej. vTaxi S.A. de C.V.)
- RFC: [RFC-XXXX000000]
- Representante legal: [Nombre del representante], [Cargo], correo: [responsable@ejemplo.com], teléfono: [+52 81 1234 5678]

2. Resumen funcional
- Objeto: plataforma PWA y API para gestión, despacho y control operativo de taxis concesionados en Nuevo León.
- Usuarios: central de despacho (operadores y administradores), conductores concesionados, supervisores y pasajeros.

3. Arquitectura general
- Componentes principales:
	- Servidor API Node.js (archivo principal: [server/index.js](server/index.js#L1)).
	- Base de datos PostgreSQL (contenedor `postgres` en `docker-compose.yml`).
	- Redis para coordinación y caché (contenedor `redis`).
	- PWA frontend servido por el mismo contenedor (carpeta `web`).
	- Proxy reverso opcional (Caddy) para HTTPS y gestión de certificados (ver [docker-compose.yml](docker-compose.yml#L1)).

	Diagrama simplificado:
	Frontend (PWA) <-> Proxy (Caddy) <-> App (Node.js) <-> Postgres / Redis

4. Endpoints de interés (implementación y ejemplos)
- `GET /api/health` — comprobación de salud.
- WebSocket: `/events` — canal autenticado para operadores/choferes (ver [server/index.js](server/index.js#L1220)).
- WebSocket: `/passenger-events` — canal para pasajeros con token pasajero.
- `POST /api/drivers` — (uso interno/administrativo) registro/actualización de conductores.
- `POST /api/vehicles` — (uso interno/administrativo) registro/actualización de vehículos.
- `POST /api/padron/upload` — (propuesto) endpoint para recepción de padrón en entorno integrado o entrega por archivo cifrado.

5. Autenticación y autorización
- Mecanismo actual: tokens estáticos para entornos locales (`VTAXI_DISPATCHER_TOKEN`, `VTAXI_DRIVER_TOKENS_JSON`) y credenciales manejadas por `AuthService` (archivo: [server/auth.js](server/auth.js#L1)).
- Roles soportados: `dispatcher`, `driver`, `customer` (y `admin` para paneles administrativos).

6. Modelos de datos (campos principales)
- Conductor (`driver`): `driverId`, `nombre`, `licenciaTipo`, `licenciaNumero`, `fechaExpedicion`, `icetCertificadoRef`, `telefono`, `email`, `vehiculos` (lista de `vehicleId`).
- Vehículo (`vehicle`): `vehicleId`, `placas`, `marca`, `modelo`, `anio`, `vin`, `tarjetonId`, `seguroValidoHasta`.
- Registro padron (CSV): `driverId,driverNombre,driverLicenciaTipo,driverLicenciaNumero,driverTelefono,vehicleId,placas,marca,modelo,anio,vin,tarjetonId,fechaRegistro`.

7. Seguridad y privacidad (resumen)
- Transporte: TLS/HTTPS obligatorio. En despliegue local el certificado se encuentra en `.vtaxi/web-tls/`.
- Entrega de padrones: archivos cifrados (AES-256) y firmados (HMAC-SHA256) o entrega mediante canal TLS autenticado según lo que exija IMA.
- Cifrado en reposo: datos sensibles cifrados y con control de acceso y rotación de claves.
- Logs y auditoría: retención mínima recomendada 12 meses, con trazabilidad de eventos y accesos.

8. Mecanismos de emergencia y trazabilidad
- Botón de pánico: genera evento con `driverId`, `lat`, `lng`, `timestamp`, `rideId` (si aplica) y nivel de gravedad.
- Registro inmutable de eventos en la base de datos y notificación a la central (webhook + persistencia).

9. Requisitos operativos y pruebas que suele solicitar IMA
- Entorno de pruebas: credenciales sandbox y endpoints de demostración accesibles desde la oficina de IMA.
- Pruebas solicitadas: alta de conductor y vehículo, envío de padrón cifrado y verificación, simulación de evento de pánico y revisión de la traza de auditoría.

10. Entregables técnicos para la autoridad
- Documentación API (OpenAPI/Swagger) — se recomienda `docs/openapi.yaml` con los endpoints mínimos.
- Imagen Docker de demostración y credenciales sandbox para pruebas.
- Ejemplo de archivo de padrón cifrado y script de verificación.

11. Contactos y responsables
- Responsable técnico (CTO): [Nombre CTO] — correo: dev@vtaxi.local
- Responsable legal: [Nombre abogado] — correo: legal@vtaxi.local
- Enlaces útiles del repositorio: [docker-compose.yml](docker-compose.yml#L1), [server/index.js](server/index.js#L1), [server/auth.js](server/auth.js#L1).

---
Notas y siguientes pasos sugeridos:
- Completar los campos entre corchetes con datos reales (RFC, representante, contactos).
- Generar `docs/openapi.yaml` con los endpoints mínimos solicitados por IMA.
- Preparar un script en `scripts/` para exportar el padrón en CSV y cifrarlo (`scripts/padron-export.ps1` / `scripts/padron-export.sh`).

Instrucciones: rellena los campos marcados y adjunta diagramas o exports de la base de datos de prueba donde se muestren los campos solicitados.
