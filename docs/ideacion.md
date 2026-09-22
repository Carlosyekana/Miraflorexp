# Sesión de ideación — Cruzar datos abiertos de Miraflores con datos de Google

**Fecha:** 2026-09-21 · **Supuesto base:** "Miraflores" = Miraflores, Lima (Perú), porque los datasets abiertos de licencias coinciden exactamente con ese distrito. Si te referías a otro Miraflores, esto se reajusta en 5 minutos.

---

## 0. La tesis en una frase

> Cruzar el **registro formal** (licencias de funcionamiento) con la **presencia real percibida** (Google Maps / Places) y anclarlo sobre el **territorio** (catastro / zonificación) para leer la brecha entre lo que Miraflores *dice autorizar* y lo que *realmente ocurre* en sus calles.

Esa "brecha" es el activo: sirve para fiscalización, desarrollo económico, urbanismo, turismo o periodismo de datos según quién la mire.

---

## 1. ¿Qué hay realmente en cada fuente?

### A. Licencias de funcionamiento — Municipalidad de Miraflores
Portal Nacional de Datos Abiertos (`datosabiertos.gob.pe`), publicador: Municipalidad Distrital de Miraflores, Subgerencia de Comercialización. Archivos mensuales 2020–2022 (XLSX), última actualización del dataset 2024.

**Sondeo real sobre el XLSX 2020 (10,249 registros):**

| Columna | Contenido | Nota |
|---|---|---|
| ID | correlativo | |
| CODIGO DE LA ENTIDAD / UBIGEO / PAÍS | 10069 / 150122 / PE | Unidad orgánica y geocódigo |
| NOMBRE DE LA UO | "Subgerencia de Comercialización" | |
| **NOMBRE_VIA** | ej. "AV. SANTA CRUZ", "CALL TRIANA" | ⚠️ Solo la vía, sin número, sin nombre comercial |
| **GIRO** | ej. "RESTAURANT CON VENTA DE LICOR" | ⚠️ 374 giros únicos |
| FECHA_INICIO | 19860131 → formato YYYYMMDD | rango 1986 → 2020 |

**Implicaciones duras para el cruce:**
1. **No trae coordenadas** → hay que geocodificar (obtener lat/lng desde la vía).
2. **No trae nombre del local** → el enlace con Google no es directo; es por *vía + giro* (record linkage difuso).
3. Los giros dominantes son **oficinas y servicios profesionales** (≈2,000 "prestación de servicios profesionales / oficinas administrativas") — un perfil que Google *subrepresenta*.

### B. Google (My Business / Places)
- **Google Business Profile (My Business API):** es la API de *gestión del local propio* (requiere ser dueño). ❌ No sirve para volcar un distrito de terceros.
- **Places API oficial:** pensada para consultas puntuales (límite ~60 resultados por búsqueda). Sirve para un muestreo, no para "todo Miraflores".
- **Para extracción masiva** de negocios de un distrito: servicios de scraping de terceros (Outscraper, Apify, SerpAPI…) — **con costo** y con restricciones de uso de Google (cuidado al *redistribuir* datos).
- **Lo valioso que sí da:** nombre, categoría, lat/lng, rating, nº de reseñas, horarios, estado (operativo / cerrado definitivamente), a veces afluencia ("popular times").

> Reflejo mental: Google captura el **negocio vivo que el público percibe**; la municipalidad captura el **negocio que por derecho debería existir**. El valor está en la diferencia.

### C. Tercer set de datos (el que convierte esto en cartografía real)
| Fuente | Qué aporta | ¿Dónde? |
|---|---|---|
| **Lotes catastrales de Miraflores** (WMS) | Polígono de lote, código catastral — el "piso" del mapa | GeoServer municipal vía GeoIDEP |
| **Zonificación 2024 + alturas** | Uso permitido del suelo por predio | GIS municipal (`miraflores.gob.pe`), PDF/JPG |
| **Licencias de edificación** | Actividad constructiva, renovación urbana | Datos abiertos (resoluciones mensuales) |
| **Paraderos autorizados / operativos** | Movilidad, control | Datos abiertos + ArcGIS Hub |
| **INEI — CPV 2017 (manzana)** | Población, viviendas, estratos (demanda) | INEI / GeoIDEP |
| **Límite distrital** | El recorte de todo el análisis | GeoIDEP |

---

## 2. La fricción central (honestidad técnica)

Esto **no es un JOIN por nombre**. Es un problema en tres actos:

1. **Geocodificación** — pasar "AV. SANTA CRUZ" a coordenadas. Se puede con Osm/Nominatim, o mejor: unir con la capa de ejes viales del catastro para ubicar por cuadra/tonelada.
2. **Equivalencia de categorías** — el GIRO municipal ("SALON DE BELLEZA Y/O PELUQUERIA") ≠ la categoría Google ("Hair salon") → hace falta una tabla de correspondencias y métricas de similitud de texto.
3. **Emparejamiento difuso** — buffer de proximidad + similitud giro↔categoría; un punto de Google puede corresponder a N licencias o a **ninguna** (informalidad, licencias canceladas, o el local cerró).
4. **Sesgo de cobertura** — Google sobrerepresenta B2C (restaurantes, tiendas) y subrepresenta oficinas profesionales; la brecha así calculada tendrá ruido por giro. Hay que contarlo, no ocultarlo.

**Regla de oro del cruce:** medir y reportar el *match rate* y la *matriz de confusión* giro↔categoría. Eso separa datos de relato.

---

## 3. Banco de ideas (agrupadas por propósito)

### Línea A — Informalidad y fiscalización 🎯
1. **Radar de informalidad:** negocios presentes en Google (visibles, con reseñas activas) sin ninguna licencia municipal en un radio de, digamos, 30–50 m → mapa de candidatos a fiscalización. *(Licencias + Places + lotes)*
2. **Tasa de formalidad por giro y por manzana:** ratio `licencias / presencia Google` por unidad catastral → qué barrios y qué rubros están "en negro".

