"""Enriquecimento geográfico dos dados de curtailment."""

import math

import pandas as pd


COLUNAS_CADASTRO_FCAP = [
    "nom_usina_conjunto",
    "cod_pontoconexao",
    "nom_pontoconexao",
    "val_latitudepontoconexao",
    "val_longitudepontoconexao",
]


def reduzir_fator_capacidade(
    df_fator_capacidade,
):
    """
    Reduz a base temporal de fator de capacidade para o
    cadastro geográfico utilizado pelo mapa.

    A redução reproduz a lógica do código original:
    seleção das colunas geográficas e remoção de linhas
    completamente duplicadas.

    Parâmetros
    ----------
    df_fator_capacidade : pandas.DataFrame
        Base completa de fator de capacidade obtida do ONS.

    Retorno
    -------
    pandas.DataFrame
        Cadastro geográfico com uma associação por nome
        de usina.
    """

    if df_fator_capacidade is None:
        raise ValueError(
            "A base de fator de capacidade não foi carregada."
        )

    colunas_ausentes = [
        coluna
        for coluna in COLUNAS_CADASTRO_FCAP
        if coluna not in df_fator_capacidade.columns
    ]

    if colunas_ausentes:
        raise ValueError(
            "Colunas ausentes na base de fator de capacidade: "
            f"{colunas_ausentes}"
        )

    cadastro = df_fator_capacidade[
        COLUNAS_CADASTRO_FCAP
    ].copy()

    cadastro["nom_usina_conjunto_lc"] = (
        cadastro["nom_usina_conjunto"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    cadastro["cod_pontoconexao"] = (
        cadastro["cod_pontoconexao"]
        .astype("string")
        .str.strip()
    )

    cadastro["nom_pontoconexao"] = (
        cadastro["nom_pontoconexao"]
        .astype("string")
        .str.strip()
    )

    cadastro["val_latitudepontoconexao"] = pd.to_numeric(
        cadastro["val_latitudepontoconexao"],
        errors="coerce",
    )

    cadastro["val_longitudepontoconexao"] = pd.to_numeric(
        cadastro["val_longitudepontoconexao"],
        errors="coerce",
    )

    cadastro = cadastro[
        [
            "nom_usina_conjunto_lc",
            "cod_pontoconexao",
            "nom_pontoconexao",
            "val_latitudepontoconexao",
            "val_longitudepontoconexao",
        ]
    ].drop_duplicates(
        ignore_index=True,
    )

    nomes_duplicados = cadastro[
        "nom_usina_conjunto_lc"
    ].duplicated(
        keep=False,
    )

    if nomes_duplicados.any():
        exemplos = (
            cadastro.loc[
                nomes_duplicados,
                "nom_usina_conjunto_lc",
            ]
            .dropna()
            .unique()
            .tolist()
        )

        raise ValueError(
            "O cadastro reduzido possui nomes relacionados "
            "a mais de uma associação geográfica. "
            f"Exemplos: {exemplos[:10]}"
        )

    return cadastro


def enriquecer_curtailment(
    df_curtailment,
    cadastro_geografico,
):
    """
    Associa os registros de curtailment ao ponto de conexão
    e às respectivas coordenadas.

    O relacionamento utiliza o nome da usina em lowercase,
    reproduzindo a regra do código original.

    Parâmetros
    ----------
    df_curtailment : pandas.DataFrame
        Base de curtailment já calculada.
    cadastro_geografico : pandas.DataFrame
        Cadastro produzido por reduzir_fator_capacidade().

    Retorno
    -------
    tuple
        DataFrame enriquecido e relatório de qualidade
        do relacionamento.
    """

    if df_curtailment is None:
        raise ValueError(
            "A base de curtailment não foi carregada."
        )

    if cadastro_geografico is None:
        raise ValueError(
            "O cadastro geográfico não foi carregado."
        )

    if "nom_usina" not in df_curtailment.columns:
        raise ValueError(
            "A base de curtailment não possui a coluna "
            "'nom_usina'."
        )

    colunas_cadastro_obrigatorias = [
        "nom_usina_conjunto_lc",
        "cod_pontoconexao",
        "nom_pontoconexao",
        "val_latitudepontoconexao",
        "val_longitudepontoconexao",
    ]

    colunas_ausentes = [
        coluna
        for coluna in colunas_cadastro_obrigatorias
        if coluna not in cadastro_geografico.columns
    ]

    if colunas_ausentes:
        raise ValueError(
            "Colunas ausentes no cadastro geográfico: "
            f"{colunas_ausentes}"
        )

    curt = df_curtailment.copy()
    cadastro = cadastro_geografico.copy()

    curt["nom_usina_lc"] = (
        curt["nom_usina"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    duplicidades_cadastro = cadastro[
        "nom_usina_conjunto_lc"
    ].duplicated(
        keep=False,
    )

    if duplicidades_cadastro.any():
        exemplos = (
            cadastro.loc[
                duplicidades_cadastro,
                "nom_usina_conjunto_lc",
            ]
            .dropna()
            .unique()
            .tolist()
        )

        raise ValueError(
            "O cadastro geográfico contém chaves duplicadas. "
            "O merge poderia multiplicar registros. "
            f"Exemplos: {exemplos[:10]}"
        )

    linhas_antes = len(curt)

    colunas_metricas = [
        "val_geracao",
        "val_curtailment",
        "val_geracao_esperada",
    ]

    totais_antes = {}

    for coluna in colunas_metricas:
        if coluna in curt.columns:
            totais_antes[coluna] = pd.to_numeric(
                curt[coluna],
                errors="coerce",
            ).sum()

    enriquecido = curt.merge(
        cadastro,
        left_on="nom_usina_lc",
        right_on="nom_usina_conjunto_lc",
        how="left",
        validate="many_to_one",
    )

    linhas_depois = len(enriquecido)

    if linhas_antes != linhas_depois:
        raise RuntimeError(
            "O enriquecimento alterou a quantidade de linhas. "
            f"Antes: {linhas_antes:,}. "
            f"Depois: {linhas_depois:,}."
        )

    encontrou_cadastro = enriquecido[
        "nom_usina_conjunto_lc"
    ].notna()

    possui_coordenadas = (
        enriquecido[
            "val_latitudepontoconexao"
        ].notna()
        & enriquecido[
            "val_longitudepontoconexao"
        ].notna()
    )

    diferencas_totais = {}

    for coluna, total_antes in totais_antes.items():
        total_depois = pd.to_numeric(
            enriquecido[coluna],
            errors="coerce",
        ).sum()

        diferenca = total_depois - total_antes

        # Converte para float nativo para facilitar a futura exibição e serialização no Streamlit.
        diferencas_totais[coluna] = float(diferenca)

        if not math.isclose(
            total_antes,
            total_depois,
            rel_tol=1e-12,
            abs_tol=1e-6,
        ):
            raise RuntimeError(
                f"O total de '{coluna}' foi alterado durante "
                f"o enriquecimento. Diferença: {diferenca}."
            )

    resumo_usinas = (
        enriquecido[
            [
                "nom_usina",
                "nom_usina_lc",
                "nom_usina_conjunto_lc",
                "val_latitudepontoconexao",
                "val_longitudepontoconexao",
            ]
        ]
        .drop_duplicates(
            subset=["nom_usina_lc"]
        )
    )

    usinas_sem_cadastro = (
        resumo_usinas.loc[
            resumo_usinas[
                "nom_usina_conjunto_lc"
            ].isna(),
            "nom_usina",
        ]
        .dropna()
        .sort_values()
        .tolist()
    )

    usinas_sem_coordenadas = (
        resumo_usinas.loc[
            resumo_usinas[
                "nom_usina_conjunto_lc"
            ].notna()
            & (
                resumo_usinas[
                    "val_latitudepontoconexao"
                ].isna()
                | resumo_usinas[
                    "val_longitudepontoconexao"
                ].isna()
            ),
            "nom_usina",
        ]
        .dropna()
        .sort_values()
        .tolist()
    )

    relatorio = {
        "linhas_antes": linhas_antes,
        "linhas_depois": linhas_depois,
        "linhas_com_cadastro": int(
            encontrou_cadastro.sum()
        ),
        "linhas_sem_cadastro": int(
            (~encontrou_cadastro).sum()
        ),
        "percentual_com_cadastro": round(
            encontrou_cadastro.mean() * 100,
            2,
        ),
        "linhas_com_coordenadas": int(
            possui_coordenadas.sum()
        ),
        "linhas_sem_coordenadas": int(
            (~possui_coordenadas).sum()
        ),
        "percentual_georreferenciado": round(
            possui_coordenadas.mean() * 100,
            2,
        ),
        "usinas_total": int(
            resumo_usinas[
                "nom_usina_lc"
            ].nunique()
        ),
        "usinas_com_cadastro": int(
            resumo_usinas[
                "nom_usina_conjunto_lc"
            ].notna().sum()
        ),
        "usinas_com_coordenadas": int(
            (
                resumo_usinas[
                    "val_latitudepontoconexao"
                ].notna()
                & resumo_usinas[
                    "val_longitudepontoconexao"
                ].notna()
            ).sum()
        ),
        "usinas_sem_cadastro": usinas_sem_cadastro,
        "usinas_sem_coordenadas": (
            usinas_sem_coordenadas
        ),
        "diferencas_totais": diferencas_totais,
    }

    enriquecido = enriquecido.drop(
        columns=[
            "nom_usina_lc",
            "nom_usina_conjunto_lc",
        ],
        errors="ignore",
    )

    return enriquecido, relatorio

