"""Port V12 CLOSED. Experimental until parity against TradingView snapshots."""
import math
import numpy as np
import pandas as pd
from core import wilder_atr, _evaluate_compatible, _evaluate_independent, BalanceZone, _normalize_ohlc

PHASES={'EARLY','FRESH','TRANSITION'}

def phase(signal, trend, mem, ha, inv, seq):
    bull=trend==1 and ha==1
    fresh=bull and signal==1 and 0<=mem<3
    return 'FRESH' if fresh else 'EARLY' if bull and inv==1 and seq==1 else 'TRANSITION' if ha==1 and 1<=seq<=2 and trend==-1 else 'MATURE' if bull else 'WAIT'

def timing(data):
    c=data.close
    def wma(x,n):
        w=np.arange(1,n+1)
        return x.rolling(n).apply(lambda a: np.dot(a,w)/w.sum(),raw=True)
    hma=wma(2*wma(c,8)-wma(c,16),4)
    bull=hma>hma.shift(1)
    hc=data[['open','high','low','close']].mean(axis=1).to_numpy()
    ho=np.empty(len(data));ho[0]=(data.open.iloc[0]+c.iloc[0])/2
    for i in range(1,len(data)): ho[i]=(ho[i-1]+hc[i-1])/2
    green=hc>=ho
    rows=[]; lastlong=lastshort=None;lastchange=None; seq=0
    for i in range(len(data)):
        b=bool(bull.iloc[i]); prev=bool(bull.iloc[i-1]) if i else False
        if i and b!=prev:
            lastchange=i
            if b:lastlong=i
            else:lastshort=i
        # Pine barssince comparisons involving na are false until both events exist.
        signal=0
        if lastlong is not None and lastshort is not None:
            if i-lastlong<3 and lastlong>lastshort:signal=1
            elif i-lastshort<3 and lastshort>lastlong:signal=-1
        inv=0
        if i and green[i]!=green[i-1]:seq=1;inv=1 if green[i] else -1
        else:seq=seq+1 if seq else 1
        rows.append(dict(HS=signal,HT=1 if b else -1,MEM=i-lastchange if lastchange is not None else -1,HA=1 if green[i] else -1,INV=inv,SEQ=seq,HMA=hma.iloc[i]))
    return pd.DataFrame(rows,index=data.index)

def auto_half(d,atr,center,discovery,valid,scan,tick):
    l,h,c=d.low.to_numpy(),d.high.to_numpy(),d.close.to_numpy();a=atr.to_numpy();n=len(d)-1
    ds=[];last=None;top= center+discovery;bottom=center-discovery
    for off in range(valid+1,scan):
        j=n-off
        above=c[j-1]>top;below=c[j-1]<bottom
        if not(l[j]<=top and h[j]>=bottom and (above or below) and (last is None or off-last>=6)):continue
        at=max(a[j] if np.isfinite(a[j]) else tick,tick)
        distance=min(abs((l[j] if above else h[j])-center),discovery)
        failed=c[j]<bottom if above else c[j]>top;success=False
        for k in range(1,valid+1):
            if success or failed:break
            q=j+k
            if (c[q]<bottom if above else c[q]>top):failed=True
            elif (h[q]-center if above else center-l[q])>=at*.2:success=True
        if success:ds.append(distance/at)
        last=off
    if len(ds)<3:return discovery
    med=np.median(ds);mad=np.median(np.abs(np.array(ds)-med))
    return max(tick,min(discovery,max(tick,atr.iloc[-1]*(med+1.4826*mad))))

def zones(d,atr,valid,engine,old,tick):
    n=len(d)-1;scan=min(400,n);window=d.iloc[-400:]
    lo=window.low.min();rng=max(window.high.max()-lo,tick*10)
    moves=np.abs(np.diff(d.close.iloc[max(0,n-scan):n].to_numpy()))
    discovery=max(tick,float(np.median(moves)))
    candidates=[]
    for pct in range(101):
        center=lo+rng*pct/100
        stats=_evaluate_compatible(d,center,discovery,scan,1,valid)
        if stats[2]>=1:candidates.append((center,stats[-1]))
    chosen=[];used=set();spacing=max(tick,rng*.08)
    def add(k):
        center=candidates[k][0]
        if any(abs(center-z.center)<spacing for z in chosen):return
        half=auto_half(d,atr,center,discovery,valid,scan,tick)
        sup,res,hits,dwell,age,strength=_evaluate_compatible(d,center,half,scan,1,valid)
        tests,succ,ss,rs,br,rel=_evaluate_independent(d,atr,center,half,scan,1,valid,tick)
        chosen.append(BalanceZone(center,half,100*(center-lo)/rng,strength,hits,sup,res,dwell,age,tests,succ,ss,rs,br,rel,engine));used.add(k)
    for z in old:
        available=[k for k in range(len(candidates)) if k not in used]
        if len(chosen)>=9 or not available:break
        k=min(available,key=lambda k:abs(candidates[k][0]-z.center))
        if abs(candidates[k][0]-z.center)<=rng*.015 and candidates[k][1]>=25:add(k)
    for k in sorted(range(len(candidates)),key=lambda k:(-candidates[k][1],k)):
        if len(chosen)>=9:break
        if k not in used:add(k)
    return sorted(chosen,key=lambda z:z.center)

