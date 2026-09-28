"""
Aplicação Streamlit para visualização de curtailment.

Regras das bases:
- dados EOL e UFV: período escolhido pelo usuário;
- fator de capacidade: última competência mensal completa;
- subestações: cadastro mais atual disponível;
- linhas de transmissão: cadastro mais atual disponível.
"""

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.mapa import (
    carregar_malha_ufs,
    criar_mapa_inicial,
    criar_mapa_interativo,
)
from src.pipeline import preparar_dados_aplicacao
from src.analise_subsistemas import (
    calcular_kpis_curtailment,
    preparar_curtailment_mensal_subsistemas,
)
# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="SINmulator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        header[data-testid="stHeader"] {
            display: none;
        }

        .block-container {
            max-width: 100%;
            padding-top: 0 !important;
            padding-right: 0 !important;
            padding-bottom: 0 !important;
            padding-left: 0 !important;
        }

        /* Barra superior */

        .sin-navbar {
            display: flex;
            align-items: center;
            justify-content: space-between;

            width: 100vw;
            min-height: 64px;

            margin: 0;
            padding: 0.65rem 2rem;

            background-color: #071f3d;
            box-sizing: border-box;
            box-shadow: 0 2px 8px rgba(7, 31, 61, 0.2);
        }

        .sin-navbar-marca {
            display: flex;
            align-items: center;
            gap: 0.65rem;
        }

        .sin-navbar-icone {
            display: inline-flex;
            align-items: center;
            justify-content: center;

            width: 30px;
            height: 30px;

            color: #ffffff;
            font-family: Arial, sans-serif;
            font-size: 1.65rem;
            font-weight: 700;
            line-height: 1;
        }

        .sin-navbar-nome {
            color: #ffffff;
            font-family:
                "Trebuchet MS",
                "Segoe UI",
                sans-serif;
            font-size: 1.55rem;
            font-weight: 800;
            letter-spacing: -0.025rem;
            line-height: 1;
        }

        .sin-navbar-menu {
            display: flex;
            align-items: center;
            gap: 0.9rem;
        }
        
        .sin-navbar-item {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.55rem;
        
            min-width: 112px;
            padding: 0.65rem 1rem;
        
            color: rgba(255, 255, 255, 0.78) !important;
            background-color: transparent;
        
            border: 1px solid transparent;
            border-radius: 8px;
        
            font-family:
                "Segoe UI",
                sans-serif;
            font-size: 0.9rem;
            font-weight: 600;
            line-height: 1;
        
            text-decoration: none !important;
        
            cursor: pointer;
        
            transition:
                color 0.15s ease,
                background-color 0.15s ease,
                border-color 0.15s ease;
        }
        
        .sin-navbar-item:hover {
            color: #ffffff !important;
            background-color: rgba(255, 255, 255, 0.08);
        
            text-decoration: none !important;
        }
        
        .sin-navbar-item:focus,
        .sin-navbar-item:active,
        .sin-navbar-item:visited {
            text-decoration: none !important;
        }
        
        .sin-navbar-item-ativo {
            color: #ffffff !important;
            background-color: #204777;
        
            border-color: rgba(255, 255, 255, 0.08);
        
            text-decoration: none !important;
        
            box-shadow:
                inset 0 0 0 1px
                rgba(255, 255, 255, 0.04);
        }
        
        .sin-navbar-item-icone {
            display: inline-flex;
            align-items: center;
            justify-content: center;
        
            color: inherit;
            font-size: 1rem;
            line-height: 1;
        }

        /* Barra suspensa de filtros */

        .st-key-filtros_mapa {
            position: relative;
            z-index: 50;

            width: min(1120px, calc(100vw - 3rem));

            margin-top: 14px;
            margin-right: auto;
            margin-bottom: -72px;
            margin-left: auto;

            padding: 0.55rem 0.75rem 0.7rem;

            background-color: rgba(255, 255, 255, 0.97);
            backdrop-filter: blur(12px);

            border: 1px solid rgba(203, 213, 225, 0.95);
            border-radius: 13px;

            box-shadow:
                0 10px 28px rgba(15, 23, 42, 0.2);

            box-sizing: border-box;
        }

        .st-key-filtros_mapa
        div[data-testid="stVerticalBlockBorderWrapper"] {
            padding: 0;
            background: transparent;
            border: 0;
            box-shadow: none;
        }

        .st-key-filtros_mapa
        div[data-testid="stSelectbox"] {
            min-width: 0;
        }

        .st-key-filtros_mapa
        div[data-testid="stSelectbox"] label {
            color: #334155;
            font-size: 0.78rem;
            font-weight: 600;
        }

        .st-key-filtros_mapa
        div[data-testid="stButton"] button {
            min-height: 40px;
            border-radius: 9px;
            font-weight: 600;
        }

        .st-key-filtros_mapa
        div[data-testid="stStatusWidget"],
        .st-key-filtros_mapa
        div[data-testid="stSpinner"] {
            margin-top: 0.45rem;
            margin-bottom: 0;
        }
        
        .st-key-filtros_mapa
        div[data-testid="stSpinner"] p {
            color: #475569;
            font-size: 0.82rem;
        }

        .resumo-filtros {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        
            margin-top: 0.45rem;
            padding-top: 0.55rem;
        
            color: #64748b;
            border-top: 1px solid #e2e8f0;
        
            font-size: 0.79rem;
            line-height: 1.4;
            text-align: left;
        }
        
        .resumo-filtros strong {
            color: #334155;
            font-weight: 600;
        }
        
        .resumo-filtros-icone {
            flex: 0 0 auto;
            color: #22a06b;
            font-size: 0.55rem;
        }

        /* Área do mapa */

        .st-key-area_mapa {
            position: relative;
            z-index: 1;

            width: 100vw;
            left: 50%;
            margin-left: -50vw;

            padding: 0;
            overflow: hidden;
        }

        .st-key-area_mapa
        div[data-testid="stVerticalBlock"] {
            gap: 0;
        }

        .st-key-area_mapa iframe {
            display: block;
            width: 100% !important;
            margin: 0;
            padding: 0;
            border: 0;
        }

        /* Regras das bases */

        .st-key-informacoes_bases {
            width: min(460px, calc(100vw - 2rem));
        
            margin-top: 0.75rem;
            margin-right: auto;
            margin-bottom: 1.25rem;
            margin-left: 1rem;
        }
        
        .st-key-informacoes_bases
        details {
            background-color: transparent;
        
            border: 1px solid #e2e8f0 !important;
            border-radius: 8px;
        
            box-shadow: none !important;
        }
        
        .st-key-informacoes_bases
        details[open] {
            background-color: #f8fafc;
        }
        
        .st-key-informacoes_bases
        summary {
            min-height: 38px;
            padding: 0.35rem 0.65rem;
        
            color: #64748b;
            font-size: 0.8rem;
            font-weight: 500;
        }
        
        .st-key-informacoes_bases
        summary:hover {
            color: #334155;
            background-color: #f8fafc;
        }
        
        .st-key-informacoes_bases
        div[data-testid="stExpanderDetails"] {
            padding: 0.25rem 0.75rem 0.65rem;
        }
        
        .st-key-informacoes_bases
        div[data-testid="stMarkdownContainer"] {
            color: #64748b;
            font-size: 0.78rem;
            line-height: 1.45;
        }
        
        .st-key-informacoes_bases
        div[data-testid="stMarkdownContainer"] ul {
            margin-top: 0.25rem;
            margin-bottom: 0;
            padding-left: 1.15rem;
        }
        
        .st-key-informacoes_bases
        div[data-testid="stMarkdownContainer"] li {
            margin-bottom: 0.28rem;
        }

        /* aba subsistemas*/

        /* Filtros da página Subsistemas */

        .st-key-filtros_subsistemas {
            position: relative;
            z-index: 10;
        
            width: min(1120px, calc(100vw - 3rem));
        
            margin-top: 14px;
            margin-right: auto;
            margin-bottom: 1.25rem;
            margin-left: auto;
        
            padding: 0.55rem 0.75rem 0.7rem;
        
            background-color: rgba(255, 255, 255, 0.97);
            backdrop-filter: blur(12px);
        
            border: 1px solid rgba(203, 213, 225, 0.95);
            border-radius: 13px;
        
            box-shadow:
                0 10px 28px rgba(15, 23, 42, 0.14);
        
            box-sizing: border-box;
        }
        
        .st-key-filtros_subsistemas
        div[data-testid="stVerticalBlockBorderWrapper"] {
            padding: 0;
            background: transparent;
            border: 0;
            box-shadow: none;
        }
        
        .st-key-filtros_subsistemas
        div[data-testid="stSelectbox"] {
            min-width: 0;
        }
        
        .st-key-filtros_subsistemas
        div[data-testid="stSelectbox"] label {
            color: #334155;
            font-size: 0.78rem;
            font-weight: 600;
        }
        
        .st-key-filtros_subsistemas
        div[data-testid="stButton"] button {
            min-height: 40px;
            border-radius: 9px;
            font-weight: 600;
        }

        .resumo-subsistemas-filtros {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        
            margin-top: 0.45rem;
            padding-top: 0.5rem;
        
            color: #64748b;
            border-top: 1px solid #e2e8f0;
        
            font-size: 0.79rem;
            line-height: 1.4;
            text-align: center;
        }
        
        .resumo-subsistemas-filtros strong {
            color: #334155;
            font-weight: 600;
        }
        
        .resumo-subsistemas-indicador {
            flex: 0 0 auto;
        
            color: #22a06b;
            font-size: 0.55rem;
        }
        
        .cabecalho-subsistemas {
            width: min(1180px, calc(100vw - 3rem));
        
            margin-top: 0.35rem;
            margin-right: auto;
            margin-bottom: 1rem;
            margin-left: auto;
        }
        
        .cabecalho-subsistemas h1 {
            margin: 0 0 0.35rem;
        
            color: #0f2948;
            font-size: 1.65rem;
            font-weight: 700;
        }
        
        .cabecalho-subsistemas p {
            margin: 0;
        
            color: #64748b;
            font-size: 0.9rem;
        }
        
        .kpis-subsistemas {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.9rem;
        
            width: min(1180px, calc(100vw - 3rem));
        
            margin-top: 1rem;
            margin-right: auto;
            margin-bottom: 1.5rem;
            margin-left: auto;
        }
        
        .kpi-subsistema-card {
            display: flex;
            align-items: center;
            gap: 0.85rem;
        
            min-width: 0;
            min-height: 86px;
        
            padding: 0.85rem 1rem;
        
            background:
                linear-gradient(
                    135deg,
                    #ffffff 0%,
                    #fbfdff 100%
                );
        
            border: 1px solid #e5edf5;
            border-radius: 13px;
        
            box-shadow:
                0 6px 18px rgba(15, 42, 70, 0.08);
        
            box-sizing: border-box;
        }
        
        .kpi-subsistema-icone {
            display: inline-flex;
            align-items: center;
            justify-content: center;
        
            flex: 0 0 auto;
        
            width: 48px;
            height: 48px;
        
            border-radius: 50%;
        }
        
        .kpi-subsistema-simbolo {
            display: inline-flex;
            align-items: center;
            justify-content: center;
        
            width: 100%;
            height: 100%;
        
            color: currentColor;
            font-family:
                "Segoe UI Symbol",
                Arial,
                sans-serif;
            font-size: 1.55rem;
            font-weight: 700;
            line-height: 1;
        
            user-select: none;
        }
        
        .kpi-icone-corte {
            color: #05aaa4;
            background-color: #ddf8f6;
        }
        
        .kpi-icone-subsistema {
            color: #ef476f;
            background-color: #ffe8ed;
        }
        
        .kpi-icone-tipo {
            color: #7959da;
            background-color: #eee9ff;
        }
        
        .kpi-icone-mes {
            color: #2979e8;
            background-color: #e4f0ff;
        }
        
        .kpi-subsistema-conteudo {
            min-width: 0;
        }
        
        .kpi-subsistema-titulo {
            margin-bottom: 0.2rem;
        
            color: #53667c;
            font-size: 0.72rem;
            font-weight: 600;
            line-height: 1.2;
        }
        
        .kpi-subsistema-valor {
            overflow: hidden;
        
            color: #102d57;
            font-size: 1.05rem;
            font-weight: 750;
            line-height: 1.2;
        
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .kpi-subsistema-detalhe {
            margin-top: 0.18rem;
        
            color: #7c8ca0;
            font-size: 0.67rem;
            line-height: 1.25;
        }
        
        @media (max-width: 1000px) {
            .kpis-subsistemas {
                grid-template-columns:
                    repeat(2, minmax(0, 1fr));
            }
        }
        
        @media (max-width: 600px) {
            .kpis-subsistemas {
                grid-template-columns: 1fr;
                width: calc(100vw - 1rem);
            }
        }

        @media (max-width: 900px) {
            .sin-navbar {
                min-height: 56px;
                padding: 0.55rem 1rem;
            }

            .sin-navbar-nome {
                font-size: 1.3rem;
            }

            .sin-navbar-item {
                min-width: auto;
                padding: 0.55rem 0.75rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


ANO_MINIMO = 2024

TIMEOUT_PIPELINE = 180

RAIZ_PROJETO = (
    Path(__file__)
    .resolve()
    .parent
)

CAMINHO_UFS = (
    RAIZ_PROJETO
    / "assets"
    / "geo"
    / "estados_brasil.geojson"
)

ALTURA_MAPA = 860
LARGURA_MAPA = 1400

NOMES_MESES = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}

OPCOES_FONTES = {
    "Eólica e solar fotovoltaica": (
        "EOL",
        "UFV",
    ),
    "Eólica": (
        "EOL",
    ),
    "Solar fotovoltaica": (
        "UFV",
    ),
}

ROTULOS_FONTES_RESUMIDOS = {
    "Eólica e solar fotovoltaica": "Eólica e solar",
    "Eólica": "Eólica",
    "Solar fotovoltaica": "Solar fotovoltaica",
}

TIPOS_CURTAILMENT = {
    "Todos": "TODOS",
    "Energético": "ENE",
    "Elétrico": "REL",
    "Confiabilidade": "CNF",
}

# ============================================================
# FUNÇÕES
# ============================================================

def obter_ultima_competencia_completa(
    data_referencia=None,
):
    """
    Retorna o ano e o mês da última competência mensal
    completa.

    Parâmetros
    ----------
    data_referencia : datetime.date, opcional
        Data usada no cálculo. Quando não informada,
        utiliza a data atual.

    Retorno
    -------
    tuple
        Ano e mês da última competência completa.
    """

    if data_referencia is None:
        data_referencia = date.today()

    if data_referencia.month == 1:
        return (
            data_referencia.year - 1,
            12,
        )

    return (
        data_referencia.year,
        data_referencia.month - 1,
    )


def obter_meses_disponiveis(
    ano,
    ultimo_ano_completo,
    ultimo_mes_completo,
):
    """
    Retorna os meses permitidos para o ano selecionado.
    """

    if ano < ultimo_ano_completo:
        return list(
            range(1, 13)
        )

    if ano == ultimo_ano_completo:
        return list(
            range(
                1,
                ultimo_mes_completo + 1,
            )
        )

    return []


def formatar_mes(
    mes,
):
    """
    Formata o mês para exibição na interface.
    """

    return (
        f"{mes:02d} - "
        f"{NOMES_MESES[mes]}"
    )


def formatar_competencia(
    ano,
    mes,
):
    """
    Formata uma competência no padrão MM/AAAA.
    """

    return f"{mes:02d}/{ano}"


def validar_periodo_interface(
    ano_inicial,
    mes_inicial,
    ano_final,
    mes_final,
    ultimo_ano_completo,
    ultimo_mes_completo,
):
    """
    Valida um período que pode abranger mais de um ano.
    """

    competencia_inicial = (
        ano_inicial,
        mes_inicial,
    )

    competencia_final = (
        ano_final,
        mes_final,
    )

    ultima_competencia_completa = (
        ultimo_ano_completo,
        ultimo_mes_completo,
    )

    if competencia_inicial > competencia_final:
        raise ValueError(
            "A competência inicial não pode ser posterior "
            "à competência final."
        )

    if competencia_final > ultima_competencia_completa:
        raise ValueError(
            "A competência final selecionada ainda não "
            "está completamente disponível."
        )

@st.cache_resource(
    show_spinner=False,
)
def executar_pipeline_aplicacao(
    ano_inicial,
    mes_inicial,
    ano_final,
    mes_final,
    fontes,
    data_referencia,
    timeout,
):
    """
    Executa o pipeline e mantém os resultados em cache.
    """

    return preparar_dados_aplicacao(
        ano_inicial=ano_inicial,
        mes_inicial=mes_inicial,
        ano_final=ano_final,
        mes_final=mes_final,
        fontes=fontes,
        data_referencia=data_referencia,
        timeout=timeout,
    )

@st.cache_data(
    show_spinner=False,
)

def carregar_ufs_aplicacao(
    caminho_geojson,
):
    """
    Carrega e valida a malha das UFs utilizada pelo mapa.
    """

    return carregar_malha_ufs(caminho_geojson)

def construir_mapa_aplicacao(
    dados_pipeline,
    gdf_ufs,
):
    """
    Constrói o mapa interativo com os resultados do pipeline.

    Retorno
    -------
    tuple
        Mapa interativo e relatório da construção.
    """

    (
        mapa_interativo,
        relatorio_mapa,
    ) = criar_mapa_interativo(
        gdf_ufs=gdf_ufs,
        gdf_usinas=dados_pipeline[
            "gdf_usinas"
        ],
        gdf_pontos=dados_pipeline[
            "gdf_pontos"
        ],
        gdf_linhas_desenhaveis=dados_pipeline[
            "gdf_linhas_desenhaveis"
        ],
        gdf_busca=dados_pipeline[
            "gdf_busca"
        ],
        usina_series_map=dados_pipeline[
            "usina_series_map"
        ],
        ponto_series_by_latlon=dados_pipeline[
            "ponto_series_by_latlon"
        ],
    )

    return (
        mapa_interativo,
        relatorio_mapa,
    )

def renderizar_filtros_subsistemas(
    ultimo_ano_completo,
    ultimo_mes_completo,
):
    """
    Renderiza os filtros independentes da página Subsistemas.

    Retorno
    -------
    dict ou None
        Configuração selecionada quando o botão Aplicar
        for acionado. Caso contrário, retorna None.
    """

    anos_disponiveis = list(
        range(
            ANO_MINIMO,
            ultimo_ano_completo + 1,
        )
    )

    with st.container(
        border=True,
        key="filtros_subsistemas",
    ):
        (
            coluna_ano_inicial,
            coluna_mes_inicial,
            coluna_ano_final,
            coluna_mes_final,
            coluna_fonte,
            coluna_botao,
        ) = st.columns(
            [
                0.8,
                1.3,
                0.8,
                1.3,
                1.9,
                1,
            ],
            vertical_alignment="bottom",
        )

        with coluna_ano_inicial:
            ano_inicial = st.selectbox(
                "Ano inicial",
                options=anos_disponiveis,
                index=len(
                    anos_disponiveis
                ) - 1,
                key="subsistemas_ano_inicial",
            )

        meses_iniciais = obter_meses_disponiveis(
            ano=ano_inicial,
            ultimo_ano_completo=(
                ultimo_ano_completo
            ),
            ultimo_mes_completo=(
                ultimo_mes_completo
            ),
        )

        with coluna_mes_inicial:
            mes_inicial = st.selectbox(
                "Mês inicial",
                options=meses_iniciais,
                index=0,
                format_func=formatar_mes,
                key="subsistemas_mes_inicial",
            )

        with coluna_ano_final:
            ano_final = st.selectbox(
                "Ano final",
                options=anos_disponiveis,
                index=len(
                    anos_disponiveis
                ) - 1,
                key="subsistemas_ano_final",
            )

        meses_finais = obter_meses_disponiveis(
            ano=ano_final,
            ultimo_ano_completo=(
                ultimo_ano_completo
            ),
            ultimo_mes_completo=(
                ultimo_mes_completo
            ),
        )

        with coluna_mes_final:
            mes_final = st.selectbox(
                "Mês final",
                options=meses_finais,
                index=len(
                    meses_finais
                ) - 1,
                format_func=formatar_mes,
                key="subsistemas_mes_final",
            )

        with coluna_fonte:
            opcao_fonte = st.selectbox(
                "Tipo de fonte",
                options=list(
                    OPCOES_FONTES
                ),
                index=0,
                key="subsistemas_opcao_fonte",
            )

        fontes_selecionadas = (
            OPCOES_FONTES[
                opcao_fonte
            ]
        )

        with coluna_botao:
            aplicar_filtros = st.button(
                "Aplicar",
                use_container_width=True,
                type="primary",
                key="subsistemas_aplicar",
            )
            
        status_subsistemas = st.empty()
        resumo_subsistemas = st.empty()

    if not aplicar_filtros:
        return (
            None,
            status_subsistemas,
            resumo_subsistemas,
        )

    validar_periodo_interface(
        ano_inicial=ano_inicial,
        mes_inicial=mes_inicial,
        ano_final=ano_final,
        mes_final=mes_final,
        ultimo_ano_completo=(
            ultimo_ano_completo
        ),
        ultimo_mes_completo=(
            ultimo_mes_completo
        ),
    )

    return (
        {
            "ano_inicial": ano_inicial,
            "mes_inicial": mes_inicial,
            "ano_final": ano_final,
            "mes_final": mes_final,
            "fontes": tuple(
                fontes_selecionadas
            ),
            "rotulo_fonte": opcao_fonte,
        },
        status_subsistemas,
        resumo_subsistemas,
    )

def renderizar_pagina_subsistemas(
    hoje,
    ultimo_ano_completo,
    ultimo_mes_completo,
):
    """
    Renderiza a página de análise dos subsistemas.
    """

    try:
        (
            filtros_aplicados,
            status_subsistemas,
            resumo_subsistemas,
        ) = renderizar_filtros_subsistemas(
            ultimo_ano_completo=(
                ultimo_ano_completo
            ),
            ultimo_mes_completo=(
                ultimo_mes_completo
            ),
        )
    except ValueError as erro:
        st.error(
            str(erro)
        )

        return

    st.html(
        """
        <div class="cabecalho-subsistemas">
            <h1>Subsistemas</h1>
        </div>
        """
    )

    if filtros_aplicados is not None:
        st.session_state[
            "filtros_subsistemas"
        ] = filtros_aplicados

        st.session_state[
            "processar_subsistemas"
        ] = True

    filtros_subsistemas = st.session_state.get(
        "filtros_subsistemas"
    )

    if filtros_subsistemas is None:
        return
    
    if st.session_state.get(
        "processar_subsistemas",
        False,
    ):
        competencia_inicial = (
            formatar_competencia(
                ano=filtros_subsistemas[
                    "ano_inicial"
                ],
                mes=filtros_subsistemas[
                    "mes_inicial"
                ],
            )
        )

        competencia_final = (
            formatar_competencia(
                ano=filtros_subsistemas[
                    "ano_final"
                ],
                mes=filtros_subsistemas[
                    "mes_final"
                ],
            )
        )

        mensagem_processamento = (
            "Coletando e processando os dados de "
            f"{competencia_inicial} a "
            f"{competencia_final}. "
            "A primeira execução pode levar alguns minutos."
        )

        try:
            with status_subsistemas.container():
                with st.spinner(
                    mensagem_processamento
                ):
                    dados_subsistemas = (
                        executar_pipeline_aplicacao(
                            ano_inicial=(
                                filtros_subsistemas[
                                    "ano_inicial"
                                ]
                            ),
                            mes_inicial=(
                                filtros_subsistemas[
                                    "mes_inicial"
                                ]
                            ),
                            ano_final=(
                                filtros_subsistemas[
                                    "ano_final"
                                ]
                            ),
                            mes_final=(
                                filtros_subsistemas[
                                    "mes_final"
                                ]
                            ),
                            fontes=tuple(
                                filtros_subsistemas[
                                    "fontes"
                                ]
                            ),
                            data_referencia=hoje,
                            timeout=TIMEOUT_PIPELINE,
                        )
                    )
        
            st.session_state[
                "dados_subsistemas"
            ] = dados_subsistemas
        
            st.session_state[
                "periodo_processado_subsistemas"
            ] = filtros_subsistemas.copy()
        
            st.session_state[
                "processar_subsistemas"
            ] = False
        
            status_subsistemas.empty()
        
            st.toast(
                "Dados dos subsistemas processados "
                "com sucesso.",
                icon="✅",
            )
        
        except Exception as erro:
            st.session_state[
                "processar_subsistemas"
            ] = False
        
            status_subsistemas.error(
                "Não foi possível processar os dados "
                "da análise por subsistemas."
            )
        
            st.exception(
                erro
            )
        
            return
        
        
        dados_subsistemas = st.session_state.get(
            "dados_subsistemas"
        )
        
        periodo_processado = st.session_state.get(
            "periodo_processado_subsistemas"
        )
        
        if (
            dados_subsistemas is None
            or periodo_processado is None
        ):
            return
    
    # ============================================================
    # RESUMO DA BASE PROCESSADA
    # ============================================================
    
    resumo_pipeline = dados_subsistemas[
        "relatorios"
    ][
        "resumo_pipeline"
    ]
    
    rotulo_fonte = periodo_processado[
        "rotulo_fonte"
    ]
    
    rotulo_fonte_resumido = (
        ROTULOS_FONTES_RESUMIDOS.get(
            rotulo_fonte,
            rotulo_fonte,
        )
    )
    
    quantidade_registros = (
        f"{resumo_pipeline['registros_curtailment']:,}"
        .replace(
            ",",
            ".",
        )
    )

    resumo_subsistemas_html = (
        '<div class="resumo-subsistemas-filtros">'
        '<span class="resumo-subsistemas-indicador">●</span>'
        '<span>'
        f'Foram processados <strong>{quantidade_registros} '
        f'registros</strong> no período de '
        f'<strong>{resumo_pipeline["periodo_inicial"]}</strong> a '
        f'<strong>{resumo_pipeline["periodo_final"]}</strong>, '
        f'para a fonte '
        f'<strong>{rotulo_fonte_resumido}</strong>.'
        '</span>'
        '</div>'
    )
    
    resumo_subsistemas.html(
        resumo_subsistemas_html
    )
    
    # ============================================================
    # CÁLCULO DOS KPIS
    # ============================================================
    
    df_curtailment_subsistemas = dados_subsistemas[
        "df_curtailment"
    ]
    
    try:
        kpis_subsistemas = (
            calcular_kpis_subsistemas_aplicacao(
                df_curtailment_subsistemas
            )
        )
    
    except (
        TypeError,
        ValueError,
        KeyError,
    ) as erro:
        st.error(
            "Não foi possível calcular os indicadores "
            "da análise por subsistemas."
        )
    
        st.exception(
            erro
        )
    
        return
    
    
    # ============================================================
    # CARTÕES DOS KPIS
    # ============================================================
    corte_medio = formatar_percentual(
        kpis_subsistemas[
            "Corte Médio (%)"
        ]
    )
    
    corte_subsistema = formatar_percentual(
        kpis_subsistemas[
            "Corte do Subsistema Crítico (%)"
        ]
    )
    
    participacao_tipo = formatar_percentual(
        kpis_subsistemas[
            "Participação do Tipo Predominante (%)"
        ]
    )
    
    corte_mes = formatar_percentual(
        kpis_subsistemas[
            "Corte no Mês Crítico (%)"
        ]
    )

    html_kpis = (
        '<div class="kpis-subsistemas">'
    
        '<div class="kpi-subsistema-card">'
        '<div class="kpi-subsistema-icone kpi-icone-corte">'
        '<span class="kpi-subsistema-simbolo" aria-hidden="true">'
        '%'
        '</span>'
        '</div>'
        '<div class="kpi-subsistema-conteudo">'
        '<div class="kpi-subsistema-titulo">'
        'Corte médio'
        '</div>'
        '<div class="kpi-subsistema-valor">'
        f'{corte_medio}'
        '</div>'
        '<div class="kpi-subsistema-detalhe">'
        'No período analisado'
        '</div>'
        '</div>'
        '</div>'
    
        '<div class="kpi-subsistema-card">'
        '<div class="kpi-subsistema-icone kpi-icone-subsistema">'
        '<span class="kpi-subsistema-simbolo" aria-hidden="true">'
        '◎'
        '</span>'
        '</div>'
        '<div class="kpi-subsistema-conteudo">'
        '<div class="kpi-subsistema-titulo">'
        'Subsistema crítico'
        '</div>'
        '<div class="kpi-subsistema-valor" '
        'title="'
        f'{kpis_subsistemas["Nome do Subsistema Crítico"]}'
        '">'
        f'{kpis_subsistemas["Nome do Subsistema Crítico"]}'
        '</div>'
        '<div class="kpi-subsistema-detalhe">'
        f'{corte_subsistema} de corte'
        '</div>'
        '</div>'
        '</div>'
    
        '<div class="kpi-subsistema-card">'
        '<div class="kpi-subsistema-icone kpi-icone-tipo">'
        '<span class="kpi-subsistema-simbolo" aria-hidden="true">'
        '&#9889;&#65038;'
        '</span>'
        '</div>'
        '<div class="kpi-subsistema-conteudo">'
        '<div class="kpi-subsistema-titulo">'
        'Tipo predominante'
        '</div>'
        '<div class="kpi-subsistema-valor">'
        f'{kpis_subsistemas["Tipo Predominante"]}'
        '</div>'
        '<div class="kpi-subsistema-detalhe">'
        f'{participacao_tipo} do curtailment'
        '</div>'
        '</div>'
        '</div>'
    
        '<div class="kpi-subsistema-card">'
        '<div class="kpi-subsistema-icone kpi-icone-mes">'
        '<span class="kpi-subsistema-simbolo" aria-hidden="true">'
        '&#x1F4C5;'
        '</span>'
        '</div>'
        '<div class="kpi-subsistema-conteudo">'
        '<div class="kpi-subsistema-titulo">'
        'Mês crítico'
        '</div>'
        '<div class="kpi-subsistema-valor">'
        f'{kpis_subsistemas["Rótulo do Mês Crítico"]}'
        '</div>'
        '<div class="kpi-subsistema-detalhe">'
        f'{corte_mes} de corte'
        '</div>'
        '</div>'
        '</div>'
    
        '</div>'
    )
    
    st.html(
        html_kpis
    )

    # ============================================================
    # CURTAILMENT MENSAL
    # ============================================================

    st.subheader(
        "Curtailment mensal por subsistema"
    )
    
    coluna_titulo, coluna_tipo = st.columns(
        [
            3,
            1,
        ],
        vertical_alignment="bottom",
    )
    
    with coluna_titulo:
        st.caption(
            "Energia curtailed mensal, distribuída entre "
            "os subsistemas do SIN."
        )
    
    with coluna_tipo:
        tipo_mensal_rotulo = st.selectbox(
            "Tipo de curtailment",
            options=[
                "Todos",
                "Energético",
                "Elétrico",
                "Confiabilidade",
            ],
            key="subsistemas_tipo_mensal",
        )
    
    tipo_mensal_codigo = TIPOS_CURTAILMENT[
        tipo_mensal_rotulo
    ]
    
    base_mensal = (
        preparar_curtailment_mensal_subsistemas(
            df=df_curtailment_subsistemas,
            tipo_curtailment=tipo_mensal_codigo,
        )
    )

    ordem_subsistemas = [
        "N",
        "NE",
        "SE",
        "S",
    ]
    
    data_inicial = pd.Timestamp(
        year=filtros_subsistemas[
            "ano_inicial"
        ],
        month=filtros_subsistemas[
            "mes_inicial"
        ],
        day=1,
    )
    
    data_final = pd.Timestamp(
        year=filtros_subsistemas[
            "ano_final"
        ],
        month=filtros_subsistemas[
            "mes_final"
        ],
        day=1,
    )
    
    meses_disponiveis = pd.date_range(
        start=data_inicial,
        end=data_final,
        freq="MS",
    )
    
    indice_completo = pd.MultiIndex.from_product(
        [
            meses_disponiveis,
            ordem_subsistemas,
        ],
        names=[
            "mes",
            "id_subsistema",
        ],
    )
    
    base_mensal_completa = (
        base_mensal
        .set_index(
            [
                "mes",
                "id_subsistema",
            ]
        )
        .reindex(
            indice_completo,
            fill_value=0.0,
        )
        .reset_index()
    )

    dados_grafico_mensal = (
        base_mensal_completa
        .pivot(
            index="mes",
            columns="id_subsistema",
            values="curtailment_gwh",
        )
        .reindex(
            columns=ordem_subsistemas,
            fill_value=0.0,
        )
        .sort_index()
    )

@st.cache_data(
    show_spinner=False,
)
def calcular_kpis_subsistemas_aplicacao(
    df_curtailment,
):
    """
    Calcula os KPIs da página Subsistemas.
    """

    return calcular_kpis_curtailment(df_curtailment)

def formatar_percentual(
    valor,
):
    """
    Formata um percentual segundo o padrão brasileiro.
    """

    if valor is None:
        return "Não disponível"

    return (f"{valor:,.2f}%".replace(",","X").replace(".",",").replace("X","."))

# ============================================================
# COMPETÊNCIA MAIS RECENTE
# ============================================================

hoje = date.today()

(
    ultimo_ano_completo,
    ultimo_mes_completo,
) = obter_ultima_competencia_completa(
    data_referencia=hoje
)

if not CAMINHO_UFS.exists():
    st.error(
        "A malha das UFs não foi encontrada."
    )

    st.code(
        str(CAMINHO_UFS)
    )

    st.stop()


(
    gdf_ufs,
    relatorio_ufs,
) = carregar_ufs_aplicacao(
    CAMINHO_UFS
)


# ============================================================
# NAVEGAÇÃO
# ============================================================

pagina_ativa = st.query_params.get(
    "pagina",
    "mapa",
)

paginas_permitidas = {
    "mapa",
    "subsistemas",
}

if pagina_ativa not in paginas_permitidas:
    pagina_ativa = "mapa"


# ============================================================
# BARRA DE NAVEGAÇÃO
# ============================================================

classe_mapa = (
    "sin-navbar-item sin-navbar-item-ativo"
    if pagina_ativa == "mapa"
    else "sin-navbar-item"
)

classe_subsistemas = (
    "sin-navbar-item sin-navbar-item-ativo"
    if pagina_ativa == "subsistemas"
    else "sin-navbar-item"
)

html_navbar = (
    '<div class="sin-navbar">'
    '<div class="sin-navbar-marca">'
    '<span class="sin-navbar-icone" aria-hidden="true">'
    '&#9889;&#65038;'
    '</span>'
    '<span class="sin-navbar-nome">'
    'SINmulator'
    '</span>'
    '</div>'

    '<div class="sin-navbar-menu">'

    f'<a class="{classe_mapa}" '
    'href="?pagina=mapa" target="_self">'
    '<span class="sin-navbar-item-icone" aria-hidden="true">'
    '&#128506;&#65039;'
    '</span>'
    '<span>Mapa</span>'
    '</a>'

    f'<a class="{classe_subsistemas}" '
    'href="?pagina=subsistemas" target="_self">'
    '<span class="sin-navbar-item-icone" aria-hidden="true">'
    '&#9638;'
    '</span>'
    '<span>Subsistemas</span>'
    '</a>'

    '</div>'
    '</div>'
)

st.html(
    html_navbar
)


# ============================================================
# CONTEÚDO DA ABA SUBSISTEMAS
# ============================================================

if pagina_ativa == "subsistemas":
    renderizar_pagina_subsistemas(
        hoje=hoje,
        ultimo_ano_completo=(
            ultimo_ano_completo
        ),
        ultimo_mes_completo=(
            ultimo_mes_completo
        ),
    )

    st.stop()


# ============================================================
# FILTROS SUSPENSOS DO MAPA
# ============================================================

anos_disponiveis = list(
    range(
        ANO_MINIMO,
        ultimo_ano_completo + 1,
    )
)

with st.container(
    border=True,
    key="filtros_mapa",
):
    (
        coluna_ano_inicial,
        coluna_mes_inicial,
        coluna_ano_final,
        coluna_mes_final,
        coluna_fonte,
        coluna_botao,
    ) = st.columns(
        [
            0.8,
            1.3,
            0.8,
            1.3,
            1.9,
            1,
        ],
        vertical_alignment="bottom",
    )

    with coluna_ano_inicial:
        ano_inicial = st.selectbox(
            "Ano inicial",
            options=anos_disponiveis,
            index=len(
                anos_disponiveis
            ) - 1,
            key="ano_inicial",
        )

    meses_iniciais_disponiveis = (
        obter_meses_disponiveis(
            ano=ano_inicial,
            ultimo_ano_completo=(
                ultimo_ano_completo
            ),
            ultimo_mes_completo=(
                ultimo_mes_completo
            ),
        )
    )

    with coluna_mes_inicial:
        mes_inicial = st.selectbox(
            "Mês inicial",
            options=meses_iniciais_disponiveis,
            index=0,
            format_func=formatar_mes,
            key="mes_inicial",
        )

    with coluna_ano_final:
        ano_final = st.selectbox(
            "Ano final",
            options=anos_disponiveis,
            index=len(
                anos_disponiveis
            ) - 1,
            key="ano_final",
        )

    meses_finais_disponiveis = (
        obter_meses_disponiveis(
            ano=ano_final,
            ultimo_ano_completo=(
                ultimo_ano_completo
            ),
            ultimo_mes_completo=(
                ultimo_mes_completo
            ),
        )
    )

    with coluna_mes_final:
        mes_final = st.selectbox(
            "Mês final",
            options=meses_finais_disponiveis,
            index=len(
                meses_finais_disponiveis
            ) - 1,
            format_func=formatar_mes,
            key="mes_final",
        )

    with coluna_fonte:
        opcao_fonte = st.selectbox(
            "Tipo de fonte",
            options=list(
                OPCOES_FONTES
            ),
            index=0,
            key="opcao_fonte",
        )

    fontes_selecionadas = (
        OPCOES_FONTES[
            opcao_fonte
        ]
    )

    with coluna_botao:
        carregar_periodo = st.button(
            "Aplicar",
            use_container_width=True,
            type="primary",
        )
        
    status_processamento = st.empty()

    resumo_filtros = st.empty()

# ============================================================
# VALIDAÇÃO DO PERÍODO
# ============================================================

if carregar_periodo:
    try:
        validar_periodo_interface(
            ano_inicial=ano_inicial,
            mes_inicial=mes_inicial,
            ano_final=ano_final,
            mes_final=mes_final,
            ultimo_ano_completo=(
                ultimo_ano_completo
            ),
            ultimo_mes_completo=(
                ultimo_mes_completo
            ),
        )

        st.session_state[
            "periodo_selecionado"
        ] = {
            "ano_inicial": ano_inicial,
            "mes_inicial": mes_inicial,
            "ano_final": ano_final,
            "mes_final": mes_final,
            "fontes": list(
                fontes_selecionadas
            ),
            "rotulo_fonte": opcao_fonte,
        }
        
        st.session_state[
            "processar_periodo"
        ] = True

    except ValueError as erro:
        st.error(
            str(erro)
        )

        if "periodo_selecionado" in st.session_state:
            st.info(
                "O período anterior continuará ativo até que "
                "uma nova seleção válida seja aplicada."
            )


# ============================================================
# PERÍODO SELECIONADO
# ============================================================

periodo_selecionado = st.session_state.get(
    "periodo_selecionado"
)

# ============================================================
# EXECUÇÃO DO PIPELINE
# ============================================================

if (
    periodo_selecionado is not None
    and st.session_state.get(
        "processar_periodo",
        False,
    )
):
    try:
        competencia_inicial = formatar_competencia(
            ano=periodo_selecionado[
                "ano_inicial"
            ],
            mes=periodo_selecionado[
                "mes_inicial"
            ],
        )
        
        competencia_final = formatar_competencia(
            ano=periodo_selecionado[
                "ano_final"
            ],
            mes=periodo_selecionado[
                "mes_final"
            ],
        )

        mensagem_processamento = (
            "Coletando e processando os dados do período "
            f"{competencia_inicial} a {competencia_final}. "
            "A primeira execução pode levar alguns minutos."
        )
        
        with status_processamento.container():
            with st.spinner(
                mensagem_processamento
            ):
                dados_pipeline = (
                    executar_pipeline_aplicacao(
                        ano_inicial=(
                            periodo_selecionado[
                                "ano_inicial"
                            ]
                        ),
                        mes_inicial=(
                            periodo_selecionado[
                                "mes_inicial"
                            ]
                        ),
                        ano_final=(
                            periodo_selecionado[
                                "ano_final"
                            ]
                        ),
                        mes_final=(
                            periodo_selecionado[
                                "mes_final"
                            ]
                        ),
                        fontes=tuple(
                            periodo_selecionado[
                                "fontes"
                            ]
                        ),
                        data_referencia=hoje,
                        timeout=TIMEOUT_PIPELINE,
                    )
                )

        st.session_state[
            "dados_pipeline"
        ] = dados_pipeline

        st.session_state[
            "periodo_processado"
        ] = periodo_selecionado.copy()

        st.session_state[
            "processar_periodo"
        ] = False
        
        status_processamento.empty()
        
        st.toast(
            "Mapa atualizado com sucesso.",
            icon="✅",
        )

    except Exception as erro:
        st.session_state[
            "processar_periodo"
        ] = False
    
        status_processamento.error(
            "Não foi possível concluir o processamento "
            "do período selecionado."
        )
    
        st.exception(
            erro
        )



# ============================================================
# RESUMO DO PIPELINE
# ============================================================

dados_pipeline = st.session_state.get(
    "dados_pipeline"
)

periodo_processado = st.session_state.get(
    "periodo_processado"
)

if (
    dados_pipeline is not None
    and periodo_processado is not None
):
    resumo_pipeline = dados_pipeline[
        "relatorios"
    ][
        "resumo_pipeline"
    ]

    rotulo_fonte = periodo_processado.get(
        "rotulo_fonte",
        "",
    )

    rotulo_fonte_resumido = (
        ROTULOS_FONTES_RESUMIDOS.get(
            rotulo_fonte,
            rotulo_fonte,
        )
    )

    quantidade_registros = (
        f"{resumo_pipeline['registros_curtailment']:,}"
        .replace(
            ",",
            ".",
        )
    )

    quantidade_linhas = (
        f"{resumo_pipeline['linhas_desenhaveis']:,}"
        .replace(
            ",",
            ".",
        )
    )

    resumo_html = (
        '<div class="resumo-filtros">'
        '<span class="resumo-filtros-icone">●</span>'
        '<span>'
        f'Foram processados <strong>{quantidade_registros} '
        f'registros</strong>, com '
        f'<strong>{resumo_pipeline["usinas"]} usinas</strong>, '
        f'<strong>{resumo_pipeline["pontos"]} pontos de conexão</strong> '
        f'e <strong>{quantidade_linhas} linhas de transmissão</strong> '
        f'no período de '
        f'<strong>{resumo_pipeline["periodo_inicial"]}</strong> a '
        f'<strong>{resumo_pipeline["periodo_final"]}</strong> '
        f'para a fonte <strong>{rotulo_fonte_resumido}</strong>.'
        '</span>'
        '</div>'
    )
    
    resumo_filtros.html(
        resumo_html
    )

# ============================================================
# MAPA INTERATIVO
# ============================================================

dados_pipeline = st.session_state.get(
    "dados_pipeline"
)

relatorio_mapa = None

with st.container(
    key="area_mapa",
):
    if dados_pipeline is None:
        (
            mapa_exibido,
            relatorio_mapa,
        ) = criar_mapa_inicial(
            gdf_ufs=gdf_ufs,
        )

    else:
        try:
            (
                mapa_exibido,
                relatorio_mapa,
            ) = construir_mapa_aplicacao(
                dados_pipeline=dados_pipeline,
                gdf_ufs=gdf_ufs,
            )

        except (
            FileNotFoundError,
            TypeError,
            ValueError,
            RuntimeError,
        ) as erro:
            st.error(
                "Não foi possível construir o mapa "
                "com os dados processados."
            )

            st.exception(
                erro
            )

            (
                mapa_exibido,
                relatorio_mapa,
            ) = criar_mapa_inicial(
                gdf_ufs=gdf_ufs,
            )

    html_mapa = (
        mapa_exibido
        .get_root()
        .render()
    )

    components.html(
        html_mapa,
        height=ALTURA_MAPA,
        scrolling=False,
    )

# ============================================================
# REGRAS DAS BASES
# ============================================================

with st.container(
    key="informacoes_bases",
):
    with st.expander(
        "Critérios de atualização",
        expanded=False,
    ):
        st.markdown(
            f"""
            - **Geração e curtailment:** período selecionado nos
              filtros.
            - **Fator de capacidade:** competência
              {ultimo_mes_completo:02d}/{ultimo_ano_completo}.
            - **Subestações e linhas de transmissão:** cadastros
              mais recentes disponibilizados pelo ONS.
            """
        )
