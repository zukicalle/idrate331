import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def _pulisci_numero(val):
    """Pulisce stringhe numeriche gestendo percentuali, virgole decimali e punti per le migliaia."""
    if pd.isna(val):
        return 0.0
    s = str(val).strip().replace('%', '').replace(' ', '')
    if not s or s == '-':
        return 0.0

    # Se c'è la virgola, è il decimale italiano (es. 46,20 o 1.256,50)
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        # Se non c'è virgola, verifica se il punto è un separatore di migliaia (es. 1.256 o 23.373)
        parts = s.split('.')
        if len(parts) > 1 and len(parts[-1]) == 3:
            s = s.replace('.', '')
    try:
        return float(s)
    except Exception:
        return 0.0

def _carica_file_flessibile(file_path):
    """
    Rileva automaticamente codifica (UTF-16, UTF-8, CP1252) e separatore (Tab, ;, ,).
    Restituisce le prime righe per decidere la struttura.
    """
    with open(file_path, 'rb') as f:
        inizio = f.read(500)

    # Rilevamento BOM UTF-16
    if inizio.startswith(b'\xff\xfe') or inizio.startswith(b'\xfe\xff'):
        codifica = 'utf-16'
    else:
        codifica = 'utf-8-sig'
        for enc in ['utf-8-sig', 'cp1252', 'latin1', 'utf-8']:
            try:
                inizio.decode(enc)
                codifica = enc
                break
            except Exception:
                continue

    with open(file_path, 'r', encoding=codifica, errors='replace') as f:
        prime_linee = [f.readline() for _ in range(3)]

    testo_test = "".join(prime_linee)
    if '\t' in testo_test:
        sep = '\t'
    elif ';' in testo_test:
        sep = ';'
    else:
        sep = ','

    return codifica, sep, prime_linee

