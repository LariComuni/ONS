"""
Coleta e consolidação dos dados de Energia Vertida
Turbinável do ONS.
"""

# ============================================================
# IMPORTAÇÕES
# ============================================================

from io import BytesIO

import pandas as pd
import requests


# ============================================================
# CONFIGURAÇÕES
# ============================================================

PASTA_ONS_EVT = (
    "energia_vertida_turbinavel_ho"
)

PREFIXO_ARQUIVO_EVT = (
    "ENERGIA_VERTIDA_TURBINAVEL"
)

URL_BASE_EVT = (
    "https://ons-aws-prod-opendata.s3.amazonaws.com/"
    "dataset/{pasta_ons}/"
    "{prefixo_arquivo}_{ano}_{mes:02d}.csv"
)

COLUNAS_OBRIGATORIAS_EVT = {
    "din_instante",
    "id_subsistema",
    "nom_subsistema",
    "nom_reservatorio",
    "cod_usina",
    "val_geracao",
    "val_energiavertidaturbinavel",
}

COLUNAS_NUMERICAS_EVT = [
    "val_geracao",
    "val_disponibilidade",
    "val_vazaoturbinada",
    "val_vazaovertida",
    "val_vazaovertidanaoturbinavel",
    "val_produtividade",
    "val_folgadegeracao",
    "val_energiavertida",
    "val_vazaovertidaturbinavel",
    "val_energiavertidaturbinavel",
]

COLUNAS_TEXTUAIS_EVT = [
    "id_subsistema",
    "nom_subsistema",
    "nom_bacia",
    "nom_rio",
    "nom_agente",
    "nom_reservatorio",
    "cod_usina",
]


# ============================================================
# MONTAGEM DA URL
# ============================================================

def montar_url_evt(
    ano,
    mes,
):
    """
    Monta a URL mensal dos dados de Energia Vertida
    Turbinável do ONS.

    Parâmetros
    ----------
    ano : int
        Ano do arquivo.

    mes : int
        Mês do arquivo, entre 1 e 12.

    Retorno
    -------
    str
        URL completa do arquivo CSV.
    """

    if not isinstance(
        ano,
        int,
    ):
        raise TypeError(
            "O ano deve ser informado como "
            "um número inteiro."
        )

    if not isinstance(
        mes,
        int,
    ):
        raise TypeError(
            "O mês deve ser informado como "
            "um número inteiro."
        )

    if ano < 2024:
        raise ValueError(
            "A estrutura mensal da base EVT é "
            "utilizada a partir de 2024."
        )

    if not 1 <= mes <= 12:
        raise ValueError(
            "O mês deve estar entre 1 e 12."
        )

    return URL_BASE_EVT.format(
        pasta_ons=PASTA_ONS_EVT,
        prefixo_arquivo=PREFIXO_ARQUIVO_EVT,
        ano=ano,
        mes=mes,
    )


# ============================================================
# OTIMIZAÇÃO DE MEMÓRIA
# ============================================================

def otimizar_tipos_evt(
    df,
):
    """
    Otimiza os tipos da base EVT para reduzir o uso
    de memória.

    Parâmetros
    ----------
    df : pandas.DataFrame
        DataFrame que será otimizado.

    Retorno
    -------
    pandas.DataFrame
        DataFrame com tipos otimizados.
    """

    if not isinstance(
        df,
        pd.DataFrame,
    ):
        raise TypeError(
            "df deve ser um DataFrame."
        )

    df = df.copy()

    if df.empty:
        return df

    colunas_textuais = (
        df.select_dtypes(
            include=[
                "object",
                "string",
            ]
        )
        .columns
        .tolist()
    )

    for coluna in colunas_textuais:
        quantidade_unicos = (
            df[coluna]
            .nunique(
                dropna=False
            )
        )

        proporcao_unicos = (
            quantidade_unicos
            / len(df)
        )

        if proporcao_unicos < 0.5:
            df[coluna] = (
                df[coluna]
                .astype(
                    "category"
                )
            )

    if "ano_referencia" in df.columns:
        df["ano_referencia"] = (
            df["ano_referencia"]
            .astype(
                "int16"
            )
        )

    if "mes_referencia" in df.columns:
        df["mes_referencia"] = (
            df["mes_referencia"]
            .astype(
                "int8"
            )
        )

    return df


# ============================================================
# TRATAMENTO DA BASE
# ============================================================

