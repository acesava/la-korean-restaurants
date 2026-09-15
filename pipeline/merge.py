import json,re,math,csv,difflib,collections,itertools
import duckdb, numpy as np, pandas as pd, statsmodels.api as sm
from shapely.geometry import shape, Point
from shapely.prepared import prep
src=open('classify.py').read(); exec(src.split("\nkor=[]")[0])       # rest, kw
county=prep(shape(json.load(open('lacounty.geojson'))['features'][0]['geometry']))
v=json.load(open('verified.json')); VK={c[0] for c in v['korean']}; VB={c[0] for c in v['kbbq']}
OWN_HD=re.compile(r'^(LONG BEACH|SIGNAL HILL_X|PASADENA|VERNON)$')
def own_hd(city,zip5):
    z=(zip5 or '')[:5]
    return z.startswith('908') or z in {'91101','91103','91104','91105','91106','91107','91125','91126','90058'} or bool(OWN_HD.match((city or '').upper()))
SUF=r'\b(ST|STREET|AVE|AVENUE|BLVD|BOULEVARD|DR|DRIVE|RD|ROAD|WAY|PL|PLACE|LN|LANE|CT|PKWY|HWY|HIGHWAY|CIR|TER|PLZ|PLAZA)\b'
def akey(addr,zip5=''):
    a=re.sub(r'(,|\b(STE|SUITE|UNIT|APT|#|FL|SPC|BLDG)\b.*$|#.*$)','',(addr or '').upper()).strip()
    m=re.match(r'^(\d+)[A-Z-]*\s+(.*)$',a)
    if not m: return None
    st=re.sub(r'^(N|S|E|W|NORTH|SOUTH|EAST|WEST)\s+','',m.group(2)); st=re.sub(SUF,'',st)
    st=re.sub(r'\b(\d+)(ST|ND|RD|TH)\b',r'\1',st).split()
    return (m.group(1), st[0] if st else '')
STOP={'THE','AND','RESTAURANT','KOREAN','BBQ','INC','LLC','HOUSE','CAFE','CORP','LA','LOS','ANGELES','OF','KITCHEN','GRILL','K','CO','&'}
def toks(s): return set(w for w in re.findall(r'[A-Z0-9]+',(s or '').upper()) if len(w)>1 and w not in STOP)
def nsim(a,b):
    ta,tb=toks(a),toks(b)
    j=len(ta&tb)/max(1,min(len(ta),len(tb))) if ta and tb else 0
    r=difflib.SequenceMatcher(None,re.sub(r'[^A-Z0-9]','',(a or '').upper()),re.sub(r'[^A-Z0-9]','',(b or '').upper())).ratio()
    return max(j,r)
# permit index
P={}; byaddr=collections.defaultdict(list); grid=collections.defaultdict(list)
for r in rest:
    try: la,lo=float(r['FACILITY LATITUDE']),float(r['FACILITY LONGITUDE'])
    except: la=lo=None
    p=dict(id=r['FACILITY ID'],name=r['FACILITY NAME']+' / '+r['PROGRAM NAME'],addr=r['FACILITY ADDRESS'],city=r['FACILITY CITY'],zip=r['FACILITY ZIP'][:5],owner=r['OWNER NAME'],la=la,lo=lo)
    P[p['id']]=p; k=akey(p['addr'])
    if k: byaddr[k].append(p['id'])
    if la: grid[(round(la,3),round(lo,3))].append(p['id'])
def dist(a,b,c,d): return math.hypot((a-c)*111000,(b-d)*92400)
def near(la,lo,R):
    out=[]
    for dx in (-1,0,1):
        for dy in (-1,0,1):
            for pid in grid.get((round(la,3)+dx*0.001,round(lo,3)+dy*0.001),[]):
                p=P[pid]; d=dist(la,lo,p['la'],p['lo'])
                if d<=R: out.append((d,pid))
    return sorted(out)
def link(name,addr,zip5,la,lo):
    k=akey(addr,zip5); same=[pid for pid in byaddr.get(k,[]) if not zip5 or P[pid]['zip']==zip5[:5]] if k else []
    nb=near(la,lo,120)
    cands=set(same)|{pid for d,pid in nb}
    best=max(((nsim(name,P[pid]['name']),pid) for pid in cands),default=(0,None))
    if best[0]>=0.6: return best[1],'name'
    if len(same)==1: return same[0],'addr-only'
    close=[pid for d,pid in nb if d<=30]
    if len(close)==1 and not same: return close[0],'geo-only'
    return None,None
# ---- load POIs
pois=[]
for e in json.load(open('osm.json'))['elements']:
    t=e['tags']; c=t.get('cuisine','').lower(); n=t.get('name','')
    if 'korean' not in c: continue
    la=e.get('lat') or e['center']['lat']; lo=e.get('lon') or e['center']['lon']
    addr=(t.get('addr:housenumber','')+' '+t.get('addr:street','')).strip()
    pois.append(dict(src='O',name=n,addr=addr,zip=t.get('addr:postcode','')[:5],city=t.get('addr:city',''),la=la,lo=lo,bbq=('barbecue' in c or 'bbq' in c or bool(re.search(r'bbq|barbe|galbi|kalbi|gogi',n,re.I)))))
