"""
Gráficos da análise CP45.

Este módulo recebe as bases consolidadas produzidas por
analise_cp45.py e cria figuras Plotly.

Nenhum dado é coletado, filtrado ou recalculado aqui.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

CORES_PERIMETROS_CP45 = {
    "Atual": "#64748B",
    "Pool nacional": "#E39632",
    "Condicionado ao PLD": "#315F8C",
}

CORES_CENARIOS_CP45 = {
    "Atual": "#64748B",
    "1A": "#E39632",
    "1B": "#315F8C",
    "2A": "#D88827",
    "2B": "#24527F",
    "3A": "#EDAA4C",
    "3B": "#47749E",
    "4A": "#C87922",
    "4B": "#163F68",
}

ORDEM_CENARIOS_CP45 = [
    "Atual",
    "1A",
    "1B",
    "2A",
    "2B",
    "3A",
    "3B",
    "4A",
    "4B",
]

def validar_resumo_cenarios_cp45(
    resumo_cenarios,
):
    """
    Valida a base consolidada dos cenários.
    """

    if not isinstance(
        resumo_cenarios,
        pd.DataFrame,
    ):
        raise TypeError(
            "resumo_cenarios deve ser um DataFrame."
        )

    if resumo_cenarios.empty:
        raise ValueError(
            "O resumo dos cenários está vazio."
        )

    colunas_obrigatorias = {
        "codigo",
        "cenario",
        "cenario_curto",
        "perimetro",
        "ordem",
        "geracao_esperada_gwh",
        "curtailment_gwh",
        "corte_pct",
        "diferenca_atual_gwh",
        "diferenca_atual_pp",
    }

    colunas_ausentes = (
        colunas_obrigatorias
        - set(
            resumo_cenarios.columns
        )
    )

    if colunas_ausentes:
        raise ValueError(
            "O resumo dos cenários não possui as "
            "colunas obrigatórias: "
            f"{sorted(colunas_ausentes)}."
        )

def validar_resumo_mensal_cp45(
    resumo_mensal,
):
    """
    Valida a base mensal da análise.
    """

    if not isinstance(
        resumo_mensal,
        pd.DataFrame,
    ):
        raise TypeError(
            "resumo_mensal deve ser um DataFrame."
        )

    if resumo_mensal.empty:
        raise ValueError(
            "O resumo mensal está vazio."
        )

    colunas_obrigatorias = {
        "mes_referencia",
        "mes_rotulo",
        "codigo",
        "cenario",
        "perimetro",
        "ordem",
        "geracao_esperada_gwh",
        "curtailment_gwh",
        "corte_pct",
        "diferenca_atual_gwh",
        "diferenca_atual_pp",
    }

    colunas_ausentes = (
        colunas_obrigatorias
        - set(
            resumo_mensal.columns
        )
    )

    if colunas_ausentes:
        raise ValueError(
            "O resumo mensal não possui as colunas "
            "obrigatórias: "
            f"{sorted(colunas_ausentes)}."
        )

def aplicar_layout_cp45(
    fig,
    altura,
    mostrar_legenda=True,
    margem_inferior=35,
):
    """
    Aplica o padrão visual da plataforma aos gráficos CP45.
    """

    fig.update_layout(
        height=altura,
        margin={
            "l": 15,
            "r": 15,
            "t": (
                55
                if mostrar_legenda
                else 25
            ),
            "b": margem_inferior,
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={
            "family": (
                "Segoe UI, Arial, sans-serif"
            ),
            "color": "#334155",
            "size": 12,
        },
        showlegend=mostrar_legenda,
        legend={
            "title": {
                "text": "",
            },
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.03,
            "xanchor": "center",
            "x": 0.5,
            "font": {
                "size": 11,
                "color": "#334155",
            },
        },
        hoverlabel={
            "bgcolor": "#FFFFFF",
            "bordercolor": "#D9E2EC",
            "font": {
                "color": "#102D57",
                "size": 12,
            },
        },
        bargap=0.22,
    )

    fig.update_xaxes(
        title=None,
        showgrid=False,
        showline=False,
        tickfont={
            "size": 10,
            "color": "#64748B",
        },
        fixedrange=True,
    )

    fig.update_yaxes(
        gridcolor=(
            "rgba(148, 163, 184, 0.20)"
        ),
        zeroline=False,
        showline=False,
        tickfont={
            "size": 10,
            "color": "#64748B",
        },
        title_font={
            "size": 11,
            "color": "#475569",
        },
        fixedrange=True,
    )

    return fig

def grafico_curtailment_cenarios_cp45(
    resumo_cenarios,
):
    """
    Compara o curtailment total do cenário atual
    e dos oito cenários simulados.
    """

    validar_resumo_cenarios_cp45(
        resumo_cenarios
    )

    base = (
        resumo_cenarios
        .copy()
        .sort_values(
            "ordem"
        )
        .reset_index(
            drop=True
        )
    )

    ordem_codigos = (
        base["codigo"]
        .tolist()
    )

    fig = px.bar(
        base,
        x="codigo",
        y="curtailment_gwh",
        color="perimetro",
        text="curtailment_gwh",
        category_orders={
            "codigo": ordem_codigos,
            "perimetro": [
                "Atual",
                "Pool nacional",
                "Condicionado ao PLD",
            ],
        },
        color_discrete_map=(
            CORES_PERIMETROS_CP45
        ),
        custom_data=[
            "cenario",
            "corte_pct",
            "diferenca_atual_gwh",
            "diferenca_atual_pp",
        ],
        labels={
            "codigo": "Cenário",
            "curtailment_gwh": (
                "Curtailment (GWh)"
            ),
            "perimetro": "Perímetro",
        },
    )

    fig.update_traces(
        texttemplate="%{text:,.1f}",
        textposition="outside",
        cliponaxis=False,
        marker_line_color="#FFFFFF",
        marker_line_width=0.5,
        hovertemplate=(
            "<b>%{customdata[0]}</b>"
            "<br>Código: %{x}"
            "<br>Curtailment: %{y:,.2f} GWh"
            "<br>Corte: %{customdata.2f}%"
            "<br>Diferença vs. atual: "
            "%{customdata+,.2f} GWh"
            "<br>Diferença de corte: "
            "%{customdata+.2f} p.p."
            "<extra></extra>"
        ),
    )

    fig.update_yaxes(
        title="Curtailment (GWh)",
        tickformat=",.0f",
    )

    fig = aplicar_layout_cp45(
        fig=fig,
        altura=390,
        mostrar_legenda=True,
        margem_inferior=35,
    )

    return fig

def grafico_corte_cenarios_cp45(
    resumo_cenarios,
):
    """
    Compara o percentual consolidado de corte no
    cenário atual e nos cenários simulados.
    """

    validar_resumo_cenarios_cp45(
        resumo_cenarios
    )

    base = (
        resumo_cenarios
        .copy()
        .sort_values(
            "ordem"
        )
        .reset_index(
            drop=True
        )
    )

    ordem_codigos = (
        base["codigo"]
        .tolist()
    )

    fig = px.bar(
        base,
        x="codigo",
        y="corte_pct",
        color="perimetro",
        text="corte_pct",
        category_orders={
            "codigo": ordem_codigos,
            "perimetro": [
                "Atual",
                "Pool nacional",
                "Condicionado ao PLD",
            ],
        },
        color_discrete_map=(
            CORES_PERIMETROS_CP45
        ),
        custom_data=[
            "cenario",
            "curtailment_gwh",
            "diferenca_atual_pp",
        ],
        labels={
            "codigo": "Cenário",
            "corte_pct": "Corte (%)",
            "perimetro": "Perímetro",
        },
    )

    fig.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="outside",
        cliponaxis=False,
        marker_line_color="#FFFFFF",
        marker_line_width=0.5,
        hovertemplate=(
            "<b>%{customdata[0]}</b>"
            "<br>Código: %{x}"
            "<br>Corte: %{y:.2f}%"
            "<br>Curtailment: "
            "%{customdata,.2f} GWh"
            "<br>Diferença vs. atual: "
            "%{customdata+.2f} p.p."
            "<extra></extra>"
        ),
    )

    fig.update_yaxes(
        title="Corte (%)",
        ticksuffix="%",
        tickformat=".1f",
    )

    fig = aplicar_layout_cp45(
        fig=fig,
        altura=390,
        mostrar_legenda=True,
        margem_inferior=35,
    )

    return fig

def grafico_mensal_cenario_cp45(
    resumo_mensal,
    codigo_cenario,
):
    """
    Compara mensalmente o cenário atual com um cenário
    simulado selecionado.
    """

    validar_resumo_mensal_cp45(
        resumo_mensal
    )

    codigo_cenario = str(
        codigo_cenario
    ).strip().upper()

    if codigo_cenario == "ATUAL":
        raise ValueError(
            "Selecione um cenário simulado."
        )

    codigos_disponiveis = set(
        resumo_mensal[
            "codigo"
        ]
        .astype(str)
        .str.upper()
        .unique()
        .tolist()
    )

    if codigo_cenario not in codigos_disponiveis:
        raise ValueError(
            "O cenário selecionado não está disponível: "
            f"{codigo_cenario}."
        )

    base = (
        resumo_mensal.loc[
            resumo_mensal[
                "codigo"
            ]
            .astype(str)
            .str.upper()
            .isin(
                [
                    "ATUAL",
                    codigo_cenario,
                ]
            )
        ]
        .copy()
    )

    base["serie"] = np.where(
        base["codigo"]
        .astype(str)
        .str.upper()
        .eq("ATUAL"),
        "Cenário atual",
        base["cenario"],
    )

    ordem_meses = (
        base[
            [
                "mes_referencia",
                "mes_rotulo",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            "mes_referencia"
        )[
            "mes_rotulo"
        ]
        .tolist()
    )

    nome_cenario = (
        base.loc[
            base["codigo"]
            .astype(str)
            .str.upper()
            .eq(
                codigo_cenario
            ),
            "cenario",
        ]
        .iloc[0]
    )

    fig = px.bar(
        base,
        x="mes_rotulo",
        y="curtailment_gwh",
        color="serie",
        barmode="group",
        category_orders={
            "mes_rotulo": ordem_meses,
            "serie": [
                "Cenário atual",
                nome_cenario,
            ],
        },
        color_discrete_map={
            "Cenário atual": "#94A3B8",
            nome_cenario: "#315F8C",
        },
        custom_data=[
            "cenario",
            "corte_pct",
            "diferenca_atual_gwh",
            "diferenca_atual_pp",
        ],
        labels={
            "mes_rotulo": "Mês",
            "curtailment_gwh": (
                "Curtailment (GWh)"
            ),
            "serie": "",
        },
    )

    fig.update_traces(
        marker_line_color="#FFFFFF",
        marker_line_width=0.4,
        hovertemplate=(
            "<b>%{customdata[0]}</b>"
            "<br>Mês: %{x}"
            "<br>Curtailment: %{y:,.2f} GWh"
            "<br>Corte: %{customdata.2f}%"
            "<br>Diferença vs. atual: "
            "%{customdata+,.2f} GWh"
            "<br>Diferença de corte: "
            "%{customdata+.2f} p.p."
            "<extra></extra>"
        ),
    )

    fig.update_yaxes(
        title="Curtailment (GWh)",
        tickformat=",.0f",
    )

    fig = aplicar_layout_cp45(
        fig=fig,
        altura=390,
        mostrar_legenda=True,
        margem_inferior=55,
    )

    fig.update_xaxes(
        categoryorder="array",
        categoryarray=ordem_meses,
        tickangle=-35,
    )

    return fig
