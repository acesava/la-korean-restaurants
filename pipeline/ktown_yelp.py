"""Step 8: Reconcile with a Yelp scrape of 'Korean BBQ near Koreatown, Los Angeles' (2026-09-14; yelp/ folder)
and add Yelp as a 4th source for the Koreatown KBBQ estimate.

Matching is hand-specified (regex per Yelp listing -> pipeline entity), one-to-one, because automatic fuzzy matching
paired e.g. "Park's BBQ" with "8 Korean BBQ Buena Park". A Yelp listing whose pipeline entity is already claimed by
another Yelp listing (several restaurants merged under one permit address) counts as a separate restaurant.
"""
import json, re, math, itertools, warnings
import pandas as pd, statsmodels.api as sm
from shapely.geometry import shape, Point
warnings.filterwarnings('ignore')
poly = shape(json.load(open('ktown_latimes.geojson'))['features'][0]['geometry'])
E = json.load(open('entities2.json'))
KT = (34.0617, -118.3004)
def km(e): return math.hypot((e['la']-KT[0])*111, (e['lo']-KT[1])*92.4) if e['la'] else 99

rows = []
for line in open('yelp/yelp-kbbq-koreatown-2026-09-14.md'):
    m = re.match(r'\|\s*(\d+)\s*\|\s*\d+\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(yes|no)\s*\|', line)
    if m: rows.append(dict(name=m[2], label=m[3], kb=m[5] == 'yes'))
DROP = {'BCD Tofu House', 'Jinsol Gukbap - 3rd St', 'The Corner Place Resta', 'Yuchun'}  # soup/tofu/noodle houses carrying a Barbeque pill
ADD = {'K Team BBQ', 'Daedo Sikdang'}                                                   # KBBQ tagged only 'Korean' on Yelp
yk = [r for r in rows if ((r['kb'] and r['name'] not in DROP) or r['name'] in ADD) and '(dup)' not in r['name']]

MAP = {  # Yelp listing -> regex over pipeline entity names (None = not in pipeline)
 'Soowon Galbi KBBQ Rest': r'SOO ?WON GALBI', 'Gangnam Station': r'GANGNAM STATION', 'Hae Jang Chon': r'HAE JANG CHON',
 'Hanu Korean BBQ': r'HANU KOREAN', 'Moohan Korean BBQ': r'MOOHAN', 'BBQ Chung Dam': r'BBQ CHUNG ?DAM', 'TEN BBQ': r'TEN-?BBQ|TEN BBQ',
 'Ahgassi Gopchang': r'AHGASSI', 'Pigya': r'PIGYA', 'King Chang - LA': r'KING ?CHANG', 'Quarters Korean BBQ': r'QUARTERS',
 'Woo Hyang Woo': r'WOO HYANG WOO', 'JJUKKU JJUKKU BBQ': r'JJUKKU', 'MUN Korean Steakhouse': r'MUN KOREAN STEAK',
 'Bulgogi Hut': r'BULGOGI HUT', 'Origin Korean BBQ': r'ORIGIN KOREAN', 'Mountain San BBQ': r'MOUNTAIN SAN',
 'Baekjeong - Los Angele': r'BAEKJEONG LOS ANGELES|BAEKJEONG L', "Park's BBQ": r"PARK'?S BBQ", 'Jeong Yuk Jeom': r'정육점|JEONG ?YUK',
 'Road to Seoul': r'ROAD TO SEOUL BBQ VERMONT', 'Brothers BBQ': r'BROTHERS KOREAN BBQ', 'Sookdal': r'SOOKDAL',
 'Jin Ju Korean BBQ': r'JIN ?JU (KBBQ|GALBI)', 'Dae Sung Ro Korean BBQ': r'DAE SUNG RO', 'Yangmani': r'YANGMANI',
 'Gabin Korean Grill': r'GABIN', 'Soot Bull Jip': r'SOOT ?BULL', 'Seogwan by Yellowcow K': r'SEOGWAN', 'TGI Korean BBQ': r'TGI KOREAN',
 'BBQ All You Can Eat': r'BBQ ALL YOU CAN EAT', 'Hwayeon Korean BBQ Res': r'HWAYEON', 'Chosun Galbee': r'CHOSUN GALBEE',
 '7th Korean BBQ': r'7TH KOREAN', 'Byul Gobchang': r'BEUL GOPCHANG|BYUL GOBCHANG', 'Wi Korean BBQ': r'WI KOREAN BBQ',
 'K Team BBQ': r'K-?TEAM', 'Moodaepo': r'MOO ?DAE ?PO', 'Kkondae K Bbq': r'KKONDAE', 'Yerim Korean BBQ': r'YERIM',
 'Ham Ji Park': r'HAM ?JI ?PARK', 'Seoul Soul BBQ': r'SEOUL SOUL', 'STE 101': r'STE ?101', 'Michin Dwaeji Galbi -': r'MICHIN',
 'Oo-Kook Korean BBQ': r'OO ?-?KOOK', 'Daedo Sikdang': r'DAEDO', 'Genwa Korean BBQ Mid W': r'GENWA', 'BBQ Garden': r'BBQ GARDEN',
 'BBQ All You Can Eat 2': r'BBQ ALL YOU CAN EAT 2', 'Castle BBQ': r'CASTLE BBQ', 'Mun Patio': r'MUN PATIO', 'Bud Namu Korean BBQ': r'BUD ?NAMU',
 'Meat Love Korean BBQ': r'MEAT LOVE', 'Bak Kung Korean BBQ': r'BAK KUNG', 'PZK Bbq': r'PZK', 'Chung Ki Wa': r'CHUNG ?KI ?WA',
 'Moon BBQ 2': r'#2 MOON|MOON BBQ NUMBER 2', 'Genwa Korean BBQ Los A': r'GENWA', 'MJD Korean BBQ': r'MJD',
 'Hwang Hae Do Korean BB': r'HWANG HAE DO', "Burnin' Shell": r'BURNING SHELL', 'J BBQ': r'\bJ ?BBQ\b',
}
claimed = set(); res = {'agree': [], 'found-not-flagged': [], 'colocated (hidden in merged record)': [], 'missing': []}
for r in yk:
    rx = re.compile(MAP[r['name']], re.I)
    hits = sorted((km(e), i) for i, e in enumerate(E) if any(rx.search(n) for n in e['names']))
    free = [(d, i) for d, i in hits if i not in claimed and d < 12]
    if free:
        i = free[0][1]; claimed.add(i); e = E[i]; e['Y'] = True
        res['agree' if e['bbq'] else 'found-not-flagged'].append(f"{r['name']} -> {e['name'][:40]}")
        e['bbq'] = True; r['inside'] = poly.contains(Point(e['lo'], e['la']))
    else:
        key = 'colocated (hidden in merged record)' if hits else 'missing'
        res[key].append(f"{r['name']} [{r['label']}]"); r['new'] = True
        r['inside'] = r['label'] in ('Koreatown', 'Wilshire Cen', '?')
