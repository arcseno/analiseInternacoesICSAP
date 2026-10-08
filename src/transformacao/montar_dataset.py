from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

# Configuracoes de entrada/saida
ARQ = {
    "municipios":  "dados/processados/municipios_pr.csv",
    "internacoes": "dados/processados/internacoes_icsap_pr.csv.gz",
    "t9514":       "dados/brutos/tabela9514.csv",
    "t6579":       "dados/brutos/tabela6579.csv",
    "t6803":       "dados/brutos/tabela6803.csv",
    "t6805":       "dados/brutos/tabela6805.csv",
    "t10295":      "dados/brutos/tabela10295.csv",
}
SAIDA_CSV = "dados/processados/dataset_municipio_ano.csv"
SAIDA_EVID = "docs/etapa2/evidencias_qualidade"   # gera .json e .md

DELIM = ","
ANOS = [2022, 2023, 2024, 2025, 2026]
ANO_CENSO, ANO_SEM_ESTIMATIVA, ANO_PARCIAL = 2022, 2023, 2026

ALIASES: dict[str, str] = {}


AGUA_REDE_PRINCIPAL = "Possui ligação à rede geral e a utiliza como forma principal"
AGUA_REDE_OUTRA = "Possui ligação à rede geral, mas utiliza principalmente outra forma"
AGUA_SEM_REDE = "Não possui ligação com a rede geral"
# 6805: "Rede geral ou pluvial" e "Fossa ... ligada à rede" sao detalhamento da 1ª categoria
ESG_REDE = "Rede geral, rede pluvial ou fossa ligada à rede"
ESG_SUBITENS = ["Rede geral ou pluvial", "Fossa séptica ou fossa filtro ligada à rede"]
ESG_FOSSA_SEPTICA_NAO_LIGADA = "Fossa séptica ou fossa filtro não ligada à rede"  # conta como adequado


# Utilitarios de leitura/normalizacao de CSV do SIDRA

def _decodificar(caminho: Path) -> str:
    bruto = caminho.read_bytes()
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return bruto.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Não consegui decodificar {caminho}")


