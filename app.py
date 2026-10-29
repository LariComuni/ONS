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
from io import BytesIO

import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import streamlit as st
import streamlit.components.v1 as components
import base64

from src.mapa import (
    carregar_malha_ufs,
    criar_mapa_inicial,
    criar_mapa_interativo,
)
from src.pipeline import preparar_dados_aplicacao
from src.analise_subsistemas import (
    calcular_kpis_curtailment,
    preparar_curtailment_mensal_subsistemas,
    preparar_download_curtailment_mensal,
    preparar_perfil_horario_curtailment,
    preparar_download_perfil_horario,
    preparar_corte_subsistema_tipo,  
    preparar_resumo_subsistemas,
    preparar_exportacao_subsistemas
)
from src.analise_ativos_elera import (
    ORDEM_ATIVOS_ELERA,
    calcular_kpis_ativos_elera,
    preparar_curtailment_mensal_ativos_elera,
    preparar_geracao_esperada_mensal_ativos_elera,
    preparar_participacao_curtailment_ativos_elera,
    preparar_participacao_geracao_ativos_elera,
    preparar_analise_individual_ativo_elera,
    preparar_exportacao_detalhada_ativos_elera,
)
from src.coleta_evt import (
    carregar_periodo_evt,
)
from src.dados_pld import (
    carregar_bases_pld,
    preparar_pld_aberto,
)
from src.preparacao_cp45 import (
    montar_base_fontes_cp45,
    preparar_ativos_horarios_cp45,
)
from src.cenarios_cp45 import (
    montar_base_cenarios_cp45,
)
from src.analise_cp45 import (
    obter_opcoes_filtros_cp45,
    preparar_analise_individual_cp45,
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
            height: 42px;
            padding: 0 1rem;
            
            box-sizing: border-box;
        
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

        .sin-navbar-item-elera {
            min-width: 138px;
            gap: 0.45rem;
        }
        
        .sin-navbar-logo-elera {
            display: inline-flex;
            align-items: center;
            justify-content: center;
        
            flex: 0 0 20px;
        
            width: 20px;
            height: 20px;
        
            overflow: hidden;
        
            background-color: #ffffff;
        
            border: 1px solid rgba(255, 255, 255, 0.35);
            border-radius: 50%;
        
            box-sizing: border-box;
        }
        
        .sin-navbar-logo-elera img {
            display: block;
        
            width: 18px;
            height: 18px;
        
            margin: 0;
            padding: 0;
        
            object-fit: contain;
            object-position: center;
        
            border: 0;
            border-radius: 50%;
        }
        
        .sin-navbar-logo-elera-fallback {
            color: #f97316;
            font-family:
                "Segoe UI Symbol",
                Arial,
                sans-serif;
            font-size: 1.1rem;
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

        /* Filtros da página Ativos Elera */

        .st-key-filtros_ativos_elera {
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
        
        .st-key-filtros_ativos_elera
        div[data-testid="stVerticalBlockBorderWrapper"] {
            padding: 0;
        
            background: transparent;
        
            border: 0;
            box-shadow: none;
        }
        
        .st-key-filtros_ativos_elera
        div[data-testid="stSelectbox"] {
            min-width: 0;
        }
        
        .st-key-filtros_ativos_elera
        div[data-testid="stSelectbox"] label {
            color: #334155;
            font-size: 0.78rem;
            font-weight: 600;
        }
        
        .st-key-filtros_ativos_elera
        div[data-testid="stButton"] button {
            min-height: 40px;
        
            border-radius: 9px;
        
            font-weight: 600;
        }
        
        /* Spinner apenas da aba Subsistemas */

        .st-key-filtros_subsistemas
        div[data-testid="stStatusWidget"],
        .st-key-filtros_subsistemas
        div[data-testid="stSpinner"] {
            margin-top: 0.45rem;
            margin-bottom: 0;
        }
        
        .st-key-filtros_subsistemas
        div[data-testid="stSpinner"] p {
            color: #475569;
            font-size: 0.82rem;
        }

        /* Spinner apenas da aba Ativos Elera */

        .st-key-filtros_ativos_elera
        div[data-testid="stStatusWidget"],
        .st-key-filtros_ativos_elera
        div[data-testid="stSpinner"] {
            margin-top: 0.45rem;
            margin-bottom: 0;
        }
        
        .st-key-filtros_ativos_elera
        div[data-testid="stSpinner"] p {
            color: #475569;
            font-size: 0.82rem;
        }

        /* resumo subsistemas */

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
        
        /* Cabeçalho subsistemas */
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
        
        /* Cabeçalho ativos elera */
        .cabecalho-ativos-elera {
            width: min(1500px, calc(100vw - 3rem));
        
            margin-top: 0.35rem;
            margin-right: auto;
            margin-bottom: 0.85rem;
            margin-left: auto;
        }
        
        .cabecalho-ativos-elera h1 {
            margin: 0 0 0.25rem;
        
            color: #0f2948;
            font-size: 1.65rem;
            font-weight: 700;
            line-height: 1.2;
        }
        
        /* KPIS */
        .kpis-subsistemas {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 1rem;
        
            width: min(1500px, calc(100vw - 3rem));
        
            margin-top: 1rem;
            margin-right: auto;
            margin-bottom: 1.25rem;
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
            margin-bottom: 0.25rem;
        
            color: #53667c;
            font-size: 0.82rem;
            font-weight: 650;
            line-height: 1.2;
        }
        
        .kpi-subsistema-valor {
            overflow: hidden;
        
            color: #102d57;
            font-size: 1.22rem;
            font-weight: 750;
            line-height: 1.2;
        
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .kpi-subsistema-detalhe {
            margin-top: 0.22rem;
        
            color: #7c8ca0;
            font-size: 0.75rem;
            line-height: 1.3;
        }
        
        .kpi-subsistema-card {
            min-height: 96px;
            padding: 0.95rem 1.05rem;
        }

        /* KPIs ativos elera */
        
        .kpis-ativos-elera {
            display: grid;
            grid-template-columns:
                repeat(4, minmax(0, 1fr));
            gap: 1rem;
        
            width: min(1500px, calc(100vw - 3rem));
        
            margin-top: 1rem;
            margin-right: auto;
            margin-bottom: 1.25rem;
            margin-left: auto;
        }
        
        .kpi-elera-card {
            display: flex;
            align-items: center;
            gap: 0.85rem;
        
            min-width: 0;
            min-height: 96px;
        
            padding: 0.95rem 1.05rem;
        
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
        
        .kpi-elera-icone {
            display: inline-flex;
            align-items: center;
            justify-content: center;
        
            flex: 0 0 auto;
        
            width: 48px;
            height: 48px;
        
            border-radius: 50%;
        }
        
        .kpi-elera-simbolo {
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
        
        .kpi-elera-conteudo {
            min-width: 0;
        }
        
        .kpi-elera-titulo {
            margin-bottom: 0.25rem;
        
            color: #53667c;
            font-size: 0.82rem;
            font-weight: 650;
            line-height: 1.2;
        }
        
        .kpi-elera-valor {
            overflow: hidden;
        
            color: #102d57;
            font-size: 1.22rem;
            font-weight: 750;
            line-height: 1.2;
        
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .kpi-elera-detalhe {
            margin-top: 0.22rem;
        
            color: #7c8ca0;
            font-size: 0.75rem;
            line-height: 1.3;
        }
        
        /* Geração esperada */
        
        .kpi-elera-icone-geracao {
            color: #2979e8;
            background-color: #e4f0ff;
        }
        
        /* Curtailment */
        
        .kpi-elera-icone-curtailment {
            color: #d97706;
            background-color: #fff3d6;
        }
        
        /* Corte médio */
        
        .kpi-elera-icone-corte {
            color: #05aaa4;
            background-color: #ddf8f6;
        }
        
        /* Usina mais cortada */
        
        .kpi-elera-icone-usina {
            color: #ef476f;
            background-color: #ffe8ed;
        }

        /* GRÁFICO CURT */

        .cabecalho-card-grafico {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
        
            width: 100%;
            min-height: 38px;
            margin: 0;
            padding: 0;
        }
        
        .titulo-card-grafico {
            display: flex;
            align-items: center;
        
            min-height: 38px;
            margin: 0;
            padding: 0;
        
            color: #102d57;
            font-size: 1.15rem;
            font-weight: 750;
            line-height: 1.2;
        }

        /* graficos ativos elera portfólio */
        
        .st-key-graficos_portfolio_elera {
            width: min(1500px, calc(100vw - 3rem));
        
            margin-top: 0.75rem;
            margin-right: auto;
            margin-bottom: 1.5rem;
            margin-left: auto;
        }
        
        .st-key-card_mensal_elera,
        .st-key-card_participacao_elera {
            width: 100%;
            min-height: 405px;
        
            margin: 0;
        
            padding: 0.75rem 0.85rem 0.45rem;
        
            background-color: #ffffff;
        
            border: 1px solid #e2e8f0;
            border-radius: 13px;
        
            box-shadow:
                0 6px 18px rgba(15, 42, 70, 0.08);
        
            box-sizing: border-box;
        }
        
        .st-key-card_mensal_elera
        div[data-testid="stVerticalBlockBorderWrapper"],
        .st-key-card_participacao_elera
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 0;
            box-shadow: none;
        }

        /* Seletor de métrica dentro do card mensal ativos elera */

        .st-key-card_mensal_elera
        div[data-testid="stSegmentedControl"] {
            display: flex;
            justify-content: flex-end;
        
            width: 100%;
        }
        
        .st-key-card_mensal_elera
        div[data-testid="stSegmentedControl"] > div {
            width: auto;
        }
        
        .st-key-card_mensal_elera
        div[data-testid="stSegmentedControl"] button {
            min-height: 34px;
        
            padding: 0.35rem 0.65rem;
        
            font-size: 0.78rem;
            line-height: 1;
            white-space: nowrap;
        }
        /*Análise individual dos ativos Elera*/
        
        .titulo-secao-elera {
            width: min(1500px, calc(100vw - 3rem));
        
            margin-top: 0;
            margin-right: auto;
            margin-bottom: 0.65rem;
            margin-left: auto;
        
            color: #0f2948;
            font-size: 1.15rem;
            font-weight: 700;
            line-height: 1.2;
        }
        
        .st-key-seletor_ativo_elera,
        .st-key-analise_individual_elera {
            width: min(1500px, calc(100vw - 3rem));
        
            margin-right: auto;
            margin-left: auto;
        }
        
        .st-key-seletor_ativo_elera {
            margin-bottom: 0.85rem;
        }
        
        .st-key-analise_individual_elera {
            margin-bottom: 1.5rem;
        }
        
        /* Seletor visual dos ativos */
        
        .st-key-seletor_ativo_elera
        div[data-testid="stPills"] {
            width: 100%;
        }
        
        .st-key-seletor_ativo_elera
        div[data-testid="stPills"] > div {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        
            width: 100%;
        }
        
        .st-key-seletor_ativo_elera
        div[data-testid="stPills"] button {
            min-height: 38px;
        
            padding: 0.45rem 0.8rem;
        
            color: #475569;
            background-color: #ffffff;
        
            border: 1px solid #dbe3ec;
            border-radius: 999px;
        
            font-size: 0.8rem;
            font-weight: 600;
        
            box-shadow:
                0 2px 6px rgba(15, 42, 70, 0.05);
        }
        
        /* Cards da análise individual */
        
        .st-key-card_grafico_ativo_elera,
        .st-key-card_resumo_ativo_elera {
            width: 100%;
            min-height: 450px;
        
            margin: 0;
            padding: 0.8rem 0.9rem;
        
            background-color: #ffffff;
        
            border: 1px solid #e2e8f0;
            border-radius: 13px;
        
            box-shadow:
                0 6px 18px rgba(15, 42, 70, 0.08);
        
            box-sizing: border-box;
        }
        
        .st-key-card_grafico_ativo_elera
        div[data-testid="stVerticalBlockBorderWrapper"],
        .st-key-card_resumo_ativo_elera
        div[data-testid="stVerticalBlockBorderWrapper"] {
            height: 100%;
        
            border: 0;
            box-shadow: none;
        }

        /* Seletores do gráfico individual */

        .st-key-card_grafico_ativo_elera
        div[data-testid="stSegmentedControl"] {
            display: flex;
            justify-content: flex-end;
        
            width: 100%;
        }
        
        .st-key-card_grafico_ativo_elera
        div[data-testid="stSegmentedControl"] > div {
            width: auto;
        }
        
        .st-key-card_grafico_ativo_elera
        div[data-testid="stSegmentedControl"] button {
            min-height: 34px;
        
            padding: 0.35rem 0.55rem;
        
            font-size: 0.75rem;
            line-height: 1;
            white-space: nowrap;
        }
        
        /* Conteúdo do card de resumo */
        
        .resumo-ativo-elera {
            display: flex;
            flex-direction: column;
        
            padding: 0.35rem 0.25rem 0;
        
            box-sizing: border-box;
        }
        .titulo-composicao-circular {
            margin-top: auto;
            margin-bottom: 0.15rem;
            padding-top: 0.75rem;
        
            color: #102d57;
            font-size: 0.85rem;
            font-weight: 700;
            line-height: 1.2;
        }
        /* Cabeçalho compacto do ativo */

        .resumo-ativo-cabecalho-compacto {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
        
            width: 100%;
        
            padding: 0.15rem 0 0.7rem;
        
            border-bottom: 1px solid #e2e8f0;
        
            box-sizing: border-box;
        }
        
        .resumo-ativo-identificacao {
            display: flex;
            align-items: center;
            gap: 0.55rem;
        
            min-width: 0;
        }
        
        .resumo-ativo-nome-compacto {
            overflow: hidden;
        
            color: #102d57;
            font-size: 1.1rem;
            font-weight: 750;
            line-height: 1.2;
        
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .resumo-ativo-selos {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 0.45rem;
        
            flex: 0 0 auto;
        }
        
        .resumo-ativo-selo {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.3rem;
        
            padding: 0.35rem 0.55rem;
        
            border: 1px solid transparent;
            border-radius: 999px;
        
            font-size: 0.72rem;
            font-weight: 650;
            line-height: 1;
            white-space: nowrap;
        }
        
        .resumo-ativo-selo-solar {
            color: #d97706;
            background-color: #fff6dc;
        
            border-color: #fde7a9;
        }
        
        .resumo-ativo-selo-eolica {
            color: #2f78ad;
            background-color: #eaf4fb;
        
            border-color: #d2e7f5;
        }
        
        .resumo-ativo-selo-local {
            color: #40668c;
            background-color: #f5f8fb;
        
            border-color: #dfe7ef;
        }
        
        .resumo-ativo-selo-icone {
            display: inline-flex;
            align-items: center;
            justify-content: center;
        
            font-family:
                "Segoe UI Symbol",
                Arial,
                sans-serif;
            font-size: 0.8rem;
            line-height: 1;
        }
        
        /* KPIs internos do ativo */
        
        .resumo-ativo-kpis {
            display: grid;
            grid-template-columns:
                repeat(3, minmax(0, 1fr));
            align-items: stretch;
            gap: 0.6rem;
        
            width: 100%;
        
            margin-top: 0.65rem;
            margin-bottom: 0.25rem;
        }
        .resumo-ativo-kpi {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        
            min-width: 0;
            min-height: 82px;
        
            padding: 0.75rem 0.65rem;
        
            text-align: center;
        
            background-color: #f8fafc;
        
            border: 1px solid #e5edf5;
            border-radius: 9px;
        
            box-sizing: border-box;
        }
        
        .resumo-ativo-kpi span,
        .resumo-ativo-kpi small {
            display: block;
        
            width: 100%;
        
            color: #7c8ca0;
        
            font-size: 0.7rem;
            line-height: 1.3;
            text-align: center;
        }
        
        .resumo-ativo-kpi strong {
            display: block;
        
            width: 100%;
        
            margin-top: 0.28rem;
        
            overflow: hidden;
        
            color: #102d57;
        
            font-size: 1rem;
            font-weight: 750;
            line-height: 1.2;
            text-align: center;
        
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .resumo-ativo-kpi small {
            margin-top: 0.18rem;
        }
        
        /* Composição dos cortes */
        
        .composicao-cortes-titulo {
            margin-bottom: 0.55rem;
        
            color: #102d57;
            font-size: 0.85rem;
            font-weight: 700;
            line-height: 1.2;
        }
        
        .barra-composicao-cortes {
            display: flex;
        
            width: 100%;
            height: 34px;
        
            overflow: hidden;
        
            background-color: #e2e8f0;
        
            border-radius: 8px;
        }
        
        .segmento-composicao {
            display: flex;
            align-items: center;
            justify-content: center;
        
            min-width: 0;
            overflow: hidden;
        
            color: #ffffff;
        
            font-size: 0.74rem;
            font-weight: 750;
            line-height: 1;
            white-space: nowrap;
        }
        
        .segmento-ene {
            background-color: #2f70c9;
        }
        
        .segmento-rel {
            background-color: #24aaa6;
        }
        
        .segmento-cnf {
            background-color: #ff6666;
        }
        
        /* Legenda da composição */
        
        .legenda-composicao-cortes {
            display: grid;
            grid-template-columns:
                repeat(3, minmax(0, 1fr));
            gap: 0.85rem;
        
            margin-top: 0.9rem;
        }
        
       .item-composicao {
            display: flex;
            align-items: flex-start;
            justify-content: flex-start;
            gap: 0.45rem;
        
            min-width: 0;
        }
        
        .bolinha-composicao {
            display: inline-block;
            flex: 0 0 10px;
        
            width: 10px;
            min-width: 10px;
            max-width: 10px;
        
            height: 10px;
            min-height: 10px;
            max-height: 10px;
        
            margin-top: 0.18rem;
        
            border-radius: 50%;
        
            box-sizing: border-box;
        }
        
        .bolinha-composicao.ene {
            background-color: #2f70c9;
        }
        
        .bolinha-composicao.rel {
            background-color: #24aaa6;
        }
        
        .bolinha-composicao.cnf {
            background-color: #ff6666;
        }
        
        .item-composicao strong,
        .item-composicao div > span {
            display: block;
        }
        
        .item-composicao strong {
            color: #334155;
            font-size: 0.72rem;
            line-height: 1.2;
        }
        
        .item-composicao div > span {
            margin-top: 0.1rem;
        
            color: #7c8ca0;
            font-size: 0.68rem;
            line-height: 1.2;
        }

        /* Exportação detalhada dos ativos Elera */

        .st-key-card_exportacao_ativos_elera {
            width: min(1500px, calc(100vw - 3rem));
        
            margin-top: 0;
            margin-right: auto;
            margin-bottom: 2rem;
            margin-left: auto;
        
            padding: 0.85rem 0.95rem;
        
            background-color: #ffffff;
        
            border: 1px solid #e2e8f0;
            border-radius: 13px;
        
            box-shadow:
                0 6px 18px rgba(15, 42, 70, 0.08);
        
            box-sizing: border-box;
        }
        
        .st-key-card_exportacao_ativos_elera
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 0;
            box-shadow: none;
        }
        
        .cabecalho-exportacao-elera {
            display: flex;
            flex-direction: column;
            justify-content: center;
        
            min-height: 46px;
        }
        
        .subtitulo-exportacao-elera {
            margin-top: 0.25rem;
        
            color: #64748b;
            font-size: 0.76rem;
            line-height: 1.35;
        }
        
        .st-key-card_exportacao_ativos_elera
        div[data-testid="stSelectbox"] label {
            color: #53667c;
            font-size: 0.76rem;
            font-weight: 600;
        }
        
        /* botões de download*/

        .st-key-download_mensal,
        .st-key-download_heatmap,
        .st-key-download_corte,
        .st-key-download_resumo,
        .st-key-download_detalhado,
        .st-key-download_portfolio_elera,
        .st-key-download_ativo_elera,
        .st-key-download_detalhado_elera {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            width: 100%;
        }
        
        .st-key-download_mensal
        div[data-testid="stDownloadButton"],
        .st-key-download_heatmap
        div[data-testid="stDownloadButton"],
        .st-key-download_corte
        div[data-testid="stDownloadButton"],
        .st-key-download_resumo
        div[data-testid="stDownloadButton"],
        .st-key-download_detalhado
        div[data-testid="stDownloadButton"],
        .st-key-download_portfolio_elera
        div[data-testid="stDownloadButton"],
        .st-key-download_ativo_elera
        div[data-testid="stDownloadButton"],
        .st-key-download_detalhado_elera
        div[data-testid="stDownloadButton"] {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            width: 100%;
        }
        
        .st-key-download_mensal
        div[data-testid="stDownloadButton"] button,
        .st-key-download_heatmap
        div[data-testid="stDownloadButton"] button,
        .st-key-download_corte
        div[data-testid="stDownloadButton"] button,
        .st-key-download_resumo
        div[data-testid="stDownloadButton"] button,
        .st-key-download_detalhado
        div[data-testid="stDownloadButton"] button,
        .st-key-download_portfolio_elera
        div[data-testid="stDownloadButton"] button,
        .st-key-download_ativo_elera
        div[data-testid="stDownloadButton"] button,
        .st-key-download_detalhado_elera
        div[data-testid="stDownloadButton"] button {
            position: relative;
        
            display: inline-flex;
            align-items: center;
            justify-content: center;
        
            width: 42px;
            min-width: 42px;
            max-width: 42px;
        
            height: 42px;
            min-height: 42px;
            max-height: 42px;
        
            padding: 0 !important;
        
            color: #ffffff !important;
            background-color: #7aaaf0 !important;
        
            border: 0 !important;
            border-radius: 50% !important;
        
            overflow: hidden;
        
            box-shadow:
                0 4px 9px rgba(45, 94, 157, 0.28);
        
            cursor: pointer;
        
            transition:
                background-color 0.15s ease,
                box-shadow 0.15s ease,
                transform 0.15s ease;
        }
        
        .st-key-download_mensal
        div[data-testid="stDownloadButton"] button:hover,
        .st-key-download_heatmap
        div[data-testid="stDownloadButton"] button:hover,
        .st-key-download_corte
        div[data-testid="stDownloadButton"] button:hover,
        .st-key-download_resumo
        div[data-testid="stDownloadButton"] button:hover,
        .st-key-download_detalhado
        div[data-testid="stDownloadButton"] button:hover,
        .st-key-download_portfolio_elera
        div[data-testid="stDownloadButton"] button:hover,
        .st-key-download_ativo_elera
        div[data-testid="stDownloadButton"] button:hover,
        .st-key-download_detalhado_elera
        div[data-testid="stDownloadButton"] button:hover {
            background-color: #6b9de8 !important;
        
            border: 0 !important;
        
            box-shadow:
                0 6px 13px rgba(45, 94, 157, 0.34);
        
            transform: translateY(-1px);
        }
        
        .st-key-download_mensal
        div[data-testid="stDownloadButton"] button:active,
        .st-key-download_heatmap
        div[data-testid="stDownloadButton"] button:active,
        .st-key-download_corte
        div[data-testid="stDownloadButton"] button:active,
        .st-key-download_resumo
        div[data-testid="stDownloadButton"] button:active,
        .st-key-download_detalhado
        div[data-testid="stDownloadButton"] button:active,
        .st-key-download_portfolio_elera
        div[data-testid="stDownloadButton"] button:active,
        .st-key-download_ativo_elera
        div[data-testid="stDownloadButton"] button:active,
        .st-key-download_detalhado_elera
        div[data-testid="stDownloadButton"] button:active {
            background-color: #5d8ed7 !important;
            transform: translateY(0);
        }
        
        .st-key-download_mensal
        div[data-testid="stDownloadButton"] button:focus-visible,
        .st-key-download_heatmap
        div[data-testid="stDownloadButton"] button:focus-visible, 
        .st-key-download_corte
        div[data-testid="stDownloadButton"] button:focus-visible,
        .st-key-download_resumo
        div[data-testid="stDownloadButton"] button:focus-visible,
        .st-key-download_detalhado
        div[data-testid="stDownloadButton"] button:focus-visible,
        .st-key-download_portfolio_elera
        div[data-testid="stDownloadButton"] button:focus-visible,
        .st-key-download_ativo_elera
        div[data-testid="stDownloadButton"] button:focus-visible,
        .st-key-download_detalhado_elera
        div[data-testid="stDownloadButton"] button:focus-visible {
            outline: 3px solid rgba(122, 170, 240, 0.35);
            outline-offset: 2px;
        }
        
        /* Esconde o conteúdo original do botão. */
        
        .st-key-download_mensal
        div[data-testid="stDownloadButton"] button p,
        .st-key-download_mensal
        div[data-testid="stDownloadButton"] button span,
        .st-key-download_heatmap
        div[data-testid="stDownloadButton"] button p,
        .st-key-download_heatmap
        div[data-testid="stDownloadButton"] button span, 
        .st-key-download_corte
        div[data-testid="stDownloadButton"] button p,
        .st-key-download_corte
        div[data-testid="stDownloadButton"] button span,
        .st-key-download_resumo
        div[data-testid="stDownloadButton"] button p,
        .st-key-download_resumo
        div[data-testid="stDownloadButton"] button span,
        .st-key-download_detalhado
        div[data-testid="stDownloadButton"] button p,
        .st-key-download_detalhado
        div[data-testid="stDownloadButton"] button span,
        .st-key-download_portfolio_elera
        div[data-testid="stDownloadButton"] button p,
        .st-key-download_portfolio_elera
        div[data-testid="stDownloadButton"] button span,
        .st-key-download_ativo_elera
        div[data-testid="stDownloadButton"] button p,
        .st-key-download_ativo_elera
        div[data-testid="stDownloadButton"] button span,
        .st-key-download_detalhado_elera
        div[data-testid="stDownloadButton"] button p,
        .st-key-download_detalhado_elera
        div[data-testid="stDownloadButton"] button span {
            visibility: hidden;
        
            width: 0;
            height: 0;
        
            margin: 0;
            padding: 0;
        }
        
        /* Ícone branco de download. */
        
        .st-key-download_mensal
        div[data-testid="stDownloadButton"] button::before,
        .st-key-download_heatmap
        div[data-testid="stDownloadButton"] button::before,
        .st-key-download_corte
        div[data-testid="stDownloadButton"] button::before,
        .st-key-download_resumo
        div[data-testid="stDownloadButton"] button::before,
        .st-key-download_detalhado
        div[data-testid="stDownloadButton"] button::before,
        .st-key-download_portfolio_elera
        div[data-testid="stDownloadButton"] button::before,
        .st-key-download_ativo_elera
        div[data-testid="stDownloadButton"] button::before,
        .st-key-download_detalhado_elera
        div[data-testid="stDownloadButton"] button::before {
            content: "";
        
            position: absolute;
            z-index: 2;
        
            top: 9px;
            left: 9px;
        
            width: 24px;
            height: 24px;
        
            background-color: #ffffff;
        
            -webkit-mask-image:
                url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M10.4 3h3.2v10.1l3.75-3.75 2.25 2.25L12 19.2 4.4 11.6l2.25-2.25 3.75 3.75V3zM5 20h14v3H5z'/%3E%3C/svg%3E");
        
            mask-image:
                url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M10.4 3h3.2v10.1l3.75-3.75 2.25 2.25L12 19.2 4.4 11.6l2.25-2.25 3.75 3.75V3zM5 20h14v3H5z'/%3E%3C/svg%3E");
        
            -webkit-mask-repeat: no-repeat;
            mask-repeat: no-repeat;
        
            -webkit-mask-position: center;
            mask-position: center;
        
            -webkit-mask-size: contain;
            mask-size: contain;
        
            pointer-events: none;
        }
        
        /* Formata o ícone Material. */
        
        .selo-tipo-curtailment {
            display: inline-flex;
            align-items: center;
            justify-content: center;
        
            flex: 0 0 auto;
        
            padding: 0.3rem 0.55rem;
        
            color: #2f6690;
            background-color: #edf5fb;
        
            border: 1px solid #d4e5f2;
            border-radius: 999px;
        
            font-size: 0.7rem;
            font-weight: 650;
            line-height: 1;
            white-space: nowrap;
        }

        .st-key-graficos_subsistemas {
            width: min(1500px, calc(100vw - 3rem));
        
            margin-top: 0;
            margin-right: auto;
            margin-bottom: 1.5rem;
            margin-left: auto;
        }
        
        .st-key-linha_superior_graficos,
        .st-key-linha_inferior_graficos {
            width: 100%;
            margin: 0;
            padding: 0;
        }
        
        .st-key-linha_inferior_graficos {
            margin-top: 1rem;
        }
        
        .st-key-card_grafico_mensal,
        .st-key-card_grafico_participacao {
            min-height: 390px;
        
            padding: 0.75rem 0.85rem 0.4rem;
        
            background-color: #ffffff;
        
            border: 1px solid #e2e8f0;
            border-radius: 13px;
        
            box-shadow:
                0 6px 18px rgba(15, 42, 70, 0.08);
        }
        
        .st-key-card_grafico_mensal
        div[data-testid="stVerticalBlockBorderWrapper"],
        .st-key-card_grafico_participacao
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 0;
            box-shadow: none;
        }

        .st-key-card_grafico_mensal
        div[data-testid="stSelectbox"] {
            width: 100%;
            max-width: 190px;
            margin-left: auto;
        }
        
        .st-key-card_grafico_mensal
        div[data-baseweb="select"] {
            min-height: 38px;
        }
        
        .st-key-card_grafico_mensal
        div[data-baseweb="select"] > div {
            min-height: 38px;
            font-size: 0.82rem;
        }

        .st-key-card_heatmap_subsistemas {
            width: 100%;
            
            margin: 0;
            padding: 0.75rem 0.85rem 0.45rem;
        
            background-color: #ffffff;
        
            border: 1px solid #e2e8f0;
            border-radius: 13px;
        
            box-shadow:
                0 6px 18px rgba(15, 42, 70, 0.08);
        
            box-sizing: border-box;
        }
        
        .st-key-card_heatmap_subsistemas
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 0;
            box-shadow: none;
        }
        
        .st-key-card_heatmap_subsistemas
        div[data-testid="stSelectbox"] {
            width: 100%;
            max-width: 190px;
            margin-left: auto;
        }

        .st-key-card_corte_subsistema {
            width: 100%;
            min-height: 100%;
        
            margin: 0;
            padding: 0.75rem 0.85rem 0.45rem;
        
            background-color: #ffffff;
        
            border: 1px solid #e2e8f0;
            border-radius: 13px;
        
            box-shadow:
                0 6px 18px rgba(15, 42, 70, 0.08);
        
            box-sizing: border-box;
        }
        
        .st-key-card_corte_subsistema
        div[data-testid="stVerticalBlockBorderWrapper"] {
            height: 100%;
        
            border: 0;
            box-shadow: none;
        }

        .st-key-card_tabela_subsistemas {
            width: min(1500px, calc(100vw - 3rem));
        
            margin-top: 0;
            margin-right: auto;
            margin-bottom: 1.75rem;
            margin-left: auto;
        
            padding: 0.85rem 0.95rem 1rem;
        
            background-color: #ffffff;
        
            border: 1px solid #e2e8f0;
            border-radius: 13px;
        
            box-shadow:
                0 6px 18px rgba(15, 42, 70, 0.08);
        
            box-sizing: border-box;
        }

        .tabela-resumo-wrapper {
            width: 100%;
            margin-top: 0.8rem;
        
            overflow-x: auto;
        
            border: 1px solid #e2e8f0;
            border-radius: 9px;
        }
        
        .tabela-resumo-subsistemas {
            width: 100%;
        
            border-collapse: collapse;
            border-spacing: 0;
        
            color: #334155;
            background-color: #ffffff;
        
            font-family:
                "Segoe UI",
                Arial,
                sans-serif;
            font-size: 0.82rem;
        }
        
        .tabela-resumo-subsistemas th {
            padding: 0.7rem 0.75rem;
        
            color: #64748b;
            background-color: #f8fafc;
        
            border-right: 1px solid #e2e8f0;
            border-bottom: 1px solid #dbe3ec;
        
            font-size: 0.76rem;
            font-weight: 600;
            text-align: left;
            white-space: nowrap;
        }
        
        .tabela-resumo-subsistemas th:last-child {
            border-right: 0;
        }
        
        .tabela-resumo-subsistemas td {
            padding: 0.72rem 0.75rem;
        
            border-right: 1px solid #edf1f5;
            border-bottom: 1px solid #edf1f5;
        
            vertical-align: middle;
            white-space: nowrap;
        }
        
        .tabela-resumo-subsistemas td:last-child {
            border-right: 0;
        }
        
        .tabela-resumo-subsistemas
        tbody tr:last-child td {
            border-bottom: 0;
        }
        
        .tabela-resumo-subsistemas
        tbody tr:hover {
            background-color: #f8fbfe;
        }
        
        .subsistema-tabela {
            display: inline-flex;
            align-items: center;
            gap: 0.55rem;
        
            color: #263b53;
            font-weight: 600;
        }
        
        .subsistema-cor {
            display: inline-block;
            flex: 0 0 auto;
        
            width: 11px;
            height: 11px;
        
            border: 1px solid rgba(15, 42, 70, 0.08);
            border-radius: 50%;
        
            box-shadow:
                0 1px 3px rgba(15, 42, 70, 0.12);
        }
        
        .numero-tabela {
            font-variant-numeric: tabular-nums;
        }
                
        .grafico-placeholder {
            display: flex;
            align-items: center;
            justify-content: center;
        
            min-height: 350px;
        
            color: #94a3b8;
            font-size: 0.82rem;
            text-align: center;
        }

        /* card de tabela completa download */

        .st-key-card_exportacao_subsistemas {
            width: min(1500px, calc(100vw - 3rem));
        
            margin-top: 0;
            margin-right: auto;
            margin-bottom: 2rem;
            margin-left: auto;
        
            padding: 0.85rem 0.95rem;
        
            background-color: #ffffff;
        
            border: 1px solid #e2e8f0;
            border-radius: 13px;
        
            box-shadow:
                0 6px 18px rgba(15, 42, 70, 0.08);
        
            box-sizing: border-box;
        }
        
        .st-key-card_exportacao_subsistemas
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 0;
            box-shadow: none;
        }
        
        .cabecalho-exportacao-subsistemas {
            display: flex;
            flex-direction: column;
            justify-content: center;
        
            min-height: 46px;
        }
        
        .subtitulo-exportacao-subsistemas {
            margin-top: 0.25rem;
        
            color: #64748b;
            font-size: 0.76rem;
            line-height: 1.35;
        }
        
        .st-key-card_exportacao_subsistemas
        div[data-testid="stSelectbox"] label {
            color: #53667c;
            font-size: 0.76rem;
            font-weight: 600;
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
                height: 38px;
                padding: 0 0.75rem;
            }
            
            .sin-navbar-item-elera {
                min-width: auto;
            }
            .kpis-subsistemas {
                grid-template-columns:
                    repeat(2, minmax(0, 1fr));
            }
            /* KPIs Ativos Elera */

            .kpis-ativos-elera {
                grid-template-columns:
                    repeat(2, minmax(0, 1fr));
            }
        
            /* Cards de gráficos da aba Subsistemas */
        
            .st-key-card_grafico_mensal,
            .st-key-card_grafico_participacao {
                min-height: auto;
            }
        
            /* Área dos gráficos Ativos Elera */
        
            .st-key-graficos_portfolio_elera {
                width: calc(100vw - 1rem);
            }
        
            .st-key-card_mensal_elera,
            .st-key-card_participacao_elera {
                min-height: auto;
            }
            
            /* Análise individual dos ativos Elera */

            .titulo-secao-elera,
            .st-key-seletor_ativo_elera,
            .st-key-analise_individual_elera {
                width: calc(100vw - 1rem);
            }
            
            .st-key-card_grafico_ativo_elera,
            .st-key-card_resumo_ativo_elera {
                min-height: auto;
            }
            
            .resumo-ativo-kpis {
                grid-template-columns:
                    repeat(3, minmax(0, 1fr));
            }
            .st-key-card_exportacao_ativos_elera {
                width: calc(100vw - 1rem);
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

GRANULARIDADES_EXPORTACAO = {
    "Dia e hora": "DIA_HORA",
    "Mês e hora": "MES_HORA",
    "Ano e hora": "ANO_HORA",
    "Dia": "DIA",
    "Mês": "MES",
    "Ano": "ANO",
}

CAMINHO_LOGO_ELERA = (
    Path(__file__).resolve().parent
    / "assets"
    / "logo_elera.png")

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

def formatar_numero_brasileiro(
    valor,
    casas_decimais=1,
):
    """
    Formata um número usando separadores no padrão brasileiro.

    Exemplos
    --------
    21976.8 -> 21.976,8
    19.423  -> 19,42
    """

    if pd.isna(
        valor
    ):
        return "—"

    valor_formatado = (f"{valor:,.{casas_decimais}f}")

    return (valor_formatado.replace(",","X").replace(".",",").replace("X","."))

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

@st.cache_resource(show_spinner=False)
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

@st.cache_data(show_spinner=False)

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

def renderizar_filtros_ativos_elera(
    ultimo_ano_completo,
    ultimo_mes_completo,
):
    """
    Renderiza os filtros independentes da página ativos elera.

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
        key="filtros_ativos_elera",
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
                key="ativos_elera_ano_inicial",
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
                key="ativos_elera_mes_inicial",
            )

        with coluna_ano_final:
            ano_final = st.selectbox(
                "Ano final",
                options=anos_disponiveis,
                index=len(
                    anos_disponiveis
                ) - 1,
                key="ativos_elera_ano_final",
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
                key="ativos_elera_mes_final",
            )

        with coluna_fonte:
            opcao_fonte = st.selectbox(
                "Tipo de fonte",
                options=list(
                    OPCOES_FONTES
                ),
                index=0,
                key="ativos_elera_opcao_fonte",
            )

        fontes_selecionadas = (OPCOES_FONTES[opcao_fonte])

        with coluna_botao:
            aplicar_filtros = st.button(
                "Aplicar",
                use_container_width=True,
                type="primary",
                key="ativos_elera_aplicar",
            )
            
        status_ativos_elera = st.empty()
        resumo_ativos_elera = st.empty()

    if not aplicar_filtros:
        return (None,status_ativos_elera,resumo_ativos_elera)

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
        status_ativos_elera,
        resumo_ativos_elera,
    )

def renderizar_filtros_cp45(
    ultimo_ano_completo,
    ultimo_mes_completo,
    usinas_disponiveis,
):
    """
    Renderiza os filtros independentes da página CP45.

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
        key="filtros_cp45",
    ):
        (
            coluna_ano_inicial,
            coluna_mes_inicial,
            coluna_ano_final,
            coluna_mes_final,
            coluna_botao,
        ) = st.columns(
            [
                0.8,
                1.3,
                0.8,
                1.3,
                1.0,
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
                key="cp45_ano_inicial",
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
                key="cp45_mes_inicial",
            )

        with coluna_ano_final:
            ano_final = st.selectbox(
                "Ano final",
                options=anos_disponiveis,
                index=len(
                    anos_disponiveis
                ) - 1,
                key="cp45_ano_final",
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
                key="cp45_mes_final",
            )

        with coluna_botao:
            aplicar_filtros = st.button(
                "Aplicar",
                use_container_width=True,
                type="primary",
                key="cp45_aplicar",
            )

        status_cp45 = st.empty()
        resumo_cp45 = st.empty()

    if not aplicar_filtros:
        return (
            None,
            status_cp45,
            resumo_cp45,
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
        },
        status_cp45,
        resumo_cp45,
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
    # ============================================================
    # RECUPERAÇÃO DOS DADOS PROCESSADOS
    # ============================================================
        
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
    # GRÁFICOS DE CURTAILMENT POR SUBSISTEMA
    # ============================================================
    
    with st.container(
        key="graficos_subsistemas",
    ):
        with st.container(
            key="linha_superior_graficos",
            ):
                (
                    coluna_grafico_mensal,
                    coluna_grafico_participacao,
                ) = st.columns(
                    [
                        1.75,
                        1,
                    ],
                    gap="medium",
                )
            
                with coluna_grafico_mensal:
                    with st.container(
                        border=True,
                        key="card_grafico_mensal",
                    ):
                        # ==========================================
                        # DOWNLOAD CO CURTAILMENT MENSAL
                        # ==========================================

                        try:
                            dados_download_mensal = (
                                preparar_download_curtailment_mensal(
                                    df_curtailment_subsistemas
                                )
                            )
                        
                            arquivo_mensal_xlsx = (
                                gerar_excel_dataframe(
                                    df=dados_download_mensal,
                                    nome_planilha=(
                                        "Curtailment mensal"
                                    ),
                                )
                            )
                        
                        except (
                            TypeError,
                            ValueError,
                            KeyError,
                        ) as erro:
                            arquivo_mensal_xlsx = None
                        
                            st.warning(
                                "Não foi possível preparar o arquivo "
                                "do curtailment mensal."
                            )
                        
                            st.caption(
                                str(erro)
                            )
                        
                        # ========================================
                        # CABEÇALHO DO GRÁFICO
                        # ========================================
                        (
                            coluna_titulo,
                            coluna_tipo,
                            coluna_download,
                        ) = st.columns(
                            [
                                4,
                                1.15,
                                0.38,
                            ],
                            vertical_alignment="bottom",
                        )
                
                        with coluna_titulo:
                            st.html(
                                """
                                <div class="titulo-card-grafico">
                                    Curtailment mensal por subsistema
                                </div>
                                """
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
                                label_visibility="collapsed",
                            )

                        with coluna_download:
                            with st.container(
                                key="download_mensal",
                            ):
                                if arquivo_mensal_xlsx is not None:
                                    nome_arquivo_mensal = (
                                        "SINmulator_"
                                        "curtailment_mensal_"
                                        f"{filtros_subsistemas['ano_inicial']}-"
                                        f"{filtros_subsistemas['mes_inicial']:02d}_"
                                        f"{filtros_subsistemas['ano_final']}-"
                                        f"{filtros_subsistemas['mes_final']:02d}"
                                        ".xlsx"
                                    )
                        
                                    st.download_button(
                                        label="Baixar",
                                        data=arquivo_mensal_xlsx,
                                        file_name=nome_arquivo_mensal,
                                        mime=(
                                            "application/vnd.openxmlformats-officedocument."
                                            "spreadsheetml.sheet"
                                        ),
                                        help=(
                                            "Baixar o curtailment mensal por "
                                            "subsistema e tipo"
                                        ),
                                        key="botao_download_mensal",
                                    )
                
                        tipo_mensal_codigo = TIPOS_CURTAILMENT[tipo_mensal_rotulo]
                
                        try:
                            base_mensal = (
                                preparar_curtailment_mensal_subsistemas(
                                    df=df_curtailment_subsistemas,
                                    tipo_curtailment=tipo_mensal_codigo,
                                )
                            )
                
                        except (
                            TypeError,
                            ValueError,
                            KeyError,
                        ) as erro:
                            st.warning(
                                "Não foi possível preparar o curtailment "
                                "mensal para o tipo selecionado."
                            )
                
                            st.caption(
                                str(erro)
                            )
                
                            base_mensal = pd.DataFrame(
                                columns=[
                                    "mes",
                                    "id_subsistema",
                                    "curtailment_gwh",
                                ]
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
            
                        rotulos_subsistemas = {
                            "N": "N",
                            "NE": "NE",
                            "SE": "SE",
                            "S": "S",
                        }
                        
                        cores_subsistemas = {
                            "N": "#F3A6B8",
                            "NE": "#2F6690",
                            "SE": "#3FA7A3",
                            "S": "#8172B3",
                        }
                        
                        dados_plot_mensal = (
                            base_mensal_completa
                            .copy()
                        )
                        
                        dados_plot_mensal["mes_rotulo"] = (
                            dados_plot_mensal["mes"]
                            .dt.strftime("%m/%Y")
                        )
                        
                        dados_plot_mensal["subsistema_rotulo"] = (
                            dados_plot_mensal["id_subsistema"]
                            .map(
                                rotulos_subsistemas
                            )
                        )
                        
                        ordem_meses = (
                            dados_plot_mensal[
                                [
                                    "mes",
                                    "mes_rotulo",
                                ]
                            ]
                            .drop_duplicates()
                            .sort_values(
                                "mes"
                            )[
                                "mes_rotulo"
                            ]
                            .tolist()
                        )
                        
                        ordem_subsistemas_rotulos = [
                            "N",
                            "NE",
                            "SE",
                            "S",
                        ]
                        
                        cores_subsistemas_rotulos = {
                            rotulos_subsistemas[codigo]: cor
                            for codigo, cor
                            in cores_subsistemas.items()
                        }
                        
                        fig_mensal = px.bar(
                            dados_plot_mensal,
                            x="mes_rotulo",
                            y="curtailment_gwh",
                            color="subsistema_rotulo",
                            category_orders={
                                "mes_rotulo": ordem_meses,
                                "subsistema_rotulo": (
                                    ordem_subsistemas_rotulos
                                ),
                            },
                            color_discrete_map=(
                                cores_subsistemas_rotulos
                            ),
                            labels={
                                "mes_rotulo": "Mês",
                                "curtailment_gwh": (
                                    "Curtailment (GWh)"
                                ),
                                "subsistema_rotulo": (
                                    "Subsistema"
                                ),
                            },
                            custom_data=[
                                "subsistema_rotulo",
                            ],
                        )
                        
                        fig_mensal.update_traces(
                            marker_line_color="#FFFFFF",
                            marker_line_width=0.7,
                            hovertemplate=(
                                "<b>%{customdata[0]}</b>"
                                "<br>Mês: %{x}"
                                "<br>Curtailment: %{y:,.2f} GWh"
                                "<extra></extra>"
                            ),
                        )
                        
                        fig_mensal.update_layout(
                            barmode="stack",
                            height=325,
                            margin={
                                "l": 10,
                                "r": 10,
                                "t": 52,
                                "b": 10,
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
                            legend={
                                "title": {
                                    "text": "",
                                },
                                "orientation": "h",
                                "yanchor": "bottom",
                                "y": 1.02,
                                "xanchor": "center",
                                "x": 0.5,
                                "font": {
                                    "size": 13,
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
                            bargap=0.25,
                        )
                        
                        fig_mensal.update_xaxes(
                            title=None,
                            showgrid=False,
                            showline=False,
                            tickfont={
                                "size": 11,
                                "color": "#64748B",
                            },
                            fixedrange=True,
                        )
                        
                        fig_mensal.update_yaxes(
                            title="Curtailment (GWh)",
                            gridcolor="rgba(148, 163, 184, 0.20)",
                            griddash="dot",
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
                            tickformat=",.0f",
                            fixedrange=True,
                        )
                        
                        st.plotly_chart(
                            fig_mensal,
                            width="stretch",
                            height=325,
                            config={
                                "displayModeBar": False,
                                "responsive": True,
                            },
                            key=(
                                "grafico_mensal_"
                                f"{tipo_mensal_codigo}"
                            ),
                        )
            
            
                with coluna_grafico_participacao:
                    with st.container(
                        border=True,
                        key="card_grafico_participacao",
                    ):
                        rotulo_tipo_participacao = {
                            "TODOS": "Todos os tipos",
                            "ENE": "Energético",
                            "REL": "Elétrico",
                            "CNF": "Confiabilidade",
                        }.get(
                            tipo_mensal_codigo,
                            tipo_mensal_rotulo,
                        )
                        
                        titulo_participacao_html = (
                            '<div class="cabecalho-card-grafico">'
                            '<div class="titulo-card-grafico">'
                            'Participação do curtailment'
                            '</div>'
                            '<span class="selo-tipo-curtailment">'
                            f'{rotulo_tipo_participacao}'
                            '</span>'
                            '</div>'
                        )
                        
                        st.markdown(
                            titulo_participacao_html,
                            unsafe_allow_html=True,
                        )
                        
                        participacao_subsistemas = (
                            base_mensal_completa
                            .groupby(
                                "id_subsistema",
                                as_index=False,
                                observed=True,
                            )
                            .agg(
                                curtailment_gwh=(
                                    "curtailment_gwh",
                                    "sum",
                                )
                            )
                        )
                
                        participacao_subsistemas[
                            "subsistema_rotulo"
                        ] = (
                            participacao_subsistemas[
                                "id_subsistema"
                            ]
                            .map(
                                rotulos_subsistemas
                            )
                        )
                
                        participacao_subsistemas = (
                            participacao_subsistemas[
                                participacao_subsistemas[
                                    "curtailment_gwh"
                                ] > 0
                            ]
                            .copy()
                        )
                
                        curtailment_total_gwh = (
                            participacao_subsistemas[
                                "curtailment_gwh"
                            ]
                            .sum()
                        )
                
                        if curtailment_total_gwh > 0:
                            participacao_subsistemas[
                                "participacao_pct"
                            ] = (
                                100
                                * participacao_subsistemas[
                                    "curtailment_gwh"
                                ]
                                / curtailment_total_gwh
                            )
            
                            ordem_codigos_subsistemas = [
                                "N",
                                "NE",
                                "SE",
                                "S",
                            ]
                            
                            participacao_subsistemas[
                                "id_subsistema"
                            ] = pd.Categorical(
                                participacao_subsistemas[
                                    "id_subsistema"
                                ],
                                categories=ordem_codigos_subsistemas,
                                ordered=True,
                            )
                            
                            participacao_subsistemas = (
                                participacao_subsistemas
                                .sort_values(
                                    "id_subsistema"
                                )
                                .reset_index(
                                    drop=True
                                )
                            )
                            
                            limite_rotulo_externo = 5.0
            
                            participacoes = (
                                participacao_subsistemas[
                                    "participacao_pct"
                                ]
                                .fillna(0.0)
                                .astype(float)
                                .tolist()
                            )
            
                            nomes_subsistemas = (
                                participacao_subsistemas[
                                    "subsistema_rotulo"
                                ]
                                .astype(str)
                                .tolist()
                            )
                            
                            posicoes_rotulos = [
                                (
                                    "inside"
                                    if participacao >= 5.0
                                    else "outside"
                                )
                                for participacao in participacoes
                            ]
                            
                            textos_percentuais = [
                                (
                                    f"{participacao:.1f}%"
                                    if participacao >= limite_rotulo_externo
                                    else (
                                        f"{subsistema}<br>{participacao:.1f}%"
                                    )
                                )
                                for subsistema, participacao
                                in zip(
                                    nomes_subsistemas,
                                    participacoes,
                                )
                            ]
                            
                            destaque_fatias = [
                                0.0
                                for _ in participacoes
                            ]
                
                            fig_participacao = px.pie(
                                participacao_subsistemas,
                                names="subsistema_rotulo",
                                values="curtailment_gwh",
                                hole=0.62,
                                category_orders={
                                    "subsistema_rotulo": (
                                        ordem_subsistemas_rotulos
                                    ),
                                },
                                color="subsistema_rotulo",
                                color_discrete_map=(
                                    cores_subsistemas_rotulos
                                ),
                            )
                
                            fig_participacao.update_traces(
                                sort=False,
                                direction="clockwise",
                                rotation=0,
                                domain={
                                    "x": [
                                        0.05,
                                        0.95,
                                    ],
                                    "y": [
                                        0.00,
                                        0.78,
                                    ],
                                },
                                marker={
                                    "line": {
                                        "color": "#FFFFFF",
                                        "width": 0.5,
                                    },
                                },
                                text=textos_percentuais,
                                textinfo="text",
                                textposition=posicoes_rotulos,
                                insidetextorientation="horizontal",
                                insidetextfont={
                                    "size": 12,
                                    "color": "#FFFFFF",
                                },
                                outsidetextfont={
                                    "size": 11,
                                    "color": "#334155",
                                },
                                hovertemplate=(
                                    "<b>%{label}</b>"
                                    "<br>Curtailment: %{value:,.2f} GWh"
                                    "<br>Participação: %{percent:.1%}"
                                    "<extra></extra>"
                                ),
                                automargin=True,
                            )
                
                            total_formatado = (
                                f"{curtailment_total_gwh:,.1f}"
                                .replace(
                                    ",",
                                    "X",
                                )
                                .replace(
                                    ".",
                                    ",",
                                )
                                .replace(
                                    "X",
                                    ".",
                                )
                            )
                
                            fig_participacao.update_layout(
                                height=365,
                                margin={
                                    "l": 55,
                                    "r": 55,
                                    "t": 65,
                                    "b": 10,
                                },
                                uniformtext={
                                    "minsize": 9,
                                    "mode": "show",
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
                                legend={
                                    "title": {
                                        "text": "",
                                    },
                                    "orientation": "h",
                                    "yanchor": "bottom",
                                    "y": 1.05,
                                    "xanchor": "center",
                                    "x": 0.5,
                                    "font": {
                                        "size": 13,
                                        "color": "#334155",
                                    },
                                    "itemsizing": "constant",
                                    "traceorder": "normal",
                                },
                                hoverlabel={
                                    "bgcolor": "#FFFFFF",
                                    "bordercolor": "#D9E2EC",
                                    "font": {
                                        "color": "#102D57",
                                        "size": 12,
                                    },
                                },
                                annotations=[
                                    {
                                        "text": (
                                            f"<b>{total_formatado}</b>"
                                            "<br>"
                                            "<span style='font-size:11px'>"
                                            "GWh no período"
                                            "</span>"
                                        ),
                                        "x": 0.5,
                                        "y": 0.39,
                                        "showarrow": False,
                                        "align": "center",
                                        "font": {
                                            "size": 16,
                                            "color": "#102D57",
                                        },
                                    }
                                ],
                            )
                
                            st.plotly_chart(
                                fig_participacao,
                                width="stretch",
                                height=325,
                                config={
                                    "displayModeBar": False,
                                    "responsive": True,
                                },
                                key=(
                                    "grafico_participacao_"
                                    f"{tipo_mensal_codigo}"
                                ),
                            )
                
                        else:
                            st.info(
                                "Não há valores de curtailment para "
                                "o tipo selecionado."
                            )
        with st.container(
            key="linha_inferior_graficos",
            ):
                (
                    coluna_heatmap,
                    coluna_direita_inferior,
                ) = st.columns(
                    [
                        1.75,
                        1,
                    ],
                    gap="medium",
                )
                
                with coluna_heatmap:
                    with st.container(
                        border=True,
                        key="card_heatmap_subsistemas",
                    ):
                        # ====================================================
                        # DOWNLOAD DO PERFIL HORÁRIO
                        # ====================================================
                
                        try:
                            dados_download_heatmap = (
                                preparar_download_perfil_horario(
                                    df_curtailment_subsistemas
                                )
                            )
                
                            arquivo_heatmap_xlsx = (
                                gerar_excel_dataframe(
                                    df=dados_download_heatmap,
                                    nome_planilha="Perfil horário",
                                )
                            )
                
                        except (
                            TypeError,
                            ValueError,
                            KeyError,
                        ) as erro_download_heatmap:
                            arquivo_heatmap_xlsx = None
                
                            st.warning(
                                "Não foi possível preparar o arquivo "
                                "do perfil horário."
                            )
                
                            st.caption(
                                str(
                                    erro_download_heatmap
                                )
                            )
                
                        # ====================================================
                        # CABEÇALHO DO HEATMAP
                        # ====================================================
                
                        (
                            coluna_titulo_heatmap,
                            coluna_tipo_heatmap,
                            coluna_download_heatmap,
                        ) = st.columns(
                            [
                                5,
                                1.15,
                                0.45,
                            ],
                            vertical_alignment="center",
                        )
                        
                        with coluna_titulo_heatmap:
                            st.html(
                                """
                                <div class="titulo-card-grafico">
                                    Perfil horário de curtailment
                                </div>
                                """
                            )
                
                        with coluna_tipo_heatmap:
                            tipo_heatmap_rotulo = st.selectbox(
                                "Tipo de curtailment do perfil horário",
                                options=[
                                    "Todos",
                                    "Energético",
                                    "Elétrico",
                                    "Confiabilidade",
                                ],
                                key="subsistemas_tipo_heatmap",
                                label_visibility="collapsed",
                            )
                
                        with coluna_download_heatmap:
                            with st.container(
                                key="download_heatmap",
                            ):
                                if arquivo_heatmap_xlsx is not None:
                                    nome_arquivo_heatmap = (
                                        "SINmulator_"
                                        "perfil_horario_"
                                        f"{filtros_subsistemas['ano_inicial']}-"
                                        f"{filtros_subsistemas['mes_inicial']:02d}_"
                                        f"{filtros_subsistemas['ano_final']}-"
                                        f"{filtros_subsistemas['mes_final']:02d}"
                                        ".xlsx"
                                    )
                
                                    st.download_button(
                                        label="Baixar",
                                        data=arquivo_heatmap_xlsx,
                                        file_name=nome_arquivo_heatmap,
                                        mime=(
                                            "application/vnd.openxmlformats-"
                                            "officedocument.spreadsheetml.sheet"
                                        ),
                                        help=(
                                            "Baixar o perfil horário médio "
                                            "por subsistema e tipo"
                                        ),
                                        key="botao_download_heatmap",
                                    )
                
                        tipo_heatmap_codigo = TIPOS_CURTAILMENT[
                            tipo_heatmap_rotulo
                        ]
                        # ========================================================
                        # PREPARAÇÃO DOS DADOS DO HEATMAP
                        # ========================================================
                        
                        try:
                            tabela_heatmap = (
                                preparar_perfil_horario_curtailment(
                                     df=df_curtailment_subsistemas,
                                    tipo_curtailment=(
                                        tipo_heatmap_codigo
                                    ),
                                )
                            )
                        
                        except (
                             TypeError,
                             ValueError,
                              KeyError,
                        ) as erro:
                             st.warning(
                                   "Não foi possível preparar o perfil horário "
                                   "de curtailment."
                             )
                        
                             st.caption(str(erro))
                        
                        # ========================================================
                        # RÓTULOS PARA EXIBIÇÃO
                        # ========================================================
                        
                        rotulos_heatmap_subsistemas = {
                            "N": "N",
                            "NE": "NE",
                            "SE": "SE",
                            "S": "S",
                        }
                        
                        tabela_heatmap_plot = tabela_heatmap.copy()
                        
                        tabela_heatmap_plot.index = [
                            rotulos_heatmap_subsistemas.get(
                                subsistema,
                                subsistema,
                            )
                            for subsistema in tabela_heatmap_plot.index]
                        
                        # ========================================================
                        # CONSTRUÇÃO DO HEATMAP
                        # ========================================================
                        
                        fig_heatmap = px.imshow(
                            tabela_heatmap_plot,
                            x=list(
                                range(24)
                            ),
                            y=tabela_heatmap_plot.index,
                            color_continuous_scale=[
                                [
                                    0.00,
                                    "#FFF7F9",
                                ],
                                [
                                    0.15,
                                    "#FCE1E8",
                                ],
                                [
                                    0.35,
                                    "#F7BAC9",
                                ],
                                [
                                    0.55,
                                    "#ED809B",
                                ],
                                [
                                    0.75,
                                    "#D94C70",
                                ],
                                [
                                    1.00,
                                    "#A61E4D",
                                ],
                            ],
                            aspect="auto",
                            labels={
                                "x": "Hora do dia",
                                "y": "",
                                "color": "MW médio",
                            },
                        )
                        
                        fig_heatmap.update_traces(
                            xgap=3,
                            ygap=5,
                            hovertemplate=(
                                "<b>%{y}</b>"
                                "<br>Hora: %{x}:00"
                                "<br>Curtailment médio: "
                                "%{z:,.2f} MW"
                                "<extra></extra>"
                            ),
                        )
                        
                        fig_heatmap.update_layout(
                            height=300,
                            margin={
                                "l": 5,
                                "r": 25,
                                "t": 20,
                                "b": 25,
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
                            coloraxis_colorbar={
                                "title": {
                                    "text": "MW médio",
                                    "side": "right",
                                },
                                "thickness": 13,
                                "len": 0.78,
                                "x": 1.01,
                                "tickfont": {
                                    "size": 10,
                                    "color": "#64748B",
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
                        )
                        
                        fig_heatmap.update_xaxes(
                            title="Hora do dia",
                            tickmode="linear",
                            dtick=1,
                            side="bottom",
                            showgrid=False,
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
                        
                        fig_heatmap.update_yaxes(
                            title=None,
                            showgrid=False,
                            showline=False,
                            tickfont={
                                "size": 13,
                                "color": "#334155",
                            },
                            autorange="reversed",
                            fixedrange=True,
                        )
                        
                        st.plotly_chart(
                            fig_heatmap,
                            width="stretch",
                            height=300,
                            config={
                                "displayModeBar": False,
                                "responsive": True,
                            },
                            key=(
                                "heatmap_subsistemas_"
                                f"{tipo_heatmap_codigo}"
                            ),
                        ) 
                        
                
                with coluna_direita_inferior:
                    with st.container(
                        border=True,
                        key="card_corte_subsistema",
                    ):
                        # ====================================================
                        # DADOS E DOWNLOAD DO GRÁFICO DE CORTE
                        # ====================================================
                
                        try:
                            tabela_corte_tipo = (
                                preparar_corte_subsistema_tipo(
                                    df_curtailment_subsistemas
                                )
                            )
                
                            tabela_download_corte = (
                                tabela_corte_tipo
                                .pivot_table(
                                    index=[
                                        "id_subsistema",
                                        "geracao_esperada_mwh",
                                    ],
                                    columns="tipo_curtailment",
                                    values="curtailment_mwh",
                                    aggfunc="sum",
                                    fill_value=0.0,
                                )
                                .reset_index()
                            )
                
                            for codigo in [
                                "ENE",
                                "REL",
                                "CNF",
                            ]:
                                if (
                                    codigo
                                    not in tabela_download_corte.columns
                                ):
                                    tabela_download_corte[
                                        codigo
                                    ] = 0.0
                
                            tabela_download_corte[
                                "Curtailment Todos (MWh)"
                            ] = (
                                tabela_download_corte["ENE"]
                                + tabela_download_corte["REL"]
                                + tabela_download_corte["CNF"]
                            )
                
                            mascara_geracao_positiva = (
                                tabela_download_corte[
                                    "geracao_esperada_mwh"
                                ] > 0
                            )
                
                            for codigo in [
                                "ENE",
                                "REL",
                                "CNF",
                            ]:
                                coluna_corte = (
                                    f"Corte {codigo} (%)"
                                )
                
                                tabela_download_corte[
                                    coluna_corte
                                ] = 0.0
                
                                tabela_download_corte.loc[
                                    mascara_geracao_positiva,
                                    coluna_corte,
                                ] = (
                                    100
                                    * tabela_download_corte.loc[
                                        mascara_geracao_positiva,
                                        codigo,
                                    ]
                                    / tabela_download_corte.loc[
                                        mascara_geracao_positiva,
                                        "geracao_esperada_mwh",
                                    ]
                                )
                
                            tabela_download_corte[
                                "Corte Todos (%)"
                            ] = 0.0
                
                            tabela_download_corte.loc[
                                mascara_geracao_positiva,
                                "Corte Todos (%)",
                            ] = (
                                100
                                * tabela_download_corte.loc[
                                    mascara_geracao_positiva,
                                    "Curtailment Todos (MWh)",
                                ]
                                / tabela_download_corte.loc[
                                    mascara_geracao_positiva,
                                    "geracao_esperada_mwh",
                                ]
                            )
                
                            dados_download_corte = (
                                tabela_download_corte
                                .rename(
                                    columns={
                                        "id_subsistema": (
                                            "Subsistema"
                                        ),
                                        "geracao_esperada_mwh": (
                                            "Geração Esperada (MWh)"
                                        ),
                                        "ENE": (
                                            "Curtailment ENE (MWh)"
                                        ),
                                        "REL": (
                                            "Curtailment REL (MWh)"
                                        ),
                                        "CNF": (
                                            "Curtailment CNF (MWh)"
                                        ),
                                    }
                                )
                            )
                
                            dados_download_corte = (
                                dados_download_corte[
                                    [
                                        "Subsistema",
                                        "Curtailment ENE (MWh)",
                                        "Curtailment REL (MWh)",
                                        "Curtailment CNF (MWh)",
                                        "Curtailment Todos (MWh)",
                                        "Geração Esperada (MWh)",
                                        "Corte ENE (%)",
                                        "Corte REL (%)",
                                        "Corte CNF (%)",
                                        "Corte Todos (%)",
                                    ]
                                ]
                            )
                
                            ordem_download_subsistemas = {
                                "N": 1,
                                "NE": 2,
                                "SE": 3,
                                "S": 4,
                            }
                
                            dados_download_corte[
                                "ordem_subsistema"
                            ] = (
                                dados_download_corte[
                                    "Subsistema"
                                ]
                                .map(
                                    ordem_download_subsistemas
                                )
                                .fillna(99)
                            )
                
                            dados_download_corte = (
                                dados_download_corte
                                .sort_values(
                                    "ordem_subsistema"
                                )
                                .drop(
                                    columns="ordem_subsistema"
                                )
                                .reset_index(
                                    drop=True
                                )
                            )
                
                            arquivo_corte_xlsx = (
                                gerar_excel_dataframe(
                                    df=dados_download_corte,
                                    nome_planilha=(
                                        "Corte por subsistema"
                                    ),
                                )
                            )
                
                        except (
                            TypeError,
                            ValueError,
                            KeyError,
                        ) as erro:
                            arquivo_corte_xlsx = None
                
                            tabela_corte_tipo = pd.DataFrame(
                                columns=[
                                    "id_subsistema",
                                    "tipo_curtailment",
                                    "tipo_rotulo",
                                    "curtailment_mwh",
                                    "geracao_esperada_mwh",
                                    "corte_pct",
                                ]
                            )
                
                            st.warning(
                                "Não foi possível preparar o corte "
                                "por subsistema e tipo."
                            )
                
                            st.caption(
                                str(erro)
                            )
                
                        # ====================================================
                        # CABEÇALHO E DOWNLOAD
                        # ====================================================
                
                        (
                            coluna_titulo_corte,
                            coluna_download_corte,
                        ) = st.columns(
                            [
                                5,
                                0.45,
                            ],
                            vertical_alignment="center",
                        )
                
                        with coluna_titulo_corte:
                            st.html(
                                """
                                <div class="titulo-card-grafico">
                                    Corte por subsistema e tipo
                                </div>
                                """
                            )
                
                        with coluna_download_corte:
                            with st.container(
                                key="download_corte",
                            ):
                                if arquivo_corte_xlsx is not None:
                                    nome_arquivo_corte = (
                                        "SINmulator_"
                                        "corte_por_subsistema_"
                                        f"{filtros_subsistemas['ano_inicial']}-"
                                        f"{filtros_subsistemas['mes_inicial']:02d}_"
                                        f"{filtros_subsistemas['ano_final']}-"
                                        f"{filtros_subsistemas['mes_final']:02d}"
                                        ".xlsx"
                                    )
                
                                    st.download_button(
                                        label="Baixar",
                                        data=arquivo_corte_xlsx,
                                        file_name=nome_arquivo_corte,
                                        mime=(
                                            "application/vnd.openxmlformats-"
                                            "officedocument.spreadsheetml.sheet"
                                        ),
                                        help=(
                                            "Baixar os dados de corte por "
                                            "subsistema e tipo"
                                        ),
                                        key="botao_download_corte",
                                    )

                        # ====================================================
                        # CONSTRUÇÃO DO GRÁFICO
                        # ====================================================

                        cores_tipos = {
                            "Energético": "#E57373",
                            "Elétrico": "#F5A65B",
                            "Confiabilidade": "#A58ACB",
                        }
                
                        ordem_tipos = [
                            "Energético",
                            "Elétrico",
                            "Confiabilidade",
                        ]
                
                        fig_corte_tipo = px.bar(
                            tabela_corte_tipo,
                            y="id_subsistema",
                            x="corte_pct",
                            color="tipo_rotulo",
                            orientation="h",
                            barmode="stack",
                            category_orders={
                                "id_subsistema": [
                                    "N",
                                    "NE",
                                    "SE",
                                    "S",
                                ],
                                "tipo_rotulo": ordem_tipos,
                            },
                            color_discrete_map=cores_tipos,
                            labels={
                                "id_subsistema": "",
                                "corte_pct": "Corte (%)",
                                "tipo_rotulo": "Tipo",
                            },
                            custom_data=[
                                "tipo_rotulo",
                                "curtailment_mwh",
                            ],
                        )
                        fig_corte_tipo.update_traces(
                            marker_line_color="#FFFFFF",
                            marker_line_width=0.7,
                            hovertemplate=(
                                "<b>Subsistema %{y}</b>"
                                "<br>Tipo: %{customdata[0]}"
                                "<br>Corte: %{x:.2f}%"
                                "<br>Curtailment: "
                                "%{customdata[1]:,.2f} MWh"
                                "<extra></extra>"
                            ),
                        )
                        
                        fig_corte_tipo.update_layout(
                            height=300,
                            margin={
                                "l": 5,
                                "r": 15,
                                "t": 55,
                                "b": 15,
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
                            bargap=0.32,
                        )
                        
                        fig_corte_tipo.update_xaxes(
                            title="Corte (%)",
                            ticksuffix="%",
                            gridcolor="rgba(148, 163, 184, 0.20)",
                            griddash="dot",
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
                        
                        fig_corte_tipo.update_yaxes(
                            title=None,
                            autorange="reversed",
                            showgrid=False,
                            showline=False,
                            tickfont={
                                "size": 12,
                                "color": "#334155",
                            },
                            fixedrange=True,
                        )
                        
                        st.plotly_chart(
                            fig_corte_tipo,
                            width="stretch",
                            height=290,
                            config={
                                "displayModeBar": False,
                                "responsive": True,
                            },
                            key="grafico_corte_subsistema_tipo",
                        )
    
    # ============================================================
    # RESUMO POR SUBSISTEMA
    # ============================================================
    
    try:
        tabela_resumo_subsistemas = (
            preparar_resumo_subsistemas_aplicacao(
                df_curtailment_subsistemas
            )
        )
    
    except (
        TypeError,
        ValueError,
        KeyError,
    ) as erro:
        st.warning(
            "Não foi possível preparar a tabela de resumo "
            "por subsistema."
        )
    
        st.caption(
            str(erro)
        )
    
        tabela_resumo_subsistemas = pd.DataFrame()
        
    arquivo_resumo_xlsx = None

    if not tabela_resumo_subsistemas.empty:
        dados_download_resumo = (tabela_resumo_subsistemas.copy())
    
        arquivo_resumo_xlsx = (gerar_excel_dataframe(df=dados_download_resumo,nome_planilha=("Resumo por subsistema")))
    
    with st.container(
        border=True,
        key="card_tabela_subsistemas",
    ):
        (coluna_titulo_resumo,coluna_download_resumo) = st.columns([8,0.45],vertical_alignment="center")

        # =======================================
        # TÍTULO DO CARD DE RESUMO
        # =======================================
        with coluna_titulo_resumo:
            st.html(
                """
                <div class="titulo-card-grafico">
                    Resumo por subsistema
                </div>
                """
            )
        # =======================================
        # BOTÃO DE DOWNLOAD DA TABELA DE RESUMO
        # =======================================
        with coluna_download_resumo:
            with st.container(
                key="download_resumo",
            ):
                if arquivo_resumo_xlsx is not None:
                    nome_arquivo_resumo = (
                        "SINmulator_"
                        "resumo_subsistemas_"
                        f"{filtros_subsistemas['ano_inicial']}-"
                        f"{filtros_subsistemas['mes_inicial']:02d}_"
                        f"{filtros_subsistemas['ano_final']}-"
                        f"{filtros_subsistemas['mes_final']:02d}"
                        ".xlsx"
                    )
        
                    st.download_button(
                        label="Baixar",
                        data=arquivo_resumo_xlsx,
                        file_name=nome_arquivo_resumo,
                        mime=(
                            "application/vnd.openxmlformats-"
                            "officedocument.spreadsheetml.sheet"
                        ),
                        help=(
                            "Baixar a tabela de resumo por "
                            "subsistema"
                        ),
                        key="botao_download_resumo",
                    )
    
        if tabela_resumo_subsistemas.empty:
            st.info("Não há dados disponíveis para a tabela de resumo.")
    
        else:
            tabela_exibicao = (tabela_resumo_subsistemas.copy())
    
            tabela_exibicao[
                "Curtailment (GWh)"
            ] = tabela_exibicao[
                "Curtailment (GWh)"
            ].map(
                lambda valor: (
                    formatar_numero_brasileiro(
                        valor,
                        casas_decimais=1,
                    )
                )
            )
    
            tabela_exibicao[
                "Geração Esperada (GWh)"
            ] = tabela_exibicao[
                "Geração Esperada (GWh)"
            ].map(
                lambda valor: (
                    formatar_numero_brasileiro(
                        valor,
                        casas_decimais=1,
                    )
                )
            )
    
            tabela_exibicao[
                "Corte (%)"
            ] = tabela_exibicao[
                "Corte (%)"
            ].map(
                lambda valor: (
                    (
                        formatar_numero_brasileiro(
                            valor,
                            casas_decimais=2,
                        )
                        + "%"
                    )
                    if pd.notna(valor)
                    else "—"
                )
            )
    
            tabela_exibicao[
                "Participação (%)"
            ] = tabela_exibicao[
                "Participação (%)"
            ].map(
                lambda valor: (
                    (
                        formatar_numero_brasileiro(
                            valor,
                            casas_decimais=2,
                        )
                        + "%"
                    )
                    if pd.notna(valor)
                    else "—"
                )
            )
    
            cores_subsistemas_tabela = {
                "N": "#F3A6B8",
                "NE": "#5F8FB5",
                "SE": "#68BDB7",
                "S": "#9B8AC4",
            }
            
            linhas_tabela = []
            
            for _, linha in tabela_exibicao.iterrows():
                subsistema = str(
                    linha["Subsistema"]
                )
            
                cor_subsistema = (
                    cores_subsistemas_tabela.get(
                        subsistema,
                        "#94A3B8",
                    )
                )
            
                linhas_tabela.append(
                    (
                        "<tr>"
                        "<td>"
                        '<div class="subsistema-tabela">'
                        '<span class="subsistema-cor" '
                        f'style="background-color:{cor_subsistema};">'
                        "</span>"
                        f"<span>{subsistema}</span>"
                        "</div>"
                        "</td>"
                        f'<td class="numero-tabela">'
                        f'{linha["Curtailment (GWh)"]}'
                        "</td>"
                        f'<td class="numero-tabela">'
                        f'{linha["Geração Esperada (GWh)"]}'
                        "</td>"
                        f'<td class="numero-tabela">'
                        f'{linha["Corte (%)"]}'
                        "</td>"
                        f'<td class="numero-tabela">'
                        f'{linha["Participação (%)"]}'
                        "</td>"
                        f"<td>{linha['Tipo Predominante']}</td>"
                        f"<td>{linha['Mês Crítico']}</td>"
                        f"<td>{linha['Hora Crítica']}</td>"
                        "</tr>"
                    )
                )
            
            html_tabela_resumo = (
                '<div class="tabela-resumo-wrapper">'
                '<table class="tabela-resumo-subsistemas">'
                "<thead>"
                "<tr>"
                "<th>Subsistema</th>"
                "<th>Curtailment (GWh)</th>"
                "<th>Geração esperada (GWh)</th>"
                "<th>Corte (%)</th>"
                "<th>Participação (%)</th>"
                "<th>Tipo predominante</th>"
                "<th>Mês crítico</th>"
                "<th>Hora crítica</th>"
                "</tr>"
                "</thead>"
                "<tbody>"
                + "".join(
                    linhas_tabela
                )
                + "</tbody>"
                "</table>"
                "</div>"
            )
            
            st.html(
                html_tabela_resumo
            )

    # ============================================================
    # EXPORTAÇÃO DA ANÁLISE DETALHADA
    # ============================================================
    
    with st.container(
        border=True,
        key="card_exportacao_subsistemas",
    ):
        (coluna_texto_exportacao,coluna_granularidade,coluna_download_detalhado) = st.columns([5,1.8,0.45],vertical_alignment="center")
    
        with coluna_texto_exportacao:
            st.html(
                """
                <div class="cabecalho-exportacao-subsistemas">
                    <div class="titulo-card-grafico">
                        Exportar análise detalhada
                    </div>
    
                    <div class="subtitulo-exportacao-subsistemas">
                        Curtailment por tipo, geração esperada
                        e corte percentual, sempre divididos
                        por subsistema.
                    </div>
                </div>
                """
            )
    
        with coluna_granularidade:
            granularidade_rotulo = st.selectbox(
                "Granularidade",
                options=list(
                    GRANULARIDADES_EXPORTACAO.keys()
                ),
                index=0,
                key="granularidade_exportacao_subsistemas",
            )
    
        granularidade_codigo = (GRANULARIDADES_EXPORTACAO[granularidade_rotulo])
    
        arquivo_exportacao_xlsx = None
    
        try:
            dados_exportacao_subsistemas = (
                preparar_exportacao_subsistemas_aplicacao(
                    df_curtailment=(df_curtailment_subsistemas),
                    granularidade=(granularidade_codigo)
                )
            )
    
            nome_planilha_exportacao = {
                "DIA_HORA": "Dia e hora",
                "MES_HORA": "Mês e hora",
                "ANO_HORA": "Ano e hora",
                "DIA": "Dia",
                "MES": "Mês",
                "ANO": "Ano",
            }[granularidade_codigo]
    
            arquivo_exportacao_xlsx = (
                gerar_excel_dataframe(
                    df=dados_exportacao_subsistemas,
                    nome_planilha=(
                        nome_planilha_exportacao
                    ),
                )
            )
    
        except (
            TypeError,
            ValueError,
            KeyError,
        ) as erro_exportacao:
            st.warning("Não foi possível preparar a análise detalhada para download.")
    
            st.caption(str(erro_exportacao))
    
        with coluna_download_detalhado:
            with st.container(
                key="download_detalhado",
            ):
                if arquivo_exportacao_xlsx is not None:
                    nome_granularidade_arquivo = (granularidade_codigo.lower())
    
                    nome_arquivo_exportacao = (
                        "SINmulator_"
                        "analise_subsistemas_"
                        f"{nome_granularidade_arquivo}_"
                        f"{filtros_subsistemas['ano_inicial']}-"
                        f"{filtros_subsistemas['mes_inicial']:02d}_"
                        f"{filtros_subsistemas['ano_final']}-"
                        f"{filtros_subsistemas['mes_final']:02d}"
                        ".xlsx"
                    )
    
                    st.download_button(
                        label="Baixar",
                        data=arquivo_exportacao_xlsx,
                        file_name=(nome_arquivo_exportacao),
                        mime=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                        help=("Baixar a análise detalhada por subsistema na granularidade selecionada"),
                        key="botao_download_detalhado"
                    )

def renderizar_pagina_ativos_elera(
    hoje,
    ultimo_ano_completo,
    ultimo_mes_completo
):
    
    """
    Renderiza a página provisória da aba Ativos Elera.
    """

    try:
        (
            filtros_aplicados,
            status_ativos_elera,
            resumo_ativos_elera,
        ) = renderizar_filtros_ativos_elera(
            ultimo_ano_completo=(
                ultimo_ano_completo
            ),
            ultimo_mes_completo=(
                ultimo_mes_completo
            ),
        )

    except ValueError as erro:
        st.error(str(erro))

        return
    #==========================================
    # CABEÇALHO
    #==========================================
    st.html(
        """
        <div class="cabecalho-ativos-elera">
                <h1>Ativos Elera</h1>
        </div>
        """
    )
    
    #==========================================
    # FILTROS APLICADOS
    #==========================================
    
    if filtros_aplicados is not None:
        st.session_state["filtros_ativos_elera"] = filtros_aplicados
        st.session_state["processar_ativos_elera"] = True
        
    filtros_ativos_elera = (st.session_state.get("filtros_ativos_elera"))
    if filtros_ativos_elera is None:
        return
    
    #==========================================
    # PROCESSAMENTO
    #==========================================
    
    if st.session_state.get("processar_ativos_elera",False):
        competencia_inicial = formatar_competencia(
            ano=filtros_ativos_elera["ano_inicial"],
            mes=filtros_ativos_elera["mes_inicial"],
        )

        competencia_final = formatar_competencia(
            ano=filtros_ativos_elera["ano_final"],
            mes=filtros_ativos_elera["mes_final"],
        )

        mensagem_processamento = (
            "Coletando e processando os dados de "
            f"{competencia_inicial} a {competencia_final}. "
            "A primeira execução pode levar alguns minutos."
        )

        try:
            with status_ativos_elera.container():
                with st.spinner(mensagem_processamento):
                    dados_ativos_elera = (
                        executar_pipeline_aplicacao(
                            ano_inicial=(filtros_ativos_elera["ano_inicial"]),
                            mes_inicial=(filtros_ativos_elera["mes_inicial"]),
                            ano_final=(filtros_ativos_elera["ano_final"]),
                            mes_final=(filtros_ativos_elera["mes_final"]),
                            fontes=tuple(filtros_ativos_elera["fontes"]),
                            data_referencia=hoje,
                            timeout=TIMEOUT_PIPELINE,
                        )
                    )

            st.session_state["dados_ativos_elera"] = dados_ativos_elera

            st.session_state["periodo_processado_ativos_elera"] = filtros_ativos_elera.copy()

            st.session_state["processar_ativos_elera"] = False

            status_ativos_elera.empty()

            st.toast("Dados dos ativos Elera processados com sucesso.",icon="✅")

        except Exception as erro:
            st.session_state["processar_ativos_elera"] = False

            status_ativos_elera.error("Não foi possível processar os dados dos ativos da Elera.")

            st.exception(erro)

            return

    #==============================================
    # RECUPERAÇÃO DOS DADOS PROCESSADOS
    #==============================================
    
    dados_ativos_elera = st.session_state.get("dados_ativos_elera")
    periodo_processado = st.session_state.get("periodo_processado_ativos_elera")

    if (dados_ativos_elera is None or periodo_processado is None):
        return

    df_curtailment_ativos_elera = (dados_ativos_elera["df_curtailment"])
    
    #=====================================
    # CÁLCULO DOS KPIs
    #=====================================
    
    try:
        kpis_ativos_elera = (calcular_kpis_ativos_elera_aplicacao(df_curtailment_ativos_elera))

    except (TypeError,ValueError,KeyError) as erro:
        st.error("Não foi possível calcular os indicadores dos ativos da Elera.")

        st.exception(erro)

        return

    # ============================================================
    # FORMATAÇÃO DOS KPIs
    # ============================================================
    
    geracao_esperada_elera = (formatar_numero_brasileiro(kpis_ativos_elera["Geração Esperada (GWh)"],casas_decimais=2))
    
    curtailment_elera = (formatar_numero_brasileiro(kpis_ativos_elera["Curtailment (GWh)"],casas_decimais=2))
    
    corte_medio_elera = (formatar_numero_brasileiro(kpis_ativos_elera["Corte Médio (%)"],casas_decimais=2))
    
    usina_mais_cortada = (kpis_ativos_elera["Usina Mais Cortada"])
    
    fonte_usina_mais_cortada = (kpis_ativos_elera["Fonte da Usina Mais Cortada"])
    
    corte_usina_mais_cortada = (formatar_numero_brasileiro(kpis_ativos_elera["Corte da Usina Mais Cortada (%)"],casas_decimais=2))
    
    curtailment_usina_mais_cortada = (formatar_numero_brasileiro(kpis_ativos_elera["Curtailment da Usina Mais Cortada (GWh)"],casas_decimais=2))

    # ============================================================
    # CARDS DOS KPIs
    # ============================================================
    
    html_kpis_ativos_elera = (
        '<div class="kpis-ativos-elera">'
    
        # Geração esperada
        '<div class="kpi-elera-card">'
        '<div class="kpi-elera-icone kpi-elera-icone-geracao">'
        '<span class="kpi-elera-simbolo" aria-hidden="true">'
        '&#9889;&#65038;'
        '</span>'
        '</div>'
        '<div class="kpi-elera-conteudo">'
        '<div class="kpi-elera-titulo">'
        'Geração esperada'
        '</div>'
        '<div class="kpi-elera-valor">'
        f'{geracao_esperada_elera} GWh'
        '</div>'
        '<div class="kpi-elera-detalhe">'
        'Produção potencial dos sete ativos'
        '</div>'
        '</div>'
        '</div>'
    
        # Curtailment
        '<div class="kpi-elera-card">'
        '<div class="kpi-elera-icone kpi-elera-icone-curtailment">'
        '<span class="kpi-elera-simbolo" aria-hidden="true">'
        '&#9888;'
        '</span>'
        '</div>'
        '<div class="kpi-elera-conteudo">'
        '<div class="kpi-elera-titulo">'
        'Curtailment'
        '</div>'
        '<div class="kpi-elera-valor">'
        f'{curtailment_elera} GWh'
        '</div>'
        '<div class="kpi-elera-detalhe">'
        'Energia restringida no período'
        '</div>'
        '</div>'
        '</div>'
    
        # Corte médio
        '<div class="kpi-elera-card">'
        '<div class="kpi-elera-icone kpi-elera-icone-corte">'
        '<span class="kpi-elera-simbolo" aria-hidden="true">'
        '%'
        '</span>'
        '</div>'
        '<div class="kpi-elera-conteudo">'
        '<div class="kpi-elera-titulo">'
        'Corte médio'
        '</div>'
        '<div class="kpi-elera-valor">'
        f'{corte_medio_elera}%'
        '</div>'
        '<div class="kpi-elera-detalhe">'
        'Curtailment sobre a geração esperada'
        '</div>'
        '</div>'
        '</div>'
    
        # Usina mais cortada
        '<div class="kpi-elera-card">'
        '<div class="kpi-elera-icone kpi-elera-icone-usina">'
        '<span class="kpi-elera-simbolo" aria-hidden="true">'
        '&#9678;'
        '</span>'
        '</div>'
        '<div class="kpi-elera-conteudo">'
        '<div class="kpi-elera-titulo">'
        'Usina mais cortada'
        '</div>'
        '<div class="kpi-elera-valor">'
        f'{usina_mais_cortada}'
        '</div>'
        '<div class="kpi-elera-detalhe">'
        f'{corte_usina_mais_cortada}% de corte'
        f' | {curtailment_usina_mais_cortada} GWh'
        f' | {fonte_usina_mais_cortada}'
        '</div>'
        '</div>'
        '</div>'
    
        '</div>'
    )
    
    st.html(html_kpis_ativos_elera)
    # ============================================================
    # BASES DOS GRÁFICOS DO PORTFÓLIO
    # ============================================================
    
    try:
        base_mensal_curtailment_elera = (preparar_curtailment_mensal_elera_aplicacao(df_curtailment_ativos_elera))
        base_participacao_curtailment_elera = (preparar_participacao_curtailment_elera_aplicacao(df_curtailment_ativos_elera))
        base_mensal_geracao_elera = (preparar_geracao_mensal_elera_aplicacao(df_curtailment_ativos_elera))
        base_participacao_geracao_elera = (preparar_participacao_geracao_elera_aplicacao(df_curtailment_ativos_elera))
    
    except (TypeError,ValueError,KeyError) as erro:
        st.error("Não foi possível preparar os gráficos do portfólio Elera.")
        st.exception(erro)
        return

    # ============================================================
    # PALETAS DOS GRÁFICOS
    # ============================================================
    
    cores_fontes_elera = {
        "Solar": "#FF7538",
        "Eólica": "#318CE7",
    }
    
    cores_tipos_elera = {
        "Energético": "#E57373",
        "Elétrico": "#F5A65B",
        "Confiabilidade": "#A58ACB",
    }
    cor_geracao_esperada_elera = "#034694"
    # ============================================================
    # GRÁFICOS MENSAIS E PARTICIPAÇÃO
    # ============================================================
    
    with st.container(key="graficos_portfolio_elera"):
        (
            coluna_mensal_elera,
            coluna_participacao_elera,
        ) = st.columns(
            [
                1.75,
                1,
            ],
            gap="medium",
            vertical_alignment="top",
        )
    
        with coluna_mensal_elera:
            with st.container(
                border=True,
                key="card_mensal_elera",
            ):
                # =================================================
                # CABEÇALHO E SELETOR
                # =================================================
    
                (coluna_titulo_mensal,coluna_seletor_mensal,coluna_download_portfolio) = st.columns([2.7,2.1,0.35],vertical_alignment="center")
                
                with coluna_titulo_mensal:
                    st.html(
                        """
                        <div class="titulo-card-grafico">
                            Mensal do portfólio
                        </div>
                        """
                    )
    
                with coluna_seletor_mensal:
                    metrica_elera = st.segmented_control(
                        "Métrica dos gráficos",
                        options=[
                            "Curtailment",
                            "Geração esperada",
                        ],
                        default="Curtailment",
                        key="metrica_portfolio_elera",
                        label_visibility="collapsed",
                        selection_mode="single",
                    )
    
                if metrica_elera is None:
                    metrica_elera = "Curtailment"
    
                # =================================================
                # GRÁFICO DE CURTAILMENT
                # =================================================
    
                if metrica_elera == "Curtailment":
                    ordem_meses_elera = (
                        base_mensal_curtailment_elera[["mes","mes_rotulo"]]
                        .drop_duplicates()
                        .sort_values("mes")["mes_rotulo"]
                        .tolist()
                    )
    
                    ordem_tipos_elera = [
                        "Energético",
                        "Elétrico",
                        "Confiabilidade",
                    ]
    
                    fig_mensal_elera = px.bar(
                        base_mensal_curtailment_elera,
                        x="mes_rotulo",
                        y="curtailment_gwh",
                        color="tipo_rotulo",
                        barmode="stack",
                        category_orders={
                            "mes_rotulo": ordem_meses_elera,
                            "tipo_rotulo": ordem_tipos_elera,
                        },
                        color_discrete_map=(cores_tipos_elera),
                        labels={
                            "mes_rotulo": "Mês",
                            "curtailment_gwh": ("Curtailment (GWh)"),
                            "tipo_rotulo": ("Tipo de curtailment"),
                        },
                        custom_data=["tipo_rotulo","tipo_curtailment"],
                    )
    
                    fig_mensal_elera.update_traces(
                        marker_line_color=("rgba(255,255,255,0.75)"),
                        marker_line_width=0.5,
                        hovertemplate=(
                            "<b>%{customdata[0]}</b>"
                            "<br>Código: %{customdata[1]}"
                            "<br>Mês: %{x}"
                            "<br>Curtailment: %{y:,.2f} GWh"
                            "<extra></extra>"
                        ),
                    )
    
                    titulo_eixo_y = ("Curtailment (GWh)")
                    mostrar_legenda = True
                    base_download_portfolio_elera = (
                        base_mensal_curtailment_elera[
                            [
                                "mes",
                                "mes_rotulo",
                                "tipo_curtailment",
                                "tipo_rotulo",
                                "curtailment_gwh",
                            ]
                        ]
                        .copy()
                        .rename(
                            columns={"mes": "Mês",
                                     "mes_rotulo": "Competência",
                                     "tipo_curtailment": ("Código do curtailment"),
                                     "tipo_rotulo": ("Tipo de curtailment"),
                                     "curtailment_gwh": ("Curtailment (GWh)")
                            }
                        )
                    )
                    
                    nome_planilha_portfolio_elera = ("Curtailment mensal")
                    nome_metrica_arquivo_portfolio = ("curtailment")
    
                # =================================================
                # GRÁFICO DE GERAÇÃO ESPERADA
                # =================================================
    
                else:
                    ordem_meses_elera = (
                        base_mensal_geracao_elera[["mes","mes_rotulo"]]
                        .drop_duplicates()
                        .sort_values("mes")["mes_rotulo"]
                        .tolist()
                    )
    
                    fig_mensal_elera = px.bar(
                        base_mensal_geracao_elera,
                        x="mes_rotulo",
                        y="geracao_esperada_gwh",
                        category_orders={
                            "mes_rotulo": ordem_meses_elera,
                        },
                        labels={
                            "mes_rotulo": "Mês",
                            "geracao_esperada_gwh": (
                                "Geração esperada (GWh)"
                            ),
                        },
                    )
    
                    fig_mensal_elera.update_traces(
                        marker_color=cor_geracao_esperada_elera,
                        marker_line_color=(
                            "rgba(255,255,255,0.75)"
                        ),
                        marker_line_width=0.5,
                        hovertemplate=(
                            "<b>Geração esperada</b>"
                            "<br>Mês: %{x}"
                            "<br>Geração esperada: "
                            "%{y:,.2f} GWh"
                            "<extra></extra>"
                        ),
                    )
    
                    titulo_eixo_y = ("Geração esperada (GWh)")
                    mostrar_legenda = False
                    base_download_portfolio_elera = (
                        base_mensal_geracao_elera[["mes","mes_rotulo","geracao_esperada_gwh"]]
                        .copy()
                        .rename(
                            columns={
                                "mes": "Mês",
                                "mes_rotulo": "Competência",
                                "geracao_esperada_gwh": ("Geração esperada (GWh)")
                            }
                        )
                    )
                    
                    nome_planilha_portfolio_elera = ("Geração mensal")
                    nome_metrica_arquivo_portfolio = ("geracao_esperada")

                # =================================================
                # DOWNLOAD PORTFOLIO
                # =================================================
                arquivo_download_portfolio_elera = (
                    gerar_excel_dataframe(
                        df=base_download_portfolio_elera,
                        nome_planilha=(nome_planilha_portfolio_elera)
                    )
                )
                
                periodo_inicial_arquivo = (
                    f"{periodo_processado['ano_inicial']}-"
                    f"{periodo_processado['mes_inicial']:02d}"
                )
                
                periodo_final_arquivo = (
                    f"{periodo_processado['ano_final']}-"
                    f"{periodo_processado['mes_final']:02d}"
                )
                
                nome_arquivo_portfolio_elera = (
                    "SINmulator_"
                    "portfolio_elera_"
                    f"{nome_metrica_arquivo_portfolio}_"
                    f"{periodo_inicial_arquivo}_"
                    f"{periodo_final_arquivo}"
                    ".xlsx"
                )
                with coluna_download_portfolio:
                    with st.container(key="download_portfolio_elera"):
                        st.download_button(
                            label="Baixar",
                            data=arquivo_download_portfolio_elera,
                            file_name=(nome_arquivo_portfolio_elera),
                            mime=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                            help=("Baixar os dados exibidos no gráfico mensal do portfólio"),
                            key=(f"botao_download_portfolio_elera_{metrica_elera}")
                        )
                                
                # =================================================
                # FORMATAÇÃO COMPARTILHADA
                # =================================================
    
                fig_mensal_elera.update_layout(
                    height=345,
                    margin={
                        "l": 10,
                        "r": 10,
                        "t": (
                            55
                            if mostrar_legenda
                            else 25
                        ),
                        "b": 15,
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
                            "size": 12,
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
                    bargap=0.25,
                )
    
                fig_mensal_elera.update_xaxes(
                    title=None,
                    showgrid=False,
                    showline=False,
                    tickfont={
                        "size": 11,
                        "color": "#64748B",
                    },
                    fixedrange=True,
                )
    
                fig_mensal_elera.update_yaxes(
                    title=titulo_eixo_y,
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
                    tickformat=",.0f",
                    fixedrange=True,
                )
    
                st.plotly_chart(
                    fig_mensal_elera,
                    width="stretch",
                    height=345,
                    config={
                        "displayModeBar": False,
                        "responsive": True,
                    },
                    key=(
                        "grafico_mensal_elera_"
                        f"{metrica_elera}"
                    ),
                )
            
        with coluna_participacao_elera:
            with st.container(border=True,key="card_participacao_elera"):
                if metrica_elera == "Curtailment":
                    titulo_participacao_elera = ("Participação no curtailment por ativo")
                    base_participacao_elera = (base_participacao_curtailment_elera.copy())
                    coluna_valor_participacao = ("curtailment_gwh")
                    rotulo_valor_participacao = ("Curtailment")
    
                else:
                    titulo_participacao_elera = ("Participação na geração por ativo")
                    base_participacao_elera = (base_participacao_geracao_elera.copy())
                    coluna_valor_participacao = ("geracao_esperada_gwh")
                    rotulo_valor_participacao = ("Geração esperada")
    
                st.html(
                    ('<div class="titulo-card-grafico">'
                     f'{titulo_participacao_elera}'
                     '</div>')
                )
    
                ordem_ativos_participacao = (base_participacao_elera["ativo_elera"].tolist())
    
                fig_participacao_elera = px.bar(
                    base_participacao_elera,
                    x="participacao_pct",
                    y="ativo_elera",
                    color="fonte_elera",
                    orientation="h",
                    category_orders={"ativo_elera": (ordem_ativos_participacao),"fonte_elera": ["Solar","Eólica",]},
                    color_discrete_map=(cores_fontes_elera),
                    labels={"participacao_pct": ("Participação (%)"),"ativo_elera": "","fonte_elera": "Fonte"},
                    custom_data=["fonte_elera",coluna_valor_participacao],
                    text="participacao_pct"
                )
    
                fig_participacao_elera.update_traces(
                    texttemplate="%{x:.1f}%",
                    textposition="outside",
                    cliponaxis=False,
                    marker_line_color="#FFFFFF",
                    marker_line_width=0.5,
                    hovertemplate=(
                        "<b>%{y}</b>"
                        "<br>Fonte: %{customdata[0]}"
                        "<br>Participação: %{x:.2f}%"
                        f"<br>{rotulo_valor_participacao}: "
                        "%{customdata[1]:,.2f} GWh"
                        "<extra></extra>")
                )

                maior_participacao = (base_participacao_elera["participacao_pct"].max())

                limite_eixo_participacao = max(maior_participacao * 1.18,10.0)
    
                fig_participacao_elera.update_layout(
                    height=345,
                    margin={
                        "l": 5,
                        "r": 45,
                        "t": 50,
                        "b": 15,
                    },
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font={"family": ("Segoe UI, Arial, sans-serif"),"color": "#334155","size": 12,},
                    legend={
                        "title": {"text": ""},
                        "orientation": "h",
                        "yanchor": "bottom",
                        "y": 1.03,
                        "xanchor": "center",
                        "x": 0.5,
                        "font": {"size": 11,"color": "#334155",}},
                    hoverlabel={"bgcolor": "#FFFFFF","bordercolor": "#D9E2EC","font": {"color": "#102D57","size": 12}},
                    bargap=0.28,
                )
    
                fig_participacao_elera.update_xaxes(
                    title="Participação (%)",
                    range=[0,limite_eixo_participacao],
                    ticksuffix="%",
                    gridcolor=("rgba(148, 163, 184, 0.20)"),
                    zeroline=False,
                    showline=False,
                    tickfont={"size": 10,"color": "#64748B"},
                    title_font={"size": 11,"color": "#475569"},
                    fixedrange=True,
                )
    
                fig_participacao_elera.update_yaxes(
                    title=None,
                    autorange="reversed",
                    showgrid=False,
                    showline=False,
                    tickfont={"size": 11,"color": "#334155"},
                    fixedrange=True,
                )
    
                st.plotly_chart(
                    fig_participacao_elera,
                    width="stretch",
                    height=345,
                    config={"displayModeBar": False,"responsive": True},
                    key=(f"grafico_participacao_elera_{metrica_elera}"),
                )

    # ============================================================
    # ANÁLISE INDIVIDUAL POR ATIVO
    # ============================================================
    
    st.html(
        """
        <div class="titulo-secao-elera">
            Análise por ativo
        </div>
        """
    )
    
    rotulos_ativos_elera = {
        "Janaúba": "☀ Janaúba",
        "Alex": "☀ Alex",
        "Alto Sertão": "≈ Alto Sertão",
        "Renascença": "≈ Renascença",
        "Pontal": "≈ Pontal",
        "Seridó": "≈ Seridó",
        "Faísa": "≈ Faísa",
    }
    
    with st.container(key="seletor_ativo_elera"):
        ativo_selecionado_elera = st.pills(
            "Selecione o ativo",
            options=ORDEM_ATIVOS_ELERA,
            default="Janaúba",
            selection_mode="single",
            required=True,
            format_func=lambda ativo: (
                rotulos_ativos_elera.get(
                    ativo,
                    ativo,
                )
            ),
            key="ativo_individual_elera",
            label_visibility="collapsed",
            width="stretch",
            wrap=True,
        )
    try:
        analise_ativo_elera = (
            preparar_analise_individual_elera_aplicacao(
                df_curtailment=(
                    df_curtailment_ativos_elera
                ),
                ativo_selecionado=(
                    ativo_selecionado_elera
                ),
            )
        )
    
    except (
        TypeError,
        ValueError,
        KeyError,
    ) as erro:
        st.error(
            "Não foi possível preparar a análise "
            "individual do ativo selecionado."
        )
    
        st.exception(
            erro
        )
    
        return
    curtailment_ativo_formatado = (formatar_numero_brasileiro(analise_ativo_elera["curtailment_gwh"],casas_decimais=2))
    
    corte_ativo = analise_ativo_elera["corte_pct"]
    
    if corte_ativo is not None:
        corte_ativo_formatado = (
            formatar_numero_brasileiro(
                corte_ativo,
                casas_decimais=2,
            )
        )
    
    else:
        corte_ativo_formatado = "—"
    
    mes_critico_ativo = analise_ativo_elera["mes_critico"]
    
    corte_mes_critico = analise_ativo_elera["corte_mes_critico_pct"]
    
    if corte_mes_critico is not None:
        corte_mes_critico_formatado = (formatar_numero_brasileiro(corte_mes_critico,casas_decimais=2))
    
    else:
        corte_mes_critico_formatado = "—"
    
    composicao_cortes_ativo = (analise_ativo_elera["composicao_cortes"].set_index("tipo_curtailment"))
    
    dados_composicao_ativo = {}
    
    for codigo in ["ENE","REL","CNF"]:
        if codigo in composicao_cortes_ativo.index:
            linha_tipo = composicao_cortes_ativo.loc[codigo]
    
            dados_composicao_ativo[codigo] = {"pct": float(linha_tipo["composicao_pct"]),"gwh": float(linha_tipo["curtailment_gwh"])}
    
        else:
            dados_composicao_ativo[codigo] = {"pct": 0.0,"gwh": 0.0}
   
    ene_gwh_formatado = formatar_numero_brasileiro(
        dados_composicao_ativo["ENE"]["gwh"],
        casas_decimais=2,
    )
    
    rel_gwh_formatado = formatar_numero_brasileiro(
        dados_composicao_ativo["REL"]["gwh"],
        casas_decimais=2,
    )
    
    cnf_gwh_formatado = formatar_numero_brasileiro(
        dados_composicao_ativo["CNF"]["gwh"],
        casas_decimais=2,
    )
    
    ene_pct = dados_composicao_ativo["ENE"]["pct"]
    rel_pct = dados_composicao_ativo["REL"]["pct"]
    cnf_pct = dados_composicao_ativo["CNF"]["pct"]

    with st.container(key="analise_individual_elera"):
        (coluna_grafico_ativo,coluna_resumo_ativo) = st.columns([1.55,1],gap="medium",vertical_alignment="top")
        
        with coluna_grafico_ativo:
            with st.container(border=True,key="card_grafico_ativo_elera"):
                (coluna_titulo_grafico_ativo,
                    coluna_visao_grafico_ativo,
                    coluna_metrica_grafico_ativo,
                    coluna_download_ativo) = st.columns([1.20,1.85,2.1,0.35],vertical_alignment="center")
            
                with coluna_titulo_grafico_ativo:
                    st.html(
                        """
                        <div class="titulo-card-grafico">
                            Análise do ativo
                        </div>
                        """
                    )
            
                with coluna_visao_grafico_ativo:
                    visao_individual_elera = (
                            st.segmented_control("Visão do ativo",options=["Volume Mensal","Perfil horário"],
                                default="Volume Mensal",
                                key="visao_individual_elera",
                                label_visibility="collapsed",
                                selection_mode="single",
                            )
                        )
            
                with coluna_metrica_grafico_ativo:
                    metrica_individual_elera = (
                        st.segmented_control("Métrica do ativo",options=["Curtailment","Geração esperada"],
                                default="Curtailment",
                                key="metrica_individual_elera",
                                label_visibility="collapsed",
                                selection_mode="single",
                            )
                        )
            
                if visao_individual_elera is None:
                    visao_individual_elera = "Volume Mensal"
            
                if metrica_individual_elera is None:
                    metrica_individual_elera = "Curtailment"

                
                
                # ============================================================
                # GRÁFICO DE CURTAILMENT
                # ============================================================
                
                if (visao_individual_elera == "Volume Mensal" and metrica_individual_elera == "Curtailment"):
                    base_grafico_ativo = (analise_ativo_elera["base_mensal_tipo"].copy())
        
                    ordem_eixo_x = (
                        base_grafico_ativo[["mes","mes_rotulo"]]
                        .drop_duplicates()
                        .sort_values("mes")["mes_rotulo"]
                        .tolist()
                    )
        
                    fig_ativo_elera = px.bar(
                        base_grafico_ativo,
                        x="mes_rotulo",
                        y="curtailment_gwh",
                        color="tipo_rotulo",
                        barmode="stack",
                        category_orders={
                            "mes_rotulo": ordem_eixo_x,
                            "tipo_rotulo": [
                                "Energético",
                                "Elétrico",
                                "Confiabilidade",
                            ],
                        },
                        color_discrete_map=(
                            cores_tipos_elera
                        ),
                        labels={
                            "mes_rotulo": "Mês",
                            "curtailment_gwh": (
                                "Curtailment (GWh)"
                            ),
                            "tipo_rotulo": "Tipo",
                        },
                        custom_data=[
                            "tipo_curtailment",
                            "tipo_rotulo",
                        ],
                    )
        
                    fig_ativo_elera.update_traces(
                        marker_line_color="#FFFFFF",
                        marker_line_width=0.5,
                        hovertemplate=(
                            "<b>%{customdata[1]}</b>"
                            "<br>Código: %{customdata[0]}"
                            "<br>Mês: %{x}"
                            "<br>Curtailment: "
                            "%{y:,.2f} GWh"
                            "<extra></extra>"
                        ),
                    )
        
                    titulo_eixo_ativo = ("Curtailment (GWh)")
                    mostrar_legenda_ativo = True

                    base_download_ativo_elera = (
                        analise_ativo_elera["base_mensal_tipo"][["mes","mes_rotulo","tipo_curtailment","tipo_rotulo","curtailment_gwh"]]
                        .copy()
                        .rename(
                            columns={
                                "mes": "Mês",
                                "mes_rotulo": "Competência",
                                "tipo_curtailment": ("Código do curtailment"),
                                "tipo_rotulo": ("Tipo de curtailment"),
                                "curtailment_gwh": ("Curtailment (GWh)")
                            }
                        )
                    )
                    
                    nome_planilha_ativo_elera = ("Curtailment mensal")
                    
                    nome_visao_arquivo_ativo = "mensal"
                    nome_metrica_arquivo_ativo = "curtailment"
                
                # ============================================================
                # GRÁFICO DE GERAÇÃO ESPERADA
                # ============================================================
                elif (visao_individual_elera == "Volume Mensal" and metrica_individual_elera== "Geração esperada"):
                    base_grafico_ativo = (analise_ativo_elera["base_mensal_resumo"].copy())
        
                    ordem_eixo_x = (
                        base_grafico_ativo[["mes","mes_rotulo"]]
                        .drop_duplicates()
                        .sort_values("mes")["mes_rotulo"]
                        .tolist()
                    )
        
                    fig_ativo_elera = px.bar(
                        base_grafico_ativo,
                        x="mes_rotulo",
                        y="geracao_esperada_gwh",
                        category_orders={
                            "mes_rotulo": ordem_eixo_x,
                        },
                        labels={
                            "mes_rotulo": "Mês",
                            "geracao_esperada_gwh": (
                                "Geração esperada (GWh)"
                            ),
                        },
                    )
        
                    fig_ativo_elera.update_traces(
                        marker_color=(
                            cor_geracao_esperada_elera
                        ),
                        marker_line_color="#FFFFFF",
                        marker_line_width=0.5,
                        hovertemplate=(
                            "<b>Geração esperada</b>"
                            "<br>Mês: %{x}"
                            "<br>Geração esperada: "
                            "%{y:,.2f} GWh"
                            "<extra></extra>"
                        ),
                    )
        
                    titulo_eixo_ativo = (
                        "Geração esperada (GWh)"
                    )
        
                    mostrar_legenda_ativo = False
                    base_download_ativo_elera = (
                        analise_ativo_elera["base_mensal_resumo"][["mes","mes_rotulo","geracao_esperada_gwh"]]
                        .copy()
                        .rename(columns={"mes": "Mês","mes_rotulo": "Competência","geracao_esperada_gwh": ("Geração esperada (GWh)")})
                    )
                    
                    nome_planilha_ativo_elera = ("Geração mensal")
                    
                    nome_visao_arquivo_ativo = "mensal"
                    nome_metrica_arquivo_ativo = "geracao_esperada"

                # ============================================================
                # PERFIL HORÁRIO COM CURTAILMENT
                # ============================================================
                elif (visao_individual_elera== "Perfil horário" and metrica_individual_elera == "Curtailment"):
                    base_grafico_ativo = (analise_ativo_elera["perfil_horario_tipo"].copy())
        
                    ordem_eixo_x = [f"{hora:02d}:00" for hora in range(24)]
        
                    fig_ativo_elera = px.bar(
                        base_grafico_ativo,
                        x="hora_rotulo",
                        y="curtailment_mw",
                        color="tipo_rotulo",
                        barmode="stack",
                        category_orders={
                            "hora_rotulo": ordem_eixo_x,
                            "tipo_rotulo": [
                                "Energético",
                                "Elétrico",
                                "Confiabilidade",
                            ],
                        },
                        color_discrete_map=(
                            cores_tipos_elera
                        ),
                        labels={
                            "hora_rotulo": "Hora",
                            "curtailment_mw": (
                                "Curtailment médio (MW)"
                            ),
                            "tipo_rotulo": "Tipo",
                        },
                        custom_data=[
                            "tipo_curtailment",
                            "tipo_rotulo",
                        ],
                    )
        
                    fig_ativo_elera.update_traces(
                        marker_line_color="#FFFFFF",
                        marker_line_width=0.4,
                        hovertemplate=(
                            "<b>%{customdata[1]}</b>"
                            "<br>Código: %{customdata[0]}"
                            "<br>Hora: %{x}"
                            "<br>Curtailment médio: "
                            "%{y:,.2f} MW"
                            "<extra></extra>"
                        ),
                    )
        
                    titulo_eixo_ativo = ("Curtailment médio (MW)")
        
                    mostrar_legenda_ativo = True
                    base_download_ativo_elera = (
                        analise_ativo_elera["perfil_horario_tipo"][["hora","hora_rotulo","tipo_curtailment","tipo_rotulo","curtailment_mw"]]
                        .copy()
                        .rename(
                            columns={
                                "hora": "Hora numérica",
                                "hora_rotulo": "Hora",
                                "tipo_curtailment": ("Código do curtailment"),
                                "tipo_rotulo": ("Tipo de curtailment"),
                                "curtailment_mw": ("Curtailment médio (MW)"),
                            }
                        )
                    )
                    
                    nome_planilha_ativo_elera = ("Curtailment horário")
                    
                    nome_visao_arquivo_ativo = "perfil_horario"
                    nome_metrica_arquivo_ativo = "curtailment"

                # ============================================================
                # PERFIL HORÁRIO COM GERAÇÃO ESPERADA
                # ============================================================
                else:
                    base_grafico_ativo = (analise_ativo_elera["perfil_horario_resumo"].copy())
        
                    ordem_eixo_x = [f"{hora:02d}:00" for hora in range(24)]
        
                    fig_ativo_elera = px.bar(
                        base_grafico_ativo,
                        x="hora_rotulo",
                        y="geracao_esperada_mw",
                        category_orders={
                            "hora_rotulo": ordem_eixo_x,
                        },
                        labels={
                            "hora_rotulo": "Hora",
                            "geracao_esperada_mw": (
                                "Geração esperada média (MW)"
                            ),
                        },
                    )
        
                    fig_ativo_elera.update_traces(
                        marker_color=(
                            cor_geracao_esperada_elera
                        ),
                        marker_line_color="#FFFFFF",
                        marker_line_width=0.4,
                        hovertemplate=(
                            "<b>Geração esperada</b>"
                            "<br>Hora: %{x}"
                            "<br>Potência média: "
                            "%{y:,.2f} MW"
                            "<extra></extra>"
                        ),
                    )
                    titulo_eixo_ativo = ("Geração esperada média (MW)")
        
                    mostrar_legenda_ativo = False
                    base_download_ativo_elera = (
                        analise_ativo_elera["perfil_horario_resumo"][["hora","hora_rotulo","geracao_esperada_mw"]]
                        .copy()
                        .rename(
                            columns={"hora": "Hora numérica","hora_rotulo": "Hora","geracao_esperada_mw": ("Geração esperada média (MW)")}
                        )
                    )
                    
                    nome_planilha_ativo_elera = ("Geração horária")
                    
                    nome_visao_arquivo_ativo = "perfil_horario"
                    nome_metrica_arquivo_ativo = "geracao_esperada"

                # ============================================================
                # DOWNLOAD DO GRÁFICO INDIVIDUAL
                # ============================================================
                
                base_download_ativo_elera.insert(0,"Ativo",analise_ativo_elera["ativo"])
                
                base_download_ativo_elera.insert(1,"Fonte",analise_ativo_elera["fonte"])
                
                base_download_ativo_elera.insert(2,"Estado",analise_ativo_elera["estado"])
                
                arquivo_download_ativo_elera = (gerar_excel_dataframe(df=base_download_ativo_elera,nome_planilha=(nome_planilha_ativo_elera)))
                nome_ativo_arquivo = (ativo_selecionado_elera.strip().lower()
                    .replace(" ","_")
                    .replace("ã","a")
                    .replace("á","a")
                    .replace("â","a")
                    .replace("é","e")
                    .replace("ê","e")
                    .replace("í","i")
                    .replace("ó","o")
                    .replace("ô","o")
                    .replace("ú","u")
                    .replace("ç","c")
                )
                periodo_inicial_arquivo = (f"{periodo_processado['ano_inicial']}-{periodo_processado['mes_inicial']:02d}")
                periodo_final_arquivo = (f"{periodo_processado['ano_final']}-{periodo_processado['mes_final']:02d}")
                nome_arquivo_ativo_elera = (
                    "SINmulator_ativo_elera_"
                    f"{nome_ativo_arquivo}_"
                    f"{nome_visao_arquivo_ativo}_"
                    f"{nome_metrica_arquivo_ativo}_"
                    f"{periodo_inicial_arquivo}_"
                    f"{periodo_final_arquivo}"
                    ".xlsx"
                )

                with coluna_download_ativo:
                    with st.container(
                        key="download_ativo_elera",
                    ):
                        st.download_button(
                            label="Baixar",
                            data=arquivo_download_ativo_elera,
                            file_name=(nome_arquivo_ativo_elera),
                            mime=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                            help=("Baixar os dados exibidos no gráfico do ativo selecionado"),
                            key=("botao_download_ativo_elera_"
                                f"{ativo_selecionado_elera}_"
                                f"{visao_individual_elera}_"
                                f"{metrica_individual_elera}"
                            ),
                        )
                # ============================================================
                # FORMATAÇÃO COMPARTILHADA
                # ============================================================
                
                fig_ativo_elera.update_layout(
                    height=350,
                    margin={
                        "l": 10,
                        "r": 10,
                        "t": (
                            50
                            if mostrar_legenda_ativo
                            else 20
                        ),
                        "b": 15,
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
                    showlegend=mostrar_legenda_ativo,
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
                            "size": 12,
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
                    bargap=0.25,
                )
                
                if (visao_individual_elera == "Perfil horário"):
                    fig_ativo_elera.update_xaxes(
                        title="Hora do dia",
                        categoryorder="array",
                        categoryarray=ordem_eixo_x,
                        tickmode="array",
                        tickvals=[
                            f"{hora:02d}:00" for hora in range(0,24,2,)],
                        showgrid=False,
                        showline=False,
                        tickfont={"size": 10,"color": "#64748B"},
                        fixedrange=True,
                    )
        
                else:
                    fig_ativo_elera.update_xaxes(
                        title=None,
                        categoryorder="array",
                        categoryarray=ordem_eixo_x,
                        showgrid=False,
                        showline=False,
                        tickfont={"size": 11,"color": "#64748B"},
                        fixedrange=True,
                    )
                
                fig_ativo_elera.update_yaxes(
                    title=titulo_eixo_ativo,
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
                    tickformat=",.0f",
                    fixedrange=True,
                )
                
                st.plotly_chart(
                    fig_ativo_elera,
                    width="stretch",
                    height=350,
                    config={
                        "displayModeBar": False,
                        "responsive": True,
                    },
                    key=(
                        "grafico_individual_elera_"
                        f"{ativo_selecionado_elera}_"
                        f"{visao_individual_elera}_"
                        f"{metrica_individual_elera}"
                    ),
                )

        with coluna_resumo_ativo:
            with st.container(border=True,key="card_resumo_ativo_elera"):
                fonte_ativo_resumo = (analise_ativo_elera["fonte"])
        
                if fonte_ativo_resumo == "Solar":
                    simbolo_fonte_ativo = "☀"
                    classe_fonte_ativo = "solar"
        
                else:
                    simbolo_fonte_ativo = "≋"
                    classe_fonte_ativo = "eolica"
                    
                html_resumo_ativo = (
                    '<div class="resumo-ativo-elera">'
                
                    # ========================================================
                    # CABEÇALHO COM ATIVO, FONTE E ESTADO
                    # ========================================================
                
                    '<div class="resumo-ativo-cabecalho-compacto">'
                
                    '<div class="resumo-ativo-identificacao">'
                
                    '<strong class="resumo-ativo-nome-compacto">'
                    f'{analise_ativo_elera["ativo"]}'
                    '</strong>'
                
                    '</div>'
                
                    '<div class="resumo-ativo-selos">'
                
                    '<span class="resumo-ativo-selo '
                    f'resumo-ativo-selo-{classe_fonte_ativo}">'
                    '<span class="resumo-ativo-selo-icone">'
                    f'{simbolo_fonte_ativo}'
                    '</span>'
                    f'{analise_ativo_elera["fonte"]}'
                    '</span>'
                
                    '<span class="resumo-ativo-selo '
                    'resumo-ativo-selo-local">'
                    '<span class="resumo-ativo-selo-icone">'
                    '⌖'
                    '</span>'
                    f'{analise_ativo_elera["estado"]}'
                    '</span>'
                
                    '</div>'
                
                    '</div>'
                
                    # ========================================================
                    # KPIs
                    # ========================================================
                
                    '<div class="resumo-ativo-kpis">'
                
                    '<div class="resumo-ativo-kpi">'
                    '<span>Curtailment</span>'
                    '<strong>'
                    f'{curtailment_ativo_formatado} GWh'
                    '</strong>'
                    '</div>'
                
                    '<div class="resumo-ativo-kpi">'
                    '<span>Corte</span>'
                    '<strong>'
                    f'{corte_ativo_formatado}%'
                    '</strong>'
                    '</div>'
                
                    '<div class="resumo-ativo-kpi">'
                    '<span>Mês crítico</span>'
                    '<strong>'
                    f'{mes_critico_ativo}'
                    '</strong>'
                    '<small>'
                    f'{corte_mes_critico_formatado}% de corte'
                    '</small>'
                    '</div>'
                
                    '</div>'
                
                    '</div>'
                )
    
                st.html(html_resumo_ativo)
                base_composicao_grafico = (analise_ativo_elera["composicao_cortes"][["tipo_curtailment","tipo_rotulo","curtailment_gwh","composicao_pct"]].copy())
                st.html(
                    """
                    <div class="titulo-composicao-circular">
                        Composição dos cortes no período
                    </div>
                    """
                )
                ordem_tipos_composicao = ["ENE","REL","CNF"]
                cores_composicao_cortes = {"ENE": "#3275C9","REL": "#2EAAA5","CNF": "#FF646B"}
                
                base_composicao_grafico["tipo_curtailment"] = pd.Categorical(
                    base_composicao_grafico["tipo_curtailment"],
                    categories=ordem_tipos_composicao,
                    ordered=True,
                )
                
                base_composicao_grafico = (
                    base_composicao_grafico
                    .sort_values("tipo_curtailment")
                    .reset_index(drop=True)
                )

                total_curtailment_composicao = (
                    base_composicao_grafico[
                        "curtailment_gwh"
                    ]
                    .sum()
                )
                
                total_curtailment_central = (
                    formatar_numero_brasileiro(
                        total_curtailment_composicao,
                        casas_decimais=2,
                    )
                )
                
                fig_composicao_ativo = px.pie(
                    base_composicao_grafico,
                    names="tipo_curtailment",
                    values="curtailment_gwh",
                    hole=0.64,
                    category_orders={"tipo_curtailment": (ordem_tipos_composicao),
                    },
                    color="tipo_curtailment",
                    color_discrete_map=(cores_composicao_cortes),
                    custom_data=["tipo_rotulo","composicao_pct","curtailment_gwh"]
                )
                fig_composicao_ativo.update_traces(
                    texttemplate="%{percent:.1%}",
                    textposition="inside",
                    textfont={
                        "color": "#FFFFFF",
                        "size": 11,
                        "family": (
                            "Segoe UI, Arial, sans-serif"
                        ),
                    },
                    marker={
                        "line": {
                            "color": "#FFFFFF",
                            "width": 2,
                        },
                    },
                    sort=False,
                    direction="clockwise",
                    domain={
                        "x": [
                            0.0,
                            0.72,
                        ],
                        "y": [
                            0.0,
                            1.0,
                        ],
                    },
                    hovertemplate=(
                        "<b>%{label} | %{customdata[0]}</b>"
                        "<br>Participação: %{customdata[1]:.2f}%"
                        "<br>Curtailment: %{customdata[2]:,.2f} GWh"
                        "<extra></extra>"
                    ),
                )
                fig_composicao_ativo.update_layout(
                    height=180,
                    margin={
                        "l": 0,
                        "r": 0,
                        "t": 5,
                        "b": 5,
                    },
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font={
                        "family": ("Segoe UI, Arial, sans-serif"),
                        "color": "#334155",
                        "size": 11,
                    },
                    legend={
                        "title": {
                            "text": "",
                        },
                        "orientation": "v",
                        "yanchor": "middle",
                        "y": 0.5,
                        "xanchor": "left",
                        "x": 0.82,
                        "font": {
                            "size": 11,
                            "color": "#334155",
                        },
                    },
                    annotations=[
                        {
                            "text": (
                                f"<b>{total_curtailment_central}</b>"
                                "<br><span style='font-size:10px'>"
                                "GWh"
                                "</span>"
                            ),
                            "x": 0.36,
                            "y": 0.5,
                            "showarrow": False,
                            "align": "center",
                            "font": {
                                "size": 13,
                                "color": "#102D57",
                            },
                        }
                    ],
                    hoverlabel={
                        "bgcolor": "#FFFFFF",
                        "bordercolor": "#D9E2EC",
                        "font": {
                            "color": "#102D57",
                            "size": 12,
                        },
                    },
                )
                st.plotly_chart(
                    fig_composicao_ativo,
                    width="stretch",
                    height=180,
                    config={
                        "displayModeBar": False,
                        "responsive": True,
                    },
                    key=(f"grafico_composicao_ativo_elera_{ativo_selecionado_elera}"),
                )
    # ============================================================
    # EXPORTAÇÃO DETALHADA DOS ATIVOS ELERA
    # ============================================================
    
    with st.container(border=True,key="card_exportacao_ativos_elera"):
        (
            coluna_titulo_exportacao_elera,
            coluna_recorte_exportacao_elera,
            coluna_granularidade_exportacao_elera,
            coluna_download_exportacao_elera,
        ) = st.columns([2.7,1.2,1.2,0.35],gap="medium",vertical_alignment="center")
    
        with coluna_titulo_exportacao_elera:
            st.html(
                """
                <div class="cabecalho-exportacao-elera">
                    <div class="titulo-card-grafico">
                        Exportar análise detalhada
                    </div>
    
                    <div class="subtitulo-exportacao-elera">
                        Curtailment por tipo, geração esperada e
                        corte percentual, separados por ativo,
                        fonte e estado.
                    </div>
                </div>
                """
            )
    
        with coluna_recorte_exportacao_elera:
            opcoes_recorte_exportacao = [
                "Portfólio inteiro",
                "Somente solares",
                "Somente eólicas",
                *ORDEM_ATIVOS_ELERA,
            ]
    
            recorte_exportacao_elera = st.selectbox(
                "Ativos",
                options=opcoes_recorte_exportacao,
                index=0,
                key="recorte_exportacao_elera",
            )
    
        with coluna_granularidade_exportacao_elera:
            granularidade_exportacao_elera = st.selectbox(
                "Granularidade",
                options=[
                    "Mês e hora",
                    "Dia e hora",
                    "Dia",
                    "Mês",
                    "Ano",
                ],
                index=2,
                key="granularidade_exportacao_elera",
            )
        try:
            base_exportacao_detalhada_elera = (
                preparar_exportacao_detalhada_elera_aplicacao(
                    df_curtailment=(df_curtailment_ativos_elera),
                    recorte_selecionado=(recorte_exportacao_elera),
                    granularidade=(granularidade_exportacao_elera),
                )
            )
    
        except (TypeError,ValueError,KeyError) as erro:
            st.error("Não foi possível preparar a base detalhada para exportação.")
            st.exception(erro)

            return
        
        nomes_recortes_arquivo = {
            "Portfólio inteiro": "portfolio_inteiro",
            "Somente solares": "somente_solares",
            "Somente eólicas": "somente_eolicas",
            "Janaúba": "janauba",
            "Alex": "alex",
            "Alto Sertão": "alto_sertao",
            "Renascença": "renascenca",
            "Pontal": "pontal",
            "Seridó": "serido",
            "Faísa": "faisa",
        }
    
        nomes_granularidades_arquivo = {
            "Mês e hora": "mes_hora",
            "Dia e hora": "dia_hora",
            "Dia": "dia",
            "Mês": "mes",
            "Ano": "ano",
        }
    
        nome_recorte_arquivo = (nomes_recortes_arquivo[recorte_exportacao_elera])
        nome_granularidade_arquivo = (nomes_granularidades_arquivo[granularidade_exportacao_elera])
        periodo_inicial_exportacao = (f"{periodo_processado['ano_inicial']}-{periodo_processado['mes_inicial']:02d}")
        periodo_final_exportacao = (f"{periodo_processado['ano_final']}-{periodo_processado['mes_final']:02d}")
        nome_planilha_exportacao = ("Análise detalhada")
    
        arquivo_exportacao_detalhada_elera = (
            gerar_excel_dataframe(df=base_exportacao_detalhada_elera,nome_planilha=(nome_planilha_exportacao),))
        nome_arquivo_exportacao_elera = (
            "SINmulator_"
            "analise_detalhada_elera_"
            f"{nome_recorte_arquivo}_"
            f"{nome_granularidade_arquivo}_"
            f"{periodo_inicial_exportacao}_"
            f"{periodo_final_exportacao}"
            ".xlsx"
        )
        with coluna_download_exportacao_elera:
            with st.container(key="download_detalhado_elera"):
                st.download_button(
                    label="Baixar",
                    data=(arquivo_exportacao_detalhada_elera),
                    file_name=(nome_arquivo_exportacao_elera),
                    mime=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                    help=("Baixar a análise detalhada dos ativos selecionados"),
                    key=("botao_download_detalhado_elera_"
                        f"{nome_recorte_arquivo}_{nome_granularidade_arquivo}"),
                )

def renderizar_pagina_cp45(
    hoje,
    ultimo_ano_completo,
    ultimo_mes_completo,
):
    """
    Renderiza a página CP45.
    """

    st.html(
        """
        <div class="cabecalho-cp45">
            <h1>CP45</h1>
            <p>
                Análise dos cenários de rateio do
                curtailment e seus impactos.
            </p>
        </div>
        """
    )
    # ========================================================
    # FILTROS
    # ========================================================

    try:

        (
            filtros_aplicados,
            status_cp45,
            resumo_cp45,
        ) = renderizar_filtros_cp45(
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

    # ========================================================
    # SALVA FILTROS
    # ========================================================

    if filtros_aplicados is not None:

        st.session_state[
            "filtros_cp45"
        ] = filtros_aplicados

        st.session_state[
            "processar_cp45"
        ] = True

    filtros_cp45 = st.session_state.get(
        "filtros_cp45"
    )

    if filtros_cp45 is None:
        return

    # ========================================================
    # PROCESSAMENTO
    # ========================================================

    if st.session_state.get(
        "processar_cp45",
        False,
    ):

        try:

            with status_cp45.container():

                with st.spinner(
                    "Preparando análise CP45..."
                ):

                    # ------------------------------------
                    # BASES
                    # ------------------------------------

                    df_curtailment = (
                        carregar_base_curtailment_cp45(
                            ano_inicial=filtros_cp45["ano_inicial"],
                            mes_inicial=filtros_cp45["mes_inicial"],
                            ano_final=filtros_cp45["ano_final"],
                            mes_final=filtros_cp45["mes_final"],
                            hoje=hoje,
                        )
                    )

                    df_pld, _ = (
                        carregar_pld_cp45_aplicacao()
                    )

                    df_pld_aberto = (
                        preparar_pld_aberto_cp45_aplicacao(
                            df_pld
                        )
                    )

                    lista_evt = []

                    for ano in range(
                        ANO_MINIMO,
                        ultimo_ano_completo + 1,
                    ):

                        mes_final = (
                            ultimo_mes_completo
                            if ano
                            == ultimo_ano_completo
                            else 12
                        )

                        df_evt_ano, _ = (
                            carregar_evt_ano_cp45_aplicacao(
                                ano=ano,
                                mes_inicial=1,
                                mes_final=mes_final,
                            )
                        )

                        lista_evt.append(
                            df_evt_ano
                        )

                    df_evt = pd.concat(
                        lista_evt,
                        ignore_index=True,
                    )

                    df_base_fontes_cp45 = (
                        montar_base_fontes_cp45_aplicacao(
                            df_curtailment=(
                                df_curtailment
                            ),
                            df_evt=df_evt,
                            df_pld_aberto=(
                                df_pld_aberto
                            ),
                        )
                    )

                    df_ativos_cp45 = (
                        preparar_ativos_cp45_aplicacao(
                            df_curtailment
                        )
                    )

                    df_ativos_cenarios_cp45 = (
                        montar_cenarios_cp45_aplicacao(
                            df_base_fontes_cp45,
                            df_ativos_cp45,
                        )["ativos"]
                    )

                    st.session_state[
                        "df_ativos_cenarios_cp45"
                    ] = (
                        df_ativos_cenarios_cp45
                    )

            st.session_state[
                "processar_cp45"
            ] = False

            status_cp45.empty()

        except Exception as erro:

            st.session_state[
                "processar_cp45"
            ] = False

            st.exception(
                erro
            )

            return

    # ========================================================
    # RESULTADOS
    # ========================================================

    df_ativos_cenarios_cp45 = (
        st.session_state.get(
            "df_ativos_cenarios_cp45"
        )
    )
    
    if df_ativos_cenarios_cp45 is None:
        return
        
    usinas_disponiveis = sorted(
        df_ativos_cenarios_cp45[
            "ativo"
        ]
        .dropna()
        .unique()
        .tolist()
    )
    if not usinas_disponiveis:
        st.warning(
            "Nenhuma usina encontrada para o período selecionado."
        )
        return
    # ========================================================
    # SELETOR DE USINA
    # ========================================================
    st.html(
        """
        <div class="titulo-secao-cp45">
            Análise por usina
        </div>
        """
    )
    usina_selecionada = st.pills(
        "Selecione a usina",
        options=usinas_disponiveis,
        default=usinas_disponiveis[0],
        selection_mode="single",
        key="cp45_usina",
        label_visibility="collapsed",
        width="stretch",
    )
    # ========================================================
    # PREPARA ANÁLISE DA USINA
    # ========================================================
    analise_cp45 = (
        preparar_analise_cp45_aplicacao(
            df_ativos_cenarios_cp45=(
                df_ativos_cenarios_cp45
            ),
            ano_inicial=(
                filtros_cp45[
                    "ano_inicial"
                ]
            ),
            mes_inicial=(
                filtros_cp45[
                    "mes_inicial"
                ]
            ),
            ano_final=(
                filtros_cp45[
                    "ano_final"
                ]
            ),
            mes_final=(
                filtros_cp45[
                    "mes_final"
                ]
            ),
            usina_selecionada=(
                usina_selecionada
            ),
        )
    )

    indicadores = (
        analise_cp45[
            "indicadores"
        ]
    )

    resumo_cenarios = (
        analise_cp45[
            "resumo_cenarios"
        ]
    )

    resumo_mensal = (
        analise_cp45[
            "resumo_mensal"
        ]
    )

    resumo_cp45.html(
        (
            '<div class="resumo-subsistemas-filtros">'
            '<span class="resumo-subsistemas-indicador">●</span>'
            '<span>'
            f'Usina <strong>{indicadores["ativo"]}</strong> | '
            f'Fonte <strong>{indicadores["fonte"]}</strong> | '
            f'Subsistema <strong>{indicadores["subsistema"]}</strong>'
            '</span>'
            '</div>'
        )
    )

    # ========================================================
    # KPIs
    # ========================================================

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Geração Esperada",
        f'{indicadores["geracao_esperada_gwh"]:,.1f} GWh'
    )

    col2.metric(
        "Curtailment Atual",
        f'{indicadores["curtailment_atual_gwh"]:,.1f} GWh'
    )

    col3.metric(
        "Melhor Cenário",
        indicadores[
            "melhor_cenario_codigo"
        ]
    )

    col4.metric(
        "Redução Potencial",
        f'{indicadores["melhor_reducao_pct"]:.1f}%'
    )

    # ========================================================
    # GRÁFICOS
    # ========================================================

    col_esq, col_dir = st.columns(2)

    with col_esq:

        fig = (
            grafico_curtailment_cenarios_cp45(
                resumo_cenarios
            )
        )

        st.plotly_chart(
            fig,
            width="stretch",
            config={
                "displayModeBar": False
            },
        )

    with col_dir:

        fig = (
            grafico_corte_cenarios_cp45(
                resumo_cenarios
            )
        )

        st.plotly_chart(
            fig,
            width="stretch",
            config={
                "displayModeBar": False
            },
        )

    cenario_mensal = st.selectbox(
        "Comparar mensalmente",
        [
            "1A",
            "1B",
            "2A",
            "2B",
            "3A",
            "3B",
            "4A",
            "4B",
        ],
        key="cp45_cenario_mensal",
    )

    fig_mensal = (
        grafico_mensal_cenario_cp45(
            resumo_mensal,
            cenario_mensal,
        )
    )

    st.plotly_chart(
        fig_mensal,
        width="stretch",
        config={
            "displayModeBar": False
        },
    )

    st.dataframe(
        resumo_cenarios,
        width="stretch",
        hide_index=True,
    )

    # ========================================================
    # TABELA RESUMO
    # ========================================================

    with st.container(
        border=True,
    ):

        st.html(
            """
            <div class="titulo-card-grafico">
                Resumo dos Cenários
            </div>
            """
        )

        st.dataframe(
            resumo_cenarios[
                [
                    "codigo",
                    "cenario",
                    "curtailment_gwh",
                    "corte_pct",
                    "diferenca_atual_gwh",
                    "diferenca_atual_pp",
                ]
            ],
            hide_index=True,
            width="stretch",
        )


@st.cache_data(show_spinner=False)
def calcular_kpis_subsistemas_aplicacao(
    df_curtailment,
):
    """
    Calcula os KPIs da página Subsistemas.
    """

    return calcular_kpis_curtailment(df_curtailment)

# FUNÇÕES COM CACHE - ATIVOS ELERA

@st.cache_data(show_spinner=False)
def calcular_kpis_ativos_elera_aplicacao(
    df_curtailment,
):
    """
    Calcula os KPIs da página Ativos Elera.
    """

    return calcular_kpis_ativos_elera(df_curtailment)

@st.cache_data(show_spinner=False)
def preparar_curtailment_mensal_elera_aplicacao(
    df_curtailment,
):
    """
    Prepara o curtailment mensal do portfólio Elera.
    """

    return preparar_curtailment_mensal_ativos_elera(df_curtailment)


@st.cache_data(show_spinner=False)
def preparar_participacao_curtailment_elera_aplicacao(
    df_curtailment,
):
    """
    Prepara a participação dos ativos no curtailment.
    """

    return preparar_participacao_curtailment_ativos_elera(df_curtailment)

@st.cache_data(show_spinner=False)
def preparar_geracao_mensal_elera_aplicacao(
    df_curtailment,
):
    """
    Prepara a geração esperada mensal do portfólio Elera.
    """

    return preparar_geracao_esperada_mensal_ativos_elera(df_curtailment)

@st.cache_data(show_spinner=False)
def preparar_participacao_geracao_elera_aplicacao(
    df_curtailment,
):
    """
    Prepara a participação dos ativos na geração esperada.
    """

    return preparar_participacao_geracao_ativos_elera(df_curtailment)

@st.cache_data(show_spinner=False)
def preparar_analise_individual_elera_aplicacao(
    df_curtailment,
    ativo_selecionado,
):
    return preparar_analise_individual_ativo_elera(df=df_curtailment, ativo_selecionado=ativo_selecionado)

@st.cache_data(show_spinner=False)
def preparar_exportacao_detalhada_elera_aplicacao(df_curtailment,recorte_selecionado,granularidade):
    """
    Prepara a base detalhada para exportação.
    """

    return preparar_exportacao_detalhada_ativos_elera(df=df_curtailment,recorte_selecionado=recorte_selecionado,granularidade=granularidade)
    
# FUNCOES COM CACHE: BASES DE PLD DA CP45

@st.cache_resource(show_spinner=False)
def carregar_base_curtailment_cp45(
    ano_inicial,
    mes_inicial,
    ano_final,
    mes_final,
    hoje,
):
    dados_pipeline = executar_pipeline_aplicacao(
        ano_inicial=ano_inicial,
        mes_inicial=mes_inicial,
        ano_final=ano_final,
        mes_final=mes_final,
        fontes=("EOL", "UFV"),
        data_referencia=hoje,
        timeout=TIMEOUT_PIPELINE,
    )

    return dados_pipeline["df_curtailment"]

@st.cache_data(show_spinner=False)
def carregar_pld_cp45_aplicacao():
    """
    Carrega e trata os arquivos anuais de PLD
    armazenados no repositório.

    Retorna
    -------
    tuple
        Base longa de PLD e relatório de carregamento.
    """

    return carregar_bases_pld()

@st.cache_data(show_spinner=False)
def preparar_pld_aberto_cp45_aplicacao(
    df_pld,
):
    """
    Abre os valores de PLD por submercado e calcula
    o descolamento horário.
    """

    return preparar_pld_aberto(
        df_pld
    )

# FUNCOES COM CACHE: SUBSISTEMAS

@st.cache_data(show_spinner=False)
def preparar_resumo_subsistemas_aplicacao(
    df_curtailment,
):
    """
    Prepara a tabela de resumo da página Subsistemas.
    """

    return preparar_resumo_subsistemas(df_curtailment)
# ============================================================
# CACHE: ENERGIA VERTIDA TURBINÁVEL
# ============================================================

@st.cache_data(show_spinner=False,ttl=3600)
def carregar_evt_ano_cp45_aplicacao(
    ano,
    mes_inicial,
    mes_final,
):
    """
    Carrega um intervalo mensal da base EVT para um ano.
    """

    df_evt, relatorio_evt = (
        carregar_periodo_evt(
            ano=int(
                ano
            ),
            mes_inicial=int(
                mes_inicial
            ),
            mes_final=int(
                mes_final
            ),
        )
    )

    return (df_evt,relatorio_evt)

# ============================================================
# CACHE: PREPARAÇÃO HORÁRIA DA CP45
# ============================================================

@st.cache_data(
    show_spinner=False,
)
def montar_base_fontes_cp45_aplicacao(
    df_curtailment,
    df_evt,
    df_pld_aberto,
):
    """
    Monta a base horária por fonte e subsistema.
    """

    return montar_base_fontes_cp45(
        df_curtailment=(
            df_curtailment
        ),
        df_evt=df_evt,
        df_pld_aberto=(
            df_pld_aberto
        ),
    )

@st.cache_data(
    show_spinner=False,
)
def preparar_ativos_cp45_aplicacao(
    df_curtailment,
):
    """
    Prepara todos os ativos EOL e UFV em
    granularidade horária.
    """

    return preparar_ativos_horarios_cp45(df_curtailment=(df_curtailment))

# ============================================================
# CACHE: CENÁRIOS DA CP45
# ============================================================

@st.cache_data(
    show_spinner=False,
)
def montar_cenarios_cp45_aplicacao(
    df_base_fontes_cp45,
    df_ativos_cp45,
):
    """
    Calcula as taxas dos cenários e aplica os
    resultados aos ativos.
    """

    return montar_base_cenarios_cp45(df_base_fontes_cp45=(df_base_fontes_cp45),df_ativos_cp45=(df_ativos_cp45))

# ============================================================
# CACHE: OPÇÕES DOS FILTROS DA CP45
# ============================================================

@st.cache_data(
    show_spinner=False,
)
def obter_opcoes_cp45_aplicacao(
    df_ativos_cenarios_cp45,
):
    """
    Retorna usinas e limites temporais disponíveis.
    """

    return obter_opcoes_filtros_cp45(df_ativos_cenarios_cp45)
# ============================================================
# CACHE: ANÁLISE INDIVIDUAL DA CP45
# ============================================================

@st.cache_data(
    show_spinner=False,
)
def preparar_analise_cp45_aplicacao(
    df_ativos_cenarios_cp45,
    ano_inicial,
    mes_inicial,
    ano_final,
    mes_final,
    usina_selecionada,
):
    """
    Prepara indicadores, resumo dos cenários e
    resultados mensais da usina selecionada.
    """

    return preparar_analise_individual_cp45(
        df=(
            df_ativos_cenarios_cp45
        ),
        ano_inicial=int(
            ano_inicial
        ),
        mes_inicial=int(
            mes_inicial
        ),
        ano_final=int(
            ano_final
        ),
        mes_final=int(
            mes_final
        ),
        usina_selecionada=str(
            usina_selecionada
        ).strip(),
    )


@st.cache_data(show_spinner=False)
def gerar_excel_dataframe(
    df,
    nome_planilha,
):
    """
    Gera um arquivo XLSX em memória a partir
    de um DataFrame.
    """

    if not isinstance(
        df,
        pd.DataFrame,
    ):
        raise TypeError(
            "df deve ser um DataFrame."
        )

    buffer = BytesIO()

    nome_planilha_excel = str(
        nome_planilha
    )[:31]

    with pd.ExcelWriter(
        buffer,
        engine="openpyxl",
    ) as escritor:
        df.to_excel(
            escritor,
            sheet_name=nome_planilha_excel,
            index=False,
        )

        planilha = escritor.book[
            nome_planilha_excel
        ]

        planilha.freeze_panes = "A2"
        planilha.auto_filter.ref = (
            planilha.dimensions
        )

        for coluna in planilha.columns:
            maior_largura = 0

            letra_coluna = (
                coluna[0].column_letter
            )

            for celula in coluna:
                if celula.value is None:
                    continue

                maior_largura = max(
                    maior_largura,
                    len(
                        str(
                            celula.value
                        )
                    ),
                )

            planilha.column_dimensions[
                letra_coluna
            ].width = min(
                max(
                    maior_largura + 2,
                    12,
                ),
                36,
            )

    buffer.seek(0)

    return buffer.getvalue()

@st.cache_data(show_spinner=False)
def preparar_exportacao_subsistemas_aplicacao(
    df_curtailment,
    granularidade,
):
    """
    Prepara a análise detalhada por subsistema
    para exportação.
    """

    return preparar_exportacao_subsistemas(
        df=df_curtailment,
        granularidade=granularidade,
    )

@st.cache_data(show_spinner=False)
def carregar_imagem_base64(
    caminho_imagem,
):
    """
    Converte uma imagem local em uma URI base64 para
    utilização em elementos HTML.
    """

    caminho = Path(caminho_imagem)

    if not caminho.exists():
        return None

    extensao = (caminho.suffix.lower().replace(".",""))

    tipos_mime = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "svg": "image/svg+xml",
    }

    tipo_mime = tipos_mime.get(extensao,"image/png",)

    imagem_base64 = base64.b64encode(caminho.read_bytes()).decode("utf-8")

    return (f"data:{tipo_mime};base64,{imagem_base64}")

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

pagina_ativa = st.query_params.get("pagina","mapa")

paginas_permitidas = {"mapa","subsistemas","ativos_elera","cp45"}

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

classe_ativos_elera = (
    "sin-navbar-item sin-navbar-item-ativo "
    "sin-navbar-item-elera"
    if pagina_ativa == "ativos_elera"
    else (
        "sin-navbar-item "
        "sin-navbar-item-elera")
)
classe_cp45 = (
    "sin-navbar-item sin-navbar-item-ativo"
    if pagina_ativa == "cp45"
    else "sin-navbar-item"
)
logo_elera_base64 = carregar_imagem_base64(CAMINHO_LOGO_ELERA)

if logo_elera_base64 is not None:
    html_logo_elera = (
        '<span class="sin-navbar-logo-elera">'
        '<img '
        f'src="{logo_elera_base64}" '
        'alt="" '
        'aria-hidden="true" '
        'width="18" '
        'height="18" '
        'style="'
        'display:block;'
        'width:18px;'
        'height:18px;'
        'margin:0;'
        'padding:0;'
        'object-fit:contain;'
        '">'
        '</span>'
    )

else:
    html_logo_elera = (
        '<span '
        'class="sin-navbar-logo-elera '
        'sin-navbar-logo-elera-fallback" '
        'aria-hidden="true">'
        '☀'
        '</span>'
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

    f'<a class="{classe_ativos_elera}" '
    'href="?pagina=ativos_elera" target="_self" '
    'title="Visualizar os ativos da Elera">'
    f'{html_logo_elera}'
    '<span>Ativos Elera</span>'
    '</a>'
    
    f'<a class="{classe_cp45}" '
    'href="?pagina=cp45" target="_self" '
    'title="Visualizar a análise da CP45">'
    '<span class="sin-navbar-item-icone" '
    'aria-hidden="true">'
    '▤'
    '</span>'
    '<span>CP45</span>'
    '</a>'

    '</div>'
    '</div>'
)

st.html(html_navbar)


# ============================================================
# CONTEÚDO DA ABA SUBSISTEMAS
# ============================================================
if pagina_ativa == "subsistemas":
    renderizar_pagina_subsistemas(
        hoje=hoje,
        ultimo_ano_completo=(ultimo_ano_completo),
        ultimo_mes_completo=(ultimo_mes_completo),
    )

    st.stop()
# ============================================================
# CONTEÚDO DA ABA ATIVOS ELERA
# ============================================================
if pagina_ativa == "ativos_elera":
    renderizar_pagina_ativos_elera(
        hoje=hoje,
        ultimo_ano_completo=(ultimo_ano_completo),
        ultimo_mes_completo=(ultimo_mes_completo)
    )

    st.stop()
# ============================================================
# CONTEÚDO DA ABA CP45
# ============================================================
if pagina_ativa == "cp45":
    renderizar_pagina_cp45(
        hoje=hoje,
        ultimo_ano_completo=ultimo_ano_completo,
        ultimo_mes_completo=ultimo_mes_completo,
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
