"""
Construção do mapa interativo de curtailment.

O módulo cria o mapa-base, adiciona os limites das UFs,
as usinas, os pontos de conexão, as linhas de transmissão,
a barra de busca e o controle de camadas.

O módulo também integra as séries horárias ao HTML, cria
um painel lateral para seleção das feições e apresenta
indicadores e gráficos por usina e ponto de conexão.
"""

import json
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
from branca.element import Element, JavascriptLink
from folium.plugins import MarkerCluster, Search


CENTRO_MAPA_BRASIL = [
    -15.0,
    -52.0,
]

ZOOM_INICIAL = 4

COR_USINA_EOL = "#1f77b4"
COR_USINA_UFV = "#ff7f0e"
COR_PONTO_CONEXAO = "#2ca02c"
COR_LINHA_TRANSMISSAO = "#d62728"
COR_DESTAQUE_LINHA = "#ff6600"
COR_LIMITE_UF = "#666666"

CRS_MAPA = "EPSG:4326"

COLUNAS_BUSCA = [
    "tipo",
    "nome",
    "ponto",
    "geometry",
]

COLUNAS_LINHAS_MAPA = [
    "cod_equipamento",
    "nom_linhadetransmissao",
    "nom_subestacao_de",
    "nom_subestacao_para",
    "num_barra_de",
    "num_barra_para",
    "geometry",
]


def carregar_malha_ufs(
    caminho_geojson,
):
    """
    Carrega e valida a malha simplificada das UFs.

    Parâmetros
    ----------
    caminho_geojson : str ou pathlib.Path
        Caminho do arquivo estados_brasil.geojson.

    Retorno
    -------
    tuple
        GeoDataFrame das UFs e relatório de qualidade.

    Raises
    ------
    FileNotFoundError
        Quando o arquivo não existe.
    ValueError
        Quando a malha está vazia, não possui geometria
        ou contém geometrias inválidas.
    """

    caminho = Path(
        caminho_geojson
    )

    if not caminho.exists():
        raise FileNotFoundError(
            "O arquivo da malha das UFs não foi encontrado: "
            f"{caminho}"
        )

    gdf_ufs = gpd.read_file(
        caminho
    )

    if gdf_ufs.empty:
        raise ValueError(
            "A malha das UFs está vazia."
        )

    if "geometry" not in gdf_ufs.columns:
        raise ValueError(
            "A malha das UFs não possui uma coluna geometry."
        )

    if gdf_ufs.crs is None:
        gdf_ufs = gdf_ufs.set_crs(
            CRS_MAPA
        )
    else:
        gdf_ufs = gdf_ufs.to_crs(
            CRS_MAPA
        )

    geometrias_ausentes = (
        gdf_ufs.geometry.isna()
    )

    geometrias_vazias = (
        gdf_ufs.geometry.is_empty
    )

    geometrias_invalidas = (
        ~gdf_ufs.geometry.is_valid
    )

    if geometrias_ausentes.any():
        raise ValueError(
            "A malha das UFs possui geometrias ausentes."
        )

    if geometrias_vazias.any():
        raise ValueError(
            "A malha das UFs possui geometrias vazias."
        )

    if geometrias_invalidas.any():
        raise ValueError(
            "A malha das UFs possui geometrias inválidas."
        )

    if "cod_uf" in gdf_ufs.columns:
        quantidade_ufs = int(
            gdf_ufs["cod_uf"].nunique(
                dropna=True
            )
        )
    else:
        quantidade_ufs = len(
            gdf_ufs
        )

    relatorio = {
        "registros_ufs": len(
            gdf_ufs
        ),
        "ufs_distintas": quantidade_ufs,
        "geometrias_ausentes": int(
            geometrias_ausentes.sum()
        ),
        "geometrias_vazias": int(
            geometrias_vazias.sum()
        ),
        "geometrias_invalidas": int(
            geometrias_invalidas.sum()
        ),
        "crs": str(
            gdf_ufs.crs
        ),
    }

    return gdf_ufs, relatorio


def validar_camadas_mapa(
    gdf_usinas,
    gdf_pontos,
    gdf_linhas_desenhaveis,
    gdf_busca,
):
    """
    Valida as camadas geográficas recebidas pelo mapa.

    Retorno
    -------
    dict
        Relatório com as dimensões e o CRS das camadas.
    """

    camadas = {
        "usinas": gdf_usinas,
        "pontos": gdf_pontos,
        "linhas": gdf_linhas_desenhaveis,
        "busca": gdf_busca,
    }

    for nome, camada in camadas.items():
        if camada is None:
            raise ValueError(
                f"A camada {nome} não foi informada."
            )

        if not isinstance(
            camada,
            gpd.GeoDataFrame,
        ):
            raise TypeError(
                f"A camada {nome} deve ser um GeoDataFrame."
            )

        if camada.empty:
            raise ValueError(
                f"A camada {nome} está vazia."
            )

        if "geometry" not in camada.columns:
            raise ValueError(
                f"A camada {nome} não possui geometry."
            )

        if camada.crs is None:
            raise ValueError(
                f"A camada {nome} não possui CRS definido."
            )

    colunas_usinas = [
        "nom_usina",
    ]

    colunas_pontos = [
        "nom_pontoconexao",
    ]

    colunas_busca_ausentes = [
        coluna
        for coluna in COLUNAS_BUSCA
        if coluna not in gdf_busca.columns
    ]

    colunas_usinas_ausentes = [
        coluna
        for coluna in colunas_usinas
        if coluna not in gdf_usinas.columns
    ]

    colunas_pontos_ausentes = [
        coluna
        for coluna in colunas_pontos
        if coluna not in gdf_pontos.columns
    ]

    if colunas_usinas_ausentes:
        raise ValueError(
            "Colunas ausentes na camada de usinas: "
            f"{colunas_usinas_ausentes}"
        )

    if colunas_pontos_ausentes:
        raise ValueError(
            "Colunas ausentes na camada de pontos: "
            f"{colunas_pontos_ausentes}"
        )

    if colunas_busca_ausentes:
        raise ValueError(
            "Colunas ausentes na camada de busca: "
            f"{colunas_busca_ausentes}"
        )

    geometrias_invalidas = {}

    for nome, camada in camadas.items():
        invalidas = (
            camada.geometry.isna()
            | camada.geometry.is_empty
            | ~camada.geometry.is_valid
        )

        geometrias_invalidas[
            nome
        ] = int(
            invalidas.sum()
        )

    if any(
        valor > 0
        for valor in geometrias_invalidas.values()
    ):
        raise ValueError(
            "Existem geometrias inválidas nas camadas: "
            f"{geometrias_invalidas}"
        )

    relatorio = {
        "usinas": len(
            gdf_usinas
        ),
        "pontos": len(
            gdf_pontos
        ),
        "linhas_desenhaveis": len(
            gdf_linhas_desenhaveis
        ),
        "registros_busca": len(
            gdf_busca
        ),
        "geometrias_invalidas": (
            geometrias_invalidas
        ),
        "crs_usinas": str(
            gdf_usinas.crs
        ),
        "crs_pontos": str(
            gdf_pontos.crs
        ),
        "crs_linhas": str(
            gdf_linhas_desenhaveis.crs
        ),
        "crs_busca": str(
            gdf_busca.crs
        ),
    }

    return relatorio


def obter_fonte_usina(
    linha,
):
    """
    Obtém a fonte da usina considerando possíveis nomes
    de coluna utilizados nas bases.
    """

    for coluna in [
        "fonte",
        "Fonte",
    ]:
        if coluna in linha.index:
            valor = linha.get(
                coluna
            )

            if pd.notna(valor):
                return str(
                    valor
                ).strip().upper()

    return ""


def obter_cor_usina(
    fonte,
):
    """
    Retorna a cor do marcador de acordo com a fonte.
    """

    if fonte == "UFV":
        return COR_USINA_UFV

    return COR_USINA_EOL


