"""
Aplicação Streamlit para visualização de curtailment.

Nesta primeira etapa, a aplicação permite selecionar e
validar o período dos dados de curtailment.

Regras das bases:
- curtailment EOL e UFV: período escolhido pelo usuário;
- fator de capacidade: última competência mensal completa;
- subestações: cadastro mais atual disponível;
- linhas de transmissão: cadastro mais atual disponível.
"""

from datetime import date

import streamlit as st


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Curtailment ONS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


ANO_MINIMO = 2025

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


def validar_periodo_interface(
    ano,
    mes_inicial,
    mes_final,
    ultimo_ano_completo,
    ultimo_mes_completo,
):
    """
    Valida o período selecionado na interface.

    Raises
    ------
    ValueError
        Quando o período é inválido ou ainda não está
        mensalmente completo.
    """

    if mes_inicial > mes_final:
        raise ValueError(
            "O mês inicial não pode ser posterior "
            "ao mês final."
        )

    if ano > ultimo_ano_completo:
        raise ValueError(
            "O ano selecionado ainda não possui uma "
            "competência mensal completa disponível."
        )

    if (
        ano == ultimo_ano_completo
        and mes_final > ultimo_mes_completo
    ):
        raise ValueError(
            "O mês final selecionado ainda não está "
            "completo."
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


# ============================================================
# CABEÇALHO
# ============================================================

st.title(
    "Curtailment no Sistema Elétrico Brasileiro"
)

st.markdown(
    """
    Selecione o período dos dados de restrição que será
    analisado. Nesta primeira etapa, a aplicação apenas
    valida o período, sem executar o pipeline.
    """
)


# ============================================================
# BARRA LATERAL
# ============================================================

with st.sidebar:
    st.header(
        "Período de análise"
    )

    st.caption(
        "O período selecionado será aplicado aos dados "
        "de curtailment EOL e UFV."
    )

    anos_disponiveis = list(
        range(
            ANO_MINIMO,
            ultimo_ano_completo + 1,
        )
    )

    ano_padrao = ultimo_ano_completo

    ano = st.selectbox(
        "Ano",
        options=anos_disponiveis,
        index=anos_disponiveis.index(
            ano_padrao
        ),
    )

    meses_disponiveis = obter_meses_disponiveis(
        ano=ano,
        ultimo_ano_completo=(
            ultimo_ano_completo
        ),
        ultimo_mes_completo=(
            ultimo_mes_completo
        ),
    )

    if not meses_disponiveis:
        st.error(
            "Não existem meses completos disponíveis "
            "para o ano selecionado."
        )

        st.stop()

    with st.form(
        "formulario_periodo"
    ):
        mes_inicial = st.selectbox(
            "Mês inicial",
            options=meses_disponiveis,
            index=0,
            format_func=formatar_mes,
        )

        mes_final = st.selectbox(
            "Mês final",
            options=meses_disponiveis,
            index=len(
                meses_disponiveis
            ) - 1,
            format_func=formatar_mes,
        )

        carregar_periodo = st.form_submit_button(
            "Aplicar período",
            use_container_width=True,
        )

    st.divider()

    st.caption(
        "Última competência mensal completa: "
        f"{ultimo_mes_completo:02d}/"
        f"{ultimo_ano_completo}"
    )


# ============================================================
# VALIDAÇÃO DO PERÍODO
# ============================================================

if carregar_periodo:
    try:
        validar_periodo_interface(
            ano=ano,
            mes_inicial=mes_inicial,
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
            "ano": ano,
            "mes_inicial": mes_inicial,
            "mes_final": mes_final,
        }

        st.success(
            "Período selecionado com sucesso: "
            f"{mes_inicial:02d}/{ano} a "
            f"{mes_final:02d}/{ano}."
        )

    except ValueError as erro:
        st.error(
            str(erro)
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

    coluna_inicio, coluna_fim, coluna_cadastro = (
        st.columns(3)
    )

    with coluna_inicio:
        st.metric(
            "Início do período",
            (
                f"{periodo_selecionado['mes_inicial'\]:02d}/"
                f"{periodo_selecionado['ano']}"
            ),
        )

    with coluna_fim:
        st.metric(
            "Fim do período",
            (
                f"{periodo_selecionado['mes_final'\]:02d}/"
                f"{periodo_selecionado['ano']}"
            ),
        )

    with coluna_cadastro:
        st.metric(
            "Último mês completo",
            (
                f"{ultimo_mes_completo:02d}/"
                f"{ultimo_ano_completo}"
            ),
        )


# ===========================================
