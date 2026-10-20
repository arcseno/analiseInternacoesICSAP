# Etapa 3: desenvolvimento e rastreabilidade da solução

## O problema que o modelo resolve

A decisão que o projeto apoia, definida na Etapa 1, é onde a SESA-PR deve priorizar investimento em atenção básica. Por isso transformamos a pergunta em uma classificação: com os dados disponíveis até o ano anterior, dá para prever quais municípios vão estar entre os 25% de maior taxa ICSAP no ano seguinte? Um município marcado como "alta" vira um alerta para a gestão olhar com prioridade.

A classe "alta" é definida dentro de cada ano (taxa maior ou igual ao percentil 75 daquele ano), porque o que interessa para priorizar é a posição relativa do município, e não um valor fixo. O corte foi de 186 internações por 10 mil habitantes em 2022 e de 219 em 2025. Por construção, cerca de 100 dos 399 municípios são "alta" em cada ano.

## Pipeline

Tudo está em `src/modelagem/pipeline.py`, que parte do `dataset_municipio_ano.csv` gerado na Etapa 2.

Dados: o script lê o CSV e calcula o hash SHA-256 do arquivo. Os 12 primeiros caracteres são a versão dos dados, então qualquer mudança no CSV gera uma versão nova, sem depender de alguém lembrar de renomear o arquivo.

Validação: antes de treinar, o script confere se há 1.995 linhas e 399 municípios, nenhum valor nulo, nenhuma chave município + ano repetida, nenhuma população zero ou negativa, nenhuma taxa negativa e nenhum percentual fora de 0 a 100. Se alguma checagem falhar, o pipeline para.

Preparação: tira 2026, que só vai até julho e não é comparável, e cria o alvo `alta`.

Features: taxa ICSAP do ano anterior (`taxa_lag1`) e de dois anos antes (`taxa_lag2`), proporção de idosos, percentual de água pela rede, percentual de esgoto adequado, renda mediana e logaritmo da população. Deixamos de fora `pct_agua_ligacao_rede` e a renda média, porque têm correlação alta com variáveis que já entraram e só repetiriam informação.

Treinamento: a divisão é temporal. O teste é sempre 2025, e o treino usa só anos anteriores. Uma divisão aleatória misturaria o futuro no treino, e o modelo pareceria melhor do que é na prática, já que na vida real ele sempre prevê um ano que ainda não aconteceu.

Avaliação e registro: calcula as métricas no ano de teste e grava a execução no registro de experimentos.

Testamos três versões de features para ver o que de fato ajuda: v1 só com IBGE e porte (treino 2022 a 2024), v2 adicionando a taxa do ano anterior (treino 2023 e 2024) e v3 adicionando também a de dois anos antes (treino 2024). Os modelos foram Logistic Regression, Decision Tree e Random Forest, todos com semente fixa (42).

## Métricas e por que essas

A métrica principal é o recall da classe "alta": de todos os municípios que de fato ficaram no quartil mais alto, quantos o modelo avisou. No contexto da SESA-PR, deixar de sinalizar um município que precisava de atenção (falso negativo) é o erro mais caro, porque a internação evitável continua acontecendo e ninguém olha para ela. Já um falso alarme custa uma análise a mais da equipe de gestão, que descobre que o município não era prioridade.

Mesmo assim, recall sozinho engana, porque um modelo que marca todos os 399 municípios teria recall de 100% e não ajudaria a priorizar nada. Por isso acompanhamos também a precisão (dos municípios alertados, quantos eram mesmo "alta") e o F1, que equilibra as duas. A AUC mostra se o modelo ordena bem os municípios por risco, independente do limiar de 0,5, o que é útil se a gestão quiser trabalhar com uma lista ordenada em vez de um sim ou não. A acurácia ficou de fora, porque com 75% dos municípios na classe "não alta" um modelo que nunca dá alerta já acertaria 75%.

Para saber se o modelo vale a pena, comparamos com um baseline simples: o município continua "alta" se foi "alta" no ano anterior.

## Registro dos experimentos

Cada execução grava uma linha em `experimentos/registro_experimentos.csv` com número da execução, data e hora, versão dos dados (hash), versão do código (commit do Git), versão das features, algoritmo, parâmetros, anos de treino e teste, tamanho das amostras, limiar, semente, métricas e matriz de confusão. Em `experimentos/runs/run_XXX/` ficam o `run.json`, com a lista exata de colunas usadas, e o modelo treinado (`modelo.joblib`).

