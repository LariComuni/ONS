"""Coleta e consolidação dos dados de curtailment do ONS."""

# Importações

from io import BytesIO
import pandas as pd
import requests

# CONFIGURAÇÕES

CONFIG_FONTES = {
    "EOL": {
        "pasta_ons": "restricao_coff_eolica_tm",
        "prefixo_arquivo": "RESTRICAO_COFF_EOLICA",
    },
    "UFV": {
        "pasta_ons": "restricao_coff_fotovoltaica_tm",
        "prefixo_arquivo": "RESTRICAO_COFF_FOTOVOLTAICA",
    },
}

URL_BASE = (
    "https://ons-aws-prod-opendata.s3.amazonaws.com/"
    "dataset/{pasta_ons}/{prefixo_arquivo}_{ano}_{mes:02d}.csv"
)

# MONTAGEM DAS URLS

def montar_url_ons(fonte, ano, mes):
    """
    Monta a URL mensal dos dados de curtailment do ONS.

    Parâmetros
    ----------
    fonte : str
        EOL para eólica ou UFV para fotovoltaica.
    ano : int
        Ano do arquivo.
    mes : int
        Mês do arquivo, entre 1 e 12.

    Retorno
    -------
    str
        URL completa do arquivo CSV.
    """

    fonte = fonte.upper().strip()

    if fonte not in CONFIG_FONTES:
        raise ValueError(
            f"Fonte inválida: {fonte}. Use EOL ou UFV."
        )

    if not isinstance(ano, int):
        raise TypeError(
            "O ano deve ser informado como um número inteiro."
        )

    if not isinstance(mes, int):
        raise TypeError(
            "O mês deve ser informado como um número inteiro."
        )

    if not 1 <= mes <= 12:
        raise ValueError(
            "O mês deve estar entre 1 e 12."
        )

    config = CONFIG_FONTES[fonte]

    return URL_BASE.format(
        pasta_ons=config["pasta_ons"],
        prefixo_arquivo=config["prefixo_arquivo"],
        ano=ano,
        mes=mes,
    )

# OTIMIZAÇÃO DE MEMÓRIA

def otimizar_tipos(df):
    """
    Otimiza os tipos do DataFrame para reduzir o uso de memória.

    Colunas textuais com alta repetição são convertidas para
    category. As colunas técnicas de ano e mês são convertidas
    para tipos inteiros menores.

    Parâmetros
    ----------
    df : pandas.DataFrame
        DataFrame que será otimizado.

    Retorno
    -------
    pandas.DataFrame
        DataFrame com os tipos otimizados.
    """

    df = df.copy()

    if df.empty:
        return df

    colunas_textuais = (
        df.select_dtypes(include=["object"])
        .columns
        .tolist()
    )

    for coluna in colunas_textuais:
        quantidade_unicos = df[coluna].nunique(
            dropna=False
        )

        proporcao_unicos = quantidade_unicos / len(df)

        if proporcao_unicos < 0.5:
            df[coluna] = df[coluna].astype(
                "category"
            )

    if "ano_referencia" in df.columns:
        df["ano_referencia"] = (
            df["ano_referencia"].astype("int16")
        )

    if "mes_referencia" in df.columns:
        df["mes_referencia"] = (
            df["mes_referencia"].astype("int8")
        )

    return df

# LEITURA MENSAL

