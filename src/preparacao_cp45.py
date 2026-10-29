"""
Preparação das bases horárias utilizadas na análise CP45.

Este módulo recebe bases já coletadas e tratadas por:

- coleta_ons.py:
  curtailment e geração esperada EOL e UFV;

- coleta_evt.py:
  geração hidráulica e energia vertida turbinável;

- dados_pld.py:
  PLD horário e indicador de descolamento.

O módulo não baixa dados e não calcula os cenários da CP45.
Sua responsabilidade é apenas padronizar e integrar as bases
em granularidade horária.
"""

# ============================================================
# IMPORTAÇÕES
# ============================================================

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURAÇÕES
# ============================================================

FONTES_RENOVAVEIS_CP45 = [
    "EOL",
    "UFV",
]

SUBSISTEMAS_CP45 = [
    "N",
    "NE",
    "S",
    "SE",
]

TIPO_CURTAILMENT_CP45 = "ENE"


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def validar_dataframe(
    df,
    nome_base,
    colunas_obrigatorias,
):
    """
    Valida um DataFrame e suas colunas obrigatórias.

    Parâmetros
    ----------
    df : pandas.DataFrame
        Base que será validada.

    nome_base : str
        Nome utilizado nas mensagens de erro.

    colunas_obrigatorias : iterable
        Colunas que devem existir na base.
    """

    if not isinstance(
        df,
        pd.DataFrame,
    ):
        raise TypeError(
            f"{nome_base} deve ser um DataFrame."
        )

    if df.empty:
        raise ValueError(
            f"{nome_base} está vazio."
        )

    colunas_ausentes = (
        set(
            colunas_obrigatorias
        )
        - set(
            df.columns
        )
    )

    if colunas_ausentes:
        raise ValueError(
            f"{nome_base} não possui as colunas "
            "obrigatórias: "
            f"{sorted(colunas_ausentes)}."
        )


def padronizar_subsistema(
    serie,
):
    """
    Padroniza identificadores de subsistema para:

    N, NE, S e SE.
    """

    mapa_subsistemas = {
        "N": "N",
        "NORTE": "N",
        "NE": "NE",
        "NORDESTE": "NE",
        "S": "S",
        "SUL": "S",
        "SE": "SE",
        "SUDESTE": "SE",
        "SUDESTE/CENTRO-OESTE": "SE",
        "SUDESTE / CENTRO-OESTE": "SE",
        "SE/CO": "SE",
    }

    serie_padronizada = (
        serie
        .astype("string")
        .str.strip()
        .str.upper()
        .map(
            mapa_subsistemas
        )
    )

    return serie_padronizada


def calcular_percentual_seguro(
    numerador,
    denominador,
):
    """
    Calcula 100 × numerador / denominador.

    Quando o denominador for zero, negativo ou ausente,
    o resultado será zero.
    """

    numerador = pd.to_numeric(
        numerador,
        errors="coerce",
    ).fillna(0.0)

    denominador = pd.to_numeric(
        denominador,
        errors="coerce",
    ).fillna(0.0)

    resultado = np.zeros(
        len(
            denominador
        ),
        dtype=float,
    )

    mascara_valida = (
        denominador > 0
    )

    resultado[
        mascara_valida
    ] = (
        100
        * numerador.loc[
            mascara_valida
        ]
        / denominador.loc[
            mascara_valida
        ]
    )

    return resultado


# ============================================================
# PREPARAÇÃO DE EOL OU UFV POR HORA E SUBSISTEMA
# ============================================================

