# Base de Datos de Números de Extorsión en México

Este repositorio contiene una base de datos colaborativa de números telefónicos asociados a reportes de extorsión en México. Los datos han sido recopilados a partir de **búsquedas en bases de datos abiertas, públicas y de gobierno**, así como de fuentes como [MiraQuienHabla](https://miraquienhabla.com.mx/reportes).

---

## Propósito
El uso principal de esta base de datos es para el proyecto **[OpenCallShield](https://github.com/xolotlsoft/opencallshield)**, una herramienta diseñada para detectar y bloquear llamadas de números asociados a fraudes o extorsión.

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

## Licencia
Este proyecto se distribuye bajo los términos de **licencia abierta** para uso en herramientas de protección contra fraudes. Se recomienda verificar la validez de los datos antes de su implementación en sistemas críticos.
