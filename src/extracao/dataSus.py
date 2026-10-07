import pandas as pd
from pysus import sih
from ftplib import FTP
from dbfread import DBF
from pyreaddbc import dbc2dbf

def ler_mes_ftp(nome_arquivo, colunas):
    ftp = FTP('ftp.datasus.gov.br')
    ftp.login()
    ftp.cwd('/dissemin/publicos/SIHSUS/200801_/Dados/')
    with open(nome_arquivo, 'wb') as arquivo:
        ftp.retrbinary('RETR ' + nome_arquivo, arquivo.write)
    ftp.quit()

    nome_dbf = nome_arquivo.replace('.dbc', '.dbf')
    dbc2dbf(nome_arquivo, nome_dbf)
    df_mes = pd.DataFrame(iter(DBF(nome_dbf, encoding='cp1252', char_decode_errors='ignore')))
    return df_mes[colunas]

colunas_interesse = ['N_AIH', 'MUNIC_RES', 'DT_INTER', 'DIAG_PRINC', 'VAL_TOT', 'DIAS_PERM', 'ANO_CMPT', 'MES_CMPT']

# pede so a lista de arquivos, sem montar a tabela gigante
# só uma anotação, propusemos utilizar o FTP do DATASUS, mas parece que agora ele lê como padrão um espelho do próprio PySUS,
# mas o conteúdo continua sendo o mesmo.
arquivos = sih(
    state='PR',
    year=list(range(2022, 2027)),
    month=list(range(1, 13)),
    group='RD',
    as_dataframe=False
)

print('Arquivos do espelho PySUS:', len(arquivos))

# le cada arquivo trazendo so as 6 colunas
partes = []
for arquivo in arquivos:
    parte = pd.read_parquet(arquivo, columns=colunas_interesse)
    partes.append(parte)

# completa os 7 meses que faltam no espelho, direto do FTP do DATASUS
meses_faltando = ['RDPR2205.dbc', 'RDPR2206.dbc', 'RDPR2307.dbc', 'RDPR2408.dbc',
                  'RDPR2510.dbc', 'RDPR2601.dbc', 'RDPR2602.dbc']
for nome in meses_faltando:
    parte = ler_mes_ftp(nome, colunas_interesse)
    partes.append(parte)

print('Total de meses (espelho + FTP):', len(partes))

df_reduzido = pd.concat(partes, ignore_index=True)
df_reduzido = df_reduzido.astype(str)
df_reduzido['DT_INTER'] = df_reduzido['DT_INTER'].str.replace('-', '')
print('Linhas baixadas:', len(df_reduzido))

df_reduzido = df_reduzido[
    (df_reduzido['DT_INTER'].astype(str).str[:4].astype(int).between(2022, 2026)) &
    (df_reduzido['MUNIC_RES'].astype(str).str.startswith('41'))
]

print('Depois do filtro de PR e periodo:', len(df_reduzido))

# lista Brasileira de ICSAP
icsap_grupos = {
    "01 - Doenças preveníveis por imunização e condições sensíveis": [
        'A37', 'A36', 'A33', 'A34', 'A35', 'B26', 'B06', 'B05', 'A95', 'B16',
        'G000', 'A170', 'A19', 'A150', 'A151', 'A152', 'A153', 'A160', 'A161', 'A162',
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
duplicatas_reais.sort_values('N_AIH').to_csv('dados/processados/duplicatas_aih.csv', index=False, sep=';')

# deduplicacao: internacao longa e cobrada mes a mes (uma linha por competencia)
# 1) remove so o que e repetido em tudo: mesma AIH, competencia, dias e valor
antes = len(df_fato)
df_fato = df_fato.drop_duplicates(subset=['N_AIH', 'ANO_CMPT', 'MES_CMPT', 'DIAS_PERM', 'VAL_TOT'])
print('Linhas repetidas removidas:', antes - len(df_fato))

# 2) junta as partes de cada AIH: soma dias e valor, o resto e igual
df_fato = df_fato.groupby('N_AIH', as_index=False).agg(
    MUNIC_RES=('MUNIC_RES', 'first'),
    DT_INTER=('DT_INTER', 'first'),
    DIAG_PRINC=('DIAG_PRINC', 'first'),
    grupo_icsap=('grupo_icsap', 'first'),
    VAL_TOT=('VAL_TOT', 'sum'),
    DIAS_PERM=('DIAS_PERM', 'sum'),
)

df_fato = df_fato.sort_values(['MUNIC_RES', 'DT_INTER']).reset_index(drop=True)

print(f"Após deduplicação: {len(df_fato)} registros ({df_fato['N_AIH'].nunique()} AIHs únicas)")

# limite de dias muito altos: percentil 99,9 de DIAS_PERM
LIMITE_DIAS = df_fato['DIAS_PERM'].quantile(0.999)
print('Limite de dias (p99,9):', LIMITE_DIAS)

# sinaliza valores suspeitos
df_fato['flag_dias_zero'] = df_fato['DIAS_PERM'] == 0
df_fato['flag_dias_alto'] = df_fato['DIAS_PERM'] > LIMITE_DIAS
df_fato['flag_valor_zero'] = df_fato['VAL_TOT'] <= 0

df_fato.to_csv('dados/processados/internacoes_icsap_pr.csv', index=False, sep=';')
print(f"Extração concluída! Total: {len(df_fato)} registros")