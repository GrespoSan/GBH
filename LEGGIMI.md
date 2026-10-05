# GBH V12 — modulo storico sperimentale

Avvio da terminale, nella cartella estratta:

    pip install -r requirements.txt
    streamlit run app.py

È un modulo separato: l'app v4.6 non viene modificata finché non è verificata la parità del nuovo motore.

## Audit delle fonti

Fonti recuperate: Radar ITA1 e ITA2 v1.2 CLOSED OPEN SLOPE RET12 CONNECTOR del 28 settembre 2026; Streamlit v4.6 rebuild.

Differenze accertate:
- Il Radar V12 usa Discovery = mediana delle variazioni assolute close-close, e geometria AUTO ROBUST BOUNDED (minimo 3 campioni, MAD × 1,4826, massimo Discovery). Streamlit v4.6 usa ATR fisso 0,20.
- Nel Pine i blocchi Balance e selezione della riga sono subordinati a barstate.islast. Le zone non vengono ricostruite storicamente barra per barra durante il caricamento. La memoria dipende dalla vita della sessione; non esiste un unico storico degli alert ricavabile dai soli OHLC senza definire l'inizializzazione.
- Il modulo offre restart (scansione da zero) e persistent (scansione ogni seduta con retention). Entrambi sono esperimenti definiti: nessuno ricostruisce automaticamente la sessione realmente avvenuta.
- In CLOSED, HA T-1 corrisponde alla stessa seduta sorgente del prezzo/Hull, senza applicare un ulteriore ritardo in Python.
- RET12 è (Close della seduta precedente alla sorgente − Close 13 barre prima della sorgente)/ATR della sorgente. Non è Close sorgente contro Close sorgente−12.
- V12 seleziona una riga per titolo tramite score tocchi/strength/reliability; prima Structural A poi Reaction B senza sovrapposizione. Fase e distanza sono filtri successivi.

## Regole congelate nel prototipo

Daily CLOSED, lookback 400, scan 1%, massimo 9 zone per motore, validation A=10 / B=5, break Close, cooldown 6, reazione 0,20 ATR, spacing 8% range, retention strength 25/tolleranza 1,5 step. Hull HMA16, memoria 3; HA ricorsiva; filtro tocchi almeno 2/3, ultima chiusura dentro non obbligatoria; EARLY/FRESH/TRANSITION e distanza dal bordo ≤1,50 ATR. SLOPE/RET12 restano osservativi.

Il minimo tick è un input del test: va impostato correttamente per ciascun titolo. L'elenco contiene 78 simboli distinti dei Pine; il suffisso .MI è una prima mappatura meccanica, non una verifica delle identità Yahoo. Simboli cessati/rinominati vanno verificati senza sostituzioni arbitrarie.

## Misure e limiti

CloseRet: rendimento dalla chiusura sorgente. OpenRet: rendimento dall'apertura della seduta successiva alla chiusura del giorno +N. MFE/MAE: massimo High/minimo Low delle N sedute successive, rispetto all'apertura successiva; valori firmati, non troncati a zero. Orizzonti incompleti vuoti. Commissioni/slippage esclusi.

Gli snapshot ripetuti non sono trade indipendenti. L'opzione inizio episodio è esplorativa: cambio fase o intervallo calendario >4 giorni, non deduplica esattamente gli alert. Confrontare prima statistiche per titolo e periodo; non interpretare percentuali grezze come prova di un vantaggio. Universo attuale: survivorship bias. Prezzi Yahoo possono differire da TradingView per rettifiche e provider.

La seduta odierna è esclusa conservativamente. Caricare almeno 400 barre precedenti al test, preferibilmente 900 giorni di calendario. Il replay Python è una versione di riferimento non ottimizzata: provare un titolo/un periodo breve prima dell'universo completo.

## Verifica eseguita

check_engine.py verifica confini di fase, stabilità dei valori di timing su prefissi, invariabilità dei segnali di replay aggiungendo futuro e minimo tick. Dati sintetici usati esclusivamente per controllare il codice, non per misurare performance di mercato.

## Verifica ancora necessaria

1. Usare CSV Daily TradingView di un titolo e il minimo tick esatto.
2. Confrontare almeno 10 snapshot storici concordati: BAL/HALF, tocchi, profilo, motore, Hull HS/HT/MEM, HA INV/SEQ, SLOPE/RET12 e fase.
3. Definire l'avvio della sessione per il confronto persistent. Per snapshot restart usare un riferimento Pine ricalcolato da zero alla data scelta.
4. Solo dopo la parità, eseguire 2–3 anni sull'universo verificato e integrare il modulo nell'app principale.

Non sono stati scaricati né testati tre anni reali di dati: il pacchetto implementa il replay, ma non contiene risultati statistici V12 validati.
