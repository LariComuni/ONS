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

import streamlit as st
import streamlit.components.v1 as components

from src.mapa import (
    carregar_malha_ufs,
    criar_mapa_inicial,
    criar_mapa_interativo,
)
from src.pipeline import preparar_dados_aplicacao

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
            padding-right: 0;
            padding-bottom: 0;
            padding-left: 0;
        }

        /* Estilos da barra azul do SINmulator */
        .sin-navbar {
            ...
        }

        .sin-navbar-marca {
            ...
        }

        /* Estilos da barra suspensa de filtros */
        .st-key-filtros_mapa {
            position: relative;
            z-index: 50;

            width: min(1080px, calc(100vw - 3rem));

            margin-top: 14px;
            margin-right: auto;
            margin-bottom: -84px;
            margin-left: auto;

            padding: 0.65rem 0.85rem 0.75rem;

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
        div[data-testid="stSelectbox"] label,
        .st-key-filtros_mapa
        div[data-testid="stButton"] label {
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

        /* Estilos da área do mapa */
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

        @media (max-width: 900px) {
            .st-key-filtros_mapa {
                width: calc(100vw - 1rem);
                margin-top: 8px;
                margin-bottom: 8px;
                padding: 0.65rem;
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
# BARRA DE NAVEGAÇÃO
# ============================================================

html_navbar = """
<div class="sin-navbar">
    <div class="sin-navbar-marca">
        <span
            class="sin-navbar-icone"
            aria-hidden="true"
        >&#9889;&#65038;</span>

        <span class="sin-navbar-nome">
            SINmulator
        </span>
    </div>

    <div class="sin-navbar-menu">
        <div class="sin-navbar-item sin-navbar-item-ativo">
            <span
                class="sin-navbar-item-icone"
                aria-hidden="true"
            >&#128506;&#65039;</span>

            <span>Mapa</span>
        </div>
    </div>
</div>
"""

st.html(
    html_navbar
)

# ============================================================
# FILTROS
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
            1.25,
            0.8,
            1.25,
            1.8,
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

    (
        coluna_competencia,
        coluna_espaco,
        coluna_botao,
    ) = st.columns(
        [
            3,
            2,
            1.5,
        ]
    )

    with coluna_competencia:
        st.caption(
            "Última competência mensal completa: "
            f"{ultimo_mes_completo:02d}/"
            f"{ultimo_ano_completo}"
        )

    with coluna_botao:
        carregar_periodo = st.button(
            "Aplicar",
            use_container_width=True,
            type="primary",
        )


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
# RESUMO DA SELEÇÃO
# ============================================================

periodo_selecionado = st.session_state.get(
    "periodo_selecionado"
)

if periodo_selecionado is None:
    st.info(
        "Selecione o período na barra lateral e clique "
        "em Aplicar período."
    )

else:
    st.subheader(
        "Configuração selecionada"
    )

    (
        coluna_inicio,
        coluna_fim,
        coluna_fonte,
        coluna_cadastro,
    ) = st.columns(
        4
    )

    with coluna_inicio:
        st.metric(
            "Início do período",
            formatar_competencia(
                ano=periodo_selecionado[
                    "ano_inicial"
                ],
                mes=periodo_selecionado[
                    "mes_inicial"
                ],
            ),
        )
    
    with coluna_fim:
        st.metric(
            "Fim do período",
            formatar_competencia(
                ano=periodo_selecionado[
                    "ano_final"
                ],
                mes=periodo_selecionado[
                    "mes_final"
                ],
            ),
        )

    with coluna_fonte:
        rotulo_fonte = periodo_selecionado[
            "rotulo_fonte"
        ]
    
        st.metric(
            "Fonte",
            ROTULOS_FONTES_RESUMIDOS.get(
                rotulo_fonte,
                rotulo_fonte,
            ),
        )
    
    with coluna_cadastro:
        st.metric(
            "Último mês completo",
            formatar_competencia(
                ano=ultimo_ano_completo,
                mes=ultimo_mes_completo,
            ),
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

        st.toast(
            "Mapa atualizado com sucesso.",
            icon="✅",
        )

    except Exception as erro:
        st.session_state[
            "processar_periodo"
        ] = False

        st.error(
            "Não foi possível concluir o processamento "
            "do período selecionado."
        )

        if "dados_pipeline" in st.session_state:
            st.info(
                "O último processamento concluído com sucesso "
                "continuará disponível abaixo."
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

    st.subheader(
        "Resumo do processamento"
    )

    (
        coluna_registros,
        coluna_agregados,
        coluna_usinas,
        coluna_pontos,
    ) = st.columns(
        4
    )

    with coluna_registros:
        st.metric(
            "Registros de curtailment",
            f"{resumo_pipeline['registros_curtailment']:,}".replace(
                ",",
                ".",
            ),
        )

    with coluna_agregados:
        st.metric(
            "Registros agregados",
            f"{resumo_pipeline['registros_agregados_ponto']:,}".replace(
                ",",
                ".",
            ),
        )

    with coluna_usinas:
        st.metric(
            "Usinas",
            resumo_pipeline[
                "usinas"
            ],
        )

    with coluna_pontos:
        st.metric(
            "Pontos de conexão",
            resumo_pipeline[
                "pontos"
            ],
        )

    (
        coluna_linhas,
        coluna_busca,
        coluna_coord_usinas,
        coluna_coord_pontos,
    ) = st.columns(
        4
    )

    with coluna_linhas:
        st.metric(
            "Linhas desenháveis",
            f"{resumo_pipeline['linhas_desenhaveis']:,}".replace(
                ",",
                ".",
            ),
        )

    with coluna_busca:
        st.metric(
            "Itens pesquisáveis",
            resumo_pipeline[
                "registros_busca"
            ],
        )

    with coluna_coord_usinas:
        st.metric(
            "Coordenadas de usinas",
            resumo_pipeline[
                "coordenadas_usinas"
            ],
        )

    with coluna_coord_pontos:
        st.metric(
            "Coordenadas de pontos",
            resumo_pipeline[
                "coordenadas_pontos"
            ],
        )

    st.caption(
        "Período efetivamente processado: "
        f"{resumo_pipeline['periodo_inicial']} a "
        f"{resumo_pipeline['periodo_final']}."
    )

    with st.expander(
        "Ver relatório completo do pipeline"
    ):
        st.json(
            resumo_pipeline
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

st.subheader(
    "Regras de atualização das bases"
)

st.markdown(
    f"""
    - **dados EOL e UFV:** período escolhido pelo
      usuário, podendo abranger mais de um ano.
    - **Fator de capacidade:** última competência mensal
      completa, atualmente
      **{ultimo_mes_completo:02d}/{ultimo_ano_completo}**.
    - **Subestações:** cadastro mais atual disponibilizado
      pelo ONS.
    - **Linhas de transmissão:** cadastro mais atual
      disponibilizado pelo ONS.
    """
)


# ============================================================
# AVISO DA ETAPA
# ============================================================

if dados_pipeline is None:
    st.info(
        "Selecione um período e clique em "
        "Aplicar período para executar o pipeline"
        "e construir o mapa."
    )
