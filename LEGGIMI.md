# Verifica del passaggio ATR nel Radar V12

La diagnostica v0.2 restituisce per PRY / Daily CLOSED 2 ottobre 2026:
- HALF usata dalla zona: 1,38
- 4 campioni geometrici (offset 15,39,49,114)
- mediana: 0,20726859
- MAD: 0,05293020
- HALF robusta prima del limite: 1,35204629

I campioni, la mediana, il MAD e la HALF robusta coincidono con Python. La discordanza rimane tra il calcolo diretto e il valore incorporato nella zona dal percorso f_buildZoneV → f_autoHalf.

Ipotesi tecnica da verificare: l'ATR storico è passato come parametro series attraverso funzioni annidate richiamate nei blocchi barstate.islast. I parametri Pine possiedono buffer locali di storia che possono risultare incompleti se le chiamate non sono eseguite su ogni barra.
Fonte ufficiale: https://www.tradingview.com/pine-script-docs/language/execution-model/

La variante proposta copia gli ATR degli offset necessari in un array, direttamente nel contesto motore che calcola ta.atr su ogni barra. f_autoHalf, f_buildZoneV e f_evaluateIndependentV ricevono quell'array e leggono i valori con array.get. Parametri, soglie, ranking, definizioni di fase e formula robusta restano uguali. La disponibilità dello storico ATR può modificare HALF e reliability, quindi anche la zona selezionata.

Non è stata eseguita compilazione Pine nel workspace; il confronto TradingView resta necessario.

## Passo immediato

Aprire GBH_V12_AUDIT_PRY_v0_3_ATR_BUFFER_FIX.pine nel Pine Editor e aggiungerlo come nuovo indicatore diagnostico. Default PRY e Daily CLOSED. Non sostituire ancora i Radar operativi e non modificare gli alert.

Per la seduta sorgente 2026-10-02, l'esito Python atteso è:
BAL 128,7668; HALF 1,3520462861; bordo inferiore 127,4147537139; 2/3 tocchi; LOW/HIGH 0/2; A; ACTIVE; RESISTANCE TEST; FRESH; Hull LONG/BULL MEM0; HA verde SEQ4.

Se questi valori coincidono, il passaggio ATR esplicito risolve l'incoerenza su questo caso. Restano ulteriori date e titoli per concludere la validazione del port e definire il comportamento della retention nel replay.

Le due copie ITA1/ITA2 v1.2.1 sono proposte da verificare, non sostituzioni automatiche. Il DATA BRIDGE è disabilitato di default in queste copie. V=12 rimane la versione del formato messaggio; il motore corretto va distinto dal vecchio negli studi e negli alert.