def carregar_mes_ons(
    fonte,
    ano,
    mes,
    timeout=120,
):
    """
    Lê diretamente do ONS um arquivo mensal de curtailment.

    O arquivo não é salvo localmente. O conteúdo é carregado
    diretamente em um DataFrame.

    Parâmetros
    ----------
    fonte : str
        EOL para eólica ou UFV para fotovoltaica.
    ano : int
        Ano da competência.
    mes : int
        Mês da competência.
    timeout : int, opcional
        Tempo máximo da requisição em segundos.

    Retorno
    -------
    pandas.DataFrame ou None
        DataFrame quando o arquivo estiver disponível.
        None quando o arquivo não for encontrado ou não puder
        ser processado.
    """

    fonte = fonte.upper().strip()
    url = montar_url_ons(fonte, ano, mes)

    print(
        f"Consultando {fonte} para "
        f"{ano}-{mes:02d}..."
    )
    print(url)

    try:
        resposta = requests.get(
            url,
            timeout=timeout,
        )

        if resposta.status_code == 404:
            print(
                f"Arquivo de {fonte} para "
                f"{ano}-{mes:02d} não encontrado."
            )
            return None

        resposta.raise_for_status()

        tamanho_mb = (
            len(resposta.content) / (1024 ** 2)
        )

        print(
            f"Download concluído. "
            f"Tamanho recebido: {tamanho_mb:.2f} MB"
        )

        df = pd.read_csv(
            BytesIO(resposta.content),
            sep=";",
            encoding="utf-8",
            low_memory=False,
        )

        if df.empty:
            print(
                "O arquivo foi encontrado, mas está vazio."
            )
            return None

        if "din_instante" not in df.columns:
            print(
                "O arquivo não possui a coluna obrigatória "
                "'din_instante'."
            )
            return None

        # A data deve ser convertida antes da otimização.
        df["din_instante"] = pd.to_datetime(
            df["din_instante"],
            errors="coerce",
        )

        quantidade_datas_invalidas = (
            df["din_instante"].isna().sum()
        )

        if quantidade_datas_invalidas > 0:
            print(
                "Aviso: foram encontradas "
                f"{quantidade_datas_invalidas:,} datas "
                "inválidas ou ausentes."
            )

        nome_arquivo = url.rsplit("/", 1)[-1]

        df["fonte"] = fonte
        df["ano_referencia"] = ano
        df["mes_referencia"] = mes
        df["competencia"] = f"{ano}-{mes:02d}"
        df["arquivo_origem"] = nome_arquivo

        df = otimizar_tipos(df)

        memoria_mb = (
            df.memory_usage(deep=True).sum()
            / (1024 ** 2)
        )

        print(
            f"Arquivo carregado: {len(df):,} linhas "
            f"e {len(df.columns)} colunas."
        )

        print(
            f"Memória após otimização: "
            f"{memoria_mb:.2f} MB"
        )

        return df

    except requests.Timeout:
        print(
            f"A consulta ultrapassou o limite de "
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

    except (ValueError, TypeError) as erro:
        print(
            f"Erro ao processar os dados: {erro}"
        )
        return None

    except Exception as erro:
        print(
            f"Erro inesperado ao processar "
            f"{fonte} para {ano}-{mes:02d}: {erro}"
        )
        return None

# LEITURA E CONSOLIDAÇÃO DE UM PERÍODO

def carregar_periodo_ons(
    fonte,
    ano,
    mes_inicial=1,
    mes_final=12,
):
    """
    Carrega e concatena dados mensais de curtailment do ONS.

    Parâmetros
    ----------
    fonte : str
        EOL para eólica ou UFV para fotovoltaica.
    ano : int
        Ano dos arquivos.
    mes_inicial : int, opcional
        Primeiro mês do período.
    mes_final : int, opcional
        Último mês do período.

    Retorno
    -------
    tuple
        DataFrame consolidado e dicionário com o relatório.
    """

    fonte = fonte.upper().strip()

    if fonte not in CONFIG_FONTES:
        raise ValueError(
            "Fonte inválida. Use EOL ou UFV."
        )

    if not isinstance(ano, int):
        raise TypeError(
            "O ano deve ser um número inteiro."
        )

    if not isinstance(mes_inicial, int):
        raise TypeError(
            "O mês inicial deve ser um número inteiro."
        )

    if not isinstance(mes_final, int):
        raise TypeError(
            "O mês final deve ser um número inteiro."
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
        df_mes = carregar_mes_ons(
            fonte=fonte,
            ano=ano,
            mes=mes,
        )

        if df_mes is None:
            meses_ausentes.append(mes)
            continue

        dataframes.append(df_mes)
        meses_carregados.append(mes)

    duplicidades_removidas = 0

    if not dataframes:
        consolidado = pd.DataFrame()

        print()
        print("Nenhum arquivo foi carregado.")

    else:
        consolidado = pd.concat(
            dataframes,
            ignore_index=True,
        )

        quantidade_antes = len(consolidado)

        consolidado = consolidado.drop_duplicates(
            ignore_index=True,
        )

        duplicidades_removidas = (
            quantidade_antes - len(consolidado)
        )

        # A concatenação pode alterar colunas category para object.
        consolidado = otimizar_tipos(
            consolidado
        )

    memoria_mb = (
        consolidado
        .memory_usage(deep=True)
        .sum()
        / (1024 ** 2)
    )

    relatorio = {
        "fonte": fonte,
        "ano": ano,
        "mes_inicial": mes_inicial,
        "mes_final": mes_final,
        "meses_carregados": meses_carregados,
        "meses_ausentes": meses_ausentes,
        "quantidade_arquivos": len(dataframes),
        "quantidade_linhas": len(consolidado),
        "quantidade_colunas": len(
            consolidado.columns
        ),
        "duplicidades_removidas": (
            duplicidades_removidas
        ),
        "memoria_mb": round(memoria_mb, 2),
    }

    print()
    print("=" * 50)
    print("RESUMO DA CARGA")
    print("=" * 50)
    print(f"Fonte: {fonte}")
    print(f"Ano: {ano}")
    print(
        f"Período solicitado: "
        f"{mes_inicial:02d}/{ano} a "
        f"{mes_final:02d}/{ano}"
    )
    print(
        f"Meses carregados: "
        f"{meses_carregados}"
    )
    print(
        f"Meses ausentes: "
        f"{meses_ausentes}"
    )
    print(
        f"Arquivos carregados: "
        f"{len(dataframes)}"
    )
    print(
        f"Linhas consolidadas: "
        f"{len(consolidado):,}"
    )
    print(
        f"Colunas: "
        f"{len(consolidado.columns)}"
    )
    print(
        f"Duplicidades completas removidas: "
        f"{duplicidades_removidas:,}"
    )
    print(
        f"Memória do consolidado: "
        f"{memoria_mb:.2f} MB"
    )

    return consolidado, relatorio
