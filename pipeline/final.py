import json,re,math
src=open('classify.py').read()
exec(src.split("\nkor=[]")[0])   # loads rest, kw, okor, osm_match, tok
cand=json.load(open('kor_candidates.json'))
NOT_KOREAN={'ANI\'S BBQ CHICKEN','CALIFORNIA CHICKEN CAFE','SAM WOO SEAFOOD BBQ REST','THE BOILING CRAB KTOWN','TRIMANA','AMERICAN RANCH & SEAFOOD MKT','ARADO JAPANESE RESTAURANT','FENG MAO','KOREATOWN GALLERIA DISH ROOM','NINE SEAFOOD','TERIYAKI ME !','KOREAN AIR/ SKYTEAM LOUNGE','BREAD PAPA\'S K-TOWN','EMC SEAFOOD & RAW BAR','MAGALY\'S TAMALES','KTOWN PHO KOBE','CHICKEN MAISON','BITES AND BASHES','OTTO KITCHEN','M PIZZA','H MART KTOWN PLAZA LLC','LOVE LETTER PIZZA & CHICKEN','BURGER CITY GRILL #4','BOO\'S PHILLY CHEESESTEAKS KTOWN','YI PIN CHUAN','KOREA TOWN SENIOR COMMUNITY CENTER','DAVE\'S HOT CHICKEN','SUNRIGHT TEA STUDIO K-TOWN','LEGEND HOT CHICKEN','SMOKING TIGER SAN GABRIEL','MOCHINUT K-TOWN','YAMA SUSHI MARKETPLACE -KTOWN','KTOWN KABAB AND GRILL','SPICY STAR','FAT TOMATO PIZZA (KTOWN)','FRESH DAILY PHO','MULBERRY LA LLC','KOREATOWN PLAZA- FOOD COURT TRAY WASHING AREA','SUGO PV','ODD ONE OUT TEA KOREATOWN','THEO\'S HOT CHICKEN & WINGS','PHO BYOB KTOWN','KOREAN ICE CO','UBATUBA ACAI KOREATOWN','WOOYOU COMPANY','NOON KOREAN BINGSOO HOUSE','GEBANG SIKDANG'}
NOT_KBBQ_RE=re.compile(r"BB\.?Q CHICKEN|BBQ ?\+ ?RICE|CORNER GRILLE|KOBUNGA|HIBACHI",re.I)
ADD_KBBQ={'GENWA','MUN KOREAN STEAKHOUSE','BAK KUNG','TENRAKU ALL YOU CAN EAT','RED PALACE #2'}
kor=[c for c in cand if c[1] not in NOT_KOREAN]
kb=[c for c in kor if (c[7] and not NOT_KBBQ_RE.search(c[1]+' '+c[2])) or c[1] in ADD_KBBQ]
la=lambda L:[c for c in L if c[4]=='LOS ANGELES']
print(f"VERIFIED  Korean county={len(kor)} cityLA={len(la(kor))} | KBBQ county={len(kb)} cityLA={len(la(kb))}")
json.dump({'korean':kor,'kbbq':kb},open('verified.json','w'))
# ---- capture-recapture: sample A = keyword-only flag, sample B = OSM korean tag matched to a permit
ids_kor={c[0] for c in kor}; ids_kb={c[0] for c in kb}
A_k={c[0] for c in kor if kw.search(c[1]+' | '+c[2])}
B_k={c[0] for c in kor if c[8]}
M=len(A_k&B_k); N=len(A_k)*len(B_k)/M
print(f"Korean  A(keyword)={len(A_k)} B(OSM)={len(B_k)} both={M} -> Lincoln-Petersen N≈{N:.0f}")
BBQ=re.compile(re.search(r"BBQ=re.compile\(r'(.*?)'",src).group(1),re.I)
A_b={c[0] for c in kb if BBQ.search(c[1]+' '+c[2]) and kw.search(c[1]+' | '+c[2])}
B_b={c[0] for c in kb if c[8]}
Mb=len(A_b&B_b); Nb=len(A_b)*len(B_b)/Mb
print(f"KBBQ    A={len(A_b)} B={len(B_b)} both={Mb} -> N≈{Nb:.0f}")
# Chapman estimator + 95% CI
def chap(n1,n2,m):
    N=(n1+1)*(n2+1)/(m+1)-1; v=(n1+1)*(n2+1)*(n1-m)*(n2-m)/((m+1)**2*(m+2)); return N,N-1.96*v**.5,N+1.96*v**.5
print('Korean Chapman',[round(x) for x in chap(len(A_k),len(B_k),M)])
print('KBBQ   Chapman',[round(x) for x in chap(len(A_b),len(B_b),Mb)])
