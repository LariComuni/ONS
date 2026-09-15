"""Preparação das geometrias utilizadas no mapa."""

from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString


COLUNAS_COORDENADAS_CURTAILMENT = [
    "val_latitudepontoconexao",
    "val_longitudepontoconexao",
]

COLUNAS_COORDENADAS_LINHAS = [
    "val_latitude_de",
    "val_longitude_de",
    "val_latitude_para",
    "val_longitude_para",
]

LIMITE_LATITUDE_MIN = -35
LIMITE_LATITUDE_MAX = 6
LIMITE_LONGITUDE_MIN = -75
LIMITE_LONGITUDE_MAX = -30

CRS_MAPA = "EPSG:4326"


def preparar_base_geografica_curtailment(
    df_curtailment_enriquecido: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Prepara a base de curtailment para a criação das
    geometrias de usinas e pontos de conexão.

    A função converte as coordenadas para valores numéricos,
    preserva a base completa e cria uma segunda base contendo
    somente os registros que possuem latitude e longitude.

    Registros sem coordenadas permanecem na base completa,
    mas não são incluídos na base georreferenciada.

    Parâmetros
    ----------
    df_curtailment_enriquecido : pandas.DataFrame
        Base de curtailment calculada e enriquecida com
        pontos de conexão e coordenadas.

    Retorno
    -------
    tuple
        O primeiro elemento é a base completa preparada.

        O segundo elemento é a base contendo somente registros
        com latitude e longitude disponíveis.

        O terceiro elemento é um dicionário com o relatório de
        qualidade geográfica.

    Raises
    ------
    ValueError
        Quando a base não foi carregada, está vazia ou não
        possui as colunas necessárias.
    """

    if df_curtailment_enriquecido is None:
        raise ValueError(
            "A base de curtailment enriquecida "
            "não foi carregada."
        )

    if df_curtailment_enriquecido.empty:
        raise ValueError(
            "A base de curtailment enriquecida está vazia."
        )

    colunas_ausentes = [
        coluna
        for coluna in COLUNAS_COORDENADAS_CURTAILMENT
        if coluna not in df_curtailment_enriquecido.columns
    ]

    if colunas_ausentes:
        raise ValueError(
            "Colunas geográficas ausentes na base "
            f"de curtailment: {colunas_ausentes}"
        )

    curt = df_curtailment_enriquecido.copy()

    for coluna in COLUNAS_COORDENADAS_CURTAILMENT:
        curt[coluna] = pd.to_numeric(
            curt[coluna],
            errors="coerce",
        )

    possui_coordenadas = (
        curt["val_latitudepontoconexao"].notna()
        & curt["val_longitudepontoconexao"].notna()
    )

    coordenadas_fora_faixa = (
        possui_coordenadas
        & (
            ~curt[
                "val_latitudepontoconexao"
            ].between(
                LIMITE_LATITUDE_MIN,
                LIMITE_LATITUDE_MAX,
            )
            | ~curt[
                "val_longitudepontoconexao"
            ].between(
                LIMITE_LONGITUDE_MIN,
                LIMITE_LONGITUDE_MAX,
            )
        )
    )

    curt_georreferenciado = (
        curt.loc[possui_coordenadas]
        .copy()
    )

    relatorio = {
        "linhas_entrada": len(curt),
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
        "linhas_com_coordenadas_fora_faixa": int(
            coordenadas_fora_faixa.sum()
        ),
    }

    return (
        curt,
        curt_georreferenciado,
        relatorio,
    )


def preparar_base_geografica_linhas(
    df_linhas_enriquecidas: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Prepara a base de linhas de transmissão para a criação
    das geometrias LineString.

    A função converte as quatro coordenadas para valores
    numéricos e separa as linhas que possuem coordenadas
    completas nas extremidades DE e PARA.

    Parâmetros
    ----------
    df_linhas_enriquecidas : pandas.DataFrame
        Base de linhas já associada às coordenadas das
        subestações DE e PARA.

    Retorno
    -------
    tuple
        O primeiro elemento é a base completa preparada.

        O segundo elemento contém somente as linhas com
        as quatro coordenadas disponíveis.

        O terceiro elemento é um dicionário com o relatório
        de cobertura geográfica.

    Raises
    ------
    ValueError
        Quando a base não foi carregada, está vazia ou não
        possui as colunas necessárias.
    """

    if df_linhas_enriquecidas is None:
        raise ValueError(
            "A base de linhas enriquecidas não foi carregada."
        )

    if df_linhas_enriquecidas.empty:
        raise ValueError(
            "A base de linhas enriquecidas está vazia."
        )

    colunas_ausentes = [
        coluna
        for coluna in COLUNAS_COORDENADAS_LINHAS
        if coluna not in df_linhas_enriquecidas.columns
    ]

    if colunas_ausentes:
        raise ValueError(
            "Colunas geográficas ausentes na base "
            f"de linhas: {colunas_ausentes}"
        )

    linhas = df_linhas_enriquecidas.copy()

    for coluna in COLUNAS_COORDENADAS_LINHAS:
        linhas[coluna] = pd.to_numeric(
            linhas[coluna],
            errors="coerce",
        )

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

    coordenadas_de_fora_faixa = (
        possui_coordenadas_de
        & (
            ~linhas["val_latitude_de"].between(
                LIMITE_LATITUDE_MIN,
                LIMITE_LATITUDE_MAX,
            )
            | ~linhas["val_longitude_de"].between(
                LIMITE_LONGITUDE_MIN,
                LIMITE_LONGITUDE_MAX,
            )
        )
    )

    coordenadas_para_fora_faixa = (
        possui_coordenadas_para
        & (
            ~linhas["val_latitude_para"].between(
                LIMITE_LATITUDE_MIN,
                LIMITE_LATITUDE_MAX,
            )
            | ~linhas["val_longitude_para"].between(
                LIMITE_LONGITUDE_MIN,
                LIMITE_LONGITUDE_MAX,
            )
        )
    )

    linhas_georreferenciadas = (
        linhas.loc[possui_geometria_completa]
        .copy()
    )

    relatorio = {
        "linhas_entrada": len(linhas),
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
        "coordenadas_de_fora_faixa": int(
            coordenadas_de_fora_faixa.sum()
        ),
        "coordenadas_para_fora_faixa": int(
            coordenadas_para_fora_faixa.sum()
        ),
    }

    return (
        linhas,
        linhas_georreferenciadas,
        relatorio,
    )


def criar_geometrias_usinas(
    df_curtailment_georreferenciado: pd.DataFrame,
) -> tuple[gpd.GeoDataFrame, dict]:
    """
    Cria um GeoDataFrame com uma geometria para cada usina.

    A localização utilizada corresponde às coordenadas do
    ponto de conexão, reproduzindo a regra do mapa original.

    Uma usina é identificada pela coluna nom_usina.

    Parâmetros
    ----------
    df_curtailment_georreferenciado : pandas.DataFrame
        Base de curtailment contendo somente registros
        com coordenadas disponíveis.

    Retorno
    -------
    tuple
        GeoDataFrame de usinas e relatório de qualidade.

    Raises
    ------
    ValueError
        Quando a base não foi informada, está vazia ou não
        possui as colunas necessárias.
    """

    if df_curtailment_georreferenciado is None:
        raise ValueError(
            "A base georreferenciada de curtailment "
            "não foi informada."
        )

    if df_curtailment_georreferenciado.empty:
        raise ValueError(
            "A base georreferenciada de curtailment está vazia."
        )

    colunas_obrigatorias = [
        "nom_usina",
        "val_latitudepontoconexao",
        "val_longitudepontoconexao",
    ]

    colunas_ausentes = [
        coluna
        for coluna in colunas_obrigatorias
        if coluna
        not in df_curtailment_georreferenciado.columns
    ]

    if colunas_ausentes:
        raise ValueError(
            "Colunas ausentes para preparar as usinas: "
            f"{colunas_ausentes}"
        )

    usinas_df = (
        df_curtailment_georreferenciado
        .drop_duplicates(
            subset=["nom_usina"],
            keep="first",
        )
        .copy()
    )

    gdf_usinas = gpd.GeoDataFrame(
        usinas_df,
        geometry=gpd.points_from_xy(
            usinas_df[
                "val_longitudepontoconexao"
            ],
            usinas_df[
                "val_latitudepontoconexao"
            ],
        ),
        crs=CRS_MAPA,
    )

    geometrias_invalidas = (
        gdf_usinas.geometry.isna()
        | gdf_usinas.geometry.is_empty
        | ~gdf_usinas.geometry.is_valid
    )

    coordenadas_compartilhadas = (
        gdf_usinas[
            [
                "val_latitudepontoconexao",
                "val_longitudepontoconexao",
            ]
        ]
        .duplicated(
            keep=False,
        )
    )

    relatorio = {
        "usinas_no_geodataframe": len(gdf_usinas),
        "nomes_distintos": int(
            gdf_usinas["nom_usina"].nunique()
        ),
        "geometrias_invalidas": int(
            geometrias_invalidas.sum()
        ),
        "usinas_em_coordenadas_compartilhadas": int(
            coordenadas_compartilhadas.sum()
        ),
        "crs": str(gdf_usinas.crs),
    }

    return gdf_usinas, relatorio


def criar_geometrias_pontos(
    df_curtailment_georreferenciado: pd.DataFrame,
) -> tuple[gpd.GeoDataFrame, dict]:
    """
    Cria um GeoDataFrame com uma geometria para cada ponto
    de conexão.

    Cada ponto é identificado pelo nome presente na coluna
    nom_pontoconexao, reproduzindo a regra do mapa original.

    Parâmetros
    ----------
    df_curtailment_georreferenciado : pandas.DataFrame
        Base de curtailment contendo pontos e coordenadas.

    Retorno
    -------
    tuple
        GeoDataFrame de pontos e relatório de qualidade.

    Raises
    ------
    ValueError
        Quando a base não foi informada, está vazia ou não
        possui as colunas necessárias.
    """

    if df_curtailment_georreferenciado is None:
        raise ValueError(
            "A base georreferenciada de curtailment "
            "não foi informada."
        )

    if df_curtailment_georreferenciado.empty:
        raise ValueError(
            "A base georreferenciada de curtailment está vazia."
        )

    colunas_obrigatorias = [
        "nom_pontoconexao",
        "val_latitudepontoconexao",
        "val_longitudepontoconexao",
    ]

    colunas_ausentes = [
        coluna
        for coluna in colunas_obrigatorias
        if coluna
        not in df_curtailment_georreferenciado.columns
    ]

    if colunas_ausentes:
        raise ValueError(
            "Colunas ausentes para preparar os pontos: "
            f"{colunas_ausentes}"
        )

    pontos_df = (
        df_curtailment_georreferenciado
        .drop_duplicates(
            subset=["nom_pontoconexao"],
            keep="first",
        )
        .copy()
    )

    gdf_pontos = gpd.GeoDataFrame(
        pontos_df,
        geometry=gpd.points_from_xy(
            pontos_df[
                "val_longitudepontoconexao"
            ],
            pontos_df[
                "val_latitudepontoconexao"
            ],
        ),
        crs=CRS_MAPA,
    )

    geometrias_invalidas = (
        gdf_pontos.geometry.isna()
        | gdf_pontos.geometry.is_empty
        | ~gdf_pontos.geometry.is_valid
    )

    relatorio = {
        "pontos_no_geodataframe": len(gdf_pontos),
        "nomes_distintos": int(
            gdf_pontos[
                "nom_pontoconexao"
            ].nunique()
        ),
        "geometrias_invalidas": int(
            geometrias_invalidas.sum()
        ),
        "crs": str(gdf_pontos.crs),
    }

    return gdf_pontos, relatorio


def criar_geometrias_linhas(
    df_linhas_georreferenciadas: pd.DataFrame,
) -> tuple[
    gpd.GeoDataFrame,
    gpd.GeoDataFrame,
    dict,
]:
    """
    Cria as geometrias LineString das linhas de transmissão.

    A função mantém todas as linhas que possuem as quatro
    coordenadas necessárias e cria uma segunda camada contendo
    somente as geometrias válidas e com extremidades distintas.

    Parâmetros
    ----------
    df_linhas_georreferenciadas : pandas.DataFrame
        Base contendo as coordenadas das extremidades
        DE e PARA.

    Retorno
    -------
    tuple
        O primeiro elemento é o GeoDataFrame com todas as
        linhas que possuem coordenadas completas.

        O segundo elemento é o GeoDataFrame contendo somente
        as linhas efetivamente desenháveis.

        O terceiro elemento é um dicionário com o relatório
        de qualidade das geometrias.

    Raises
    ------
    ValueError
        Quando a base não foi informada, está vazia, não possui
        as colunas necessárias ou ainda contém coordenadas
        ausentes.
    """

    if df_linhas_georreferenciadas is None:
        raise ValueError(
            "A base georreferenciada de linhas "
            "não foi informada."
        )

    if df_linhas_georreferenciadas.empty:
        raise ValueError(
            "A base georreferenciada de linhas está vazia."
        )

    colunas_ausentes = [
        coluna
        for coluna in COLUNAS_COORDENADAS_LINHAS
        if coluna not in df_linhas_georreferenciadas.columns
    ]

    if colunas_ausentes:
        raise ValueError(
            "Colunas ausentes para preparar as linhas: "
            f"{colunas_ausentes}"
        )

    linhas = df_linhas_georreferenciadas.copy()

    for coluna in COLUNAS_COORDENADAS_LINHAS:
        linhas[coluna] = pd.to_numeric(
            linhas[coluna],
            errors="coerce",
        )

    possui_coordenadas = (
        linhas[
            COLUNAS_COORDENADAS_LINHAS
        ]
        .notna()
        .all(axis=1)
    )

    if not possui_coordenadas.all():
        quantidade_sem_coordenadas = int(
            (~possui_coordenadas).sum()
        )

        raise ValueError(
            "A base informada ainda possui "
            f"{quantidade_sem_coordenadas:,} linhas sem as "
            "quatro coordenadas necessárias. Utilize primeiro "
            "preparar_base_geografica_linhas()."
        )

    linhas["geometry"] = linhas.apply(
        lambda linha: LineString(
            [
                (
                    linha["val_longitude_de"],
                    linha["val_latitude_de"],
                ),
                (
                    linha["val_longitude_para"],
                    linha["val_latitude_para"],
                ),
            ]
        ),
        axis=1,
    )

    gdf_linhas = gpd.GeoDataFrame(
        linhas,
        geometry="geometry",
        crs=CRS_MAPA,
    )

    geometrias_invalidas = (
        gdf_linhas.geometry.isna()
        | gdf_linhas.geometry.is_empty
        | ~gdf_linhas.geometry.is_valid
    )

    extremidades_coincidentes = (
        (
            gdf_linhas["val_latitude_de"]
            == gdf_linhas["val_latitude_para"]
        )
        & (
            gdf_linhas["val_longitude_de"]
            == gdf_linhas["val_longitude_para"]
        )
    )

    linhas_desenhaveis = (
        ~geometrias_invalidas
        & ~extremidades_coincidentes
    )

    gdf_linhas_desenhaveis = (
        gdf_linhas.loc[
            linhas_desenhaveis
        ]
        .copy()
    )

    quantidade_linhas = len(gdf_linhas)

    quantidade_desenhaveis = int(
        linhas_desenhaveis.sum()
    )

    relatorio = {
        "linhas_no_geodataframe": quantidade_linhas,
        "geometrias_invalidas": int(
            geometrias_invalidas.sum()
        ),
        "linhas_com_extremidades_coincidentes": int(
            extremidades_coincidentes.sum()
        ),
        "linhas_desenhaveis": quantidade_desenhaveis,
        "linhas_nao_desenhaveis": int(
            quantidade_linhas
            - quantidade_desenhaveis
        ),
        "percentual_desenhavel_sobre_georreferenciadas": round(
            linhas_desenhaveis.mean() * 100,
            2,
        ),
        "crs": str(gdf_linhas.crs),
    }

    return (
        gdf_linhas,
        gdf_linhas_desenhaveis,
        relatorio,
    )


def criar_indice_busca(
    gdf_usinas: gpd.GeoDataFrame,
    gdf_pontos: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, dict]:
    """
    Cria o GeoDataFrame usado pela busca do mapa.

    O índice reúne as usinas e os pontos de conexão em uma
    estrutura única com tipo, nome, ponto e geometria.

    Parâmetros
    ----------
    gdf_usinas : geopandas.GeoDataFrame
        GeoDataFrame de usinas.
    gdf_pontos : geopandas.GeoDataFrame
        GeoDataFrame de pontos de conexão.

    Retorno
    -------
    tuple
        GeoDataFrame de busca e relatório de qualidade.

    Raises
    ------
    ValueError
        Quando algum GeoDataFrame não foi informado ou ambos
        estão vazios.
    TypeError
        Quando os objetos informados não são GeoDataFrames.
    """

    if gdf_usinas is None or gdf_pontos is None:
        raise ValueError(
            "Os GeoDataFrames de usinas e pontos "
            "devem ser informados."
        )

    if not isinstance(
        gdf_usinas,
        gpd.GeoDataFrame,
    ):
        raise TypeError(
            "gdf_usinas deve ser um GeoDataFrame."
        )

    if not isinstance(
        gdf_pontos,
        gpd.GeoDataFrame,
    ):
        raise TypeError(
            "gdf_pontos deve ser um GeoDataFrame."
        )

    if gdf_usinas.empty and gdf_pontos.empty:
        raise ValueError(
            "Os GeoDataFrames de usinas e pontos estão vazios."
        )

    registros_busca = []

    for _, linha in gdf_usinas.iterrows():
        nome_usina = linha.get(
            "nom_usina",
            "Usina",
        )

        nome_ponto = linha.get(
            "nom_pontoconexao",
            "",
        )

        registros_busca.append(
            {
                "tipo": "Usina",
                "nome": (
                    "Usina"
                    if pd.isna(nome_usina)
                    else str(nome_usina)
                ),
                "ponto": (
                    ""
                    if pd.isna(nome_ponto)
                    else str(nome_ponto)
                ),
                "geometry": linha.geometry,
            }
        )

    for _, linha in gdf_pontos.iterrows():
        nome_ponto = linha.get(
            "nom_pontoconexao",
            "Ponto",
        )

        nome_ponto = (
            "Ponto"
            if pd.isna(nome_ponto)
            else str(nome_ponto)
        )

        registros_busca.append(
            {
                "tipo": "Ponto",
                "nome": nome_ponto,
                "ponto": nome_ponto,
                "geometry": linha.geometry,
            }
        )

    gdf_busca = gpd.GeoDataFrame(
        registros_busca,
        geometry="geometry",
        crs=CRS_MAPA,
    )

    geometrias_invalidas = (
        gdf_busca.geometry.isna()
        | gdf_busca.geometry.is_empty
        | ~gdf_busca.geometry.is_valid
    )

    relatorio = {
        "registros_busca": len(gdf_busca),
        "registros_usinas": int(
            (gdf_busca["tipo"] == "Usina").sum()
        ),
        "registros_pontos": int(
            (gdf_busca["tipo"] == "Ponto").sum()
        ),
        "geometrias_invalidas": int(
            geometrias_invalidas.sum()
        ),
        "crs": str(gdf_busca.crs),
    }

    return gdf_busca, relatorio


def tornar_geodataframe_serializavel(
    gdf: gpd.GeoDataFrame,
    colunas_manter: Optional[list[str]] = None,
) -> gpd.GeoDataFrame:
    """
    Converte as colunas de um GeoDataFrame para tipos
    serializáveis pelo GeoJSON e pelo Folium.

    O GeoDataFrame original não é modificado.

    Valores NaN, positivos infinitos e negativos infinitos
    são substituídos por None.

    Parâmetros
    ----------
    gdf : geopandas.GeoDataFrame
        GeoDataFrame que será preparado.
    colunas_manter : list[str] ou None, opcional
        Colunas que devem ser mantidas além da geometria.
        Quando não informado, todas as colunas são preservadas.

    Retorno
    -------
    geopandas.GeoDataFrame
        Cópia preparada para serialização.

    Raises
    ------
    ValueError
        Quando o GeoDataFrame não foi informado ou alguma
        coluna solicitada não existe.
    TypeError
        Quando o objeto informado não é um GeoDataFrame.
    """

    if gdf is None:
        raise ValueError(
            "O GeoDataFrame não foi informado."
        )

    if not isinstance(
        gdf,
        gpd.GeoDataFrame,
    ):
        raise TypeError(
            "O objeto informado deve ser um GeoDataFrame."
        )

    resultado = gdf.copy()

    if colunas_manter is not None:
        colunas_ausentes = [
            coluna
            for coluna in colunas_manter
            if (
                coluna != "geometry"
                and coluna not in resultado.columns
            )
        ]

        if colunas_ausentes:
            raise ValueError(
                "Colunas solicitadas não encontradas no "
                f"GeoDataFrame: {colunas_ausentes}"
            )

        colunas_seguras = [
            coluna
            for coluna in colunas_manter
            if coluna != "geometry"
        ]

        resultado = resultado[
            colunas_seguras + ["geometry"]
        ].copy()

    for coluna in resultado.columns:
        if coluna == "geometry":
            continue

        serie = resultado[coluna]

        if pd.api.types.is_datetime64_any_dtype(
            serie
        ):
            valores_formatados = (
                serie
                .dt.strftime("%Y-%m-%d %H:%M:%S")
                .astype(object)
            )

            resultado[coluna] = (
                valores_formatados
                .where(serie.notna(), None)
            )

        elif isinstance(
            serie.dtype,
            pd.CategoricalDtype,
        ):
            resultado[coluna] = (
                serie
                .astype("string")
                .astype(object)
                .where(serie.notna(), None)
            )

        elif isinstance(
            serie.dtype,
            pd.PeriodDtype,
        ):
            resultado[coluna] = (
                serie
                .astype("string")
                .astype(object)
                .where(serie.notna(), None)
            )

        elif pd.api.types.is_timedelta64_dtype(
            serie
        ):
            resultado[coluna] = (
                serie
                .astype("string")
                .astype(object)
                .where(serie.notna(), None)
            )

        elif (
            pd.api.types.is_integer_dtype(serie)
            or pd.api.types.is_float_dtype(serie)
            or pd.api.types.is_bool_dtype(serie)
        ):
            resultado[coluna] = (
                serie
                .astype(object)
                .where(serie.notna(), None)
            )

        else:
            resultado[coluna] = (
                serie
                .astype(object)
                .where(serie.notna(), None)
            )

    resultado = resultado.replace(
        {
            np.nan: None,
            np.inf: None,
            -np.inf: None,
        }
    )

    return resultado
