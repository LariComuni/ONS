"""
Funções analíticas para a página de subsistemas.

O módulo prepara KPIs, tabelas e bases agregadas para
as análises dos subsistemas Norte, Nordeste,
Sudeste/Centro-Oeste e Sul.
"""

import pandas as pd


ROTULOS_TIPO_CURTAILMENT = {
    "ENE": "Energético",
    "REL": "Elétrico",
    "CNF": "Confiabilidade",
    "SEM_CODIGO": "Sem classificação",
}


ROTULOS_SUBSISTEMAS = {
    "N": "Norte",
    "NE": "Nordeste",
    "SE": "Sudeste/Centro-Oeste",
    "SE/CO": "Sudeste/Centro-Oeste",
    "S": "Sul",
}


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

def calcular_kpis_curtailment(
    df,
):
    """
    Calcula os principais KPIs de curtailment.

    Os registros da base do ONS representam intervalos
    de 30 minutos. Por isso, a conversão de MW para MWh
    utiliza o fator fixo de 0.5.

    Parâmetros
    ----------
    df : pandas.DataFrame
        Base calculada de curtailment EOL e UFV.

    Retorno
    -------
    dict
        Dicionário com Corte Médio, Subsistema Crítico,
        Tipo Predominante e Mês Crítico.
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
            "A base informada está vazia."
        )

    colunas_obrigatorias = {
        "din_instante",
        "id_subsistema",
        "val_curtailment",
        "val_geracao_esperada",
        "cod_razaorestricao",
    }

    colunas_ausentes = (
        colunas_obrigatorias
        - set(df.columns)
    )

    if colunas_ausentes:
        raise ValueError(
            "A base não possui as colunas obrigatórias: "
            f"{sorted(colunas_ausentes)}."
        )

    df_aux = df.copy()

    # ========================================================
    # TRATAMENTO DOS DADOS
    # ========================================================

    df_aux["din_instante"] = pd.to_datetime(
        df_aux["din_instante"],
        errors="coerce",
    )

    df_aux["val_curtailment"] = pd.to_numeric(
        df_aux["val_curtailment"],
        errors="coerce",
    )

    df_aux["val_geracao_esperada"] = pd.to_numeric(
        df_aux["val_geracao_esperada"],
        errors="coerce",
    )

    df_aux = df_aux.dropna(
        subset=[
            "din_instante",
            "id_subsistema",
            "val_curtailment",
            "val_geracao_esperada",
        ]
    ).copy()

    if df_aux.empty:
        raise ValueError(
            "Não restaram registros válidos após "
            "o tratamento da base."
        )

    df_aux["mes"] = (
        df_aux["din_instante"]
        .dt.to_period("M")
    )

    df_aux["tipo_curtailment"] = (
        df_aux["cod_razaorestricao"]
        .astype("string")
        .str.strip()
        .str.upper()
        .fillna("SEM_CODIGO")
        .replace(
            "",
            "SEM_CODIGO",
        )
    )

    # Cada registro representa 30 minutos.
    # MW multiplicado por 0.5 hora resulta em MWh.

    df_aux["curtailment_mwh"] = (
        df_aux["val_curtailment"]
        .clip(lower=0)
        * 0.5
    )

    df_aux["geracao_esperada_mwh"] = (
        df_aux["val_geracao_esperada"]
        .clip(lower=0)
        * 0.5
    )

    # ========================================================
    # CORTE MÉDIO DO PERÍODO
    # ========================================================

    curtailment_total_mwh = (
        df_aux["curtailment_mwh"].sum()
    )

    geracao_esperada_total_mwh = (
        df_aux["geracao_esperada_mwh"].sum()
    )

    if geracao_esperada_total_mwh > 0:
        corte_medio_pct = (
            100
            * curtailment_total_mwh
            / geracao_esperada_total_mwh
        )
    else:
        corte_medio_pct = None

    # ========================================================
    # SUBSISTEMA CRÍTICO
    # ========================================================

    corte_subsistema = (
        df_aux
        .groupby(
            "id_subsistema",
            observed=True,
        )
        .agg(
            curtailment_mwh=(
                "curtailment_mwh",
                "sum",
            ),
            geracao_esperada_mwh=(
                "geracao_esperada_mwh",
                "sum",
            ),
        )
        .reset_index()
    )

    corte_subsistema = corte_subsistema[
        corte_subsistema[
            "geracao_esperada_mwh"
        ] > 0
    ].copy()

    corte_subsistema["corte_pct"] = (
        100
        * corte_subsistema["curtailment_mwh"]
        / corte_subsistema["geracao_esperada_mwh"]
    )

    if corte_subsistema.empty:
        subsistema_critico = None
        nome_subsistema_critico = "Não disponível"
        corte_subsistema_critico_pct = None

    else:
        linha_subsistema_critico = (
            corte_subsistema.loc[
                corte_subsistema[
                    "corte_pct"
                ].idxmax()
            ]
        )

        subsistema_critico = (
            linha_subsistema_critico[
                "id_subsistema"
            ]
        )

        nome_subsistema_critico = (
            ROTULOS_SUBSISTEMAS.get(
                subsistema_critico,
                subsistema_critico,
            )
        )

        corte_subsistema_critico_pct = (
            linha_subsistema_critico[
                "corte_pct"
            ]
        )

    # ========================================================
    # TIPO PREDOMINANTE
    # ========================================================

    curtailment_tipo = (
        df_aux
        .groupby(
            "tipo_curtailment",
            observed=True,
        )["curtailment_mwh"]
        .sum()
    )

    curtailment_tipo = curtailment_tipo[
        curtailment_tipo > 0
    ]

    if curtailment_tipo.empty:
        codigo_tipo_predominante = None
        tipo_predominante = "Não disponível"
        participacao_tipo_predominante_pct = None

    else:
        codigo_tipo_predominante = (
            curtailment_tipo.idxmax()
        )

        tipo_predominante = (
            ROTULOS_TIPO_CURTAILMENT.get(
                codigo_tipo_predominante,
                codigo_tipo_predominante,
            )
        )

        if curtailment_tipo.sum() > 0:
            participacao_tipo_predominante_pct = (
                100
                * curtailment_tipo.loc[
                    codigo_tipo_predominante
                ]
                / curtailment_tipo.sum()
            )
        else:
            participacao_tipo_predominante_pct = None

    # ========================================================
    # MÊS CRÍTICO
    # ========================================================

    corte_mes = (
        df_aux
        .groupby(
            "mes",
            observed=True,
        )
        .agg(
            curtailment_mwh=(
                "curtailment_mwh",
                "sum",
            ),
            geracao_esperada_mwh=(
                "geracao_esperada_mwh",
                "sum",
            ),
        )
        .reset_index()
    )

    corte_mes = corte_mes[
        corte_mes[
            "geracao_esperada_mwh"
        ] > 0
    ].copy()

    corte_mes["corte_pct"] = (
        100
        * corte_mes["curtailment_mwh"]
        / corte_mes["geracao_esperada_mwh"]
    )

    if corte_mes.empty:
        mes_critico = None
        rotulo_mes_critico = "Não disponível"
        corte_mes_critico_pct = None

    else:
        linha_mes_critico = corte_mes.loc[
            corte_mes[
                "corte_pct"
            ].idxmax()
        ]

        mes_critico_periodo = (
            linha_mes_critico[
                "mes"
            ]
        )

        mes_critico = (
            mes_critico_periodo
            .to_timestamp()
            .strftime("%m/%Y")
        )

        rotulo_mes_critico = (
            f"{NOMES_MESES[mes_critico_periodo.month]} "
            f"de {mes_critico_periodo.year}"
        )

        corte_mes_critico_pct = (
            linha_mes_critico[
                "corte_pct"
            ]
        )

    # ========================================================
    # RETORNO
    # ========================================================

    return {
    "Corte Médio (%)": (
        round(
            corte_medio_pct,
            2,
        )
        if corte_medio_pct is not None
        else None
    ),
    "Subsistema Crítico": (
        subsistema_critico
    ),
    "Nome do Subsistema Crítico": (
        nome_subsistema_critico
    ),
    "Corte do Subsistema Crítico (%)": (
        round(
            corte_subsistema_critico_pct,
            2,
        )
        if corte_subsistema_critico_pct
        is not None
        else None
    ),
    "Tipo Predominante": (
        tipo_predominante
    ),
    "Código do Tipo Predominante": (
        codigo_tipo_predominante
    ),
    "Participação do Tipo Predominante (%)": (
        round(
            participacao_tipo_predominante_pct,
            2,
        )
        if participacao_tipo_predominante_pct
        is not None
        else None
    ),
    "Mês Crítico": (
        mes_critico
    ),
    "Rótulo do Mês Crítico": (
        rotulo_mes_critico
    ),
    "Corte no Mês Crítico (%)": (
        round(
            corte_mes_critico_pct,
            2,
        )
        if corte_mes_critico_pct is not None
        else None
    ),
}


def preparar_curtailment_mensal_subsistemas(
    df,
    tipo_curtailment,
):
    """
    Prepara o curtailment mensal por subsistema.

    Os registros do ONS representam intervalos de 30 minutos.
    Portanto, a conversão utiliza:

    MW * 0.5 = MWh
    MWh / 1000 = GWh

    Parâmetros
    ----------
    df : pandas.DataFrame
        Base calculada de curtailment.
    tipo_curtailment : str
        Código do tipo de curtailment. São aceitos:
        ENE, REL, CNF ou TODOS.

    Retorno
    -------
    pandas.DataFrame
        Base mensal no formato longo, com mês, subsistema
        e curtailment em GWh.
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
            "A base informada está vazia."
        )

    colunas_obrigatorias = {
        "din_instante",
        "id_subsistema",
        "cod_razaorestricao",
        "val_curtailment",
    }

    colunas_ausentes = (
        colunas_obrigatorias
        - set(df.columns)
    )

    if colunas_ausentes:
        raise ValueError(
            "A base não possui as colunas obrigatórias: "
            f"{sorted(colunas_ausentes)}."
        )

    tipo_normalizado = (
        str(tipo_curtailment)
        .strip()
        .upper()
    )

    tipos_permitidos = {
        "TODOS",
        "ENE",
        "REL",
        "CNF",
    }

    if tipo_normalizado not in tipos_permitidos:
        raise ValueError(
            "O tipo de curtailment deve ser TODOS, "
            "ENE, REL ou CNF."
        )

    df_aux = df.copy()

    df_aux["din_instante"] = pd.to_datetime(
        df_aux["din_instante"],
        errors="coerce",
    )

    df_aux["val_curtailment"] = pd.to_numeric(
        df_aux["val_curtailment"],
        errors="coerce",
    )

    df_aux["tipo_curtailment"] = (
        df_aux["cod_razaorestricao"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    df_aux = df_aux.dropna(
        subset=[
            "din_instante",
            "id_subsistema",
            "val_curtailment",
        ]
    ).copy()

    if tipo_normalizado != "TODOS":
        df_aux = df_aux[
            df_aux["tipo_curtailment"]
            == tipo_normalizado
        ].copy()

    if df_aux.empty:
        raise ValueError(
            "Não foram encontrados registros para "
            "o tipo de curtailment selecionado."
        )

    df_aux["mes"] = (
        df_aux["din_instante"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    df_aux["curtailment_gwh"] = (
        df_aux["val_curtailment"]
        .clip(lower=0)
        * 0.5
        / 1000
    )

    base_mensal = (
        df_aux
        .groupby(
            [
                "mes",
                "id_subsistema",
            ],
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

    base_mensal["id_subsistema"] = (
        base_mensal["id_subsistema"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    ordem_subsistemas = {
        "N": 1,
        "NE": 2,
        "SE": 3,
        "SE/CO": 3,
        "S": 4,
    }

    base_mensal["ordem_subsistema"] = (
        base_mensal["id_subsistema"]
        .map(
            ordem_subsistemas
        )
        .fillna(99)
    )

    base_mensal = (
        base_mensal
        .sort_values(
            [
                "mes",
                "ordem_subsistema",
            ]
        )
        .drop(
            columns="ordem_subsistema"
        )
        .reset_index(
            drop=True
        )
    )

    return base_mensal

def preparar_perfil_horario_curtailment(
    df,
    tipo_curtailment,
):
    """
    Prepara o perfil horário médio de curtailment
    por subsistema.

    Parâmetros
    ----------
    df : pandas.DataFrame
        Base calculada de curtailment.
    tipo_curtailment : str
        Tipo considerado na análise. São aceitos:
        TODOS, ENE, REL e CNF.

    Retorno
    -------
    pandas.DataFrame
        Tabela com subsistemas nas linhas, horas nas
        colunas e curtailment médio em MW nos valores.
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
            "A base informada está vazia."
        )

    colunas_obrigatorias = {
        "din_instante",
        "id_subsistema",
        "cod_razaorestricao",
        "val_curtailment",
    }

    colunas_ausentes = (
        colunas_obrigatorias
        - set(df.columns)
    )

    if colunas_ausentes:
        raise ValueError(
            "A base não possui as colunas obrigatórias: "
            f"{sorted(colunas_ausentes)}."
        )

    tipo_normalizado = (
        str(tipo_curtailment)
        .strip()
        .upper()
    )

    tipos_permitidos = {
        "TODOS",
        "ENE",
        "REL",
        "CNF",
    }

    if tipo_normalizado not in tipos_permitidos:
        raise ValueError(
            "O tipo de curtailment deve ser TODOS, "
            "ENE, REL ou CNF."
        )

    df_aux = df.copy()

    df_aux["din_instante"] = pd.to_datetime(
        df_aux["din_instante"],
        errors="coerce",
    )

    df_aux["val_curtailment"] = pd.to_numeric(
        df_aux["val_curtailment"],
        errors="coerce",
    )

    df_aux["tipo_curtailment"] = (
        df_aux["cod_razaorestricao"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    df_aux["id_subsistema"] = (
        df_aux["id_subsistema"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    df_aux = df_aux.dropna(
        subset=[
            "din_instante",
            "id_subsistema",
            "val_curtailment",
        ]
    ).copy()

    if tipo_normalizado != "TODOS":
        df_aux = df_aux[
            df_aux["tipo_curtailment"]
            == tipo_normalizado
        ].copy()

    ordem_subsistemas = [
        "N",
        "NE",
        "SE",
        "S",
    ]

    if df_aux.empty:
        return pd.DataFrame(
            0.0,
            index=ordem_subsistemas,
            columns=range(24),
        )

    df_aux["hora"] = (
        df_aux["din_instante"]
        .dt.hour
    )

    tabela_horaria = (
        df_aux
        .groupby(
            [
                "id_subsistema",
                "hora",
            ],
            observed=True,
        )["val_curtailment"]
        .mean()
        .unstack(
            fill_value=0.0
        )
    )

    tabela_horaria = tabela_horaria.reindex(
        index=ordem_subsistemas,
        fill_value=0.0,
    )

    tabela_horaria = tabela_horaria.reindex(
        columns=range(24),
        fill_value=0.0,
    )

    tabela_horaria.index.name = (
        "id_subsistema"
    )

    tabela_horaria.columns.name = (
        "hora"
    )

    return tabela_horaria