| Run | Dados | Features | Modelo | Parâmetros | Precisão | Recall | F1 | AUC |
|---|---|---|---|---|---|---|---|---|
| 001 | 6a5ce9c56854 | - | Baseline (repete ano anterior) | - | 0,83 | 0,83 | 0,83 | - |
| 002 | 6a5ce9c56854 | v1 | Logistic Regression | C=1 | 0,71 | 0,05 | 0,09 | 0,67 |
| 003 | 6a5ce9c56854 | v1 | Decision Tree | max_depth=4 | 0,69 | 0,09 | 0,16 | 0,70 |
| 004 | 6a5ce9c56854 | v1 | Random Forest | n=300, leaf=3, balanced | 0,75 | 0,91 | 0,82 | 0,93 |
| 005 | 6a5ce9c56854 | v2 | Logistic Regression | C=1 | 0,83 | 0,77 | 0,80 | 0,97 |
| 006 | 6a5ce9c56854 | v2 | Decision Tree | max_depth=4 | 0,73 | 0,76 | 0,75 | 0,94 |
| 007 | 6a5ce9c56854 | v2 | Random Forest | n=300, leaf=3, balanced | 0,77 | 0,91 | 0,83 | 0,96 |
| 008 | 6a5ce9c56854 | v3 | Logistic Regression | C=1 | 0,84 | 0,81 | 0,82 | 0,97 |
| 009 | 6a5ce9c56854 | v3 | Decision Tree | max_depth=4 | 0,80 | 0,86 | 0,83 | 0,93 |
| 010 | 6a5ce9c56854 | v3 | Random Forest | n=300, leaf=3, balanced | 0,79 | 0,93 | 0,85 | 0,96 |
| 011 | 6a5ce9c56854 | v3 | Random Forest | n=500, leaf=5, balanced | 0,77 | 0,93 | 0,84 | 0,96 |

Rodamos a grade completa duas vezes do zero e as métricas foram idênticas.

## O que os resultados mostram

O modelo escolhido é o da execução 010 (Random Forest com features v3). Em 2025, dos 100 municípios que ficaram no quartil mais alto, ele avisou 93 e deixou passar 7. O baseline deixou passar 17. Em troca, o modelo deu 25 falsos alarmes, contra 17 do baseline. Considerando que perder um município prioritário é o erro mais caro, essa troca compensa, mas o ganho sobre a regra simples é moderado, e é importante dizer isso.

O resultado mais importante para entender o modelo é que a taxa do ano anterior carrega quase toda a informação. Ela responde por cerca de metade da importância no Random Forest, e as variáveis do IBGE, sozinhas, quase não separam as classes (Logistic Regression com v1 achou só 5 dos 100 municípios). A taxa ICSAP de um município é muito estável de um ano para o outro (correlação de 0,91 entre 2024 e 2025), então o histórico é o melhor preditor.

A execução 004 parece contradizer isso, já que o Random Forest só com IBGE teve recall de 0,91. Mas, como as variáveis do Censo são fixas para cada município, a combinação delas funciona como uma "impressão digital" do município. A árvore aprende "esse município era alto nos anos de treino" sem que saneamento ou renda expliquem alguma coisa. Ou seja, um modelo com métrica boa pode estar aprendendo a coisa errada, e só dá para perceber isso comparando versões, como o registro permite. Por isso não usamos esse modelo para concluir nada sobre fatores socioeconômicos.

## Limitações

O teste é um único ano (2025, 399 municípios), então uma diferença de poucos municípios muda bastante as métricas. As variáveis do IBGE são do Censo 2022 e repetidas nos anos seguintes. O modelo herda os vieses da base descritos na Etapa 2: só entram internações pagas pelo SUS, e municípios pequenos têm taxas instáveis. O modelo serve para priorizar municípios, não para explicar a causa das internações nem para avaliar hospitais ou equipes.

## Como reproduzir

Na raiz do repositório:

```
pip install -r requirements.txt
python src/modelagem/pipeline.py --grade
```

Para rodar um experimento novo, por exemplo um Random Forest com outros parâmetros:

```
python src/modelagem/pipeline.py --modelo rf --features v3 --param n_estimators=1000
```

A execução nova entra no fim do registro com o próximo número, sem apagar as anteriores.
