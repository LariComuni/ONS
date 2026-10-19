"""
Funções analíticas da página Ativos Elera.

Este módulo concentra os filtros, indicadores,
agregações e bases de exportação utilizados no
dashboard dos ativos da Elera.
"""

import pandas as pd


ATIVOS_ELERA = {
    "Conj. Janaúba": {
        "nome_exibicao": "Janaúba",
        "fonte": "Solar",
        "participacao_elera": 1.0,
        "estado": "MG",
    },
    "Conj. Alex": {
        "nome_exibicao": "Alex",
        "fonte": "Solar",
        "participacao_elera": 1.0,
        "estado": "CE",
    },
    "Conj. Igaporã II": {
        "nome_exibicao": "Alto Sertão",
        "fonte": "Eólica",
        "participacao_elera": 1.0,
        "estado": "BA",
    },
    "Conj. Renascença": {
        "nome_exibicao": "Renascença",
        "fonte": "Eólica",
        "participacao_elera": 1.0,
        "estado": "RN",
    },
    "Conj. Viamão 3": {
        "nome_exibicao": "Pontal",
        "fonte": "Eólica",
        "participacao_elera": 1.0,
        "estado": "RS",
    },
    "Conj. Oeste Seridó": {
        "nome_exibicao": "Seridó",
        "fonte": "Eólica",
        "participacao_elera": 1.0,
        "estado": "PB",
    },
    "Conj. Faísa": {
        "nome_exibicao": "Faísa",
        "fonte": "Eólica",
        "participacao_elera": 0.5992,
        "estado": "CE",
    },
}


ORDEM_ATIVOS_ELERA = [
    "Janaúba",
    "Alex",
    "Alto Sertão",
    "Renascença",
    "Pontal",
    "Seridó",
    "Faísa",
]


def filtrar_ativos_elera(
    df,
):
    """
    Filtra a base e mantém somente os ativos da Elera.

    Também adiciona as colunas de nome amigável e fonte.

    Parâmetros
    ----------
    df : pandas.DataFrame
        Base calculada de curtailment.

    Retorno
    -------
    pandas.DataFrame
        Base contendo somente os ativos da Elera.
    """

    if not isinstance(
        df,
        pd.DataFrame,
    ):
        raise TypeError("df deve ser um DataFrame.")

    if df.empty:
        raise ValueError("A base informada está vazia.")

    if "nom_usina" not in df.columns:
        raise ValueError("A base não possui a coluna nom_usina.")

    df_elera = df.copy()

    df_elera["nom_usina"] = (df_elera["nom_usina"].astype("string").str.strip())

    df_elera = df_elera[df_elera["nom_usina"].isin(ATIVOS_ELERA.keys())].copy()

    if df_elera.empty:
        raise ValueError("Nenhum ativo da Elera foi encontrado na base processada.")

    df_elera["ativo_elera"] = (df_elera["nom_usina"].map({nome_base: dados["nome_exibicao"] for nome_base, dados in ATIVOS_ELERA.items()}))

    df_elera["fonte_elera"] = (df_elera["nom_usina"].map({nome_base: dados["fonte"] for nome_base, dados in ATIVOS_ELERA.items()}))

    df_elera["participacao_elera"] = (df_elera["nom_usina"]
        .map({nome_base: dados["participacao_elera"] for nome_base, dados in ATIVOS_ELERA.items()}).fillna(0.0)
    )

    df_elera["val_curtailment"] = pd.to_numeric(df_elera["val_curtailment"],errors="coerce")
    
    df_elera["val_geracao_esperada"] = pd.to_numeric(df_elera["val_geracao_esperada"],errors="coerce")
    
    df_elera["val_curtailment_elera"] = (df_elera["val_curtailment"] * df_elera["participacao_elera"])
    
    df_elera["val_geracao_esperada_elera"] = (df_elera["val_geracao_esperada"] * df_elera["participacao_elera"])

    return df_elera


