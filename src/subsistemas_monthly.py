"""Compact renewable input for the Subsistemas view, independent of Mapa."""
import pandas as pd

CHAVES = ["din_instante", "id_subsistema", "cod_razaorestricao"]
VALORES = ["val_curtailment", "val_geracao_esperada"]


def compactar_subsistemas(df):
    """Keep half-hour totals and counts, separating nulls and negative values.

    Existing views disagree on which nulls to exclude and clip negatives
    before summing. Keep those strata so each view can apply its own rule.
    """
    base = df[CHAVES + VALORES].copy()
    grupos = CHAVES.copy()
    for coluna in VALORES:
        base[coluna] = pd.to_numeric(base[coluna], errors="coerce")
        chave = f"_{coluna}_classe"
        base[chave] = base[coluna].lt(0).astype("int8").mask(base[coluna].isna(), -1)
        grupos.append(chave)
    agrupado = base.groupby(grupos, observed=True, dropna=False, sort=False)
    resultado = agrupado[VALORES].sum(min_count=1)
    resultado["_registros"] = agrupado.size()
    return resultado.reset_index().drop(columns=grupos[len(CHAVES):])


def preparar_dados_subsistemas(ano_inicial, mes_inicial, ano_final, mes_final, fontes):
    from .leitura_parquet import carregar_periodo_parquet

    if not 2024 <= ano_inicial <= ano_final <= 2026:
        raise ValueError("O histórico disponível abrange somente 2024 a 2026.")
    if not fontes or set(fontes) - {"EOL", "UFV"}:
        raise ValueError("Selecione EOL, UFV ou ambas as fontes.")
    fontes = tuple(dict.fromkeys(fontes))
    inicio = pd.Period(year=ano_inicial, month=mes_inicial, freq="M")
    fim = pd.Period(year=ano_final, month=mes_final, freq="M")
    partes = []
    registros = 0
    for mes in pd.period_range(inicio, fim, freq="M"):
        for fonte in fontes:
            dados, _ = carregar_periodo_parquet(fonte, mes.year, mes.month, mes.month)
            if not dados.empty:
                registros += len(dados)
                partes.append(compactar_subsistemas(dados))
            del dados, _
    if not partes:
        raise ValueError("Nenhum dado disponível para o período e as fontes selecionadas.")
    return {
        "df_curtailment": pd.concat(partes, ignore_index=True),
        "relatorios": {"resumo_pipeline": {
            "registros_curtailment": registros,
            "periodo_inicial": inicio.strftime("%m/%Y"),
            "periodo_final": fim.strftime("%m/%Y"),
        }},
    }
