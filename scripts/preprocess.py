#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preprocesa los datos crudos → JSONs procesados que consume build_dashboard.py.

Entradas (data/):
  licencias_2020.xlsx        licencias de funcionamiento (MD Miraflores, 2020)
  vias_estudio.geojson       ejes viales (GeoServer municipal)
  manzanas_estudio.geojson   manzanas catastrales (GeoServer municipal)
  osm_estudio.osm            POIs OpenStreetMap (proxy de Google)

Salidas (data/):
  licencias_respaldo.json     licencias georreferenciadas sobre su vía
  pois_respaldo.json          POIs con calle asignada + flag "respaldado"

Método de cruce (el robusto): un local está "respaldado" si en SU MISMA CALLE
(núcleo de nombre de vía) existe al menos una licencia de rubro compatible.
"""
import json, re, unicodedata, random, xml.etree.ElementTree as ET
from collections import Counter
import pandas as pd
from shapely.geometry import shape, Point, LineString, MultiLineString, Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely.geometry import box as Box

D = "data/"
random.seed(42)

# ------------------------------------------------------------------ normalización
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

# ------------------------------------------------------------------ vías → geometría
vias = json.load(open(D + "vias_estudio.geojson"))
def longest_line(g):
    if isinstance(g, MultiLineString):
        g = max(g.geoms, key=lambda x: x.length)
    return g if isinstance(g, LineString) else None

via_geom = {}; via_name = {}
for f in vias["features"]:
    p = f["properties"]; nome = p.get("nomenclatura") or ""
    c = core(nome)
    if not c or not f["geometry"]: continue
    ln = longest_line(shape(f["geometry"]))
    if ln is None: continue
    if c in via_geom and ln.length <= via_geom[c].length: continue
    via_geom[c] = ln; via_name[c] = nome
print("vías con geometría:", len(via_geom))

# ------------------------------------------------------------------ licencias
df = pd.read_excel(D + "licencias_2020.xlsx")
df["NOMBRE_VIA"] = df["NOMBRE_VIA"].astype(str).str.strip().str.upper()
df["core"] = df["NOMBRE_VIA"].apply(core)

# georreferenciar: punto determinista a lo largo del eje vial
def point_along(geom):
    d = geom.length * random.random()
    return geom.interpolate(d)

lic_all = []
for k, rk in df.groupby("core"):
    if k not in via_geom: continue
    for _, r in rk.iterrows():
        pt = point_along(via_geom[k])
        lic_all.append({
            "giro": str(r["GIRO"]), "via": r["NOMBRE_VIA"], "street_core": k,
            "lon": round(pt.x, 6), "lat": round(pt.y, 6),
            "fecha": int(r["FECHA_INICIO"]) if pd.notna(r["FECHA_INICIO"]) else None,
        })
print("licencias georreferenciadas (distrito estudios viales):", len(lic_all))

# recortar a la zona de estudio (bbox de las manzanas)
manz = json.load(open(D + "manzanas_estudio.geojson"))
mz_union = unary_union([shape(f["geometry"]) for f in manz["features"] if f["geometry"]])
xmin, ymin, xmax, ymax = mz_union.bounds
pad = 0.001
lic = [l for l in lic_all if xmin-pad <= l["lon"] <= xmax+pad and ymin-pad <= l["lat"] <= ymax+pad]
print("licencias en zona de estudio:", len(lic))

# ------------------------------------------------------------------ POIs (OSM → proxy Google)
EXCLUDE_AMENITIES = {'parking','bench','waste_basket','toilets','bicycle_parking','fountain','clock','atm'}
tree = ET.parse(D + "osm_estudio.osm"); root = tree.getroot()

def enrich(t):
    """Datos extra de OSM que gratis enriquecen la ficha (proxy de 'presencia digital')."""
    phone = t.get("phone") or t.get("contact:phone") or ""
    website = t.get("website") or t.get("contact:website") or ""
    hours = t.get("opening_hours") or ""
    cuisine = t.get("cuisine") or ""
    brand = t.get("brand") or ""
    return {"phone": phone.strip(), "website": website.strip(),
            "hours": hours.strip(), "cuisine": cuisine.strip(), "brand": brand.strip()}

pois = []
for nd in root.findall("node"):
    t = {x.attrib["k"]: x.attrib["v"] for x in nd.findall("tag")}
    cat = None
    if "amenity" in t and t["amenity"] not in EXCLUDE_AMENITIES: cat = t["amenity"]
    elif "shop" in t: cat = "shop:" + t["shop"]
    elif "tourism" in t and t["tourism"] in ('hotel','hostel','attraction','museum','gallery','guest_house','apartment'):
        cat = "tourism:" + t["tourism"]
    if cat is None: continue
    p = {"name": t.get("name") or t.get("brand") or "", "cat": cat,
         "lon": float(nd.attrib["lon"]), "lat": float(nd.attrib["lat"])}
    p.update(enrich(t))
    pois.append(p)

node_locs = {nd.attrib["id"]: (float(nd.attrib["lat"]), float(nd.attrib["lon"])) for nd in root.findall("node")}
for wy in root.findall("way"):
    t = {x.attrib["k"]: x.attrib["v"] for x in wy.findall("tag")}
    cat = None
    if "amenity" in t: cat = t["amenity"]
    elif "shop" in t: cat = "shop:" + t["shop"]
    elif "tourism" in t and t["tourism"] in ('hotel','hostel','attraction','museum','gallery','guest_house','apartment'):
        cat = "tourism:" + t["tourism"]
    if cat is None: continue
    refs = [r.attrib["ref"] for r in wy.findall("nd")]
    pts = [node_locs[r] for r in refs if r in node_locs]
    if not pts: continue
    p = {"name": t.get("name", ""), "cat": cat,
         "lon": sum(p[1] for p in pts)/len(pts), "lat": sum(p[0] for p in pts)/len(pts)}
    p.update(enrich(t))
    pois.append(p)
print("POIs crudos extraídos de OSM:", len(pois))

# recortar a la zona de estudio
pois = [p for p in pois if xmin-pad <= p["lon"] <= xmax+pad and ymin-pad <= p["lat"] <= ymax+pad]
print("POIs en zona de estudio:", len(pois))

# ------------------------------------------------------------------ deduplicar POIs
# OSM suele listar el mismo negocio 2 veces (nodo + contorno, o doble alta).
# Regla segura: mismo nombre a <=30m, o nombre contenido en otro a <=30m y mismo rubro → fundir.
import math
def _norm_name(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    s = re.sub(r'\b(la|el|los|las|de|del|y|e)\b', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def _catfam(cat):
    c = str(cat or '')
    if c.startswith('shop:') or c in ('marketplace', 'mall'): return 'shop'
    if c in ('restaurant','cafe','fast_food','food_court','bar','pub','nightclub','ice_cream','bakery','canteen','biergarten'): return 'food'
    if c in ('tourism:hotel','tourism:hostel','tourism:guest_house','tourism:motel','tourism:chalet','tourism:apartment'): return 'lodging'
    if c in ('bank','atm','bureau_de_change','money_transfer'): return 'bank'
    if c in ('pharmacy','dentist','doctors','clinic','hospital','veterinary','shop:chemist','shop:optician'): return 'health'
    if c in ('school','college','university','kindergarten','language_school','music_school'): return 'edu'
    return 'g:' + c

def _dist_m(a, b):
    R = 6371000
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp, dl = math.radians(b["lat"] - a["lat"]), math.radians(b["lon"] - a["lon"])
    h = math.sin(dp/2)**2 + math.cos(p1) * math.cos(p2) * math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(h))

def _richness(p):
    return sum(1 for k in ('phone','website','hours','cuisine','brand') if p.get(k))

def _merge_into(keep, drop_p):
    for k in ('phone','website','hours','cuisine','brand','name'):
        if not keep.get(k) and drop_p.get(k):
            keep[k] = drop_p[k]

def dedup_pois(pois, maxd_m=30):
    n = len(pois); drop = set()
    for i in range(n):
        if i in drop: continue
        ni = _norm_name(pois[i].get('name'))
        if not ni or len(ni) < 4: continue
        for j in range(i+1, n):
            if j in drop: continue
            nj = _norm_name(pois[j].get('name'))
            if not nj or len(nj) < 4: continue
            if _dist_m(pois[i], pois[j]) > maxd_m: continue
            same = (ni == nj)
            cont = ((ni in nj or nj in ni) and min(len(ni), len(nj)) >= 6)
            if not (same or cont): continue
            # mismo nombre: fundir siempre; nombre contenido: solo si mismo rubro
            if same or _catfam(pois[i]['cat']) == _catfam(pois[j]['cat']):
                keep, rem = (i, j)
                if _richness(pois[j]) > _richness(pois[i]):
                    keep, rem = (j, i)
                _merge_into(pois[keep], pois[rem])
                drop.add(rem)
    removed = len(drop)
    out = [p for idx, p in enumerate(pois) if idx not in drop]
    print(f"deduplicación POIs: eliminados {removed} duplicados → quedan {len(out)}")
    return out

pois = dedup_pois(pois)

# ------------------------------------------------------------------ respaldo por calle
# reglas giro → categorías compatibles
RULES = [
 (r'RESTAURANT|CAFET|FUENTE DE SODA|CEVICH|SANGUCHE|CHIFA|POLL|PIZZA|FAST|BROASTER|COMIDA|SALCHIPAPA|HAMBURGUE', {'restaurant','cafe','fast_food','food_court'}),
 (r'BAR\b|CANTINA|PUB', {'bar','pub'}),
 (r'PANADERIA|PASTELERIA', {'shop:bakery','shop:confectionery'}),
 (r'BODEGA|MINIMARKET|ABARROT|SUPERMERCAD|VINOS|LICOR', {'shop:convenience','shop:supermarket','shop:alcohol','shop:beverages'}),
 (r'BELLEZA|PELUQUERIA|BARBER|SPA|MANICURE|COSMETIC', {'shop:hairdresser','shop:beauty','shop:cosmetics'}),
 (r'JOYERIA|RELOJERIA|ALHAJA', {'shop:jewelry'}),
 (r'FARMACIA|BOTICA|FARMACEUTIC', {'pharmacy','shop:chemist'}),
 (r'BANCO|CAJERO|CORRESPONSAL|FINANCIER|COOPERATIVA|CAMBIO', {'bank','atm','bureau_de_change'}),
 (r'ROPA|TEXTIL|MODA|CONFECCION|BOUTIQUE', {'shop:clothes','shop:fashion','shop:boutique'}),
 (r'CALZADO|CARTERA|CUERO|ZAPATERIA|BOLSO', {'shop:shoes','shop:bag','shop:leathergoods'}),
 (r'VIAJE', {'shop:travel_agency'}),
 (r'COMPUTADOR|SOFTWARE|TELEFON|CELULAR|ELECTRONIC|INFORMATIC|INTERNET|APARATOS|SONIDO', {'shop:electronics','shop:computer','shop:mobile_phone'}),
 (r'HOSPEDAJE|ALBERGUE|HOTEL|HOSTAL|PENSION', {'tourism:hotel','tourism:hostel','tourism:guest_house','tourism:apartment','tourism:chalet'}),
 (r'ODONTOLOGIC|DENTAL', {'dentist','clinic','doctors'}),
 (r'CONSULTORIO|CLINICA|MEDIC|VETERINARIA|LABORATORIO|POLICLINICO|HOSPITAL|OPTICA', {'doctors','clinic','hospital','veterinary','dentist','shop:optician'}),
 (r'LAVANDERIA|TINTORERIA|LAVASECO', {'shop:laundry','shop:dry_cleaning'}),
 (r'LIBRERIA|LIBRO', {'shop:books'}),
 (r'ARTESANIA|REGALO|RECUERDO|SOUVENIR', {'shop:gift','shop:art','shop:craft'}),
 (r'FERRETERIA|PINTURA|ELECTRICIDAD|GASFITERIA', {'shop:hardware','shop:doityourself','shop:paint'}),
 (r'GIMNASIO|GYM|FITNESS', {'gym','fitness_centre'}),
 (r'CASINO|BILLAR|JUEGO|TRAGAMONEDA|BOWLING', {'casino','amusement_arcade','adult_gaming_centre'}),
 (r'JUGUET', {'shop:toys'}),
 (r'FLORERIA|FLORES', {'shop:florist'}),
 (r'PERFUMERIA', {'shop:perfumery','shop:beauty'}),
 (r'COPIA|IMPRENTA|FOTOCOPIA|IMPRESION', {'shop:copyshop'}),
 (r'MUEBLE|DECORACION|TAPICERIA', {'shop:furniture','shop:interior_decoration'}),
 (r'ESTACIONAMIENTO|ESTAC|COCHERA', {'parking','parking_entrance'}),
 (r'ESCUELA|ACADEMIA|COLEGIO|EDUCATIV|INSTITUTO', {'school','college','language_school','music_school'}),
]
def allowed(giro):
    g = str(giro).upper(); s = set()
    for pat, cats in RULES:
        if re.search(pat, g): s |= cats
    return s

# giros por calle
lic_core = {}
for l in lic:
    lic_core.setdefault(l["street_core"], set()).add(l["giro"].upper())

# índice espacial de vías
vkeys = list(via_geom.keys()); vgeoms = [via_geom[k] for k in vkeys]
vtree = STRtree(vgeoms)
def nearest_via(lon, lat, radius_m=60):
    dr = radius_m / 111000
    pt = Point(lon, lat)
    best, bestd = None, 9e9
    for gi in vtree.query(Box(lon-dr, lat-dr, lon+dr, lat+dr)):
        d = vgeoms[gi].distance(pt)
        if d < bestd: bestd, best = d, vkeys[gi]
    return best, bestd

pois_out = []
for p in pois:
    k, _ = nearest_via(p["lon"], p["lat"])
    p["street_core"] = k
    p["street_name"] = via_name.get(k, "")
    p["respaldado"] = bool(k and k in lic_core and ({p["cat"]} & {c for g in lic_core[k] for c in allowed(g)}))
    pois_out.append(p)

rsp = sum(1 for p in pois_out if p["respaldado"])
print(f"POIs: {len(pois_out)} | respaldados {rsp} ({rsp/len(pois_out)*100:.1f}%) | brecha {len(pois_out)-rsp}")

# ------------------------------------------------------------------ guardar
json.dump(lic, open(D + "licencias_respaldo.json", "w"), ensure_ascii=False)
json.dump(pois_out, open(D + "pois_respaldo.json", "w"), ensure_ascii=False)
print("OK → licencias_respaldo.json / pois_respaldo.json")