def adicionar_camadas_ufs(
    mapa,
    gdf_ufs,
):
    """
    Adiciona os limites das UFs ao mapa.
    """

    camada_ufs = folium.GeoJson(
        data=gdf_ufs,
        name="UFs",
        style_function=lambda elemento: {
            "fill": False,
            "fillOpacity": 0,
            "color": COR_LIMITE_UF,
            "weight": 1,
            "opacity": 0.8,
        },
        highlight_function=lambda elemento: {
            "fill": False,
            "fillOpacity": 0,
            "color": "#333333",
            "weight": 2,
            "opacity": 1,
        },
        show=True,
        control=True,
    )

    camada_ufs.add_to(
        mapa
    )

    return camada_ufs


def adicionar_camadas_usinas(
    mapa,
    gdf_usinas,
):
    """
    Adiciona os marcadores agrupados das usinas.
    """

    grupo_usinas = folium.FeatureGroup(
        name="Usinas",
        show=True,
    )

    grupo_usinas.add_to(
        mapa
    )

    cluster_usinas = MarkerCluster(
        name="Usinas agrupadas",
        disableClusteringAtZoom=8,
    )

    cluster_usinas.add_to(
        grupo_usinas
    )

    for _, linha in gdf_usinas.iterrows():
        geometria = linha.geometry

        fonte = obter_fonte_usina(
            linha
        )

        nome_usina = linha.get(
            "nom_usina",
            "Usina",
        )

        if pd.isna(nome_usina):
            nome_usina = "Usina"
        else:
            nome_usina = str(
                nome_usina
            )

        cor = obter_cor_usina(
            fonte
        )

        texto_tooltip = nome_usina

        if fonte:
            texto_tooltip = (
                f"{nome_usina} | {fonte}"
            )

        marcador = folium.CircleMarker(
            location=[
                geometria.y,
                geometria.x,
            ],
            radius=5,
            color=cor,
            weight=1,
            fill=True,
            fill_color=cor,
            fill_opacity=0.75,
            tooltip=texto_tooltip,
        )

        marcador.add_to(
            cluster_usinas
        )

    return (
        grupo_usinas,
        cluster_usinas,
    )


def adicionar_camadas_pontos(
    mapa,
    gdf_pontos,
):
    """
    Adiciona os marcadores agrupados dos pontos de conexão.
    """

    grupo_pontos = folium.FeatureGroup(
        name="Pontos de Conexão",
        show=False,
    )

    grupo_pontos.add_to(
        mapa
    )

    cluster_pontos = MarkerCluster(
        name="Pontos agrupados",
        disableClusteringAtZoom=8,
    )

    cluster_pontos.add_to(
        grupo_pontos
    )

    for _, linha in gdf_pontos.iterrows():
        geometria = linha.geometry

        nome_ponto = linha.get(
            "nom_pontoconexao",
            "Ponto de Conexão",
        )

        if pd.isna(nome_ponto):
            nome_ponto = (
                "Ponto de Conexão"
            )
        else:
            nome_ponto = str(
                nome_ponto
            )

        marcador = folium.CircleMarker(
            location=[
                geometria.y,
                geometria.x,
            ],
            radius=4,
            color=COR_PONTO_CONEXAO,
            weight=1,
            fill=True,
            fill_color=COR_PONTO_CONEXAO,
            fill_opacity=0.75,
            tooltip=nome_ponto,
        )

        marcador.add_to(
            cluster_pontos
        )

    return (
        grupo_pontos,
        cluster_pontos,
    )


def preparar_atributos_linhas(
    gdf_linhas,
):
    """
    Seleciona atributos relevantes para a camada de linhas.
    """

    colunas_disponiveis = [
        coluna
        for coluna in COLUNAS_LINHAS_MAPA
        if coluna in gdf_linhas.columns
    ]

    if "geometry" not in colunas_disponiveis:
        colunas_disponiveis.append(
            "geometry"
        )

    linhas_mapa = (
        gdf_linhas[
            colunas_disponiveis
        ]
        .copy()
    )

    for coluna in linhas_mapa.columns:
        if coluna == "geometry":
            continue

        serie = linhas_mapa[coluna]

        if pd.api.types.is_datetime64_any_dtype(
            serie
        ):
            linhas_mapa[coluna] = (
                serie
                .dt.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                .astype(object)
                .where(
                    serie.notna(),
                    None,
                )
            )
        else:
            linhas_mapa[coluna] = (
                serie
                .astype(object)
                .where(
                    serie.notna(),
                    None,
                )
            )

    return linhas_mapa


def adicionar_camada_linhas(
    mapa,
    gdf_linhas_desenhaveis,
):
    """
    Adiciona as linhas de transmissão ao mapa.
    """

    linhas_mapa = preparar_atributos_linhas(
        gdf_linhas_desenhaveis
    )

    camada_linhas = folium.GeoJson(
        data=linhas_mapa,
        name="Linhas de Transmissão",
        style_function=lambda elemento: {
            "color": COR_LINHA_TRANSMISSAO,
            "weight": 2,
            "opacity": 0.75,
        },
        highlight_function=lambda elemento: {
            "color": COR_DESTAQUE_LINHA,
            "weight": 4,
            "opacity": 1,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[
                coluna
                for coluna in [
                    "cod_equipamento",
                    "nom_linhadetransmissao",
                    "nom_subestacao_de",
                    "nom_subestacao_para",
                ]
                if coluna in linhas_mapa.columns
            ],
            aliases=[
                alias
                for coluna, alias in [
                    (
                        "cod_equipamento",
                        "Código",
                    ),
                    (
                        "nom_linhadetransmissao",
                        "Linha",
                    ),
                    (
                        "nom_subestacao_de",
                        "Subestação DE",
                    ),
                    (
                        "nom_subestacao_para",
                        "Subestação PARA",
                    ),
                ]
                if coluna in linhas_mapa.columns
            ],
            labels=True,
            sticky=False,
        ),
        show=True,
    )

    camada_linhas.add_to(
        mapa
    )

    return camada_linhas


def adicionar_busca(
    mapa,
    gdf_busca,
):
    """
    Adiciona um índice GeoJSON invisível e uma barra
    de busca para usinas e pontos.
    """

    busca_mapa = (
        gdf_busca[
            COLUNAS_BUSCA
        ]
        .copy()
    )

    camada_busca = folium.GeoJson(
        data=busca_mapa,
        name="Índice de busca",
        style_function=lambda elemento: {
            "opacity": 0,
            "fillOpacity": 0,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "tipo",
                "nome",
                "ponto",
            ],
            aliases=[
                "Tipo",
                "Nome",
                "Ponto",
            ],
            labels=True,
            sticky=False,
        ),
        show=False,
    )

    camada_busca.add_to(
        mapa
    )

    controle_busca = Search(
        layer=camada_busca,
        search_label="nome",
        placeholder=(
            "Buscar usina ou ponto..."
        ),
        collapsed=False,
        geom_type="Point",
        position="topright",
        search_zoom=10,
    )

    controle_busca.add_to(
        mapa
    )

    return (
        camada_busca,
        controle_busca,
    )

