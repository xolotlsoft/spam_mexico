# Fuentes de Datos para Base de Números de Extorsión en México

Este documento describe las **fuentes confiables** utilizadas para compilar la base de datos de números de extorsión telefónica en México, así como los **criterios de confiabilidad** y los **métodos de extracción** empleados. El objetivo es facilitar la reproducción y actualización de la base de datos por parte de otros agentes o colaboradores.

---

## 📌 **Fuentes Utilizadas**

### 1. **MiraQuienHabla** ✅ SOPORTADA (automatizada)
   - **URL**: [https://miraquienhabla.com.mx/reportes](https://miraquienhabla.com.mx/reportes)
   - **Descripción**: Plataforma colaborativa donde los usuarios reportan números telefónicos asociados a extorsión, fraudes o llamadas sospechosas.
   - **Confiabilidad**:
     - **Comunidad activa**: Miles de reportes verificados por usuarios.
     - **Transparencia**: Los reportes incluyen fechas, descripciones y número de denuncia.
     - **Acceso público**: Los datos son accesibles sin restricciones.
   - **Método de extracción**:
     - **Web Scraping**: Se extraen los números, reportes, etiquetas y fuentes de la página de "Últimos Reportes".
     - **Automatización**: Se puede usar un script en Python con `requests` y `BeautifulSoup` para parsear los datos.
     - **Ejemplo de script**:
       ```python
       import requests
       from bs4 import BeautifulSoup

       url = "https://miraquienhabla.com.mx/reportes"
       response = requests.get(url)
       soup = BeautifulSoup(response.text, 'html.parser')
       # Extraer números y detalles de los reportes
       ```
   - **Workflow**: `extraer_miraquienhabla.yml` (semanal, martes 12:00 UTC).

---

### 2. **CONDUSEF (Comisión Nacional para la Protección y Defensa de los Usuarios de Servicios Financieros)** ✅ SOPORTADA (automatizada, alertas oficiales)
   - **URL**: [https://www.condusef.gob.mx](https://www.condusef.gob.mx)
   - **Descripción**: Organismo público que recopila reportes de fraudes financieros, incluyendo números telefónicos asociados a estafas.
   - **Confiabilidad**:
     - **Fuente oficial**: Dependencia del gobierno mexicano.
     - **Datos verificados**: Los reportes son validados por la institución.
     - **Herramienta digital**: Ofrece un [portal para consultar números sospechosos](https://www.condusef.gob.mx/?p=contenido&idc=2828&idcat=1).
   - **Método de extracción**:
     - **Automatizado (desde 2026-09-24)**: `scripts/extraer_alertas_oficiales.py` consulta el portal de números sospechosos y parsea los comunicados de prensa en PDF (con `PyPDF2`), extrayendo números con filtros anti-falsos-positivos (ver sección *Alertas Oficiales*).
     - **API**: No tiene API pública, por lo que la extracción se realiza por scraping/PDF parsing.

---

### 3. **Profeco (Procuraduría Federal del Consumidor)** ✅ SOPORTADA (automatizada, alertas oficiales)
   - **URL**: [https://www.profeco.gob.mx](https://www.profeco.gob.mx)
   - **Descripción**: Institución que protege a los consumidores y recopila denuncias sobre llamadas no deseadas, fraudes y extorsiones.
   - **Confiabilidad**:
     - **Base de datos oficial**: Incluye números reportados por ciudadanos.
     - **REPEP**: Registro Público para Evitar Publicidad (aunque no todos los números son de extorsión, algunos pueden ser de spam).
   - **Método de extracción**:
     - **Automatizado (desde 2026-09-24)**: `scripts/extraer_alertas_oficiales.py` busca artículos de gob.mx relacionados con Profeco que mencionen números de extorsión.
     - **Limitación**: Algunas denuncias requieren acceso manual o solicitud de información.

---

### 4. **Gobierno de Baja California (Seguridad BC)** ✅ SOPORTADA (automatizada, alertas oficiales)
   - **URL**: [https://seguridadbc.gob.mx/ExtorsionTelefonica](https://seguridadbc.gob.mx/ExtorsionTelefonica)
   - **Descripción**: Publica estadísticas y números de extorsión reportados en el estado de Baja California.
   - **Confiabilidad**:
     - **Datos oficiales**: Información proporcionada por autoridades estatales.
     - **Actualización periódica**: Reportes mensuales de números denunciados.
   - **Método de extracción**:
     - **Automatizado (desde 2026-09-24)**: `scripts/extraer_alertas_oficiales.py` (fuente `fuente_bc`) hace scraping de la página de "Teléfonos más denunciados".
     - La extracción es *best-effort*: si el sitio cambia de estructura, la fuente falla sin detener las demás.

---

### 5. **Gobierno de Guanajuato (C5i)** ⚠️ CONSULTA MANUAL
   - **URL**: [https://seguridad.guanajuato.gob.mx/c5i/consulta-de-reportes-de-extorsion](https://seguridad.guanajuato.gob.mx/c5i/consulta-de-reportes-de-extorsion)
   - **Descripción**: Sistema de consulta de reportes de extorsión vinculado a la línea de denuncia anónima **089**.
   - **Confiabilidad**:
     - **Base de datos oficial**: Reportes validados por la Secretaría de Seguridad de Guanajuato.
   - **Método de extracción**:
     - **Consulta manual**: Ingresar números individualmente para verificar si están reportados.
     - **Limitación**: No permite descarga masiva de datos ni acceso automatizado.

---

### 6. **Gobierno de Aguascalientes (C5i)** ⚠️ CONSULTA MANUAL
   - **URL**: [https://c5i.aguascalientes.gob.mx/sistemas/extorsiones](https://c5i.aguascalientes.gob.mx/sistemas/extorsiones)
   - **Descripción**: Sistema de búsqueda de números de extorsión en Aguascalientes.
   - **Confiabilidad**:
     - **Fuente oficial**: Dependencia de seguridad pública.
   - **Método de extracción**:
     - **Consulta manual**: Similar a Guanajuato, requiere ingresar números uno por uno.

---

### 7. **Reddit (r/Mexico, r/Scams)** ❌ NO SOPORTADA
   - **URL**: [https://www.reddit.com/r/mexico](https://www.reddit.com/r/mexico)
   - **Descripción**: Comunidades donde usuarios comparten experiencias y números asociados a extorsión o fraudes.
   - **Motivo del no soporte**:
     - La [Responsible Builder Policy de Reddit](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy) (vigente desde noviembre de 2025) exige revisión y aprobación previa de Reddit para crear apps que usen su API, además de restricciones sobre datos de terceros y uso comercial. No se obtuvo dicha aprobación, por lo que **este proyecto no consume la API de Reddit ni hace scraping del sitio**.
     - El workflow `extraer_reddit_twitter.yml` fue **deshabilitado** y el issue #3 se cerró como *not planned*.

---

### 8. **Twitter/X** ❌ NO SOPORTADA
   - **URL**: [https://twitter.com](https://twitter.com)
   - **Descripción**: Búsquedas de hashtags como `#ExtorsiónTelefónica` o `#FraudeEnMéxico`.
   - **Motivo del no soporte**:
     - El acceso a la API de X requiere un **plan de pago** (Basic o superior) desde 2023, y sus términos restringen el uso de datos para productos derivados. No se dispone de presupuesto ni autorización, por lo que **este proyecto no consume la API de X**.
     - El workflow `extraer_reddit_twitter.yml` fue **deshabilitado** por la misma razón.

---

### 9. **Policía Cibernética (SSPC)** ✅ SOPORTADA (automatizada, alertas oficiales)
   - **URL**: [https://www.gob.mx/sspc](https://www.gob.mx/sspc)
   - **Descripción**: Reportes oficiales sobre delitos cibernéticos, incluyendo extorsión telefónica.
   - **Confiabilidad**:
     - **Fuente gubernamental**: Datos validados por la Secretaría de Seguridad y Protección Ciudadana.
   - **Método de extracción**:
     - **Automatizado (desde 2026-09-24)**: `scripts/extraer_alertas_oficiales.py` (fuente `fuente_gobmx`) busca artículos de gob.mx de SSPC/Profeco/CONDUSEF que mencionen números de extorsión.

---

## 🤖 **Alertas Oficiales (extracción diaria automatizada)**

El script `scripts/extraer_alertas_oficiales.py` consolida las fuentes oficiales (CONDUSEF, Profeco, SSPC y Seguridad BC) en un pipeline diario:

- **Fuentes implementadas**:
  - `fuente_bc`: scraping de `seguridadbc.gob.mx` (teléfonos más denunciados).
  - `fuente_condusef`: portal de números sospechosos + parseo de PDFs de comunicados de prensa (PyPDF2).
  - `fuente_gobmx`: búsqueda de artículos de gob.mx (Profeco/SSPC/CONDUSEF) que mencionen números de extorsión.
- **Filtros anti-falsos-positivos**:
  - Solo números nacionales de 10 dígitos (formato `+52` + 10 dígitos).
  - Excluye números de tarifa especial (prefijos 800/900) y números con dígitos repetidos.
  - Exige proximidad de palabras clave de extorsión (±150 caracteres) para aceptar un número.
- **Comportamiento**:
  - Ejecución *best-effort*: si una fuente falla, las demás continúan (`try/except` por fuente).
  - Merge deduplicado contra `mexico_spam_db.json`; si hay números nuevos, hace bump de versión (+0.1), actualiza `updated_at` y valida contra el schema de OpenCallShield antes de guardar.
  - CLI: `python3 scripts/extraer_alertas_oficiales.py --fuentes bc condusef gobmx`.
- **Workflow**: `.github/workflows/extraer_alertas_oficiales.yml` (diario, 08:00 UTC + `workflow_dispatch`), instala dependencias (`requests`, `beautifulsoup4`, `PyPDF2`, `jsonschema`), ejecuta el script y hace commit solo si hubo cambios.

**Instrucciones para otros agentes**: para agregar una fuente oficial nueva, añade una función `fuente_<nombre>()` al script que devuelva una lista de dicts `{number, reports, tag, source}` (ya normalizados a formato `+52XXXXXXXXXX`), regístrala en `FUENTES_DISPONIBLES` y documenta aquí su URL, confiabilidad y método.

---

## 🔍 **Criterios de Confiabilidad**

Para que una fuente sea considerada **confiable**, debe cumplir con al menos **3 de los siguientes criterios**:

1. **Fuente oficial**: Pertenecer a una institución de gobierno o organismo regulador (ej. CONDUSEF, Profeco, SSPC).
2. **Transparencia**: Proporcionar acceso público a los datos sin restricciones.
3. **Validación social**: Contar con una comunidad activa que revise y valide los reportes (ej. MiraQuienHabla).
4. **Actualización periódica**: Los datos deben estar actualizados (menos de 6 meses de antigüedad).
5. **Consistencia**: Los números reportados deben aparecer en **múltiples fuentes** para reducir falsos positivos.

**Nota sobre Reddit/Twitter**: aunque cumplen el criterio de validación social, sus **políticas de API** impiden su uso automatizado en este proyecto, por lo que quedan excluidos.

---

## 🛠 **Métodos de Extracción**

### 1. **Web Scraping**
   - **Herramientas**: `requests`, `BeautifulSoup` (Python), `Scrapy`.
   - **Ejemplo genérico**:
     ```python
     import requests
     from bs4 import BeautifulSoup

     url = "URL_DE_LA_FUENTE"
     response = requests.get(url)
     soup = BeautifulSoup(response.text, 'html.parser')
     # Extraer datos relevantes (números, reportes, fechas)
     ```
   - **Limitaciones**: Algunas páginas bloquean el acceso automatizado (ej. CAPTCHA).

### 2. **Parseo de PDFs**
   - **Herramientas**: `PyPDF2` (usado en los comunicados de CONDUSEF).
   - **Ventaja**: Muchas fuentes oficiales publican sus alertas como PDF.

### 3. **APIs Públicas**
   - **Ejemplo**: APIs de gobierno (si están disponibles).
   - **Ventaja**: Datos estructurados y fáciles de procesar.
   - **Excepciones**: Reddit y Twitter/X requieren aprobación/pago (ver secciones 7 y 8).

### 4. **Consulta Manual**
   - **Para fuentes sin acceso automatizado**: Descargar datos manualmente y convertirlos a JSON.
   - **Ejemplo**: C5i de Guanajuato y Aguascalientes (ingreso número por número).

---

## 📝 **Formato de Datos**

El archivo `mexico_spam_db.json` sigue el siguiente esquema:

```json
{
  "version": "X.X",
  "updated_at": "YYYY-MM-DD",
  "description": "Descripción de la base de datos y fuentes.",
  "numbers": [
    {
      "number": "+52XXXXXXXXXX",
      "reports": 1,
      "tag": "extorsion|fraude|spam",
      "source": "Fuente (ej. MiraQuienHabla)"
    }
  ]
}
```

El patrón del número es `^\+52\d{10}$` (13 caracteres, código de país + 10 dígitos nacionales).

---

## 🔄 **Proceso de Actualización**

1. **Identificar fuentes**: Revisar las fuentes listadas en este documento.
2. **Extraer datos**: Usar los métodos descritos (scraping, PDFs, consulta manual).
3. **Validar formato**: Asegurar que los números cumplan con el esquema JSON.
4. **Eliminar duplicados**: Usar el número telefónico como clave única.
5. **Actualizar repositorio**: Hacer un *Pull Request* en [xolotlsoft/spam_mexico](https://github.com/xolotlsoft/spam_mexico).

---

## 📌 **Recomendaciones para Agentes**

- **Automatizar**: Usar `scripts/extraer_alertas_oficiales.py` como plantilla para nuevas fuentes.
- **Validar**: Cruzar números con múltiples fuentes para aumentar la confiabilidad.
- **Documentar**: Registrar la fuente y fecha de extracción para cada número.
- **Respetar términos de uso**: No usar fuentes cuyas políticas lo prohíban (ej. Reddit, Twitter/X).

---

## 📅 **Frecuencia de Actualización**

| Fuente | Frecuencia | Método | Estado |
|---|---|---|---|
| MiraQuienHabla | Semanal (mar 12:00 UTC) | Workflow `extraer_miraquienhabla` | ✅ Activo |
| Alertas oficiales (CONDUSEF, Profeco, SSPC, BC) | Diario (08:00 UTC) | Workflow `extraer_alertas_oficiales` | ✅ Activo |
| Guanajuato C5i | Bajo demanda | Consulta manual | ⚠️ Manual |
| Aguascalientes C5i | Bajo demanda | Consulta manual | ⚠️ Manual |
| Reddit | — | — | ❌ No soportado (política de API) |
| Twitter/X | — | — | ❌ No soportado (API de pago) |

---

## ⚙️ **Workflows de GitHub Actions**

- **Activos**:
  - `validate_json.yml`: valida `mexico_spam_db.json` contra el schema de OpenCallShield en cada push/PR.
  - `extraer_miraquienhabla.yml`: scraping semanal de MiraQuienHabla.
  - `extraer_alertas_oficiales.yml`: extracción diaria de alertas oficiales (script real, filtros anti-FP).
- **Deshabilitados** (no-op, sin cron; los reemplazan los workflows activos):
  - `extraer_reddit_twitter.yml`: Reddit y X no son soportados por sus políticas de API.
  - `extraer_condusef_profeco.yml`: datos simulados; sustituido por `extraer_alertas_oficiales`.
  - `extraer_gobiernos_estatales.yml`: datos simulados; BC cubierto por alertas oficiales, GTO/AGS manual.

---

## 🚀 **Contribuciones**

Si encuentras una **nueva fuente confiable** o un **método de extracción mejorado**, puedes:
1. Abrir un *Pull Request* en el repositorio con los cambios.
2. Sugerir la fuente en este documento.

---

**Nota**: Este documento se actualizará periódicamente para incluir nuevas fuentes o métodos de extracción.