def calcular_kpis_ativos_elera(df):
    """
    Calcula os principais KPIs dos ativos da Elera.

    Os registros representam intervalos de 30 minutos.
    Portanto:

    MW * 0.5 = MWh
    MWh / 1000 = GWh

    A usina mais cortada é aquela que apresenta o maior
    percentual de corte em relação à geração esperada
    no período analisado.

    Parâmetros
    ----------
    df : pandas.DataFrame
        Base calculada de curtailment.

    Retorno
    -------
    dict
        Geração esperada, curtailment, corte médio
        e ativo com maior percentual de corte.
    """

    if not isinstance(df,pd.DataFrame):
        raise TypeError("df deve ser um DataFrame.")

    if df.empty:
        raise ValueError("A base informada está vazia.")

    colunas_obrigatorias = {"nom_usina","val_curtailment","val_geracao_esperada"}

    colunas_ausentes = (colunas_obrigatorias - set(df.columns))

    if colunas_ausentes:
        raise ValueError(f"A base não possui as colunas obrigatórias: {sorted(colunas_ausentes)}.")

    df_elera = filtrar_ativos_elera(df)

    df_elera["val_curtailment"] = pd.to_numeric(df_elera["val_curtailment"],errors="coerce")

    df_elera["val_geracao_esperada"] = pd.to_numeric(df_elera["val_geracao_esperada"],errors="coerce")

    df_elera = df_elera.dropna(subset=["ativo_elera","val_curtailment_elera","val_geracao_esperada_elera"]).copy()

    if df_elera.empty:
        raise ValueError("Não restaram registros válidos dos ativos da Elera após o tratamento.")

    # ========================================================
    # CONVERSÃO PARA ENERGIA
    # ========================================================

    df_elera["curtailment_mwh"] = (df_elera["val_curtailment_elera"].clip(lower=0) * 0.5)

    df_elera["geracao_esperada_mwh"] = (df_elera["val_geracao_esperada_elera"].clip(lower=0) * 0.5)

    # ========================================================
    # TOTAIS DOS ATIVOS ELERA
    # ========================================================

    curtailment_total_mwh = (df_elera["curtailment_mwh"].sum())

    geracao_esperada_total_mwh = (df_elera["geracao_esperada_mwh"].sum())

    if geracao_esperada_total_mwh > 0:
        corte_medio_pct = (100 * curtailment_total_mwh / geracao_esperada_total_mwh)

    else:
        corte_medio_pct = None

    # ========================================================
    # INDICADORES POR ATIVO
    # ========================================================

    indicadores_ativos = (
        df_elera
        .groupby(
            [
                "nom_usina",
                "ativo_elera",
                "fonte_elera",
            ],
            as_index=False,
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

    indicadores_ativos["corte_pct"] = 0.0

    mascara_geracao_positiva = (indicadores_ativos["geracao_esperada_mwh"] > 0)

    indicadores_ativos.loc[
        mascara_geracao_positiva,
        "corte_pct",
    ] = (
        100
        * indicadores_ativos.loc[
            mascara_geracao_positiva,
            "curtailment_mwh",
        ]
        / indicadores_ativos.loc[
            mascara_geracao_positiva,
            "geracao_esperada_mwh",
        ]
    )

    # ========================================================
    # USINA MAIS CORTADA
    # ========================================================

    ativos_com_geracao = indicadores_ativos[indicadores_ativos["geracao_esperada_mwh"] > 0].copy()

    if ativos_com_geracao.empty:
        nome_usina_mais_cortada = ("Não disponível")
        nome_base_usina_mais_cortada = None
        fonte_usina_mais_cortada = None
        corte_usina_mais_cortada_pct = None
        curtailment_usina_mais_cortada_gwh = None

    else:
        linha_mais_cortada = (ativos_com_geracao.loc[ativos_com_geracao["corte_pct"].idxmax()])
        nome_usina_mais_cortada = (linha_mais_cortada["ativo_elera"])
        nome_base_usina_mais_cortada = (linha_mais_cortada["nom_usina"])
        fonte_usina_mais_cortada = (linha_mais_cortada["fonte_elera"])
        corte_usina_mais_cortada_pct = round(float(linha_mais_cortada["corte_pct"]),2,)
        curtailment_usina_mais_cortada_gwh = (round(float(linha_mais_cortada["curtailment_mwh"]) / 1000,2))

    # ========================================================
    # ATIVOS ENCONTRADOS
    # ========================================================

    nomes_encontrados = (indicadores_ativos["ativo_elera"].dropna().unique().tolist())
    nomes_encontrados = [nome for nome in ORDEM_ATIVOS_ELERA if nome in nomes_encontrados]

    # ========================================================
    # RETORNO
    # ========================================================

    return {
      "Geração Esperada (GWh)": round(float(geracao_esperada_total_mwh) / 1000,2),
      "Curtailment (GWh)": round(float(curtailment_total_mwh) / 1000,2),
      "Corte Médio (%)": (round(float(corte_medio_pct),2) if corte_medio_pct is not None else None),
      "Usina Mais Cortada": (nome_usina_mais_cortada),
      "Nome na Base da Usina Mais Cortada": (nome_base_usina_mais_cortada),
      "Fonte da Usina Mais Cortada": (fonte_usina_mais_cortada),
      "Corte da Usina Mais Cortada (%)": (corte_usina_mais_cortada_pct),
      "Curtailment da Usina Mais Cortada (GWh)": (curtailment_usina_mais_cortada_gwh),
      "Quantidade de Ativos Encontrados": (len(nomes_encontrados)),
      "Ativos Encontrados": (nomes_encontrados),
    }

def preparar_curtailment_mensal_ativos_elera(
    df,
):
    """
    Prepara o curtailment mensal dos ativos da Elera, separado por tipo de restrição.

    Os registros representam intervalos de 30 minutos.Portanto:

    MW * 0.5 = MWh
    MWh / 1000 = GWh

    Parâmetros
    ----------
    df : pandas.DataFrame
        Base calculada de curtailment.

    Retorno
    -------
    pandas.DataFrame
        Tabela mensal com curtailment ENE, REL e CNF em GWh para o portfólio consolidado da Elera.
    """

    colunas_obrigatorias = {
        "din_instante",
        "nom_usina",
        "cod_razaorestricao",
        "val_curtailment"}

    colunas_ausentes = (colunas_obrigatorias - set(df.columns))

    if colunas_ausentes:
        raise ValueError(
            f"A base não possui as colunas obrigatórias:{sorted(colunas_ausentes)}.")

    df_elera = filtrar_ativos_elera(df)

    if "val_curtailment_elera" not in df_elera.columns:
        raise ValueError("A função filtrar_ativos_elera não criou a coluna val_curtailment_elera.")

    df_elera["din_instante"] = pd.to_datetime(df_elera["din_instante"],errors="coerce")

    df_elera["val_curtailment_elera"] = pd.to_numeric(df_elera["val_curtailment_elera"],errors="coerce")

    df_elera["tipo_curtailment"] = (
        df_elera["cod_razaorestricao"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    df_elera = df_elera.dropna(subset=["din_instante","ativo_elera","val_curtailment_elera"]).copy()

    tipos_permitidos = ["ENE","REL","CNF"]

    df_elera = df_elera[df_elera["tipo_curtailment"].isin(tipos_permitidos)].copy()

    if df_elera.empty:
        raise ValueError("Não foram encontrados registros de curtailment ENE, REL ou CNF para os ativos da Elera.")

    df_elera["mes"] = (df_elera["din_instante"].dt.to_period("M").dt.to_timestamp())

    df_elera["curtailment_gwh"] = (df_elera["val_curtailment_elera"].clip(lower=0) * 0.5 / 1000)

    base_mensal = (
        df_elera
        .groupby(["mes","tipo_curtailment"],as_index=False,observed=True)
        .agg(curtailment_gwh=("curtailment_gwh","sum"))
    )

    # Garante todos os meses entre o primeiro e o último mês disponíveis na base.

    meses_disponiveis = pd.date_range(start=base_mensal["mes"].min(),end=base_mensal["mes"].max(),freq="MS",)

    indice_completo = pd.MultiIndex.from_product([meses_disponiveis,tipos_permitidos],names=["mes","tipo_curtailment"])

    base_mensal = (base_mensal.set_index(["mes","tipo_curtailment"]).reindex(indice_completo,fill_value=0.0).reset_index())

    rotulos_tipos = {"ENE": "Energético","REL": "Elétrico","CNF": "Confiabilidade"}

    base_mensal["tipo_rotulo"] = (base_mensal["tipo_curtailment"].map(rotulos_tipos))

    base_mensal["mes_rotulo"] = (base_mensal["mes"].dt.strftime("%m/%Y"))

    base_mensal["ordem_tipo"] = (base_mensal["tipo_curtailment"].map({"ENE": 1,"REL": 2,"CNF": 3}))

    base_mensal = (base_mensal.sort_values(["mes","ordem_tipo"]).drop(columns="ordem_tipo").reset_index(drop=True))

    return base_mensal

def preparar_geracao_esperada_mensal_ativos_elera(
    df,
):
    """
    Prepara a geração esperada mensal atribuída ao
    portfólio da Elera.

    Para Conj. Faísa, os valores da base original são
    multiplicados por 0.5992, representando somente
    a parcela do conjunto atribuível à Elera.

    Os registros representam intervalos de 30 minutos.
    Portanto:

    MW * 0.5 = MWh
    MWh / 1000 = GWh

    Parâmetros
    ----------
    df : pandas.DataFrame
        Base calculada de curtailment.

    Retorno
    -------
    pandas.DataFrame
        Tabela mensal com a geração esperada atribuída
        ao portfólio da Elera, em GWh.
    """

    if not isinstance(df,pd.DataFrame):
        raise TypeError("df deve ser um DataFrame.")

    if df.empty:
        raise ValueError("A base informada está vazia.")

    colunas_obrigatorias = {"din_instante","nom_usina","val_geracao_esperada"}

    colunas_ausentes = (colunas_obrigatorias - set(df.columns))

    if colunas_ausentes:
        raise ValueError(f"A base não possui as colunas obrigatórias: {sorted(colunas_ausentes)}.")

    df_elera = filtrar_ativos_elera(df)

    colunas_ajustadas_obrigatorias = {"ativo_elera","participacao_elera","val_geracao_esperada_elera"}

    colunas_ajustadas_ausentes = (colunas_ajustadas_obrigatorias - set(df_elera.columns))

    if colunas_ajustadas_ausentes:
        raise ValueError(f"A base filtrada não possui as colunas ajustadas obrigatórias:{sorted(colunas_ajustadas_ausentes)}.")

    df_elera["din_instante"] = pd.to_datetime(df_elera["din_instante"],errors="coerce")

    df_elera["val_geracao_esperada_elera"] = pd.to_numeric(df_elera["val_geracao_esperada_elera"],errors="coerce")

    df_elera = df_elera.dropna(subset=["din_instante","ativo_elera","val_geracao_esperada_elera"]).copy()

    if df_elera.empty:
        raise ValueError("Não restaram registros válidos dos ativos da Elera após o tratamento.")

    df_elera["mes"] = (df_elera["din_instante"].dt.to_period("M").dt.to_timestamp())

    df_elera["geracao_esperada_gwh"] = (df_elera["val_geracao_esperada_elera"].clip(lower=0) * 0.5 / 1000)

    base_mensal = (
        df_elera
        .groupby("mes",as_index=False,observed=True)
        .agg(geracao_esperada_gwh=("geracao_esperada_gwh","sum"))
    )

    if base_mensal.empty:
        raise ValueError("Não foi possível preparar a geração esperada mensal dos ativos da Elera.")

    meses_disponiveis = pd.date_range(start=base_mensal["mes"].min(),end=base_mensal["mes"].max(),freq="MS")

    base_mensal = (
        base_mensal.set_index("mes")
        .reindex(meses_disponiveis,fill_value=0.0)
        .rename_axis("mes")
        .reset_index()
    )

    base_mensal["mes_rotulo"] = (base_mensal["mes"].dt.strftime("%m/%Y"))

    return base_mensal

def preparar_participacao_curtailment_ativos_elera(
    df,
):
    """
    Prepara a participação de cada ativo da Elera
    no curtailment total do portfólio.

    Para Conj. Faísa, os valores da base original são
    multiplicados por 0.5992, de forma a representar
    somente a parcela do conjunto atribuível à Elera.
    
    O fator 0.5992 não representa a participação de
    Faísa no curtailment total do portfólio.

    Os registros representam intervalos de 30 minutos.
    Portanto:

    MW * 0.5 = MWh
    MWh / 1000 = GWh

    Parâmetros
    ----------
    df : pandas.DataFrame
        Base calculada de curtailment.

    Retorno
    -------
    pandas.DataFrame
        Tabela com curtailment em GWh, participação
        percentual e fonte de cada ativo da Elera.
    """

    if not isinstance(df,pd.DataFrame):
        raise TypeError("df deve ser um DataFrame.")

    if df.empty:
        raise ValueError("A base informada está vazia.")

    colunas_obrigatorias = {"nom_usina","val_curtailment"}

    colunas_ausentes = (colunas_obrigatorias - set(df.columns))

    if colunas_ausentes:
        raise ValueError(f"A base não possui as colunas obrigatórias: {sorted(colunas_ausentes)}.")

    # filtrar_ativos_elera cria: ativo_elera, fonte_elera, participacao_elera, val_curtailment_elera

    df_elera = filtrar_ativos_elera(df)

    colunas_ajustadas_obrigatorias = {
        "ativo_elera",
        "fonte_elera",
        "participacao_elera",
        "val_curtailment_elera",
    }

    colunas_ajustadas_ausentes = (colunas_ajustadas_obrigatorias - set(df_elera.columns))

    if colunas_ajustadas_ausentes:
        raise ValueError(f"A base filtrada não possui as colunas ajustadas obrigatórias: {sorted(colunas_ajustadas_ausentes)}.")

    df_elera["val_curtailment_elera"] = pd.to_numeric(df_elera["val_curtailment_elera"],errors="coerce")

    df_elera = df_elera.dropna(subset=["ativo_elera","fonte_elera","val_curtailment_elera",]).copy()

    if df_elera.empty:
        raise ValueError("Não restaram registros válidos dos ativos da Elera após o tratamento.")

    df_elera["curtailment_gwh"] = (df_elera["val_curtailment_elera"].clip(lower=0) * 0.5 / 1000)

    participacao_ativos = (
        df_elera
        .groupby(["ativo_elera","fonte_elera"],as_index=False,observed=True)
        .agg(curtailment_gwh=("curtailment_gwh","sum"))
    )

    curtailment_total_gwh = (participacao_ativos["curtailment_gwh"].sum())

    if curtailment_total_gwh <= 0:
        participacao_ativos["participacao_pct"] = 0.0

    else:
        participacao_ativos["participacao_pct"] = (
            100 * participacao_ativos["curtailment_gwh"] / curtailment_total_gwh)

    # Ordem visual: maior participação primeiro. Como o gráfico será horizontal e o eixo Y será invertido no Plotly, o maior ficará no topo.

    participacao_ativos = (
        participacao_ativos
        .sort_values(["participacao_pct","ativo_elera"],ascending=[False,True],)
        .reset_index(drop=True)
    )

    participacao_ativos["ordem_participacao"] = range(1,len(participacao_ativos) + 1)

    return participacao_ativos

def preparar_participacao_geracao_ativos_elera(
    df,
):
    """
    Prepara a participação de cada ativo na geração
    esperada total atribuída ao portfólio da Elera.

    Para Conj. Faísa, os valores da base original são
    multiplicados por 0.5992 antes do cálculo da
    participação no portfólio.

    O fator 0.5992 não representa a participação de
    Faísa na geração esperada total do portfólio.
    A participação do ativo é calculada posteriormente
    pela razão entre sua geração esperada ajustada e a
    geração esperada ajustada total do portfólio.

    Os registros representam intervalos de 30 minutos.
    Portanto:

    MW * 0.5 = MWh
    MWh / 1000 = GWh

    Parâmetros
    ----------
    df : pandas.DataFrame
        Base calculada de curtailment.

    Retorno
    -------
    pandas.DataFrame
        Tabela com geração esperada ajustada em GWh,
        participação percentual e fonte de cada ativo.
    """

    if not isinstance(df,pd.DataFrame):
        raise TypeError("df deve ser um DataFrame")

    if df.empty:
        raise ValueError("A base informada está vazia.")

    colunas_obrigatorias = {"nom_usina","val_geracao_esperada"}

    colunas_ausentes = (colunas_obrigatorias - set(df.columns))

    if colunas_ausentes:
        raise ValueError(f"A base não possui as colunas obrigatórias: {sorted(colunas_ausentes)}.")

    df_elera = filtrar_ativos_elera(df)

    colunas_ajustadas_obrigatorias = {"ativo_elera","fonte_elera","participacao_elera","val_geracao_esperada_elera"}

    colunas_ajustadas_ausentes = (colunas_ajustadas_obrigatorias - set(df_elera.columns))

    if colunas_ajustadas_ausentes:
        raise ValueError(f"A base filtrada não possui as colunas ajustadas obrigatórias:{sorted(colunas_ajustadas_ausentes)}.")

    df_elera["val_geracao_esperada_elera"] = pd.to_numeric(df_elera["val_geracao_esperada_elera"],errors="coerce")

    df_elera = df_elera.dropna(subset=["ativo_elera","fonte_elera","val_geracao_esperada_elera"]).copy()

    if df_elera.empty:
        raise ValueError("Não restaram registros válidos dos ativos da Elera após o tratamento.")

    df_elera["geracao_esperada_gwh"] = (df_elera["val_geracao_esperada_elera"].clip(lower=0) * 0.5 / 1000)

    participacao_ativos = (
        df_elera
        .groupby(["ativo_elera","fonte_elera"],as_index=False,observed=True)
        .agg(geracao_esperada_gwh=("geracao_esperada_gwh","sum"))
    )

    geracao_total_gwh = (participacao_ativos["geracao_esperada_gwh"].sum())

    if geracao_total_gwh <= 0:
        participacao_ativos["participacao_pct"] = 0.0

    else:
        participacao_ativos["participacao_pct"] = (100 * participacao_ativos["geracao_esperada_gwh"] / geracao_total_gwh)

    participacao_ativos = (
        participacao_ativos
        .sort_values(["participacao_pct","ativo_elera",],ascending=[False,True])
        .reset_index(drop=True)
    )

    participacao_ativos["ordem_participacao"] = range(1,len(participacao_ativos) + 1)

    return participacao_ativos

def preparar_analise_individual_ativo_elera(
    df,
    ativo_selecionado,
):
    """
    Prepara a análise individual de um ativo da Elera.

    A função retorna:

    - informações cadastrais do ativo;
    - geração esperada no período;
    - curtailment no período;
    - percentual de corte;
    - mês crítico;
    - curtailment mensal dividido em ENE, REL e CNF;
    - composição do curtailment entre ENE, REL e CNF.

    Para Conj. Faísa, os valores da base original são
    multiplicados por 0.5992 antes das agregações, de
    modo a considerar somente a parcela do conjunto
    atribuível à Elera.

    Os registros representam intervalos de 30 minutos.
    Portanto:

    MW * 0.5 = MWh
    MWh / 1000 = GWh

    Parâmetros
    ----------
    df : pandas.DataFrame
        Base calculada de curtailment.

    ativo_selecionado : str
        Nome amigável do ativo selecionado.

    Retorno
    -------
    dict
        Dicionário com informações, KPIs e bases
        analíticas do ativo.
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
        "nom_usina",
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

    ativo_normalizado = str(
        ativo_selecionado
    ).strip()

    if ativo_normalizado not in ORDEM_ATIVOS_ELERA:
        raise ValueError(
            "O ativo selecionado não pertence ao "
            "portfólio cadastrado da Elera."
        )

    # filtrar_ativos_elera aplica o fator 0.5992
    # somente aos registros de Conj. Faísa.

    df_elera = filtrar_ativos_elera(
        df
    )

    colunas_ajustadas_obrigatorias = {
        "nom_usina",
        "ativo_elera",
        "fonte_elera",
        "estado_elera",
        "participacao_elera",
        "val_curtailment_elera",
        "val_geracao_esperada_elera",
    }

    colunas_ajustadas_ausentes = (
        colunas_ajustadas_obrigatorias
        - set(df_elera.columns)
    )

    if colunas_ajustadas_ausentes:
        raise ValueError(
            "A base filtrada não possui as colunas "
            "necessárias para a análise individual: "
            f"{sorted(colunas_ajustadas_ausentes)}."
        )

    df_ativo = df_elera[
        df_elera["ativo_elera"]
        == ativo_normalizado
    ].copy()

    if df_ativo.empty:
        raise ValueError(
            "Não foram encontrados registros para o "
            f"ativo {ativo_normalizado}."
        )

    # ========================================================
    # TRATAMENTO
    # ========================================================

    df_ativo["din_instante"] = pd.to_datetime(
        df_ativo["din_instante"],
        errors="coerce",
    )

    df_ativo[
        "val_curtailment_elera"
    ] = pd.to_numeric(
        df_ativo[
            "val_curtailment_elera"
        ],
        errors="coerce",
    )

    df_ativo[
        "val_geracao_esperada_elera"
    ] = pd.to_numeric(
        df_ativo[
            "val_geracao_esperada_elera"
        ],
        errors="coerce",
    )

    df_ativo["tipo_curtailment"] = (
        df_ativo["cod_razaorestricao"]
        .astype("string")
        .str.strip()
        .str.upper()
        .fillna("SEM_CODIGO")
        .replace(
            "",
            "SEM_CODIGO",
        )
    )

    df_ativo = df_ativo.dropna(
        subset=[
            "din_instante",
            "ativo_elera",
            "val_curtailment_elera",
            "val_geracao_esperada_elera",
        ]
    ).copy()

    if df_ativo.empty:
        raise ValueError(
            "Não restaram registros válidos para o "
            "ativo selecionado."
        )

    df_ativo["mes"] = (
        df_ativo["din_instante"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    df_ativo["curtailment_mwh"] = (
        df_ativo[
            "val_curtailment_elera"
        ]
        .clip(lower=0)
        * 0.5
    )

    df_ativo["geracao_esperada_mwh"] = (
        df_ativo[
            "val_geracao_esperada_elera"
        ]
        .clip(lower=0)
        * 0.5
    )

    # ========================================================
    # INFORMAÇÕES DO ATIVO
    # ========================================================

    nome_base = (
        df_ativo["nom_usina"]
        .dropna()
        .iloc[0]
    )

    fonte = (
        df_ativo["fonte_elera"]
        .dropna()
        .iloc[0]
    )

    estado = (
        df_ativo["estado_elera"]
        .dropna()
        .iloc[0]
    )

    participacao_fator = float(
        df_ativo["participacao_elera"]
        .dropna()
        .iloc[0]
    )

    # ========================================================
    # KPIs DO PERÍODO
    # ========================================================

    curtailment_total_mwh = (
        df_ativo["curtailment_mwh"]
        .sum()
    )

    geracao_esperada_total_mwh = (
        df_ativo["geracao_esperada_mwh"]
        .sum()
    )

    if geracao_esperada_total_mwh > 0:
        corte_periodo_pct = (
            100
            * curtailment_total_mwh
            / geracao_esperada_total_mwh
        )

    else:
        corte_periodo_pct = None

    # ========================================================
    # MÊS CRÍTICO
    # Maior corte percentual mensal.
    # ========================================================

    resumo_mensal = (
        df_ativo
        .groupby(
            "mes",
            as_index=False,
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

    resumo_mensal["corte_pct"] = 0.0

    mascara_geracao_positiva = (
        resumo_mensal[
            "geracao_esperada_mwh"
        ] > 0
    )

    resumo_mensal.loc[
        mascara_geracao_positiva,
        "corte_pct",
    ] = (
        100
        * resumo_mensal.loc[
            mascara_geracao_positiva,
            "curtailment_mwh",
        ]
        / resumo_mensal.loc[
            mascara_geracao_positiva,
            "geracao_esperada_mwh",
        ]
    )

    meses_validos = resumo_mensal[
        resumo_mensal[
            "geracao_esperada_mwh"
        ] > 0
    ].copy()

    if meses_validos.empty:
        mes_critico = "Não disponível"
        corte_mes_critico_pct = None
        curtailment_mes_critico_gwh = None

    else:
        linha_mes_critico = meses_validos.loc[
            meses_validos[
                "corte_pct"
            ].idxmax()
        ]

        mes_critico = (
            linha_mes_critico["mes"]
            .strftime("%m/%Y")
        )

        corte_mes_critico_pct = float(
            linha_mes_critico[
                "corte_pct"
            ]
        )

        curtailment_mes_critico_gwh = float(
            linha_mes_critico[
                "curtailment_mwh"
            ]
            / 1000
        )

    # ========================================================
    # CURTAILMENT MENSAL POR TIPO
    # ========================================================

    tipos_permitidos = [
        "ENE",
        "REL",
        "CNF",
    ]

    df_tipos = df_ativo[
        df_ativo["tipo_curtailment"]
        .isin(
            tipos_permitidos
        )
    ].copy()

    base_mensal_tipo = (
        df_tipos
        .groupby(
            [
                "mes",
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

    meses_disponiveis = pd.date_range(
        start=df_ativo["mes"].min(),
        end=df_ativo["mes"].max(),
        freq="MS",
    )

    indice_completo = pd.MultiIndex.from_product(
        [
            meses_disponiveis,
            tipos_permitidos,
        ],
        names=[
            "mes",
            "tipo_curtailment",
        ],
    )

    if base_mensal_tipo.empty:
        base_mensal_tipo = pd.DataFrame(
            index=indice_completo
        ).reset_index()

        base_mensal_tipo[
            "curtailment_mwh"
        ] = 0.0

    else:
        base_mensal_tipo = (
            base_mensal_tipo
            .set_index(
                [
                    "mes",
                    "tipo_curtailment",
                ]
            )
            .reindex(
                indice_completo,
                fill_value=0.0,
            )
            .reset_index()
        )

    base_mensal_tipo[
        "curtailment_gwh"
    ] = (
        base_mensal_tipo[
            "curtailment_mwh"
        ]
        / 1000
    )

    rotulos_tipos = {
        "ENE": "Energético",
        "REL": "Elétrico",
        "CNF": "Confiabilidade",
    }

    ordem_tipos = {
        "ENE": 1,
        "REL": 2,
        "CNF": 3,
    }

    base_mensal_tipo["tipo_rotulo"] = (
        base_mensal_tipo[
            "tipo_curtailment"
        ]
        .map(
            rotulos_tipos
        )
    )

    base_mensal_tipo["mes_rotulo"] = (
        base_mensal_tipo["mes"]
        .dt.strftime("%m/%Y")
    )

    base_mensal_tipo["ordem_tipo"] = (
        base_mensal_tipo[
            "tipo_curtailment"
        ]
        .map(
            ordem_tipos
        )
    )

    base_mensal_tipo = (
        base_mensal_tipo
        .sort_values(
            [
                "mes",
                "ordem_tipo",
            ]
        )
        .drop(
            columns="ordem_tipo"
        )
        .reset_index(
            drop=True
        )
    )

    # ========================================================
    # COMPOSIÇÃO DOS CORTES NO PERÍODO
    # ========================================================

    composicao_cortes = (
        df_tipos
        .groupby(
            "tipo_curtailment",
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

    indice_tipos = pd.Index(
        tipos_permitidos,
        name="tipo_curtailment",
    )

    if composicao_cortes.empty:
        composicao_cortes = pd.DataFrame(
            index=indice_tipos
        ).reset_index()

        composicao_cortes[
            "curtailment_mwh"
        ] = 0.0

    else:
        composicao_cortes = (
            composicao_cortes
            .set_index(
                "tipo_curtailment"
            )
            .reindex(
                indice_tipos,
                fill_value=0.0,
            )
            .reset_index()
        )

    composicao_cortes[
        "curtailment_gwh"
    ] = (
        composicao_cortes[
            "curtailment_mwh"
        ]
        / 1000
    )

    curtailment_classificado_mwh = (
        composicao_cortes[
            "curtailment_mwh"
        ]
        .sum()
    )

    if curtailment_classificado_mwh > 0:
        composicao_cortes[
            "composicao_pct"
        ] = (
            100
            * composicao_cortes[
                "curtailment_mwh"
            ]
            / curtailment_classificado_mwh
        )

    else:
        composicao_cortes[
            "composicao_pct"
        ] = 0.0

    composicao_cortes["tipo_rotulo"] = (
        composicao_cortes[
            "tipo_curtailment"
        ]
        .map(
            rotulos_tipos
        )
    )

    composicao_cortes["ordem_tipo"] = (
        composicao_cortes[
            "tipo_curtailment"
        ]
        .map(
            ordem_tipos
        )
    )

    composicao_cortes = (
        composicao_cortes
        .sort_values(
            "ordem_tipo"
        )
        .drop(
            columns="ordem_tipo"
        )
        .reset_index(
            drop=True
        )
    )

    # ========================================================
    # RETORNO
    # ========================================================

    return {
        "ativo": ativo_normalizado,
        "nome_base": nome_base,
        "fonte": fonte,
        "estado": estado,
        "fator_atribuicao": participacao_fator,
        "curtailment_gwh": float(
            curtailment_total_mwh
            / 1000
        ),
        "geracao_esperada_gwh": float(
            geracao_esperada_total_mwh
            / 1000
        ),
        "corte_pct": (
            float(
                corte_periodo_pct
            )
            if corte_periodo_pct is not None
            else None
        ),
        "mes_critico": mes_critico,
        "corte_mes_critico_pct": (
            corte_mes_critico_pct
        ),
        "curtailment_mes_critico_gwh": (
            curtailment_mes_critico_gwh
        ),
        "base_mensal_tipo": (
            base_mensal_tipo
        ),
        "composicao_cortes": (
            composicao_cortes
        ),
    }