def tratar_base_evt(
    df,
):
    """
    Trata a base horária de Energia Vertida
    Turbinável.

    A variável val_energiavertidaturbinavel é
    disponibilizada em MWmed. Como cada registro
    representa uma hora, o valor numérico também
    corresponde a MWh no intervalo horário.

    Parâmetros
    ----------
    df : pandas.DataFrame
        Base bruta mensal da EVT.

    Retorno
    -------
    pandas.DataFrame
        Base tratada.
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
            "A base EVT informada está vazia."
        )

    df = df.copy()

    df.columns = (
        df.columns
        .astype(
            str
        )
        .str.strip()
        .str.lower()
    )

    colunas_ausentes = (
        COLUNAS_OBRIGATORIAS_EVT
        - set(
            df.columns
        )
    )

    if colunas_ausentes:
        raise ValueError(
            "A base EVT não possui as colunas "
            "obrigatórias: "
            f"{sorted(colunas_ausentes)}."
        )

    df["din_instante"] = pd.to_datetime(
        df["din_instante"],
        errors="coerce",
    )

    for coluna in COLUNAS_NUMERICAS_EVT:
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(
                df[coluna],
                errors="coerce",
            )

    for coluna in COLUNAS_TEXTUAIS_EVT:
        if coluna in df.columns:
            df[coluna] = (
                df[coluna]
                .astype(
                    "string"
                )
                .str.strip()
            )

    df = df.dropna(
        subset=[
            "din_instante",
            "nom_reservatorio",
            "val_geracao",
            "val_energiavertidaturbinavel",
        ]
    ).copy()

    if df.empty:
        raise ValueError(
            "Não restaram registros válidos na base "
            "EVT após o tratamento."
        )
      
    df["val_geracao"] = (
        df["val_geracao"]
        .clip(lower=0)
    )
    df[
        "val_energiavertidaturbinavel"
    ] = (
        df[
            "val_energiavertidaturbinavel"
        ]
        .clip(
            lower=0
        )
    )

    # A base é horária:
    # MWmed × 1 hora = MWh.
    df["geracao_mwh"] = (
        df["val_geracao"]
    )
    df[
        "energia_vertida_turbinavel_mwh"
    ] = (
        df[
            "val_energiavertidaturbinavel"
        ]
    )

    return (
        df
        .sort_values(
            [
                "din_instante",
                "nom_reservatorio",
            ]
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# LEITURA MENSAL
# ============================================================

def carregar_mes_evt(
    ano,
    mes,
    timeout=120,
):
    """
    Lê diretamente do ONS um arquivo mensal da base
    de Energia Vertida Turbinável.

    O arquivo não é salvo localmente.

    Parâmetros
    ----------
    ano : int
        Ano da competência.

    mes : int
        Mês da competência.

    timeout : int, opcional
        Tempo máximo da requisição em segundos.

    Retorno
    -------
    pandas.DataFrame ou None
        Base mensal tratada quando disponível.
        None quando não for possível carregar o arquivo.
    """

    url = montar_url_evt(
        ano=ano,
        mes=mes,
    )

    print(
        "Consultando EVT para "
        f"{ano}-{mes:02d}..."
    )

    print(
        url
    )

    try:
        resposta = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "SINmulator/1.0"
                ),
                "Accept": (
                    "text/csv,"
                    "application/octet-stream;q=0.9,"
                    "*/*;q=0.8"
                ),
            },
        )

        if resposta.status_code == 404:
            print(
                "Arquivo de EVT para "
                f"{ano}-{mes:02d} não encontrado."
            )

            return None

        resposta.raise_for_status()

        tamanho_mb = (
            len(
                resposta.content
            )
            / (1024 ** 2)
        )

        print(
            "Download concluído. "
            f"Tamanho recebido: {tamanho_mb:.2f} MB"
        )

        try:
            df = pd.read_csv(
                BytesIO(
                    resposta.content
                ),
                sep=";",
                encoding="utf-8",
                decimal=".",
                low_memory=False,
            )

        except UnicodeDecodeError:
            df = pd.read_csv(
                BytesIO(
                    resposta.content
                ),
                sep=";",
                encoding="utf-8-sig",
                decimal=".",
                low_memory=False,
            )

        if df.empty:
            print(
                "O arquivo foi encontrado, "
                "mas está vazio."
            )

            return None

        df = tratar_base_evt(
            df
        )

        quantidade_datas_invalidas = (
            df[
                "din_instante"
            ]
            .isna()
            .sum()
        )

        if quantidade_datas_invalidas > 0:
            print(
                "Aviso: foram encontradas "
                f"{quantidade_datas_invalidas:,} "
                "datas inválidas ou ausentes."
            )

        nome_arquivo = (
            url.rsplit(
                "/",
                1,
            )[-1]
        )

        df["fonte"] = "EVT"
        df["ano_referencia"] = ano
        df["mes_referencia"] = mes
        df["competencia"] = (
            f"{ano}-{mes:02d}"
        )
        df["arquivo_origem"] = (
            nome_arquivo
        )
        df["granularidade_origem"] = (
            "1h"
        )

        df = otimizar_tipos_evt(
            df
        )

        memoria_mb = (
            df
            .memory_usage(
                deep=True
            )
            .sum()
            / (1024 ** 2)
        )

        print(
            f"Arquivo carregado: {len(df):,} "
            f"linhas e {len(df.columns)} colunas."
        )

        print(
            "Memória após otimização: "
            f"{memoria_mb:.2f} MB"
        )

        return df

    except requests.Timeout:
        print(
            "A consulta ultrapassou o limite de "
            f"{timeout} segundos."
        )

        return None

    except requests.RequestException as erro:
        print(
            f"Erro ao acessar o ONS: {erro}"
        )

        return None

    except pd.errors.ParserError as erro:
        print(
            f"Erro ao interpretar o CSV: {erro}"
        )

        return None

    except (
        ValueError,
        TypeError,
    ) as erro:
        print(
            f"Erro ao processar os dados: {erro}"
        )

        return None

    except Exception as erro:
        print(
            "Erro inesperado ao processar EVT "
            f"para {ano}-{mes:02d}: {erro}"
        )

        return None


# ============================================================
# LEITURA E CONSOLIDAÇÃO DE UM PERÍODO
# ============================================================

def carregar_periodo_evt(
    ano,
    mes_inicial=1,
    mes_final=12,
):
    """
    Carrega e concatena dados mensais de Energia
    Vertida Turbinável do ONS.

    Parâmetros
    ----------
    ano : int
        Ano dos arquivos.

    mes_inicial : int, opcional
        Primeiro mês do período.

    mes_final : int, opcional
        Último mês do período.

    Retorno
    -------
    tuple
        DataFrame consolidado e dicionário com relatório.
    """

    if not isinstance(
        ano,
        int,
    ):
        raise TypeError(
            "O ano deve ser um número inteiro."
        )

    if not isinstance(
        mes_inicial,
        int,
    ):
        raise TypeError(
            "O mês inicial deve ser um número inteiro."
        )

    if not isinstance(
        mes_final,
        int,
    ):
        raise TypeError(
            "O mês final deve ser um número inteiro."
        )

    if ano < 2024:
        raise ValueError(
            "A estrutura mensal da base EVT é "
            "utilizada a partir de 2024."
        )

    if not 1 <= mes_inicial <= 12:
        raise ValueError(
            "O mês inicial deve estar entre 1 e 12."
        )

    if not 1 <= mes_final <= 12:
        raise ValueError(
            "O mês final deve estar entre 1 e 12."
        )

    if mes_inicial > mes_final:
        raise ValueError(
            "O mês inicial não pode ser maior "
            "que o mês final."
        )

    dataframes = []
    meses_carregados = []
    meses_ausentes = []

    for mes in range(
        mes_inicial,
        mes_final + 1,
    ):
        df_mes = carregar_mes_evt(
            ano=ano,
            mes=mes,
        )

        if df_mes is None:
            meses_ausentes.append(
                mes
            )

            continue

        dataframes.append(
            df_mes
        )

        meses_carregados.append(
            mes
        )

    duplicidades_removidas = 0

    if not dataframes:
        consolidado = pd.DataFrame()

        print()
        print(
            "Nenhum arquivo EVT foi carregado."
        )

    else:
        consolidado = pd.concat(
            dataframes,
            ignore_index=True,
        )

        quantidade_antes = len(
            consolidado
        )

        consolidado = (
            consolidado
            .drop_duplicates(
                ignore_index=True,
            )
        )

        duplicidades_removidas = (
            quantidade_antes
            - len(
                consolidado
            )
        )

        consolidado = otimizar_tipos_evt(
            consolidado
        )

    memoria_mb = (
        consolidado
        .memory_usage(
            deep=True
        )
        .sum()
        / (1024 ** 2)
    )

    relatorio = {
        "fonte": "EVT",
        "ano": ano,
        "mes_inicial": mes_inicial,
        "mes_final": mes_final,
        "meses_carregados": (
            meses_carregados
        ),
        "meses_ausentes": (
            meses_ausentes
        ),
        "quantidade_arquivos": len(
            dataframes
        ),
        "quantidade_linhas": len(
            consolidado
        ),
        "quantidade_colunas": len(
            consolidado.columns
        ),
        "duplicidades_removidas": (
            duplicidades_removidas
        ),
        "memoria_mb": round(
            memoria_mb,
            2,
        ),
    }

    print()
    print(
        "=" * 50
    )
    print(
        "RESUMO DA CARGA EVT"
    )
    print(
        "=" * 50
    )
    print(
        f"Ano: {ano}"
    )
    print(
        "Período solicitado: "
        f"{mes_inicial:02d}/{ano} a "
        f"{mes_final:02d}/{ano}"
    )
    print(
        "Meses carregados: "
        f"{meses_carregados}"
    )
    print(
        "Meses ausentes: "
        f"{meses_ausentes}"
    )
    print(
        "Arquivos carregados: "
        f"{len(dataframes)}"
    )
    print(
        "Linhas consolidadas: "
        f"{len(consolidado):,}"
    )
    print(
        "Colunas: "
        f"{len(consolidado.columns)}"
    )
    print(
        "Duplicidades completas removidas: "
        f"{duplicidades_removidas:,}"
    )
    print(
        "Memória do consolidado: "
        f"{memoria_mb:.2f} MB"
    )

    return (
        consolidado,
        relatorio,
    )
