"""
Construção do mapa interativo de curtailment.

O módulo cria o mapa-base, adiciona os limites das UFs,
as usinas, os pontos de conexão, as linhas de transmissão,
o índice de busca e o controle de camadas.

O painel lateral, as séries horárias e os gráficos serão
adicionados em etapas posteriores.
"""

from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
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
