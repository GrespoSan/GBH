import numpy as np
import pandas as pd
from engine import timing, snapshot, replay, phase, auto_half
from core import wilder_atr
rng=np.random.default_rng(41);n=90
c=100+np.cumsum(rng.normal(0,.7,n));o=np.r_[c[0],c[:-1]]
d=pd.DataFrame(dict(open=o,high=np.maximum(o,c)+.4,low=np.minimum(o,c)-.4,close=c),index=pd.bdate_range('2024-01-01',periods=n))
assert phase(1,1,2,1,0,4)=='FRESH'
assert phase(0,1,8,1,1,1)=='EARLY'
assert phase(0,-1,5,1,0,2)=='TRANSITION'
assert phase(1,1,3,1,0,4)=='MATURE'
a=wilder_atr(d)
pd.testing.assert_frame_equal(timing(d).iloc[:70],timing(d.iloc[:70]))
snap,za,zb=snapshot(d.iloc[:70],a.iloc[:70],[],[],.01)
# Replay prefixes must produce identical signal fields, even as later outcomes mature.
x=replay(d.iloc[:75],'TEST');y=replay(d,'TEST')
if not x.empty:
 cols=[c for c in x if not c.startswith(('CloseRet','OpenRet','MFE','MAE')) and c!='EntryOpen']
 pd.testing.assert_frame_equal(x[cols].reset_index(drop=True),y[y.Date<=d.index[74]][cols].reset_index(drop=True))
for z in za+zb:assert z.half>=.01
print('PASS: phase boundaries, timing prefix invariance, replay prefix invariance, geometry floor')
print('Synthetic events:',len(y),'(verification only; no market evidence)')
