# Verifica TradingView / Python — 5 ottobre 2026

Motore Pine con ATR storico passato tramite array, diagnostica v0.3. Python con confronti numerici a nove decimali. Sorgente comune: Daily CLOSED 2 ottobre 2026, ore 17:30 Europe/Rome. Confronto Python restart, senza zone iniziali, tick assunto 0.0001.

| Campo | PRY | ISP | ELN | ENI |
|---|---:|---:|---:|---:|
| Close | 129.8 | 6.328 | 16.27 | 24.19 |
| BAL | 128.7668 | 6.60945 | nessuna | 24.03465 |
| HALF | 1.35204629 | 0.052 | nessuna | 0.08447119 |
| Motore | A | A | nessuno | A |
| Tocchi / LOW / HIGH | 2/0/2 | 2/1/0 | 0/0/0 | 3/1/0 |
| Fase | FRESH | WAIT | FRESH | EARLY |
| Hull segnale / trend / memoria | 1/1/0 | -1/-1/2 | 1/1/1 | 0/1/5 |
| HA / sequenza | 1/4 | -1/3 | 1/3 | 1/1 |
| SLOPE | 0.11274286 | -0.68531108 | 0.07777593 | 0.03753369 |
| RET12 | 1.40541812 | -2.51209516 | 0.43901717 | -0.74419850 |
| Snapshot ammesso | sì | no | no | sì |

Questi campi coincidono alla precisione visualizzata nelle quattro schermate utente e nei calcoli sui rispettivi CSV TradingView. Il bordo inferiore ENI è parzialmente coperto da un riquadro nella schermata e non è stato usato come confronto diretto.

ISP: distanza della fascia 1.80125073 ATR e fase WAIT; non ammesso. Geometria con soli due campioni: il minimo è tre, quindi mediana/MAD/HALF robusta della diagnostica risultano NaN e la fascia usa Discovery HALF 0.052. Non è un errore di calcolo.

ELN: nessuna zona supera la selezione dei tocchi; valori della zona NaN e 0/0/0 coerenti con Python. Fase FRESH da sola non basta.

ENI: zona A 24.03465, HALF 0.084471194731, bordi Python 23.950178805269–24.119121194731. Prezzo sopra fascia, distanza 0.13186975 ATR, NEAR, SUPPORT_TEST, EARLY. Nove campioni robusti indicati nella diagnostica. È il secondo caso con geometria robusta selezionata e il primo caso EARLY verificato.

Fonti: CSV MIL_LS_PRY, 1D.csv; MIL_LS_ISP, 1D.csv; MIL_LS_ELN, 1D(1).csv; MIL_LS_ENI, 1D.csv. Schermate image(20261005-203951).png, image(20261005-204702).png, image(20261005-204749).png, image(20261005-204825).png. Simboli trattati come etichette dei file/feed, senza reinterpretare ELN come ENI.

## Stato della validazione

Quattro titoli nella stessa data verificati: due snapshot ammessi, un caso WAIT/lontano, un caso senza Balance. Nessuna discrepanza osservata nei campi confrontati. Questo verifica la coerenza della diagnostica e del port su quei casi, non l’intera storia o tutti i Radar.

Restano date diverse, motore B, fase TRANSITION e casi ai bordi, oltre alla retention: restart e persistent sono varianti sperimentali. Il motore Pine originale costruisce zone su barstate.islast e la memoria reale dipende dalla sessione. La correzione ATR può cambiare zone e risultati rispetto al motore originale. V=12 è la versione del formato connector, non la certificazione del motore. Nessun vantaggio statistico dimostrato.