print(f"Yelp judged KBBQ: {len(yk)} (Koreatown / Wilshire Center / unlabeled: {sum(r['label'] in ('Koreatown','Wilshire Cen','?') for r in yk)})")
for k, v in res.items():
    print(f"\n{k}: {len(v)}"); [print('   ', x) for x in v]

# 4-source estimate (K, O, V, Y) for KBBQ inside the LA Times boundary
def w(e):
    if 'K' in e['S'] or e.get('Y'): return 1.0
    return 0.72 if 'pid' in e else 0.60
sub = [dict(S=set(e['S']) | ({'Y'} if e.get('Y') else set()), w=w(e)) for e in E
       if e['la'] and e['bbq'] and poly.contains(Point(e['lo'], e['la']))]
sub += [dict(S={'Y'}, w=1.0) for r in yk if r.get('new') and r['inside']]
yin = sum(1 for r in yk if r['inside'])
print(f"\nKBBQ inside LA Times Koreatown: seen {len(sub)} (Yelp listings inside: {yin}); precision-adjusted {sum(s['w'] for s in sub):.0f}")
src = 'KOVY'
cells = {c: 0.0 for c in itertools.product((0, 1), repeat=4) if any(c)}
for s in sub: cells[tuple(int(x in s['S']) for x in src)] += s['w']
df = pd.DataFrame([list(c) + [n] for c, n in cells.items()], columns=list(src) + ['n'])
for a, b in itertools.combinations(src, 2): df[a+b] = df[a]*df[b]
obs = df.n.sum(); out = []
for extra in [[]] + [[p] for p in ['KO','KV','KY','OV','OY','VY']] + [['KO','KV'], ['KO','OV'], ['KO','KY'], ['KV','OV'], ['KY','VY'], ['OV','VY'], ['KO','VY']]:
    try:
        f = sm.GLM(df.n, sm.add_constant(df[list(src) + extra].astype(float)), family=sm.families.Poisson()).fit()
        n = obs + math.exp(f.params['const'])
        if math.isfinite(n) and n <= 3*obs: out.append((f.aic, n, '+'.join(extra) or 'indep'))
    except Exception: pass
out.sort(); m0 = out[0][0]; ws = [math.exp(-(a - m0)/2) for a, _, _ in out]
avg = sum(wi*n for wi, (_, n, _) in zip(ws, out))/sum(ws)
print(f"4-source KBBQ estimate, LA Times Koreatown: ≈{avg:.0f} (best {out[0][2]} ≈{out[0][1]:.0f}; models {min(n for _, n, _ in out):.0f}–{max(n for _, n, _ in out):.0f})")
print("cells K O V Y:", {''.join(map(str, c)): round(n, 1) for c, n in cells.items() if n})
json.dump(dict(ktown_kbbq_4source=round(avg), observed=round(obs), yelp_inside=yin), open('ktown_yelp_estimate.json', 'w'))
