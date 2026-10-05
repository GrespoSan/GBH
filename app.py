import io
import zipfile
import pandas as pd
import streamlit as st
from engine import replay
st.set_page_config(page_title='GBH V12 storico',layout='wide')
st.title('GBH V12 — test storico')
st.warning('Versione sperimentale: port Python implementato, equivalenza con snapshot TradingView ancora da verificare. I risultati non sono un backtest V12 certificato.')
st.caption('Daily chiuse • 400 barre di lookback • AUTO ROBUST BOUNDED • Hull 16 / memoria 3 • HA • distanza ≤ 1,50 ATR')
mode=st.selectbox('Inizializzazione Balance',['restart','persistent'],format_func=lambda x:'Scansione da zero a ogni data' if x=='restart' else 'Replay continuo con memoria delle zone')
st.caption('Il Pine usa barstate.islast: lo storico effettivo degli alert dipende dall’avvio e dalla persistenza della sessione. Confrontare entrambi i modi.')
start=st.date_input('Prima data da analizzare',value=pd.Timestamp('2023-10-01'))
source=st.radio('Prezzi',['CSV Daily','Yahoo'])
frames={}
if source=='CSV Daily':
    uploads=st.file_uploader('CSV: Date, Open, High, Low, Close (Volume opzionale)',type='csv',accept_multiple_files=True)
    for f in uploads:
        try:
            d=pd.read_csv(f);d.columns=d.columns.str.lower()
            key='date' if 'date' in d else 'time'
            d.index=pd.to_datetime(d.pop(key));frames[f.name.rsplit('.',1)[0]]=d.loc[d.index.normalize()<pd.Timestamp.now(tz='Europe/Rome').tz_localize(None).normalize()]
        except Exception as e:st.error(f'{f.name}: {e}')
else:
    from pathlib import Path
    default=Path(__file__).with_name('universe.txt').read_text()
    tickers=st.text_area('Ticker Yahoo: verificare la corrispondenza con MIL_LS',default)
    st.caption('Yahoo può avere prezzi rettificati, simboli cambiati o titoli senza storico. I titoli esclusi vengono segnalati. Nessuna sostituzione automatica.')
    if st.button('Scarica Daily'):
        import yfinance as yf
        for tk in tickers.replace(',',' ').split():
            try:
                d=yf.Ticker(tk).history(start=(pd.Timestamp(start)-pd.Timedelta(days=900)).date(),auto_adjust=False)
                d.index=d.index.tz_localize(None).normalize();frames[tk]=d.loc[d.index.normalize()<pd.Timestamp.now(tz='Europe/Rome').tz_localize(None).normalize()]
                if d.empty:st.error(f'{tk}: nessun dato')
            except Exception as e:st.error(f'{tk}: {e}')
        st.session_state['frames']=frames
    frames=st.session_state.get('frames',{})
tick=st.number_input('Minimo tick per il lotto di test (specificare quello TradingView)',min_value=.000001,value=.0001,format='%.6f')
st.caption('Per la prima validazione usare un titolo alla volta e il suo tick esatto. La seduta odierna è esclusa in modo conservativo da CSV e Yahoo. Servono almeno 400 barre precedenti al periodo del test.')
if st.button('Esegui replay',disabled=not frames):
    results=[];bar=st.progress(0)
    for tk,d in frames.items():
        if len(d.loc[d.index<pd.Timestamp(start)])<400:st.warning(f'{tk}: meno di 400 barre prima del test; warm-up incompleto.')
        with st.spinner(f'Replay {tk}…'):
            results.append(replay(d,tk,start,mode,tick,lambda i,n:bar.progress((i+1)/n)))
    st.session_state['events']=pd.concat(results,ignore_index=True) if results else pd.DataFrame()
if 'events' in st.session_state:
    events=st.session_state['events']
    if events.empty:st.info('Nessun evento nei dati forniti.')
    else:
        st.write(f'{len(events)} snapshot. Uno stesso setup può comparire in più sedute: non sono operazioni indipendenti.')
        first=events.sort_values(['Ticker','Date']).copy()
        first['episode_start']=(first.PHASE!=first.groupby('Ticker').PHASE.shift()) | (first.groupby('Ticker').Date.diff().dt.days>4)
        use=st.checkbox('Solo inizio episodio di fase (regola esplorativa)',value=False)
        view=first[first.episode_start] if use else first
        group=st.multiselect('Confronta per',['PHASE','STATE','PROFILE','HT','HA'],default=['PHASE'])
        horizon=st.selectbox('Sedute successive',[1,3,5,10,20],index=2)
        if group:
            col=f'OpenRet{horizon}';g=view.groupby(group,dropna=False)
            summary=g.agg(N=('Ticker','size'),N_complete=(col,'count'),Median_return=(col,'median'),Median_MFE=(f'MFE{horizon}','median'),Median_MAE=(f'MAE{horizon}','median'))
            summary['Positive_pct']=g[col].apply(lambda s:100*(s.dropna()>0).mean())
            st.dataframe(summary)
        st.caption('Rendimenti dall’apertura successiva; MFE/MAE sono estremi firmati rispetto a tale prezzo. Commissioni/slippage esclusi. Ultimi orizzonti incompleti = vuoti. SLOPE e RET12 osservativi. Universo attuale: possibile survivorship bias.')
        st.dataframe(view)
        st.download_button('Esporta tutti gli snapshot',events.to_csv(index=False).encode(),file_name='gbh_v12_events.csv')
