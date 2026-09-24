# Fuentes de Datos para Base de Números de Extorsión en México

Este documento describe las **fuentes confiables** utilizadas para compilar la base de datos de números de extorsión telefónica en México, así como los **criterios de confiabilidad** y los **métodos de extracción** empleados. El objetivo es facilitar la reproducción y actualización de la base de datos por parte de otros agentes o colaboradores.

---

## 📌 **Fuentes Utilizadas**

### 1. **MiraQuienHabla**
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

---

### 2. **CONDUSEF (Comisión Nacional para la Protección y Defensa de los Usuarios de Servicios Financieros)**
   - **URL**: [https://www.condusef.gob.mx](https://www.condusef.gob.mx)
   - **Descripción**: Organismo público que recopila reportes de fraudes financieros, incluyendo números telefónicos asociados a estafas.
   - **Confiabilidad**:
     - **Fuente oficial**: Dependencia del gobierno mexicano.
     - **Datos verificados**: Los reportes son validados por la institución.
     - **Herramienta digital**: Ofrece un [portal para consultar números sospechosos](https://www.condusef.gob.mx/?p=contenido&idc=2828&idcat=1).
   - **Método de extracción**:
     - **Consulta manual**: Descargar los reportes públicos desde su portal.
     - **API**: No tiene API pública, pero se pueden extraer datos de sus comunicados oficiales (ej. [Comunicado 084](https://www.condusef.gob.mx/documentos/prensa/Comunicado%20084.pdf)).

---

### 3. **Profeco (Procuraduría Federal del Consumidor)**
   - **URL**: [https://www.profeco.gob.mx](https://www.profeco.gob.mx)
   - **Descripción**: Institución que protege a los consumidores y recopila denuncias sobre llamadas no deseadas, fraudes y extorsiones.
   - **Confiabilidad**:
     - **Base de datos oficial**: Incluye números reportados por ciudadanos.
     - **REPEP**: Registro Público para Evitar Publicidad (aunque no todos los números son de extorsión, algunos pueden ser de spam).
   - **Método de extracción**:
     - **Denuncias públicas**: Revisar las [denuncias en línea](https://repep.profeco.gob.mx/Denunciar.jsp).
     - **Limitación**: Algunos datos requieren acceso manual o solicitud de información.

---

### 4. **Gobierno de Baja California (Seguridad BC)**
   - **URL**: [https://seguridadbc.gob.mx/ExtorsionTelefonica](https://seguridadbc.gob.mx/ExtorsionTelefonica)
   - **Descripción**: Publica estadísticas y números de extorsión reportados en el estado de Baja California.
   - **Confiabilidad**:
     - **Datos oficiales**: Información proporcionada por autoridades estatales.
     - **Actualización periódica**: Reportes mensuales de números denunciados.
   - **Método de extracción**:
     - **Web Scraping**: Extraer tablas de números desde la página de "Teléfonos más denunciados".
     - **Ejemplo**:
       ```python
       # Usar requests y BeautifulSoup para extraer tablas HTML
       ```

---

### 5. **Gobierno de Guanajuato (C5i)**
   - **URL**: [https://seguridad.guanajuato.gob.mx/c5i/consulta-de-reportes-de-extorsion](https://seguridad.guanajuato.gob.mx/c5i/consulta-de-reportes-de-extorsion)
   - **Descripción**: Sistema de consulta de reportes de extorsión vinculado a la línea de denuncia anónima **089**.
   - **Confiabilidad**:
     - **Base de datos oficial**: Reportes validados por la Secretaría de Seguridad de Guanajuato.
   - **Método de extracción**:
     - **Consulta manual**: Ingresar números individualmente para verificar si están reportados.
     - **Limitación**: No permite descarga masiva de datos.

---

### 6. **Gobierno de Aguascalientes (C5i)**
   - **URL**: [https://c5i.aguascalientes.gob.mx/sistemas/extorsiones](https://c5i.aguascalientes.gob.mx/sistemas/extorsiones)
   - **Descripción**: Sistema de búsqueda de números de extorsión en Aguascalientes.
   - **Confiabilidad**:
     - **Fuente oficial**: Dependencia de seguridad pública.
   - **Método de extracción**:
     - **Consulta manual**: Similar a Guanajuato, requiere ingresar números uno por uno.

---

### 7. **Reddit (r/Mexico, r/Scams)**
   - **URL**: [https://www.reddit.com/r/mexico](https://www.reddit.com/r/mexico)
   - **Descripción**: Comunidades donde usuarios comparten experiencias y números asociados a extorsión o fraudes.
   - **Confiabilidad**:
     - **Comunidad activa**: Reportes recientes y discusiones sobre estafas.
     - **Validación social**: Los posts con más upvotes suelen ser confiables.
   - **Método de extracción**:
     - **API de Reddit**: Usar la API oficial o herramientas como `PRAW` (Python Reddit API Wrapper).
     - **Ejemplo**:
       ```python
       import praw
       reddit = praw.Reddit(client_id='...', client_secret='...', user_agent='...')
       submissions = reddit.subreddit('mexico').search('extorsión telefónica', limit=100)
       ```

---

### 8. **Twitter/X**
   - **URL**: [https://twitter.com](https://twitter.com)
   - **Descripción**: Búsquedas de hashtags como `#ExtorsiónTelefónica` o `#FraudeEnMéxico`.
   - **Confiabilidad**:
     - **Tiempo real**: Reportes recientes de usuarios.
     - **Validación manual**: Requiere filtrar información relevante.
   - **Método de extracción**:
     - **API de Twitter**: Usar `tweepy` para buscar tweets con palabras clave.
     - **Ejemplo**:
       ```python
       import tweepy
       client = tweepy.Client(bearer_token='...')
       tweets = client.search_recent_tweets(query='#ExtorsiónTelefónica', max_results=100)
       ```

---

### 9. **Policía Cibernética (SSPC)**
   - **URL**: [https://www.gob.mx/sspc](https://www.gob.mx/sspc)
   - **Descripción**: Reportes oficiales sobre delitos cibernéticos, incluyendo extorsión telefónica.
   - **Confiabilidad**:
     - **Fuente gubernamental**: Datos validados por la Secretaría de Seguridad y Protección Ciudadana.
   - **Método de extracción**:
     - **Comunicados oficiales**: Revisar boletines de prensa o reportes anuales.

---

## 🔍 **Criterios de Confiabilidad**

Para que una fuente sea considerada **confiable**, debe cumplir con al menos **3 de los siguientes criterios**:

1. **Fuente oficial**: Pertenecer a una institución de gobierno o organismo regulador (ej. CONDUSEF, Profeco, SSPC).
2. **Transparencia**: Proporcionar acceso público a los datos sin restricciones.
3. **Validación social**: Contar con una comunidad activa que revise y valide los reportes (ej. MiraQuienHabla, Reddit).
4. **Actualización periódica**: Los datos deben estar actualizados (menos de 6 meses de antigüedad).
5. **Consistencia**: Los números reportados deben aparecer en **múltiples fuentes** para reducir falsos positivos.

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

### 2. **APIs Públicas**
   - **Ejemplo**: Reddit, Twitter, o APIs de gobierno (si están disponibles).
   - **Ventaja**: Datos estructurados y fáciles de procesar.

### 3. **Consulta Manual**
   - **Para fuentes sin acceso automatizado**: Descargar datos manualmente y convertirlos a JSON.
   - **Ejemplo**: CONDUSEF o Profeco (algunos reportes requieren descarga de PDFs).

### 4. **Integración con Bases de Datos Abiertas**
   - **Ejemplo**: OpenSanctions (para números asociados a actividades ilícitas globales).

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
      "reports": N,
      "tag": "extorsion|fraude|spam",
      "source": "Fuente (ej. MiraQuienHabla)"
    }
  ]
}
```

---

## 🔄 **Proceso de Actualización**

1. **Identificar fuentes**: Revisar las fuentes listadas en este documento.
2. **Extraer datos**: Usar los métodos descritos (scraping, APIs, consulta manual).
3. **Validar formato**: Asegurar que los números cumplan con el esquema JSON.
4. **Eliminar duplicados**: Usar el número telefónico como clave única.
5. **Actualizar repositorio**: Hacer un *Pull Request* en [xolotlsoft/spam_mexico](https://github.com/xolotlsoft/spam_mexico).

---

## 📌 **Recomendaciones para Agentes**

- **Automatizar**: Usar scripts en Python para extraer datos periódicamente.
- **Validar**: Cruzar números con múltiples fuentes para aumentar la confiabilidad.
- **Documentar**: Registrar la fuente y fecha de extracción para cada número.
- **Respetar términos de uso**: Algunas fuentes prohíben el scraping masivo (ej. Twitter).

---

## 📅 **Frecuencia de Actualización**

- **MiraQuienHabla**: Semanal (datos colaborativos en tiempo real).
- **CONDUSEF/Profeco**: Mensual (reportes oficiales).
- **Reddit/Twitter**: Diario (para reportes recientes).
- **Gobiernos estatales**: Mensual (depende de la entidad).

---

## 🚀 **Contribuciones**

Si encuentras una **nueva fuente confiable** o un **método de extracción mejorado**, puedes:
1. Abrir un *Pull Request* en el repositorio con los cambios.
2. Sugerir la fuente en este documento.

---

**Nota**: Este documento se actualizará periódicamente para incluir nuevas fuentes o métodos de extracción.