def criar_mapa_inicial(
    gdf_ufs,
):
    """
    Cria o mapa apresentado antes da execução do pipeline.

    O mapa inicial contém a camada-base e os limites das UFs,
    sem usinas, pontos de conexão, linhas de transmissão,
    busca ou painel de gráficos.

    Parâmetros
    ----------
    gdf_ufs : geopandas.GeoDataFrame
        Malha geográfica das UFs.

    Retorno
    -------
    tuple
        Mapa inicial e relatório da construção.
    """

    if gdf_ufs is None:
        raise ValueError(
            "A camada das UFs não foi informada."
        )

    if not isinstance(
        gdf_ufs,
        gpd.GeoDataFrame,
    ):
        raise TypeError(
            "A camada das UFs deve ser um GeoDataFrame."
        )

    if gdf_ufs.empty:
        raise ValueError(
            "A camada das UFs está vazia."
        )

    if gdf_ufs.crs is None:
        raise ValueError(
            "A camada das UFs não possui CRS definido."
        )

    geometrias_invalidas = (
        gdf_ufs.geometry.isna()
        | gdf_ufs.geometry.is_empty
        | ~gdf_ufs.geometry.is_valid
    )

    if geometrias_invalidas.any():
        raise ValueError(
            "A camada das UFs possui "
            f"{int(geometrias_invalidas.sum())} "
            "geometrias inválidas."
        )

    mapa = folium.Map(
        location=CENTRO_MAPA_BRASIL,
        zoom_start=ZOOM_INICIAL,
        tiles="CartoDB positron",
        control_scale=True,
        zoom_control=True,
        prefer_canvas=True,
    )

    camada_ufs = adicionar_camadas_ufs(
        mapa=mapa,
        gdf_ufs=gdf_ufs,
    )

    relatorio = {
        "tipo_mapa": "inicial",
        "ufs": len(
            gdf_ufs
        ),
        "crs_ufs": str(
            gdf_ufs.crs
        ),
        "geometrias_ufs_invalidas": int(
            geometrias_invalidas.sum()
        ),
        "centro_mapa": (
            CENTRO_MAPA_BRASIL.copy()
        ),
        "zoom_inicial": ZOOM_INICIAL,
        "mapa_base": "CartoDB positron",
        "camada_ufs": (
            camada_ufs.get_name()
        ),
        "usinas": 0,
        "pontos": 0,
        "linhas": 0,
        "painel_lateral": False,
        "graficos_series": False,
    }

    return mapa, relatorio

def criar_mapa_basico(
    gdf_ufs,
    gdf_usinas,
    gdf_pontos,
    gdf_linhas_desenhaveis,
    gdf_busca,
):
    """
    Cria o mapa interativo básico de curtailment.

    O mapa utiliza CartoDB positron como camada-base e
    adiciona as UFs, usinas, pontos de conexão, linhas de
    transmissão, índice de busca e controle de camadas.

    As UFs, usinas e linhas começam visíveis. Os pontos de
    conexão e o índice de busca começam desativados.

    Parâmetros
    ----------
    gdf_ufs : geopandas.GeoDataFrame
        Malha simplificada das UFs.
    gdf_usinas : geopandas.GeoDataFrame
        Camada das usinas georreferenciadas.
    gdf_pontos : geopandas.GeoDataFrame
        Camada dos pontos de conexão.
    gdf_linhas_desenhaveis : geopandas.GeoDataFrame
        Camada das linhas de transmissão desenháveis.
    gdf_busca : geopandas.GeoDataFrame
        Índice geográfico de busca.

    Retorno
    -------
    tuple
        Objeto Folium Map e relatório da criação.
    """

    if gdf_ufs is None:
        raise ValueError(
            "A camada das UFs não foi informada."
        )

    if not isinstance(
        gdf_ufs,
        gpd.GeoDataFrame,
    ):
        raise TypeError(
            "A camada das UFs deve ser um GeoDataFrame."
        )

    if gdf_ufs.empty:
        raise ValueError(
            "A camada das UFs está vazia."
        )

    if gdf_ufs.crs is None:
        raise ValueError(
            "A camada das UFs não possui CRS definido."
        )

    geometrias_ufs_invalidas = (
        gdf_ufs.geometry.isna()
        | gdf_ufs.geometry.is_empty
        | ~gdf_ufs.geometry.is_valid
    )

    if geometrias_ufs_invalidas.any():
        raise ValueError(
            "A camada das UFs possui "
            f"{int(geometrias_ufs_invalidas.sum())} "
            "geometrias inválidas."
        )

    relatorio_camadas = validar_camadas_mapa(
        gdf_usinas=gdf_usinas,
        gdf_pontos=gdf_pontos,
        gdf_linhas_desenhaveis=(
            gdf_linhas_desenhaveis
        ),
        gdf_busca=gdf_busca,
    )

    mapa = folium.Map(
        location=CENTRO_MAPA_BRASIL,
        zoom_start=ZOOM_INICIAL,
        tiles="CartoDB positron",
        control_scale=True,
        zoom_control=True,
        prefer_canvas=True,
    )

    camada_ufs = adicionar_camadas_ufs(
        mapa=mapa,
        gdf_ufs=gdf_ufs,
    )

    (
        grupo_usinas,
        cluster_usinas,
    ) = adicionar_camadas_usinas(
        mapa=mapa,
        gdf_usinas=gdf_usinas,
    )

    (
        grupo_pontos,
        cluster_pontos,
    ) = adicionar_camadas_pontos(
        mapa=mapa,
        gdf_pontos=gdf_pontos,
    )

    quantidade_marcadores_usinas = len(
        gdf_usinas
    )

    quantidade_marcadores_pontos = len(
        gdf_pontos
    )

    camada_linhas = adicionar_camada_linhas(
        mapa=mapa,
        gdf_linhas_desenhaveis=(
            gdf_linhas_desenhaveis
        ),
    )

    (
        camada_busca,
        controle_busca,
    ) = adicionar_busca(
        mapa=mapa,
        gdf_busca=gdf_busca,
    )

    folium.LayerControl(
        collapsed=False,
        position="topright",
    ).add_to(
        mapa
    )

    relatorio = {
        **relatorio_camadas,
        "ufs": len(
            gdf_ufs
        ),
        "crs_ufs": str(
            gdf_ufs.crs
        ),
        "geometrias_ufs_invalidas": int(
            geometrias_ufs_invalidas.sum()
        ),
        "marcadores_usinas_adicionados": (
            quantidade_marcadores_usinas
        ),
        "marcadores_pontos_adicionados": (
            quantidade_marcadores_pontos
        ),
        "centro_mapa": (
            CENTRO_MAPA_BRASIL.copy()
        ),
        "zoom_inicial": ZOOM_INICIAL,
        "enquadramento_automatico": False,
        "mapa_base_externo": True,
        "mapa_base": "CartoDB positron",
        "camadas_inicialmente_visiveis": [
            "UFs",
            "Usinas",
            "Linhas de Transmissão",
        ],
        "camadas_inicialmente_ocultas": [
            "Pontos de Conexão",
            "Índice de busca",
        ],
        "camadas_visiveis_no_controle": [
            "CartoDB positron",
            "UFs",
            "Usinas",
            "Pontos de Conexão",
            "Linhas de Transmissão",
            "Índice de busca",
        ],
        "camada_ufs": (
            camada_ufs.get_name()
        ),
        "grupo_usinas": (
            grupo_usinas.get_name()
        ),
        "cluster_usinas": (
            cluster_usinas.get_name()
        ),
        "grupo_pontos": (
            grupo_pontos.get_name()
        ),
        "cluster_pontos": (
            cluster_pontos.get_name()
        ),
        "camada_linhas": (
            camada_linhas.get_name()
        ),
        "camada_busca": (
            camada_busca.get_name()
        ),
        "controle_busca": (
            controle_busca.get_name()
        ),
    }

    return mapa, relatorio

def serializar_series_mapa(
    usina_series_map,
    ponto_series_by_latlon,
):
    """
    Serializa as séries horárias utilizadas pelo painel.

    Parâmetros
    ----------
    usina_series_map : dict
        Séries das usinas agrupadas por coordenada.
    ponto_series_by_latlon : dict
        Séries dos pontos agrupadas por coordenada.

    Retorno
    -------
    tuple
        JSON das usinas, JSON dos pontos e relatório da
        serialização.
    """

    if usina_series_map is None:
        raise ValueError(
            "As séries geográficas das usinas "
            "não foram informadas."
        )

    if ponto_series_by_latlon is None:
        raise ValueError(
            "As séries geográficas dos pontos "
            "não foram informadas."
        )

    if not isinstance(
        usina_series_map,
        dict,
    ):
        raise TypeError(
            "As séries geográficas das usinas "
            "devem ser um dicionário."
        )

    if not isinstance(
        ponto_series_by_latlon,
        dict,
    ):
        raise TypeError(
            "As séries geográficas dos pontos "
            "devem ser um dicionário."
        )

    json_usinas = json.dumps(
        usina_series_map,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )

    json_pontos = json.dumps(
        ponto_series_by_latlon,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )

    relatorio = {
        "coordenadas_usinas": len(
            usina_series_map
        ),
        "coordenadas_pontos": len(
            ponto_series_by_latlon
        ),
        "tamanho_json_usinas": len(
            json_usinas
        ),
        "tamanho_json_pontos": len(
            json_pontos
        ),
    }

    return (
        json_usinas,
        json_pontos,
        relatorio,
    )


