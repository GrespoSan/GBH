# Misura di velocità v0.1.3

Misure nello stesso workspace, sugli stessi CSV Daily TradingView e parametri: restart, prima data 2026-06-01, ultimo giorno ammesso 2026-10-02, tick 0.0001.

| Titolo | Prima | Dopo | Accelerazione | Snapshot |
|---|---:|---:|---:|---:|
| PRY | 31.57 s | 2.69 s | 11.7× | 26 |
| ENI | 30.20 s | 2.37 s | 12.7× | 18 |

Tutte le colonne dei replay precedenti e nuovi coincidono con tolleranza numerica assoluta 1e-9 e relativa 1e-10, categorie e date uguali. Confronto persistent su 90 barre ENI: 11 snapshot identici. Confronto del valutatore compatibile scalare e vettoriale: 234 casi, conteggi/età esatti e strength entro 1e-12. Passano anche i controlli di fase, prefissi temporali, futuro e tick di check_engine.py. Compilazione Python riuscita. La cache Streamlit è configurata ma non è stata misurata nell’interfaccia locale. I tempi sul PC dell’utente dipenderanno dall’hardware e dai dati.

Questo verifica l’ottimizzazione rispetto alla precedente versione Python. Non estende la validazione TradingView a tutte le date. Nessun cambiamento delle regole del motore.
