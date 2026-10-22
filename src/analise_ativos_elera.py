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

    df_elera["estado_elera"] = (df_elera["nom_usina"]
        .map({nome_base: dados.get("estado","Não informado") for nome_base, dados in ATIVOS_ELERA.items()})
    )
    
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
    - composição do curtailment entre ENE, REL e CNF;
    - perfil horário médio da geração esperada;
    - perfil horário médio do curtailment;
    - perfil horário médio do curtailment por ENE, REL e CNF;

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

    # ========================================================
    # BASE MENSAL CONSOLIDADA
    # ========================================================

    resumo_mensal["curtailment_gwh"] = (
        resumo_mensal[
            "curtailment_mwh"
        ]
        / 1000
    )

    resumo_mensal[
        "geracao_esperada_gwh"
    ] = (
        resumo_mensal[
            "geracao_esperada_mwh"
        ]
        / 1000
    )

    resumo_mensal["mes_rotulo"] = (
        resumo_mensal["mes"]
        .dt.strftime("%m/%Y")
    )

    resumo_mensal = (
        resumo_mensal
        .sort_values(
            "mes"
        )
        .reset_index(
            drop=True
        )
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

    # ========================================================
    # PERFIL HORÁRIO CONSOLIDADO
    # ========================================================

    # O perfil horário representa potência média em MW. Portanto, não se aplica o fator de 0.5 utilizado na conversão dos registros semihorários para MWh.

    base_instante_ativo = (
        df_ativo
        .groupby(
            "din_instante",
            as_index=False,
            observed=True,
        )
        .agg(
            curtailment_mw=(
                "val_curtailment_elera",
                "sum",
            ),
            geracao_esperada_mw=(
                "val_geracao_esperada_elera",
                "sum",
            ),
        )
    )

    base_instante_ativo["hora"] = (
        base_instante_ativo[
            "din_instante"
        ]
        .dt.hour
    )

    perfil_horario_resumo = (
        base_instante_ativo
        .groupby(
            "hora",
            as_index=False,
            observed=True,
        )
        .agg(
            curtailment_mw=(
                "curtailment_mw",
                "mean",
            ),
            geracao_esperada_mw=(
                "geracao_esperada_mw",
                "mean",
            ),
        )
    )

    # Garante as 24 horas do dia, mesmo que alguma
    # hora não possua registros válidos.

    perfil_horario_resumo = (
        perfil_horario_resumo
        .set_index(
            "hora"
        )
        .reindex(
            range(24),
            fill_value=0.0,
        )
        .rename_axis(
            "hora"
        )
        .reset_index()
    )

    perfil_horario_resumo[
        "hora_rotulo"
    ] = (
        perfil_horario_resumo[
            "hora"
        ]
        .map(
            lambda hora: (
                f"{int(hora):02d}:00"
            )
        )
    )

    # ========================================================
    # PERFIL HORÁRIO DO CURTAILMENT POR TIPO
    # ========================================================

    # Primeiro, soma o curtailment em cada instante
    # e tipo de restrição.

    base_instante_tipo = (
        df_tipos
        .groupby(
            [
                "din_instante",
                "tipo_curtailment",
            ],
            as_index=False,
            observed=True,
        )
        .agg(
            curtailment_mw=(
                "val_curtailment_elera",
                "sum",
            )
        )
    )

    # Cria uma tabela com uma linha por instante e uma
    # coluna para cada tipo. Os tipos ausentes em um
    # instante recebem zero.

    base_instante_tipo = (
        base_instante_tipo
        .pivot_table(
            index="din_instante",
            columns="tipo_curtailment",
            values="curtailment_mw",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reindex(
            columns=tipos_permitidos,
            fill_value=0.0,
        )
        .reset_index()
    )

    # Garante que sejam considerados todos os instantes
    # válidos do ativo. Se nenhum dos três tipos ocorreu
    # em determinado instante, ENE, REL e CNF recebem zero.

    instantes_ativo = (
        base_instante_ativo[
            [
                "din_instante",
            ]
        ]
        .drop_duplicates()
    )

    base_instante_tipo = (
        instantes_ativo
        .merge(
            base_instante_tipo,
            on="din_instante",
            how="left",
            validate="one_to_one",
        )
    )

    for codigo in tipos_permitidos:
        base_instante_tipo[codigo] = (
            base_instante_tipo[codigo]
            .fillna(0.0)
        )

    base_instante_tipo["hora"] = (
        base_instante_tipo[
            "din_instante"
        ]
        .dt.hour
    )

    # Calcula a potência média de cada tipo em cada
    # hora do dia, considerando zero quando o tipo
    # não ocorreu em um instante.

    perfil_horario_tipo_largo = (
        base_instante_tipo
        .groupby(
            "hora",
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
        )
    )

    perfil_horario_tipo_largo = (
        perfil_horario_tipo_largo
        .set_index(
            "hora"
        )
        .reindex(
            range(24),
            fill_value=0.0,
        )
        .rename_axis(
            "hora"
        )
        .reset_index()
    )

    # Converte novamente para o formato longo,
    # apropriado para o gráfico empilhado.

    perfil_horario_tipo = (
        perfil_horario_tipo_largo
        .melt(
            id_vars=[
                "hora",
            ],
            value_vars=tipos_permitidos,
            var_name="tipo_curtailment",
            value_name="curtailment_mw",
        )
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

    perfil_horario_tipo[
        "tipo_rotulo"
    ] = (
        perfil_horario_tipo[
            "tipo_curtailment"
        ]
        .map(
            rotulos_tipos
        )
    )

    perfil_horario_tipo[
        "hora_rotulo"
    ] = (
        perfil_horario_tipo[
            "hora"
        ]
        .map(
            lambda hora: (
                f"{int(hora):02d}:00"
            )
        )
    )

    perfil_horario_tipo[
        "ordem_tipo"
    ] = (
        perfil_horario_tipo[
            "tipo_curtailment"
        ]
        .map(
            ordem_tipos
        )
    )

    perfil_horario_tipo = (
        perfil_horario_tipo
        .sort_values(
            [
                "hora",
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
        "curtailment_gwh": float(curtailment_total_mwh/ 1000),
        "geracao_esperada_gwh": float(geracao_esperada_total_mwh/ 1000),
        "corte_pct": (float(corte_periodo_pct) if corte_periodo_pct is not None else None),
        "mes_critico": mes_critico,
        "corte_mes_critico_pct": (corte_mes_critico_pct),
        "curtailment_mes_critico_gwh": (curtailment_mes_critico_gwh),
        "base_mensal_resumo": (resumo_mensal),
        "base_mensal_tipo": (base_mensal_tipo),
        "perfil_horario_resumo": (perfil_horario_resumo),
        "perfil_horario_tipo": (perfil_horario_tipo),
        "composicao_cortes": (composicao_cortes),
    }


def preparar_exportacao_detalhada_ativos_elera(df,recorte_selecionado,granularidade):
    """
Prepara a base detalhada de exportação dos ativos
da Elera.

O usuário pode selecionar:

- Portfólio inteiro;
- Somente solares;
- Somente eólicas;
- Um ativo específico.

Em todos os recortes, os dados permanecem separados
por ativo, fonte e estado. O recorte determina quais
ativos entram no arquivo, mas não consolida ativos
diferentes em uma mesma linha.

As granularidades disponíveis são:

- Instante;
- Mês e hora;
- Dia e hora;
- Dia;
- Mês;
- Ano.

Para Conj. Faísa, os valores originais são
multiplicados pelo fator 0.5992 antes das
agregações.

Os registros originais representam intervalos
de 30 minutos. Portanto:

MW * 0.5 = MWh

Parâmetros
----------
df : pandas.DataFrame
    Base calculada de curtailment.

recorte_selecionado : str
    Portfólio inteiro, Somente solares,
    Somente eólicas ou nome de um ativo.

granularidade : str
    Nível temporal de agregação.

Retorno
-------
pandas.DataFrame
    Base separada por ativo, fonte, estado e período,
    com curtailment por tipo, geração esperada e
    percentuais de corte.
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

    granularidades_permitidas = {
        "Instante",
        "Mês e hora",
        "Dia e hora",
        "Dia",
        "Mês",
        "Ano",
    }

    if granularidade not in granularidades_permitidas:
        raise ValueError(
            "Granularidade inválida. Opções permitidas: "
            f"{sorted(granularidades_permitidas)}."
        )

    recortes_permitidos = {
        "Portfólio inteiro",
        "Somente solares",
        "Somente eólicas",
        *ORDEM_ATIVOS_ELERA,
    }

    if recorte_selecionado not in recortes_permitidos:
        raise ValueError(
            "O recorte selecionado não é válido."
        )

    # filtrar_ativos_elera aplica o fator 0.5992
    # ao Conj. Faísa e 1.0 aos demais ativos.

    df_elera = filtrar_ativos_elera(
        df
    )

    colunas_ajustadas = {
        "ativo_elera",
        "fonte_elera",
        "estado_elera",
        "val_curtailment_elera",
        "val_geracao_esperada_elera",
    }

    colunas_ajustadas_ausentes = (
        colunas_ajustadas
        - set(df_elera.columns)
    )

    if colunas_ajustadas_ausentes:
        raise ValueError(
            "A base filtrada não possui as colunas "
            "ajustadas necessárias: "
            f"{sorted(colunas_ajustadas_ausentes)}."
        )

    # ========================================================
    # APLICAÇÃO DO RECORTE
    # ========================================================
    
    # O recorte determina quais ativos entram no arquivo.
    # Mesmo para o portfólio inteiro ou para os recortes
    # por fonte, os ativos permanecem separados na base.
    
    if recorte_selecionado == "Somente solares":
        df_elera = df_elera[
            df_elera["fonte_elera"]
            == "Solar"
        ].copy()
    
    elif recorte_selecionado == "Somente eólicas":
        df_elera = df_elera[
            df_elera["fonte_elera"]
            == "Eólica"
        ].copy()
    
    elif recorte_selecionado in ORDEM_ATIVOS_ELERA:
        df_elera = df_elera[
            df_elera["ativo_elera"]
            == recorte_selecionado
        ].copy()
    
    # Para "Portfólio inteiro", todos os ativos são mantidos.

    # ========================================================
    # TRATAMENTO
    # ========================================================
    if df_elera.empty:
        raise ValueError("Não foram encontrados registros para o recorte selecionado.")

    df_elera["din_instante"] = pd.to_datetime(
        df_elera["din_instante"],
        errors="coerce",
    )

    df_elera[
        "val_curtailment_elera"
    ] = pd.to_numeric(
        df_elera[
            "val_curtailment_elera"
        ],
        errors="coerce",
    )

    df_elera[
        "val_geracao_esperada_elera"
    ] = pd.to_numeric(
        df_elera[
            "val_geracao_esperada_elera"
        ],
        errors="coerce",
    )

    df_elera["tipo_curtailment"] = (
        df_elera["cod_razaorestricao"]
        .astype("string")
        .str.strip()
        .str.upper()
        .fillna("SEM_CODIGO")
        .replace(
            "",
            "SEM_CODIGO",
        )
    )

    df_elera = df_elera.dropna(
        subset=[
            "din_instante",
            "ativo_elera",
            "fonte_elera",
            "val_curtailment_elera",
            "val_geracao_esperada_elera",
        ]
    ).copy()

    if df_elera.empty:
        raise ValueError(
            "Não restaram registros válidos após "
            "o tratamento da base."
        )

    # Valores negativos não devem compor energia
    # restringida ou geração esperada.

    df_elera["curtailment_mwh"] = (
        df_elera[
            "val_curtailment_elera"
        ]
        .clip(lower=0)
        * 0.5
    )

    df_elera["geracao_esperada_mwh"] = (
        df_elera[
            "val_geracao_esperada_elera"
        ]
        .clip(lower=0)
        * 0.5
    )

    # ========================================================
    # COLUNAS TEMPORAIS
    # ========================================================
    
    df_elera["data"] = (
        df_elera["din_instante"]
        .dt.normalize()
    )
    
    df_elera["ano"] = (
        df_elera["din_instante"]
        .dt.year
    )
    
    df_elera["mes"] = (
        df_elera["din_instante"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )
    
    df_elera["hora"] = (
        df_elera["din_instante"]
        .dt.hour
    )
    
    df_elera["hora_rotulo"] = (
        df_elera["hora"]
        .map(
            lambda hora: (
                f"{int(hora):02d}:00"
            )
        )
    )
    
    # ========================================================
    # COLUNAS DE IDENTIFICAÇÃO
    # ========================================================
    
    # Ativo, fonte e estado são preservados em todos
    # os recortes e granularidades.
    
    colunas_identificacao = [
        "ativo_elera",
        "fonte_elera",
        "estado_elera",
    ]
    
    # ========================================================
    # DEFINIÇÃO DA GRANULARIDADE
    # ========================================================
    
    if granularidade == "Instante":
        colunas_tempo = [
            "din_instante",
        ]
    
    elif granularidade == "Mês e hora":
        colunas_tempo = [
            "mes",
            "hora",
            "hora_rotulo",
        ]
    
    elif granularidade == "Dia e hora":
        colunas_tempo = [
            "data",
            "hora",
            "hora_rotulo",
        ]
    
    elif granularidade == "Dia":
        colunas_tempo = [
            "data",
        ]
    
    elif granularidade == "Mês":
        colunas_tempo = [
            "mes",
        ]
    
    else:
        colunas_tempo = [
            "ano",
        ]
    
    colunas_grupo = (
        colunas_identificacao
        + colunas_tempo
    )
    # ========================================================
    # CURTAILMENT POR TIPO
    # ========================================================

    tipos_permitidos = [
        "ENE",
        "REL",
        "CNF",
    ]

    df_tipos = df_elera[
        df_elera["tipo_curtailment"]
        .isin(
            tipos_permitidos
        )
    ].copy()

    curtailment_tipos = (
        df_tipos
        .groupby(
            colunas_grupo
            + [
                "tipo_curtailment",
            ],
            as_index=False,
            observed=True,
            dropna=False,
        )
        .agg(
            curtailment_mwh=(
                "curtailment_mwh",
                "sum",
            )
        )
    )

    curtailment_tipos = (
        curtailment_tipos
        .pivot_table(
            index=colunas_grupo,
            columns="tipo_curtailment",
            values="curtailment_mwh",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reindex(
            columns=tipos_permitidos,
            fill_value=0.0,
        )
        .reset_index()
    )

    curtailment_tipos.columns.name = None

    curtailment_tipos = (
        curtailment_tipos
        .rename(
            columns={
                "ENE": "Curtailment ENE (MWh)",
                "REL": "Curtailment REL (MWh)",
                "CNF": "Curtailment CNF (MWh)",
            }
        )
    )

    # ========================================================
    # GERAÇÃO ESPERADA
    # ========================================================

    geracao_esperada = (
        df_elera
        .groupby(
            colunas_grupo,
            as_index=False,
            observed=True,
            dropna=False,
        )
        .agg(
            **{
                "Geração Esperada (MWh)": (
                    "geracao_esperada_mwh",
                    "sum",
                ),
            }
        )
    )

        # ========================================================
        # UNIÃO E TOTAIS
        # ========================================================
    
        base_exportacao = (
            geracao_esperada
            .merge(
                curtailment_tipos,
                on=colunas_grupo,
                how="left",
                validate="one_to_one",
            )
        )
    
        colunas_curtailment = [
            "Curtailment ENE (MWh)",
            "Curtailment REL (MWh)",
            "Curtailment CNF (MWh)",
        ]
    
        base_exportacao[
            colunas_curtailment
        ] = (
            base_exportacao[
                colunas_curtailment
            ]
            .fillna(0.0)
        )
    
        base_exportacao[
            "Curtailment Todos (MWh)"
        ] = (
            base_exportacao[
                colunas_curtailment
            ]
            .sum(
                axis=1
            )
        )
    
        # ========================================================
        # PERCENTUAIS DE CORTE
        # ========================================================
    
        geracao_positiva = (
            base_exportacao[
                "Geração Esperada (MWh)"
            ] > 0
        )
    
        calculos_corte = {
            "Corte ENE (%)": (
                "Curtailment ENE (MWh)"
            ),
            "Corte REL (%)": (
                "Curtailment REL (MWh)"
            ),
            "Corte CNF (%)": (
                "Curtailment CNF (MWh)"
            ),
            "Corte Todos (%)": (
                "Curtailment Todos (MWh)"
            ),
        }
    
        for coluna_corte, coluna_volume in (
            calculos_corte.items()
        ):
            base_exportacao[
                coluna_corte
            ] = 0.0
    
            base_exportacao.loc[
                geracao_positiva,
                coluna_corte,
            ] = (
                100
                * base_exportacao.loc[
                    geracao_positiva,
                    coluna_volume,
                ]
                / base_exportacao.loc[
                    geracao_positiva,
                    "Geração Esperada (MWh)",
                ]
            )
    
        # ========================================================
        # NOMES DAS COLUNAS DE IDENTIFICAÇÃO E TEMPO
        # ========================================================
    
        base_exportacao = (
            base_exportacao
            .rename(
                columns={
                    "ativo_elera": "Ativo",
                    "fonte_elera": "Fonte",
                    "estado_elera": "Estado",
                    "din_instante": "Instante",
                    "data": "Data",
                    "ano": "Ano",
                    "mes": "Mês",
                    "hora": "Hora numérica",
                    "hora_rotulo": "Hora",
                }
            )
        )
    
        # ========================================================
        # ORDENAÇÃO DAS COLUNAS
        # ========================================================
    
        colunas_identificacao_resultado = [
            "Ativo",
            "Fonte",
            "Estado",
        ]
    
        colunas_tempo_resultado = [
            coluna
            for coluna in [
                "Instante",
                "Data",
                "Mês",
                "Ano",
                "Hora numérica",
                "Hora",
            ]
            if coluna in base_exportacao.columns
        ]
    
        colunas_indicadores_resultado = [
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
    
        colunas_resultado = (
            colunas_identificacao_resultado
            + colunas_tempo_resultado
            + colunas_indicadores_resultado
        )
    
        # ========================================================
        # ORDENAÇÃO DAS LINHAS
        # ========================================================
    
        colunas_ordenacao = [
            coluna
            for coluna in [
                "Ativo",
                "Instante",
                "Data",
                "Mês",
                "Ano",
                "Hora numérica",
            ]
            if coluna in base_exportacao.columns
        ]
    
        base_exportacao = (
            base_exportacao[
                colunas_resultado
            ]
            .sort_values(
                colunas_ordenacao,
                kind="stable",
            )
            .reset_index(
                drop=True
            )
        )
    
        # ========================================================
        # METADADOS DA EXPORTAÇÃO
        # ========================================================
    
        base_exportacao.attrs[
            "recorte"
        ] = recorte_selecionado
    
        base_exportacao.attrs[
            "granularidade"
        ] = granularidade
    
        return base_exportacao
