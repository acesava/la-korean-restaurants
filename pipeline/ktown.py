"""Step 7: Koreatown subset — counts inside (a) LA Times Mapping L.A. boundary, (b) 2010 LA City Council designation (approximated)."""
import json, math, itertools, warnings, csv
import pandas as pd, statsmodels.api as sm
from shapely.geometry import shape, Point, box
from shapely.ops import unary_union
warnings.filterwarnings('ignore')
latimes = shape(json.load(open('ktown_latimes.geojson'))['features'][0]['geometry'])
# Council 2010: Vermont (E) / Western (W) / 3rd St (N) / Olympic (S) + Western Ave corridor north to Rosewood Ave.
council = unary_union([box(-118.3093, 34.0520, -118.2915, 34.0692), box(-118.3100, 34.0692, -118.3080, 34.0777)])
E = json.load(open('entities2.json'))
def w(e, bbq):
    if 'K' in e['S']: return 1.0
    linked = 'pid' in e
    if bbq: return 0.72 if linked else 0.60
    if linked: return 0.80 if e['S'] == 'V' else 0.90
    return 0.55 if e['S'] in ('V', 'O') else 0.70
def est(sub, bbq):
    c = {k: 0.0 for k in ['001', '010', '011', '100', '101', '110', '111']}
    for e in sub: c[''.join(str(int(s in e['S'])) for s in 'KOV')] += w(e, bbq)
    df = pd.DataFrame([(int(k[0]), int(k[1]), int(k[2]), v) for k, v in c.items()], columns=['K', 'O', 'V', 'n'])
    df['KO'] = df.K*df.O; df['KV'] = df.K*df.V; df['OV'] = df.O*df.V
    obs = df.n.sum(); out = []
    for cols in [['K','O','V'], ['K','O','V','KO'], ['K','O','V','KV'], ['K','O','V','OV'], ['K','O','V','KO','KV'], ['K','O','V','KO','OV'], ['K','O','V','KV','OV']]:
        try:
            f = sm.GLM(df.n, sm.add_constant(df[cols].astype(float)), family=sm.families.Poisson()).fit()
            n = obs + math.exp(f.params['const'])
            if math.isfinite(n) and n <= 3*obs: out.append((f.aic, n))   # drop degenerate fits (empty cells in small subsets)
        except Exception: pass
    m = min(a for a, _ in out); ws = [math.exp(-(a - m)/2) for a, _ in out]
    return obs, sum(wi*n for wi, (_, n) in zip(ws, out))/sum(ws), min(n for _, n in out), max(n for _, n in out)
perm = [r for r in csv.DictReader(open('county_inv.csv', encoding='cp1252', errors='replace'))]
perm = {r['FACILITY ID']: r for r in perm if r['PE DESCRIPTION'].startswith('RESTAURANT')}
for label, poly in [('LA Times Mapping L.A. Koreatown', latimes), ('2010 City Council Koreatown (approx.)', council)]:
    inside = lambda la, lo: la is not None and poly.contains(Point(lo, la))
    npermit = sum(1 for r in perm.values() if r['FACILITY LATITUDE'] and inside(float(r['FACILITY LATITUDE']), float(r['FACILITY LONGITUDE'])))
    sub = [e for e in E if inside(e['la'], e['lo'])]
    k = est(sub, False); b = est([e for e in sub if e['bbq']], True)
    km2 = poly.area * (111.0 * 92.4)
    print(f"\n{label}  (~{km2/2.59:.1f} sq mi)")
    print(f"  all restaurant permits: {npermit}")
    print(f"  Korean: seen {len(sub)} | precision-adj {k[0]:.0f} | estimate ≈{k[1]:.0f} (models {k[2]:.0f}–{k[3]:.0f}) | share of permits ≈{k[1]/npermit:.0%}")
    print(f"  KBBQ:   seen {sum(e['bbq'] for e in sub)} | precision-adj {b[0]:.0f} | estimate ≈{b[1]:.0f} (models {b[2]:.0f}–{b[3]:.0f}) | ≈{b[1]/k[1]:.0%} of Korean")
