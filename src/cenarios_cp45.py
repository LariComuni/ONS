"""
Cálculo e aplicação dos cenários da CP45.

Este módulo recebe as bases produzidas por
preparacao_cp45.py e calcula:

- taxas horárias dos cenários 1 a 4;
- condições A, de pool nacional;
- condições B, condicionadas ao descolamento de PLD;
- curtailment simulado para cada ativo.
"""

import numpy as np
import pandas as pd


SUBSISTEMAS_CP45 = [
    "N",
    "NE",
    "S",
    "SE",
]


CENARIOS_CP45 = [
    "1A",
    "1B",
    "2A",
    "2B",
    "3A",
    "3B",
    "4A",
    "4B",
]

COLUNAS_BASE_FONTES_CP45 = {
    "din_instante",
    "subsistema",
    "descolamento_horario",
    "curtailment_eol_mwh",
    "geracao_eol_mwh",
    "curtailment_ufv_mwh",
    "geracao_ufv_mwh",
    "evt_mwh",
    "geracao_hidro_condicionada_mwh",
    "geracao_hidro_completa_mwh",
}

def calcular_percentual_seguro(
    numerador,
    denominador,
):
    """
    Calcula 100 vezes numerador dividido por denominador.

    Quando o denominador for zero, negativo ou ausente,
    o resultado será zero.
    """

    numerador = (
        pd.to_numeric(
            numerador,
            errors="coerce",
        )
        .fillna(0.0)
    )

    denominador = (
        pd.to_numeric(
            denominador,
            errors="coerce",
        )
        .fillna(0.0)
    )

    resultado = np.zeros(
        len(denominador),
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
        ].to_numpy()
        / denominador.loc[
            mascara_valida
        ].to_numpy()
    )

    return resultado

def validar_base_fontes_cp45(
    df_base_fontes,
):
    """
    Valida a base horária de fontes usada no cálculo
    dos cenários da CP45.

    A chave esperada é:

    din_instante + subsistema
    """

    if not isinstance(
        df_base_fontes,
        pd.DataFrame,
    ):
        raise TypeError(
            "df_base_fontes deve ser um DataFrame."
        )

    if df_base_fontes.empty:
        raise ValueError(
            "A base horária de fontes está vazia."
        )

    colunas_ausentes = (
        COLUNAS_BASE_FONTES_CP45
        - set(
            df_base_fontes.columns
        )
    )

    if colunas_ausentes:
        raise ValueError(
            "A base horária de fontes não possui "
            "as colunas obrigatórias: "
            f"{sorted(colunas_ausentes)}."
        )

    duplicidades = (
        df_base_fontes
        .duplicated(
            subset=[
                "din_instante",
                "subsistema",
            ],
            keep=False,
        )
    )

    if duplicidades.any():
        exemplos = (
            df_base_fontes.loc[
                duplicidades,
                [
                    "din_instante",
                    "subsistema",
                ],
            ]
            .head(10)
            .to_dict(
                orient="records"
            )
        )

        raise ValueError(
            "A base horária de fontes possui "
            f"{int(duplicidades.sum())} linhas "
            "envolvidas em duplicidades da chave "
            "din_instante e subsistema. "
            f"Exemplos: {exemplos}"
        )