def _k(s: str) -> str:
    """Chave de comparação de rótulos: NFC + casefold + espaços."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip().casefold()


def _norm(s: str) -> str:
    """Normaliza nome de município: sem '(PR)', sem acento/pontuação, minúsculo."""
    s = re.sub(r"\s*\(PR\)\s*$", "", s.strip())
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]", "", s)
    return ALIASES.get(s, s)


def _num(v: str) -> float:
    v = v.strip()
    if v == "-":                 # zero absoluto (legenda do SIDRA)
        return 0.0
    try:
        return float(v.replace(",", "."))
    except ValueError:           # 'X', '..', '...', letras A-E, vazio
        return np.nan


def _eh_linha_de_dado(c0: str) -> bool:
    c = c0.strip()
    return bool(re.search(r"\(PR\)$", c)) or bool(re.fullmatch(r"41\d{5}", c))


# Leitura de CSV do SIDRA

def _parse_bloco(linhas: list[list[str]], origem: str) -> pd.DataFrame:
    variavel = next((r[0] for r in linhas if len(r) == 1 and r[0].startswith("Variável")), "")
    i0 = next((i for i, r in enumerate(linhas) if r and _eh_linha_de_dado(r[0])), None)
    if i0 is None:
        raise ValueError(f"{origem}: nenhuma linha de dado encontrada (esperava 'Nome (PR)' ou código 41xxxxx).")
    cab = [r for r in linhas[:i0] if len(r) > 1]
    ncol = len(cab[-1])
    n_id = 0
    for j in range(ncol):
        if len({r[j] for r in cab if len(r) > j}) == 1:
            n_id += 1
        else:
            break
    nomes_id = cab[-1][:n_id]
    niveis = []
    for r in cab[1:]:
        niveis.append(r[n_id:] if len(r) == ncol else [r[n_id]] * (ncol - n_id))

    reg = []
    for r in linhas[i0:]:
        if not r or not _eh_linha_de_dado(r[0]):
            continue
        r = r + [""] * (ncol - len(r))
        ids = dict(zip(nomes_id, r[:n_id]))
        for j in range(n_id, ncol):
            d = dict(ids)
            d["variavel"] = variavel
            for m, nv in enumerate(niveis, start=1):
                d[f"nivel_{m}"] = nv[j - n_id]
            d["rotulo"] = niveis[-1][j - n_id]
            d["valor_bruto"] = r[j]
            reg.append(d)
    return pd.DataFrame(reg)


def ler_sidra(caminho: str | Path) -> pd.DataFrame:
    p = Path(caminho)
    if not p.exists():
        sys.exit(f"[ERRO] Arquivo não encontrado: {p}")
    linhas = list(csv.reader(io.StringIO(_decodificar(p)), delimiter=DELIM))
    blocos, atual = [], None
    for r in linhas:
        if len(r) == 1 and r[0].startswith("Tabela "):
            atual = []
            blocos.append(atual)
        elif atual is not None:
            atual.append(r)
    if not blocos:
        raise ValueError(f"{p.name}: não achei a linha de título 'Tabela ...'.")
    df = pd.concat([_parse_bloco(b, p.name) for b in blocos], ignore_index=True)
    df["valor"] = df["valor_bruto"].map(_num)
    n_nan = int(df["valor"].isna().sum())
    if n_nan:
        print(f"  [aviso] {p.name}: {n_nan} células sem valor numérico (X, .., ...) -> NaN")
    df.attrs["n_nan"] = n_nan
    return df


def anexar_cod7(df: pd.DataFrame, mun: pd.DataFrame) -> pd.DataFrame:
    c_cod = next((c for c in df.columns if re.match(r"^c[oó]d", c, re.I)), None)
    if c_cod:
        df["cod7"] = df[c_cod].str.strip()
    else:
        mapa = dict(zip(mun["nome_municipio"].map(_norm), mun["cod_municipio_ibge"]))
        if len(mapa) != len(mun):
            sys.exit("[ERRO] nomes de município colidem após normalização; use ALIASES")
        df["cod7"] = df["Município"].map(lambda s: mapa.get(_norm(s)))
        nao = sorted(df.loc[df["cod7"].isna(), "Município"].unique())
        if nao:
            sys.exit(f"[ERRO] {len(nao)} nomes sem correspondência em municipios_pr.csv: {nao[:10]} ... "
                     "Ajuste ALIASES no topo do script")
    return df


def _wide(df: pd.DataFrame, colunas: str = "rotulo") -> pd.DataFrame:
    return df.pivot_table(index="cod7", columns=colunas, values="valor", aggfunc="first", dropna=False)


def _col(w: pd.DataFrame, rotulo: str) -> pd.Series:
    por_k = {_k(c): c for c in w.columns}
    if _k(rotulo) not in por_k:
        raise ValueError(f"Coluna '{rotulo}' não existe. Colunas: {list(w.columns)}")
    return w[por_k[_k(rotulo)]]


def _soma(*series: pd.Series) -> pd.Series:
    return pd.concat(series, axis=1).sum(axis=1, skipna=False)


def inspecionar():
    for k, v in ARQ.items():
        print(f"\n=== {k}: {v}")
        p = Path(v)
        if not p.exists():
            print("   (não encontrado)")
            continue
        if k in ("municipios", "internacoes"):
            print(pd.read_csv(p, sep=";" if k == "internacoes" else None, engine="python", nrows=3, dtype=str).to_string())
        else:
            print("\n".join(_decodificar(p).splitlines()[:8]))


# Tabelas

RE_FAIXA = r"^(\d+) a (\d+) anos$"
RE_MAIS = r"^(\d+) anos ou mais$"


def tab_9514(df: pd.DataFrame, mun: pd.DataFrame):
    """População total do Censo 2022 = SOMA das faixas (a tabela exportada não tem coluna 'Total')."""
    df = anexar_cod7(df, mun)
    if "Forma de declaração da idade" in df:
        df = df[df["Forma de declaração da idade"].map(_k) == "total"]
    df = df[(df["nivel_1"] == "2022") & (df["nivel_2"].map(_k) == "total")]
    if df.empty:
        raise ValueError("9514: sem linhas para ano=2022 e sexo=Total. Confira o layout (--inspecionar).")
    w = _wide(df)
    inicio = {}
    for c in w.columns:
        lab = _k(c)
        m = re.match(RE_FAIXA, lab)
        m2 = re.match(RE_MAIS, lab)
        if m:
            inicio[c] = int(m.group(1))
        elif m2 and int(m2.group(1)) == 100:
            inicio[c] = 100
        else:
            raise ValueError(f"9514: rótulo de idade inesperado: '{c}' (esperado faixas quinquenais e '100 anos ou mais')")
    esperado = set(range(0, 100, 5)) | {100}
    if set(inicio.values()) != esperado:
        raise ValueError(f"9514: faixas incompletas: {sorted(set(inicio.values()))}")
    total = w.sum(axis=1, skipna=False)
    idosos = w[[c for c, i in inicio.items() if i >= 60]].sum(axis=1, skipna=False)
    out = pd.DataFrame({"pop_censo_2022": total, "proporcao_idosos": idosos / total}).reset_index()
    return out, {"9514_municipios_com_faixa_sem_valor": int(total.isna().sum())}


def tab_6579(df: pd.DataFrame, mun: pd.DataFrame) -> pd.DataFrame:
    df = anexar_cod7(df, mun)
    out = df.assign(ano=pd.to_numeric(df["rotulo"], errors="coerce"))[["cod7", "ano", "valor"]].dropna(subset=["ano"])
    out = out.astype({"ano": int}).rename(columns={"valor": "pop_estimada"})
    return out[out["ano"].isin(ANOS)]


def tab_6803(df: pd.DataFrame, mun: pd.DataFrame):
    df = anexar_cod7(df, mun)
    df = df[df["nivel_1"] == "2022"]
    w = _wide(df)
    topo = [c for c in w.columns if " - " not in c]
    esperado = {_k(AGUA_REDE_PRINCIPAL), _k(AGUA_REDE_OUTRA), _k(AGUA_SEM_REDE)}
    if {_k(c) for c in topo} != esperado:
        raise ValueError(f"6803: categorias de topo inesperadas: {topo}")
    principal, outra, sem = _col(w, AGUA_REDE_PRINCIPAL), _col(w, AGUA_REDE_OUTRA), _col(w, AGUA_SEM_REDE)
    total = _soma(principal, outra, sem)
    # consistência interna: pai == soma dos detalhamentos
    n_div = 0
    for pai in (AGUA_REDE_OUTRA, AGUA_SEM_REDE):
        filhos = [c for c in w.columns if _k(c).startswith(_k(pai) + " - ")]
        n_div += int(((w[filhos].sum(axis=1, skipna=False) - _col(w, pai)).abs() > 0.5).sum())
    out = pd.DataFrame({
        "pct_agua_rede": 100 * principal / total,               # rede geral como principal fonte
        "pct_agua_ligacao_rede": 100 * (principal + outra) / total,  # tem ligação (mesmo que use outra fonte)
        "dom_total_6803": total}).reset_index()
    return out, {"6803_pai_diferente_da_soma_dos_detalhes": n_div}


def tab_6805(df: pd.DataFrame, mun: pd.DataFrame):
    df = anexar_cod7(df, mun)
    df = df[df["nivel_1"] == "2022"]
    w = _wide(df)
    rede = _col(w, ESG_REDE)
    nao_lig = _col(w, ESG_FOSSA_SEPTICA_NAO_LIGADA)
    sub = {_k(s) for s in ESG_SUBITENS}
    topo = [c for c in w.columns if _k(c) not in sub]
    total = _soma(*[w[c] for c in topo])
    n_div = int(((_soma(*[_col(w, s) for s in ESG_SUBITENS]) - rede).abs() > 0.5).sum())
    out = pd.DataFrame({
        "pct_esgoto_rede": 100 * rede / total,
        "pct_esgoto_adequado": 100 * (rede + nao_lig) / total,
        "dom_total_6805": total}).reset_index()
    return out, {"6805_pai_diferente_da_soma_dos_detalhes": n_div}


def tab_10295(df: pd.DataFrame, mun: pd.DataFrame) -> pd.DataFrame:
    df = anexar_cod7(df, mun)
    v = df["variavel"].str.lower()
    if v.str.contains("percentual").any():
        raise ValueError("10295: variável 'percentual do total' detectada. Exporte rendimento médio e mediano (Reais).")
    df = df.assign(medida=np.where(v.str.contains("mediano"), "renda_domiciliar_mediana",
                           np.where(v.str.contains("m[eé]dio"), "renda_domiciliar_media", "")))
    if (df["medida"] == "").any():
        raise ValueError(f"10295: variável não reconhecida: {df.loc[df['medida'] == '', 'variavel'].iloc[0]}")
    df = df[(df["Grupo de idade"].map(_k) == "total") & (df["nivel_1"] == "2022")
            & (df["nivel_2"].map(_k) == "total") & (df["nivel_3"].map(_k) == "total")]
    out = df.pivot_table(index="cod7", columns="medida", values="valor", aggfunc="first", dropna=False).reset_index()
    if {"renda_domiciliar_media", "renda_domiciliar_mediana"} - set(out.columns):
        raise ValueError("10295: faltou média ou mediana no arquivo.")
    return out


# Internações ICSAP (SIH/DATASUS) e municípios do PR

def ler_municipios(caminho: str) -> pd.DataFrame:
    df = pd.read_csv(caminho, sep=None, engine="python", dtype=str)
    c7 = next((c for c in df.columns if df[c].str.fullmatch(r"\d{7}").all()), None)
    c6 = next((c for c in df.columns if df[c].str.fullmatch(r"\d{6}").all()), None)
    if not c7:
        sys.exit(f"[ERRO] municipios_pr.csv sem coluna de 7 dígitos (IBGE). Colunas: {list(df.columns)}")
    if not c6:
        c6 = "_cod6"
        df[c6] = df[c7].str[:6]
    nome = next((c for c in df.columns if re.search(r"nome|munic", c, re.I) and c not in (c6, c7)), None)
    if not nome:
        sys.exit(f"[ERRO] municipios_pr.csv sem coluna de nome. Colunas: {list(df.columns)}")
    out = df.rename(columns={c7: "cod_municipio_ibge", c6: "cod_municipio_datasus", nome: "nome_municipio"})
    out = out[["cod_municipio_datasus", "cod_municipio_ibge", "nome_municipio"]]
    assert out["cod_municipio_datasus"].is_unique and out["cod_municipio_ibge"].is_unique
    assert (out["cod_municipio_ibge"].str[:6] == out["cod_municipio_datasus"]).all(), "regra de truncamento violada"
    return out


def contar_internacoes(caminho: str) -> tuple[pd.DataFrame, int]:
    # DT_INTER vem como AAAAMMDD (ex.: 20220108): ler como TEXTO, senão vira inteiro e a data quebra.
    df = pd.read_csv(caminho, sep=";", dtype=str, usecols=["N_AIH", "MUNIC_RES", "DT_INTER"])
    d = df["DT_INTER"].str.strip().str.replace("-", "", regex=False)
    data = pd.to_datetime(d, format="%Y%m%d", errors="coerce")
    if data.isna().any():
        sys.exit(f"[ERRO] {int(data.isna().sum())} DT_INTER inválidas")
    cont = (df.assign(ano=data.dt.year.astype(int)).groupby(["MUNIC_RES", "ano"]).size()
              .rename("internacoes_icsap").reset_index()
              .rename(columns={"MUNIC_RES": "cod_municipio_datasus"}))
    return cont, len(df)


# Montagem do dataset final

def montar(raiz: Path):
    P = lambda k: str(raiz / ARQ[k])
    print("Lendo municípios e internações...")
    mun = ler_municipios(P("municipios"))
    cont, n_linhas_fonte = contar_internacoes(P("internacoes"))

    print("Lendo IBGE...")
    chk: dict = {}
    pop_censo, i = tab_9514(ler_sidra(P("t9514")), mun); chk.update(i)
    pop_est = tab_6579(ler_sidra(P("t6579")), mun)
    agua, i = tab_6803(ler_sidra(P("t6803")), mun); chk.update(i)
    esgoto, i = tab_6805(ler_sidra(P("t6805")), mun); chk.update(i)
    renda = tab_10295(ler_sidra(P("t10295")), mun)

    # cada tabela deve ter os 399 municipios
    cod_ok = set(mun["cod_municipio_ibge"])
    for nome, t in [("9514", pop_censo), ("6579", pop_est), ("6803", agua), ("6805", esgoto), ("10295", renda)]:
        chk[f"{nome}_municipios_do_PR_ausentes_na_tabela"] = len(cod_ok - set(t["cod7"]))
    # 6803 e 6805 contam os mesmos domicilios
    dom = agua[["cod7", "dom_total_6803"]].merge(esgoto[["cod7", "dom_total_6805"]], on="cod7")
    chk["total_domicilios_6803_diferente_de_6805"] = int((dom["dom_total_6803"] != dom["dom_total_6805"]).sum())
    agua, esgoto = agua.drop(columns="dom_total_6803"), esgoto.drop(columns="dom_total_6805")

    # populacao por (municipio, ano)
    p = pop_censo[["cod7", "pop_censo_2022"]].rename(columns={"cod7": "cod_municipio_ibge"})
    est = (pop_est.pivot(index="cod7", columns="ano", values="pop_estimada").add_prefix("pop_")
           .reset_index().rename(columns={"cod7": "cod_municipio_ibge"}))
    p = p.merge(est, on="cod_municipio_ibge", how="outer")
    linhas = []
    for _, r in p.iterrows():
        pe = r.get("pop_2024")
        interp = np.sqrt(r["pop_censo_2022"] * pe) if pd.notna(r["pop_censo_2022"]) and pd.notna(pe) else np.nan
        linhas += [(r["cod_municipio_ibge"], ANO_CENSO, r["pop_censo_2022"], "censo_2022"),
                   (r["cod_municipio_ibge"], ANO_SEM_ESTIMATIVA, interp, "interpolada_geometrica_2022_2024")]
        linhas += [(r["cod_municipio_ibge"], a, r.get(f"pop_{a}"), "estimativa_ibge")
                   for a in ANOS if a not in (ANO_CENSO, ANO_SEM_ESTIMATIVA)]
    pop = pd.DataFrame(linhas, columns=["cod_municipio_ibge", "ano", "populacao", "populacao_origem"])
    razao = (p["pop_2024"] / p["pop_censo_2022"])
    chk["pop_2024_sobre_censo_2022_fora_de_0.85_1.25"] = int(((razao < 0.85) | (razao > 1.25)).sum())

    # grade completa municipio x ano
    grade = mun.merge(pd.DataFrame({"ano": ANOS}), how="cross")
    ds = grade.merge(cont, on=["cod_municipio_datasus", "ano"], how="left", indicator="_m")
    n_zero = int((ds["_m"] == "left_only").sum())
    ds["internacoes_icsap"] = ds["internacoes_icsap"].fillna(0).astype(int)
    ds = ds.drop(columns="_m")
    ds = ds.merge(pop, on=["cod_municipio_ibge", "ano"], how="left")
    estat = (pop_censo[["cod7", "proporcao_idosos"]].merge(agua, on="cod7", how="outer")
             .merge(esgoto, on="cod7", how="outer").merge(renda, on="cod7", how="outer")
             .rename(columns={"cod7": "cod_municipio_ibge"}))
    ds = ds.merge(estat, on="cod_municipio_ibge", how="left")
    ds["taxa_icsap"] = ds["internacoes_icsap"] / ds["populacao"] * 10_000
    ds["ano_parcial"] = ds["ano"] == ANO_PARCIAL

    ordem = ["cod_municipio_datasus", "cod_municipio_ibge", "nome_municipio", "ano", "ano_parcial",
             "internacoes_icsap", "populacao", "populacao_origem", "taxa_icsap", "proporcao_idosos",
             "pct_agua_rede", "pct_agua_ligacao_rede", "pct_esgoto_rede", "pct_esgoto_adequado",
             "renda_domiciliar_media", "renda_domiciliar_mediana"]
    ds = ds[ordem].sort_values(["cod_municipio_ibge", "ano"]).reset_index(drop=True)
    return ds, dict(n_linhas_fonte=n_linhas_fonte, n_preenchidos_zero=n_zero, n_mun_fonte=len(mun), checagens=chk)


# Evidencias de qualidade do dataset

def evidencias(ds: pd.DataFrame, ctx: dict) -> dict:
    ok = ds[~ds["ano_parcial"]]
    pcts = ["pct_agua_rede", "pct_agua_ligacao_rede", "pct_esgoto_rede", "pct_esgoto_adequado"]
    return {
        "n_linhas": len(ds),
        "n_linhas_esperado_(municipios x anos)": ctx["n_mun_fonte"] * len(ANOS),
        "n_municipios": int(ds["cod_municipio_ibge"].nunique()),
        "chave_municipio_ano_duplicada": int(ds.duplicated(["cod_municipio_ibge", "ano"]).sum()),
        "linhas_municipio_ano_preenchidas_com_zero": ctx["n_preenchidos_zero"],
        "populacao_nao_positiva": int((ds["populacao"] <= 0).sum()),
        "populacao_interpolada_linhas": int(ds["populacao_origem"].str.startswith("interp").sum()),
        "proporcao_idosos_fora_de_0_1": int(((ds["proporcao_idosos"] < 0) | (ds["proporcao_idosos"] > 1)).sum()),
        "renda_negativa": int((ds[["renda_domiciliar_media", "renda_domiciliar_mediana"]] < 0).sum().sum()),
        "renda_mediana_maior_que_media_(municipios)": int((ds.drop_duplicates("cod_municipio_ibge")
                                                       .eval("renda_domiciliar_mediana > renda_domiciliar_media")).sum()),
        "esgoto_adequado_menor_que_rede": int((ds["pct_esgoto_adequado"] < ds["pct_esgoto_rede"] - 1e-9).sum()),
        "agua_ligacao_menor_que_rede_principal": int((ds["pct_agua_ligacao_rede"] < ds["pct_agua_rede"] - 1e-9).sum()),
        "municipio_ano_com_menos_de_10_internacoes_(2022-2025)": int((ok["internacoes_icsap"] < 10).sum()),
        "municipio_ano_sem_internacao_(2022-2025)": int((ok["internacoes_icsap"] == 0).sum()),
        "reconciliacao_internacoes": {
            "linhas_base_tratada": ctx["n_linhas_fonte"],
            "soma_no_dataset_analitico": int(ds["internacoes_icsap"].sum()),
            "confere": bool(ctx["n_linhas_fonte"] == ds["internacoes_icsap"].sum())},
        "pct_fora_de_0_100": {c: int(((ds[c] < 0) | (ds[c] > 100)).sum()) for c in pcts},
        "completude_pct_ausente": {c: round(100 * ds[c].isna().mean(), 2) for c in ds.columns},
        "taxa_icsap_2022_2025": ok["taxa_icsap"].describe().round(2).to_dict(),
        "checagens_tabelas_ibge": ctx["checagens"],
    }


def gravar_evidencias(ev: dict, destino: Path):
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.with_suffix(".json").write_text(json.dumps(ev, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md = ["# Evidências de qualidade: dataset analítico (município × ano)\n"]
    md += [f"- {k}: **{v}**" for k, v in ev.items() if not isinstance(v, dict)]
    for k, v in ev.items():
        if isinstance(v, dict):
            md.append(f"\n## {k}\n")
            md += [f"- {kk}: **{vv}**" for kk, vv in v.items()]
    destino.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=".", help="raiz do repositório")
    ap.add_argument("--inspecionar", action="store_true")
    a = ap.parse_args()
    raiz = Path(a.raiz).resolve()
    if a.inspecionar:
        import os
        os.chdir(raiz)
        inspecionar()
        return
    ds, ctx = montar(raiz)
    ev = evidencias(ds, ctx)
    saida = raiz / SAIDA_CSV
    saida.parent.mkdir(parents=True, exist_ok=True)
    ds.to_csv(saida, sep=";", index=False, encoding="utf-8")
    gravar_evidencias(ev, raiz / SAIDA_EVID)
    print(f"\nOK: {len(ds)} linhas -> {saida}")
    print(json.dumps({k: ev[k] for k in ["n_linhas", "n_linhas_esperado_(municipios x anos)",
          "chave_municipio_ano_duplicada", "reconciliacao_internacoes", "checagens_tabelas_ibge"]},
          ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()