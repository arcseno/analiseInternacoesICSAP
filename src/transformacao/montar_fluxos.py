from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

# Configuracoes de entrada/saida
ARQ = {
    "municipios":  "dados/processados/municipios_pr.csv",
    "internacoes": "dados/processados/internacoes_icsap_pr.csv.gz",
}
SAIDA_FLUXOS = "dados/processados/fluxos_municipio_ano.csv"
SAIDA_FORA = "dados/processados/internado_fora_municipio_ano.csv"

ANO_PARCIAL = 2026          # dados só até julho
NOME_FORA_PR = "Outro estado"


def ler_municipios(raiz: Path) -> pd.Series:
    """Mapa codigo_datasus -> nome_municipio (arquivo separado por vírgula)."""
    m = pd.read_csv(raiz / ARQ["municipios"], sep=",", dtype=str)
    return m.set_index("codigo_datasus")["nome_municipio"]


def montar(raiz: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    nomes = ler_municipios(raiz)
    df = pd.read_csv(raiz / ARQ["internacoes"], sep=";", dtype=str,
                     usecols=["MUNIC_RES", "MUNIC_MOV", "DT_INTER"])
    df["ano"] = df["DT_INTER"].str[:4].astype(int)
    df["fora"] = df["MUNIC_RES"] != df["MUNIC_MOV"]

    # Fluxos residência -> internação
    fluxos = (df.groupby(["MUNIC_RES", "MUNIC_MOV", "ano"]).size()
                .reset_index(name="internacoes")
                .rename(columns={"MUNIC_RES": "cod_municipio_datasus",
                                 "MUNIC_MOV": "cod_municipio_internacao"}))
    fluxos.insert(1, "nome_municipio", fluxos["cod_municipio_datasus"].map(nomes))
    fluxos.insert(3, "nome_municipio_internacao",
                  fluxos["cod_municipio_internacao"].map(nomes).fillna(NOME_FORA_PR))
    fluxos.insert(fluxos.columns.get_loc("ano") + 1, "ano_parcial", fluxos["ano"] == ANO_PARCIAL)

    # Internações fora do município de residência
    fora = (df.groupby(["MUNIC_RES", "ano"])
              .agg(internacoes_total=("fora", "size"), internacoes_fora=("fora", "sum"))
              .reset_index()
              .rename(columns={"MUNIC_RES": "cod_municipio_datasus"}))
    fora.insert(1, "nome_municipio", fora["cod_municipio_datasus"].map(nomes))
    fora.insert(3, "ano_parcial", fora["ano"] == ANO_PARCIAL)
    fora["pct_fora"] = 100 * fora["internacoes_fora"] / fora["internacoes_total"]

    sem_nome = fluxos["nome_municipio"].isna().sum()
    if sem_nome:
        print(f"AVISO: {sem_nome} linhas de fluxo com município de residência sem nome")
    return fluxos, fora


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=".", help="raiz do repositório")
    a = ap.parse_args()
    raiz = Path(a.raiz).resolve()

    fluxos, fora = montar(raiz)
    for tab, rel in [(fluxos, SAIDA_FLUXOS), (fora, SAIDA_FORA)]:
        saida = raiz / rel
        saida.parent.mkdir(parents=True, exist_ok=True)
        tab.to_csv(saida, sep=";", decimal=",", index=False, encoding="utf-8")
        print(f"OK: {len(tab)} linhas -> {saida}")

    total, n_fora = fora["internacoes_total"].sum(), fora["internacoes_fora"].sum()
    print(f"Internações fora do município: {n_fora} de {total} "
          f"({100 * n_fora / total:.1f}%)".replace(".", ","))


if __name__ == "__main__":
    main()
