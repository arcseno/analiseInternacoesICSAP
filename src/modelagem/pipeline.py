"""
Etapa 3: pipeline de modelagem com registro de experimentos.

Pergunta do modelo: com os dados até o ano t-1, dá para prever quais municípios
do PR vão estar entre os 25% de maior taxa ICSAP no ano t?

Etapas: dados -> validação -> preparação -> features -> treinamento -> avaliação -> registro

Uso (a partir da raiz do repositório):
    python src/modelagem/pipeline.py --grade                      # roda todos os experimentos planejados
    python src/modelagem/pipeline.py --modelo rf --features v3 --param n_estimators=500
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

# Configurações

RAIZ = Path(__file__).resolve().parents[2]
ARQ_DADOS = RAIZ / "dados/processados/dataset_municipio_ano.csv"
PASTA_EXP = RAIZ / "experimentos"
ARQ_REGISTRO = PASTA_EXP / "registro_experimentos.csv"

SEMENTE = 42
QUANTIL_ALTA = 0.75        # "alta" = taxa no quartil superior do próprio ano
ANO_TESTE = 2025           # último ano completo. 2026 é parcial e fica fora
LIMIAR = 0.5               # probabilidade a partir da qual o município é marcado como alerta

IBGE = ["proporcao_idosos", "pct_agua_rede", "pct_esgoto_adequado",
        "renda_domiciliar_mediana", "log_populacao"]

# Cada versão de features define também quais anos podem ser usados no treino,
# porque as defasagens precisam de anos anteriores disponíveis.
FEATURES = {
    "v1": {"colunas": IBGE, "anos_treino": [2022, 2023, 2024],
           "descricao": "só variáveis do IBGE (Censo 2022) e porte do município"},
    "v2": {"colunas": IBGE + ["taxa_lag1"], "anos_treino": [2023, 2024],
           "descricao": "IBGE + taxa ICSAP do ano anterior"},
    "v3": {"colunas": IBGE + ["taxa_lag1", "taxa_lag2"], "anos_treino": [2024],
           "descricao": "IBGE + taxa dos dois anos anteriores"},
}

MODELOS = {
    "logreg": ("Logistic Regression",
               lambda p: make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=SEMENTE, **p)),
               {"C": 1.0}),
    "arvore": ("Decision Tree",
               lambda p: DecisionTreeClassifier(random_state=SEMENTE, **p),
               {"max_depth": 4}),
    "rf": ("Random Forest",
           lambda p: RandomForestClassifier(random_state=SEMENTE, n_jobs=1, **p),
           {"n_estimators": 300, "min_samples_leaf": 3, "class_weight": "balanced"}),
}

# Experimentos planejados (--grade)
GRADE = [
    ("baseline", "v2", {}),
    ("logreg", "v1", {}), ("arvore", "v1", {}), ("rf", "v1", {}),
    ("logreg", "v2", {}), ("arvore", "v2", {}), ("rf", "v2", {}),
    ("logreg", "v3", {}), ("arvore", "v3", {}), ("rf", "v3", {}),
    ("rf", "v3", {"n_estimators": 500, "min_samples_leaf": 5}),
]


# 1. Dados

def hash_arquivo(caminho: Path) -> str:
    """Versão dos dados = primeiros 12 caracteres do SHA-256 do arquivo.
    Se qualquer valor do CSV mudar, a versão muda."""
    return hashlib.sha256(caminho.read_bytes()).hexdigest()[:12]


def versao_codigo() -> str:
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ,
                                capture_output=True, text=True, check=True).stdout.strip()
        sujo = subprocess.run(["git", "status", "--porcelain", "src/"], cwd=RAIZ,
                              capture_output=True, text=True).stdout.strip()
        return commit + ("-modificado" if sujo else "")
    except Exception:
        return "sem_git"


def carregar() -> pd.DataFrame:
    return pd.read_csv(ARQ_DADOS, sep=";", dtype={"cod_municipio_ibge": str, "cod_municipio_datasus": str})


# 2. Validação: se algo falhar, o pipeline para antes de treinar

def validar(df: pd.DataFrame) -> dict:
    esperadas = {"cod_municipio_ibge", "ano", "ano_parcial", "internacoes_icsap", "populacao",
                 "taxa_icsap", "proporcao_idosos", "pct_agua_rede", "pct_esgoto_adequado",
                 "renda_domiciliar_mediana"}
    faltando = esperadas - set(df.columns)
    assert not faltando, f"colunas ausentes: {faltando}"
    checagens = {
        "linhas": len(df),
        "municipios": df["cod_municipio_ibge"].nunique(),
        "nulos": int(df[list(esperadas)].isna().sum().sum()),
        "chave_duplicada": int(df.duplicated(["cod_municipio_ibge", "ano"]).sum()),
        "populacao_nao_positiva": int((df["populacao"] <= 0).sum()),
        "taxa_negativa": int((df["taxa_icsap"] < 0).sum()),
        "pct_fora_0_100": int(((df[["pct_agua_rede", "pct_esgoto_adequado"]] < 0) |
                               (df[["pct_agua_rede", "pct_esgoto_adequado"]] > 100)).sum().sum()),
    }
    assert checagens["linhas"] == 1995 and checagens["municipios"] == 399, checagens
    for k in ["nulos", "chave_duplicada", "populacao_nao_positiva", "taxa_negativa", "pct_fora_0_100"]:
        assert checagens[k] == 0, f"validação falhou: {k} = {checagens[k]}"
    return checagens


# 3. Preparação: tira o ano parcial e cria o alvo

def preparar(df: pd.DataFrame) -> pd.DataFrame:
    df = df[~df["ano_parcial"]].copy()     # 2026 só tem até julho, não é comparável
    corte = df.groupby("ano")["taxa_icsap"].transform(lambda s: s.quantile(QUANTIL_ALTA))
    df["alta"] = (df["taxa_icsap"] >= corte).astype(int)
    return df.sort_values(["cod_municipio_ibge", "ano"]).reset_index(drop=True)


# 4. Features

def criar_features(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("cod_municipio_ibge")
    df["taxa_lag1"] = g["taxa_icsap"].shift(1)
    df["taxa_lag2"] = g["taxa_icsap"].shift(2)
    df["alta_lag1"] = g["alta"].shift(1)       # usado só pelo baseline
    df["log_populacao"] = np.log(df["populacao"])
    return df


# 5 e 6. Treinamento e avaliação

def metricas(y, pred, prob=None) -> dict:
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "precision": round(precision_score(y, pred, zero_division=0), 4),
        "recall": round(recall_score(y, pred), 4),
        "f1": round(f1_score(y, pred), 4),
        "auc": round(roc_auc_score(y, prob), 4) if prob is not None else None,
        "vp": int(tp), "fp": int(fp), "fn": int(fn), "vn": int(tn),
    }


def rodar(df: pd.DataFrame, chave_modelo: str, versao_feat: str, params_extra: dict, ctx: dict) -> dict:
    cfg = FEATURES[versao_feat]
    teste = df[df["ano"] == ANO_TESTE]

    if chave_modelo == "baseline":
        # Regra ingênua: o município continua "alto" se foi "alto" no ano anterior.
        nome, params, modelo = "Baseline (repete ano anterior)", {}, None
        anos_treino = []
        res = metricas(teste["alta"], teste["alta_lag1"].astype(int))
        n_treino = 0
    else:
        nome, construtor, params = MODELOS[chave_modelo]
        params = {**params, **params_extra}
        anos_treino = cfg["anos_treino"]
        treino = df[df["ano"].isin(anos_treino)].dropna(subset=cfg["colunas"])
        modelo = construtor(params).fit(treino[cfg["colunas"]], treino["alta"])
        prob = modelo.predict_proba(teste[cfg["colunas"]])[:, 1]
        res = metricas(teste["alta"], (prob >= LIMIAR).astype(int), prob)
        n_treino = len(treino)

    run_id = proximo_run_id()
    registro = {
        "run": run_id,
        "data_execucao": datetime.now().isoformat(timespec="seconds"),
        "versao_dados": ctx["versao_dados"],
        "versao_codigo": ctx["versao_codigo"],
        "features": versao_feat if modelo is not None else "-",
        "modelo": nome,
        "parametros": json.dumps(params, sort_keys=True),
        "anos_treino": "-".join(map(str, anos_treino)) or "-",
        "ano_teste": ANO_TESTE,
        "n_treino": n_treino,
        "n_teste": len(teste),
        "limiar": LIMIAR if modelo is not None else "-",
        "semente": SEMENTE,
        **res,
    }
    salvar(registro, modelo, cfg if modelo is not None else None)
    return registro


# Registro dos experimentos

def proximo_run_id() -> str:
    if not ARQ_REGISTRO.exists():
        return "001"
    return f"{len(pd.read_csv(ARQ_REGISTRO)) + 1:03d}"


def salvar(reg: dict, modelo, cfg: dict | None):
    PASTA_EXP.mkdir(exist_ok=True)
    pd.DataFrame([reg]).to_csv(ARQ_REGISTRO, mode="a", header=not ARQ_REGISTRO.exists(), index=False)
    pasta_run = PASTA_EXP / "runs" / f"run_{reg['run']}"
    pasta_run.mkdir(parents=True, exist_ok=True)
    detalhes = {**reg, "parametros": json.loads(reg["parametros"]),
                "colunas_features": cfg["colunas"] if cfg else ["alta_lag1"],
                "descricao_features": cfg["descricao"] if cfg else "regra: repete a classe do ano anterior",
                "arquivo_dados": str(ARQ_DADOS.relative_to(RAIZ))}
    (pasta_run / "run.json").write_text(json.dumps(detalhes, ensure_ascii=False, indent=2), encoding="utf-8")
    if modelo is not None:
        joblib.dump(modelo, pasta_run / "modelo.joblib")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grade", action="store_true", help="roda todos os experimentos planejados")
    ap.add_argument("--modelo", choices=["baseline", *MODELOS])
    ap.add_argument("--features", choices=list(FEATURES), default="v3")
    ap.add_argument("--param", action="append", default=[], help="ex.: --param n_estimators=500")
    a = ap.parse_args()

    df = carregar()
    ctx = {"versao_dados": hash_arquivo(ARQ_DADOS), "versao_codigo": versao_codigo()}
    print(f"Dados: {ARQ_DADOS.name} (versão {ctx['versao_dados']}) | código: {ctx['versao_codigo']}")
    print("Validação:", validar(df))
    df = criar_features(preparar(df))

    if a.grade:
        experimentos = GRADE
    elif a.modelo:
        extra = {k: json.loads(v) if v.replace(".", "").isdigit() or v in ("true", "false") else v
                 for k, v in (p.split("=", 1) for p in a.param)}
        experimentos = [(a.modelo, a.features, extra)]
    else:
        ap.error("use --grade ou --modelo")

    for chave, feat, extra in experimentos:
        r = rodar(df, chave, feat, extra, ctx)
        print(f"run {r['run']} | {r['modelo']:<32} | feat {r['features']:<2} | "
              f"P {r['precision']:.2f} R {r['recall']:.2f} F1 {r['f1']:.2f} AUC {r['auc'] if r['auc'] is not None else '-'}")
    print(f"\nRegistro: {ARQ_REGISTRO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
