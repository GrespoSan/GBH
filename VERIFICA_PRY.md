# Verifica PRY — 5 ottobre 2026

Il codice Pine incollato dall'utente coincide, dopo normalizzazione CRLF, con Radar ITA1 v1.2 CLOSED OPEN recuperato del 28 settembre.

Lo screenshot successivo alla richiesta di reinserimento mostra ancora PRY 129,80, Balance 128,7668, tocchi 3/3, LOW/HIGH 0/3, RESISTANCE TEST, ACTIVE, LONG/BULL MEM0, HA verde SEQ4, FRESH, SLOPE .113A e RET12 1.405A.

CSV: 489 Daily, dal 28 ottobre 2024 al 5 ottobre 2026. La sorgente confrontata è la seduta del 2 ottobre, con 488 barre disponibili. Nessun dato successivo entra nel segnale.

Errore Python individuato: Pine arrotonda gli operandi float a 9 cifre decimali nei confronti; Python usava precisione piena. Ad esempio 9.494399999999985 < 9.4944 risulta vero in Python, falso in Pine. L'esclusione di zone esattamente alla distanza minima cambiava il set di zone selezionate.

Correzione: confronti numerici in core/engine allineati a nove decimali, senza cambiare le soglie né preimpostare zone iniziali. La correzione riguarda anche condizioni ai bordi e confronti di score/reazione.

Dopo la correzione, la scansione da zero produce spontaneamente Balance A 128,7668, HALF 1,3520462861, ACTIVE, RESISTANCE TEST, FRESH, LONG/BULL MEM0, HA verde SEQ4, SLOPE 0,1127428638, RET12 1,4054181177. Non richiede alcuna zona seminata.

Resta una discrepanza: Python calcola 2/3 tocchi, LOW/HIGH 0/2, mentre screenshot 3/3 e 0/3. La terza candela (30 settembre) ha High 127,40: con HALF 1,3520462861 il bordo inferiore è 127,4147537139 e non viene toccato. Per 3/3, HALF dovrebbe essere almeno 1,3668 (salvo diverso dato High nello storico del Radar). Lo screenshot non mostra HALF né il motore A/B; il dato originale non consente ancora di verificare la geometria finale.

Conclusione: l'ipotesi che la sola memoria spiegasse l'errore era prematura. Il livello ora coincide nella scansione da zero. Restano da verificare gli input salvati del Radar (possono differire dai default del codice), HALF/ENGINE, e l'ATR storico usato per la stima geometrica. Il backtest resta sperimentale e non validato integralmente.

L'esportazione PRY_events_precision_fixed.csv è una ricalcolazione sui prezzi reali forniti dall'utente, non una prova del vantaggio statistico V12. Include warm-up parziale nella prima porzione del periodo. Nessun rendimento è una simulazione di operazioni con stop/target e costi.

Fonte sulla semantica numerica: https://www.tradingview.com/pine-script-docs/language/type-system/
