import csv,json,re,math,collections
rows=[r for r in csv.DictReader(open('county_inv.csv',encoding='cp1252',errors='replace'))]
rows=[{k.strip():v for k,v in r.items()} for r in rows]
rest=[r for r in rows if r['PE DESCRIPTION'].startswith('RESTAURANT')]
# dedupe by facility id
seen={};
for r in rest: seen[r['FACILITY ID']]=r
rest=list(seen.values())
print('county restaurant permits (unique facilities):',len(rest))
print('  in FACILITY CITY=LOS ANGELES:',sum(r['FACILITY CITY']=='LOS ANGELES' for r in rest))
KW=r"KOREA|SEOUL|BUSAN|K[- ]?BBQ|K[- ]?TOWN|GOGI|GALBI|GALBEE|KALBI|BULGOGI|BULGOKI|SOON ?DU?BU|SUNDUBU|TOFU HOUSE|JJIGAE|CHIGAE|POCHA|BIBIMBAP|BIBIMBOP|KIMCHI|KIMBAP|GIMBAP|TTEOK|DUKBOKKI|TTEOKBOKKI|YUPDDUK|NAENGMYUN|NAENG MYUN|MANDOO|GUKBAP|GUKSU|SAMGYEOP|JOKBAL|GOPCHANG|DAKGALBI|SIKDANG|BAEKJEONG|HAN ?JIP|HANJIP|HANSIK|GANGNAM|MYUNG ?DONG|MYEONGDONG|JEJU|ITAEWON|SINCHON|APGUJEONG|CHUNG ?DAM|HODORI|DONG ?IL ?JANG|SOOT BULL|CHOSUN|CHO SUN|HAE JANG|HAM JI|KANG HO ?DONG|GEN KOREAN|OO-?KOOK|JJUKKU|SUN HA JANG|ONG GA NAE|SOOWON|GWANG YANG|MAGAL|AHGASSI|DAEDO|YOUNG ?DONG|HANOO|BCD TOFU|BEE HIVE|KYOCHON|BONCHON|PELICANA|BB\.?Q CHICKEN|CHICKEN PLUS|KKANBU|OB BEAR|HANCHAN|JINSOL|SURAH|ARIRANG|KOBAWOO|YANGJI|EMC|SEOLLEUNG|MUN DAE|HANGARI|MAPO|JANGTEO|DAN SUNG SA|NAK WON|HO DORI|OJANGDONG|OKDONGSIK|KOGI"
kw=re.compile(r'\b(?:'+KW+r')',re.I)
# OSM korean points
osm=[e for e in json.load(open('osm.json'))['elements']]
def ll(e): return (e.get('lat') or e['center']['lat'], e.get('lon') or e['center']['lon'])
okor=[]
for e in osm:
    t=e['tags']; 
    if 'korean' in t.get('cuisine','').lower() or re.search(r'korea|seoul|kbbq|gogi|galbi|kalbi|bulgogi|soondubu|sundubu|jjigae|pocha|bibimbap',t.get('name',''),re.I):
        okor.append((ll(e),t.get('name',''),t.get('cuisine','')))
def tok(s): return set(w for w in re.findall(r'[a-z0-9]+',s.lower()) if len(w)>2 and w not in {'the','and','restaurant','korean','bbq','inc','llc','house','cafe'})
def osm_match(r):
    try: la,lo=float(r['FACILITY LATITUDE']),float(r['FACILITY LONGITUDE'])
    except: return None
    for (a,b),n,c in okor:
        d=math.hypot((la-a)*111000,(lo-b)*92000)
        if d<150 and (tok(n)&tok(r['FACILITY NAME']+' '+r['PROGRAM NAME'])): return (n,c)
    return None
kor=[]
for r in rest:
    nm=r['FACILITY NAME']+' | '+r['PROGRAM NAME']
    m=osm_match(r)
    if kw.search(nm) or m: kor.append((r,m))
BBQ=re.compile(r'B\.?B\.?Q|BARBE|GOGI|GALBI|GALBEE|KALBI|GRILL|SAMGYEOP|GOPCHANG|BAEKJEONG|SOOT BULL|HAE JANG|HAM JI|GEN KOREAN|OO-?KOOK|JJUKKU|SUN HA JANG|SOOWON|GWANG YANG|MAGAL|AHGASSI|DAEDO|HANOO|CHOSUN GALBEE|HONEY PIG|KANG HO|YAKINIKU|CHARCOAL|MEAT|BUTCHER|SIKDANG|QUARTERS|MOOHAN|ROAD TO SEOUL',re.I)
json.dump([[r['FACILITY ID'],r['FACILITY NAME'],r['PROGRAM NAME'],r['FACILITY ADDRESS'],r['FACILITY CITY'],r['FACILITY ZIP'],r['PE DESCRIPTION'],bool(BBQ.search(r['FACILITY NAME']+' '+r['PROGRAM NAME']) or (m and 'barbecue' in m[1])),m] for r,m in kor],open('kor_candidates.json','w'),indent=0)
print('korean candidates:',len(kor),' bbq-flagged:',sum(1 for x in json.load(open('kor_candidates.json')) if x[7]))