def calcular_taxas_cenarios_cp45(
    df_base_fontes,
):
    """
    Calcula as taxas horárias dos cenários da CP45.

    Cenário 1
    ----------
    Pool formado por:

    Curtailment:
        EOL + UFV + EVT

    Geração:
        EOL + UFV + geração hidráulica condicionada

    Cenário 2
    ----------
    Pool formado por:

    Curtailment:
        EOL + UFV + EVT

    Geração:
        EOL + UFV + geração hidráulica completa

    Cenário 3
    ----------
    Pool formado somente por EOL e UFV.

    Cenário 4
    ----------
    Taxas calculadas separadamente por fonte:

    - EOL;
    - UFV.

    Condição A
    ----------
    Utiliza a taxa nacional da respectiva composição.

    Condição B
    ----------
    Sem descolamento de PLD:
        utiliza a taxa nacional.

    Com descolamento de PLD:
        utiliza a taxa do próprio subsistema.

    Parâmetros
    ----------
    df_base_fontes : pandas.DataFrame
        Base horária produzida por montar_base_fontes_cp45().

    Retorno
    -------
    pandas.DataFrame
        Taxas horárias por instante e subsistema.
    """

    validar_base_fontes_cp45(
        df_base_fontes
    )

    base = df_base_fontes.copy()

    base["din_instante"] = pd.to_datetime(
        base["din_instante"],
        errors="coerce",
    )

    base["subsistema"] = (
        base["subsistema"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    base["descolamento_horario"] = (
        base["descolamento_horario"]
        .fillna(False)
        .astype(bool)
    )

    colunas_numericas = [
        "curtailment_eol_mwh",
        "geracao_eol_mwh",
        "curtailment_ufv_mwh",
        "geracao_ufv_mwh",
        "evt_mwh",
        "geracao_hidro_condicionada_mwh",
        "geracao_hidro_completa_mwh",
    ]

    for coluna in colunas_numericas:
        base[coluna] = (
            pd.to_numeric(
                base[coluna],
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

    base = base[
        base["subsistema"].isin(
            SUBSISTEMAS_CP45
        )
    ].copy()

    if base.empty:
        raise ValueError(
            "Não restaram registros válidos para "
            "o cálculo dos cenários."
        )

    # ========================================================
    # CENÁRIO 1: HIDRO CONDICIONADA AO EVT
    # ========================================================

    base["curtailment_pool_1_mwh"] = (
        base["curtailment_eol_mwh"]
        + base["curtailment_ufv_mwh"]
        + base["evt_mwh"]
    )

    base["geracao_pool_1_mwh"] = (
        base["geracao_eol_mwh"]
        + base["geracao_ufv_mwh"]
        + base[
            "geracao_hidro_condicionada_mwh"
        ]
    )

    base["taxa_local_1_pct"] = (
        calcular_percentual_seguro(
            numerador=base[
                "curtailment_pool_1_mwh"
            ],
            denominador=base[
                "geracao_pool_1_mwh"
            ],
        )
    )

    # ========================================================
    # CENÁRIO 2: PARQUE HIDRÁULICO COMPLETO
    # ========================================================

    base["curtailment_pool_2_mwh"] = (
        base["curtailment_eol_mwh"]
        + base["curtailment_ufv_mwh"]
        + base["evt_mwh"]
    )

    base["geracao_pool_2_mwh"] = (
        base["geracao_eol_mwh"]
        + base["geracao_ufv_mwh"]
        + base[
            "geracao_hidro_completa_mwh"
        ]
    )

    base["taxa_local_2_pct"] = (
        calcular_percentual_seguro(
            numerador=base[
                "curtailment_pool_2_mwh"
            ],
            denominador=base[
                "geracao_pool_2_mwh"
            ],
        )
    )

    # ========================================================
    # CENÁRIO 3: EOL + UFV
    # ========================================================

    base["curtailment_pool_3_mwh"] = (
        base["curtailment_eol_mwh"]
        + base["curtailment_ufv_mwh"]
    )

    base["geracao_pool_3_mwh"] = (
        base["geracao_eol_mwh"]
        + base["geracao_ufv_mwh"]
    )

    base["taxa_local_3_pct"] = (
        calcular_percentual_seguro(
            numerador=base[
                "curtailment_pool_3_mwh"
            ],
            denominador=base[
                "geracao_pool_3_mwh"
            ],
        )
    )

    # ========================================================
    # CENÁRIO 4: TAXAS POR FONTE
    # ========================================================

    base["taxa_local_4_eol_pct"] = (
        calcular_percentual_seguro(
            numerador=base[
                "curtailment_eol_mwh"
            ],
            denominador=base[
                "geracao_eol_mwh"
            ],
        )
    )

    base["taxa_local_4_ufv_pct"] = (
        calcular_percentual_seguro(
            numerador=base[
                "curtailment_ufv_mwh"
            ],
            denominador=base[
                "geracao_ufv_mwh"
            ],
        )
    )

    # ========================================================
    # TOTAIS NACIONAIS POR INSTANTE
    # ========================================================

    colunas_somar_nacional = [
        "curtailment_pool_1_mwh",
        "geracao_pool_1_mwh",
        "curtailment_pool_2_mwh",
        "geracao_pool_2_mwh",
        "curtailment_pool_3_mwh",
        "geracao_pool_3_mwh",
        "curtailment_eol_mwh",
        "geracao_eol_mwh",
        "curtailment_ufv_mwh",
        "geracao_ufv_mwh",
    ]

    base_nacional = (
        base
        .groupby(
            "din_instante",
            as_index=False,
            observed=True,
        )[colunas_somar_nacional]
        .sum()
    )

    base_nacional["corte_1a_pct"] = (
        calcular_percentual_seguro(
            numerador=base_nacional[
                "curtailment_pool_1_mwh"
            ],
            denominador=base_nacional[
                "geracao_pool_1_mwh"
            ],
        )
    )

    base_nacional["corte_2a_pct"] = (
        calcular_percentual_seguro(
            numerador=base_nacional[
                "curtailment_pool_2_mwh"
            ],
            denominador=base_nacional[
                "geracao_pool_2_mwh"
            ],
        )
    )

    base_nacional["corte_3a_pct"] = (
        calcular_percentual_seguro(
            numerador=base_nacional[
                "curtailment_pool_3_mwh"
            ],
            denominador=base_nacional[
                "geracao_pool_3_mwh"
            ],
        )
    )

    base_nacional["corte_4a_eol_pct"] = (
        calcular_percentual_seguro(
            numerador=base_nacional[
                "curtailment_eol_mwh"
            ],
            denominador=base_nacional[
                "geracao_eol_mwh"
            ],
        )
    )

    base_nacional["corte_4a_ufv_pct"] = (
        calcular_percentual_seguro(
            numerador=base_nacional[
                "curtailment_ufv_mwh"
            ],
            denominador=base_nacional[
                "geracao_ufv_mwh"
            ],
        )
    )

    colunas_taxas_nacionais = [
        "din_instante",
        "corte_1a_pct",
        "corte_2a_pct",
        "corte_3a_pct",
        "corte_4a_eol_pct",
        "corte_4a_ufv_pct",
    ]

    base = base.merge(
        base_nacional[
            colunas_taxas_nacionais
        ],
        on="din_instante",
        how="left",
        validate="many_to_one",
    )

    # ========================================================
    # CONDIÇÕES B: NACIONAL OU SUBSISTEMA CONFORME PLD
    # ========================================================

    descolamento = (
        base["descolamento_horario"]
        .to_numpy(
            dtype=bool
        )
    )

    base["corte_1b_pct"] = np.where(
        descolamento,
        base["taxa_local_1_pct"],
        base["corte_1a_pct"],
    )

    base["corte_2b_pct"] = np.where(
        descolamento,
        base["taxa_local_2_pct"],
        base["corte_2a_pct"],
    )

    base["corte_3b_pct"] = np.where(
        descolamento,
        base["taxa_local_3_pct"],
        base["corte_3a_pct"],
    )

    base["corte_4b_eol_pct"] = np.where(
        descolamento,
        base["taxa_local_4_eol_pct"],
        base["corte_4a_eol_pct"],
    )

    base["corte_4b_ufv_pct"] = np.where(
        descolamento,
        base["taxa_local_4_ufv_pct"],
        base["corte_4a_ufv_pct"],
    )

    # ========================================================
    # ORGANIZAÇÃO DO RETORNO
    # ========================================================

    colunas_resultado = [
        "din_instante",
        "subsistema",
        "descolamento_horario",
        "corte_1a_pct",
        "corte_1b_pct",
        "corte_2a_pct",
        "corte_2b_pct",
        "corte_3a_pct",
        "corte_3b_pct",
        "corte_4a_eol_pct",
        "corte_4b_eol_pct",
        "corte_4a_ufv_pct",
        "corte_4b_ufv_pct",
        "taxa_local_1_pct",
        "taxa_local_2_pct",
        "taxa_local_3_pct",
        "taxa_local_4_eol_pct",
        "taxa_local_4_ufv_pct",
    ]

    resultado = base[
        colunas_resultado
    ].copy()

    colunas_taxas = [
        coluna
        for coluna in resultado.columns
        if coluna.endswith(
            "_pct"
        )
    ]

    for coluna in colunas_taxas:
        resultado[coluna] = (
            pd.to_numeric(
                resultado[coluna],
                errors="coerce",
            )
            .replace(
                [
                    np.inf,
                    -np.inf,
                ],
                0.0,
            )
            .fillna(0.0)
        )

    duplicidades = resultado.duplicated(
        subset=[
            "din_instante",
            "subsistema",
        ],
        keep=False,
    )

    if duplicidades.any():
        raise ValueError(
            "A base de taxas possui duplicidades na "
            "chave din_instante e subsistema."
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
  
