import io
import zipfile
import pandas as pd
import streamlit as st
from time import perf_counter
from engine import replay

@st.cache_data(show_spinner=False, max_entries=32)
def cached_replay(data, ticker, start, mode, tick):
    return replay(data, ticker, start, mode, tick)
st.set_page_config(page_title='GBH V12 storico',layout='wide')
st.title('GBH V12 — test storico')
st.warning('Versione sperimentale: confronto TradingView riuscito su PRY, ISP, ELN ed ENI al 2 ottobre 2026. La validazione dello storico completo resta aperta.')
st.caption('Daily chiuse • 400 barre di lookback • AUTO ROBUST BOUNDED • Hull 16 / memoria 3 • HA • distanza ≤ 1,50 ATR')
mode=st.selectbox('Inizializzazione Balance',['restart','persistent'],format_func=lambda x:'Scansione da zero a ogni data' if x=='restart' else 'Replay continuo con memoria delle zone')
st.caption('Il Pine usa barstate.islast: lo storico effettivo degli alert dipende dall’avvio e dalla persistenza della sessione. Confrontare entrambi i modi.')
start=st.date_input('Prima data da analizzare',value=pd.Timestamp('2026-06-01'))
source=st.radio('Prezzi',['CSV Daily','Yahoo'])
frames={}
if source=='CSV Daily':
    uploads=st.file_uploader('CSV: Date, Open, High, Low, Close (Volume opzionale)',type='csv',accept_multiple_files=True)
    for f in uploads:
        try:
            d=pd.read_csv(f);d.columns=d.columns.str.lower()
            key='date' if 'date' in d else 'time'
            raw_date=d.pop(key)
            if pd.api.types.is_numeric_dtype(raw_date):
                unit='ms' if raw_date.abs().median()>1e11 else 's'
                d.index=pd.to_datetime(raw_date,unit=unit,utc=True).dt.tz_convert('Europe/Rome').dt.tz_localize(None).dt.normalize()
            else:
                d.index=pd.to_datetime(raw_date).dt.normalize()
            frames[f.name.rsplit('.',1)[0]]=d.loc[d.index.normalize()<pd.Timestamp.now(tz='Europe/Rome').tz_localize(None).normalize()]
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
    started=perf_counter()
    results=[];bar=st.progress(0)
    for count,(tk,d) in enumerate(frames.items(),1):
        if len(d.loc[d.index<pd.Timestamp(start)])<400:st.warning(f'{tk}: meno di 400 barre prima del test; warm-up incompleto.')
        with st.spinner(f'Replay {tk}…'):
            results.append(cached_replay(d,tk,start,mode,tick))
        bar.progress(count/len(frames))
    st.session_state['events']=pd.concat(results,ignore_index=True) if results else pd.DataFrame()
    st.session_state['elapsed']=perf_counter()-started
if 'events' in st.session_state:
    st.caption(f"Ultima esecuzione: {st.session_state.get('elapsed',0):.1f} secondi. I risultati con gli stessi dati e parametri vengono riutilizzati dalla cache.")
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
