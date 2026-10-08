# Evidências de qualidade: dataset analítico (município × ano)

- n_linhas: **1995**
- n_linhas_esperado_(municipios x anos): **1995**
- n_municipios: **399**
- chave_municipio_ano_duplicada: **0**
- linhas_municipio_ano_preenchidas_com_zero: **0**
- populacao_nao_positiva: **0**
- populacao_interpolada_linhas: **399**
- proporcao_idosos_fora_de_0_1: **0**
- renda_negativa: **0**
- renda_mediana_maior_que_media_(municipios): **0**
- esgoto_adequado_menor_que_rede: **0**
- agua_ligacao_menor_que_rede_principal: **0**
- municipio_ano_com_menos_de_10_internacoes_(2022-2025): **1**
- municipio_ano_sem_internacao_(2022-2025): **0**

## reconciliacao_internacoes

- linhas_base_tratada: **662730**
- soma_no_dataset_analitico: **662730**
- confere: **True**

## pct_fora_de_0_100

- pct_agua_rede: **0**
- pct_agua_ligacao_rede: **0**
- pct_esgoto_rede: **0**
- pct_esgoto_adequado: **0**

## completude_pct_ausente

- cod_municipio_datasus: **0.0**
- cod_municipio_ibge: **0.0**
- nome_municipio: **0.0**
- ano: **0.0**
- ano_parcial: **0.0**
- internacoes_icsap: **0.0**
- populacao: **0.0**
- populacao_origem: **0.0**
- taxa_icsap: **0.0**
- proporcao_idosos: **0.0**
- pct_agua_rede: **0.0**
- pct_agua_ligacao_rede: **0.0**
- pct_esgoto_rede: **0.0**
- pct_esgoto_adequado: **0.0**
- renda_domiciliar_media: **0.0**
- renda_domiciliar_mediana: **0.0**

## taxa_icsap_2022_2025

- count: **1596.0**
- mean: **166.75**
- std: **97.34**
- min: **19.16**
- 25%: **103.93**
- 50%: **143.72**
- 75%: **202.01**
- max: **1248.87**

## checagens_tabelas_ibge

- 9514_municipios_com_faixa_sem_valor: **0**
- 6803_pai_diferente_da_soma_dos_detalhes: **0**
- 6805_pai_diferente_da_soma_dos_detalhes: **0**
- 9514_municipios_do_PR_ausentes_na_tabela: **0**
- 6579_municipios_do_PR_ausentes_na_tabela: **0**
- 6803_municipios_do_PR_ausentes_na_tabela: **0**
- 6805_municipios_do_PR_ausentes_na_tabela: **0**
- 10295_municipios_do_PR_ausentes_na_tabela: **0**
- total_domicilios_6803_diferente_de_6805: **0**
- pop_2024_sobre_censo_2022_fora_de_0.85_1.25: **0**
