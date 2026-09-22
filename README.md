# Miraflorexp — Catastro Comercial de Miraflores

**Explorar el cruce de datos abiertos de la Municipalidad de Miraflores con la
presencia digital de negocios, anclado al catastro oficial.**

Resultado: un **tablero de decisiones** para fiscalización, tributación y
desarrollo económico a escala de distrito (o de un par de manzanas, en el piloto).

> ⚠️ Piloto demostrativo. Las métricas son indicativas, no vinculantes.

---

## 📦 El entregable

Abre **`dashboard_miraflores.html`** en cualquier navegador (no necesita internet
ni servidor: es un único archivo autocontenido con los datos embebidos).

### Qué responde (3 modos)

| Modo | Pregunta de gestión | Color |
|---|---|---|
| 🎯 **Fiscalización** | ¿Dónde envío la ronda mañana? | rojo = brecha |
| 💰 **Tributación** | ¿Cuánta recaudación se pierde? | rojo × tarifa |
| 🏙️ **Desarrollo** | ¿Dónde hay saturación o vacíos? | teal = densidad |

### Interacciones
- 🖱️ **Arrastrar** para mover · **rueda / doble clic / pellizco** para zoom.
- Clic en **manzana** → ficha (zonificación, lotes, rubros) + zoom.
- Clic en **local** → ficha individual con **dirección** (`ej. Av. José Larco 765`),
  **lote catastral** y **zonificación del lote**.
- Toggle de **capas** (lotes, numeración de puertas, locales).
- **Bandeja de operativo** con checkbox → exporta la **ronda a CSV**.
- **Slider de tarifa** de saneamiento → recalcula recaudación potencial al instante.

---

## 🗂️ Estructura

```
Miraflorexp/
├── dashboard_miraflores.html    ← ⭐ entregable principal (abrir en el navegador)
├── mapa_piloto_miraflores.html  ← mapa SVG estático (v1, validación técnica)
├── template_dashboard.html      ← plantilla HTML/JS/CSS del tablero
├── build_dashboard.py           ← pipeline: cruza licencias × POIs × catastro → JSON → HTML
├── build_map.py                 ← genera el mapa SVG estático
├── data/                        ← datos crudos y procesados (zona de estudio)
│   ├── licencias_2020.xlsx      ← licencias municipales (fuente oficial)
│   ├── manzanas_estudio.geojson ← manzanas catastrales (GeoServer municipal)
│   ├── lotes_estudio.geojson    ← lotes catastrales
│   ├── vias_estudio.geojson     ← ejes viales
│   ├── numeracion_estudio.geojson ← numeración de puertas
│   ├── osm_estudio.osm          ← POIs OpenStreetMap (proxy de Google)
│   ├── licencias_respaldo.json  ← licencias georreferenciadas (procesadas)
│   └── pois_respaldo.json       ← POIs con flag de "respaldo formal" (procesados)
└── docs/
    └── ideacion.md              ← sesión de ideación original (10 ideas + matriz)
```

---

## 🔁 Cómo se obtuvieron los datos (reproducible)

### 1 · Licencias de funcionamiento (Municipalidad de Miraflores)
Publicadas en la Plataforma Nacional de Datos Abiertos del Perú:
`datosabiertos.gob.pe` → dataset *"Licencias de funcionamiento de la Municipalidad
de Miraflores"* (archivos mensuales, 2020–2022). El piloto usa el anual 2020
(10,249 registros). Columnas clave: `NOMBRE_VIA`, `GIRO`, `FECHA_INICIO`.

> ⚠️ Las licencias solo traen la **vía** (sin número ni nombre del local), por lo
> que se georreferencian asignando cada licencia a un punto sobre su eje vial.

### 2 · Catastro municipal (GeoServer WFS público)
El GeoServer oficial de la municipalidad expone capas WFS **abiertas**
(`geoserver.miraflores.gob.pe:8443/geoserver/idep/wfs`):

| Capa | Uso en el piloto |
|---|---|
| `idep:wms_tg_manzanas` | polígonos de manzana (base del choropleth) + `zon_vec` |
| `idep:wms_tg_lotes` | polígonos de lote + `cod_catastral`, `tipo_lote`, `zon_vec` |
| `idep:wms_tg_vias` | ejes viales + `nomenclatura` (llave de unión con licencias) |
| `idep:wms_tg_numeracion` | puertas numeradas → **direcciones reales** |

### 3 · Presencia digital (proxy de "Google mi negocio")
OpenStreetMap como **proxy** de Google Business/Places: mismo tipo de dato
(nombre, categoría, lat/lng) y gratuito/reproducible.

> Por qué proxy y no Google real: Places API oficial está limitada a consultas
> puntuales; una extracción de distrito entero requiere servicios de pago
> (Outscraper, Apify…). El pipeline está preparado para **intercambiar OSM por
> Places API** sin tocar el resto.

### 4 · Cruce (dos métodos)
- **a) Radio de proximidad (45 m)**: match exacto local↔licencia.
- **b) Núcleo de calle (60 m)** ⭐: un local está "respaldado" si en **su misma
  calle** existe una licencia de rubro compatible. Método robusto porque la calle
  es la llave común real entre ambas fuentes.

Resultado del cruce (zona de estudio Kennedy–Larco–La Mar, 158 ha):

```
Manzanas catastrales: 172   ·   Lotes: 2 097   ·   Puertas: 6 752
Locales visibles (proxy): 1 331
  Con respaldo formal en su calle:    590  (44.3%)
  Sin licencia compatible (brecha):   741  (55.7%)
Licencias georreferenciadas: 5 511  (sobre 10 249 del distrito)
```

### 5 · Regenerar el tablero
```bash
pip install pandas openpyxl shapely
python3 build_dashboard.py
```

---

## ⚠️ Límites y honestidad de alcance

- **La brecha NO es "informalidad"**: mezcla (1) desfase temporal (licencias 2020
  vs. presencia actual), (2) sesgo de cobertura (Google subrepresenta oficinas y
  servicios profesionales, que sí tienen licencia), y (3) geocodificación
  aproximada (sin número de puerta en la licencia).
- **Direcciones aproximadas**: se asocia el local a la puerta numerada más cercana
  de su misma calle. Con números exactos de licencia serían precisas.
- **Términos de Google**: si se migra a Places API, el dato crudo no debe
  redistribuirse; conviene agregar/anonimizar.
- **Privacidad (Ley 29733)**: no se exponen titulares de licencias; se trabaja a
  nivel de calle/manzana/lote.

---

## 🗺️ Siguientes pasos sugeridos

1. Migrar la capa de presencia digital a **Google Places API** (muestreo) o
   Outscraper (masivo): suma rating, reseñas, horarios.
2. Afinar el **supuesto recaudatorio** con tarifas reales (UIT, escala de multas
   de Miraflores, arbitrios).
3. Llevar el cruce a **todo el distrito** (las capas catastrales completas ya
   están publicadas en el GeoServer municipal).
4. Cruzar con **zonificación** para la vista de desarrollo económico → usos
   permitidos por lote.

---

## 📚 Fuentes
- Municipalidad Distrital de Miraflores — Licencias de funcionamiento
  ([datosabiertos.gob.pe](https://www.datosabiertos.gob.pe))
- Municipalidad Distrital de Miraflores — GeoServer WFS (catastro)
- OpenStreetMap (proxy de presencia digital) · © contribuidores OSM, ODbL