def adicionar_estrutura_painel(
    mapa,
):
    """
    Adiciona ao mapa a estrutura HTML e os estilos básicos
    do painel lateral.

    O painel abre pela esquerda para não cobrir a barra de
    pesquisa localizada no canto superior direito.
    """

    if mapa is None:
        raise ValueError(
            "O mapa não foi informado."
        )

    painel_html = """
    <style>
        #painel-curtailment {
            position: fixed;
            top: 0;
            left: -420px;
            width: 400px;
            height: 100%;
            z-index: 9999;
            background: #ffffff;
            border-right: 1px solid #d0d0d0;
            box-shadow: 4px 0 14px rgba(0, 0, 0, 0.18);
            transition: left 0.25s ease;
            overflow-y: auto;
            box-sizing: border-box;
            padding: 18px;
            font-family: Arial, sans-serif;
        }

        #painel-curtailment.aberto {
            left: 0;
        }

        #painel-curtailment-cabecalho {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 18px;
        }

        #painel-curtailment-titulo {
            margin: 0;
            font-size: 18px;
            color: #222222;
        }

        #painel-curtailment-fechar {
            border: 0;
            background: transparent;
            cursor: pointer;
            font-size: 24px;
            line-height: 1;
            color: #555555;
        }

        #painel-curtailment-conteudo {
            color: #444444;
            font-size: 14px;
            line-height: 1.5;
        }

        #botao-abrir-painel {
            position: fixed;
            top: 20px;
            left: 55px;
            z-index: 9998;
            border: 1px solid #bbbbbb;
            border-radius: 4px;
            background: #ffffff;
            padding: 8px 10px;
            cursor: pointer;
            box-shadow: 0 1px 5px rgba(0, 0, 0, 0.22);
            font-size: 13px;
            color: #333333;
        }

        @media (max-width: 600px) {
            #painel-curtailment {
                left: -100%;
                width: 100%;
            }

            #painel-curtailment.aberto {
                left: 0;
            }
        }
    </style>

    <button
        id="botao-abrir-painel"
        type="button"
        onclick="abrirPainelCurtailment()"
    >
        Abrir painel
    </button>

    <aside id="painel-curtailment">
        <div id="painel-curtailment-cabecalho">
            <h2 id="painel-curtailment-titulo">
                Curtailment
            </h2>

            <button
                id="painel-curtailment-fechar"
                type="button"
                aria-label="Fechar painel"
                onclick="fecharPainelCurtailment()"
            >
                &times;
            </button>
        </div>

        <div id="painel-curtailment-conteudo">
            Selecione uma usina, ponto de conexão ou linha
            de transmissão no mapa.
        </div>
    </aside>

    <script>
        function abrirPainelCurtailment() {
            const painel = document.getElementById(
                "painel-curtailment"
            );

            if (painel) {
                painel.classList.add("aberto");
            }
        }

        function fecharPainelCurtailment() {
            const painel = document.getElementById(
                "painel-curtailment"
            );

            if (painel) {
                painel.classList.remove("aberto");
            }
        }
    </script>
    """

    mapa.get_root().html.add_child(
        Element(
            painel_html
        )
    )

    return mapa


def adicionar_estilos_selecao_painel(
    mapa,
):
    """
    Adiciona os estilos dos menus de seleção e dos cartões
    de usinas e pontos apresentados no painel.
    """

    if mapa is None:
        raise ValueError(
            "O mapa não foi informado."
        )

    estilos = """
    <style>
        .painel-instrucao {
            margin-top: 0;
            margin-bottom: 14px;
            color: #555555;
        }

        .painel-lista-itens {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .painel-item {
            width: 100%;
            border: 1px solid #dddddd;
            border-radius: 7px;
            background: #ffffff;
            padding: 11px 12px;
            text-align: left;
            cursor: pointer;
            display: flex;
            flex-direction: column;
            gap: 3px;
            color: #333333;
        }

        .painel-item:hover {
            background: #f7f7f7;
            border-color: #bbbbbb;
        }

        .painel-item-usina {
            border-left: 4px solid #1f77b4;
        }

        .painel-item-ponto {
            border-left: 4px solid #2ca02c;
        }

        .painel-item-tipo {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            color: #777777;
        }

        .painel-item small {
            color: #666666;
        }

        .painel-voltar {
            border: 0;
            background: transparent;
            color: #2b6cb0;
            cursor: pointer;
            padding: 0;
            margin-bottom: 14px;
            font-size: 13px;
        }

        .painel-voltar:hover {
            text-decoration: underline;
        }

        .painel-cartao-detalhe {
            border: 1px solid #dddddd;
            border-radius: 8px;
            padding: 14px;
            background: #fafafa;
        }

        .painel-cartao-detalhe h3 {
            margin: 5px 0 14px;
            font-size: 17px;
            color: #222222;
        }

        .painel-tipo-item {
            color: #777777;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }

        .painel-observacao {
            margin-top: 18px;
            color: #777777;
            font-size: 12px;
        }
    </style>
    """

    mapa.get_root().html.add_child(
        Element(
            estilos
        )
    )

    return mapa


def adicionar_estilos_graficos_painel(
    mapa,
):
    """
    Adiciona os estilos dos indicadores e gráficos
    apresentados no painel lateral.
    """

    if mapa is None:
        raise ValueError(
            "O mapa não foi informado."
        )

    estilos = """
    <style>
        .painel-identificacao {
            margin-bottom: 14px;
        }

        .painel-identificacao h3 {
            margin: 4px 0 8px;
            color: #222222;
            font-size: 17px;
        }

        .painel-identificacao p {
            margin: 4px 0;
            color: #555555;
            font-size: 13px;
        }

        .painel-kpis {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
            margin: 14px 0;
        }

        .painel-kpi {
            border: 1px solid #dddddd;
            border-radius: 7px;
            background: #fafafa;
            padding: 10px;
            min-height: 62px;
            box-sizing: border-box;
        }

        .painel-kpi-label {
            display: block;
            margin-bottom: 5px;
            color: #777777;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
        }

        .painel-kpi-valor {
            color: #222222;
            font-size: 17px;
            font-weight: 700;
        }

        .painel-grafico {
            margin-top: 14px;
            border: 1px solid #dddddd;
            border-radius: 8px;
            background: #ffffff;
            padding: 10px;
        }

        .painel-grafico h4 {
            margin: 0 0 8px;
            color: #333333;
            font-size: 13px;
        }

        .painel-grafico-canvas {
            position: relative;
            width: 100%;
            height: 220px;
        }

        .painel-grafico-canvas canvas {
            width: 100% !important;
            height: 100% !important;
        }

        .painel-sem-grafico {
            margin-top: 16px;
            border: 1px solid #dddddd;
            border-radius: 7px;
            background: #fafafa;
            padding: 12px;
            color: #666666;
            font-size: 13px;
        }

        @media (max-width: 600px) {
            .painel-kpis {
                grid-template-columns: 1fr;
            }
        }
    </style>
    """

    mapa.get_root().html.add_child(
        Element(
            estilos
        )
    )

    return mapa


