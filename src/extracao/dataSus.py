import pandas as pd
from pysus import sih

df_bruto = sih(
    state='PR',
    year=list(range(2022, 2027)),
    month=list(range(1, 13)),
    group='RD',
    as_dataframe=True
)

colunas_interesse = ['N_AIH', 'MUNIC_RES', 'DT_INTER', 'DIAG_PRINC', 'VAL_TOT', 'DIAS_PERM']
df_reduzido = df_bruto[colunas_interesse].copy()
del df_bruto

df_reduzido = df_reduzido[
    (df_reduzido['DT_INTER'].astype(str).str[:4].astype(int).between(2022, 2026)) &
    (df_reduzido['MUNIC_RES'].astype(str).str.startswith('41'))
]

# lista Brasileira de ICSAP
icsap_grupos = {
    "01 - Doenças preveníveis por imunização e condições sensíveis": [
        'A37', 'A36', 'A33', 'A34', 'A35', 'B26', 'B06', 'B05', 'A95', 'B16',
        'G000', 'A170', 'A19', 'A150', 'A151', 'A152', 'A153', 'A160', 'A162',
        'A154', 'A155', 'A156', 'A157', 'A158', 'A159', 'A163', 'A164', 'A165',
        'A166', 'A167', 'A168', 'A169', 'A171', 'A172', 'A173', 'A174', 'A175',
        'A176', 'A177', 'A178', 'A179', 'A18', 'I00', 'I01', 'I02', 'A51', 'A52',
        'A53', 'B50', 'B51', 'B52', 'B53', 'B54', 'B77'
    ],
    "02 - Gastroenterites infecciosas e complicações": ['E86', 'A00', 'A01', 'A02', 'A03', 'A04', 'A05', 'A06', 'A07', 'A08', 'A09'],
    "03 - Anemia": ['D50'],
    "04 - Deficiências nutricionais": ['E40', 'E41', 'E42', 'E43', 'E44', 'E45', 'E46', 'E50', 'E51', 'E52', 'E53', 'E54', 'E55', 'E56', 'E57', 'E58', 'E59', 'E60', 'E61', 'E62', 'E63', 'E64'],
    "05 - Infecções de ouvido, nariz e garganta": ['H66', 'J00', 'J01', 'J02', 'J03', 'J06', 'J31'],
    "06 - Pneumonias bacterianas": ['J13', 'J14', 'J153', 'J154', 'J158', 'J159', 'J181'],
    "07 - Asma": ['J45', 'J46'],
    "08 - Doenças pulmonares": ['J20', 'J21', 'J40', 'J41', 'J42', 'J43', 'J47', 'J44'],
    "09 - Hipertensão": ['I10', 'I11'],
    "10 - Angina": ['I20'],
    "11 - Insuficiência cardíaca": ['I50', 'J81'],
    "12 - Doenças cerebrovasculares": ['I63', 'I64', 'I65', 'I66', 'I67', 'I69', 'G45', 'G46'],
    "13 - Diabetes mellitus": ['E10', 'E11', 'E12', 'E13', 'E14'],
    "14 - Epilepsias": ['G40', 'G41'],
    "15 - Infecção no rim e trato urinário": ['N10', 'N11', 'N12', 'N30', 'N34', 'N390'],
    "16 - Infecção da pele e tecido subcutâneo": ['A46', 'L01', 'L02', 'L03', 'L04', 'L08'],
    "17 - Doença inflamatória órgãos pélvicos femininos": ['N70', 'N71', 'N72', 'N73', 'N75', 'N76'],
    "18 - Úlcera gastrointestinal": ['K25', 'K26', 'K27', 'K28', 'K920', 'K921', 'K922'],
    "19 - Doenças relacionadas ao pré-natal e parto": ['O23', 'A50', 'P350'],
}

mapa_prefixos = {prefixo: grupo for grupo, prefixos in icsap_grupos.items() for prefixo in prefixos}

diag_str = df_reduzido['DIAG_PRINC'].astype(str)
match_4_chars = diag_str.str[:4].map(mapa_prefixos)
match_3_chars = diag_str.str[:3].map(mapa_prefixos)

df_reduzido['grupo_icsap'] = match_4_chars.fillna(match_3_chars)

# filtra apenas ICSAP
df_fato = df_reduzido[df_reduzido['grupo_icsap'].notna()].copy()

df_fato['DIAS_PERM'] = pd.to_numeric(df_fato['DIAS_PERM'], errors='coerce')
df_fato['VAL_TOT'] = pd.to_numeric(
    df_fato['VAL_TOT'].astype(str).str.replace(',', '.'), errors='coerce'
)

duplicatas_reais = df_fato[df_fato.duplicated(subset='N_AIH', keep=False)]
print(f"AIHs com mais de um registro: {duplicatas_reais['N_AIH'].nunique()}")
print(f"Linhas envolvidas: {len(duplicatas_reais)}")

# deduplicação
df_fato = (
    df_fato
    .sort_values('DIAS_PERM', ascending=False)
    .drop_duplicates(subset='N_AIH', keep='first')
    .sort_values(['MUNIC_RES', 'DT_INTER'])
    .reset_index(drop=True)
)

print(f"Após deduplicação: {len(df_fato)} registros ({df_fato['N_AIH'].nunique()} AIHs únicas)")

df_fato.to_csv('internacoes_icsap_pr.csv', index=False, sep=';')
print(f"Extração concluída! Total: {len(df_fato)} registros")
