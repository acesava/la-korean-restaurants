exec(open('merge.py').read().split('# ---- load POIs')[0])
from shapely.geometry import shape as _sh
city=prep(_sh(json.load(open('lacity.geojson'))['features'][0]['geometry']))
HANGUL=re.compile(r'[가-힣]')
NONK=re.compile(r"flame broiler|\bkogi\b|alibi room|\bpho\b|sushi|japanese|katsu|ramen|izakaya|shokudo|chinese|szechuan|sichuan|dim sum|\bthai\b|kebab|kabob|kaboob|mediterranean|hawaiian|ohana|taco|mexican|teriyaki|boba|\btea\b|coffee|bakery|dessert|bingsu|bingsoo|donut|acai|yogurt|grocery|salon|\bspa\b|church|dental|clinic|\bpoke\b|burger|rib shack|kazu|cali pho|robowok|mixabowl|kebab|byblos|shrine room|[一-鿿]",re.I)
pois=[]
for e in json.load(open('osm.json'))['elements']:
    t=e['tags']; c=t.get('cuisine','').lower(); n=t.get('name','')
    if 'korean' not in c: continue
    la=e.get('lat') or e['center']['lat']; lo=e.get('lon') or e['center']['lon']
    pois.append(dict(src='O',name=n,addr=(t.get('addr:housenumber','')+' '+t.get('addr:street','')).strip(),zip=t.get('addr:postcode','')[:5],city=t.get('addr:city',''),la=la,lo=lo,
        bbq=('barbecue' in c or 'bbq' in c or bool(re.search(r'bbq|barbe|galbi|kalbi|gogi|samgyeop',n,re.I)))))
ov=duckdb.sql("""select * from 'overture_la.parquet' where (cat='korean_restaurant' or (list_contains(alt,'korean_restaurant') and (cat like '%restaurant%' or cat in ('bar','pub','buffet_restaurant'))))
                 and coalesce(operating_status,'open')<>'permanently_closed' and confidence>=0.5""").df()
S_=lambda x: x if isinstance(x,str) else ''
for r in ov.itertuples():
    alt=list(r.alt) if hasattr(r.alt,"__len__") and not isinstance(r.alt,str) else []
    pois.append(dict(src='V',name=S_(r.name),addr=S_(r.addr),zip=S_(r.zip)[:5],city=S_(r.city),la=r.lat,lo=r.lon,
        bbq=(r.cat=='barbecue_restaurant' or 'barbecue_restaurant' in alt or bool(re.search(r'bbq|barbe|galbi|kalbi|gogi|samgyeop',S_(r.name),re.I)))))
pois=[p for p in pois if county.contains(Point(p['lo'],p['la']))]
n0=len(pois); pois=[p for p in pois if not NONK.search(p['name'])]; print('dropped non-Korean-named POIs:',n0-len(pois))
hd=[p for p in pois if own_hd(p['city'],p['zip'])]; pois=[p for p in pois if not own_hd(p['city'],p['zip'])]
print('Pasadena/Long Beach/Vernon POIs (outside permit data):',len(hd),[p['name'] for p in hd])
ent={}
def mk(pid): p=P[pid]; return dict(S=set(),bbq=False,name=p['name'],addr=p['addr'],pid=pid,la=p['la'],lo=p['lo'],names=[p['name']])
for pid in VK: e=ent['P:'+pid]=mk(pid); e['S'].add('K'); e['bbq']=pid in VB
unl=[]; how=collections.Counter()
for p in pois:
    pid,m=link(p['name'],p['addr'],p['zip'],p['la'],p['lo'])
    if pid and NONK.search(P[pid]['name']) and not kw.search(P[pid]['name']): pid=None; m='rejected-nonK-permit'
    how[(p['src'],m)]+=1
    if pid:
        e=ent.get('P:'+pid)
        # Co-location guard: a multi-tenant address can hold several restaurants under one permit. If this permit already
        # has a map place attached and the new place resembles neither the permit name nor that place, treat it as a
        # separate (unconfirmed) restaurant instead of merging. Korean-script names can't be compared, so they merge.
        halves=[h for h in P[pid]['name'].split(' / ') if h.strip()]
        pois_here=e['names'][1:] if e else []
        if pois_here and not HANGUL.search(p['name']) and max(nsim(p['name'],h) for h in halves)<0.6 and all(nsim(p['name'],x)<0.6 for x in pois_here):
            how[(p['src'],'split-colocated')]+=1; unl.append(p); continue
        e=ent.setdefault('P:'+pid,mk(pid)); e['S'].add(p['src']); e['bbq']|=p['bbq']; e['names'].append(p['name'])
    else: unl.append(p)
for p in unl:
    hit=None
    for e in ent.values():
        if e['la'] is None: continue
        d=dist(p['la'],p['lo'],e['la'],e['lo'])
        if d<150 and max(nsim(p['name'],x) for x in e['names'])>=0.6: hit=e;break
        if d<40 and HANGUL.search(p['name']): hit=e;break
    if hit: hit['S'].add(p['src']); hit['bbq']|=p['bbq']; hit['names'].append(p['name'])
    else: ent['U:%d'%len(ent)]=dict(S={p['src']},bbq=p['bbq'],name=p['name'],addr=p['addr'],la=p['la'],lo=p['lo'],names=[p['name']])
E=list(ent.values())
for e in E: e['cityLA']=bool(e['la']) and city.contains(Point(e['lo'],e['la']))
print('link methods:',dict(how))
lk=[e for e in E if 'pid' in e]; un=[e for e in E if 'pid' not in e]
print(f"permit-linked {len(lk)} (KBBQ {sum(e['bbq'] for e in lk)}) | unlinked {len(un)} (KBBQ {sum(e['bbq'] for e in un)}) | cityLA share {sum(e['cityLA'] for e in E)}/{len(E)}")
json.dump([{**{k:v for k,v in e.items() if k!='S'},'S':''.join(sorted(e['S']))} for e in E],open('entities2.json','w'))
def cells(sub):
    c=collections.Counter(''.join(str(int(s in e['S'])) for s in 'KOV') for e in sub); return {k:c.get(k,0) for k in ['001','010','011','100','101','110','111']}
for lab,sub in [('KOREAN',E),('KBBQ',[e for e in E if e['bbq']]),('KOREAN cityLA',[e for e in E if e['cityLA']]),('KBBQ cityLA',[e for e in E if e['bbq'] and e['cityLA']])]:
    print(lab, cells(sub), 'linked-only', cells([e for e in sub if 'pid' in e]))
random.seed(11) if 'random' in dir() else None
import random; random.seed(11)
for title,L in [('V-only linked',[e for e in E if ''.join(sorted(e['S']))=='V' and 'pid' in e]),('unlinked',un),('KBBQ not-K',[e for e in E if e['bbq'] and 'K' not in e['S']])]:
    print(f"\n=== AUDIT {title} n={len(L)}")
    for e in random.sample(L,min(40,len(L))): print(('B ' if e['bbq'] else '  ')+' | '.join(dict.fromkeys(e['names']))[:110])