def adicionar_chartjs(
    mapa,
):
    """
    Adiciona Chart.js e SheetJS ao HTML do mapa.
    Chart.js renderiza os gráficos do painel lateral.
    SheetJS permite exportar os dados dos gráficos
    para arquivos no formato XLSX.
    """

    if mapa is None:
        raise ValueError(
            "O mapa não foi informado."
        )

    url_chartjs = (
        "https://cdn.jsdelivr.net/npm/"
        "chart.js@4.4.7/dist/"
        "chart.umd.min.js"
    )

    url_sheetjs = (
        "https://cdn.sheetjs.com/"
        "xlsx-0.20.3/package/dist/"
        "xlsx.full.min.js"
    )

    mapa.get_root().header.add_child(
        JavascriptLink(
            url_chartjs
        )
    )

    mapa.get_root().header.add_child(
        JavascriptLink(
            url_sheetjs
        )
    )

    return mapa


def adicionar_series_ao_mapa(
    mapa,
    json_usinas,
    json_pontos,
):
    """
    Injeta no HTML do mapa as séries horárias das usinas
    e dos pontos de conexão.
    """

    if mapa is None:
        raise ValueError(
            "O mapa não foi informado."
        )

    if not isinstance(
        json_usinas,
        str,
    ):
        raise TypeError(
            "O JSON das usinas deve ser uma string."
        )

    if not isinstance(
        json_pontos,
        str,
    ):
        raise TypeError(
            "O JSON dos pontos deve ser uma string."
        )

    if not json_usinas.strip():
        raise ValueError(
            "O JSON das usinas está vazio."
        )

    if not json_pontos.strip():
        raise ValueError(
            "O JSON dos pontos está vazio."
        )

    script_series = f"""
    <script>
        window.USINA_SERIES = {json_usinas};
        window.PONTO_SERIES_BY_LATLON = {json_pontos};

        window.SERIES_MAPA_STATUS = {{
            coordenadasUsinas: Object.keys(
                window.USINA_SERIES
            ).length,
            coordenadasPontos: Object.keys(
                window.PONTO_SERIES_BY_LATLON
            ).length
        }};

        console.log(
            "Séries do mapa carregadas:",
            window.SERIES_MAPA_STATUS
        );
    </script>
    """

    mapa.get_root().html.add_child(
        Element(
            script_series
        )
    )

    return mapa


def localizar_camada_busca(
    mapa,
):
    """
    Localiza a camada GeoJSON utilizada pelo plugin Search.

    Retorno
    -------
    folium.GeoJson
        Camada denominada Índice de busca.
    """

    if mapa is None:
        raise ValueError(
            "O mapa não foi informado."
        )

    for elemento in mapa._children.values():
        if (
            isinstance(
                elemento,
                folium.GeoJson,
            )
            and getattr(
                elemento,
                "layer_name",
                None,
            ) == "Índice de busca"
        ):
            return elemento

    raise ValueError(
        "A camada do índice de busca não foi localizada."
    )


