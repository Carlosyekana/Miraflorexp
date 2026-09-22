#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pipeline completo del piloto: cruza licencias × POIs × catastro (lotes, manzanas,
numeración) y genera el JSON inyectado en el dashboard.

Entradas (data/):
  wms_tg_manzanas_estudio.geojson | wms_tg_vias_estudio.geojson | wms_tg_lotes_4326.geojson
  wms_tg_numeracion_4326.geojson  | licencias_respaldo.json    | pois_respaldo.json
"""
import json, math, re, unicodedata
from collections import Counter
from shapely.geometry import shape, Point, Polygon, MultiPolygon, LineString, MultiLineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely.validation import make_valid

D = "data/"

manz = json.load(open(D + "manzanas_estudio.geojson"))
vias = json.load(open(D + "vias_estudio.geojson"))
lotes = json.load(open(D + "lotes_estudio.geojson"))
numer = json.load(open(D + "numeracion_estudio.geojson"))
pois = json.load(open(D + "pois_respaldo.json"))
lic  = json.load(open(D + "licencias_respaldo.json"))

# ------------------------------------------------------------------ utils
VIA_TYPE_TOKENS = {'CALL','CALLE','CA','AV','AVENIDA','JR','JIRON','PS','PSJ','PSJE','PASAJE',
 'PASEO','PASE','MLC','MLCN','MALECON','OVALO','PLAZA','PARQUE','CRT','CARRETERA','ALAMEDA',
 'MAL','PROLON','PROLONGACION','CUADRA','CDRA','CALLEJON'}
def norm(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii','ignore').decode().upper()
    return re.sub(r'[^A-Z0-9]+',' ', s).strip()
def core(s):
    toks = norm(s).split()
    while toks and toks[0] in VIA_TYPE_TOKENS:
        toks = toks[1:]
    return ' '.join(toks)

# ------------------------------------------------------------------ manzanas
polys = []; mz_meta = []
for f in manz["features"]:
    g = shape(f["geometry"])
    if not g.is_valid: g = make_valid(g)
    polys.append(g)
    mz_meta.append({"cod": f["properties"].get("cod_manzana"), "zon_vec": f["properties"].get("zon_vec")})
mz_tree = STRtree(polys)

def assign_mz(x, y, maxd=0.0012):
    pt = Point(x, y)
    for gi in mz_tree.query(pt):
        if polys[gi].contains(pt):
            return gi
    near = mz_tree.nearest(pt)
    i = int(near)
    return i if i < len(polys) and polys[i].distance(pt) <= maxd else None

# ------------------------------------------------------------------ vías
def line_of(g):
    if isinstance(g, MultiLineString):
        return [list(ln.coords) for ln in g.geoms]
    if isinstance(g, LineString):
        return [list(g.coords)]
    return []

via_lines = []
via_by_cod = {}
WIDTHS = {'PRINCIPALES': 2.7, 'COLECTORAS': 2.0, 'LOCALES': 1.15}
for f in vias["features"]:
    p = f["properties"]; nome = p.get("nomenclatura") or ""
    clas = (p.get("clasificacion") or "LOCALES").upper()
    for k in ("cod_via", "codigo"):
        if p.get(k) is not None:
            via_by_cod[str(p.get(k))] = nome
    if not f["geometry"]: continue
    try:
        lines = line_of(shape(f["geometry"]))
    except Exception:
        continue
    w = WIDTHS.get(clas, 1.1)
    for ln in lines:
        pts = [[round(x, 6), round(y, 6)] for x, y in ln]
        if len(pts) >= 2:
            via_lines.append({"pts": pts, "w": w, "n": nome, "clas": clas})

# ------------------------------------------------------------------ lotes (clip estudio + corregir + simplificar)
STUDIO = [ -77.0392, -12.1309, -77.0206, -12.1136 ]
from shapely.geometry import box as Box
sbox = Box(STUDIO[0], STUDIO[1], STUDIO[2], STUDIO[3])

lote_polys = []; lote_info = []
for f in lotes["features"]:
    if not f["geometry"]: continue
    p = f["properties"]
    g = shape(f["geometry"])
    if not g.is_valid: g = make_valid(g)
    if g.geom_type not in ("Polygon", "MultiPolygon"): continue
    if not sbox.contains(g.centroid): continue
    lote_polys.append(g)
    lote_info.append({
        "cod_catastral": p.get("cod_catastral"),
        "cod_manzana": p.get("cod_manzana"), "cod_lote": p.get("cod_lote"),
        "tipo_lote": p.get("tipo_lote"), "zon_vec": p.get("zon_vec"),
        "mz_i": None, "area": round(g.area * (111320 ** 2), 1),
    })

# asignar lote -> manzana
for li in range(len(lote_polys)):
    c = lote_polys[li].centroid
    mi = assign_mz(c.x, c.y, maxd=0.0015)
    lote_info[li]["mz_i"] = mi
lotes_sin_mz = sum(1 for i in lote_info if i["mz_i"] is None)
print("lotes en estudio:", len(lote_polys), "| sin manzana:", lotes_sin_mz)

def ring_of(g):
    g2 = g.simplify(0.000004, preserve_topology=True)
    if isinstance(g2, Polygon):
        ext = list(g2.exterior.coords)
    elif isinstance(g2, MultiPolygon):
        ext = list(max(g2.geoms, key=lambda p: p.area).exterior.coords)
    else:
        ext = list(g2.coords)
    if ext and ext[0] == ext[-1]: ext = ext[:-1]
    if len(ext) < 3: return None
    return [[round(x, 6), round(y, 6)] for x, y in ext]

lotes_out = []
for i, g in enumerate(lote_polys):
    pts = ring_of(g)
    if not pts: continue
    c = g.centroid
    inf = lote_info[i]
    lotes_out.append({
        "pts": pts, "cx": round(c.x, 6), "cy": round(c.y, 6),
        "cc": inf["cod_catastral"], "tipo": inf["tipo_lote"], "zv": inf["zon_vec"],
        "mz": inf["mz_i"] if inf["mz_i"] is not None else -1,
    })
print("lotes renderizables:", len(lotes_out))

# ------------------------------------------------------------------ numeración -> direcciones
num_info = []
for f in numer["features"]:
    if not f["geometry"]: continue
    p = f["properties"]
    g = shape(f["geometry"])
    if not sbox.contains(g.centroid): continue
    norte = via_by_cod.get(str(p.get("cod_via")))
    if not norte:
        continue
    num_info.append({
        "nro": p.get("nro_puerta"), "via": norte, "core": core(norte),
        "lon": round(g.centroid.x, 6), "lat": round(g.centroid.y, 6),
    })
num_pts = [Point(x["lon"], x["lat"]) for x in num_info]
num_tree = STRtree(num_pts)
print("numeración en estudio con vía:", len(num_info))

def nearest_door(poi_street, x, y, radius_m=45):
    key = core(poi_street or "")
    if not key: return None, None
    pt = Point(x, y)
    dr = radius_m / 111000
    cand = num_tree.query(Box(x - dr, y - dr, x + dr, y + dr))
    best = None; bestd = 1e9
    for gi in cand:
        info = num_info[gi]
        if info["core"] != key: continue
        d = num_pts[gi].distance(pt)
        if d < bestd:
            bestd = d; best = info
    return best, bestd

# lote asignado al POI
lote_tree = STRtree(lote_polys)
def nearest_lote(x, y):
    pt = Point(x, y)
    for gi in lote_tree.query(pt):
        if lote_polys[gi].contains(pt):
            return lote_info[gi]
    near = lote_tree.nearest(pt)
    return lote_info[int(near)]

# ------------------------------------------------------------------ licencias -> manzanas
lic_mz = Counter(); mz_giro = {}
for l in lic:
    i = assign_mz(l["lon"], l["lat"])
    if i is None: continue
    lic_mz[i] += 1
    mz_giro.setdefault(i, Counter())[l["giro"].upper()] += 1

# ------------------------------------------------------------------ POIs
for p in pois:
    p["mz"] = assign_mz(p["lon"], p["lat"])
    # dirección por numeración
    door, dd = nearest_door(p.get("street_name") or p.get("street") or "", p["lon"], p["lat"])
    if door:
        p["address"] = f"{door['via']} {door['nro']}".replace("  ", " ").strip()
    else:
        p["address"] = (p.get("street_name") or "") + " (s/n)"
    linf = nearest_lote(p["lon"], p["lat"])
    p["lote"] = linf["cod_catastral"] if linf else None
    p["lote_zon"] = linf["zon_vec"] if linf else None

# ------------------------------------------------------------------ manzanas output
manzanas_out = []
for i, g in enumerate(polys):
    pts = ring_of(g)
    if not pts: continue
    top = mz_giro.get(i, Counter())
    lotes_mz = [lf for lf in lote_info if lf["mz_i"] == i]
    zonDist = Counter((str(lf["zon_vec"]) if lf["zon_vec"] is not None else "n/d") for lf in lotes_mz)
    area_priv = sum(lf["area"] for lf in lotes_mz if str(lf["tipo_lote"]).upper() == "PRIVADO")
    c = g.centroid
    manzanas_out.append({
        "i": i, "cod": mz_meta[i]["cod"], "zon_vec": mz_meta[i]["zon_vec"],
        "n_lic": lic_mz.get(i, 0),
        "topG": [gx for gx, _ in top.most_common(4)],
        "pts": pts, "cx": round(c.x, 6), "cy": round(c.y, 6),
        "n_lotes": len(lotes_mz),
        "area_priv_m2": round(area_priv, 0),
        "zonDist": dict(zonDist),
    })
print("manzanas:", len(manzanas_out))

# reindexar POI.mz
newidx = {m["i"]: k for k, m in enumerate(manzanas_out)}
for p in pois:
    p["mz"] = newidx.get(p["mz"], -1)
for lo in lotes_out:
    lo["mz"] = newidx.get(lo["mz"], -1)

# ------------------------------------------------------------------ bounds
union = unary_union(polys)
xmin, ymin, xmax, ymax = union.bounds
pad = 0.0008
xmin -= pad; ymin -= pad; xmax += pad; ymax += pad

# ------------------------------------------------------------------ labels vías
via_best = {}
for f in vias["features"]:
    p = f["properties"]; nome = p.get("nomenclatura") or ""
    c = core(nome)
    if not c or not f["geometry"]: continue
    g = shape(f["geometry"])
    if isinstance(g, MultiLineString): g = max(g.geoms, key=lambda x: x.length)
    if not isinstance(g, LineString): continue
    if c not in via_best or g.length > via_best[c].length:
        via_best[c] = g
labels = []
WANT = [('JOSE A LARCO','Av. José Larco'), ('MARISCAL LA MAR','Av. Mariscal La Mar'),
        ('28 DE JULIO','Av. 28 de Julio'), ('SCHELL','Calle Schell'),
        ('ALCANFORES','Calle Alcanfores'), ('DIAGONAL','Av. Diagonal')]
for c, txt in WANT:
    if c in via_best:
        ln = via_best[c]
        mid = ln.interpolate(0.5, normalized=True)
        a = ln.coords[0]; b = ln.coords[-1]
        ang = math.degrees(math.atan2(b[1]-a[1], b[0]-a[0]))
        labels.append({"t": txt, "lon": round(mid.x, 6), "lat": round(mid.y, 6), "ang": round(ang, 1)})
labels.append({"t": "Parque Kennedy", "lon": -77.0301, "lat": -12.1240, "ang": 0})

street_counts = Counter(p.get("street_name") or "" for p in pois if p.get("street_name"))
streets = [{"name": n, "n": c} for n, c in street_counts.most_common(14)]

# ------------------------------------------------------------------ índice de búsqueda
# calles con bbox (desde la geometría oficial de vías)
calle_bb = {}
for f in vias["features"]:
    p = f["properties"]; nome = p.get("nomenclatura") or ""
    if not f["geometry"] or not nome: continue
    g = shape(f["geometry"])
    x0, y0, x1, y1 = g.bounds
    if nome in calle_bb:
        a = calle_bb[nome]
        calle_bb[nome] = [min(a[0], x0), min(a[1], y0), max(a[2], x1), max(a[3], y1)]
    else:
        calle_bb[nome] = [x0, y0, x1, y1]
calles = [{"name": n, "bb": [round(v, 6) for v in bb]} for n, bb in calle_bb.items()]

# locales con nombre para búsqueda
localesIndex = [
    {"i": i, "name": p["name"], "cat": p["cat"], "address": p.get("address", "")}
    for i, p in enumerate(pois) if p.get("name")
]

un = sum(1 for p in pois if not p.get("respaldado"))
rsp = sum(1 for p in pois if p.get("respaldado"))
data = {
    "bounds": [xmin, ymin, xmax, ymax],
    "meta": {
        "poiTotal": len(pois), "licTotal": sum(lic_mz.values()), "mzTotal": len(manzanas_out),
        "noResp": un, "resp": rsp,
        "lotesTotal": len(lotes_out), "numeracionTotal": len(num_info),
        "areaEstudioHa": round(union.area * (111320**2) / 10000, 1),
    },
    "manzanas": manzanas_out,
    "lotes": lotes_out,
    "vias": via_lines,
    "numeracion": [{"lon": i["lon"], "lat": i["lat"], "nro": i["nro"]} for i in num_info],
    "pois": [{"mz": p["mz"], "cat": p["cat"], "resp": bool(p.get("respaldado")),
              "name": p.get("name") or "", "street": p.get("street_name") or "",
              "address": p.get("address", ""), "lote": p.get("lote"), "lote_zon": p.get("lote_zon"),
              "phone": p.get("phone") or "", "website": p.get("website") or "",
              "hours": p.get("hours") or "", "cuisine": p.get("cuisine") or "",
              "brand": p.get("brand") or "",
              "lon": round(p["lon"], 6), "lat": round(p["lat"], 6)} for p in pois],
    "streets": streets,
    "labels": labels,
    "calles": calles,
    "localesIndex": localesIndex,
}

out = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
print("JSON bytes:", len(out))
print("meta:", data["meta"])

tpl = open("template_dashboard.html", encoding="utf-8").read()
html = tpl.replace("__DATA_JSON__", out)
open("dashboard_miraflores.html", "w", encoding="utf-8").write(html)
open("index.html", "w", encoding="utf-8").write(html)   # para GitHub Pages
print("dashboard_miraflores.html:", len(html)//1024, "KB")
