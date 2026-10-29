"""
Análises consolidadas dos cenários da CP45.

Este módulo recebe a base horária de ativos produzida
por cenarios_cp45.py e prepara:

- filtros de período e usina;
- resumo dos cenários;
- indicadores consolidados;
- resultados mensais;
- resultados por usina.

O módulo não coleta dados, não recalcula taxas horárias
e não cria gráficos.
"""

import numpy as np
import pandas as pd


# ============================================================
# CATÁLOGO DOS CENÁRIOS
# ============================================================

CENARIOS_CP45 = {
    "Atual": {
        "coluna_curtailment": (
            "curtailment_atual_mwh"
        ),
        "coluna_corte": (
            "corte_atual_pct"
        ),
        "nome": "Cenário atual",
        "nome_curto": "Atual",
        "escopo": "Cenário atual",
        "perimetro": "Atual",
        "ordem": 0,
    },
    "1A": {
        "coluna_curtailment": (
            "curtailment_1a_mwh"
        ),
        "coluna_corte": (
            "corte_1a_pct"
        ),
        "nome": (
            "EVT nos conjuntos vertendo · Nacional"
        ),
        "nome_curto": (
            "EVT nos conjuntos vertendo"
        ),
        "escopo": (
            "EVT nos conjuntos vertendo"
        ),
        "perimetro": "Pool nacional",
        "ordem": 1,
    },
    "1B": {
        "coluna_curtailment": (
            "curtailment_1b_mwh"
        ),
        "coluna_corte": (
            "corte_1b_pct"
        ),
        "nome": (
            "EVT nos conjuntos vertendo · PLD"
        ),
        "nome_curto": (
            "EVT nos conjuntos vertendo"
        ),
        "escopo": (
            "EVT nos conjuntos vertendo"
        ),
        "perimetro": (
            "Condicionado ao PLD"
        ),
        "ordem": 2,
    },
    "2A": {
        "coluna_curtailment": (
            "curtailment_2a_mwh"
        ),
        "coluna_corte": (
            "corte_2a_pct"
        ),
        "nome": (
            "Parque hidráulico completo · Nacional"
        ),
        "nome_curto": (
            "Parque hidráulico completo"
        ),
        "escopo": (
            "Parque hidráulico completo"
        ),
        "perimetro": "Pool nacional",
        "ordem": 3,
    },
    "2B": {
        "coluna_curtailment": (
            "curtailment_2b_mwh"
        ),
        "coluna_corte": (
            "corte_2b_pct"
        ),
        "nome": (
            "Parque hidráulico completo · PLD"
        ),
        "nome_curto": (
            "Parque hidráulico completo"
        ),
        "escopo": (
            "Parque hidráulico completo"
        ),
        "perimetro": (
            "Condicionado ao PLD"
        ),
        "ordem": 4,
    },
    "3A": {
        "coluna_curtailment": (
            "curtailment_3a_mwh"
        ),
        "coluna_corte": (
            "corte_3a_pct"
        ),
        "nome": "EOL + UFV · Nacional",
        "nome_curto": "EOL + UFV",
        "escopo": "EOL + UFV",
        "perimetro": "Pool nacional",
        "ordem": 5,
    },
    "3B": {
        "coluna_curtailment": (
            "curtailment_3b_mwh"
        ),
        "coluna_corte": (
            "corte_3b_pct"
        ),
        "nome": "EOL + UFV · PLD",
        "nome_curto": "EOL + UFV",
        "escopo": "EOL + UFV",
        "perimetro": (
            "Condicionado ao PLD"
        ),
        "ordem": 6,
    },
    "4A": {
        "coluna_curtailment": (
            "curtailment_4a_mwh"
        ),
        "coluna_corte": (
            "corte_4a_pct"
        ),
        "nome": (
            "Rateio por fonte · Nacional"
        ),
        "nome_curto": (
            "Rateio por fonte"
        ),
        "escopo": "Rateio por fonte",
        "perimetro": "Pool nacional",
        "ordem": 7,
    },
    "4B": {
        "coluna_curtailment": (
            "curtailment_4b_mwh"
        ),
        "coluna_corte": (
            "corte_4b_pct"
        ),
        "nome": (
            "Rateio por fonte · PLD"
        ),
        "nome_curto": (
            "Rateio por fonte"
        ),
        "escopo": "Rateio por fonte",
        "perimetro": (
            "Condicionado ao PLD"
        ),
        "ordem": 8,
    },
}

