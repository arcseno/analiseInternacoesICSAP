# Inventário dos dados

O projeto usa uma base principal de saúde (SIH/DATASUS), que traz o evento que queremos explicar, e seis bases do IBGE, que dão o denominador populacional e os fatores socioeconômicos de cada município. A descrição de por que cada base entrou está em `docs/fontesDeDados.md`. Aqui fica o inventário no formato pedido pela Etapa 2.

## Base principal: internações hospitalares (SIH/DATASUS)

| Item | Descrição |
|---|---|
| Fonte | Sistema de Informações Hospitalares do SUS (SIH/SUS), arquivos RD (AIH reduzida) |
| Responsável/provedor | Ministério da Saúde, via DATASUS |
| Acesso | Espelho do PySUS 2.11.6 (48 meses) e FTP oficial `ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/` (7 meses que faltavam no espelho) |
| Formato | Arquivos `.dbc` mensais por UF (`RDPRaamm.dbc`), convertidos para DataFrame com `pyreaddbc` |
| Período | Janeiro/2022 a julho/2026 (55 meses de internação) |
| Frequência de atualização | Mensal. Os meses mais recentes ainda recebem AIHs nas competências seguintes |
| Quantidade de registros | 4.615.785 linhas baixadas, 662.730 internações ICSAP após o tratamento |
| Principais atributos | `N_AIH`, `MUNIC_RES`, `DT_INTER`, `DIAG_PRINC`, `VAL_TOT`, `DIAS_PERM` (mais `ANO_CMPT` e `MES_CMPT`, usados só na deduplicação) |
| Licença/condições de uso | Dados públicos e anonimizados, de livre acesso, com citação da fonte. O diagnóstico é dado de saúde (sensível pela LGPD), então o uso fica restrito a análises agregadas (ver `05_privacidade_etica.md`) |
| Arquivo tratado | `dados/processados/internacoes_icsap_pr.csv.gz`, gerado por `src/extracao/dataSus.py` |

## Bases complementares (IBGE)

Todas vêm do SIDRA (Sistema IBGE de Recuperação Automática), exportadas em CSV no nível de município para o Paraná, e são publicadas pelo IBGE como dados públicos de uso livre com citação da fonte. Os arquivos brutos ficam em `dados/brutos/` e são lidos por `src/transformacao/montar_dataset.py`.

| Tabela | Conteúdo | Período | Atualização | Registros | Atributos usados |
|---|---|---|---|---|---|
| 9514 | População residente por sexo e idade | Censo 2022 | Decenal (Censo) | 399 municípios × 21 faixas etárias | População total e população de 60 anos ou mais |
| 6579 | População residente estimada | 2024, 2025 e 2026 | Anual (não houve estimativa em 2023) | 399 municípios × 3 anos | População estimada |
| 6803 | Domicílios por forma de abastecimento de água | Censo 2022 | Decenal | 399 municípios | Domicílios com rede geral como fonte principal, com ligação à rede e sem ligação |
| 6805 | Domicílios por tipo de esgotamento sanitário | Censo 2022 | Decenal | 399 municípios | Domicílios por tipo de esgotamento |
| 10295 | Rendimento domiciliar per capita | Censo 2022 | Decenal | 399 municípios | Rendimento médio e mediano (R$) |
| DTB | Divisão Territorial Brasileira (códigos de município) | Versão vigente no download | Anual | 5.570 municípios, 399 do PR | Código IBGE de 7 dígitos e nome |

A tabela de códigos (`RELATORIO_DTB_BRASIL_MUNICIPIO.xls`) vira `dados/processados/municipios_pr.csv` pelo script `codigosMunicipios.py`, e é ela que permite ligar o código de 6 dígitos do DATASUS ao de 7 dígitos do IBGE.

## Produto final

| Arquivo | Granularidade | Linhas | Uso |
|---|---|---|---|
| `internacoes_icsap_pr.csv.gz` | Uma internação | 662.730 | Base tratada, uso interno (não publicada) |
| `dataset_municipio_ano.csv` | Município × ano | 1.995 (399 × 5) | Base analítica para o BI e o modelo da Etapa 3 |
