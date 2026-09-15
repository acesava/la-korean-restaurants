import json,re,collections
src=open('classify.py').read(); exec(src.split("\nkor=[]")[0])
v=json.load(open('verified.json')); kid={c[0] for c in v['korean']}; bid={c[0] for c in v['kbbq']}
KT={'90004','90005','90006','90010','90019','90020','90057'}
SUR=r"KIM|LEE|PARK|CHOI|CHOE|JUNG|JEONG|CHUNG|KANG|CHO|JO|YOON|YUN|JANG|LIM|HAN|OH|SEO|SUH|SHIN|KWON|HWANG|AHN|AN|SONG|YOO|YU|HONG|JEON|JUN|CHUN|KO|GO|MOON|YANG|SON|BAE|BAEK|PAIK|HEO|HUH|NAM|SIM|SHIM|NOH|ROH|HA|KWAK|SUNG|CHA|JOO|JU|WOO|KOO|KU|MIN|RYU|YOO|NA|JIN|UM|EOM|CHAE|WON|BANG|KONG|HYUN|PYO|TAK|MYUNG|BYUN|YEO|GIL|LA|DO|SUK|KWAK|KOH"
surre=re.compile(r'\b(?:'+SUR+r')\b')
ktz=[r for r in rest if r['FACILITY ZIP'][:5] in KT]
own=[r for r in ktz if surre.search(r['OWNER NAME'])]
fl=[r for r in ktz if r['FACILITY ID'] in kid]
print('Ktown-ZIP restaurant permits:',len(ktz),' Korean-surname owner:',len(own),' our verified Korean:',len(fl))
print('  verified Korean with Korean-surname owner:',sum(1 for r in fl if surre.search(r['OWNER NAME'])),'of',len(fl))
# unflagged korean-surname-owner sample to eyeball
import random; random.seed(1)
un=[r for r in own if r['FACILITY ID'] not in kid]
for r in random.sample(un,min(40,len(un))): print('   ?',r['FACILITY NAME'],'|',r['OWNER NAME'])
# countywide surname-owner counts
allown=[r for r in rest if surre.search(r['OWNER NAME'])]
print('County permits w/ Korean-surname owner token:',len(allown),'(upper bound-ish; LEE/HAN/CHANG overlap Chinese)')
# city-level Chapman