def adicionar_eventos_selecao_painel(
    mapa,
    camada_busca,
    tolerancia=0.0005,
):
    """
    Adiciona eventos para localizar usinas e pontos pelas
    coordenadas e apresentá-los no painel lateral.

    A seleção funciona tanto pelo clique no mapa quanto pelo
    resultado encontrado na barra de busca.

    Parâmetros
    ----------
    mapa : folium.Map
        Mapa que receberá os eventos.
    camada_busca : folium.GeoJson
        Camada GeoJSON utilizada pelo controle de busca.
    tolerancia : float, opcional
        Distância máxima aproximada, em graus, utilizada para
        localizar a coordenada quando não há igualdade exata.

    Retorno
    -------
    folium.Map
        Mapa com os eventos de seleção.
    """

    if mapa is None:
        raise ValueError(
            "O mapa não foi informado."
        )

    if camada_busca is None:
        raise ValueError(
            "A camada de busca não foi informada."
        )

    tolerancia = float(
        tolerancia
    )

    if tolerancia < 0:
        raise ValueError(
            "A tolerância de seleção não pode ser negativa."
        )

    nome_mapa = mapa.get_name()

    nome_controle_busca = (
        f"{camada_busca.get_name()}searchControl"
    )

    script_eventos = """
    <script>
        window.CHAVE_SELECIONADA = null;

        function escaparHtml(valor) {
            if (
                valor === null
                || valor === undefined
            ) {
                return "";
            }

            return String(valor)
                .replaceAll("&", "&amp;")
                .replaceAll("<", "&lt;")
                .replaceAll(">", "&gt;")
                .replaceAll('"', "&quot;")
                .replaceAll("'", "&#039;");
        }

        function criarChaveCoordenadas(
            latitude,
            longitude
        ) {
            return (
                Number(latitude).toFixed(6)
                + ","
                + Number(longitude).toFixed(6)
            );
        }

        function decomporChaveCoordenadas(chave) {
            const partes = String(chave).split(",");

            if (partes.length !== 2) {
                return null;
            }

            const latitude = Number(partes[0]);
            const longitude = Number(partes[1]);

            if (
                !Number.isFinite(latitude)
                || !Number.isFinite(longitude)
            ) {
                return null;
            }

            return {
                latitude: latitude,
                longitude: longitude
            };
        }

        function localizarChaveMaisProxima(
            latitude,
            longitude,
            chaves,
            tolerancia
        ) {
            const chaveExata = criarChaveCoordenadas(
                latitude,
                longitude
            );

            if (chaves.includes(chaveExata)) {
                return chaveExata;
            }

            let melhorChave = null;
            let menorDistancia = Infinity;

            for (const chave of chaves) {
                const coordenada = decomporChaveCoordenadas(
                    chave
                );

                if (!coordenada) {
                    continue;
                }

                const diferencaLatitude = (
                    latitude - coordenada.latitude
                );

                const diferencaLongitude = (
                    longitude - coordenada.longitude
                );

                const distancia = Math.sqrt(
                    diferencaLatitude ** 2
                    + diferencaLongitude ** 2
                );

                if (distancia < menorDistancia) {
                    menorDistancia = distancia;
                    melhorChave = chave;
                }
            }

            if (menorDistancia <= tolerancia) {
                return melhorChave;
            }

            return null;
        }

        function obterItensPorCoordenada(
            latitude,
            longitude
        ) {
            const seriesUsinas = (
                window.USINA_SERIES || {}
            );

            const seriesPontos = (
                window.PONTO_SERIES_BY_LATLON || {}
            );

            const todasAsChaves = Array.from(
                new Set([
                    ...Object.keys(seriesUsinas),
                    ...Object.keys(seriesPontos)
                ])
            );

            const chave = localizarChaveMaisProxima(
                Number(latitude),
                Number(longitude),
                todasAsChaves,
                __TOLERANCIA__
            );

            if (!chave) {
                return {
                    chave: null,
                    usinas: [],
                    pontos: []
                };
            }

            return {
                chave: chave,
                usinas: seriesUsinas[chave] || [],
                pontos: seriesPontos[chave] || []
            };
        }

        function abrirPainelComConteudo(
            titulo,
            conteudo
        ) {
            const painel = document.getElementById(
                "painel-curtailment"
            );

            const tituloElemento = document.getElementById(
                "painel-curtailment-titulo"
            );

            const conteudoElemento = document.getElementById(
                "painel-curtailment-conteudo"
            );

            if (tituloElemento) {
                tituloElemento.textContent = titulo;
            }

            if (conteudoElemento) {
                conteudoElemento.innerHTML = conteudo;
            }

            if (painel) {
                painel.classList.add("aberto");
            }
        }

        function renderizarResumoUsina(indice) {
            const chave = window.CHAVE_SELECIONADA;

            if (!chave) {
                return;
            }

            const itens = (
                window.USINA_SERIES[chave] || []
            );

            const item = itens[indice];

            if (!item) {
                return;
            }

            const html = `
                <button
                    type="button"
                    class="painel-voltar"
                    onclick="renderizarMenuCoordenada(
                        '${escaparHtml(chave)}'
                    )"
                >
                    ← Voltar
                </button>

                <div class="painel-cartao-detalhe">
                    <div class="painel-tipo-item">
                        Usina
                    </div>

                    <h3>
                        ${escaparHtml(
                            item.nome_usina
                        )}
                    </h3>

                    <p>
                        <strong>Ponto de conexão:</strong><br>
                        ${escaparHtml(
                            item.ponto || "Não informado"
                        )}
                    </p>

                    <p>
                        <strong>Horas disponíveis:</strong>
                        ${
                            Array.isArray(item.horas)
                            ? item.horas.length
                            : 0
                        }
                    </p>
                </div>
            `;

            abrirPainelComConteudo(
                "Detalhes da usina",
                html
            );
        }

        function renderizarResumoPonto(indice) {
            const chave = window.CHAVE_SELECIONADA;

            if (!chave) {
                return;
            }

            const itens = (
                window.PONTO_SERIES_BY_LATLON[chave] || []
            );

            const item = itens[indice];

            if (!item) {
                return;
            }

            const html = `
                <button
                    type="button"
                    class="painel-voltar"
                    onclick="renderizarMenuCoordenada(
                        '${escaparHtml(chave)}'
                    )"
                >
                    ← Voltar
                </button>

                <div class="painel-cartao-detalhe">
                    <div class="painel-tipo-item">
                        Ponto de conexão
                    </div>

                    <h3>
                        ${escaparHtml(
                            item.nome_ponto
                            || "Ponto de conexão"
                        )}
                    </h3>

                    <p>
                        <strong>Horas disponíveis:</strong>
                        ${
                            Array.isArray(item.horas)
                            ? item.horas.length
                            : 0
                        }
                    </p>
                </div>
            `;

            abrirPainelComConteudo(
                "Detalhes do ponto",
                html
            );
        }

        function renderizarMenuCoordenada(chave) {
            window.CHAVE_SELECIONADA = chave;

            const usinas = (
                window.USINA_SERIES[chave] || []
            );

            const pontos = (
                window.PONTO_SERIES_BY_LATLON[chave] || []
            );

            const total = usinas.length + pontos.length;

            if (total === 0) {
                return;
            }

            if (
                usinas.length === 1
                && pontos.length === 0
            ) {
                renderizarResumoUsina(0);
                return;
            }

            if (
                pontos.length === 1
                && usinas.length === 0
            ) {
                renderizarResumoPonto(0);
                return;
            }

            let html = `
                <p class="painel-instrucao">
                    Foram encontrados
                    <strong>${total}</strong>
                    itens nesta coordenada.
                    Selecione o item desejado.
                </p>

                <div class="painel-lista-itens">
            `;

            usinas.forEach(
                function(item, indice) {
                    html += `
                        <button
                            type="button"
                            class="painel-item painel-item-usina"
                            onclick="renderizarResumoUsina(
                                ${indice}
                            )"
                        >
                            <span class="painel-item-tipo">
                                Usina
                            </span>

                            <strong>
                                ${escaparHtml(
                                    item.nome_usina
                                )}
                            </strong>

                            <small>
                                ${escaparHtml(
                                    item.ponto || ""
                                )}
                            </small>
                        </button>
                    `;
                }
            );

            pontos.forEach(
                function(item, indice) {
                    html += `
                        <button
                            type="button"
                            class="painel-item painel-item-ponto"
                            onclick="renderizarResumoPonto(
                                ${indice}
                            )"
                        >
                            <span class="painel-item-tipo">
                                Ponto
                            </span>

                            <strong>
                                ${escaparHtml(
                                    item.nome_ponto
                                    || "Ponto de conexão"
                                )}
                            </strong>
                        </button>
                    `;
                }
            );

            html += "</div>";

            abrirPainelComConteudo(
                "Itens encontrados",
                html
            );
        }

        function selecionarPorCoordenada(
            latitude,
            longitude
        ) {
            const resultado = obterItensPorCoordenada(
                latitude,
                longitude
            );

            if (!resultado.chave) {
                console.warn(
                    "Nenhuma série encontrada para:",
                    latitude,
                    longitude
                );

                return false;
            }

            renderizarMenuCoordenada(
                resultado.chave
            );

            return true;
        }

        function extrairLatLngBusca(evento) {
            if (!evento) {
                return null;
            }

            if (
                evento.latlng
                && Number.isFinite(
                    Number(evento.latlng.lat)
                )
                && Number.isFinite(
                    Number(evento.latlng.lng)
                )
            ) {
                return evento.latlng;
            }

            if (
                evento.layer
                && typeof evento.layer.getLatLng
                    === "function"
            ) {
                return evento.layer.getLatLng();
            }

            if (
                evento.layer
                && typeof evento.layer.getBounds
                    === "function"
            ) {
                return evento.layer
                    .getBounds()
                    .getCenter();
            }

            return null;
        }

        function tratarCliqueMapa(evento) {
            if (
                !evento
                || !evento.latlng
            ) {
                return;
            }

            selecionarPorCoordenada(
                evento.latlng.lat,
                evento.latlng.lng
            );
        }

        function tratarResultadoBusca(evento) {
            const coordenada = extrairLatLngBusca(
                evento
            );

            if (!coordenada) {
                console.warn(
                    "Resultado da busca sem coordenada.",
                    evento
                );

                return;
            }

            selecionarPorCoordenada(
                coordenada.lat,
                coordenada.lng
            );
        }

        function inicializarEventosPainel() {
            const mapa = __NOME_MAPA__;
            const controleBusca = __CONTROLE_BUSCA__;

            if (!mapa) {
                console.error(
                    "Mapa Folium não encontrado."
                );

                return;
            }

            mapa.on(
                "click",
                tratarCliqueMapa
            );

            if (
                controleBusca
                && typeof controleBusca.on === "function"
            ) {
                controleBusca.on(
                    "search:locationfound",
                    tratarResultadoBusca
                );
            } else {
                console.error(
                    "Controle de busca não encontrado."
                );
            }

            console.log(
                "Eventos de clique e busca inicializados."
            );
        }

        setTimeout(
            inicializarEventosPainel,
            600
        );
    </script>
    """

    script_eventos = (
        script_eventos
        .replace(
            "__NOME_MAPA__",
            nome_mapa,
        )
        .replace(
            "__CONTROLE_BUSCA__",
            nome_controle_busca,
        )
        .replace(
            "__TOLERANCIA__",
            repr(tolerancia),
        )
    )

    mapa.get_root().html.add_child(
        Element(
            script_eventos
        )
    )

    return mapa


