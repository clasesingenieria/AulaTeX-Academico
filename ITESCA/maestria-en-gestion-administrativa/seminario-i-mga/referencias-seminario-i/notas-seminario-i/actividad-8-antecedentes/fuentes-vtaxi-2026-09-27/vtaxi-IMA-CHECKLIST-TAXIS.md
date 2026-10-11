**Checklist y formatos para presentación a IMA — Taxis concesionados**

1) Documentación legal (original o copia certificada)
- Acta Constitutiva de la empresa.
- Poder Notarial del representante legal.
- RFC y constancia fiscal (vigente).

2) Documentación técnica
- `Ficha Técnica` completa (ver `docs/FICHA-TECNICA-TAXIS.md`).
- Documentación de políticas de privacidad y tratamiento de datos.
- Diagrama de arquitectura y listado de endpoints públicos/privados.

3) Padrón inicial de vehículos y conductores (ejemplo y formato)
- Formato recomendado: CSV UTF-8 con encabezado exacto:
  - `driverId,driverNombre,driverLicenciaTipo,driverLicenciaNumero,driverTelefono,vehicleId,placas,marca,modelo,anio,vin,tarjetonId,fechaRegistro`
- Alternativa JSON: array de objetos con las mismas propiedades.
- Requisitos de entrega: archivo cifrado (AES-256) y firmado (HMAC-SHA256) o entregado vía canal seguro que proponga IMA.

4) Ejemplo de padrón (CSV)
driverId,driverNombre,driverLicenciaTipo,driverLicenciaNumero,driverTelefono,vehicleId,placas,marca,modelo,anio,vin,tarjetonId,fechaRegistro
DR-001,Juan Perez,E,ABC12345,8112345678,VH-001,NL-ABC-01,Nissan,Versa,2018,1N4AL3AP0JC...,TRJ-0001,2026-09-01

5) Requisitos para los conductores (documentos que deben presentar)
- Identificación oficial vigente.
- Licencia de conducir en regla (tipo que determine movilidad, p. ej. tipo E si aplica).
- Constancia ICET de capacitación (curso para plataformas digitales), si la normativa lo exige.
- Constancia de antecedentes y prueba toxicológica (según normativa local).

6) Formato de entrega y periodicidad
- Entrega inicial: padrón completo al momento de validación.
- Entrega periódica: mensual (u otra periodicidad que indique IMA).
- Nombre de archivo sugerido: `padron_vtaxi_YYYYMM.csv.aes` y `padron_vtaxi_YYYYMM.csv.hmac`.

7) Requisitos de seguridad para la entrega
- Clave simétrica gestionada por el equipo de seguridad de la empresa; intercambio de claves mediante canal seguro con la autoridad.
- Registro de envíos, confirmación de recepción y logs de verificación de integridad.

8) Pruebas solicitadas por la autoridad
- Alta de conductor y vehículo en entorno de pruebas.
- Envío de padrón encriptado y verificación de integridad.
- Simulación de evento de pánico y rastreo de la traza de auditoría.

9) Observaciones operativas
- Mantener proceso documentado para correcciones y subsanaciones.
- Preparar plantilla de respuesta para subsanaciones comunes (archivos mal formados, datos incompletos).
