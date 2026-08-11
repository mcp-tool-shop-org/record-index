<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.md">English</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/record-index/main/docs/assets/logo-wide.png" alt="record-index — query the record instead of reading it" width="820">
</p>

# índice de registros

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/record-index/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/record-index/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/record-index/"><img src="https://img.shields.io/badge/landing%20page-live-2ea043" alt="Landing page"></a>
</p>

Un mapa gobernado de SQLite+FTS5 sobre un registro de decisiones en formato Markdown, para que una sesión pueda **consultar** el registro en lugar de leerlo, y luego leer las cuarenta líneas a las que apunta la consulta, en lugar de las seiscientas que habría leído rápidamente.

**[Página de inicio y manual →](https://mcp-tool-shop-org.github.io/record-index/)**

El formato Markdown permanece como el original. El índice se deriva y se regenera en cada iteración, y está controlado por una condición de cuatro elementos `verify`, y es **incorrecto por definición desde el día en que se edita manualmente**.

## Estado: extraído, probado, aún no disponible en PyPI

*(Esta sección decía "SOLO PLANTILLA — todavía no hay código de herramienta en este repositorio" hasta el 11 de agosto de 2026, lo que la extracción inicial falsificó. Corregido in situ).*

**La extracción se realizó correctamente.** El paquete está en `main` y su inclusión está controlada por la identidad de bytes con la versión del árbol de "facet" (19/19) y **cero diferencias a nivel de fila** en el mismo corpus. Dos consumidores lo utilizan: [facet](https://github.com/mcp-tool-shop-org/facet), cuyas ~2462 líneas del árbol se convirtieron en una declaración más un adaptador con ~140 de sus pruebas, que ejercitan el paquete a través de él; y [armature](https://github.com/mcp-tool-shop-org/armature), cuyo propio índice inició 15/15 con 47 reglas.

**El paquete incluye su propia suite: 455 pruebas** en los diez módulos, que se ejecutan en CI en Python 3.11 y 3.13, y se basan en dos repositorios de registros de referencia que difieren en todos los ejes declarables: marcadores, raíces del corpus, reglas de arco, vocabulario de veredicto, formatos de encabezado; por lo que una implementación incorrecta tiene un lugar donde puede hacerse visible. **Dependencias: ninguna.** Solo la biblioteca estándar (`sqlite3` + `re` + `json`), y eso es una propiedad declarada, no un accidente.

**Se conocen cuatro defectos, se han reproducido y se han fijado en el árbol como pruebas `xfail(strict=True)`**, en lugar de ocultarlos: `verify()` duplica sus recuentos de diagnóstico (los elementos de control no se ven afectados); el patrón de arco de afirmación asume arcos numerados con `E`; el localizador de subreglas no se deriva del formato de encabezado declarado; y cuatro campos de declaración no pueden declararse honestamente como vacíos. Ninguno afecta a los dos consumidores actuales; los cuatro están en cola para la próxima versión.

**Aún no está disponible en PyPI.** `release.yml` se publica mediante Publicación confiable OIDC cuando se crea una versión de GitHub; nada se publica al realizar un "push".

## De dónde proviene esto

Esta es una extracción del índice de registros, que se ha creado y reforzado en [`mcp-tool-shop-org/facet`](https://github.com/mcp-tool-shop-org/facet), donde se pagó por cada convención a continuación. Extrae en lugar de bifurcar porque el propio libro de leyes de "facet" registra cinco copias manuales de una función que existen bajo cuatro nombres, invisibles para una búsqueda basada en nombres durante meses; bifurcar miles de líneas en un segundo repositorio es ese error con tres ceros más.

La condición de extracción se declaró por adelantado y se controló mediante la medición: *el índice se extrae cuando un segundo repositorio adopta las convenciones*. [`mcp-tool-shop-org/armature`](https://github.com/mcp-tool-shop-org/armature) es ese repositorio.

## El diseño, en un párrafo

Un repositorio de registros declara **qué significan sus documentos**: qué archivos contienen reglas, qué formatos de encabezado los abren, cuál es su vocabulario de veredicto y qué corpus tiene. La herramienta proporciona **cómo funciona la búsqueda**: análisis sintáctico, clasificación, determinismo, las etapas de verificación, con valores de ajuste que incluyen el corpus y la fecha en que se calibraron. Las convenciones son una **declaración completa** (un repositorio declara su propio significado; nunca hereda la historia de otro repositorio por omisión). El mecanismo es **valores predeterminados con anulación**.

Cada vocabulario informa qué **no reconoció**. Una tabla vacía y una tabla que descartó silenciosamente seis artefactos son indistinguibles en el sitio de llamada, y solo una de ellas es correcta.

## La parada que solía estar aquí y cómo terminó

*(Hasta el 11 de agosto de 2026, esta sección detenía la compilación debido a una colisión medida. La parada era real, se emitió la regla y la compilación continuó; se mantiene aquí como registro en lugar de eliminarse).*

El paso de clasificación había medido que derivar el arco de un documento a partir de su prefijo principal `E\d\d` **genera una colisión en 7 claves primarias** con "facet" (tanto `E10-ruling.md` como `E10-offsurface-ruling.md` se convierten en el arco `E10`). El ejecutor lo detectó frente a una prueba cuyo nombre registra el mismo fallo, la regla conjunta se retiró y se volvió a derivar, y la extracción continuó a través de sus puertas. El registro —evidencia, las respuestas revocadas y la regla que las reemplazó— está en `armature/docs/dispatches/` (el arco S02).

## Licencia

MIT: consulte [LICENSE](LICENSE).
