# Base de Datos de Números de Extorsión en México

Este repositorio contiene una base de datos colaborativa de números telefónicos asociados a reportes de extorsión en México. Los datos han sido recopilados a partir de **búsquedas en bases de datos abiertas, públicas y de gobierno**, así como de fuentes como [MiraQuienHabla](https://miraquienhabla.com.mx/reportes).

---

## Propósito
El uso principal de esta base de datos es para el proyecto **[OpenCallShield](https://github.com/xolotlsoft/opencallshield)**, una herramienta diseñada para detectar y bloquear llamadas de números asociados a fraudes o extorsión.

---

## Modo de Uso

### Integración con OpenCallShield
Para utilizar esta base de datos en **OpenCallShield**, sigue estos pasos:

1. **Configuración de la URL**:
   - Usa la siguiente URL para acceder al archivo JSON:
     ```
     https://raw.githubusercontent.com/xolotlsoft/spam_mexico/main/mexico_spam_db.json
     ```
   - Esta URL apunta directamente al contenido crudo del archivo, lo que permite que **OpenCallShield** pueda consumirlo sin problemas.

2. **Validación del JSON**:
   - El repositorio incluye un workflow de GitHub Actions que valida automáticamente el formato del archivo `mexico_spam_db.json` contra un schema esperado para **OpenCallShield**. Esto garantiza que los datos estén siempre en el formato correcto.

3. **Actualización de Datos**:
   - Si deseas actualizar los datos, puedes hacer un *Pull Request* con los cambios o reportar números adicionales a través de las fuentes mencionadas.

---

## Estructura del Archivo
El archivo `mexico_spam_db.json` contiene una lista de números telefónicos con los siguientes campos:
- `number`: Número telefónico en formato internacional (ej. `+52XXXXXXXXXX`).
- `reports`: Número de reportes asociados al número.
- `tag`: Etiqueta que clasifica el tipo de incidente (ej. `extorsion`).
- `source`: Fuente de la que se obtuvo el dato (ej. `MiraQuienHabla`).

---

## Contribuciones
Si deseas contribuir con más números o mejorar la base de datos, puedes:
1. Abrir un *Pull Request* con los cambios.
2. Reportar números adicionales a través de las fuentes mencionadas.

---

## Automatización y monitoreo

El repositorio cuenta con workflows en `.github/workflows/` para automatizar la actualización y validación de `mexico_spam_db.json`:

- `extraer_miraquienhabla.yml`: ejecución semanal los martes a las 12:00 UTC.
- `extraer_condusef_profeco.yml`: revisión semanal los lunes a las 10:00 UTC, con extracción solo el primer lunes de cada mes.
- `extraer_reddit_twitter.yml`: ejecución diaria a las 08:00 UTC.
- `extraer_gobiernos_estatales.yml`: revisión semanal los lunes a las 10:00 UTC, con extracción solo el segundo lunes de cada mes.
- `validate_json.yml`: validación automática en pushes, pull requests y después de actualizaciones automáticas.
- `monitor_automation.yml`: reintento automático una vez tras 1 hora en caso de fallo, creación de issues de seguimiento y notificación de conflictos en PRs.

### Secrets requeridos

Para `extraer_reddit_twitter.yml` deben configurarse estos GitHub Secrets antes de habilitar la automatización:

- `TWITTER_BEARER_TOKEN`
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`

### Flujo de validación

Cada workflow de extracción valida localmente el JSON antes de publicar cambios. Si hay cambios válidos, el workflow hace `push` y luego dispara `validate_json.yml` para verificar el estado final del repositorio. Si la validación falla en `main`, el workflow de monitoreo intenta revertir el commit fallido y abre un issue para el agente de validación/orquestación.

### Notificaciones

Las alertas operativas se registran vía GitHub Issues para fallos tras reintento y conflictos de PR. Además, el equipo puede usar las GitHub Notifications nativas del repositorio para seguir ejecuciones exitosas/fallidas de Actions.

---

## Licencia
Este proyecto se distribuye bajo los términos de **licencia abierta** para uso en herramientas de protección contra fraudes. Se recomienda verificar la validez de los datos antes de su implementación en sistemas críticos.