### Línea B — Desarrollo económico y planeamiento 🏙️
3. **Actividad real vs. zonificación:** dónde opera cada giro y dónde lo *permite* la zonificación → conflictos de uso, y también oportunidades (zonas comerciales subutilizadas). *(Licencias + Places + zonificación)*
4. **Oferta vs. demanda por barrio:** licencias + Google (oferta) contra INEI-población/NSE (demanda) → saturación o vacíos comerciales por manzana.
5. **Mortandad comercial:** locales de Google marcados "cerrado definitivamente" que en el registro siguen con licencia vigente → churn y riesgo de obsolescencia del registro.

### Línea C — Experiencia ciudadana y turismo ✨
6. **"Miraflores real":** directorio-mapa que cruza la data oficial con rating/reseñas → qué hay, qué está bien evaluado, qué zona anima cada giro.
7. **Calidad percibida vs. giro autorizado:** ratings/reseñas agrupados por categoría de licencia → qué rubros enamoran y cuáles fallan.

### Línea D — Analítica urbana 📊
8. **Pie de calle:** densidad de locales (licencias + Google) por fachada/manzana con los lotes de fondo → "quién anima cada cuadra".
9. **Detección de clusters:** hotspots de rubros específicos (clínicas odontológicas de Miraflores, salones, cafés) → polos de especialización.

### Línea E — Transparencia y periodismo de datos 🗞️
10. **"El Miraflores que se ve vs. el que está registrado":** pieza interactiva sobre la brecha formal/informal, la concentración de giros y la historia de licencias desde 1986.

---

## 4. Matriz rápida (impacto × viabilidad)

Escalas: Impacto y Novedad 1–5 (5 = mejor) · Dificultad 1–5 (5 = más difícil) · Costo de datos: Bajo/Medio/Alto

| # | Idea | Impacto | Novedad | Dificultad | Costo datos | Primer paso crítico |
|---|---|---|---|---|---|---|
| 1 | Radar de informalidad | 5 | 4 | 4 | Alto* | Geocodificar licencias |
| 2 | Tasa de formalidad por manzana | 4 | 3 | 3 | Alto* | match difuso básico |
| 3 | Actividad vs. zonificación | 4 | 4 | 3 | Bajo | bajar capa zonificación |
| 4 | Oferta vs. INEI | 4 | 3 | 3 | Medio | CPV 2017 por manzana |
| 5 | Mortandad comercial | 3 | 4 | 4 | Alto* | histórico Places |
| 6 | Directorio "Miraflores real" | 3 | 2 | 2 | Alto* | muestra Places oficial |
| 7 | Calidad vs. giro | 2 | 3 | 2 | Alto* | ratings por giro |
| 8 | Pie de calle / densidad | 3 | 3 | 2 | Bajo | licencias + lotes |
| 9 | Clusters por rubro | 3 | 3 | 2 | Bajo | hotspots |
| 10 | Pieza cívica/periodística | 4 | 4 | 3 | Medio | narrativa de la brecha |

\* "Alto" porque el dato Google a escala distrital requiere scraping de pago o un muestreo vía API oficial.

**Observación para priorizar:** las ideas 3, 8, 9 y 10 (que usan solo datos municipales + INEI, sin depender de Google) son las más baratas para prototipar; las ideas 1, 2 y 5 son las de mayor impacto pero dependen de conseguir data de Google a escala.

---

## 5. Ruta mínima para un primer prototipo (cuando digas "vamos")

1. **Geocodificar** las licencias por `NOMBRE_VIA` (Nominatim o cruce con ejes viales del catastro).
2. **Obtener una muestra** de Google Places: 30–100 locales vía Places API oficial (gratis→crédito), o 1 extracción masiva con Outscraper si hay presupuesto.
3. **Bajar** límite distrital + lotes + zonificación (WMS municipal / GeoIDEP).
4. **Match difuso:** buffer de proximidad + similitud de texto giro↔categoría, reportando match rate.
5. **Visualizar:** Folium/MapLibre → mapa HTML interactivo (que además se ve en este workspace).

---

## 6. Riesgos y permisos (para no chocar después)

- **Términos de Google:** la redistribución de datos de Places está restringida; para una pieza pública conviene agregar/anonimizar (no publicar el volcado crudo).
- **Precisión del geocódigo:** la vía sin número ubica al centro de la calle; el buffer de match debe ser generoso y declarado.
- **Cobertura y sesgo:** la brecha mide *presencia detectable en Google*, no informalidad absoluta. Acompañar con la frase honesta del alcance.
- **Datos personales (Ley 29733 / habeas data):** no exponer titulares de licencias; trabajar a nivel de giro/manzana, no de persona.

---

## 7. Preguntas que disparan más ideas (si quieres seguir explorando)

- ¿Y si en vez de "informales" buscamos **licencias que ya no operan pero siguen figurando** (registro obsoleto)? Eso es un problema municipal valioso.
- ¿Qué pasa con los **giros que Google no tiene categoría** (ej. "venta de equipos médicos")? ¿Qué dice eso del vocabulario urbano?
- ¿Sirve esto para **elegir dónde abrir un local** (inversionista) más que para fiscalizar? El mismo cruce, otro cliente.
- ¿Puede el mapa servir como **tablero ciudadano** que la propia municipalidad use para contestar "¿por qué hay tantas boticas en mi cuadra?"

---

*Preparado con un sondeo real al XLSX de licencias 2020 (10,249 registros, 8 columnas) y revisión de catálogos GeoIDEP, portal de datos abiertos del Perú y documentación de APIs de Google.*
