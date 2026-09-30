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

def preparar_download_curtailment_mensal(
    df,
):
    """
    Prepara os dados mensais de curtailment por subsistema
    e tipo para exportação.

    Os registros representam intervalos de 30 minutos.
    A conversão utilizada é:

    MW * 0.5 / 1000 = GWh

    Parâmetros
    ----------
    df : pandas.DataFrame
        Base calculada de curtailment.

    Retorno
    -------
    pandas.DataFrame
        Tabela mensal com colunas separadas para ENE,
        REL e CNF.
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

    df_aux = df.copy()

    df_aux["din_instante"] = pd.to_datetime(
        df_aux["din_instante"],
        errors="coerce",
    )

    df_aux["val_curtailment"] = pd.to_numeric(
        df_aux["val_curtailment"],
        errors="coerce",
    )

    df_aux["id_subsistema"] = (
        df_aux["id_subsistema"]
        .astype("string")
        .str.strip()
        .str.upper()
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

    df_aux = df_aux[
        df_aux["tipo_curtailment"]
        .isin(
            [
                "ENE",
                "REL",
                "CNF",
            ]
        )
    ].copy()

    if df_aux.empty:
        raise ValueError(
            "Não foram encontrados registros ENE, REL ou CNF."
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

    base_agrupada = (
        df_aux
        .groupby(
            [
                "mes",
                "id_subsistema",
                "tipo_curtailment",
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

    tabela_download = (
        base_agrupada
        .pivot_table(
            index=[
                "mes",
                "id_subsistema",
            ],
            columns="tipo_curtailment",
            values="curtailment_gwh",
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
        if codigo not in tabela_download.columns:
            tabela_download[codigo] = 0.0
    
    tabela_download["TODOS"] = (tabela_download["ENE"] + tabela_download["REL"] + tabela_download["CNF"])

    ordem_subsistemas = {
        "N": 1,
        "NE": 2,
        "SE": 3,
        "S": 4,
    }

    tabela_download["ordem_subsistema"] = (
        tabela_download["id_subsistema"]
        .map(
            ordem_subsistemas
        )
        .fillna(99)
    )

    tabela_download = (
        tabela_download
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

    tabela_download["Mês"] = (
        tabela_download["mes"]
        .dt.strftime("%m/%Y")
    )

    tabela_download = tabela_download.rename(
        columns={
            "id_subsistema": "Subsistema",
            "ENE": "Curtailment ENE (GWh)",
            "REL": "Curtailment REL (GWh)",
            "CNF": "Curtailment CNF (GWh)",
            "TODOS": "Curtailment Todos (GWh)",
        }
    )

    tabela_download = tabela_download[
        [
            "Mês",
            "Subsistema",
            "Curtailment ENE (GWh)",
            "Curtailment REL (GWh)",
            "Curtailment CNF (GWh)",
            "Curtailment Todos (GWh)",
        ]
    ]

    return tabela_download

def preparar_perfil_horario_curtailment(
    df,
    tipo_curtailment,
):
    """
    Prepara o perfil horário médio de curtailment
    por subsistema.

    O curtailment é agregado por instante e tipo antes
    do cálculo da média horária.
    """

    tipo_normalizado = (
        str(tipo_curtailment)
        .strip()
        .upper()
    )

    colunas_tipos = {
        "ENE": "Curtailment ENE médio (MW)",
        "REL": "Curtailment REL médio (MW)",
        "CNF": "Curtailment CNF médio (MW)",
        "TODOS": "Curtailment Todos médio (MW)",
    }

    if tipo_normalizado not in colunas_tipos:
        raise ValueError(
            "O tipo de curtailment deve ser TODOS, "
            "ENE, REL ou CNF."
        )

    base_horaria = (
        preparar_download_perfil_horario(
            df
        )
    )

    coluna_valor = colunas_tipos[
        tipo_normalizado
    ]

    base_horaria["hora_numero"] = (
        base_horaria["Hora"]
        .str.slice(
            0,
            2,
        )
        .astype(int)
    )

    tabela_horaria = (
        base_horaria
        .pivot(
            index="Subsistema",
            columns="hora_numero",
            values=coluna_valor,
        )
        .reindex(
            index=[
                "N",
                "NE",
                "SE",
                "S",
            ],
            columns=range(24),
            fill_value=0.0,
        )
    )

    tabela_horaria.index.name = (
        "id_subsistema"
    )

    tabela_horaria.columns.name = (
        "hora"
    )

    return tabela_horaria

def preparar_download_perfil_horario(
    df,
):
    """
    Prepara o perfil horário médio de curtailment
    por subsistema e tipo para exportação.

    Primeiro, o curtailment é agregado por instante,
    subsistema e tipo. Depois, calcula-se a potência
    média em MW para cada hora do dia.

    Retorno
    -------
    pandas.DataFrame
        Tabela com uma linha por subsistema e hora,
        contendo ENE, REL, CNF e Todos em MW médio.
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

    df_aux = df.copy()

    df_aux["din_instante"] = pd.to_datetime(
        df_aux["din_instante"],
        errors="coerce",
    )

    df_aux["val_curtailment"] = pd.to_numeric(
        df_aux["val_curtailment"],
        errors="coerce",
    )

    df_aux["id_subsistema"] = (
        df_aux["id_subsistema"]
        .astype("string")
        .str.strip()
        .str.upper()
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

    tipos_permitidos = [
        "ENE",
        "REL",
        "CNF",
    ]

    df_aux = df_aux[
        df_aux["tipo_curtailment"]
        .isin(
            tipos_permitidos
        )
    ].copy()

    if df_aux.empty:
        raise ValueError(
            "Não foram encontrados registros "
            "ENE, REL ou CNF."
        )

    df_aux["val_curtailment"] = (
        df_aux["val_curtailment"]
        .clip(lower=0)
    )

    # Soma as usinas em cada instante,
    # subsistema e tipo de restrição.

    base_instante_tipo = (
        df_aux
        .groupby(
            [
                "din_instante",
                "id_subsistema",
                "tipo_curtailment",
            ],
            as_index=False,
            observed=True,
        )
        .agg(
            curtailment_mw=(
                "val_curtailment",
                "sum",
            )
        )
    )

    # Transforma os tipos em colunas.

    base_instante = (
        base_instante_tipo
        .pivot_table(
            index=[
                "din_instante",
                "id_subsistema",
            ],
            columns="tipo_curtailment",
            values="curtailment_mw",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
    )

    for codigo in tipos_permitidos:
        if codigo not in base_instante.columns:
            base_instante[codigo] = 0.0

    base_instante["TODOS"] = (
        base_instante["ENE"]
        + base_instante["REL"]
        + base_instante["CNF"]
    )

    base_instante["hora"] = (
        base_instante["din_instante"]
        .dt.hour
    )

    # Média da potência agregada em cada hora do dia.

    perfil_horario = (
        base_instante
        .groupby(
            [
                "id_subsistema",
                "hora",
            ],
            as_index=False,
            observed=True,
        )
        .agg(
            ENE=(
                "ENE",
                "mean",
            ),
            REL=(
                "REL",
                "mean",
            ),
            CNF=(
                "CNF",
                "mean",
            ),
            TODOS=(
                "TODOS",
                "mean",
            ),
        )
    )

    ordem_subsistemas = [
        "N",
        "NE",
        "SE",
        "S",
    ]

    indice_completo = pd.MultiIndex.from_product(
        [
            ordem_subsistemas,
            range(24),
        ],
        names=[
            "id_subsistema",
            "hora",
        ],
    )

    perfil_horario = (
        perfil_horario
        .set_index(
            [
                "id_subsistema",
                "hora",
            ]
        )
        .reindex(
            indice_completo,
            fill_value=0.0,
        )
        .reset_index()
    )

    perfil_horario = perfil_horario.rename(
        columns={
            "id_subsistema": "Subsistema",
            "hora": "Hora",
            "ENE": "Curtailment ENE médio (MW)",
            "REL": "Curtailment REL médio (MW)",
            "CNF": "Curtailment CNF médio (MW)",
            "TODOS": "Curtailment Todos médio (MW)",
        }
    )

    perfil_horario["Hora"] = (
        perfil_horario["Hora"]
        .map(
            lambda hora: (
                f"{int(hora):02d}:00"
            )
        )
    )

    return perfil_horario

def preparar_corte_subsistema_tipo(
    df,
):
    """
    Prepara o corte percentual por subsistema e tipo
    de curtailment.

    Para cada subsistema, o curtailment de cada tipo
    é dividido pela geração esperada total do subsistema.

    Os registros representam intervalos de 30 minutos.
    Por isso, a conversão de MW para MWh utiliza 0.5.

    Parâmetros
    ----------
    df : pandas.DataFrame
        Base calculada de curtailment.

    Retorno
    -------
    pandas.DataFrame
        Base com subsistema, tipo de curtailment,
        curtailment em MWh, geração esperada em MWh
        e corte percentual.
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
        "id_subsistema",
        "cod_razaorestricao",
        "val_curtailment",
        "val_geracao_esperada",
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

    df_aux["id_subsistema"] = (
        df_aux["id_subsistema"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    df_aux["tipo_curtailment"] = (
        df_aux["cod_razaorestricao"]
        .astype("string")
        .str.strip()
        .str.upper()
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
            "id_subsistema",
            "tipo_curtailment",
            "val_curtailment",
            "val_geracao_esperada",
        ]
    ).copy()

    tipos_permitidos = [
        "ENE",
        "REL",
        "CNF",
    ]

    df_aux = df_aux[
        df_aux["tipo_curtailment"]
        .isin(
            tipos_permitidos
        )
    ].copy()

    if df_aux.empty:
        raise ValueError(
            "Não foram encontrados registros dos tipos "
            "ENE, REL ou CNF."
        )

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

    # Curtailment por subsistema e tipo.

    curtailment_tipo = (
        df_aux
        .groupby(
            [
                "id_subsistema",
                "tipo_curtailment",
            ],
            as_index=False,
            observed=True,
        )
        .agg(
            curtailment_mwh=(
                "curtailment_mwh",
                "sum",
            )
        )
    )

    # Geração esperada total por subsistema.
    # O denominador é o mesmo para todos os tipos.

    geracao_subsistema = (
        df_aux
        .groupby(
            "id_subsistema",
            as_index=False,
            observed=True,
        )
        .agg(
            geracao_esperada_mwh=(
                "geracao_esperada_mwh",
                "sum",
            )
        )
    )

    tabela = curtailment_tipo.merge(
        geracao_subsistema,
        on="id_subsistema",
        how="left",
        validate="many_to_one",
    )

    tabela["corte_pct"] = 0.0

    mascara_geracao_positiva = (
        tabela["geracao_esperada_mwh"] > 0
    )

    tabela.loc[
        mascara_geracao_positiva,
        "corte_pct",
    ] = (
        100
        * tabela.loc[
            mascara_geracao_positiva,
            "curtailment_mwh",
        ]
        / tabela.loc[
            mascara_geracao_positiva,
            "geracao_esperada_mwh",
        ]
    )

    # Completa todas as combinações entre
    # subsistemas e tipos com zero.

    ordem_subsistemas = [
        "N",
        "NE",
        "SE",
        "S",
    ]

    indice_completo = pd.MultiIndex.from_product(
        [
            ordem_subsistemas,
            tipos_permitidos,
        ],
        names=[
            "id_subsistema",
            "tipo_curtailment",
        ],
    )

    tabela = (
        tabela
        .set_index(
            [
                "id_subsistema",
                "tipo_curtailment",
            ]
        )
        .reindex(
            indice_completo,
        )
        .reset_index()
    )

    tabela["curtailment_mwh"] = (
        tabela["curtailment_mwh"]
        .fillna(0.0)
    )

    tabela["corte_pct"] = (
        tabela["corte_pct"]
        .fillna(0.0)
    )

    geracao_por_subsistema = (
        geracao_subsistema
        .set_index(
            "id_subsistema"
        )[
            "geracao_esperada_mwh"
        ]
    )

    tabela["geracao_esperada_mwh"] = (
        tabela[
            "id_subsistema"
        ]
        .map(
            geracao_por_subsistema
        )
        .fillna(0.0)
    )

    rotulos_tipos = {
        "ENE": "Energético",
        "REL": "Elétrico",
        "CNF": "Confiabilidade",
    }

    tabela["tipo_rotulo"] = (
        tabela["tipo_curtailment"]
        .map(
            rotulos_tipos
        )
    )

    tabela["ordem_subsistema"] = (
        tabela["id_subsistema"]
        .map(
            {
                "N": 1,
                "NE": 2,
                "SE": 3,
                "S": 4,
            }
        )
    )

    tabela["ordem_tipo"] = (
        tabela["tipo_curtailment"]
        .map(
            {
                "ENE": 1,
                "REL": 2,
                "CNF": 3,
            }
        )
    )

    tabela = (
        tabela
        .sort_values(
            [
                "ordem_subsistema",
                "ordem_tipo",
            ]
        )
        .drop(
            columns=[
                "ordem_subsistema",
                "ordem_tipo",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return tabela

def preparar_resumo_subsistemas(
    df,
):
    """
    Prepara a tabela de resumo da análise por subsistema.

    Os registros representam intervalos de 30 minutos.
    Por isso, a conversão de MW para MWh utiliza o fator 0.5.

    Parâmetros
    ----------
    df : pandas.DataFrame
        Base calculada de curtailment.

    Retorno
    -------
    pandas.DataFrame
        Tabela com os principais indicadores por subsistema.
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
        "val_geracao_esperada",
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

    df_aux["id_subsistema"] = (
        df_aux["id_subsistema"]
        .astype("string")
        .str.strip()
        .str.upper()
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
            "Não restaram registros válidos após o "
            "tratamento da base."
        )

    df_aux["mes"] = (
        df_aux["din_instante"]
        .dt.to_period("M")
    )

    df_aux["hora"] = (
        df_aux["din_instante"]
        .dt.hour
    )

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

    curtailment_total_mwh = (
        df_aux["curtailment_mwh"]
        .sum()
    )

    ordem_subsistemas = [
        "N",
        "NE",
        "SE",
        "S",
    ]

    rotulos_tipos = {
        "ENE": "Energético",
        "REL": "Elétrico",
        "CNF": "Confiabilidade",
        "SEM_CODIGO": "Sem classificação",
    }

    resultados = []

    for subsistema in ordem_subsistemas:
        df_sub = df_aux[
            df_aux["id_subsistema"]
            == subsistema
        ].copy()

        if df_sub.empty:
            continue

        curtailment_sub_mwh = (
            df_sub["curtailment_mwh"]
            .sum()
        )

        geracao_esperada_sub_mwh = (
            df_sub["geracao_esperada_mwh"]
            .sum()
        )

        if geracao_esperada_sub_mwh > 0:
            corte_pct = (
                100
                * curtailment_sub_mwh
                / geracao_esperada_sub_mwh
            )
        else:
            corte_pct = None

        if curtailment_total_mwh > 0:
            participacao_pct = (
                100
                * curtailment_sub_mwh
                / curtailment_total_mwh
            )
        else:
            participacao_pct = None

        # ====================================================
        # TIPO PREDOMINANTE
        # ====================================================

        curtailment_tipo = (
            df_sub
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
            tipo_predominante = (
                "Não disponível"
            )

        else:
            codigo_predominante = (
                curtailment_tipo
                .idxmax()
            )

            tipo_predominante = (
                rotulos_tipos.get(
                    codigo_predominante,
                    codigo_predominante,
                )
            )

        # ====================================================
        # MÊS CRÍTICO
        # ====================================================

        resumo_mensal = (
            df_sub
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
        )

        resumo_mensal = resumo_mensal[
            resumo_mensal[
                "geracao_esperada_mwh"
            ] > 0
        ].copy()

        resumo_mensal["corte_pct"] = (
            100
            * resumo_mensal[
                "curtailment_mwh"
            ]
            / resumo_mensal[
                "geracao_esperada_mwh"
            ]
        )

        if resumo_mensal.empty:
            mes_critico = (
                "Não disponível"
            )

        else:
            periodo_critico = (
                resumo_mensal[
                    "corte_pct"
                ]
                .idxmax()
            )

            mes_critico = (
                periodo_critico
                .to_timestamp()
                .strftime("%m/%Y")
            )

        # ====================================================
        # HORA CRÍTICA
        # ====================================================

        perfil_horario = (
            df_sub
            .groupby(
                "hora",
                observed=True,
            )["val_curtailment"]
            .mean()
        )

        if perfil_horario.empty:
            hora_critica = (
                "Não disponível"
            )

        else:
            hora_critica_valor = (
                int(
                    perfil_horario
                    .idxmax()
                )
            )

            hora_critica = (
                f"{hora_critica_valor:02d}:00"
            )

        resultados.append(
            {
                "Subsistema": subsistema,
                "Curtailment (GWh)": (
                    curtailment_sub_mwh
                    / 1000
                ),
                "Geração Esperada (GWh)": (
                    geracao_esperada_sub_mwh
                    / 1000
                ),
                "Corte (%)": corte_pct,
                "Participação (%)": (
                    participacao_pct
                ),
                "Tipo Predominante": (
                    tipo_predominante
                ),
                "Mês Crítico": (
                    mes_critico
                ),
                "Hora Crítica": (
                    hora_critica
                ),
            }
        )

    resumo = pd.DataFrame(
        resultados
    )

    if resumo.empty:
        return resumo

    ordem_subsistemas_mapa = {
        subsistema: ordem
        for ordem, subsistema
        in enumerate(
            ordem_subsistemas,
            start=1,
        )
    }

    resumo["ordem_subsistema"] = (
        resumo["Subsistema"]
        .map(
            ordem_subsistemas_mapa
        )
    )

    resumo = (
        resumo
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

    return resumo