def validar_base_analise_cp45(
    df,
):
    """
    Valida a base horária de ativos com cenários.
    """

    if not isinstance(
        df,
        pd.DataFrame,
    ):
        raise TypeError(
            "df deve ser um DataFrame."
        )

    if df.empty:
        raise ValueError(
            "A base de cenários da CP45 está vazia."
        )

    colunas_obrigatorias = {
        "din_instante",
        "ativo",
        "subsistema",
        "fonte",
        "geracao_esperada_mwh",
    }

    for configuracao in (
        CENARIOS_CP45.values()
    ):
        colunas_obrigatorias.add(
            configuracao[
                "coluna_curtailment"
            ]
        )

    colunas_ausentes = (
        colunas_obrigatorias
        - set(
            df.columns
        )
    )

    if colunas_ausentes:
        raise ValueError(
            "A base de cenários não possui as "
            "colunas obrigatórias: "
            f"{sorted(colunas_ausentes)}."
        )

def obter_opcoes_filtros_cp45(
    df,
):
    """
    Retorna opções de usinas e limites temporais
    disponíveis na base da CP45.
    """

    validar_base_analise_cp45(
        df
    )

    base = df[
        [
            "din_instante",
            "ativo",
            "fonte",
            "subsistema",
        ]
    ].copy()

    base["din_instante"] = pd.to_datetime(
        base["din_instante"],
        errors="coerce",
    )

    base["ativo"] = (
        base["ativo"]
        .astype("string")
        .str.strip()
    )

    base = base.dropna(
        subset=[
            "din_instante",
            "ativo",
        ]
    ).copy()

    if base.empty:
        raise ValueError(
            "Não restaram registros válidos para "
            "obter as opções da CP45."
        )

    cadastro_usinas = (
        base[
            [
                "ativo",
                "fonte",
                "subsistema",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            [
                "ativo",
                "fonte",
                "subsistema",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    opcoes_usinas = (
        cadastro_usinas[
            "ativo"
        ]
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    data_minima = (
        base["din_instante"]
        .min()
    )

    data_maxima = (
        base["din_instante"]
        .max()
    )

    return {
        "usinas": opcoes_usinas,
        "cadastro_usinas": cadastro_usinas,
        "data_minima": data_minima,
        "data_maxima": data_maxima,
        "ano_minimo": int(
            data_minima.year
        ),
        "mes_inicial_disponivel": int(
            data_minima.month
        ),
        "ano_maximo": int(
            data_maxima.year
        ),
        "mes_final_disponivel": int(
            data_maxima.month
        ),
    }

def filtrar_base_cp45(
    df,
    ano_inicial,
    mes_inicial,
    ano_final,
    mes_final,
    usina_selecionada,
):
    """
    Filtra a base da CP45 por período mensal e usina.
    """

    validar_base_analise_cp45(
        df
    )

    base = df.copy()

    base["din_instante"] = pd.to_datetime(
        base["din_instante"],
        errors="coerce",
    )

    base["ativo"] = (
        base["ativo"]
        .astype("string")
        .str.strip()
    )

    data_inicial = pd.Timestamp(
        year=int(
            ano_inicial
        ),
        month=int(
            mes_inicial
        ),
        day=1,
    )

    data_final_exclusiva = (
        pd.Timestamp(
            year=int(
                ano_final
            ),
            month=int(
                mes_final
            ),
            day=1,
        )
        + pd.offsets.MonthBegin(
            1
        )
    )

    if data_inicial >= data_final_exclusiva:
        raise ValueError(
            "O período inicial não pode ser "
            "posterior ao período final."
        )

    usina_selecionada = str(
        usina_selecionada
    ).strip()

    if not usina_selecionada:
        raise ValueError(
            "A usina selecionada não pode ser vazia."
        )

    mascara = (
        (
            base["din_instante"]
            >= data_inicial
        )
        & (
            base["din_instante"]
            < data_final_exclusiva
        )
        & (
            base["ativo"]
            .eq(
                usina_selecionada
            )
        )
    )

    resultado = (
        base.loc[
            mascara
        ]
        .copy()
        .sort_values(
            "din_instante"
        )
        .reset_index(
            drop=True
        )
    )

    if resultado.empty:
        raise ValueError(
            "Não foram encontrados registros para "
            "a usina e o período selecionados."
        )

    return resultado

def resumir_cenarios_cp45(
    df_filtrado,
):
    """
    Consolida geração, curtailment e percentual de
    corte para o cenário atual e os oito cenários
    simulados.
    """

    validar_base_analise_cp45(
        df_filtrado
    )

    geracao_mwh = (
        pd.to_numeric(
            df_filtrado[
                "geracao_esperada_mwh"
            ],
            errors="coerce",
        )
        .fillna(0.0)
        .sum()
    )

    registros = []

    for codigo, configuracao in (
        CENARIOS_CP45.items()
    ):
        coluna_curtailment = (
            configuracao[
                "coluna_curtailment"
            ]
        )

        curtailment_mwh = (
            pd.to_numeric(
                df_filtrado[
                    coluna_curtailment
                ],
                errors="coerce",
            )
            .fillna(0.0)
            .sum()
        )

        corte_pct = (
            100
            * curtailment_mwh
            / geracao_mwh
            if geracao_mwh > 0
            else 0.0
        )

        registros.append(
            {
                "codigo": codigo,
                "cenario": (
                    configuracao[
                        "nome"
                    ]
                ),
                "cenario_curto": (
                    configuracao[
                        "nome_curto"
                    ]
                ),
                "escopo": (
                    configuracao[
                        "escopo"
                    ]
                ),
                "perimetro": (
                    configuracao[
                        "perimetro"
                    ]
                ),
                "ordem": int(
                    configuracao[
                        "ordem"
                    ]
                ),
                "geracao_esperada_gwh": (
                    geracao_mwh
                    / 1000
                ),
                "curtailment_gwh": (
                    curtailment_mwh
                    / 1000
                ),
                "corte_pct": (
                    corte_pct
                ),
            }
        )

    resumo = pd.DataFrame(
        registros
    )

    linha_atual = (
        resumo.loc[
            resumo["codigo"]
            .eq("Atual")
        ]
        .iloc[0]
    )

    resumo[
        "diferenca_atual_gwh"
    ] = (
        resumo[
            "curtailment_gwh"
        ]
        - linha_atual[
            "curtailment_gwh"
        ]
    )

    resumo[
        "diferenca_atual_pp"
    ] = (
        resumo[
            "corte_pct"
        ]
        - linha_atual[
            "corte_pct"
        ]
    )

    return (
        resumo
        .sort_values(
            "ordem"
        )
        .reset_index(
            drop=True
        )
    )

def obter_indicadores_cp45(
    df_filtrado,
):
    """
    Retorna os principais indicadores da análise CP45.
    """

    resumo = resumir_cenarios_cp45(
        df_filtrado
    )

    atual = (
        resumo.loc[
            resumo["codigo"]
            .eq("Atual")
        ]
        .iloc[0]
    )

    simulados = (
        resumo.loc[
            ~resumo["codigo"]
            .eq("Atual")
        ]
        .copy()
    )

    melhor = simulados.loc[
        simulados[
            "curtailment_gwh"
        ]
        .idxmin()
    ]

    pior = simulados.loc[
        simulados[
            "curtailment_gwh"
        ]
        .idxmax()
    ]

    primeira_linha = (
        df_filtrado
        .iloc[0]
    )

    return {
        "ativo": str(
            primeira_linha[
                "ativo"
            ]
        ),
        "fonte": str(
            primeira_linha[
                "fonte"
            ]
        ),
        "subsistema": str(
            primeira_linha[
                "subsistema"
            ]
        ),
        "geracao_esperada_gwh": float(
            atual[
                "geracao_esperada_gwh"
            ]
        ),
        "curtailment_atual_gwh": float(
            atual[
                "curtailment_gwh"
            ]
        ),
        "corte_atual_pct": float(
            atual[
                "corte_pct"
            ]
        ),
        "melhor_cenario_codigo": str(
            melhor[
                "codigo"
            ]
        ),
        "melhor_cenario": str(
            melhor[
                "cenario"
            ]
        ),
        "melhor_cenario_gwh": float(
            melhor[
                "curtailment_gwh"
            ]
        ),
        "melhor_corte_pct": float(
            melhor[
                "corte_pct"
            ]
        ),
        "melhor_diferenca_gwh": float(
            melhor[
                "diferenca_atual_gwh"
            ]
        ),
        "melhor_diferenca_pp": float(
            melhor[
                "diferenca_atual_pp"
            ]
        ),
        "pior_cenario_codigo": str(
            pior[
                "codigo"
            ]
        ),
        "pior_cenario": str(
            pior[
                "cenario"
            ]
        ),
        "pior_cenario_gwh": float(
            pior[
                "curtailment_gwh"
            ]
        ),
        "pior_corte_pct": float(
            pior[
                "corte_pct"
            ]
        ),
        "pior_diferenca_gwh": float(
            pior[
                "diferenca_atual_gwh"
            ]
        ),
        "pior_diferenca_pp": float(
            pior[
                "diferenca_atual_pp"
            ]
        ),
    }

def resumir_mensal_cp45(
    df_filtrado,
):
    """
    Consolida mensalmente o cenário atual e os oito
    cenários simulados.
    """

    validar_base_analise_cp45(
        df_filtrado
    )

    base = df_filtrado.copy()

    base["din_instante"] = pd.to_datetime(
        base["din_instante"],
        errors="coerce",
    )

    base["mes_referencia"] = (
        base["din_instante"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    registros = []

    for codigo, configuracao in (
        CENARIOS_CP45.items()
    ):
        resumo = (
            base
            .groupby(
                "mes_referencia",
                as_index=False,
                observed=True,
            )
            .agg(
                geracao_mwh=(
                    "geracao_esperada_mwh",
                    "sum",
                ),
                curtailment_mwh=(
                    configuracao[
                        "coluna_curtailment"
                    ],
                    "sum",
                ),
            )
        )

        resumo["codigo"] = codigo
        resumo["cenario"] = (
            configuracao[
                "nome"
            ]
        )
        resumo["cenario_curto"] = (
            configuracao[
                "nome_curto"
            ]
        )
        resumo["perimetro"] = (
            configuracao[
                "perimetro"
            ]
        )
        resumo["ordem"] = int(
            configuracao[
                "ordem"
            ]
        )

        registros.append(
            resumo
        )

    resultado = pd.concat(
        registros,
        ignore_index=True,
    )

    resultado[
        "geracao_esperada_gwh"
    ] = (
        resultado[
            "geracao_mwh"
        ]
        / 1000
    )

    resultado[
        "curtailment_gwh"
    ] = (
        resultado[
            "curtailment_mwh"
        ]
        / 1000
    )

    resultado["corte_pct"] = np.where(
        resultado[
            "geracao_mwh"
        ] > 0,
        (
            100
            * resultado[
                "curtailment_mwh"
            ]
            / resultado[
                "geracao_mwh"
            ]
        ),
        0.0,
    )

    atual = (
        resultado.loc[
            resultado[
                "codigo"
            ].eq("Atual"),
            [
                "mes_referencia",
                "curtailment_gwh",
                "corte_pct",
            ],
        ]
        .rename(
            columns={
                "curtailment_gwh": (
                    "curtailment_atual_gwh"
                ),
                "corte_pct": (
                    "corte_atual_pct"
                ),
            }
        )
    )

    resultado = resultado.merge(
        atual,
        on="mes_referencia",
        how="left",
        validate="many_to_one",
    )

    resultado[
        "diferenca_atual_gwh"
    ] = (
        resultado[
            "curtailment_gwh"
        ]
        - resultado[
            "curtailment_atual_gwh"
        ]
    )

    resultado[
        "diferenca_atual_pp"
    ] = (
        resultado[
            "corte_pct"
        ]
        - resultado[
            "corte_atual_pct"
        ]
    )

    resultado["mes_rotulo"] = (
        resultado[
            "mes_referencia"
        ]
        .dt.strftime(
            "%m/%Y"
        )
    )

    return (
        resultado
        .sort_values(
            [
                "mes_referencia",
                "ordem",
            ]
        )
        .reset_index(
            drop=True
        )
    )

def preparar_analise_individual_cp45(
    df,
    ano_inicial,
    mes_inicial,
    ano_final,
    mes_final,
    usina_selecionada,
):
    """
    Prepara a análise completa da CP45 para uma usina
    e um período selecionados.

    A função:

    1. filtra a base horária por período e usina;
    2. identifica a fonte e o subsistema da usina;
    3. consolida o cenário atual e os cenários 1A a 4B;
    4. calcula os principais indicadores;
    5. prepara a análise mensal;
    6. cria um diagnóstico da seleção.

    Parâmetros
    ----------
    df : pandas.DataFrame
        Base horária de ativos produzida por
        montar_base_cenarios_cp45().

    ano_inicial : int
        Ano inicial da análise.

    mes_inicial : int
        Mês inicial da análise.

    ano_final : int
        Ano final da análise.

    mes_final : int
        Mês final da análise.

    usina_selecionada : str
        Nome da usina selecionada.

    Retorno
    -------
    dict
        Dicionário contendo a base horária filtrada,
        resumo dos cenários, indicadores, base mensal
        e diagnóstico.
    """

    # ========================================================
    # FILTRO
    # ========================================================

    base_filtrada = filtrar_base_cp45(
        df=df,
        ano_inicial=ano_inicial,
        mes_inicial=mes_inicial,
        ano_final=ano_final,
        mes_final=mes_final,
        usina_selecionada=(
            usina_selecionada
        ),
    )

    # ========================================================
    # VALIDAÇÃO CADASTRAL DA USINA
    # ========================================================

    cadastro_usina = (
        base_filtrada[
            [
                "ativo",
                "fonte",
                "subsistema",
            ]
        ]
        .drop_duplicates()
        .reset_index(
            drop=True
        )
    )

    if len(cadastro_usina) != 1:
        raise ValueError(
            "A usina selecionada possui mais de uma "
            "combinação de fonte e subsistema no período: "
            f"{cadastro_usina.to_dict(orient='records')}."
        )

    ativo = str(
        cadastro_usina.loc[
            0,
            "ativo",
        ]
    )

    fonte = str(
        cadastro_usina.loc[
            0,
            "fonte",
        ]
    )

    subsistema = str(
        cadastro_usina.loc[
            0,
            "subsistema",
        ]
    )

    # ========================================================
    # RESUMOS E INDICADORES
    # ========================================================

    resumo_cenarios = resumir_cenarios_cp45(
        base_filtrada
    )

    indicadores = obter_indicadores_cp45(
        base_filtrada
    )

    resumo_mensal = resumir_mensal_cp45(
        base_filtrada
    )

    # ========================================================
    # DIAGNÓSTICO
    # ========================================================

    colunas_cenarios = [
        configuracao[
            "coluna_curtailment"
        ]
        for configuracao
        in CENARIOS_CP45.values()
    ]

    quantidade_nulos = int(
        base_filtrada[
            [
                "geracao_esperada_mwh",
                *colunas_cenarios,
            ]
        ]
        .isna()
        .sum()
        .sum()
    )

    quantidade_infinitos = int(
        np.isinf(
            base_filtrada[
                [
                    "geracao_esperada_mwh",
                    *colunas_cenarios,
                ]
            ]
            .to_numpy(
                dtype=float
            )
        )
        .sum()
    )

    duplicidades_horarias = int(
        base_filtrada
        .duplicated(
            subset=[
                "din_instante",
                "ativo",
                "subsistema",
                "fonte",
            ]
        )
        .sum()
    )

    data_minima = (
        base_filtrada[
            "din_instante"
        ]
        .min()
    )

    data_maxima = (
        base_filtrada[
            "din_instante"
        ]
        .max()
    )

    horas_esperadas = int(
        (
            data_maxima.floor("h")
            - data_minima.floor("h")
        )
        / pd.Timedelta(
            hours=1
        )
        + 1
    )

    quantidade_horas = int(
        base_filtrada[
            "din_instante"
        ]
        .nunique()
    )

    horas_ausentes = max(
        horas_esperadas
        - quantidade_horas,
        0,
    )

    diagnostico = {
        "ativo": ativo,
        "fonte": fonte,
        "subsistema": subsistema,
        "data_inicial": data_minima,
        "data_final": data_maxima,
        "quantidade_linhas": int(
            len(
                base_filtrada
            )
        ),
        "quantidade_horas": (
            quantidade_horas
        ),
        "horas_esperadas": (
            horas_esperadas
        ),
        "horas_ausentes": (
            horas_ausentes
        ),
        "quantidade_meses": int(
            resumo_mensal[
                "mes_referencia"
            ]
            .nunique()
        ),
        "quantidade_cenarios": int(
            resumo_cenarios[
                "codigo"
            ]
            .nunique()
        ),
        "duplicidades_horarias": (
            duplicidades_horarias
        ),
        "quantidade_nulos": (
            quantidade_nulos
        ),
        "quantidade_infinitos": (
            quantidade_infinitos
        ),
    }

    problemas = {
        chave: valor
        for chave, valor in {
            "duplicidades_horarias": (
                duplicidades_horarias
            ),
            "quantidade_nulos": (
                quantidade_nulos
            ),
            "quantidade_infinitos": (
                quantidade_infinitos
            ),
        }.items()
        if valor > 0
    }

    if problemas:
        raise ValueError(
            "A análise individual da CP45 apresentou "
            "problemas de consistência: "
            f"{problemas}."
        )

    return {
        "ativo": ativo,
        "fonte": fonte,
        "subsistema": subsistema,
        "periodo_inicial": data_minima,
        "periodo_final": data_maxima,
        "base_horaria": base_filtrada,
        "resumo_cenarios": resumo_cenarios,
        "indicadores": indicadores,
        "resumo_mensal": resumo_mensal,
        "diagnostico": diagnostico,
    }
