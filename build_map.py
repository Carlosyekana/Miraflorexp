#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera un mapa SVG autocontenido (sin dependencias externas) del piloto:
brecha entre licencias municipales (Miraflores 2020) y presencia digital (POIs OSM).
"""
import json
from shapely.geometry import shape, LineString, MultiLineString, MultiPolygon, Polygon, mapping
from shapely.ops import unary_union, transform
from shapely.geometry import box

D = "data/"

# ---------- datos ----------
pois = json.load(open(D + "pois_respaldo.json"))
lic = json.load(open(D + "licencias_respaldo.json"))
manz = json.load(open(D + "manzanas_estudio.geojson"))
vias = json.load(open(D + "vias_estudio.geojson"))

# ---------- bounds del estudio ----------
polys = [shape(f["geometry"]) for f in manz["features"]]
union = unary_union(polys)
xmin, ymin, xmax, ymax = union.bounds
pad = 0.0009  # ~100 m
xmin -= pad; ymin -= pad; xmax += pad; ymax += pad

W, H = 1000, 1000
def X(lon): return (lon - xmin) / (xmax - xmin) * W
def Y(lat): return (ymax - lat) / (ymax - ymin) * H

def ring_svg(geom, close=True):
    """geom -> puntos svg; geom.exterior.coords"""
    if isinstance(geom, Polygon):
        rings = [geom.exterior.coords] + [r.coords for r in geom.interiors]
    elif isinstance(geom, MultiPolygon):
        rings = []
        for p in geom.geoms:
            rings += [p.exterior.coords] + [r.coords for r in p.interiors]
    else:
        rings = [list(geom.coords)]
    out = []
    for r in rings:
        coords = [f"{X(c[0]):.2f},{Y(c[1]):.2f}" for c in r]
        # evitar punto final duplicado con el inicial
        if len(coords) > 1 and coords[0] == coords[-1]:
            coords = coords[:-1]
        if not coords:
            continue
        p = 'M' + coords[0] + ' L' + ' L'.join(coords[1:]) + (' Z' if close else '')
        out.append(p)
    return out

# ---------- SVG: manzanas ----------
manz_paths = []
for f in manz["features"]:
    g = shape(f["geometry"])
    manz_paths.extend(ring_svg(g))
manz_d = " ".join(manz_paths)

# ---------- SVG: vías ----------
via_segs = []
for f in vias["features"]:
    g = shape(f["geometry"])
    if isinstance(g, MultiLineString):
        lines = list(g.geoms)
    else:
        lines = [g]
    for ln in lines:
        coords = list(ln.coords)
        pts = " ".join(f"{X(c[0]):.2f},{Y(c[1]):.2f}" for c in coords)
        via_segs.append(f'<polyline points="{pts}" />')
vias_svg = '\n  '.join(via_segs)

# ---------- SVG: licencias (puntos azules) ----------
lic_svg = []
seen = set()
for l in lic:
    px, py = X(l["lon"]), Y(l["lat"])
    key = (round(px,1), round(py,1))
    if key in seen: continue
    seen.add(key)
    lic_svg.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="1.15" fill="#4a7bbf" fill-opacity="0.5"/>')
lic_svg = "\n  ".join(lic_svg)

# ---------- SVG: POIs (verde/rojo) ----------
poi_svg = []
esc = {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}
def esc_(s): return "".join(esc.get(c,c) for c in str(s))
n_resp = 0
cat_poi = []
for p in pois:
    if p["respaldado"]: n_resp += 1
    color = "#1f9d55" if p["respaldado"] else "#e0524d"
    r = 2.6 if p["respaldado"] else 2.3
    street = p.get("street_name") or "—"
    name = p.get("name") or "(sin nombre)"
    cat_poi.append(p["cat"])
    tip = f'{esc_(name)} · {esc_(p["cat"].replace("shop:","").replace("tourism:",""))}\nCalle: {esc_(street)}\n{"✔ respaldo formal" if p["respaldado"] else "✘ sin licencia compatible"}'
    poi_svg.append(f'<circle cx="{X(p["lon"]):.2f}" cy="{Y(p["lat"]):.2f}" r="{r}" fill="{color}" fill-opacity="0.82" stroke="#ffffff" stroke-width="0.4"><title>{tip}</title></circle>')
poi_svg = "\n  ".join(poi_svg)

# ---------- labels de vías principales ----------
labels = [
    ("Av. José Larco", -77.0298, -12.1262, -72),
    ("Av. Mariscal La Mar", -77.0346, -12.1210, -18),
    ("Calle Schell", -77.0262, -12.1218, 18),
    ("Av. 28 de Julio", -77.0298, -12.1290, -8),
    ("Parque Kennedy", -77.0300, -12.1240, 0),
]
labels_svg = "".join(
    f'<text x="{X(lo):.2f}" y="{Y(la):.2f}" font-size="9.5" font-family="Arial" fill="#6b6a63" '
    f'transform="rotate({a} {X(lo):.2f} {Y(la):.2f})">{t}</text>'
    for t, lo, la, a in labels
)

# ---------- stats ----------
n_lic = len(lic)
n_poi = len(pois)
sin_resp = n_poi - n_resp
pct = n_resp / n_poi * 100
from collections import Counter
top = Counter(p["cat"].replace("shop:","").replace("tourism:","") for p in pois).most_common(3)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" style="width:100%;max-width:1100px;height:auto;display:block;background:#fbfaf5;font-family:Arial,Helvetica,sans-serif;">
<rect x="0" y="0" width="{W}" height="{H}" fill="#fbfaf5"/>
<g id="scene">
  <!-- manzanas -->
  <path d="{manz_d}" fill="#f6f1e6" stroke="#d8d2c2" stroke-width="0.6"/>
  <!-- vías -->
  <g stroke="#bab5a6" stroke-width="1.4" fill="none">{vias_svg}</g>
  <!-- licencias -->
  {lic_svg}
  <!-- pois -->
  {poi_svg}
  <!-- labels -->
  <g>{labels_svg}</g>
</g>

<!-- panel título -->
<g>
  <rect x="14" y="14" width="430" height="118" rx="10" fill="#ffffff" fill-opacity="0.94" stroke="#e2ddd0"/>
  <text x="30" y="40" font-size="17" font-weight="bold" fill="#2b2a26">PILOTO · Miraflores: registro formal vs. presencia digital</text>
  <text x="30" y="59" font-size="11.5" fill="#4d4b44">Eje Kennedy / Larco / La Mar · base municipal + POIs (proxy Google)</text>
  <text x="30" y="77" font-size="11.5" fill="#4d4b44">Licencias funcionamiento 2020 (MD Miraflores) × POIs OpenStreetMap</text>
  <text x="30" y="95" font-size="10" fill="#8a877c">Matching por núcleo de calle + rubro compatible · radio 60 m</text>
  <text x="30" y="112" font-size="10" fill="#8a877c">Proyección local WGS84 (~1.4 km de ancho) · escala no oficial</text>
</g>

<!-- panel stats -->
<g>
  <rect x="{W-330}" y="14" width="316" height="150" rx="10" fill="#ffffff" fill-opacity="0.94" stroke="#e2ddd0"/>
  <text x="{W-316}" y="40" font-size="13" font-weight="bold" fill="#2b2a26">Resultados del cruce</text>
  <rect x="{W-316}" y="50" width="12" height="12" rx="6" fill="#4a7bbf" fill-opacity="0.7"/>
  <text x="{W-298}" y="61" font-size="11.5" fill="#4d4b44">Licencias georreferenciadas: {n_lic:,}</text>
  <rect x="{W-316}" y="70" width="12" height="12" rx="6" fill="#1f9d55"/>
  <text x="{W-298}" y="81" font-size="11.5" fill="#4d4b44">Negocios con respaldo formal: {n_resp:,} ({pct:.1f}%)</text>
  <rect x="{W-316}" y="90" width="12" height="12" rx="6" fill="#e0524d"/>
  <text x="{W-298}" y="101" font-size="11.5" fill="#4d4b44">Negocios sin licencia compatible: {sin_resp:,} ({(n_poi-n_resp)/n_poi*100:.1f}%)</text>
  <text x="{W-316}" y="121" font-size="10.5" fill="#8a877c">Categorías dominantes (proxy): </text>
  <text x="{W-316}" y="136" font-size="10.5" fill="#8a877c">{", ".join(f"{c} ({n})" for c,n in top)}</text>
  <text x="{W-316}" y="153" font-size="10" fill="#b3afa2">Piloto demostrativo · no es hallazgo oficial</text>
</g>

<!-- leyenda de colores -->
<g>
  <rect x="14" y="{H-104}" width="236" height="90" rx="10" fill="#ffffff" fill-opacity="0.94" stroke="#e2ddd0"/>
  <text x="30" y="{H-82}" font-size="12" font-weight="bold" fill="#2b2a26">Leyenda</text>
  <circle cx="32" cy="{H-66}" r="4" fill="#4a7bbf" fill-opacity="0.6"/>
  <text x="42" y="{H-62}" font-size="11" fill="#4d4b44">Licencia municipal (radicada por calle)</text>
  <circle cx="32" cy="{H-46}" r="4" fill="#1f9d55"/>
  <text x="42" y="{H-42}" font-size="11" fill="#4d4b44">POI con licencia compatible en su calle</text>
  <circle cx="32" cy="{H-26}" r="4" fill="#e0524d"/>
  <text x="42" y="{H-22}" font-size="11" fill="#4d4b44">POI sin licencia compatible (señal brecha)</text>
</g>
</svg>'''

open("mapa_piloto_miraflores.html", "w", encoding="utf-8").write(svg)
n_geom_pts = len(manz_paths)
print("SVG generado:", len(svg)//1024, "KB")
print(f"POIs: {n_poi} | respaldados {n_resp} ({pct:.1f}%) | licencias ploteadas {len(seen)}")
print("mapa_piloto_miraflores.html listo")