def genera_report(file_path):
    """
    Funzione universale: accetta sia export 'Dati' che export 'Tabella a campi incrociati' di Tableau.
    Produce file CSV conformi a Google Fogli, cartella Excel multi-scheda e grafici JPG a 300 DPI.
    """
    nome_base = os.path.splitext(os.path.basename(file_path))[0]
    codifica, sep, prime_linee = _carica_file_flessibile(file_path)

    # 1. Identificazione del tipo di export Tableau
    # Se la seconda riga contiene 'date granularity label' o la prima riga ha categorie come 'Omni'/'ASSISTITE'
    linea_0 = prime_linee[0].lower() if len(prime_linee) > 0 else ""
    linea_1 = prime_linee[1].lower() if len(prime_linee) > 1 else ""

    is_crosstab = ('omni' in linea_0 or 'assistite' in linea_0 or 'date granularity' in linea_1) and ('valori misure' not in linea_0)

    if is_crosstab:

        df_raw = pd.read_csv(file_path, sep=sep, encoding=codifica, header=[0, 1], dtype=str)


        col_data = df_raw.columns[0]
        date_series = df_raw[col_data].astype(str).str.strip()


        mask_valide = ~date_series.str.lower().str.contains('totale|overall|complessivo', na=False) & (date_series != '')

        righe = []
        casse_trovate = list(dict.fromkeys([c[0] for c in df_raw.columns[1:]]))

        for _, riga in df_raw[mask_valide].iterrows():
            d = str(riga[col_data]).strip()
            for cassa in casse_trovate:
                cassa_std = 'TOTALE' if cassa.strip().upper() == 'OMNI' else cassa.strip().upper()
                sub_riga = riga[cassa]

                # Trova Totale Y e Tracciato Y
                tot_y = 0
                tracc_y = 0
                for misura_nome, val in sub_riga.items():
                    m_lower = str(misura_nome).lower()
                    if 'totale y' in m_lower or 'totale' in m_lower:
                        tot_y = int(_pulisci_numero(val))
                    elif 'tracciato y' in m_lower or 'tracciato' in m_lower or 'tessera' in m_lower:
                        tracc_y = int(_pulisci_numero(val))

                righe.append({
                    'data': d,
                    'cassa': cassa_std,
                    'scontrini_totali': tot_y,
                    'scontrini_tessera': tracc_y
                })

        df_base = pd.DataFrame(righe)

    else:

        df_raw = pd.read_csv(file_path, sep=sep, encoding=codifica, dtype=str)
        df_raw.columns = [str(c).strip() for c in df_raw.columns]

        mappa = {}
        for c in df_raw.columns:
            cl = c.lower()
            if 'valori misur' in cl or 'measure value' in cl: mappa[c] = 'Valori misure'
            elif 'nomi misur' in cl or 'measure name' in cl: mappa[c] = 'Nomi misure'
            elif 'date gran' in cl or cl in ['data', 'date']: mappa[c] = 'date granularity label'
            elif 'split' in cl or cl in ['cassa']: mappa[c] = 'Split Selection'
        df_raw = df_raw.rename(columns=mappa)

        df_raw['Valori misure'] = df_raw['Valori misure'].apply(_pulisci_numero)

        df_pivot = df_raw.pivot_table(
            index=['date granularity label', 'Split Selection'],
            columns='Nomi misure',
            values='Valori misure',
            aggfunc='first'
        ).reset_index()

        col_data = 'date granularity label'
        col_cassa = 'Split Selection'
        col_tot = [c for c in df_pivot.columns if 'totale y' in str(c).lower() or 'totale' in str(c).lower()][0]
        col_tracc = [c for c in df_pivot.columns if 'tracciato y' in str(c).lower() or 'tracciato' in str(c).lower()][0]

        df_base = pd.DataFrame({
            'data': df_pivot[col_data].astype(str).str.strip(),
            'cassa': df_pivot[col_cassa].astype(str).str.strip().str.upper(),
            'scontrini_totali': df_pivot[col_tot].fillna(0).astype(int),
            'scontrini_tessera': df_pivot[col_tracc].fillna(0).astype(int)
        })


    if 'TOTALE' not in df_base['cassa'].values:
        df_tot = df_base.groupby('data', as_index=False)[['scontrini_totali', 'scontrini_tessera']].sum()
        df_tot['cassa'] = 'TOTALE'
        df_all = pd.concat([df_base, df_tot], ignore_index=True)
    else:
        df_all = df_base.copy()

    df_all['id_rate_%'] = np.where(
        df_all['scontrini_totali'] > 0,
        ((df_all['scontrini_tessera'] / df_all['scontrini_totali']) * 100).round(2),
        0.0
    )

    benchmarks = {}
    for cassa_nome in df_all['cassa'].unique():
        sub = df_all[df_all['cassa'] == cassa_nome]
        tot = sub['scontrini_totali'].sum()
        tess = sub['scontrini_tessera'].sum()
        id_rate_pond = (tess / tot * 100) if tot > 0 else 0
        corr = sub['scontrini_totali'].corr(sub['id_rate_%']) if len(sub) > 1 else 0
        benchmarks[cassa_nome] = {
            'scontrini_totali': tot,
            'scontrini_tessera': tess,
            'id_rate_ponderato_%': round(id_rate_pond, 2),
            'correlazione_volumi': round(corr, 2) if not np.isnan(corr) else 0.0
        }

    df_all['media_ponderata'] = df_all['cassa'].map(lambda c: benchmarks[c]['id_rate_ponderato_%'])
    df_all['tessere_attese'] = (df_all['scontrini_totali'] * (df_all['media_ponderata'] / 100)).round(1)
    df_all['delta_tessere'] = (df_all['scontrini_tessera'] - df_all['tessere_attese']).round(1)
    df_all['indice_efficienza_%'] = np.where(
        df_all['media_ponderata'] > 0,
        ((df_all['id_rate_%'] / df_all['media_ponderata']) * 100).round(1),
        0.0
    )

    colonne_finali = [
        'data', 'cassa', 'scontrini_totali', 'scontrini_tessera',
        'id_rate_%', 'media_ponderata', 'tessere_attese', 'delta_tessere', 'indice_efficienza_%'
    ]
    df_all = df_all[colonne_finali].sort_values(by=['cassa', 'data']).reset_index(drop=True)

    df_totali = df_all[df_all['cassa'] == 'TOTALE'].sort_values('data').reset_index(drop=True)
    df_assistite = df_all[df_all['cassa'] == 'ASSISTITE'].sort_values('data').reset_index(drop=True)
    df_qco = df_all[df_all['cassa'] == 'QCO'].sort_values('data').reset_index(drop=True)

    liste_classifiche = []
    for mod in ['ASSISTITE', 'QCO', 'TOTALE']:
        if mod in df_all['cassa'].values:
            sub = df_all[df_all['cassa'] == mod]
            top10 = sub.sort_values(by='delta_tessere', ascending=False).head(10).copy()
            top10['Categoria'] = f'🏆 TOP 10 - {mod}'

            flop10 = sub.sort_values(by='delta_tessere', ascending=True).head(10).copy()
            flop10['Categoria'] = f'⚠️ FLOP 10 - {mod}'

            liste_classifiche.extend([top10, flop10])

    col_class = ['Categoria', 'data', 'cassa', 'scontrini_totali', 'scontrini_tessera', 'id_rate_%', 'delta_tessere', 'indice_efficienza_%']
    df_classifiche = pd.concat(liste_classifiche)[col_class].reset_index(drop=True)


    colori_barre = ['#2563eb', '#f59e0b', '#10b981', '#6b7280']
    colori_scatter = {'ASSISTITE': '#2563eb', 'QCO': '#f59e0b', 'TOTALE': '#10b981'}
    tab_bench = pd.DataFrame(benchmarks).T.reset_index().rename(columns={'index': 'Modalità Cassa'})
    nomi_casse = tab_bench['Modalità Cassa'].tolist()
    valori_pond = tab_bench['id_rate_ponderato_%'].tolist()

    fig1, ax1 = plt.subplots(figsize=(6, 5))
    barre = ax1.bar(nomi_casse, valori_pond, color=colori_barre[:len(nomi_casse)], width=0.5)
    ax1.set_title("ID Rate Ponderato Globale (%)", fontsize=12, fontweight='bold', pad=12)
    ax1.set_ylabel("ID Rate Ponderato (%)")
    ax1.set_ylim(0, (max(valori_pond) * 1.25) if valori_pond else 100)
    ax1.grid(axis='y', linestyle=':', alpha=0.6)
    for bar in barre:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2.0, h + 0.5, f"{h:.1f}%", ha='center', va='bottom', fontweight='bold')
    plt.tight_layout()
    jpg_g1 = f"grafico_1_benchmark_{nome_base}.jpg"
    fig1.savefig(jpg_g1, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close(fig1)

    fig2, ax2 = plt.subplots(figsize=(7, 5))
    for mod in ['ASSISTITE', 'QCO']:
        if mod in df_all['cassa'].values:
            sub = df_all[df_all['cassa'] == mod]
            ax2.scatter(sub['scontrini_totali'], sub['id_rate_%'], alpha=0.5, label=mod, color=colori_scatter.get(mod, '#6b7280'))
            if len(sub) > 1:
                m, q = np.polyfit(sub['scontrini_totali'], sub['id_rate_%'], 1)
                x_trend = np.linspace(sub['scontrini_totali'].min(), sub['scontrini_totali'].max(), 50)
                ax2.plot(x_trend, m * x_trend + q, linewidth=2, color=colori_scatter.get(mod, '#6b7280'))
    ax2.set_title("Impatto Volumi su ID Rate", fontsize=12, fontweight='bold', pad=12)
    ax2.set_xlabel("Scontrini Totali")
    ax2.set_ylabel("ID Rate (%)")
    ax2.legend()
    ax2.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    jpg_g2 = f"grafico_2_volumi_idrate_{nome_base}.jpg"
    fig2.savefig(jpg_g2, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close(fig2)

    fig3, ax3 = plt.subplots(figsize=(7, 5))
    for mod in ['ASSISTITE', 'QCO']:
        if mod in df_all['cassa'].values:
            sub = df_all[df_all['cassa'] == mod]
            ax3.scatter(sub['scontrini_totali'], sub['delta_tessere'], alpha=0.5, label=mod, color=colori_scatter.get(mod, '#6b7280'))
    ax3.axhline(0, color='black', linewidth=1.2, linestyle='--')
    ax3.set_title("Delta Tessere vs Benchmark", fontsize=12, fontweight='bold', pad=12)
    ax3.set_xlabel("Scontrini Totali")
    ax3.set_ylabel("Delta Tessere (Reali - Attese)")
    ax3.legend()
    ax3.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    jpg_g3 = f"grafico_3_delta_tessere_{nome_base}.jpg"
    fig3.savefig(jpg_g3, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close(fig3)


    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    barre_all = axes[0].bar(nomi_casse, valori_pond, color=colori_barre[:len(nomi_casse)], width=0.5)
    axes[0].set_title("1. ID Rate Ponderato Globale (%)", fontsize=11, fontweight='bold')
    axes[0].set_ylabel("ID Rate Ponderato (%)")
    axes[0].set_ylim(0, (max(valori_pond) * 1.25) if valori_pond else 100)
    axes[0].grid(axis='y', linestyle=':', alpha=0.6)
    for bar in barre_all:
        h = bar.get_height()
        axes[0].text(bar.get_x() + bar.get_width() / 2.0, h + 0.5, f"{h:.1f}%", ha='center', va='bottom', fontweight='bold')

    for mod in ['ASSISTITE', 'QCO']:
        if mod in df_all['cassa'].values:
            sub = df_all[df_all['cassa'] == mod]
            axes[1].scatter(sub['scontrini_totali'], sub['id_rate_%'], alpha=0.5, label=mod, color=colori_scatter.get(mod, '#6b7280'))
            if len(sub) > 1:
                m, q = np.polyfit(sub['scontrini_totali'], sub['id_rate_%'], 1)
                x_trend = np.linspace(sub['scontrini_totali'].min(), sub['scontrini_totali'].max(), 50)
                axes[1].plot(x_trend, m * x_trend + q, linewidth=2, color=colori_scatter.get(mod, '#6b7280'))
    axes[1].set_title("2. Impatto Volumi su ID Rate", fontsize=11, fontweight='bold')
    axes[1].set_xlabel("Scontrini Totali")
    axes[1].set_ylabel("ID Rate (%)")
    axes[1].legend()
    axes[1].grid(True, linestyle=':', alpha=0.6)

    for mod in ['ASSISTITE', 'QCO']:
        if mod in df_all['cassa'].values:
            sub = df_all[df_all['cassa'] == mod]
            axes[2].scatter(sub['scontrini_totali'], sub['delta_tessere'], alpha=0.5, label=mod, color=colori_scatter.get(mod, '#6b7280'))
    axes[2].axhline(0, color='black', linewidth=1.2, linestyle='--')
    axes[2].set_title("3. Delta Tessere vs Benchmark", fontsize=11, fontweight='bold')
    axes[2].set_xlabel("Scontrini Totali")
    axes[2].set_ylabel("Delta Tessere (Reali - Attese)")
    axes[2].legend()
    axes[2].grid(True, linestyle=':', alpha=0.6)

    plt.tight_layout()
    jpg_completo = f"grafici_completi_{nome_base}.jpg"
    fig.savefig(jpg_completo, dpi=300, facecolor='white', bbox_inches='tight')
    plt.show()

    df_all.to_csv(f"risultati_completi_{nome_base}.csv", sep=';', decimal=',', index=False)
    df_totali.to_csv(f"risultati_TOTALE_{nome_base}.csv", sep=';', decimal=',', index=False)
    df_assistite.to_csv(f"risultati_ASSISTITE_{nome_base}.csv", sep=';', decimal=',', index=False)
    df_qco.to_csv(f"risultati_QCO_{nome_base}.csv", sep=';', decimal=',', index=False)
    df_classifiche.to_csv(f"top_flop_10_{nome_base}.csv", sep=';', decimal=',', index=False)

    nome_excel = f"report_completo_{nome_base}.xlsx"
    try:
        with pd.ExcelWriter(nome_excel, engine='openpyxl') as writer:
            df_totali.to_excel(writer, sheet_name='TOTALE', index=False)
            df_assistite.to_excel(writer, sheet_name='ASSISTITE', index=False)
            df_qco.to_excel(writer, sheet_name='QCO', index=False)
            df_classifiche.to_excel(writer, sheet_name='TOP_FLOP_10', index=False)
            df_all.to_excel(writer, sheet_name='TUTTI_I_DATI', index=False)
        print(f"📊 Cartella Excel generata: {nome_excel}")
    except ModuleNotFoundError:
        print("ℹ️ openpyxl non installato: cartella Excel saltata, generati tutti i file CSV.")

    print("\n" + "=" * 60)
    print("      ESPORTAZIONE COMPLETATA CON SUCCESSO!")
    print("=" * 60)
    print(f"🖼️ Grafici JPG salvati a 300 DPI:")
    print(f"   - {jpg_g1}")
    print(f"   - {jpg_g2}")
    print(f"   - {jpg_g3}")
    print(f"   - {jpg_completo}")
    print(f"📁 File CSV divisi per Google Fogli:")
    print(f"   - risultati_TOTALE_{nome_base}.csv")
    print(f"   - risultati_ASSISTITE_{nome_base}.csv")
    print(f"   - risultati_QCO_{nome_base}.csv")
    print(f"   - top_flop_10_{nome_base}.csv")

    return df_all
