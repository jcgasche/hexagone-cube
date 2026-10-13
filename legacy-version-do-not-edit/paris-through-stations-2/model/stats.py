import csv, json, statistics as S, collections
from model import HS_PAX, TRAIN_DELTA
rows=list(csv.DictReader(open('points.csv')))
tot=sum(HS_PAX.values()); W={k:v/tot for k,v in HS_PAX.items()}
SC={'A':'t_Pleyel','B':'t_Pleyel_2031','C':'t_Pleyel_prog'}
for r in rows:
    for k in list(r):
        if k.startswith('t_'): r[k]=float(r[k])
    r['arr']=int(float(r['arr']))
    r['today']=sum(W[k]*r['t_'+k] for k in W)
    r['nearest']=min(r['t_'+k] for k in W)
    for s,c in SC.items():
        r['d'+s]=r[c]-r['today']
def q(v,p):
    v=sorted(v); i=(len(v)-1)*p; lo=int(i); hi=min(lo+1,len(v)-1); return v[lo]+(v[hi]-v[lo])*(i-lo)
out={'weights':W,'train_delta':TRAIN_DELTA,'train_delta_weighted':sum(W[k]*TRAIN_DELTA[k] for k in W)}
n=len(rows)
def desc(v): return {'mean':S.mean(v),'median':S.median(v),'p10':q(v,.1),'p90':q(v,.9),'min':min(v),'max':max(v)}
out['today']=desc([r['today'] for r in rows]); out['nearest']=desc([r['nearest'] for r in rows])
for k in W: out['t_'+k]=desc([r['t_'+k] for r in rows])
for s,c in SC.items():
    out['hub_'+s]=desc([r[c] for r in rows]); out['delta_'+s]=desc([r['d'+s] for r in rows])
    out['share_faster_'+s]=sum(r['d'+s]<0 for r in rows)/n
    out['share_within5_'+s]=sum(r['d'+s]<=5 for r in rows)/n
    out['share_over10_'+s]=sum(r['d'+s]>10 for r in rows)/n
    out['share_over15_'+s]=sum(r['d'+s]>15 for r in rows)/n
    out['by_dir_'+s]={k:{'today':S.mean([r['t_'+k] for r in rows]),'diff':S.mean([r[c]-r['t_'+k] for r in rows]),
                         'faster':sum(r[c]<r['t_'+k] for r in rows)/n} for k in W}
    out['cum_'+s]={t:sum(r[c]<=t for r in rows)/n for t in (20,30,40,45)}
out['cum_today']={t:sum(r['today']<=t for r in rows)/n for t in (20,30,40,45)}
out['share_faster_nearest_B']=sum(r['t_Pleyel_2031']<r['nearest'] for r in rows)/n
pop={}
g=json.load(open('/home/claude/data/boundaries/paris_arrondissements_from_communescore.geojson'))
for f in g['features']:
    p=f['properties']; pop[int(str(p['code_insee'])[-2:])]=p['population']
by=collections.defaultdict(list)
for r in rows: by[r['arr']].append(r)
out['arr']={}; acc=collections.Counter(); tw=0
for a in sorted(by):
    v=by[a]; m=lambda k: S.mean([x[k] for x in v])
    out['arr'][a]={'n':len(v),'pop':pop[a],'today':m('today'),'A':m('t_Pleyel'),'B':m('t_Pleyel_2031'),'C':m('t_Pleyel_prog'),'dA':m('dA'),'dB':m('dB'),'dC':m('dC')}
    for k in ('today','dA','dB','dC'): acc[k]+=pop[a]*m(k)
    tw+=pop[a]
out['pop_weighted']={k:v/tw for k,v in acc.items()}
json.dump(out,open('stats.json','w'),indent=1)
json.dump(rows,open('points_stats.json','w'))
def f(x): return round(x,2) if isinstance(x,float) else x
for k in ['weights','train_delta_weighted','today','nearest','hub_A','hub_B','hub_C','delta_A','delta_B','delta_C','share_faster_A','share_faster_B','share_faster_C','share_within5_B','share_over10_B','share_over15_B','by_dir_B','by_dir_C','cum_today','cum_B','cum_C','share_faster_nearest_B','pop_weighted']:
    v=out[k]; print(k, {a:(f(b) if not isinstance(b,dict) else {c:f(d) for c,d in b.items()}) for a,b in v.items()} if isinstance(v,dict) else f(v))
for a,v in out['arr'].items(): print(a, v['n'], v['pop'], *(round(v[k],1) for k in ('today','A','B','C','dA','dB','dC')))
