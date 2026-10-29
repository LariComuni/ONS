"""
Leitura, tratamento e consolidação das bases de PLD
utilizadas na análise da CP45.
"""

# ============================================================
# IMPORTAÇÕES
# ============================================================

from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# CAMINHOS
# ============================================================

RAIZ_PROJETO = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

PASTA_PLD = (
    RAIZ_PROJETO
    / "data"
    / "cp45"
    / "pld"
)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

COLUNAS_ESPERADAS_PLD = {
    "MES_REFERENCIA",
    "SUBMERCADO",
    "PERIODO_COMERCIALIZACAO",
    "DIA",
    "HORA",
    "PLD_HORA",
}

COLUNAS_NUMERICAS_PLD = [
    "MES_REFERENCIA",
    "PERIODO_COMERCIALIZACAO",
    "DIA",
    "HORA",
    "PLD_HORA",
]

SUBMERCADOS_PLD = [
    "SUDESTE",
    "SUL",
    "NORDESTE",
    "NORTE",
]

MAPA_COLUNAS_SUBMERCADO = {
    "SUDESTE": "PLD_SUDESTE",
    "SUL": "PLD_SUL",
    "NORDESTE": "PLD_NORDESTE",
    "NORTE": "PLD_NORTE",
}


# ============================================================
# LEITURA DE UM CSV
# ============================================================

def ler_csv_pld(
    caminho,
):
    """
    Lê e valida um arquivo CSV de PLD.

    Parâmetros
    ----------
    caminho : str ou pathlib.Path
        Caminho do arquivo CSV.

    Retorno
    -------
    pandas.DataFrame
        Base de PLD lida e com cabeçalhos padronizados.
    """

    caminho = Path(
        caminho
    )

    if not caminho.exists():
        raise FileNotFoundError(
            "O arquivo de PLD não foi encontrado: "
            f"{caminho}."
        )

    if not caminho.is_file():
        raise ValueError(
            "O caminho informado não corresponde "
            f"a um arquivo: {caminho}."
        )

    try:
        df = pd.read_csv(
            caminho,
            sep=";",
            encoding="utf-8-sig",
            decimal=".",
            low_memory=False,
        )

    except UnicodeDecodeError as erro:
        raise ValueError(
            "Não foi possível interpretar a codificação "
            f"do arquivo {caminho.name}."
        ) from erro

    except pd.errors.ParserError as erro:
        raise ValueError(
            "Não foi possível interpretar a estrutura "
            f"do CSV {caminho.name}."
        ) from erro

    if df.empty:
        raise ValueError(
            "O arquivo de PLD está vazio: "
            f"{caminho.name}."
        )

    df.columns = (
        df.columns
        .astype(
            str
        )
        .str.strip()
        .str.upper()
    )

    colunas_ausentes = (
        COLUNAS_ESPERADAS_PLD
        - set(
            df.columns
        )
    )

    if colunas_ausentes:
        raise ValueError(
            f"{caminho.name}: colunas ausentes: "
            f"{sorted(colunas_ausentes)}."
        )

    df["ARQUIVO_ORIGEM"] = (
        caminho.name
    )

    return df


# ============================================================
# TRATAMENTO DA BASE
# ============================================================

