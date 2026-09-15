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

COLUNAS_GERADAS_ENRIQUECIMENTO = [
    "nom_subestacao_de_cadastro",
    "val_latitude_de",
    "val_longitude_de",
    "nom_subestacao_para_cadastro",
    "val_latitude_para",
    "val_longitude_para",
]


def preparar_subestacoes(
    df_subestacoes,
):
    """
    Prepara o cadastro de subestações para associação às
    extremidades das linhas de transmissão.

    A função preserva o DataFrame original e produz um cadastro
    reduzido com uma linha por número de barra.

    Registros sem número de barra permanecem na base original,
    mas não participam do cadastro utilizado nos merges.

    Parâmetros
    ----------
    df_subestacoes : pandas.DataFrame
        Cadastro completo de subestações disponibilizado pelo ONS.

    Retorno
    -------
    pandas.DataFrame
        Cadastro reduzido com números de barra, nomes e
        coordenadas das subestações.

    Raises
    ------
    ValueError
        Quando a base não foi carregada, está vazia, não possui
        as colunas obrigatórias ou contém mais de um registro
        para o mesmo número de barra.
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

    # Remove somente registros completamente duplicados
    # nas quatro colunas utilizadas pelo cadastro.
    subestacoes = subestacoes.drop_duplicates(
        ignore_index=True,
    )

    # Uma chave nula não pode ser usada no relacionamento.
    #
    # Isso evita que linhas sem barra recebam coordenadas
    # de uma subestação que também esteja sem número de barra.
    subestacoes = (
        subestacoes
        .dropna(subset=["num_barra"])
        .reset_index(drop=True)
    )

    # O merge many-to-one exige uma associação única
    # para cada número de barra.
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

    O relacionamento é realizado exclusivamente pelos números
    das barras. Linhas com barras ausentes são preservadas, mas
    não recebem associação cadastral naquela extremidade.

    Parâmetros
    ----------
    df_linhas : pandas.DataFrame
        Cadastro completo de linhas de transmissão do ONS.
    subestacoes_preparadas : pandas.DataFrame
        Cadastro retornado por preparar_subestacoes().

    Retorno
    -------
    tuple
        O primeiro elemento é o DataFrame de linhas enriquecido.
        O segundo elemento é um dicionário com o relatório de
        qualidade do relacionamento.

    Raises
    ------
    ValueError
        Quando alguma base não foi informada, está vazia,
        não possui as colunas necessárias, contém barras
        duplicadas ou aparenta já ter sido enriquecida.
    RuntimeError
        Quando os merges alteram a quantidade de linhas.
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

    colunas_ausentes_subestacoes = [
        coluna
        for coluna in COLUNAS_SUBESTACOES
        if coluna not in subestacoes_preparadas.columns
    ]

    if colunas_ausentes_subestacoes:
        raise ValueError(
            "Colunas ausentes no cadastro preparado de "
            f"subestações: {colunas_ausentes_subestacoes}"
        )

    # Evita executar o enriquecimento sobre uma base que já
    # tenha recebido as colunas geográficas.
    colunas_ja_existentes = [
        coluna
        for coluna in COLUNAS_GERADAS_ENRIQUECIMENTO
        if coluna in df_linhas.columns
    ]

    if colunas_ja_existentes:
        raise ValueError(
            "A base de linhas aparenta já estar enriquecida. "
            "As seguintes colunas já existem: "
            f"{colunas_ja_existentes}"
        )

    linhas = df_linhas.copy()
    subestacoes = subestacoes_preparadas.copy()

    # Padroniza as chaves das linhas.
    linhas["num_barra_de"] = pd.to_numeric(
        linhas["num_barra_de"],
        errors="coerce",
    ).astype("Int64")

    linhas["num_barra_para"] = pd.to_numeric(
        linhas["num_barra_para"],
        errors="coerce",
    ).astype("Int64")

    # Padroniza novamente a chave cadastral como medida
    # defensiva.
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

    # Impede associações entre chaves nulas.
    if subestacoes["num_barra"].isna().any():
        raise ValueError(
            "O cadastro preparado de subestações ainda possui "
            "números de barra ausentes. Execute primeiro "
            "preparar_subestacoes()."
        )

    # Confirma a unicidade da chave cadastral.
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

    # Conjunto usado para identificar se uma barra foi
    # encontrada no cadastro independentemente do nome
    # ou das coordenadas da subestação.
    barras_cadastradas = set(
        subestacoes["num_barra"]
        .dropna()
        .tolist()
    )

    linhas_antes = len(linhas)

    # ========================================================
    # DIAGNÓSTICO DAS CHAVES DA BASE DE LINHAS
    # ========================================================

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

    # ========================================================
    # PREPARAÇÃO DOS CADASTROS DE ESTRUTURA DE E PARA
    # ========================================================

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

    # ========================================================
    # ASSOCIAÇÃO DAS EXTREMIDADES
    # ========================================================

    linhas = linhas.merge(
        subestacoes_de,
        on="num_barra_de",
        how="left",
        validate="many_to_one",
    )

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

    # ========================================================
    # VALIDAÇÃO DAS ASSOCIAÇÕES
    # ========================================================

    # Confirma que a barra existe no cadastro usando a chave,
    # sem depender do nome ou das coordenadas.
    barra_de_encontrada = (
        linhas["num_barra_de"].notna()
        & linhas["num_barra_de"].isin(
            barras_cadastradas
        )
    )

    barra_para_encontrada = (
        linhas["num_barra_para"].notna()
        & linhas["num_barra_para"].isin(
            barras_cadastradas
        )
    )

    # Disponibilidade das coordenadas.
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

    # Barra preenchida, mas ausente no cadastro.
    barra_de_preenchida_nao_encontrada = (
        linhas["num_barra_de"].notna()
        & ~barra_de_encontrada
    )

    barra_para_preenchida_nao_encontrada = (
        linhas["num_barra_para"].notna()
        & ~barra_para_encontrada
    )

    # Barra presente no cadastro, mas sem alguma coordenada.
    barra_de_encontrada_sem_coordenadas = (
        barra_de_encontrada
        & ~possui_coordenadas_de
    )

    barra_para_encontrada_sem_coordenadas = (
        barra_para_encontrada
        & ~possui_coordenadas_para
    )

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

    # ========================================================
    # VALIDAÇÃO GEOGRÁFICA
    # ========================================================

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

    # Uma linha pode ter quatro coordenadas preenchidas, mas
    # as duas extremidades podem estar na mesma posição.
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

    # Uma linha desenhável precisa das quatro coordenadas e
    # de extremidades espacialmente diferentes.
    linha_desenhavel = (
        possui_geometria_completa
        & ~extremidades_coincidentes
    )

    # ========================================================
    # RELATÓRIO
    # ========================================================

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
