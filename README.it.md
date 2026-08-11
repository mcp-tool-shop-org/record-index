<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.md">English</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/record-index/main/docs/assets/logo-wide.png" alt="record-index — query the record instead of reading it" width="820">
</p>

# indice-record

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/record-index/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/record-index/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/record-index/"><img src="https://img.shields.io/badge/landing%20page-live-2ea043" alt="Landing page"></a>
</p>

Una mappa SQLite+FTS5 gestita su un record di decisione in formato Markdown, in modo che una sessione possa **interrogare** il record invece di leggerlo e quindi leggere le quaranta righe a cui l'interrogazione fa riferimento, anziché le seicento che avrebbe esaminato.

**[Pagina di destinazione e manuale →](https://mcp-tool-shop-org.github.io/record-index/)**

Il formato Markdown rimane quello originale. L'indice viene derivato e rigenerato a ogni iterazione, ed è soggetto a un controllo tramite un sistema a quattro livelli `verify`, e per definizione è **errato il giorno in cui viene modificato manualmente**.

## Stato: estratto, testato, non ancora su PyPI

*(Questa sezione riportava "SOLO SCAFFOLD — al momento non sono presenti codici di strumenti in questo repository" fino al 2026-08-11, cosa che è stata falsificata durante l'estrazione. Corretto.)*

**L'estrazione è avvenuta con successo.** Il pacchetto è su `main` e il processo di integrazione è controllato tramite la corrispondenza dei byte con la versione del codice presente nel repository principale (19/19) e **l'assenza di differenze a livello di riga** nello stesso corpus. Due componenti lo utilizzano: [facet](https://github.com/mcp-tool-shop-org/facet), le cui circa 2.462 righe di codice sono state trasformate in una dichiarazione e un adattatore con circa 140 test che ne verificano il funzionamento, e [armature](https://github.com/mcp-tool-shop-org/armature), il cui indice ha fornito 15 risultati su 15 con 47 regole.

**Il pacchetto include la propria suite di test: 455 controlli** su tutti e dieci i moduli, eseguiti in CI con Python 3.11 e 3.13, basati su due repository di record che presentano discrepanze su ogni asse dichiarabile (marcatori, radici del corpus, regole degli archi, vocabolario dei risultati, formati dell'intestazione), in modo che un'implementazione errata possa essere individuata. **Dipendenze: nessuna.** Solo la libreria standard (`sqlite3` + `re` + `json`) e questa è una proprietà dichiarata, non un incidente.

**Sono noti quattro difetti, riprodotti e memorizzati nel codice come test `xfail(strict=True)`** anziché nascosti: `verify()` raddoppia il numero di elementi diagnostici (i livelli di controllo rimangono invariati); lo schema claim-arc presuppone archi numerati con `E`; il localizzatore delle sotto-regole non viene derivato dal formato dell'intestazione dichiarato; e quattro campi della dichiarazione non possono essere dichiarati come vuoti. Nessuno di questi influisce sui due componenti attuali; tutti e quattro sono in coda per la prossima versione.

**Non ancora su PyPI.** `release.yml` pubblica tramite OIDC Trusted Publishing quando viene creata una release su GitHub; nulla viene pubblicato al momento del commit.

## Da dove proviene

Questo è un estratto dell'indice dei record, creato e perfezionato in [`mcp-tool-shop-org/facet`](https://github.com/mcp-tool-shop-org/facet), che è il luogo in cui sono stati definiti tutti i criteri seguenti. Estrae invece di creare una copia perché il libro delle regole di facet registra cinque copie manuali di una funzione, presenti sotto quattro nomi diversi e invisibili a un grep basato sul nome per mesi; copiare migliaia di righe in un secondo repository sarebbe lo stesso errore moltiplicato per tre.

La condizione di estrazione è stata definita in anticipo ed è soggetta a controllo tramite misurazione: *l'indice viene estratto quando un secondo repository adotta i criteri*. [`mcp-tool-shop-org/armature`](https://github.com/mcp-tool-shop-org/armature) è quel repository.

## Il design, in un paragrafo

Un repository di record dichiara **cosa significano i suoi documenti**: quali file contengono le regole, quali formati di intestazione li aprono, qual è il suo vocabolario dei risultati e quali corpora possiede. Lo strumento fornisce **come funziona la ricerca**: analisi sintattica, classificazione, determinismo, i livelli di verifica, con valori di regolazione che includono il corpus e la data in cui sono stati calibrati. I criteri rappresentano una **dichiarazione completa** (un repository dichiara il proprio significato; non eredita mai la cronologia di un altro repository per omissione). Il meccanismo è costituito da **valori predefiniti con possibilità di sovrascrittura**.

Ogni vocabolario indica cosa **non ha riconosciuto**. Una tabella vuota e una tabella che ha eliminato silenziosamente sei elementi sono indistinguibili nel punto in cui viene effettuata la chiamata, e solo uno dei due è corretto.

## L'arresto che era presente qui e come è terminato

*(Fino al 2026-08-11 questa sezione interrompeva il processo di compilazione in caso di collisione misurata. L'arresto era reale, la decisione è stata presa e il processo di compilazione è proseguito; è stato mantenuto qui come traccia anziché eliminato.)*

La fase di classificazione aveva rilevato che derivare l'arco di un documento dal suo prefisso iniziale `E\d\d` **causava una collisione su 7 chiavi primarie** rispetto a facet (sia `E10-ruling.md` che `E10-offsurface-ruling.md` diventano arco `E10`). L'esecutore lo ha rilevato rispetto a un test il cui nome registra lo stesso errore, la decisione congiunta è stata ritirata e ridefinita e l'estrazione è proseguita attraverso i suoi controlli. La traccia (evidenza, le risposte annullate e la decisione che le ha sostituite) si trova in `armature/docs/dispatches/` (l'arco S02).

## Licenza

MIT — vedere [LICENSE](LICENSE).