def tratar_base_pld(
    df,
):
    """
    Trata uma base consolidada de PLD.

    Converte colunas numéricas, padroniza submercados,
    cria a data de referência e remove registros
    inválidos.

    Parâmetros
    ----------
    df : pandas.DataFrame
        Base bruta consolidada de PLD.

    Retorno
    -------
    pandas.DataFrame
        Base de PLD tratada em formato longo.
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
            "A base de PLD informada está vazia."
        )

    df = df.copy()

    df.columns = (
        df.columns
        .astype(
            str
        )
        .str.strip()
        .str.upper()
    )

    colunas_ausentes = (
        COLUNAS_ESPERADAS_PLD
        - set(
            df.columns
        )
    )

    if colunas_ausentes:
        raise ValueError(
            "A base consolidada de PLD não possui "
            "as colunas obrigatórias: "
            f"{sorted(colunas_ausentes)}."
        )

    for coluna in COLUNAS_NUMERICAS_PLD:
        df[coluna] = pd.to_numeric(
            df[coluna],
            errors="coerce",
        )

    df["SUBMERCADO"] = (
        df["SUBMERCADO"]
        .astype(
            "string"
        )
        .str.strip()
        .str.upper()
    )

    # Cria AAAAMM com seis caracteres e acrescenta o dia.
    mes_referencia_texto = (
        df["MES_REFERENCIA"]
        .astype(
            "Int64"
        )
        .astype(
            "string"
        )
        .str.zfill(
            6
        )
    )

    dia_texto = (
        df["DIA"]
        .astype(
            "Int64"
        )
        .astype(
            "string"
        )
        .str.zfill(
            2
        )
    )

    df["DATA"] = pd.to_datetime(
        mes_referencia_texto
        + dia_texto,
        format="%Y%m%d",
        errors="coerce",
    )

    df = df.dropna(
        subset=[
            "DATA",
            "HORA",
            "PLD_HORA",
            "SUBMERCADO",
        ]
    ).copy()

    if df.empty:
        raise ValueError(
            "Não restaram registros válidos após "
            "o tratamento da base de PLD."
        )

    # A hora deve estar dentro do intervalo esperado.
    df = df[
        df["HORA"].between(
            0,
            23,
            inclusive="both",
        )
    ].copy()

    if df.empty:
        raise ValueError(
            "Não foram encontrados registros com "
            "horas válidas entre 0 e 23."
        )

    df["HORA"] = (
        df["HORA"]
        .astype(
            "int8"
        )
    )

    df["ANO"] = (
        df["DATA"]
        .dt.year
        .astype(
            "int16"
        )
    )

    df["MES"] = (
        df["DATA"]
        .dt.month
        .astype(
            "int8"
        )
    )

    df["HORA_ROTULO"] = (
        df["HORA"]
        .map(
            lambda hora: (
                f"{int(hora):02d}:00"
            )
        )
    )

    df["DIN_INSTANTE"] = (
        df["DATA"]
        + pd.to_timedelta(
            df["HORA"],
            unit="h",
        )
    )

    # Mantém somente os quatro submercados esperados.
    df = df[
        df["SUBMERCADO"]
        .isin(
            SUBMERCADOS_PLD
        )
    ].copy()

    if df.empty:
        raise ValueError(
            "A base não possui registros para os "
            "submercados esperados."
        )

    colunas_ordenacao = [
        coluna
        for coluna in [
            "DIN_INSTANTE",
            "SUBMERCADO",
            "PERIODO_COMERCIALIZACAO",
        ]
        if coluna in df.columns
    ]

    return (
        df
        .sort_values(
            colunas_ordenacao,
            kind="stable",
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# CONSOLIDAÇÃO DOS ARQUIVOS
# ============================================================

def carregar_bases_pld(
    pasta_pld=PASTA_PLD,
):
    """
    Carrega, concatena e trata todos os CSVs de PLD
    existentes na pasta informada.

    Parâmetros
    ----------
    pasta_pld : str ou pathlib.Path, opcional
        Pasta que contém os arquivos CSV anuais de PLD.

    Retorno
    -------
    tuple
        DataFrame tratado e relatório da leitura.
    """

    pasta_pld = Path(
        pasta_pld
    )

    if not pasta_pld.exists():
        raise FileNotFoundError(
            "A pasta de PLD não foi encontrada: "
            f"{pasta_pld}."
        )

    if not pasta_pld.is_dir():
        raise ValueError(
            "O caminho da base de PLD não corresponde "
            f"a uma pasta: {pasta_pld}."
        )

    arquivos_pld = sorted(
        pasta_pld.glob(
            "*.csv"
        )
    )

    if not arquivos_pld:
        raise FileNotFoundError(
            "Nenhum arquivo CSV foi encontrado na "
            f"pasta: {pasta_pld}."
        )

    bases_pld = []
    arquivos_carregados = []
    erros_leitura = []

    for arquivo in arquivos_pld:
        try:
            df_arquivo = ler_csv_pld(
                arquivo
            )

            bases_pld.append(
                df_arquivo
            )

            arquivos_carregados.append(
                arquivo.name
            )

        except (
            FileNotFoundError,
            ValueError,
            TypeError,
        ) as erro:
            erros_leitura.append(
                {
                    "arquivo": arquivo.name,
                    "erro": str(
                        erro
                    ),
                }
            )

    if not bases_pld:
        mensagens_erros = "; ".join(
            (
                f"{item['arquivo']}: "
                f"{item['erro']}"
            )
            for item in erros_leitura
        )

        raise ValueError(
            "Nenhuma base de PLD pôde ser carregada. "
            f"Erros: {mensagens_erros}"
        )

    df_pld = pd.concat(
        bases_pld,
        ignore_index=True,
    )

    quantidade_antes = len(
        df_pld
    )

    df_pld = (
        df_pld
        .drop_duplicates()
        .reset_index(
            drop=True
        )
    )

    duplicidades_completas_removidas = (
        quantidade_antes
        - len(
            df_pld
        )
    )

    df_pld = tratar_base_pld(
        df_pld
    )

    memoria_mb = (
        df_pld
        .memory_usage(
            deep=True
        )
        .sum()
        / (1024 ** 2)
    )

    relatorio = {
        "pasta": str(
            pasta_pld
        ),
        "arquivos_encontrados": [
            arquivo.name
            for arquivo in arquivos_pld
        ],
        "arquivos_carregados": (
            arquivos_carregados
        ),
        "erros_leitura": erros_leitura,
        "quantidade_arquivos": len(
            arquivos_carregados
        ),
        "quantidade_linhas": len(
            df_pld
        ),
        "quantidade_colunas": len(
            df_pld.columns
        ),
        "duplicidades_completas_removidas": (
            duplicidades_completas_removidas
        ),
        "memoria_mb": round(
            memoria_mb,
            2,
        ),
    }

    return (
        df_pld,
        relatorio,
    )


# ============================================================
# VALIDAÇÃO DA CHAVE HORÁRIA
# ============================================================

def validar_chave_pld(
    df_pld,
):
    """
    Verifica se existe mais de um PLD para a mesma
    combinação de instante e submercado.

    Retorno
    -------
    pandas.DataFrame
        Registros duplicados na chave analítica.
    """

    if not isinstance(
        df_pld,
        pd.DataFrame,
    ):
        raise TypeError(
            "df_pld deve ser um DataFrame."
        )

    colunas_obrigatorias = {
        "DIN_INSTANTE",
        "SUBMERCADO",
        "PLD_HORA",
    }

    colunas_ausentes = (
        colunas_obrigatorias
        - set(
            df_pld.columns
        )
    )

    if colunas_ausentes:
        raise ValueError(
            "A base tratada não possui as colunas "
            "necessárias para validar a chave: "
            f"{sorted(colunas_ausentes)}."
        )

    contagem_chave = (
        df_pld
        .groupby(
            [
                "DIN_INSTANTE",
                "SUBMERCADO",
            ],
            as_index=False,
            observed=True,
            dropna=False,
        )
        .agg(
            quantidade_registros=(
                "PLD_HORA",
                "size",
            ),
            quantidade_valores_pld=(
                "PLD_HORA",
                "nunique",
            ),
        )
    )

    return (
        contagem_chave[
            (
                contagem_chave[
                    "quantidade_registros"
                ] > 1
            )
            | (
                contagem_chave[
                    "quantidade_valores_pld"
                ] > 1
            )
        ]
        .sort_values(
            [
                "DIN_INSTANTE",
                "SUBMERCADO",
            ]
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# BASE ABERTA POR SUBMERCADO
# ============================================================

def preparar_pld_aberto(
    df_pld,
):
    """
    Transforma a base de PLD em formato aberto, com
    uma coluna para cada submercado.

    Retorno
    -------
    pandas.DataFrame
        Base horária com PLD por submercado.
    """

    if not isinstance(
        df_pld,
        pd.DataFrame,
    ):
        raise TypeError(
            "df_pld deve ser um DataFrame."
        )

    if df_pld.empty:
        raise ValueError(
            "A base de PLD está vazia."
        )

    duplicidades_chave = validar_chave_pld(
        df_pld
    )

    if not duplicidades_chave.empty:
        raise ValueError(
            "Foram encontrados registros duplicados "
            "para a mesma combinação de instante e "
            "submercado. Verifique a base antes de "
            "abrir os submercados em colunas."
        )

    df_pld_aberto = (
        df_pld
        .pivot(
            index="DIN_INSTANTE",
            columns="SUBMERCADO",
            values="PLD_HORA",
        )
        .reset_index()
    )

    df_pld_aberto.columns.name = None

    df_pld_aberto = (
        df_pld_aberto
        .rename(
            columns=MAPA_COLUNAS_SUBMERCADO
        )
    )

    for coluna in MAPA_COLUNAS_SUBMERCADO.values():
        if coluna not in df_pld_aberto.columns:
            df_pld_aberto[coluna] = np.nan

    df_pld_aberto["DATA"] = (
        df_pld_aberto[
            "DIN_INSTANTE"
        ]
        .dt.normalize()
    )

    df_pld_aberto["HORA"] = (
        df_pld_aberto[
            "DIN_INSTANTE"
        ]
        .dt.hour
        .astype(
            "int8"
        )
    )

    colunas_pld = list(
        MAPA_COLUNAS_SUBMERCADO.values()
    )

    df_pld_aberto[
        "PLD_MINIMO"
    ] = (
        df_pld_aberto[
            colunas_pld
        ]
        .min(
            axis=1,
            skipna=True,
        )
    )

    df_pld_aberto[
        "PLD_MAXIMO"
    ] = (
        df_pld_aberto[
            colunas_pld
        ]
        .max(
            axis=1,
            skipna=True,
        )
    )

    df_pld_aberto[
        "AMPLITUDE_DESCOLAMENTO"
    ] = (
        df_pld_aberto[
            "PLD_MAXIMO"
        ]
        - df_pld_aberto[
            "PLD_MINIMO"
        ]
    )

    # O descolamento só é considerado válido quando
    # os quatro submercados possuem PLD no instante.

    df_pld_aberto[
        "QUANTIDADE_SUBMERCADOS"
    ] = (
        df_pld_aberto[
            colunas_pld
        ]
        .notna()
        .sum(
            axis=1
        )
        .astype(
            "int8"
        )
    )

    df_pld_aberto[
        "DESCOLAMENTO_HORARIO"
    ] = (
        (
            df_pld_aberto[
                "QUANTIDADE_SUBMERCADOS"
            ] == 4
        )
        & (
            df_pld_aberto[
                "AMPLITUDE_DESCOLAMENTO"
            ] > 0
        )
    )

    colunas_resultado = [
        "DIN_INSTANTE",
        "DATA",
        "HORA",
        "PLD_SUDESTE",
        "PLD_SUL",
        "PLD_NORDESTE",
        "PLD_NORTE",
        "PLD_MINIMO",
        "PLD_MAXIMO",
        "AMPLITUDE_DESCOLAMENTO",
        "QUANTIDADE_SUBMERCADOS",
        "DESCOLAMENTO_HORARIO",
    ]

    return (
        df_pld_aberto[
            colunas_resultado
        ]
        .sort_values(
            "DIN_INSTANTE"
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# FILTRO DE PERÍODO
# ============================================================

def filtrar_pld_periodo(
    df_pld,
    ano_inicial,
    mes_inicial,
    ano_final,
    mes_final,
):
    """
    Filtra uma base tratada de PLD por intervalo mensal.
    """

    if not isinstance(
        df_pld,
        pd.DataFrame,
    ):
        raise TypeError(
            "df_pld deve ser um DataFrame."
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

    coluna_data = (
        "DIN_INSTANTE"
        if "DIN_INSTANTE" in df_pld.columns
        else "DATA"
    )

    datas = pd.to_datetime(
        df_pld[
            coluna_data
        ],
        errors="coerce",
    )

    mascara_periodo = (
        (datas >= data_inicial)
        & (
            datas
            < data_final_exclusiva
        )
    )

    resultado = (
        df_pld.loc[
            mascara_periodo
        ]
        .copy()
        .reset_index(
            drop=True
        )
    )

    if resultado.empty:
        raise ValueError(
            "Não foram encontrados registros de PLD "
            "para o período informado."
        )

    return resultado
