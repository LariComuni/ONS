"""Preparação geográfica da rede de transmissão."""

import pandas as pd


COLUNAS_SUBESTACOES = [
    "num_barra",
    "nom_subestacao",
    "val_latitude",
    "val_longitude",
]

COLUNAS_BARRAS_LINHAS = [
    "num_barra_de",
    "num_barra_para",
]


def preparar_subestacoes(df_subestacoes):
    """
    Prepara o cadastro de subestações para associação
    às extremidades das linhas de transmissão.

    Parâmetros
    ----------
    df_subestacoes : pandas.DataFrame
        Cadastro completo de subestações do ONS.

    Retorno
    -------
    pandas.DataFrame
        Cadastro reduzido de barras, nomes e coordenadas.
    """

    if df_subestacoes is None:
        raise ValueError(
            "A base de subestações não foi carregada."
        )

    if df_subestacoes.empty:
        raise ValueError(
            "A base de subestações está vazia."
        )

    colunas_ausentes = [
        coluna
        for coluna in COLUNAS_SUBESTACOES
        if coluna not in df_subestacoes.columns
    ]

    if colunas_ausentes:
        raise ValueError(
            "Colunas ausentes na base de subestações: "
            f"{colunas_ausentes}"
        )

    subestacoes = df_subestacoes[
        COLUNAS_SUBESTACOES
    ].copy()

    subestacoes["num_barra"] = pd.to_numeric(
        subestacoes["num_barra"],
        errors="coerce",
    ).astype("Int64")

    subestacoes["val_latitude"] = pd.to_numeric(
        subestacoes["val_latitude"],
        errors="coerce",
    )

    subestacoes["val_longitude"] = pd.to_numeric(
        subestacoes["val_longitude"],
        errors="coerce",
    )

    subestacoes = subestacoes.drop_duplicates(
        ignore_index=True,
    )

    # Registros sem número de barra não podem ser usados
    # como chave no relacionamento com as linhas.
    subestacoes = (
        subestacoes
        .dropna(subset=["num_barra"])
        .reset_index(drop=True)
    )

    # O merge many-to-one exige uma linha por barra.
    barras_duplicadas = subestacoes[
        "num_barra"
    ].duplicated(
        keep=False,
    )

    if barras_duplicadas.any():
        exemplos = (
            subestacoes.loc[
                barras_duplicadas,
                "num_barra",
            ]
            .dropna()
            .unique()
            .tolist()
        )

        raise ValueError(
            "O cadastro de subestações possui barras "
            "associadas a múltiplos registros. "
            f"Exemplos: {exemplos[:10]}"
        )

    return subestacoes

