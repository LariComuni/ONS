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
        .block-container {
            max-width: 1280px;
            padding-top: 0.8rem;
            padding-bottom: 2rem;
        }

        .sinmulator-cabecalho {
            margin: 0 0 1rem;
            text-align: center;
        }

        .sinmulator-titulo {
            margin: 0;
            color: #111111;
            font-family: "Trebuchet MS", "Segoe UI", sans-serif;
            font-size: 3.2rem;
            font-weight: 800;
            letter-spacing: -0.06rem;
            line-height: 1.05;
        }

        .sinmulator-subtitulo {
            margin: 0.4rem 0 0;
            color: #60656f;
            font-family: "Segoe UI", sans-serif;
            font-size: 0.95rem;
            font-weight: 400;
        }

        .filtros-titulo {
            margin: 0 0 0.2rem;
            color: #111827;
            font-size: 1.1rem;
            font-weight: 700;
        }

        .filtros-descricao {
            margin: 0 0 1rem;
            color: #6b7280;
            font-size: 0.88rem;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #d9dde3;
            border-radius: 10px;
        }

        div[data-testid="stAlert"] {
            border-radius: 9px;
        }

        @media (max-width: 800px) {
            .block-container {
                padding-top: 0.5rem;
            }

            .sinmulator-titulo {
                font-size: 2.4rem;
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

ALTURA_MAPA = 850
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
):
    """
    Constrói o mapa interativo a partir dos resultados
    produzidos pelo pipeline.

    Retorno
    -------
    tuple
        Mapa Folium, relatório do mapa e relatório das UFs.
    """

    if not CAMINHO_UFS.exists():
        raise FileNotFoundError(
            "A malha das UFs não foi encontrada em: "
            f"{CAMINHO_UFS}")

    (
        gdf_ufs,
        relatorio_ufs,
    ) = carregar_ufs_aplicacao(
        CAMINHO_UFS
    )

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

    return (mapa_interativo,relatorio_mapa,relatorio_ufs)

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


# ============================================================
# CABEÇALHO
# ============================================================

st.markdown(
    """
    <div class="sinmulator-cabecalho">
        <h1 class="sinmulator-titulo">SINmulator</h1>
        <p class="sinmulator-subtitulo">
            Curtailment e restrições operativas no
            Sistema Interligado Nacional
        </p>
    </div>
    """,
    unsafe_allow_html=True,
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
    border=True
):
    st.markdown(
        """
        <p class="filtros-titulo">
            Filtros
        </p>

        <p class="filtros-descricao">
            Selecione as competências inicial e final e o tipo
            de fonte. O período pode abranger mais de um ano.
        </p>
        """,
        unsafe_allow_html=True,
    )

    (
        coluna_ano_inicial,
        coluna_mes_inicial,
        coluna_ano_final,
        coluna_mes_final,
        coluna_fonte,
    ) = st.columns(
        [
            1,
            1.4,
            1,
            1.4,
            2,
        ]
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
        
        st.success(
            "Configuração aplicada com sucesso: "
            f"{mes_inicial:02d}/{ano_inicial} a "
            f"{mes_final:02d}/{ano_final}, "
            f"fonte: {opcao_fonte}."
        )

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

        st.success(
            "Processamento concluído com sucesso."
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

if dados_pipeline is not None:
    try:
        with st.spinner(
            "Construindo o mapa interativo..."
        ):
            (
                mapa_interativo,
                relatorio_mapa,
                relatorio_ufs,
            ) = construir_mapa_aplicacao(
                dados_pipeline
            )

        st.subheader(
            "Mapa interativo"
        )

        st.caption(
            "Utilize a barra de pesquisa para localizar "
            "uma usina ou ponto de conexão. O painel lateral "
            "apresenta indicadores e gráficos."
        )

        html_mapa = (
            mapa_interativo
            .get_root()
            .render()
        )
        
        components.html(
            html_mapa,
            height=ALTURA_MAPA,
            scrolling=False,
        )

        with st.expander(
            "Ver relatório técnico do mapa"
        ):
            st.markdown(
                "**Construção do mapa**"
            )

            st.json(
                relatorio_mapa
            )

            st.markdown(
                "**Malha das UFs**"
            )

            st.json(
                relatorio_ufs
            )

    except (
        FileNotFoundError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as erro:
        st.error("Não foi possível construir o mapa interativo.")

        st.exception(erro)

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
