# Painel ICSAP no Paraná

Painel de indicadores em Power BI (`painel_icsap.pbix`) que apresenta a taxa de internações por condições sensíveis à atenção primária (ICSAP) nos 399 municípios do Paraná, de 2022 a 2025. Uma versão estática do painel está em `painel_icsap.pdf`.

## Para quem é e que decisão apoia

O painel é a camada de entrega da solução proposta na Etapa 1. Os usuários são a gestão da Atenção Básica da SESA-PR e as secretarias municipais de saúde. A decisão que ele apoia é onde priorizar investimento em atenção básica: municípios com taxa ICSAP alta e persistente indicam falha de prevenção que está virando internação.

O painel não avalia hospitais nem equipes, e não explica a causa das internações.

## Fontes de dados

O painel lê três arquivos gerados pelo pipeline do repositório, mais o contorno dos municípios para o mapa:

| Arquivo | Gerado por | Conteúdo |
|---|---|---|
| `dados/processados/dataset_municipio_ano.csv` | `src/transformacao/montar_dataset.py` | Uma linha por município e ano, com internações ICSAP, população, taxa e variáveis do IBGE |
| `dados/processados/fluxos_municipio_ano.csv` | `src/transformacao/montar_fluxos.py` | Uma linha por município de residência, município de internação e ano, com o número de internações |
| `dados/processados/internado_fora_municipio_ano.csv` | `src/transformacao/montar_fluxos.py` | Uma linha por município de residência e ano, com o total de internações e quantas ocorreram fora do município |
| `bi/pr_municipios.topojson` | — | Contorno dos municípios do PR, usado no mapa |

Para atualizar o painel com dados novos, basta rodar o pipeline de novo e clicar em **Atualizar** no Power BI. Nenhum dado é digitado ou editado manualmente dentro do painel.

## Transformações feitas no Power BI

Todas as transformações de dados acontecem no pipeline em Python. No Power BI ficam só ajustes de leitura e as medidas abaixo.

- **Leitura dos números em `dataset_municipio_ano.csv`.** O arquivo usa ponto como separador decimal. Como o Power BI em português lê o ponto como separador de milhar, as colunas decimais (`populacao`, `taxa_icsap`, `proporcao_idosos`, `pct_agua_rede`, `pct_agua_ligacao_rede`, `pct_esgoto_rede`, `pct_esgoto_adequado`, `renda_domiciliar_media`, `renda_domiciliar_mediana`) foram convertidas com a opção *Alterar tipo → Usando a localidade → Inglês (Estados Unidos)*. Sem isso, as taxas ficam mil vezes maiores sem nenhum aviso.
- **Coluna `pct_fora` removida de `internado_fora_municipio_ano.csv`.** O percentual é recalculado pela medida `% internado fora`, porque percentuais não podem ser somados nem tirada a média entre municípios.
- **Ano parcial excluído.** 2026 só tem dados até julho e não é comparável aos anos completos. Todas as páginas têm o filtro `ano_parcial = False`.

## Tabelas auxiliares

```
Anos = DISTINCT(dataset_municipio_ano[ano])
```

```
Municipios = DISTINCT(SELECTCOLUMNS(dataset_municipio_ano,
    "cod_municipio_datasus", dataset_municipio_ano[cod_municipio_datasus],
    "Município", dataset_municipio_ano[nome_municipio]))
```

Relacionamentos (todos de um para muitos, com a tabela auxiliar do lado "um"):

- `Anos[ano]` → `dataset_municipio_ano[ano]`, `fluxos_municipio_ano[ano]` e `internado_fora_municipio_ano[ano]`
- `Municipios[cod_municipio_datasus]` → `internado_fora_municipio_ano[cod_municipio_datasus]` e `fluxos_municipio_ano[cod_municipio_datasus]` (município de residência)

As três tabelas de dados não se ligam diretamente entre si, porque cada uma tem várias linhas por município e uma ligação direta seria de muitos para muitos, o que gera totais errados.

## Medidas

**Taxa ICSAP** (internações por 10 mil habitantes)

