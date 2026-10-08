# Privacidade e ética

As análises estão em `notebooks/privacidade.ipynb`, que mostra só contagens e nunca linhas individuais.

Mesmo sendo pública, a base de internações não tem nome, CPF nem endereço, mas o `N_AIH` é único em cada linha e identifica a internação. O diagnóstico (CID) é dado de saúde, que a LGPD trata como dado pessoal sensível. Por isso aplicamos minimização: das cerca de 100 colunas do SIH, ficamos com 6, e idade, sexo e CEP ficaram de fora.

O risco de reidentificação existe. 74,2% das internações (491.608) são únicas na combinação município + data + CID, então quem sabe que alguém foi internado num certo dia, numa certa cidade, consegue achar o registro. Na agregação, 12.247 das 29.669 combinações de município × ano × grupo ICSAP (41%) têm menos de 5 casos.

Também há grupos sub-representados: 4 municípios têm menos de 100 internações no período (o menor tem 62), e neles a taxa é instável. Quanto aos vieses, só entram internações pagas pelo SUS, então município com muito plano privado parece ter menos ICSAP do que tem. Só entram moradores do PR internados em hospital do PR, e o CID depende do preenchimento de cada hospital. As variáveis do IBGE são do Censo 2022 e podem não refletir mudanças posteriores, principalmente em municípios que cresceram rápido.

A análise é por município e não serve para avaliar paciente, médico ou hospital individualmente.

## Decisões

1. O CSV registro a registro não é publicado, e o repositório fica privado enquanto ele estiver no histórico.
2. O que for publicado (painel, tabelas, apresentação) é só agregado, com células de menos de 5 casos suprimidas.
3. Em municípios pequenos, as comparações agregam anos ou regiões, ou sinalizam que a taxa é instável.

Esses dados já são públicos no DATASUS. O risco não é vazar algo secreto, e sim facilitar o acesso e o cruzamento, por isso as decisões tratam do que nós publicamos.
