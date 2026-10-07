import pandas as pd

dup = pd.read_csv('dados/processados/duplicatas_aih.csv', sep=';',
                  dtype={'N_AIH': str, 'DT_INTER': str})

# linhas totalmente iguais
print('Linhas identicas:', dup.duplicated().sum())

# a mesma AIH aparece com datas de internacao diferentes?
datas_por_aih = dup.groupby('N_AIH')['DT_INTER'].nunique()
print('AIHs com a mesma data:', (datas_por_aih == 1).sum())
print('AIHs com datas diferentes:', (datas_por_aih > 1).sum())

# a mesma AIH aparece com valores diferentes?
valores_por_aih = dup.groupby('N_AIH')['VAL_TOT'].nunique()
print('AIHs com o mesmo valor:', (valores_por_aih == 1).sum())
print('AIHs com valores diferentes:', (valores_por_aih > 1).sum())

# quanto de valor a regra atual descarta
total_todas = dup['VAL_TOT'].sum()
mantidas = dup.sort_values('DIAS_PERM', ascending=False).drop_duplicates('N_AIH')
total_mantidas = mantidas['VAL_TOT'].sum()
print('Valor somando todas as linhas:', total_todas)
print('Valor so nas linhas mantidas:', total_mantidas)

# exemplo pra olhar com os proprios olhos
print(dup.head(12))