```
Taxa ICSAP = DIVIDE(SUM(dataset_municipio_ano[internacoes_icsap]), SUM(dataset_municipio_ano[populacao])) * 10000
```

A taxa de um conjunto de municípios é o total de internações dividido pela população total, e não a média das taxas municipais. A média daria o mesmo peso a um município de 2 mil habitantes e a Curitiba.

**Variação anual**

```
Variação anual =
VAR AnoSel = SELECTEDVALUE(dataset_municipio_ano[ano])
VAR Atual = [Taxa ICSAP]
VAR Anterior = CALCULATE([Taxa ICSAP], dataset_municipio_ano[ano] = AnoSel - 1)
RETURN DIVIDE(Atual - Anterior, Anterior)
```

Compara a taxa do ano selecionado com a do ano anterior. Só funciona com um ano selecionado. Em 2022 fica em branco, porque não há ano anterior na base.

**% internado fora**

```
% internado fora = DIVIDE(SUM(internado_fora_municipio_ano[internacoes_fora]), SUM(internado_fora_municipio_ano[internacoes_total]))
```

Parcela das internações ICSAP de residentes que aconteceram em um município diferente do de residência.

**Municípios sem internação local**

```
Municípios sem internação local = COUNTROWS(FILTER(internado_fora_municipio_ano, internado_fora_municipio_ano[internacoes_fora] = internado_fora_municipio_ano[internacoes_total]))
```

Conta os municípios em que todas as internações ICSAP de residentes ocorreram em outro município. A medida conta linhas da tabela, ou seja, pares município e ano. Com um único ano selecionado, o resultado é o número de municípios. Com vários anos selecionados, o mesmo município é contado uma vez por ano. A base não tem municípios com zero internações no ano, então o caso 0 = 0 não infla a contagem.

## Páginas

**Visão Geral.** Taxa ICSAP do estado no ano selecionado, total de internações, variação em relação ao ano anterior, evolução da taxa de 2022 a 2025, ranking dos municípios com maior taxa e mapa do PR colorido pela taxa (quanto mais escuro, maior). É a página para identificar onde está o problema.

**Fatores.** Gráficos de dispersão da taxa ICSAP contra proporção de idosos, renda domiciliar mediana, água pela rede, esgoto adequado e esgoto pela rede, com linha de tendência. Cada ponto é um município. As variáveis do IBGE são do Censo 2022 e se repetem nos anos seguintes. A página mostra que o perfil socioeconômico explica pouco da taxa, o que reforça o uso do histórico do município para priorizar.

**Deslocamento.** Percentual de internações fora do município de residência, número de municípios sem nenhuma internação ICSAP local, municípios que mais enviam pacientes para outras cidades e municípios que mais recebem. Ao clicar em um município na tabela, o gráfico de barras passa a mostrar para onde vão os pacientes daquele município. Clicar de novo desfaz a seleção.

Cada página tem o seu próprio filtro de ano. Eles não estão sincronizados, então mudar o ano em uma página não muda nas outras.

## Limitações

- Só entram internações pagas pelo SUS e registradas no SIH.
- A base usa os arquivos do SIH do Paraná, que registram apenas internações em hospitais do PR. Residentes do PR internados em outros estados não aparecem, então o deslocamento real é um pouco maior que o mostrado.
- Municípios pequenos têm taxas instáveis: poucas internações a mais mudam bastante a taxa.
- A população de 2023 é interpolada entre o Censo 2022 e a estimativa de 2024 (ver Etapa 2).

## Como abrir

1. Instale o Power BI Desktop (gratuito, apenas Windows, disponível na Microsoft Store).
2. Abra `bi/painel_icsap.pbix`.
3. Se aparecer erro de arquivo não encontrado, o painel está procurando os CSVs no caminho do computador onde foi criado. Vá em **Página Inicial → Transformar dados → Configurações da fonte de dados**, clique em cada fonte, depois em **Alterar fonte**, e aponte para o mesmo arquivo dentro de `dados/processados/` na sua cópia do repositório.
4. Clique em **Atualizar**.
