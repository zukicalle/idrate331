
# Analizzatore ID Rate & Performance Casse

## Obiettivo del Progetto

Questo strumento automatizza l'elaborazione, l'analisi e il reporting dei dati di tracciamento fidelity (**ID Rate**) esportati da Tableau.

Gli obiettivi principali sono:

1. **Normalizzare i dati grezzi**: Gestire in automatico codifiche Windows/Tableau (`cp1252`, `latin1`, `utf-8-sig`) e ripulire le colonne superflue (come parametri tecnici o passaggi carta).
2. **Segmentare le performance**: Suddividere l'analisi per canale di incasso (**Casse Assistite**, **Casse Self/QCO** e **Totale Negozio**).
3. **Calcolare benchmark operativi**: Stabilire medie ponderate reali per scorporare l'effetto dei volumi di traffico e misurare l'efficienza reale.
4. **Individuare anomalie (Top & Flop 10)**: Evidenziare le giornate con il maggior guadagno o perdita di tessere tracciate rispetto all'atteso.
5. **Esportazione pronta all'uso**: Generare report compatibili con Google Fogli (con virgola decimale italiana per evitare errori di conversione in orari) e grafici ad alta risoluzione in formato JPG.

---

## Significato delle Metriche e dei Campi

| Metrica / Colonna | Formula / Definizione | Spiegazione Operativa |
| --- | --- | --- |
| **`data`** | Data contabile | Giorno di riferimento della transazione. |
| **`cassa`** | Categoria cassa | Modalità operativa analizzata (`ASSISTITE`, `QCO`, `TOTALE`). |
| **`scontrini_totali`** | $\sum \text{Transazioni}$ | Numero complessivo di passaggi in cassa registrati nella giornata. |
| **`scontrini_tessera`** | $\sum \text{Transazioni con Loyalty}$ | Numero di scontrini a cui è stata associata una carta fedeltà cliente. |
| **`id_rate_%`** | $\frac{\text{scontrini\_tessera}}{\text{scontrini\_totali}} \times 100$ | **Tasso di identificazione effettivo**: percentuale di clienti che hanno passato la carta fedeltà nella specifica giornata. |
| **`media_ponderata`** | $\frac{\sum_{\text{periodo}} \text{scontrini\_tessera}}{\sum_{\text{periodo}} \text{scontrini\_totali}} \times 100$ | **Benchmark di reparto**: media ponderata sui volumi dell'intero periodo per quella cassa. Rispetto alla media semplice, evita che giorni festivi o a basso volume distorcano il valore reale. |
| **`tessere_attese`** | $\text{scontrini\_totali} \times \frac{\text{media\_ponderata}}{100}$ | **Volume teorico obiettivo**: quante tessere ci si aspettava di registrare in quel giorno dato il numero effettivo di clienti transitati. |
| **`delta_tessere`** | $\text{scontrini\_tessera} - \text{tessere\_attese}$ | **Scostamento netto**: <br>

<br>• **Valore positivo ($> 0$)**: tessere fedeltà "guadagnate" rispetto allo standard storico.<br>

<br>• **Valore negativo ($< 0$)**: tessere "perse" a causa di mancata richiesta in cassa o fretta operativa. |
| **`indice_efficienza_%`** | $\frac{\text{id\_rate\_\%}}{\text{media\_ponderata}} \times 100$ | **Indice di resa**: <br>

<br>• **$100\%$**: performance esattamente in linea con la media del reparto.<br>

<br>• **$> 100\%$**: sovraperformance operativa.<br>

<br>• **$< 100\%$**: giornata sottotono rispetto al potenziale. |
| **`correlazione_volumi`** | Coeff. di correlazione di Pearson ($r$) | Misura se all'aumentare dell'affluenza l'ID Rate cala: valori marcatamente negativi (es. $r < -0.4$) indicano che nei momenti di punta la richiesta della carta fedeltà viene trascurata per smaltire la coda. |

---

## Logica delle Classifiche (Top & Flop 10)

La graduatoria non viene ordinata semplicemente in base all'ID Rate percentuale, bensì sul **`delta_tessere`**:

* **🏆 TOP 10**: Le 10 giornate in cui il reparto ha generato il più alto volume incrementale di fidelizzazione rispetto al benchmark.
* **⚠️ FLOP 10**: Le 10 giornate in cui si è registrata la perdita più marcata di tessere rispetto ai volumi di traffico registrati, evidenziando criticità operative su cui intervenire.

---

## File Generati in Output

1. **Cartella Excel multi-scheda (`.xlsx`)**:
* Contiene i fogli già separati per visualizzazione immediata: `TOTALE`, `ASSISTITE`, `QCO`, `TOP_FLOP_10`, `TUTTI_I_DATI`.


2. **File CSV dedicati (`.csv`)**:
* Formattati con delimitatore `;` e separatore decimale `,` per l'importazione diretta in Google Fogli senza distorsioni di formato.


3. **Immagini ad alta definizione (`.jpg`)**:
* `grafico_1_benchmark`: Istogramma di confronto dell'ID Rate ponderato tra i reparti.
* `grafico_2_volumi_idrate`: Analisi di dispersione con retta di tendenza tra volumi e tasso di tracciamento.
* `grafico_3_delta_tessere`: Monitoraggio del Delta Tessere rispetto alla linea neutrale dello zero.
* `grafici_completi`: Dashboard panoramica 3-in-1.
