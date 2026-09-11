"""Cálculo dos indicadores de curtailment."""

import numpy as np
import pandas as pd


COLUNAS_NUMERICAS = [
    "val_geracao",
    "val_geracaolimitada",
    "val_disponibilidade",
    "val_geracaoreferencia",
]


COLUNAS_OBRIGATORIAS = [
    "id_subsistema",
    "nom_subsistema",
    "id_estado",
    "nom_estado",
    "nom_usina",
    "id_ons",
    "ceg",
    "din_instante",
    "val_geracao",
    "val_geracaolimitada",
    "val_disponibilidade",
    "val_geracaoreferencia",
    "val_geracaoreferenciafinal",
    "cod_razaorestricao",
    "cod_origemrestricao",
]


COLUNAS_RESULTADO = [
    "id_subsistema",
    "nom_subsistema",
    "id_estado",
    "nom_estado",
    "nom_usina",
    "id_ons",
    "ceg",
    "din_instante",
    "val_geracao",
    "val_geracaolimitada",
    "val_disponibilidade",
    "val_geracaoreferencia",
    "val_geracaoreferenciafinal",
    "cod_razaorestricao",
    "cod_origemrestricao",
    "val_geracaoreferenciafinal2",
    "val_curtailment",
    "val_geracao_esperada",
    "fonte",
]


def validar_colunas(df):
    """
    Verifica se o DataFrame possui as colunas necessárias.

    Parâmetros
    ----------
    df : pandas.DataFrame
        DataFrame que será validado.

    Raises
    ------
    ValueError
        Quando uma ou mais colunas obrigatórias não existem.
    """

    colunas_ausentes = [
        coluna
        for coluna in COLUNAS_OBRIGATORIAS
        if coluna not in df.columns
    ]

    if colunas_ausentes:
        raise ValueError(
            "As seguintes colunas obrigatórias não foram "
            f"encontradas: {colunas_ausentes}"
        )


def converter_colunas_numericas(df):
    """
    Converte as medidas do cálculo para valores numéricos.

    A função aceita valores que utilizem ponto ou vírgula
    como separador decimal.
    """

    df = df.copy()

    for coluna in COLUNAS_NUMERICAS:
        if pd.api.types.is_numeric_dtype(df[coluna]):
            continue

        valores = (
            df[coluna]
            .astype("string")
            .str.strip()
            .str.replace(",", ".", regex=False)
        )

        df[coluna] = pd.to_numeric(
            valores,
            errors="coerce",
        )

    return df


def calcular_curtailment(df, fonte=None):
    """
    Calcula geração de referência final ajustada, curtailment
    e geração esperada.

    Parâmetros
    ----------
    df : pandas.DataFrame
        Dados de curtailment obtidos do ONS.
    fonte : str ou None, opcional
        EOL ou UFV. Quando não informada, a função utiliza
        a coluna fonte que já existe no DataFrame.

    Retorno
    -------
    pandas.DataFrame
        Base tratada com os indicadores calculados.
    """

    validar_colunas(df)

    df = converter_colunas_numericas(df)

    if fonte is not None:
        fonte = fonte.upper().strip()

        if fonte not in {"EOL", "UFV"}:
            raise ValueError(
                "Fonte inválida. Use EOL ou UFV."
            )

        df["fonte"] = fonte

    elif "fonte" not in df.columns:
        raise ValueError(
            "A fonte deve ser informada ou estar presente "
            "na coluna 'fonte'."
        )

    # Indica os registros que possuem razão de restrição.
    possui_restricao = (
        df["cod_razaorestricao"].notna()
    )

    # Diferença entre geração limitada e geração verificada.
    diferenca_geracao = (
        df["val_geracaolimitada"]
        - df["val_geracao"]
    )

    # Mínimo entre disponibilidade e geração de referência.
    referencia_base = np.minimum(
        df["val_disponibilidade"],
        df["val_geracaoreferencia"],
    )

    # Identifica diferenças relevantes.
    diferenca_relevante = (
        (
            df["val_geracao"]
            < df["val_geracaolimitada"]
        )
        & (
            (
                diferenca_geracao
                > 0.05 * df["val_geracaolimitada"]
            )
            | (
                diferenca_geracao > 5
            )
        )
    )

    # Referência final ajustada pela metodologia.
    df["val_geracaoreferenciafinal2"] = np.where(
        possui_restricao & diferenca_relevante,
        referencia_base - diferenca_geracao,
        np.where(
            possui_restricao,
            referencia_base,
            np.nan,
        ),
    )

    # Curtailment calculado.
    curtailment_valido = (
        possui_restricao
        & (
            df["val_geracaoreferenciafinal2"]
            > df["val_geracao"]
        )
    )

    df["val_curtailment"] = np.where(
        curtailment_valido,
        (
            df["val_geracaoreferenciafinal2"]
            - df["val_geracao"]
        ),
        0.0,
    )

    # Geração esperada.
    df["val_geracao_esperada"] = np.where(
        curtailment_valido,
        df["val_geracaoreferenciafinal2"],
        df["val_geracao"],
    )

    return df[COLUNAS_RESULTADO].copy()