def snapshot(d,atr,oldA,oldB,tick):
    a=zones(d,atr,10,'A',oldA,tick);b=zones(d,atr,5,'B',oldB,tick)
    visible=a+[z for z in b if not any(z.center+z.half>=x.center-x.half and z.center-z.half<=x.center+x.half for x in a)]
    best=None;bestscore=-1
    for z in visible:
        bottom,top=z.center-z.half,z.center+z.half
        touches=low=high=last=0
        for off in range(3):
            row=d.iloc[-1-off];prev=d.close.iloc[-2-off]
            if row.low<=top and row.high>=bottom:
                touches+=1;t=3
                if prev>top:low+=1;t=4 if row.close<bottom else 1
                elif prev<bottom:high+=1;t=4 if row.close>top else 2
                if not last:last=t
        if touches<2:continue
        score=.45*100*touches/3+.35*z.strength+.2*(z.reliability if math.isfinite(z.reliability) else 50)
        if score<=bestscore:continue
        bestscore=score;p=d.close.iloc[-1];distance=max(bottom-p,p-top,0)/atr.iloc[-1]
        profile='CROSS' if last==4 else 'SUPPORT_TEST' if low>high else 'RESISTANCE_TEST' if high>low else 'INSIDE' if last==3 else 'MIXED' if low>0 else 'INSIDE'
        best=dict(BAL=z.center,HALF=z.half,STATE='ACTIVE' if distance==0 else 'NEAR',DIST=distance,TOUCH=touches,LOW=low,HIGH=high,PROFILE=profile,ENGINE=z.engine,SCORE=bestscore)
    return best,a,b

def replay(data,ticker,start=None,mode='restart',tick=.0001,progress=None):
    d=_normalize_ohlc(data);atr=wilder_atr(d);t=timing(d);a=[];b=[];rows=[]
    for i in range(60,len(d)):
        if mode=='restart':a=[];b=[]
        snap,a,b=snapshot(d.iloc[:i+1],atr.iloc[:i+1],a,b,tick)
        if progress:progress(i,len(d))
        if start is not None and d.index[i]<pd.Timestamp(start):continue
        if snap is None:continue
        state=t.iloc[i].to_dict();ph=phase(state['HS'],state['HT'],state['MEM'],state['HA'],state['INV'],state['SEQ'])
        if ph not in PHASES or snap['DIST']>1.5:continue
        row=dict(Date=d.index[i],Ticker=ticker,PHASE=ph,Close=d.close.iloc[i],**snap,**state)
        row['SLOPE']=(t.HMA.iloc[i]-t.HMA.iloc[i-1])/atr.iloc[i]
        row['RET12']=(d.close.iloc[i-1]-d.close.iloc[i-13])/atr.iloc[i]
        # Signal known at previous close; actionable from following session open.
        entry=d.open.iloc[i+1] if i+1<len(d) else np.nan;row['EntryOpen']=entry
        for horizon in (1,3,5,10,20):
            complete=i+horizon<len(d);future=d.iloc[i+1:i+horizon+1]
            row[f'CloseRet{horizon}']=100*(d.close.iloc[i+horizon]/d.close.iloc[i]-1) if complete else np.nan
            row[f'OpenRet{horizon}']=100*(d.close.iloc[i+horizon]/entry-1) if complete else np.nan
            row[f'MFE{horizon}']=100*(future.high.max()/entry-1) if complete else np.nan
            row[f'MAE{horizon}']=100*(future.low.min()/entry-1) if complete else np.nan
        rows.append(row)
    return pd.DataFrame(rows)
