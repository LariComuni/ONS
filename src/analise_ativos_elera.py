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
    },
    "Conj. Alex": {
        "nome_exibicao": "Alex",
        "fonte": "Solar",
        "participacao_elera": 1.0,
    },
    "Conj. Igaporã II": {
        "nome_exibicao": "Alto Sertão",
        "fonte": "Eólica",
        "participacao_elera": 1.0,
    },
    "Conj. Renascença": {
        "nome_exibicao": "Renascença",
        "fonte": "Eólica",
        "participacao_elera": 1.0,
    },
    "Conj. Viamão 3": {
        "nome_exibicao": "Pontal",
        "fonte": "Eólica",
        "participacao_elera": 1.0,
    },
    "Conj. Oeste Seridó": {
        "nome_exibicao": "Seridó",
        "fonte": "Eólica",
        "participacao_elera": 1.0,
    },
    "Conj. Faísa": {
        "nome_exibicao": "Faísa",
        "fonte": "Eólica",
        "participacao_elera": 0.5992,
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
