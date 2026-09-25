import pandas as pd

caminho_bruto = 'dados/brutos/RELATORIO_DTB_BRASIL_MUNICIPIO.xls'
df_ibge = pd.read_excel(caminho_bruto, skiprows=6)

df_pr = df_ibge[df_ibge['UF'] == 41].copy()

df_pr = df_pr[['Código Município Completo', 'Nome_Município']]
df_pr.columns = ['codigo_ibge', 'nome_municipio'] 

df_pr['codigo_datasus'] = df_pr['codigo_ibge'].astype(str).str[:-1].astype(int)

caminho_processado = 'dados/processados/municipios_pr.csv'
df_pr.to_csv(caminho_processado, index=False)

print(df_pr.head())