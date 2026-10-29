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

def aplicar_cenarios_ativos_cp45(
    df_ativos_cp45,
    df_taxas_cp45,
):
    """
    Aplica as taxas horárias dos cenários da CP45
    à geração esperada de cada ativo.

    A base dos ativos deve possuir uma linha por:

    din_instante + ativo + subsistema + fonte

    A base de taxas deve possuir uma linha por:

    din_instante + subsistema

    Para os cenários 1, 2 e 3, a taxa é comum às
    fontes do mesmo subsistema.

    Para o cenário 4, cada ativo recebe a taxa
    correspondente à própria fonte:

    - EOL recebe a taxa EOL;
    - UFV recebe a taxa UFV.

    Parâmetros
    ----------
    df_ativos_cp45 : pandas.DataFrame
        Base horária de ativos produzida por
        preparar_ativos_horarios_cp45().

    df_taxas_cp45 : pandas.DataFrame
        Base horária de taxas produzida por
        calcular_taxas_cenarios_cp45().

    Retorno
    -------
    pandas.DataFrame
        Base horária dos ativos com cenário atual
        e cenários simulados de 1A a 4B.
    """

    if not isinstance(
        df_ativos_cp45,
        pd.DataFrame,
    ):
        raise TypeError(
            "df_ativos_cp45 deve ser um DataFrame."
        )

    if not isinstance(
        df_taxas_cp45,
        pd.DataFrame,
    ):
        raise TypeError(
            "df_taxas_cp45 deve ser um DataFrame."
        )

    if df_ativos_cp45.empty:
        raise ValueError(
            "A base horária de ativos está vazia."
        )

    if df_taxas_cp45.empty:
        raise ValueError(
            "A base horária de taxas está vazia."
        )

    colunas_obrigatorias_ativos = {
        "din_instante",
        "ativo",
        "subsistema",
        "fonte",
        "curtailment_atual_mwh",
        "geracao_esperada_mwh",
        "corte_atual_pct",
    }

    colunas_obrigatorias_taxas = {
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
    }

    colunas_ausentes_ativos = (
        colunas_obrigatorias_ativos
        - set(
            df_ativos_cp45.columns
        )
    )

    if colunas_ausentes_ativos:
        raise ValueError(
            "A base horária de ativos não possui "
            "as colunas obrigatórias: "
            f"{sorted(colunas_ausentes_ativos)}."
        )

    colunas_ausentes_taxas = (
        colunas_obrigatorias_taxas
        - set(
            df_taxas_cp45.columns
        )
    )

    if colunas_ausentes_taxas:
        raise ValueError(
            "A base horária de taxas não possui "
            "as colunas obrigatórias: "
            f"{sorted(colunas_ausentes_taxas)}."
        )

    # ========================================================
    # TRATAMENTO DA BASE DE ATIVOS
    # ========================================================

    ativos = df_ativos_cp45.copy()

    ativos["din_instante"] = pd.to_datetime(
        ativos["din_instante"],
        errors="coerce",
    ).dt.floor("h")

    ativos["ativo"] = (
        ativos["ativo"]
        .astype("string")
        .str.strip()
    )

    ativos["subsistema"] = (
        ativos["subsistema"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    ativos["fonte"] = (
        ativos["fonte"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    for coluna in [
        "curtailment_atual_mwh",
        "geracao_esperada_mwh",
        "corte_atual_pct",
    ]:
        ativos[coluna] = (
            pd.to_numeric(
                ativos[coluna],
                errors="coerce",
            )
            .fillna(0.0)
        )

    ativos = ativos.dropna(
        subset=[
            "din_instante",
            "ativo",
            "subsistema",
            "fonte",
        ]
    ).copy()

    ativos = ativos[
        ativos["fonte"].isin(
            [
                "EOL",
                "UFV",
            ]
        )
    ].copy()

    if ativos.empty:
        raise ValueError(
            "Não restaram ativos EOL ou UFV válidos."
        )

    # ========================================================
    # TRATAMENTO DA BASE DE TAXAS
    # ========================================================

    taxas = df_taxas_cp45[
        [
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
        ]
    ].copy()

    taxas["din_instante"] = pd.to_datetime(
        taxas["din_instante"],
        errors="coerce",
    ).dt.floor("h")

    taxas["subsistema"] = (
        taxas["subsistema"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    taxas["descolamento_horario"] = (
        taxas["descolamento_horario"]
        .fillna(False)
        .astype(bool)
    )

    colunas_taxas_percentuais = [
        coluna
        for coluna in taxas.columns
        if coluna.endswith(
            "_pct"
        )
    ]

    for coluna in colunas_taxas_percentuais:
        taxas[coluna] = (
            pd.to_numeric(
                taxas[coluna],
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

    taxas = taxas.dropna(
        subset=[
            "din_instante",
            "subsistema",
        ]
    ).copy()

    duplicidades_taxas = taxas.duplicated(
        subset=[
            "din_instante",
            "subsistema",
        ],
        keep=False,
    )

    if duplicidades_taxas.any():
        raise ValueError(
            "A base de taxas possui duplicidades na "
            "chave din_instante e subsistema."
        )

    # ========================================================
    # JUNÇÃO DOS ATIVOS COM AS TAXAS
    # ========================================================

    resultado = ativos.merge(
        taxas,
        on=[
            "din_instante",
            "subsistema",
        ],
        how="left",
        validate="many_to_one",
        indicator=True,
    )

    sem_correspondencia = (
        resultado["_merge"]
        .ne("both")
    )

    quantidade_sem_correspondencia = int(
        sem_correspondencia.sum()
    )

    resultado = resultado.drop(
        columns="_merge"
    )

    # Taxas ausentes ficam em zero, mas a quantidade é
    # registrada nos atributos para permitir diagnóstico.

    for coluna in [
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
    ]:
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

    resultado[
        "descolamento_horario"
    ] = (
        resultado[
            "descolamento_horario"
        ]
        .fillna(False)
        .astype(bool)
    )

    # ========================================================
    # CENÁRIOS 1, 2 E 3
    # ========================================================

    for numero_cenario in [
        1,
        2,
        3,
    ]:
        for condicao in [
            "a",
            "b",
        ]:
            coluna_taxa_origem = (
                f"corte_{numero_cenario}"
                f"{condicao}_pct"
            )

            coluna_corte_destino = (
                f"corte_{numero_cenario}"
                f"{condicao}_pct"
            )

            coluna_curtailment = (
                f"curtailment_{numero_cenario}"
                f"{condicao}_mwh"
            )

            resultado[
                coluna_corte_destino
            ] = resultado[
                coluna_taxa_origem
            ]

            resultado[
                coluna_curtailment
            ] = (
                resultado[
                    "geracao_esperada_mwh"
                ]
                * resultado[
                    coluna_corte_destino
                ]
                / 100
            )

    # ========================================================
    # CENÁRIO 4: TAXA CONFORME A FONTE DO ATIVO
    # ========================================================

    mascara_eol = (
        resultado["fonte"]
        .eq("EOL")
        .fillna(False)
        .to_numpy(
            dtype=bool
        )
    )

    mascara_ufv = (
        resultado["fonte"]
        .eq("UFV")
        .fillna(False)
        .to_numpy(
            dtype=bool
        )
    )

    resultado["corte_4a_pct"] = np.select(
        [
            mascara_eol,
            mascara_ufv,
        ],
        [
            resultado[
                "corte_4a_eol_pct"
            ],
            resultado[
                "corte_4a_ufv_pct"
            ],
        ],
        default=0.0,
    )

    resultado["corte_4b_pct"] = np.select(
        [
            mascara_eol,
            mascara_ufv,
        ],
        [
            resultado[
                "corte_4b_eol_pct"
            ],
            resultado[
                "corte_4b_ufv_pct"
            ],
        ],
        default=0.0,
    )

    resultado["curtailment_4a_mwh"] = (
        resultado["geracao_esperada_mwh"]
        * resultado["corte_4a_pct"]
        / 100
    )

    resultado["curtailment_4b_mwh"] = (
        resultado["geracao_esperada_mwh"]
        * resultado["corte_4b_pct"]
        / 100
    )

    # ========================================================
    # VALIDAÇÃO DOS RESULTADOS NUMÉRICOS
    # ========================================================

    colunas_cenarios = []

    for numero_cenario in [
        1,
        2,
        3,
        4,
    ]:
        for condicao in [
            "a",
            "b",
        ]:
            colunas_cenarios.extend(
                [
                    (
                        f"corte_{numero_cenario}"
                        f"{condicao}_pct"
                    ),
                    (
                        f"curtailment_{numero_cenario}"
                        f"{condicao}_mwh"
                    ),
                ]
            )

    for coluna in colunas_cenarios:
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

    # Curtailment simulado não deve ficar negativo.

    colunas_curtailment_simulado = [
        coluna
        for coluna in colunas_cenarios
        if coluna.startswith(
            "curtailment_"
        )
    ]

    resultado[
        colunas_curtailment_simulado
    ] = (
        resultado[
            colunas_curtailment_simulado
        ]
        .clip(lower=0)
    )

    # ========================================================
    # ORGANIZAÇÃO DAS COLUNAS
    # ========================================================

    colunas_identificacao = [
        coluna
        for coluna in [
            "din_instante",
            "semestre",
            "dia",
            "hora",
            "ano",
            "mes",
            "ativo",
            "subsistema",
            "fonte",
            "descolamento_horario",
        ]
        if coluna in resultado.columns
    ]

    colunas_atuais = [
        "geracao_esperada_mwh",
        "curtailment_atual_mwh",
        "corte_atual_pct",
    ]

    colunas_resultado_cenarios = []

    for numero_cenario in [
        1,
        2,
        3,
        4,
    ]:
        for condicao in [
            "a",
            "b",
        ]:
            colunas_resultado_cenarios.extend(
                [
                    (
                        f"corte_{numero_cenario}"
                        f"{condicao}_pct"
                    ),
                    (
                        f"curtailment_{numero_cenario}"
                        f"{condicao}_mwh"
                    ),
                ]
            )

    resultado = resultado[
        colunas_identificacao
        + colunas_atuais
        + colunas_resultado_cenarios
    ].copy()

    # ========================================================
    # VALIDAÇÃO DA CHAVE FINAL
    # ========================================================

    chave_resultado = [
        "din_instante",
        "ativo",
        "subsistema",
        "fonte",
    ]

    duplicidades_resultado = (
        resultado
        .duplicated(
            subset=chave_resultado,
            keep=False,
        )
    )

    if duplicidades_resultado.any():
        raise ValueError(
            "A base final dos cenários possui "
            f"{int(duplicidades_resultado.sum())} "
            "linhas envolvidas em duplicidades da "
            "chave analítica."
        )

    resultado.attrs[
        "linhas_sem_taxa_correspondente"
    ] = quantidade_sem_correspondencia

    return (
        resultado
        .sort_values(
            [
                "din_instante",
                "ativo",
                "subsistema",
                "fonte",
            ]
        )
        .reset_index(
            drop=True
        )
    )
  