def preparar_curtailment_horario_fonte_cp45(
    df_curtailment,
    fonte,
):
    """
    Prepara curtailment ENE e geração esperada de uma
    fonte renovável por hora e subsistema.

    A base original possui registros de 30 minutos.
    Portanto:

    MW × 0,5 hora = MWh

    Somente o curtailment com código ENE compõe o
    curtailment atual utilizado na análise CP45.

    A geração esperada não é ajustada pela retirada
    de CNF ou REL.

    Parâmetros
    ----------
    df_curtailment : pandas.DataFrame
        Base consolidada de curtailment.

    fonte : str
        EOL ou UFV.

    Retorno
    -------
    pandas.DataFrame
        Base horária por fonte e subsistema.
    """

    colunas_obrigatorias = {
        "din_instante",
        "fonte",
        "id_subsistema",
        "cod_razaorestricao",
        "val_curtailment",
        "val_geracao_esperada",
    }

    validar_dataframe(
        df=df_curtailment,
        nome_base="df_curtailment",
        colunas_obrigatorias=(
            colunas_obrigatorias
        ),
    )

    fonte = str(
        fonte
    ).strip().upper()

    if fonte not in FONTES_RENOVAVEIS_CP45:
        raise ValueError(
            "A fonte deve ser EOL ou UFV."
        )

    base = df_curtailment.copy()

    base["fonte"] = (
        base["fonte"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    base = base[
        base["fonte"].eq(
            fonte
        )
    ].copy()

    if base.empty:
        raise ValueError(
            "Não foram encontrados registros para "
            f"a fonte {fonte}."
        )

    base["din_instante"] = pd.to_datetime(
        base["din_instante"],
        errors="coerce",
    )

    base["subsistema"] = (
        padronizar_subsistema(
            base[
                "id_subsistema"
            ]
        )
    )

    base["cod_razaorestricao"] = (
        base["cod_razaorestricao"]
        .astype("string")
        .str.strip()
        .str.upper()
        .fillna("SEM_CODIGO")
        .replace(
            "",
            "SEM_CODIGO",
        )
    )

    base["val_curtailment"] = (
        pd.to_numeric(
            base["val_curtailment"],
            errors="coerce",
        )
        .fillna(0.0)
        .clip(lower=0)
    )

    base["val_geracao_esperada"] = (
        pd.to_numeric(
            base[
                "val_geracao_esperada"
            ],
            errors="coerce",
        )
        .fillna(0.0)
        .clip(lower=0)
    )

    base = base.dropna(
        subset=[
            "din_instante",
            "subsistema",
        ]
    ).copy()

    if base.empty:
        raise ValueError(
            "Não restaram registros válidos para "
            f"a fonte {fonte}."
        )

    # Registros 00 e 30 são consolidados na hora cheia.
    base["din_instante_hora"] = (
        base["din_instante"]
        .dt.floor("h")
    )

    mascara_curtailment_ene = (
        base["cod_razaorestricao"]
        .eq(
            TIPO_CURTAILMENT_CP45
        )
        .fillna(False)
        .to_numpy(
            dtype=bool
        )
    )
    
    base["curtailment_ene_mwh"] = np.where(
        mascara_curtailment_ene,
        base["val_curtailment"] * 0.5,
        0.0,
    )

    base[
        "geracao_esperada_mwh"
    ] = (
        base[
            "val_geracao_esperada"
        ]
        * 0.5
    )

    nome_fonte = fonte.lower()

    resultado = (
        base
        .groupby(
            [
                "din_instante_hora",
                "subsistema",
            ],
            as_index=False,
            observed=True,
        )
        .agg(
            curtailment_mwh=(
                "curtailment_ene_mwh",
                "sum",
            ),
            geracao_mwh=(
                "geracao_esperada_mwh",
                "sum",
            ),
        )
        .rename(
            columns={
                "din_instante_hora": (
                    "din_instante"
                ),
                "curtailment_mwh": (
                    f"curtailment_"
                    f"{nome_fonte}_mwh"
                ),
                "geracao_mwh": (
                    f"geracao_"
                    f"{nome_fonte}_mwh"
                ),
            }
        )
    )

    resultado[
        f"corte_{nome_fonte}_pct"
    ] = calcular_percentual_seguro(
        numerador=resultado[
            f"curtailment_{nome_fonte}_mwh"
        ],
        denominador=resultado[
            f"geracao_{nome_fonte}_mwh"
        ],
    )

    return (
        resultado
        .sort_values(
            [
                "din_instante",
                "subsistema",
            ]
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# PREPARAÇÃO DA EVT E GERAÇÃO HIDRÁULICA
# ============================================================

def preparar_hidro_horario_cp45(
    df_evt,
):
    """
    Prepara EVT e geração hidráulica por hora e
    subsistema.

    A base EVT possui periodicidade horária. Portanto:

    MWmed × 1 hora = MWh

    São criadas duas formas de geração hidráulica:

    1. Condicionada:
       geração + EVT somente nas horas em que EVT > 0.

    2. Completa:
       geração + EVT em todas as horas.

    Parâmetros
    ----------
    df_evt : pandas.DataFrame
        Base tratada por coleta_evt.py.

    Retorno
    -------
    pandas.DataFrame
        Base horária hidráulica por subsistema.
    """

    colunas_obrigatorias = {
        "din_instante",
        "id_subsistema",
        "val_geracao",
        "val_energiavertidaturbinavel",
    }

    validar_dataframe(
        df=df_evt,
        nome_base="df_evt",
        colunas_obrigatorias=(
            colunas_obrigatorias
        ),
    )

    base = df_evt.copy()

    base["din_instante"] = (
        pd.to_datetime(
            base["din_instante"],
            errors="coerce",
        )
        .dt.floor("h")
    )

    base["subsistema"] = (
        padronizar_subsistema(
            base[
                "id_subsistema"
            ]
        )
    )

    base["val_geracao"] = (
        pd.to_numeric(
            base["val_geracao"],
            errors="coerce",
        )
        .fillna(0.0)
        .clip(lower=0)
    )

    base[
        "val_energiavertidaturbinavel"
    ] = (
        pd.to_numeric(
            base[
                "val_energiavertidaturbinavel"
            ],
            errors="coerce",
        )
        .fillna(0.0)
        .clip(lower=0)
    )

    base = base.dropna(
        subset=[
            "din_instante",
            "subsistema",
        ]
    ).copy()

    if base.empty:
        raise ValueError(
            "Não restaram registros válidos na "
            "base hidráulica."
        )

    base["geracao_hidro_mwh"] = (
        base["val_geracao"]
    )

    base["evt_mwh"] = (
        base[
            "val_energiavertidaturbinavel"
        ]
    )

    base[
        "geracao_hidro_condicionada_mwh"
    ] = np.where(
        base["evt_mwh"] > 0,
        (
            base["geracao_hidro_mwh"]
            + base["evt_mwh"]
        ),
        0.0,
    )

    base[
        "geracao_hidro_completa_mwh"
    ] = (
        base["geracao_hidro_mwh"]
        + base["evt_mwh"]
    )

    resultado = (
        base
        .groupby(
            [
                "din_instante",
                "subsistema",
            ],
            as_index=False,
            observed=True,
        )
        .agg(
            evt_mwh=(
                "evt_mwh",
                "sum",
            ),
            geracao_hidro_mwh=(
                "geracao_hidro_mwh",
                "sum",
            ),
            geracao_hidro_condicionada_mwh=(
                "geracao_hidro_condicionada_mwh",
                "sum",
            ),
            geracao_hidro_completa_mwh=(
                "geracao_hidro_completa_mwh",
                "sum",
            ),
        )
    )

    resultado[
        "corte_hidro_condicionado_pct"
    ] = calcular_percentual_seguro(
        numerador=resultado[
            "evt_mwh"
        ],
        denominador=resultado[
            "geracao_hidro_condicionada_mwh"
        ],
    )

    resultado[
        "corte_hidro_completo_pct"
    ] = calcular_percentual_seguro(
        numerador=resultado[
            "evt_mwh"
        ],
        denominador=resultado[
            "geracao_hidro_completa_mwh"
        ],
    )

    return (
        resultado
        .sort_values(
            [
                "din_instante",
                "subsistema",
            ]
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# PREPARAÇÃO DO DESCASAMENTO DE PLD
# ============================================================

def preparar_descolamento_horario_cp45(
    df_pld_aberto,
):
    """
    Prepara o indicador horário de descolamento de PLD.

    A função espera a base produzida por
    preparar_pld_aberto() de dados_pld.py.

    Parâmetros
    ----------
    df_pld_aberto : pandas.DataFrame
        Base de PLD aberta por submercado.

    Retorno
    -------
    pandas.DataFrame
        Base com uma linha por instante.
    """

    colunas_obrigatorias = {
        "DIN_INSTANTE",
        "DESCOLAMENTO_HORARIO",
        "AMPLITUDE_DESCOLAMENTO",
    }

    validar_dataframe(
        df=df_pld_aberto,
        nome_base="df_pld_aberto",
        colunas_obrigatorias=(
            colunas_obrigatorias
        ),
    )

    colunas_opcionais = [
        coluna
        for coluna in [
            "PLD_SUDESTE",
            "PLD_SUL",
            "PLD_NORDESTE",
            "PLD_NORTE",
            "PLD_MINIMO",
            "PLD_MAXIMO",
            "QUANTIDADE_SUBMERCADOS",
        ]
        if coluna
        in df_pld_aberto.columns
    ]

    resultado = df_pld_aberto[
        [
            "DIN_INSTANTE",
            "DESCOLAMENTO_HORARIO",
            "AMPLITUDE_DESCOLAMENTO",
            *colunas_opcionais,
        ]
    ].copy()

    resultado = resultado.rename(
        columns={
            "DIN_INSTANTE": "din_instante",
            "DESCOLAMENTO_HORARIO": (
                "descolamento_horario"
            ),
            "AMPLITUDE_DESCOLAMENTO": (
                "amplitude_descolamento"
            ),
        }
    )

    resultado["din_instante"] = (
        pd.to_datetime(
            resultado["din_instante"],
            errors="coerce",
        )
        .dt.floor("h")
    )

    resultado[
        "descolamento_horario"
    ] = (
        resultado[
            "descolamento_horario"
        ]
        .fillna(False)
        .astype(bool)
    )

    resultado[
        "amplitude_descolamento"
    ] = (
        pd.to_numeric(
            resultado[
                "amplitude_descolamento"
            ],
            errors="coerce",
        )
        .fillna(0.0)
    )

    resultado = resultado.dropna(
        subset=[
            "din_instante",
        ]
    ).copy()

    duplicidades = resultado.duplicated(
        subset=[
            "din_instante",
        ],
        keep=False,
    )

    if duplicidades.any():
        raise ValueError(
            "A base de PLD possui "
            f"{int(duplicidades.sum())} linhas "
            "envolvidas em duplicidades da chave "
            "din_instante."
        )

    return (
        resultado
        .sort_values(
            "din_instante"
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# MONTAGEM DA BASE HORÁRIA DE FONTES
# ============================================================

def montar_base_fontes_cp45(
    df_curtailment,
    df_evt,
    df_pld_aberto,
):
    """
    Monta a base horária de fontes e subsistemas da CP45.

    A base final reúne:

    - curtailment ENE EOL;
    - geração esperada EOL;
    - curtailment ENE UFV;
    - geração esperada UFV;
    - EVT;
    - geração hidráulica;
    - geração hidráulica condicionada;
    - geração hidráulica completa;
    - descolamento de PLD.

    Retorno
    -------
    pandas.DataFrame
        Base horária por instante e subsistema.
    """

    base_eol = (
        preparar_curtailment_horario_fonte_cp45(
            df_curtailment=(
                df_curtailment
            ),
            fonte="EOL",
        )
    )

    base_ufv = (
        preparar_curtailment_horario_fonte_cp45(
            df_curtailment=(
                df_curtailment
            ),
            fonte="UFV",
        )
    )

    base_hidro = (
        preparar_hidro_horario_cp45(
            df_evt=df_evt,
        )
    )

    base_pld = (
        preparar_descolamento_horario_cp45(
            df_pld_aberto=(
                df_pld_aberto
            ),
        )
    )

    chaves_fontes = [
        "din_instante",
        "subsistema",
    ]

    base = (
        base_eol
        .merge(
            base_ufv,
            on=chaves_fontes,
            how="outer",
            validate="one_to_one",
        )
        .merge(
            base_hidro,
            on=chaves_fontes,
            how="outer",
            validate="one_to_one",
        )
        .merge(
            base_pld,
            on="din_instante",
            how="left",
            validate="many_to_one",
        )
    )

    colunas_energia = [
        "curtailment_eol_mwh",
        "geracao_eol_mwh",
        "curtailment_ufv_mwh",
        "geracao_ufv_mwh",
        "evt_mwh",
        "geracao_hidro_mwh",
        "geracao_hidro_condicionada_mwh",
        "geracao_hidro_completa_mwh",
    ]

    for coluna in colunas_energia:
        base[coluna] = (
            pd.to_numeric(
                base[coluna],
                errors="coerce",
            )
            .fillna(0.0)
        )

    colunas_percentuais = [
        "corte_eol_pct",
        "corte_ufv_pct",
        "corte_hidro_condicionado_pct",
        "corte_hidro_completo_pct",
        "amplitude_descolamento",
    ]

    for coluna in colunas_percentuais:
        if coluna in base.columns:
            base[coluna] = (
                pd.to_numeric(
                    base[coluna],
                    errors="coerce",
                )
                .fillna(0.0)
            )

    base[
        "descolamento_horario"
    ] = (
        base[
            "descolamento_horario"
        ]
        .fillna(False)
        .astype(bool)
    )

    base["ano"] = (
        base["din_instante"]
        .dt.year
        .astype("int16")
    )

    base["mes"] = (
        base["din_instante"]
        .dt.month
        .astype("int8")
    )

    base["dia"] = (
        base["din_instante"]
        .dt.normalize()
    )

    base["hora"] = (
        base["din_instante"]
        .dt.hour
        .astype("int8")
    )

    base["semestre"] = np.where(
        base["mes"] <= 6,
        (
            "H1/"
            + base["ano"].astype(str)
        ),
        (
            "H2/"
            + base["ano"].astype(str)
        ),
    )

    colunas_inicio = [
        "din_instante",
        "semestre",
        "dia",
        "hora",
        "ano",
        "mes",
        "subsistema",
        "descolamento_horario",
        "amplitude_descolamento",
    ]

    outras_colunas = [
        coluna
        for coluna in base.columns
        if coluna not in colunas_inicio
    ]

    base = base[
        colunas_inicio
        + outras_colunas
    ]

    duplicidades = base.duplicated(
        subset=chaves_fontes,
        keep=False,
    )

    if duplicidades.any():
        raise ValueError(
            "A base integrada da CP45 possui "
            f"{int(duplicidades.sum())} linhas "
            "envolvidas em duplicidades da chave "
            "din_instante e subsistema."
        )

    return (
        base
        .sort_values(
            chaves_fontes
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# PREPARAÇÃO HORÁRIA DOS ATIVOS
# ============================================================

def preparar_ativos_horarios_cp45(
    df_curtailment,
):
    """
    Prepara todos os ativos EOL e UFV em granularidade
    horária para a análise CP45.

    O curtailment atual considera somente ENE.

    A geração esperada é utilizada sem ajuste de CNF
    ou REL.

    Parâmetros
    ----------
    df_curtailment : pandas.DataFrame
        Base consolidada de curtailment EOL e UFV.

    Retorno
    -------
    pandas.DataFrame
        Base horária de todos os ativos disponíveis.
    """

    colunas_obrigatorias = {
        "nom_usina",
        "id_subsistema",
        "din_instante",
        "cod_razaorestricao",
        "val_curtailment",
        "val_geracao_esperada",
        "fonte",
    }

    validar_dataframe(
        df=df_curtailment,
        nome_base="df_curtailment",
        colunas_obrigatorias=(
            colunas_obrigatorias
        ),
    )

    base = df_curtailment.copy()

    base["din_instante"] = pd.to_datetime(
        base["din_instante"],
        errors="coerce",
    )

    base["ativo"] = (
        base["nom_usina"]
        .astype("string")
        .str.strip()
    )

    base["fonte"] = (
        base["fonte"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    base["subsistema"] = (
        padronizar_subsistema(
            base[
                "id_subsistema"
            ]
        )
    )

    base["cod_razaorestricao"] = (
        base["cod_razaorestricao"]
        .astype("string")
        .str.strip()
        .str.upper()
        .fillna("SEM_CODIGO")
        .replace(
            "",
            "SEM_CODIGO",
        )
    )

    base["val_curtailment"] = (
        pd.to_numeric(
            base["val_curtailment"],
            errors="coerce",
        )
        .fillna(0.0)
        .clip(lower=0)
    )

    base["val_geracao_esperada"] = (
        pd.to_numeric(
            base[
                "val_geracao_esperada"
            ],
            errors="coerce",
        )
        .fillna(0.0)
        .clip(lower=0)
    )

    base = base[
        base["fonte"].isin(
            FONTES_RENOVAVEIS_CP45
        )
    ].copy()

    base = base.dropna(
        subset=[
            "din_instante",
            "ativo",
            "subsistema",
        ]
    ).copy()

    if base.empty:
        raise ValueError(
            "Não restaram ativos válidos para a CP45."
        )

    base["din_instante_hora"] = (
        base["din_instante"]
        .dt.floor("h")
    )

    mascara_curtailment_ene = (
        base["cod_razaorestricao"]
        .eq(
            TIPO_CURTAILMENT_CP45
        )
        .fillna(False)
        .to_numpy(
            dtype=bool
        )
    )
    
    base["curtailment_atual_mwh"] = np.where(
        mascara_curtailment_ene,
        base["val_curtailment"] * 0.5,
        0.0,
    )

    base[
        "geracao_esperada_mwh"
    ] = (
        base[
            "val_geracao_esperada"
        ]
        * 0.5
    )

    resultado = (
        base
        .groupby(
            [
                "din_instante_hora",
                "ativo",
                "subsistema",
                "fonte",
            ],
            as_index=False,
            observed=True,
        )
        .agg(
            curtailment_atual_mwh=(
                "curtailment_atual_mwh",
                "sum",
            ),
            geracao_esperada_mwh=(
                "geracao_esperada_mwh",
                "sum",
            ),
        )
        .rename(
            columns={
                "din_instante_hora": (
                    "din_instante"
                ),
            }
        )
    )

    resultado["corte_atual_pct"] = (
        calcular_percentual_seguro(
            numerador=resultado[
                "curtailment_atual_mwh"
            ],
            denominador=resultado[
                "geracao_esperada_mwh"
            ],
        )
    )

    resultado["ano"] = (
        resultado["din_instante"]
        .dt.year
        .astype("int16")
    )

    resultado["mes"] = (
        resultado["din_instante"]
        .dt.month
        .astype("int8")
    )

    resultado["dia"] = (
        resultado["din_instante"]
        .dt.normalize()
    )

    resultado["hora"] = (
        resultado["din_instante"]
        .dt.hour
        .astype("int8")
    )

    resultado["semestre"] = np.where(
        resultado["mes"] <= 6,
        (
            "H1/"
            + resultado["ano"].astype(str)
        ),
        (
            "H2/"
            + resultado["ano"].astype(str)
        ),
    )

    ordem_colunas = [
        "din_instante",
        "semestre",
        "dia",
        "hora",
        "ano",
        "mes",
        "ativo",
        "subsistema",
        "fonte",
        "curtailment_atual_mwh",
        "geracao_esperada_mwh",
        "corte_atual_pct",
    ]

    resultado = resultado[
        ordem_colunas
    ]

    duplicidades = resultado.duplicated(
        subset=[
            "din_instante",
            "ativo",
        ],
        keep=False,
    )

    if duplicidades.any():
        raise ValueError(
            "A base de ativos possui "
            f"{int(duplicidades.sum())} linhas "
            "envolvidas em duplicidades de "
            "din_instante e ativo."
        )

    return (
        resultado
        .sort_values(
            [
                "din_instante",
                "ativo",
            ]
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# FILTRO DE PERÍODO
# ============================================================

def filtrar_periodo_cp45(
    df,
    ano_inicial,
    mes_inicial,
    ano_final,
    mes_final,
):
    """
    Filtra uma base da CP45 por intervalo mensal.
    """

    if not isinstance(
        df,
        pd.DataFrame,
    ):
        raise TypeError(
            "df deve ser um DataFrame."
        )

    if "din_instante" not in df.columns:
        raise ValueError(
            "A base não possui a coluna din_instante."
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
            "O período inicial não pode ser posterior "
            "ao período final."
        )

    instantes = pd.to_datetime(
        df["din_instante"],
        errors="coerce",
    )

    mascara_periodo = (
        (instantes >= data_inicial)
        & (
            instantes
            < data_final_exclusiva
        )
    )

    resultado = (
        df.loc[
            mascara_periodo
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )

    if resultado.empty:
        raise ValueError(
            "Não foram encontrados registros para "
            "o período informado."
        )

    return resultado
