"""Step 6: KBBQ share by source category tags, and a sub-category breakdown of the merged list.

Run after merge2.py (needs entities2.json). Prints:
  1) share of Korean places each source tags as barbecue
  2) precision-weighted breakdown of the merged list by dish category (name keywords)
"""
import json, re, collections, duckdb
from shapely.geometry import shape, Point
from shapely.prepared import prep

county = prep(shape(json.load(open('lacounty.geojson'))['features'][0]['geometry']))
NONK = re.compile(r"flame broiler|\bkogi\b|\bpho\b|sushi|japanese|katsu|ramen|chinese|thai|kebab|kabob|hawaiian|taco|teriyaki|boba|coffee|bakery|dessert|[一-鿿]", re.I)

# 1) per-source category share
ov = duckdb.sql("""select name,cat,alt,lon,lat from 'overture_la.parquet'
    where (cat='korean_restaurant' or (list_contains(alt,'korean_restaurant') and cat like '%restaurant%'))
      and coalesce(operating_status,'open')<>'permanently_closed' and confidence>=0.5""").fetchall()
ov = [r for r in ov if county.contains(Point(r[3], r[4])) and not NONK.search(r[0] or '')]
ovb = [r for r in ov if r[1] == 'barbecue_restaurant' or (r[2] and 'barbecue_restaurant' in r[2])]
print(f"Overture category tags: {len(ovb)}/{len(ov)} = {len(ovb)/len(ov):.1%} tagged barbecue")

osm = [e['tags'] for e in json.load(open('osm.json'))['elements']
       if 'korean' in e['tags'].get('cuisine', '').lower()
       and county.contains(Point(e.get('lon') or e['center']['lon'], e.get('lat') or e['center']['lat']))
       and not NONK.search(e['tags'].get('name', ''))]
ob = [t for t in osm if re.search('barbecue|bbq', t['cuisine'], re.I)]
print(f"OSM cuisine tags:       {len(ob)}/{len(osm)} = {len(ob)/len(osm):.1%} tagged barbecue")
print(f"Permit names:           92/272 = {92/272:.1%}")

# 2) sub-category breakdown over merged entities (name-based, precision-weighted)
E = json.load(open('entities2.json'))
def w(e):
    if 'K' in e['S']: return 1.0
    if 'pid' in e: return 0.80 if e['S'] == 'V' else 0.90
    return 0.55
CATS = [
    ('Tofu / soondubu', r'TOFU|SOON ?DU?BU|SUNDUBU'),
    ('Fried chicken', r'CHICKEN|CHIMAC|KYOCHON|BONCHON|PELICANA|BB\.?Q CHICK|BBQ CHICKEN|DAK\b|KKOKKO|CHIMM'),
    ('Soup / stew', r'SUL ?LUNG|SEOLLEONG|SULLUNG|GAMJA|GUKBAP|GOOK ?BAP|HAEJANG|GOM ?TANG|SAMGYE|TANG\b|JJIGAE|CHIGAE|BONE SOUP|SOONDAE|SOON DAE|JUK\b|BONJUK|JOOK'),
    ('Noodles / dumplings', r'NOODLE|NAENG|MYUN|GUKSU|KALGUKSU|MANDOO|MANDU|DUMPLING|KYODONG|JJAMPPONG|JJAJANG'),
    ('Gimbap / bunsik / street food', r'GIMBAP|KIMBAP|KIMBOB|BUNSIK|TTEOK|TOPOKKI|DDUK|STREET FOOD|CORN ?DOG|BOP\b|BAP\b|BOWL'),
    ('Pocha / pub / soju bar', r'POCHA|PUB\b|SOJU|HOF\b|TAVERN|ANJU|BAR\b|SUL ?JIP|JUMAK'),
    ('Jokbal / bossam / seafood', r'JOKBAL|BOSSAM|SEAFOOD|RAW FISH|HWE|FISH|CRAB|ONDAL|JAEBUDO'),
]
cnt = collections.Counter(); tot = 0
for e in E:
    nm = ' '.join(e['names']).upper(); ww = w(e); tot += ww
    if e['bbq']:
        cnt['Korean BBQ'] += ww; continue
    for c, rx in CATS:
        if re.search(rx, nm):
            cnt[c] += ww; break
    else:
        cnt['General / unspecified Korean'] += ww
print(f"\nMerged list, precision-weighted ({tot:.0f} likely-real of {len(E)} seen):")
for c, v in cnt.most_common():
    print(f"  {c:32} {v:5.0f}  {v/tot:5.1%}")