def adicionar_graficos_series_painel(
    mapa,
):
    """
    Adiciona indicadores e gráficos de 24 horas aos detalhes
    das usinas e dos pontos de conexão.
    """

    if mapa is None:
        raise ValueError(
            "O mapa não foi informado."
        )

    script = """
    <script>
        window.GRAFICOS_PAINEL = (
            window.GRAFICOS_PAINEL || {}
        );

        function destruirGraficosPainel() {
            Object.values(
                window.GRAFICOS_PAINEL
            ).forEach(
                function(grafico) {
                    if (
                        grafico
                        && typeof grafico.destroy
                            === "function"
                    ) {
                        grafico.destroy();
                    }
                }
            );

            window.GRAFICOS_PAINEL = {};
        }

        function numeroValido(valor) {
            if (
                valor === null
                || valor === undefined
                || valor === ""
            ) {
                return null;
            }

            const numero = Number(valor);

            return Number.isFinite(numero)
                ? numero
                : null;
        }

        function valoresValidos(serie) {
            if (!Array.isArray(serie)) {
                return [];
            }

            return serie
                .map(numeroValido)
                .filter(
                    function(valor) {
                        return valor !== null;
                    }
                );
        }

        function mediaSerie(serie) {
            const valores = valoresValidos(
                serie
            );

            if (valores.length === 0) {
                return null;
            }

            return valores.reduce(
                function(total, valor) {
                    return total + valor;
                },
                0
            ) / valores.length;
        }

        function maximoSerie(serie) {
            const valores = valoresValidos(
                serie
            );

            if (valores.length === 0) {
                return null;
            }

            return Math.max(...valores);
        }

        function formatarNumero(
            valor,
            casas = 2
        ) {
            const numero = numeroValido(
                valor
            );

            if (numero === null) {
                return "—";
            }

            return numero.toLocaleString(
                "pt-BR",
                {
                    minimumFractionDigits: casas,
                    maximumFractionDigits: casas
                }
            );
        }

        function normalizarSerie(
            serie,
            quantidade = 24
        ) {
            const resultado = new Array(
                quantidade
            ).fill(null);

            if (!Array.isArray(serie)) {
                return resultado;
            }

            for (
                let indice = 0;
                indice < quantidade;
                indice += 1
            ) {
                resultado[indice] = numeroValido(
                    serie[indice]
                );
            }

            return resultado;
        }

        function seriePossuiValor(serie) {
            return valoresValidos(
                serie
            ).some(
                function(valor) {
                    return Math.abs(valor) > 1e-12;
                }
            );
        }

        function criarKpi(
            titulo,
            valor
        ) {
            return `
                <div class="painel-kpi">
                    <span class="painel-kpi-label">
                        ${escaparHtml(titulo)}
                    </span>

                    <span class="painel-kpi-valor">
                        ${escaparHtml(valor)}
                    </span>
                </div>
            `;
        }

        function criarGraficoLinhas(
            identificador,
            horas,
            conjuntos
        ) {
            if (typeof Chart === "undefined") {
                console.error(
                    "Chart.js não foi carregado."
                );

                return;
            }

            const canvas = document.getElementById(
                identificador
            );

            if (!canvas) {
                return;
            }

            window.GRAFICOS_PAINEL[
                identificador
            ] = new Chart(
                canvas,
                {
                    type: "line",
                    data: {
                        labels: horas,
                        datasets: conjuntos
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {
                            mode: "index",
                            intersect: false
                        },
                        plugins: {
                            legend: {
                                display: true,
                                position: "bottom",
                                labels: {
                                    boxWidth: 10,
                                    font: {
                                        size: 10
                                    }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(contexto) {
                                        return (
                                            contexto.dataset.label
                                            + ": "
                                            + formatarNumero(
                                                contexto.parsed.y,
                                                2
                                            )
                                            + " MW"
                                        );
                                    }
                                }
                            }
                        },
                        scales: {
                            x: {
                                title: {
                                    display: true,
                                    text: "Hora"
                                },
                                ticks: {
                                    maxRotation: 0,
                                    autoSkip: true,
                                    maxTicksLimit: 12
                                }
                            },
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: "MW"
                                }
                            }
                        }
                    }
                }
            );
        }

        function criarGraficoCurtailment(
            identificador,
            horas,
            curtByCode
        ) {
            if (typeof Chart === "undefined") {
                console.error(
                    "Chart.js não foi carregado."
                );

                return;
            }

            const canvas = document.getElementById(
                identificador
            );

            if (!canvas) {
                return;
            }

            const cores = {
                CNF: "#9467bd",
                ENE: "#d62728",
                REL: "#ff7f0e",
                SEM_CODIGO: "#7f7f7f"
            };

            const ordemCodigos = [
                "CNF",
                "ENE",
                "REL",
                "SEM_CODIGO"
            ];

            const conjuntos = [];

            ordemCodigos.forEach(
                function(codigo) {
                    const serie = normalizarSerie(
                        curtByCode
                            ? curtByCode[codigo]
                            : null
                    );

                    if (!seriePossuiValor(serie)) {
                        return;
                    }

                    conjuntos.push({
                        label: codigo,
                        data: serie,
                        borderColor: cores[codigo],
                        backgroundColor: cores[codigo],
                        borderWidth: 1.5,
                        pointRadius: 1.5,
                        pointHoverRadius: 4,
                        tension: 0.2,
                        spanGaps: false
                    });
                }
            );

            if (conjuntos.length === 0) {
                return;
            }

            window.GRAFICOS_PAINEL[
                identificador
            ] = new Chart(
                canvas,
                {
                    type: "line",
                    data: {
                        labels: horas,
                        datasets: conjuntos
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {
                            mode: "index",
                            intersect: false
                        },
                        plugins: {
                            legend: {
                                display: true,
                                position: "bottom",
                                labels: {
                                    boxWidth: 10,
                                    font: {
                                        size: 10
                                    }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(contexto) {
                                        return (
                                            contexto.dataset.label
                                            + ": "
                                            + formatarNumero(
                                                contexto.parsed.y,
                                                2
                                            )
                                            + " MW"
                                        );
                                    }
                                }
                            }
                        },
                        scales: {
                            x: {
                                title: {
                                    display: true,
                                    text: "Hora"
                                },
                                ticks: {
                                    maxRotation: 0,
                                    autoSkip: true,
                                    maxTicksLimit: 12
                                }
                            },
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: "MW"
                                }
                            }
                        }
                    }
                }
            );
        }

        function calcularIndicadoresItem(item) {
            const mediaGeracao = mediaSerie(
                item.avg_geracao
            );

            const mediaCurtailment = mediaSerie(
                item.avg_curtailment
            );

            const mediaEsperada = mediaSerie(
                item.avg_geracao_esperada
            );

            const picoCurtailment = maximoSerie(
                item.avg_curtailment
            );

            let percentualCurtailment = null;

            if (
                mediaEsperada !== null
                && mediaEsperada !== 0
                && mediaCurtailment !== null
            ) {
                percentualCurtailment = (
                    mediaCurtailment
                    / mediaEsperada
                    * 100
                );
            }

            return {
                mediaGeracao: mediaGeracao,
                mediaCurtailment: mediaCurtailment,
                mediaEsperada: mediaEsperada,
                picoCurtailment: picoCurtailment,
                percentualCurtailment: percentualCurtailment
            };
        }

        function montarConteudoDetalhes(
            tipo,
            nome,
            ponto,
            item
        ) {
            const indicadores = calcularIndicadoresItem(
                item
            );

            let identificacaoPonto = "";

            if (ponto) {
                identificacaoPonto = `
                    <p>
                        <strong>Ponto de conexão:</strong><br>
                        ${escaparHtml(ponto)}
                    </p>
                `;
            }

            const possuiDecomposicao = (
                item.curt_by_code
                && Object.keys(
                    item.curt_by_code
                ).some(
                    function(codigo) {
                        return seriePossuiValor(
                            normalizarSerie(
                                item.curt_by_code[codigo]
                            )
                        );
                    }
                )
            );

            return `
                <button
                    type="button"
                    class="painel-voltar"
                    onclick="renderizarMenuCoordenada(
                        '${escaparHtml(
                            window.CHAVE_SELECIONADA
                        )}'
                    )"
                >
                    ← Voltar
                </button>

                <div class="painel-identificacao">
                    <div class="painel-tipo-item">
                        ${escaparHtml(tipo)}
                    </div>

                    <h3>
                        ${escaparHtml(nome)}
                    </h3>

                    ${identificacaoPonto}
                </div>

                <div class="painel-kpis">
                    ${criarKpi(
                        "Geração média",
                        formatarNumero(
                            indicadores.mediaGeracao,
                            2
                        ) + " MW"
                    )}

                    ${criarKpi(
                        "Curtailment médio",
                        formatarNumero(
                            indicadores.mediaCurtailment,
                            2
                        ) + " MW"
                    )}

                    ${criarKpi(
                        "Geração esperada",
                        formatarNumero(
                            indicadores.mediaEsperada,
                            2
                        ) + " MW"
                    )}

                    ${criarKpi(
                        "Pico de curtailment",
                        formatarNumero(
                            indicadores.picoCurtailment,
                            2
                        ) + " MW"
                    )}

                    ${criarKpi(
                        "Curtailment / esperada",
                        indicadores.percentualCurtailment
                            === null
                            ? "—"
                            : (
                                formatarNumero(
                                    indicadores
                                        .percentualCurtailment,
                                    2
                                )
                                + "%"
                            )
                    )}

                    ${criarKpi(
                        "Horas disponíveis",
                        Array.isArray(item.horas)
                            ? String(item.horas.length)
                            : "0"
                    )}
                </div>

                <div class="painel-grafico">
                    <h4>
                        Geração, curtailment e geração esperada
                    </h4>

                    <div class="painel-grafico-canvas">
                        <canvas
                            id="grafico-perfil-principal"
                        ></canvas>
                    </div>
                </div>

                ${
                    possuiDecomposicao
                    ? `
                        <div class="painel-grafico">
                            <h4>
                                Curtailment por código
                            </h4>

                            <div class="painel-grafico-canvas">
                                <canvas
                                    id="grafico-curtailment-codigo"
                                ></canvas>
                            </div>
                        </div>
                    `
                    : `
                        <div class="painel-sem-grafico">
                            Não há decomposição por código
                            disponível para este item.
                        </div>
                    `
                }
            `;
        }

        function renderizarGraficosItem(item) {
            destruirGraficosPainel();

            const horas = (
                Array.isArray(item.horas)
                && item.horas.length > 0
            )
                ? item.horas
                : Array.from(
                    {length: 24},
                    function(_, indice) {
                        return indice;
                    }
                );

            criarGraficoLinhas(
                "grafico-perfil-principal",
                horas,
                [
                    {
                        label: "Geração",
                        data: normalizarSerie(
                            item.avg_geracao
                        ),
                        borderColor: "#1f77b4",
                        backgroundColor: "#1f77b4",
                        borderWidth: 2,
                        pointRadius: 1.5,
                        pointHoverRadius: 4,
                        tension: 0.2,
                        spanGaps: false
                    },
                    {
                        label: "Curtailment",
                        data: normalizarSerie(
                            item.avg_curtailment
                        ),
                        borderColor: "#d62728",
                        backgroundColor: "#d62728",
                        borderWidth: 2,
                        pointRadius: 1.5,
                        pointHoverRadius: 4,
                        tension: 0.2,
                        spanGaps: false
                    },
                    {
                        label: "Geração esperada",
                        data: normalizarSerie(
                            item.avg_geracao_esperada
                        ),
                        borderColor: "#2ca02c",
                        backgroundColor: "#2ca02c",
                        borderWidth: 2,
                        pointRadius: 1.5,
                        pointHoverRadius: 4,
                        tension: 0.2,
                        spanGaps: false
                    }
                ]
            );

            if (
                document.getElementById(
                    "grafico-curtailment-codigo"
                )
            ) {
                criarGraficoCurtailment(
                    "grafico-curtailment-codigo",
                    horas,
                    item.curt_by_code || {}
                );
            }
        }

        function renderizarResumoUsina(indice) {
            const chave = window.CHAVE_SELECIONADA;

            if (!chave) {
                return;
            }

            const itens = (
                window.USINA_SERIES[chave] || []
            );

            const item = itens[indice];

            if (!item) {
                return;
            }

            const html = montarConteudoDetalhes(
                "Usina",
                item.nome_usina || "Usina",
                item.ponto || "",
                item
            );

            abrirPainelComConteudo(
                "Detalhes da usina",
                html
            );

            setTimeout(
                function() {
                    renderizarGraficosItem(
                        item
                    );
                },
                50
            );
        }

        function renderizarResumoPonto(indice) {
            const chave = window.CHAVE_SELECIONADA;

            if (!chave) {
                return;
            }

            const itens = (
                window.PONTO_SERIES_BY_LATLON[chave] || []
            );

            const item = itens[indice];

            if (!item) {
                return;
            }

            const html = montarConteudoDetalhes(
                "Ponto de conexão",
                (
                    item.nome_ponto
                    || "Ponto de conexão"
                ),
                "",
                item
            );

            abrirPainelComConteudo(
                "Detalhes do ponto",
                html
            );

            setTimeout(
                function() {
                    renderizarGraficosItem(
                        item
                    );
                },
                50
            );
        }
    </script>
    """

    mapa.get_root().html.add_child(
        Element(
            script
        )
    )

    return mapa


