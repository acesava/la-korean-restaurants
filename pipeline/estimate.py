import json,itertools,math,warnings; import pandas as pd, statsmodels.api as sm
warnings.filterwarnings('ignore')
E=json.load(open('entities2.json'))
# audited precision by group
def w(e,bbq):
    if 'K' in e['S']: return 1.0
    linked='pid' in e
    if bbq: return (0.72 if linked else 0.60)
    if linked: return 0.80 if e['S']=='V' else 0.90
    return 0.55 if e['S'] in ('V','O') else 0.70
def fit(sub,bbq,label):
    c={k:0.0 for k in ['001','010','011','100','101','110','111']}
    for e in sub: c[''.join(str(int(s in e['S'])) for s in 'KOV')]+=w(e,bbq)
    df=pd.DataFrame([(int(k[0]),int(k[1]),int(k[2]),v) for k,v in c.items()],columns=['K','O','V','n'])
    df['KO']=df.K*df.O; df['KV']=df.K*df.V; df['OV']=df.O*df.V
    obs=df.n.sum(); out=[]
    for nm,cols in {'indep':['K','O','V'],'K*O':['K','O','V','KO'],'K*V':['K','O','V','KV'],'O*V':['K','O','V','OV'],'KO+KV':['K','O','V','KO','KV'],'KO+OV':['K','O','V','KO','OV'],'KV+OV':['K','O','V','KV','OV']}.items():
        f=sm.GLM(df.n,sm.add_constant(df[cols].astype(float)),family=sm.families.Poisson()).fit()
        m0=math.exp(f.params['const']); se=f.bse['const']
        out.append((f.aic,nm,obs+m0,obs+m0*math.exp(-1.96*se),obs+m0*math.exp(1.96*se)))
    out.sort(); best=out[0]; minA=best[0]
    # AIC-weighted model average
    ws=[math.exp(-(a-minA)/2) for a,*_ in out]; avg=sum(wi*o[2] for wi,o in zip(ws,out))/sum(ws)
    print(f"{label:22} observed(precision-adj)={obs:6.0f}  best={best[1]} N≈{best[2]:.0f} [{best[3]:.0f}–{best[4]:.0f}]  AIC-avg N≈{avg:.0f}  models range {min(o[2] for o in out):.0f}–{max(o[2] for o in out):.0f}")
    return obs,avg
r={}
r['k']=fit(E,False,'Korean — county*')
r['b']=fit([e for e in E if e['bbq']],True,'KBBQ — county*')
r['kc']=fit([e for e in E if e['cityLA']],False,'Korean — City of LA')
r['bc']=fit([e for e in E if e['bbq'] and e['cityLA']],True,'KBBQ — City of LA')
print('* county figures exclude Pasadena/Long Beach/Vernon; map data there: ~13 Korean incl ~4 KBBQ observed')
json.dump(r,open('estimates.json','w'))