def enriquecer_linhas_transmissao(
    df_linhas,
    subestacoes_preparadas,
):
    """
    Associa as coordenadas das subestações às extremidades
    DE e PARA das linhas de transmissão.

    O relacionamento é realizado pelos números das barras.
    Barras ausentes não recebem associação cadastral.

    Parâmetros
    ----------
    df_linhas : pandas.DataFrame
        Cadastro completo de linhas de transmissão do ONS.
    subestacoes_preparadas : pandas.DataFrame
        Cadastro retornado por preparar_subestacoes().

    Retorno
    -------
    tuple
        DataFrame de linhas enriquecido e dicionário com
        o relatório de qualidade do relacionamento.
    """

    if df_linhas is None:
        raise ValueError(
            "A base de linhas de transmissão não foi carregada."
        )

    if df_linhas.empty:
        raise ValueError(
            "A base de linhas de transmissão está vazia."
        )

    if subestacoes_preparadas is None:
        raise ValueError(
            "O cadastro preparado de subestações não foi informado."
        )

    if subestacoes_preparadas.empty:
        raise ValueError(
            "O cadastro preparado de subestações está vazio."
        )

    colunas_ausentes_linhas = [
        coluna
        for coluna in COLUNAS_BARRAS_LINHAS
        if coluna not in df_linhas.columns
    ]

    if colunas_ausentes_linhas:
        raise ValueError(
            "Colunas ausentes na base de linhas: "
            f"{colunas_ausentes_linhas}"
        )

    colunas_subestacoes_obrigatorias = [
        "num_barra",
        "nom_subestacao",
        "val_latitude",
        "val_longitude",
    ]

    colunas_ausentes_subestacoes = [
        coluna
        for coluna in colunas_subestacoes_obrigatorias
        if coluna not in subestacoes_preparadas.columns
    ]

    if colunas_ausentes_subestacoes:
        raise ValueError(
            "Colunas ausentes no cadastro preparado de "
            f"subestações: {colunas_ausentes_subestacoes}"
        )

    linhas = df_linhas.copy()
    subestacoes = subestacoes_preparadas.copy()

    # Padroniza os números das barras.
    linhas["num_barra_de"] = pd.to_numeric(
        linhas["num_barra_de"],
        errors="coerce",
    ).astype("Int64")

    linhas["num_barra_para"] = pd.to_numeric(
        linhas["num_barra_para"],
        errors="coerce",
    ).astype("Int64")

    subestacoes["num_barra"] = pd.to_numeric(
        subestacoes["num_barra"],
        errors="coerce",
    ).astype("Int64")

    # Esta proteção evita associações entre chaves ausentes.
    if subestacoes["num_barra"].isna().any():
        raise ValueError(
            "O cadastro preparado de subestações ainda possui "
            "números de barra ausentes. Execute primeiro "
            "preparar_subestacoes()."
        )

    # O relacionamento many-to-one exige uma linha por barra.
    barras_duplicadas = subestacoes[
        "num_barra"
    ].duplicated(
        keep=False,
    )

    if barras_duplicadas.any():
        exemplos = (
            subestacoes.loc[
                barras_duplicadas,
                "num_barra",
            ]
            .dropna()
            .unique()
            .tolist()
        )

        raise ValueError(
            "O cadastro preparado de subestações possui "
            "barras duplicadas. "
            f"Exemplos: {exemplos[:10]}"
        )

    linhas_antes = len(linhas)

    # Identifica barras ausentes na própria base de linhas.
    barra_de_ausente = (
        linhas["num_barra_de"].isna()
    )

    barra_para_ausente = (
        linhas["num_barra_para"].isna()
    )

    ambas_barras_ausentes = (
        barra_de_ausente
        & barra_para_ausente
    )

    alguma_barra_ausente = (
        barra_de_ausente
        | barra_para_ausente
    )

    # Prepara o cadastro da extremidade DE.
    subestacoes_de = subestacoes.rename(
        columns={
            "num_barra": "num_barra_de",
            "nom_subestacao": (
                "nom_subestacao_de_cadastro"
            ),
            "val_latitude": "val_latitude_de",
            "val_longitude": "val_longitude_de",
        }
    )

    # Prepara o cadastro da extremidade PARA.
    subestacoes_para = subestacoes.rename(
        columns={
            "num_barra": "num_barra_para",
            "nom_subestacao": (
                "nom_subestacao_para_cadastro"
            ),
            "val_latitude": "val_latitude_para",
            "val_longitude": "val_longitude_para",
        }
    )

    # Associa a extremidade DE.
    linhas = linhas.merge(
        subestacoes_de,
        on="num_barra_de",
        how="left",
        validate="many_to_one",
    )

    # Associa a extremidade PARA.
    linhas = linhas.merge(
        subestacoes_para,
        on="num_barra_para",
        how="left",
        validate="many_to_one",
    )

    linhas_depois = len(linhas)

    if linhas_antes != linhas_depois:
        raise RuntimeError(
            "O enriquecimento da rede alterou a quantidade "
            "de linhas. "
            f"Antes: {linhas_antes:,}. "
            f"Depois: {linhas_depois:,}."
        )

    # Verifica se a barra foi encontrada no cadastro.
    barra_de_encontrada = (
        linhas[
            "nom_subestacao_de_cadastro"
        ].notna()
    )

    barra_para_encontrada = (
        linhas[
            "nom_subestacao_para_cadastro"
        ].notna()
    )

    # Verifica a disponibilidade das coordenadas.
    possui_coordenadas_de = (
        linhas["val_latitude_de"].notna()
        & linhas["val_longitude_de"].notna()
    )

    possui_coordenadas_para = (
        linhas["val_latitude_para"].notna()
        & linhas["val_longitude_para"].notna()
    )

    possui_geometria_completa = (
        possui_coordenadas_de
        & possui_coordenadas_para
    )

    # Barra preenchida, mas não encontrada no cadastro.
    barra_de_preenchida_nao_encontrada = (
        linhas["num_barra_de"].notna()
        & ~barra_de_encontrada
    )

    barra_para_preenchida_nao_encontrada = (
        linhas["num_barra_para"].notna()
        & ~barra_para_encontrada
    )

    # Barra encontrada, mas sem latitude ou longitude.
    barra_de_encontrada_sem_coordenadas = (
        barra_de_encontrada
        & ~possui_coordenadas_de
    )

    barra_para_encontrada_sem_coordenadas = (
        barra_para_encontrada
        & ~possui_coordenadas_para
    )

    # Lista as barras preenchidas que não encontraram cadastro.
    barras_de_preenchidas_nao_encontradas = (
        linhas.loc[
            barra_de_preenchida_nao_encontrada,
            "num_barra_de",
        ]
        .dropna()
        .unique()
        .tolist()
    )

    barras_para_preenchidas_nao_encontradas = (
        linhas.loc[
            barra_para_preenchida_nao_encontrada,
            "num_barra_para",
        ]
        .dropna()
        .unique()
        .tolist()
    )

    # Validação geográfica ampla para o território brasileiro.
    coordenadas_de_fora_faixa = (
        possui_coordenadas_de
        & (
            ~linhas["val_latitude_de"].between(
                -35,
                6,
            )
            | ~linhas["val_longitude_de"].between(
                -75,
                -30,
            )
        )
    )

    coordenadas_para_fora_faixa = (
        possui_coordenadas_para
        & (
            ~linhas["val_latitude_para"].between(
                -35,
                6,
            )
            | ~linhas["val_longitude_para"].between(
                -75,
                -30,
            )
        )
    )

    # Identifica linhas cujas duas extremidades possuem
    # exatamente a mesma coordenada.
    extremidades_coincidentes = (
        possui_geometria_completa
        & (
            linhas["val_latitude_de"]
            == linhas["val_latitude_para"]
        )
        & (
            linhas["val_longitude_de"]
            == linhas["val_longitude_para"]
        )
    )

    # Uma linha desenhável precisa de quatro coordenadas
    # e de extremidades espacialmente distintas.
    linha_desenhavel = (
        possui_geometria_completa
        & ~extremidades_coincidentes
    )

    relatorio = {
        "linhas_entrada": linhas_antes,
        "linhas_saida": linhas_depois,

        "linhas_com_barra_de_ausente": int(
            barra_de_ausente.sum()
        ),
        "linhas_com_barra_para_ausente": int(
            barra_para_ausente.sum()
        ),
        "linhas_com_ambas_barras_ausentes": int(
            ambas_barras_ausentes.sum()
        ),
        "linhas_com_alguma_barra_ausente": int(
            alguma_barra_ausente.sum()
        ),

        "linhas_com_barra_de_encontrada": int(
            barra_de_encontrada.sum()
        ),
        "linhas_com_barra_para_encontrada": int(
            barra_para_encontrada.sum()
        ),

        "linhas_com_barra_de_preenchida_nao_encontrada": int(
            barra_de_preenchida_nao_encontrada.sum()
        ),
        "linhas_com_barra_para_preenchida_nao_encontrada": int(
            barra_para_preenchida_nao_encontrada.sum()
        ),

        "linhas_com_barra_de_encontrada_sem_coordenadas": int(
            barra_de_encontrada_sem_coordenadas.sum()
        ),
        "linhas_com_barra_para_encontrada_sem_coordenadas": int(
            barra_para_encontrada_sem_coordenadas.sum()
        ),

        "linhas_com_coordenadas_de": int(
            possui_coordenadas_de.sum()
        ),
        "linhas_sem_coordenadas_de": int(
            (~possui_coordenadas_de).sum()
        ),
        "linhas_com_coordenadas_para": int(
            possui_coordenadas_para.sum()
        ),
        "linhas_sem_coordenadas_para": int(
            (~possui_coordenadas_para).sum()
        ),

        "linhas_com_geometria_completa": int(
            possui_geometria_completa.sum()
        ),
        "linhas_sem_geometria_completa": int(
            (~possui_geometria_completa).sum()
        ),
        "percentual_geometria_completa": round(
            possui_geometria_completa.mean() * 100,
            2,
        ),

        "linhas_com_extremidades_coincidentes": int(
            extremidades_coincidentes.sum()
        ),
        "linhas_desenhaveis": int(
            linha_desenhavel.sum()
        ),
        "percentual_linhas_desenhaveis": round(
            linha_desenhavel.mean() * 100,
            2,
        ),

        "barras_de_preenchidas_nao_encontradas": (
            barras_de_preenchidas_nao_encontradas
        ),
        "barras_para_preenchidas_nao_encontradas": (
            barras_para_preenchidas_nao_encontradas
        ),

        "coordenadas_de_fora_faixa": int(
            coordenadas_de_fora_faixa.sum()
        ),
        "coordenadas_para_fora_faixa": int(
            coordenadas_para_fora_faixa.sum()
        ),
    }

    return linhas, relatorio
