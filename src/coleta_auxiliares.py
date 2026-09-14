"""Coleta das bases auxiliares utilizadas no mapa."""

from datetime import date
from io import BytesIO

import pandas as pd
import requests

# URLS DAS BASES AUXILIARES DO ONS

URL_FATOR_CAPACIDADE = (
    "https://ons-aws-prod-opendata.s3.amazonaws.com/"
    "dataset/fator_capacidade_2_di/"
    "FATOR_CAPACIDADE-2_{ano}_{mes:02d}.xlsx"
)

URL_SUBESTACAO = (
    "https://ons-aws-prod-opendata.s3.amazonaws.com/"
    "dataset/subestacao/SUBESTACAO.xlsx"
)

URL_LINHA_TRANSMISSAO = (
    "https://ons-aws-prod-opendata.s3.amazonaws.com/"
    "dataset/linha_transmissao/LINHA_TRANSMISSAO.xlsx"
)

# LEITURA GENÉRICA DE ARQUIVOS EXCEL

def ler_excel_ons(
    url,
    timeout=180,
):
    """
    Lê diretamente um arquivo Excel disponibilizado pelo ONS.

    A função não remove linhas, não remove colunas e não altera
    os valores presentes no arquivo original.

    Parâmetros
    ----------
    url : str
        Endereço completo do arquivo.
    timeout : int, opcional
        Tempo máximo de espera pela resposta, em segundos.

    Retorno
    -------
    pandas.DataFrame ou None
        DataFrame completo quando o arquivo estiver disponível.
        None quando o arquivo não for encontrado ou não puder
        ser processado.
    """

    try:
        resposta = requests.get(
            url,
            timeout=timeout,
        )

        if resposta.status_code == 404:
            print(
                f"Arquivo não encontrado: {url}"
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

        df = pd.read_excel(
            BytesIO(resposta.content),
            engine="openpyxl",
        )

        if df.empty:
            print(
                "O arquivo foi encontrado, mas está vazio."
            )
            return None

        print(
            f"Arquivo carregado: {len(df):,} linhas "
            f"e {len(df.columns)} colunas."
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

    except (
        ValueError,
        OSError,
        ImportError,
    ) as erro:
        print(
            f"Erro ao interpretar o arquivo Excel: {erro}"
        )
        return None

# FATOR DE CAPACIDADE

def montar_url_fator_capacidade(
    ano,
    mes,
):
    """
    Monta a URL mensal da base de fator de capacidade.

    Parâmetros
    ----------
    ano : int
        Ano da competência.
    mes : int
        Mês da competência, entre 1 e 12.

    Retorno
    -------
    str
        URL completa do arquivo.
    """

    if not isinstance(ano, int):
        raise TypeError(
            "O ano deve ser um número inteiro."
        )

    if not isinstance(mes, int):
        raise TypeError(
            "O mês deve ser um número inteiro."
        )

    if not 1 <= mes <= 12:
        raise ValueError(
            "O mês deve estar entre 1 e 12."
        )

    return URL_FATOR_CAPACIDADE.format(
        ano=ano,
        mes=mes,
    )


def obter_ultima_competencia_completa(
    data_referencia=None,
):
    """
    Retorna o ano e o mês da última competência encerrada.

    Por exemplo, durante setembro de 2026, retorna agosto
    de 2026.

    Parâmetros
    ----------
    data_referencia : datetime.date ou None, opcional
        Data utilizada como referência. Quando não informada,
        utiliza a data atual.

    Retorno
    -------
    tuple
        Ano e mês da última competência completa.
    """

    if data_referencia is None:
        data_referencia = date.today()

    if not isinstance(data_referencia, date):
        raise TypeError(
            "data_referencia deve ser uma data."
        )

    if data_referencia.month == 1:
        return data_referencia.year - 1, 12

    return (
        data_referencia.year,
        data_referencia.month - 1,
    )


def carregar_fator_capacidade(
    ano,
    mes,
    timeout=180,
):
    """
    Lê a base mensal completa de fator de capacidade do ONS.

    A função preserva todas as linhas e colunas originais.
    São acrescentadas apenas três colunas técnicas:
    ano_referencia, mes_referencia e competencia.

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
        Base completa do fator de capacidade.
    """

    url = montar_url_fator_capacidade(
        ano=ano,
        mes=mes,
    )

    print(
        f"Consultando fator de capacidade "
        f"para {ano}-{mes:02d}..."
    )
    print(url)

    df = ler_excel_ons(
        url=url,
        timeout=timeout,
    )

    if df is None:
        return None

    # Converte a coluna temporal sem remover registros.
    if "din_instante" in df.columns:
        df["din_instante"] = pd.to_datetime(
            df["din_instante"],
            errors="coerce",
        )

    # Acrescenta metadados técnicos.
    df["ano_referencia"] = ano
    df["mes_referencia"] = mes
    df["competencia"] = f"{ano}-{mes:02d}"

    return df


def carregar_ultimo_fator_capacidade_completo(
    data_referencia=None,
    timeout=180,
):
    """
    Carrega automaticamente a última competência mensal
    completa do fator de capacidade.

    Retorno
    -------
    tuple
        DataFrame, ano e mês da competência carregada.
    """

    ano, mes = obter_ultima_competencia_completa(
        data_referencia=data_referencia,
    )

    df = carregar_fator_capacidade(
        ano=ano,
        mes=mes,
        timeout=timeout,
    )

    return df, ano, mes


# ============================================================
# SUBESTAÇÕES
# ============================================================

def carregar_subestacoes(
    timeout=180,
):
    """
    Lê o cadastro atual completo de subestações do ONS.

    A função não seleciona, remove ou transforma colunas.
    """

    print(
        "Consultando cadastro de subestações..."
    )
    print(URL_SUBESTACAO)

    return ler_excel_ons(
        url=URL_SUBESTACAO,
        timeout=timeout,
    )

# LINHAS DE TRANSMISSÃO

def carregar_linhas_transmissao(
    timeout=180,
):
    """
    Lê o cadastro atual completo de linhas de transmissão
    disponibilizado pelo ONS.

    A função não seleciona, remove ou transforma colunas.
    """

    print(
        "Consultando cadastro de linhas "
        "de transmissão..."
    )
    print(URL_LINHA_TRANSMISSAO)

    return ler_excel_ons(
        url=URL_LINHA_TRANSMISSAO,
        timeout=timeout,
    )
