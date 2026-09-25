# Fontes de Dados

Este documento descreve as bases de dados utilizadas no projeto de análise de Internações
Sensíveis à Atenção Primária (ICSAP) no Paraná: origem, granularidade, justificativa de
inclusão e papel de cada uma na análise.

## 1. Visão geral

O projeto cruza duas famílias de dados:

1. **Dados de saúde (SIH/DATASUS)** — o evento que queremos explicar (internações ICSAP por
   município).
2. **Dados socioeconômicos e demográficos (IBGE/SIDRA)** — os fatores explicativos, usados
   para normalizar o volume bruto de internações e capturar diferenças estruturais entre
   municípios.

A junção das duas famílias depende da correspondência entre os códigos
de município do DATASUS e do IBGE.

---

## 2. Base primária: internações ICSAP (SIH/DATASUS)

**Arquivo:** `internacoes_icsap_pr` (sem duplicações)
**Fonte:** Sistema de Informações Hospitalares do SUS (SIH/DATASUS)
**Granularidade:** internação individual, agregável por município e ano

O volume de internações por condições que, em tese, não
deveriam ocorrer se a atenção primária estivesse funcionando adequadamente (ex: complicações
de diabetes e hipertensão, insuficiência cardíaca, infecções que poderiam ser tratadas antes de
evoluir).

---

## 3. Bases complementares (IBGE/SIDRA)

### 3.1 Tabela 9514 — População residente, por sexo, idade e forma de declaração da idade
**Período:** Censo Demográfico 2022 | **Nível:** município

Traz a distribuição etária completa (idade simples ou faixas). Serve para dois propósitos:

- **Denominador populacional**: internações não podem ser comparadas em número absoluto entre
  municípios de tamanhos muito diferentes, precisa virar taxa (ex.: internações ICSAP por
  10 mil habitantes).
- **Estrutura etária**: a proporção de idosos (60+) é um preditor forte de ICSAP, porque boa
  parte das condições sensíveis (insuficiência cardíaca, diabetes descompensada) concentra-se
  nessa faixa. Sem controlar por isso, um município mais envelhecido pareceria ter
  atenção primária ineficiente apenas por ter mais idosos.

### 3.2 Tabela 6579 — População residente estimada
**Período:** 2024, 2025, 2026 | **Nível:** município

Como o Censo só existe para 2022, essa tabela cobre os anos seguintes com estimativas anuais
oficiais.

*Observação de série: não existe estimativa oficial para 2023 — o IBGE cancelou essa rodada
por estar em transição para o Censo 2022. Isso deixa um espaço de um ano na série de
população, que precisa ser tratado (interpolação entre 2022 e
2024, ou exclusão do ano 2023 da análise temporal).*

### 3.3 Tabela 6803 — Domicílios por forma de abastecimento de água
**Período:** Censo 2022 | **Nível:** município

Percentual de domicílios com ligação à rede geral de água. Proxy de infraestrutura sanitária:
municípios com baixa cobertura têm mais doenças de veiculação hídrica e infecções evitáveis,
que entram na lista de condições ICSAP.

### 3.4 Tabela 6805 — Domicílios por tipo de esgotamento sanitário
**Período:** Censo 2022 | **Nível:** município

Água e esgoto são tratados como duas variáveis
separadas porque cobertura de um não implica cobertura
do outro, é comum município ter rede de água quase universal e esgotamento sanitário
precário, ou vice-versa.

### 3.5 Tabela 10295 — Rendimento domiciliar per capita (médio e mediano)
**Período:** Censo 2022 | **Nível:** município

O rendimento é usado
como proxy de vulnerabilidade socioeconômica. Populações de renda mais baixa têm menor acesso
a plano de saúde privado e maior dependência da rede pública, o que tende a aumentar o volume
de internações evitáveis quando a atenção primária pública é insuficiente. Usar mediana junto
com a média ajuda a reduzir a distorção que outliers de renda alta causam em municípios
pequenos.

### 3.6 Tabela de correspondência de códigos de município (IBGE ↔ DATASUS)
**Arquivo bruto:** `RELATORIO_DTB_BRASIL_MUNICIPIO.xls`
**Fonte:** IBGE — Banco de Estruturas Territoriais / Divisão Territorial Brasileira

O DATASUS usa um código de município de 6 dígitos, enquanto o IBGE usa 7 dígitos (os mesmos 6 dígitos + 1 dígito verificador no final). 

Para o projeto, o arquivo bruto irá ser processado para filtrar apenas os 399 municípios do Paraná e derivar uma nova coluna sem o dígito verificador (gerando o arquivo tratado `municipios_pr.csv`). Essa tabela de correspondência é o que permitirá fazer o `JOIN` entre a base de internações e todas as bases do IBGE citadas acima, sem gerar valores nulos por incompatibilidade de chave.

---

## 4. Como as variáveis serão combinadas

Estrutura de dados final: uma linha por (município, ano), com:

- `internacoes_icsap` (contagem, de `internacoes_icsap_pr`)
- `populacao` (de 9514 para 2022, de 6579 para 2024–2026)
- `taxa_icsap = internacoes_icsap / populacao * 10000`
- `proporcao_idosos` (derivada de 9514, fixa em 2022 — ver limitação abaixo)
- `pct_agua_rede`, `pct_esgoto_adequado` (de 6803/6805, fixos em 2022)
- `renda_domiciliar_media`, `renda_domiciliar_mediana` (de 10295, fixas em 2022)

**As variáveis 9514, 6803, 6805 e 10295 são fotografias únicas de 2022**, enquanto internações e
população têm variação ano a ano. Isso significa que, para 2024–2026, estamos assumindo que
estrutura etária, saneamento e renda dos municípios não mudaram desde 2022, o que é uma limitação devido a característica dos dados.**