ov=duckdb.sql("""select * from 'overture_la.parquet' where (cat='korean_restaurant' or (list_contains(alt,'korean_restaurant') and (cat like '%restaurant%' or cat in ('bar','pub','buffet_restaurant'))))
                 and coalesce(operating_status,'open')<>'permanently_closed' and confidence>=0.5""").df()
S_=lambda x: x if isinstance(x,str) else ''
for r in ov.itertuples():
    alt=list(r.alt) if hasattr(r.alt,"__len__") and not isinstance(r.alt,str) else []
    pois.append(dict(src='V',name=S_(r.name),addr=S_(r.addr),zip=S_(r.zip)[:5],city=S_(r.city),la=r.lat,lo=r.lon,conf=r.confidence,
                     bbq=(r.cat=='barbecue_restaurant' or 'barbecue_restaurant' in alt or bool(re.search(r'bbq|barbe|galbi|kalbi|gogi',S_(r.name),re.I)))))
pois=[p for p in pois if county.contains(Point(p['lo'],p['la']))]
print('POIs in LA County: OSM',sum(p['src']=='O' for p in pois),' Overture',sum(p['src']=='V' for p in pois))
hd=[p for p in pois if own_hd(p['city'],p['zip'])]; pois=[p for p in pois if not own_hd(p['city'],p['zip'])]
print('  in Pasadena/Long Beach/Vernon (separate health depts):',collections.Counter(p['src'] for p in hd))
# ---- build entities
ent={}   # key -> dict(srcs set, bbq flag, name)
how=collections.Counter()
for pid in VK: ent['P:'+pid]=dict(S={'K'},bbq=pid in VB,name=P[pid]['name'],addr=P[pid]['addr'],pid=pid)
unl=[]
for p in pois:
    pid,m=link(p['name'],p['addr'],p['zip'],p['la'],p['lo']); how[(p['src'],m)]+=1
    if pid:
        e=ent.setdefault('P:'+pid,dict(S=set(),bbq=False,name=P[pid]['name'],addr=P[pid]['addr'],pid=pid)); e['S'].add(p['src']); e['bbq']|=p['bbq']; e.setdefault('pois',[]).append(p['name'])
    else: unl.append(p)
# dedupe unlinked POIs among themselves
for p in unl:
    hit=None
    for k,e in ent.items():
        if k.startswith('U:') and dist(p['la'],p['lo'],e['la'],e['lo'])<100 and nsim(p['name'],e['name'])>=0.6: hit=e;break
    if hit: hit['S'].add(p['src']); hit['bbq']|=p['bbq']
    else: ent['U:%d'%len(ent)]=dict(S={p['src']},bbq=p['bbq'],name=p['name'],addr=p['addr'],la=p['la'],lo=p['lo'])
print('link methods:',dict(how))
E=list(ent.values())
linked=[e for e in E if 'pid' in e]; un=[e for e in E if 'pid' not in e]
print(f"entities: permit-linked {len(linked)} (KBBQ {sum(e['bbq'] for e in linked)}), unlinked POIs {len(un)} (KBBQ {sum(e['bbq'] for e in un)})")
json.dump([{**{k:v for k,v in e.items() if k!='S'},'S':''.join(sorted(e['S']))} for e in E],open('entities.json','w'))
# ---- 3-source log-linear capture-recapture
def loglinear(sub,label):
    cnt=collections.Counter(tuple(int(s in e['S']) for s in 'KOV') for e in sub)
    rows=[(a,b,c,cnt.get((a,b,c),0)) for a,b,c in itertools.product((0,1),repeat=3) if (a,b,c)!=(0,0,0)]
    df=pd.DataFrame(rows,columns=['K','O','V','n'])
    print(f"\n{label}: cells", {f"{a}{b}{c}":n for a,b,c,n in rows}, 'observed',df.n.sum())
    forms={'indep':['K','O','V'],'K*O':['K','O','V','KO'],'K*V':['K','O','V','KV'],'O*V':['K','O','V','OV'],'KO+KV':['K','O','V','KO','KV'],'KO+OV':['K','O','V','KO','OV'],'KV+OV':['K','O','V','KV','OV']}
    df['KO']=df.K*df.O; df['KV']=df.K*df.V; df['OV']=df.O*df.V
    res=[]
    for nm,cols in forms.items():
        X=sm.add_constant(df[cols].astype(float)); f=sm.GLM(df.n,X,family=sm.families.Poisson()).fit()
        n0=math.exp(f.params['const']); se=f.bse['const']
        lo_,hi_=df.n.sum()+n0*math.exp(-1.96*se), df.n.sum()+n0*math.exp(1.96*se)
        res.append((f.aic,nm,df.n.sum()+n0,lo_,hi_))
    for a,nm,N,l,h in sorted(res): print(f"   {nm:7} AIC={a:6.1f}  N≈{N:5.0f}  95% CI {l:.0f}–{h:.0f}")
    return sorted(res)
rk=loglinear(E,'KOREAN (all entities)')
rb=loglinear([e for e in E if e['bbq']],'KBBQ')
rkl=loglinear(linked,'KOREAN (permit-linked only)')
rbl=loglinear([e for e in linked if e['bbq']],'KBBQ (permit-linked only)')