def criar_mapa_interativo(
    gdf_ufs,
    gdf_usinas,
    gdf_pontos,
    gdf_linhas_desenhaveis,
    gdf_busca,
    usina_series_map,
    ponto_series_by_latlon,
    tolerancia_selecao=0.0005,
):
    """
    Cria o mapa completo com painel, busca, indicadores
    e gráficos de séries horárias.

    Parâmetros
    ----------
    gdf_ufs : geopandas.GeoDataFrame
        Malha simplificada das UFs.
    gdf_usinas : geopandas.GeoDataFrame
        Usinas georreferenciadas.
    gdf_pontos : geopandas.GeoDataFrame
        Pontos de conexão georreferenciados.
    gdf_linhas_desenhaveis : geopandas.GeoDataFrame
        Linhas de transmissão desenháveis.
    gdf_busca : geopandas.GeoDataFrame
        Índice geográfico de busca.
    usina_series_map : dict
        Séries das usinas agrupadas por coordenada.
    ponto_series_by_latlon : dict
        Séries dos pontos agrupadas por coordenada.
    tolerancia_selecao : float, opcional
        Tolerância geográfica utilizada na seleção.

    Retorno
    -------
    tuple
        Mapa interativo e relatório da construção.
    """

    (
        json_usinas,
        json_pontos,
        relatorio_serializacao,
    ) = serializar_series_mapa(
        usina_series_map=(
            usina_series_map
        ),
        ponto_series_by_latlon=(
            ponto_series_by_latlon
        ),
    )

    mapa, relatorio_mapa = criar_mapa_basico(
        gdf_ufs=gdf_ufs,
        gdf_usinas=gdf_usinas,
        gdf_pontos=gdf_pontos,
        gdf_linhas_desenhaveis=(
            gdf_linhas_desenhaveis
        ),
        gdf_busca=gdf_busca,
    )

    adicionar_estrutura_painel(
        mapa
    )

    adicionar_estilos_selecao_painel(
        mapa
    )

    adicionar_estilos_graficos_painel(
        mapa
    )

    adicionar_chartjs(
        mapa
    )

    adicionar_series_ao_mapa(
        mapa=mapa,
        json_usinas=json_usinas,
        json_pontos=json_pontos,
    )

    camada_busca = localizar_camada_busca(
        mapa
    )

    adicionar_eventos_selecao_painel(
        mapa=mapa,
        camada_busca=camada_busca,
        tolerancia=tolerancia_selecao,
    )

    adicionar_graficos_series_painel(
        mapa
    )

    relatorio = {
        **relatorio_mapa,
        **relatorio_serializacao,
        "painel_lateral": True,
        "painel_lado": "esquerdo",
        "chartjs": True,
        "graficos_series": True,
        "selecao_por_busca": True,
        "selecao_por_coordenada": True,
        "tolerancia_selecao": float(
            tolerancia_selecao
        ),
    }

    return mapa, relatorio


def salvar_mapa_html(
    mapa,
    caminho_saida,
):
    """
    Salva o mapa como um arquivo HTML.

    Parâmetros
    ----------
    mapa : folium.Map
        Mapa que será salvo.
    caminho_saida : str ou pathlib.Path
        Caminho do arquivo HTML.

    Retorno
    -------
    pathlib.Path
        Caminho absoluto do arquivo criado.
    """

    if mapa is None:
        raise ValueError(
            "O mapa não foi informado."
        )

    caminho = Path(
        caminho_saida
    )

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    mapa.save(
        str(caminho)
    )

    if not caminho.exists():
        raise RuntimeError(
            "O arquivo HTML do mapa não foi criado."
        )

    return caminho.resolve()
