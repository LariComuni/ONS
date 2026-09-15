"""Agregações dos dados de curtailment para visualização."""

import math

import pandas as pd


COLUNAS_AGREGACAO_PONTO = [
    "din_instante",
    "cod_pontoconexao",
    "nom_pontoconexao",
]

COLUNAS_METRICAS = [
    "val_geracao",
    "val_curtailment",
    "val_geracao_esperada",
]


def agregar_por_instante_e_ponto(
    df_curtailment_enriquecido,
):
    """
    Agrega os dados de curtailment por instante e ponto de conexão.

    Para cada combinação de instante, código do ponto e nome do
    ponto, soma geração, curtailment e geração esperada.

    Parâmetros
    ----------
    df_curtailment_enriquecido : pandas.DataFrame
        Base de curtailment calculada e enriquecida com os dados
        dos pontos de conexão.

    Retorno
    -------
    tuple
        DataFrame agregado e dicionário com o relatório da execução.
    """

    if df_curtailment_enriquecido is None:
        raise ValueError(
            "A base de curtailment enriquecida não foi carregada."
        )

    if df_curtailment_enriquecido.empty:
        raise ValueError(
            "A base de curtailment enriquecida está vazia."
        )

    colunas_obrigatorias = (
        COLUNAS_AGREGACAO_PONTO
        + COLUNAS_METRICAS
    )

    colunas_ausentes = [
        coluna
        for coluna in colunas_obrigatorias
        if coluna not in df_curtailment_enriquecido.columns
    ]

    if colunas_ausentes:
        raise ValueError(
            "Colunas ausentes na base de curtailment "
            f"enriquecida: {colunas_ausentes}"
        )

    # Cria uma cópia para não alterar o DataFrame original.
    df = df_curtailment_enriquecido.copy()

    # Padroniza a coluna temporal.
    df["din_instante"] = pd.to_datetime(
        df["din_instante"],
        errors="coerce",
    )

    # Garante que as métricas estejam em formato numérico.
    for coluna in COLUNAS_METRICAS:
        df[coluna] = pd.to_numeric(
            df[coluna],
            errors="coerce",
        )

    quantidade_linhas_entrada = len(df)

    quantidade_datas_invalidas = int(
        df["din_instante"].isna().sum()
    )

    # Registros sem instante válido não podem formar uma série temporal
    df_valido = df.dropna(
        subset=["din_instante"]
    ).copy()

    if df_valido.empty:
        raise ValueError(
            "Nenhuma linha possui uma data válida para agregação."
        )

    # Agrega por instante e ponto de conexão.
    #
    # dropna=False mantém registros sem ponto de conexão, permitindo que esses valores continuem nos totais.
    #
    # min_count=1 evita transformar um grupo totalmente ausente em zero.
    df_agg = (
        df_valido
        .groupby(
            COLUNAS_AGREGACAO_PONTO,
            dropna=False,
            observed=True,
        )[COLUNAS_METRICAS]
        .sum(min_count=1)
        .reset_index()
    )

    # Cria a hora do dia no resultado agregado.
    df_agg["hora"] = (
        df_agg["din_instante"]
        .dt.hour
        .astype("int8")
    )

    ordem_colunas = [
        "din_instante",
        "hora",
        "cod_pontoconexao",
        "nom_pontoconexao",
        "val_geracao",
        "val_curtailment",
        "val_geracao_esperada",
    ]

    df_agg = (
        df_agg[ordem_colunas]
        .sort_values(
            [
                "din_instante",
                "cod_pontoconexao",
                "nom_pontoconexao",
            ],
            na_position="last",
        )
        .reset_index(drop=True)
    )

    # Valida se os totais foram preservados.
    totais_antes = {}
    totais_depois = {}
    diferencas_totais = {}

    for coluna in COLUNAS_METRICAS:
        total_antes = df_valido[coluna].sum(
            min_count=1
        )

        total_depois = df_agg[coluna].sum(
            min_count=1
        )

        totais_antes[coluna] = float(total_antes)
        totais_depois[coluna] = float(total_depois)

        diferenca = total_depois - total_antes

        diferencas_totais[coluna] = float(
            diferenca
        )

        if not math.isclose(
            total_antes,
            total_depois,
            rel_tol=1e-12,
            abs_tol=1e-6,
        ):
            raise RuntimeError(
                f"O total de '{coluna}' foi alterado "
                f"durante a agregação. "
                f"Diferença: {diferenca}."
            )

    # Identifica os grupos agregados que não possuem ponto de conexão cadastrado.
    sem_codigo_ponto = (
        df_agg["cod_pontoconexao"].isna()
    )

    sem_nome_ponto = (
        df_agg["nom_pontoconexao"].isna()
    )

    sem_identificacao_ponto = (
        sem_codigo_ponto
        | sem_nome_ponto
    )

    # Monta o relatório.
    relatorio = {
        "linhas_entrada": quantidade_linhas_entrada,
        "linhas_com_data_valida": len(df_valido),
        "datas_invalidas": quantidade_datas_invalidas,
        "linhas_agregadas": len(df_agg),
        "instantes_distintos": int(
            df_agg["din_instante"].nunique()
        ),
        "pontos_por_codigo": int(
            df_agg["cod_pontoconexao"]
            .nunique(dropna=True)
        ),
        "pontos_por_nome": int(
            df_agg["nom_pontoconexao"]
            .nunique(dropna=True)
        ),
        "linhas_sem_codigo_ponto": int(
            sem_codigo_ponto.sum()
        ),
        "linhas_sem_nome_ponto": int(
            sem_nome_ponto.sum()
        ),
        "linhas_sem_identificacao_ponto": int(
            sem_identificacao_ponto.sum()
        ),
        "percentual_linhas_agregadas_com_ponto": round(
            (
                1
                - sem_identificacao_ponto.mean()
            )
            * 100,
            2,
        ),
        "totais_antes": totais_antes,
        "totais_depois": totais_depois,
        "diferencas_totais": diferencas_totais,
    }

    return df_agg, relatorio
