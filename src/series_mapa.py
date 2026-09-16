"""
Preparação das séries horárias utilizadas nos gráficos do mapa.

O módulo transforma a base de curtailment enriquecida em
perfis médios de 24 horas por usina, ponto de conexão e
código de restrição.
"""

import re
import unicodedata

import numpy as np
import pandas as pd

COLUNAS_METRICAS_SERIES = [
    "val_geracao",
    "val_curtailment",
    "val_geracao_esperada",
]

COLUNA_CODIGO_RESTRICAO = "cod_razao_str"

HORAS_DIA = list(range(24))

def preparar_base_series_mapa(df_curtailment_enriquecido):
    """
    Prepara a base de curtailment para o cálculo das séries
    horárias utilizadas no mapa.

    A função cria uma cópia do DataFrame, converte o instante
    para datetime, cria a coluna hora, converte as métricas
    para valores numéricos e padroniza o código da razão de
    restrição.

    A base recebida não é modificada.

    Parâmetros
    ----------
    df_curtailment_enriquecido : pandas.DataFrame
        Base de curtailment calculada e enriquecida com
        ponto de conexão e coordenadas.

    Retorno
    -------
    tuple
        DataFrame preparado e relatório de qualidade.

    Raises
    ------
    ValueError
        Quando a base não foi carregada, está vazia ou não
        possui as colunas necessárias.
    """

    if df_curtailment_enriquecido is None:
        raise ValueError(
            "A base de curtailment enriquecida "
            "não foi carregada."
        )

    if df_curtailment_enriquecido.empty:
        raise ValueError(
            "A base de curtailment enriquecida está vazia."
        )

    colunas_obrigatorias = [
        "din_instante",
        "nom_usina",
        "nom_pontoconexao",
        *COLUNAS_METRICAS_SERIES,
    ]

    colunas_ausentes = [
        coluna
        for coluna in colunas_obrigatorias
        if coluna not in df_curtailment_enriquecido.columns
    ]

    if colunas_ausentes:
        raise ValueError(
            "Colunas ausentes para preparar as séries "
            f"do mapa: {colunas_ausentes}"
        )

    curt = df_curtailment_enriquecido.copy()

    curt["din_instante"] = pd.to_datetime(
        curt["din_instante"],
        errors="coerce",
    )

    datas_invalidas = curt[
        "din_instante"
    ].isna()

    curt["hora"] = (
        curt["din_instante"]
        .dt.hour
        .astype("Int64")
    )

    for coluna in COLUNAS_METRICAS_SERIES:
        curt[coluna] = pd.to_numeric(
            curt[coluna],
            errors="coerce",
        )

    if "cod_razaorestricao" in curt.columns:
        curt[COLUNA_CODIGO_RESTRICAO] = (
            curt["cod_razaorestricao"]
            .astype("string")
            .str.strip()
            .fillna("SEM_CODIGO")
        )

        curt.loc[
            curt[COLUNA_CODIGO_RESTRICAO] == "",
            COLUNA_CODIGO_RESTRICAO,
        ] = "SEM_CODIGO"

    else:
        curt[COLUNA_CODIGO_RESTRICAO] = (
            "SEM_CODIGO"
        )

    horas_invalidas = (
        curt["hora"].notna()
        & ~curt["hora"].between(0, 23)
    )

    codigos_distintos = (
        curt[COLUNA_CODIGO_RESTRICAO]
        .dropna()
        .sort_values()
        .unique()
        .tolist()
    )

    relatorio = {
        "linhas_entrada": len(
            df_curtailment_enriquecido
        ),
        "linhas_saida": len(curt),
        "datas_invalidas": int(
            datas_invalidas.sum()
        ),
        "horas_invalidas": int(
            horas_invalidas.sum()
        ),
        "instantes_distintos": int(
            curt["din_instante"].nunique(
                dropna=True
            )
        ),
        "horas_distintas": int(
            curt["hora"].nunique(
                dropna=True
            )
        ),
        "usinas_distintas": int(
            curt["nom_usina"].nunique(
                dropna=True
            )
        ),
        "pontos_distintos": int(
            curt["nom_pontoconexao"].nunique(
                dropna=True
            )
        ),
        "linhas_sem_ponto": int(
            curt["nom_pontoconexao"].isna().sum()
        ),
        "codigos_restricao": codigos_distintos,
    }

    return curt, relatorio

def criar_serie_24(df,coluna_valor,coluna_hora="hora",casas_decimais=6):
    """
    Cria uma lista com uma posição para cada hora do dia.

    Horas sem observação recebem None. Valores infinitos ou
    ausentes também são representados por None.

    Parâmetros
    ----------
    df : pandas.DataFrame
        DataFrame contendo hora e valor.
    coluna_valor : str
        Nome da coluna que será transformada em série.
    coluna_hora : str, opcional
        Nome da coluna de hora.
    casas_decimais : int ou None, opcional
        Quantidade de casas decimais. Quando None, não realiza
        arredondamento.

    Retorno
    -------
    list
        Lista com exatamente 24 posições.
    """

    if df is None:
        raise ValueError(
            "O DataFrame da série não foi informado."
        )

    colunas_ausentes = [
        coluna
        for coluna in [
            coluna_hora,
            coluna_valor,
        ]
        if coluna not in df.columns
    ]

    if colunas_ausentes:
        raise ValueError(
            "Colunas ausentes para produzir a série: "
            f"{colunas_ausentes}"
        )

    horas = pd.to_numeric(
        df[coluna_hora],
        errors="coerce",
    )

    valores = pd.to_numeric(
        df[coluna_valor],
        errors="coerce",
    )

    mascara_valida = (
        horas.notna()
        & horas.between(0, 23)
    )

    horas_validas = horas.loc[
        mascara_valida
    ].astype(int)

    valores_validos = valores.loc[
        mascara_valida
    ]

    mapa_valores = {}

    for hora, valor in zip(
        horas_validas,
        valores_validos,
    ):
        if pd.isna(valor):
            mapa_valores[int(hora)] = None
            continue

        valor_float = float(valor)

        if not np.isfinite(valor_float):
            mapa_valores[int(hora)] = None
            continue

        if casas_decimais is None:
            mapa_valores[int(hora)] = valor_float
        else:
            mapa_valores[int(hora)] = round(
                valor_float,
                casas_decimais,
            )

    return [
        mapa_valores.get(hora)
        for hora in HORAS_DIA
    ]

def normalizar_nome(valor):
    """
    Normaliza um nome para criação de índices de consulta.

    A função remove acentos, elimina espaços externos,
    reduz espaços consecutivos e converte o texto para
    letras maiúsculas.

    Parâmetros
    ----------
    valor : object
        Valor que será normalizado.

    Retorno
    -------
    str
        Texto normalizado.
    """

    if valor is None or pd.isna(valor):
        return ""

    texto = str(valor).strip()

    texto = (
        unicodedata
        .normalize("NFKD", texto)
        .encode("ascii", "ignore")
        .decode("ascii")
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.upper()

def criar_chave_coordenadas(latitude,longitude,casas_decimais=6):
    """
    Cria a chave textual usada para associar as séries aos
    marcadores do mapa.

    Parâmetros
    ----------
    latitude : number
        Latitude do marcador.
    longitude : number
        Longitude do marcador.
    casas_decimais : int, opcional
        Quantidade de casas utilizadas na chave.

    Retorno
    -------
    str ou None
        Chave no formato latitude,longitude.
    """

    latitude = pd.to_numeric(
        latitude,
        errors="coerce",
    )

    longitude = pd.to_numeric(
        longitude,
        errors="coerce",
    )

    if pd.isna(latitude) or pd.isna(longitude):
        return None

    latitude = float(latitude)
    longitude = float(longitude)

    if (
        not np.isfinite(latitude)
        or not np.isfinite(longitude)
    ):
        return None

    return (
        f"{latitude:.{casas_decimais}f},"
        f"{longitude:.{casas_decimais}f}"
    )

def calcular_perfil_horario_usinas(df_series):
    """
    Calcula o perfil horário médio de cada usina.

    Para cada combinação de usina, ponto de conexão e hora,
    calcula a média da geração, do curtailment e da geração
    esperada.

    Em seguida, transforma os resultados em séries com
    exatamente 24 posições por usina.

    Parâmetros
    ----------
    df_series : pandas.DataFrame
        Base retornada por preparar_base_series_mapa().

    Retorno
    -------
    tuple
        O primeiro elemento é o DataFrame com as médias
        horárias por usina.

        O segundo elemento é um dicionário indexado pelo
        nome da usina, contendo as séries de 24 horas.

        O terceiro elemento é um relatório da execução.
    """

    if df_series is None:
        raise ValueError(
            "A base preparada para as séries não foi informada."
        )

    if df_series.empty:
        raise ValueError(
            "A base preparada para as séries está vazia."
        )

    colunas_obrigatorias = [
        "nom_usina",
        "nom_pontoconexao",
        "hora",
        *COLUNAS_METRICAS_SERIES,
    ]

    colunas_ausentes = [
        coluna
        for coluna in colunas_obrigatorias
        if coluna not in df_series.columns
    ]

    if colunas_ausentes:
        raise ValueError(
            "Colunas ausentes para calcular o perfil "
            f"horário das usinas: {colunas_ausentes}"
        )

    curt = df_series.copy()

    usina_hourly = (
        curt
        .groupby(
            [
                "nom_usina",
                "nom_pontoconexao",
                "hora",
            ],
            dropna=True,
            observed=True,
        )
        .agg(
            avg_geracao=(
                "val_geracao",
                "mean",
            ),
            avg_curtailment=(
                "val_curtailment",
                "mean",
            ),
            avg_geracao_esperada=(
                "val_geracao_esperada",
                "mean",
            ),
        )
        .reset_index()
    )

    usina_hourly["hora"] = pd.to_numeric(
        usina_hourly["hora"],
        errors="coerce",
    ).astype("Int64")

    series_by_usina_nome = {}

    for nome_usina, grupo in usina_hourly.groupby(
        "nom_usina",
        dropna=True,
        observed=True,
    ):
        pontos = (
            grupo["nom_pontoconexao"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        ponto_principal = (
            pontos[0]
            if pontos
            else "—"
        )

        payload = {
            "nome_usina": str(nome_usina),
            "ponto": ponto_principal,
            "horas": HORAS_DIA.copy(),
            "avg_geracao": criar_serie_24(
                grupo,
                coluna_valor="avg_geracao",
            ),
            "avg_curtailment": criar_serie_24(
                grupo,
                coluna_valor="avg_curtailment",
            ),
            "avg_geracao_esperada": criar_serie_24(
                grupo,
                coluna_valor=(
                    "avg_geracao_esperada"
                ),
            ),
        }

        series_by_usina_nome[
            str(nome_usina)
        ] = payload

    usinas_base = set(
        curt["nom_usina"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    usinas_com_series = set(
        series_by_usina_nome.keys()
    )

    usinas_sem_series = sorted(
        usinas_base - usinas_com_series
    )

    pontos_por_usina = (
        usina_hourly
        .groupby(
            "nom_usina",
            dropna=True,
            observed=True,
        )["nom_pontoconexao"]
        .nunique(dropna=True)
    )

    usinas_com_multiplos_pontos = (
        pontos_por_usina[
            pontos_por_usina > 1
        ]
        .index
        .astype(str)
        .tolist()
    )

    relatorio = {
        "linhas_entrada": len(curt),
        "linhas_perfil_horario": len(
            usina_hourly
        ),
        "usinas_na_base": len(
            usinas_base
        ),
        "usinas_com_series": len(
            usinas_com_series
        ),
        "usinas_sem_series": (
            usinas_sem_series
        ),
        "usinas_com_multiplos_pontos": (
            sorted(
                usinas_com_multiplos_pontos
            )
        ),
        "quantidade_usinas_com_multiplos_pontos": len(
            usinas_com_multiplos_pontos
        ),
        "horas_distintas": int(
            usina_hourly["hora"]
            .nunique(dropna=True)
        ),
    }

    return (usina_hourly,series_by_usina_nome,relatorio)

def calcular_decomposicao_curtailment(df_series,usina_hourly):
    """
    Calcula a contribuição ponderada de cada código de
    restrição para o curtailment médio por usina e hora.

    A contribuição de cada código é calculada como:

        média do curtailment do código
        ×
        quantidade de registros do código
        ÷
        quantidade total de registros da usina e hora

    A soma das contribuições dos códigos deve coincidir com
    o curtailment médio total da usina em cada hora.

    Parâmetros
    ----------
    df_series : pandas.DataFrame
        Base retornada por preparar_base_series_mapa().
    usina_hourly : pandas.DataFrame
        Perfil retornado por calcular_perfil_horario_usinas().

    Retorno
    -------
    tuple
        DataFrame com as contribuições ponderadas, dicionário
        de séries por usina e código, dicionário de séries por
        ponto e código e relatório de validação.
    """

    if df_series is None:
        raise ValueError(
            "A base preparada para as séries não foi informada."
        )

    if df_series.empty:
        raise ValueError(
            "A base preparada para as séries está vazia."
        )

    if usina_hourly is None:
        raise ValueError(
            "O perfil horário das usinas não foi informado."
        )

    if usina_hourly.empty:
        raise ValueError(
            "O perfil horário das usinas está vazio."
        )

    colunas_obrigatorias_series = [
        "nom_usina",
        "nom_pontoconexao",
        "hora",
        "val_curtailment",
        COLUNA_CODIGO_RESTRICAO,
    ]

    colunas_ausentes_series = [
        coluna
        for coluna in colunas_obrigatorias_series
        if coluna not in df_series.columns
    ]

    if colunas_ausentes_series:
        raise ValueError(
            "Colunas ausentes para calcular a decomposição: "
            f"{colunas_ausentes_series}"
        )

    colunas_obrigatorias_perfil = [
        "nom_usina",
        "hora",
        "avg_curtailment",
    ]

    colunas_ausentes_perfil = [
        coluna
        for coluna in colunas_obrigatorias_perfil
        if coluna not in usina_hourly.columns
    ]

    if colunas_ausentes_perfil:
        raise ValueError(
            "Colunas ausentes no perfil horário das usinas: "
            f"{colunas_ausentes_perfil}"
        )

    curt = df_series.copy()

    usina_code_hourly = (
        curt
        .groupby(
            [
                "nom_usina",
                "nom_pontoconexao",
                COLUNA_CODIGO_RESTRICAO,
                "hora",
            ],
            dropna=True,
            observed=True,
        )
        .agg(
            avg_curtailment=(
                "val_curtailment",
                "mean",
            )
        )
        .reset_index()
    )

    contagem_usina_hora = (
        curt
        .groupby(
            [
                "nom_usina",
                "hora",
            ],
            dropna=True,
            observed=True,
        )
        .size()
        .reset_index(
            name="n_us_h"
        )
    )

    contagem_usina_codigo_hora = (
        curt
        .groupby(
            [
                "nom_usina",
                COLUNA_CODIGO_RESTRICAO,
                "hora",
            ],
            dropna=True,
            observed=True,
        )
        .size()
        .reset_index(
            name="n_us_code_h"
        )
    )

    contribuicoes = (
        usina_code_hourly
        .merge(
            contagem_usina_codigo_hora,
            on=[
                "nom_usina",
                COLUNA_CODIGO_RESTRICAO,
                "hora",
            ],
            how="left",
            validate="one_to_one",
        )
        .merge(
            contagem_usina_hora,
            on=[
                "nom_usina",
                "hora",
            ],
            how="left",
            validate="many_to_one",
        )
    )

    contribuicoes["peso"] = (
        contribuicoes["n_us_code_h"]
        / contribuicoes["n_us_h"]
    )

    contribuicoes["peso"] = (
        pd.to_numeric(
            contribuicoes["peso"],
            errors="coerce",
        )
        .fillna(0.0)
        .clip(
            lower=0.0,
            upper=1.0,
        )
    )

    contribuicoes["contribuicao"] = (
        contribuicoes["avg_curtailment"]
        * contribuicoes["peso"]
    )

    series_by_usina_code = {}

    for (
        nome_usina,
        codigo,
    ), grupo in contribuicoes.groupby(
        [
            "nom_usina",
            COLUNA_CODIGO_RESTRICAO,
        ],
        dropna=False,
        observed=True,
    ):
        nome_usina = str(nome_usina)
        codigo = str(codigo)

        if nome_usina not in series_by_usina_code:
            series_by_usina_code[nome_usina] = {}

        series_by_usina_code[
            nome_usina
        ][codigo] = criar_serie_24(
            grupo,
            coluna_valor="contribuicao",
        )

    ponto_code_hourly = (
        contribuicoes
        .groupby(
            [
                "nom_pontoconexao",
                COLUNA_CODIGO_RESTRICAO,
                "hora",
            ],
            dropna=True,
            observed=True,
        )
        .agg(
            contribuicao=(
                "contribuicao",
                "sum",
            )
        )
        .reset_index()
    )

    series_by_ponto_code = {}

    for (
        nome_ponto,
        codigo,
    ), grupo in ponto_code_hourly.groupby(
        [
            "nom_pontoconexao",
            COLUNA_CODIGO_RESTRICAO,
        ],
        dropna=False,
        observed=True,
    ):
        nome_ponto = str(nome_ponto)
        codigo = str(codigo)

        if nome_ponto not in series_by_ponto_code:
            series_by_ponto_code[nome_ponto] = {}

        series_by_ponto_code[
            nome_ponto
        ][codigo] = criar_serie_24(
            grupo,
            coluna_valor="contribuicao",
        )

    verificacao = (
        contribuicoes
        .groupby(
            [
                "nom_usina",
                "hora",
            ],
            dropna=True,
            observed=True,
        )
        .agg(
            soma_contribuicoes=(
                "contribuicao",
                "sum",
            )
        )
        .reset_index()
        .merge(
            usina_hourly[
                [
                    "nom_usina",
                    "hora",
                    "avg_curtailment",
                ]
            ],
            on=[
                "nom_usina",
                "hora",
            ],
            how="left",
            validate="one_to_one",
        )
    )

    verificacao["diferenca_absoluta"] = (
        verificacao["avg_curtailment"]
        - verificacao["soma_contribuicoes"]
    ).abs()

    diferenca_maxima = (
        verificacao[
            "diferenca_absoluta"
        ].max()
    )

    diferenca_maxima = (
        0.0
        if pd.isna(diferenca_maxima)
        else float(diferenca_maxima)
    )

    tolerancia = 1e-10

    linhas_fora_tolerancia = (
        verificacao[
            "diferenca_absoluta"
        ] > tolerancia
    )

    codigos = sorted(
        contribuicoes[
            COLUNA_CODIGO_RESTRICAO
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    relatorio = {
        "linhas_usina_codigo_hora": len(
            usina_code_hourly
        ),
        "linhas_contribuicoes": len(
            contribuicoes
        ),
        "linhas_ponto_codigo_hora": len(
            ponto_code_hourly
        ),
        "usinas_com_decomposicao": len(
            series_by_usina_code
        ),
        "pontos_com_decomposicao": len(
            series_by_ponto_code
        ),
        "codigos_restricao": codigos,
        "diferenca_maxima_total_vs_codigos": (
            diferenca_maxima
        ),
        "linhas_fora_tolerancia": int(
            linhas_fora_tolerancia.sum()
        ),
        "tolerancia": tolerancia,
    }

    return (contribuicoes,series_by_usina_code,series_by_ponto_code,relatorio)

def calcular_perfil_horario_pontos(usina_hourly):
    """
    Calcula o perfil horário agregado de cada ponto de conexão.

    A função soma, por ponto e hora, as médias horárias
    anteriormente calculadas para cada usina. Isso reproduz
    a metodologia do mapa original.

    Parâmetros
    ----------
    usina_hourly : pandas.DataFrame
        Perfil horário por usina retornado por
        calcular_perfil_horario_usinas().

    Retorno
    -------
    tuple
        O primeiro elemento é o DataFrame com o perfil
        horário por ponto.

        O segundo elemento é um dicionário indexado pelo
        nome original do ponto, contendo séries de 24 horas.

        O terceiro elemento é um relatório de qualidade.

    Raises
    ------
    ValueError
        Quando o perfil não foi informado, está vazio ou
        não possui as colunas necessárias.
    """

    if usina_hourly is None:
        raise ValueError(
            "O perfil horário das usinas não foi informado."
        )

    if usina_hourly.empty:
        raise ValueError(
            "O perfil horário das usinas está vazio."
        )

    colunas_obrigatorias = [
        "nom_pontoconexao",
        "hora",
        "avg_geracao",
        "avg_curtailment",
        "avg_geracao_esperada",
    ]

    colunas_ausentes = [
        coluna
        for coluna in colunas_obrigatorias
        if coluna not in usina_hourly.columns
    ]

    if colunas_ausentes:
        raise ValueError(
            "Colunas ausentes para calcular o perfil "
            f"horário dos pontos: {colunas_ausentes}"
        )

    perfil_usinas = usina_hourly.copy()

    perfil_pontos = (
        perfil_usinas
        .groupby(
            [
                "nom_pontoconexao",
                "hora",
            ],
            dropna=True,
            observed=True,
        )
        .agg(
            avg_geracao=(
                "avg_geracao",
                "sum",
            ),
            avg_curtailment=(
                "avg_curtailment",
                "sum",
            ),
            avg_geracao_esperada=(
                "avg_geracao_esperada",
                "sum",
            ),
        )
        .reset_index()
    )

    perfil_pontos["hora"] = pd.to_numeric(
        perfil_pontos["hora"],
        errors="coerce",
    ).astype("Int64")

    series_by_ponto = {}

    for nome_ponto, grupo in perfil_pontos.groupby(
        "nom_pontoconexao",
        dropna=True,
        observed=True,
    ):
        series_by_ponto[
            str(nome_ponto)
        ] = {
            "horas": HORAS_DIA.copy(),
            "avg_geracao": criar_serie_24(
                grupo,
                coluna_valor="avg_geracao",
            ),
            "avg_curtailment": criar_serie_24(
                grupo,
                coluna_valor="avg_curtailment",
            ),
            "avg_geracao_esperada": criar_serie_24(
                grupo,
                coluna_valor=(
                    "avg_geracao_esperada"
                ),
            ),
        }

    pontos_perfil = set(
        perfil_pontos["nom_pontoconexao"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    pontos_series = set(
        series_by_ponto.keys()
    )

    pontos_sem_series = sorted(
        pontos_perfil - pontos_series
    )

    relatorio = {
        "linhas_perfil_usinas": len(
            perfil_usinas
        ),
        "linhas_perfil_pontos": len(
            perfil_pontos
        ),
        "pontos_no_perfil": len(
            pontos_perfil
        ),
        "pontos_com_series": len(
            pontos_series
        ),
        "pontos_sem_series": pontos_sem_series,
        "horas_distintas": int(
            perfil_pontos["hora"]
            .nunique(dropna=True)
        ),
    }

    return (perfil_pontos,series_by_ponto,relatorio)

def criar_indices_series_pontos(df_series,df_pontos_georreferenciados,series_by_ponto,series_by_ponto_code):
    """
    Cria índices auxiliares para localizar as séries dos
    pontos por nome normalizado e por código.

    As séries por nome contemplam todos os pontos presentes
    na base analítica.

    Os índices por código são criados somente para os pontos
    georreferenciados, reproduzindo o comportamento do mapa
    original, pois somente esses pontos possuem marcadores.

    Parâmetros
    ----------
    df_series : pandas.DataFrame
        Base completa retornada por
        preparar_base_series_mapa().

    df_pontos_georreferenciados : pandas.DataFrame
        Base contendo somente pontos com coordenadas
        disponíveis. Pode ser o DataFrame retornado por
        preparar_base_geografica_curtailment() ou o
        GeoDataFrame de pontos.

    series_by_ponto : dict
        Séries horárias indexadas pelo nome original
        do ponto.

    series_by_ponto_code : dict
        Séries de curtailment por código de restrição,
        indexadas pelo nome original do ponto.

    Retorno
    -------
    tuple
        Dicionário de séries por nome normalizado,
        dicionário de nomes originais, dicionário de séries
        por código do ponto, decomposição por nome
        normalizado, decomposição por código do ponto e
        relatório da execução.
    """

    if df_series is None:
        raise ValueError(
            "A base preparada para as séries não foi informada."
        )

    if df_series.empty:
        raise ValueError(
            "A base preparada para as séries está vazia."
        )

    if df_pontos_georreferenciados is None:
        raise ValueError(
            "A base de pontos georreferenciados "
            "não foi informada."
        )

    if df_pontos_georreferenciados.empty:
        raise ValueError(
            "A base de pontos georreferenciados está vazia."
        )

    if series_by_ponto is None:
        raise ValueError(
            "As séries dos pontos não foram informadas."
        )

    if series_by_ponto_code is None:
        raise ValueError(
            "As séries de decomposição por código "
            "não foram informadas."
        )

    colunas_obrigatorias_series = [
        "nom_pontoconexao",
        "cod_pontoconexao",
    ]

    colunas_ausentes_series = [
        coluna
        for coluna in colunas_obrigatorias_series
        if coluna not in df_series.columns
    ]

    if colunas_ausentes_series:
        raise ValueError(
            "Colunas ausentes na base completa de séries: "
            f"{colunas_ausentes_series}"
        )

    colunas_ausentes_georreferenciadas = [
        coluna
        for coluna in colunas_obrigatorias_series
        if coluna not in df_pontos_georreferenciados.columns
    ]

    if colunas_ausentes_georreferenciadas:
        raise ValueError(
            "Colunas ausentes na base de pontos "
            "georreferenciados: "
            f"{colunas_ausentes_georreferenciadas}"
        )

    # ========================================================
    # ÍNDICES POR NOME NORMALIZADO
    # ========================================================

    series_by_ponto_norm = {}
    nome_original_by_norm = {}
    nomes_normalizados_duplicados = []

    for nome_original, dados in series_by_ponto.items():
        nome_normalizado = normalizar_nome(
            nome_original
        )

        if (
            nome_normalizado in series_by_ponto_norm
            and nome_original_by_norm[
                nome_normalizado
            ] != str(nome_original)
        ):
            nomes_normalizados_duplicados.append(
                {
                    "nome_normalizado": nome_normalizado,
                    "primeiro_nome": nome_original_by_norm[
                        nome_normalizado
                    ],
                    "outro_nome": str(nome_original),
                }
            )

            continue

        series_by_ponto_norm[
            nome_normalizado
        ] = dados

        nome_original_by_norm[
            nome_normalizado
        ] = str(nome_original)

    series_by_ponto_code_norm = {}

    colisoes_decomposicao_normalizada = []

    for nome_original, mapa_codigos in (
        series_by_ponto_code.items()
    ):
        nome_normalizado = normalizar_nome(
            nome_original
        )

        if (
            nome_normalizado
            in series_by_ponto_code_norm
        ):
            colisoes_decomposicao_normalizada.append(
                nome_normalizado
            )

            continue

        series_by_ponto_code_norm[
            nome_normalizado
        ] = mapa_codigos

    # ========================================================
    # MAPA CÓDIGO → NOME DOS PONTOS GEORREFERENCIADOS
    # ========================================================

    base_codigo_nome = (
        df_pontos_georreferenciados[
            [
                "cod_pontoconexao",
                "nom_pontoconexao",
            ]
        ]
        .dropna(
            subset=[
                "cod_pontoconexao",
                "nom_pontoconexao",
            ]
        )
        .copy()
    )

    contagem_codigo_nome = (
        base_codigo_nome
        .groupby(
            [
                "cod_pontoconexao",
                "nom_pontoconexao",
            ],
            dropna=True,
            observed=True,
        )
        .size()
        .reset_index(
            name="quantidade"
        )
    )

    mapa_codigo_nome = (
        contagem_codigo_nome
        .sort_values(
            [
                "cod_pontoconexao",
                "quantidade",
                "nom_pontoconexao",
            ],
            ascending=[
                True,
                False,
                True,
            ],
        )
        .drop_duplicates(
            subset=["cod_pontoconexao"],
            keep="first",
        )
        .set_index(
            "cod_pontoconexao"
        )["nom_pontoconexao"]
        .to_dict()
    )

    # ========================================================
    # ÍNDICES POR CÓDIGO DO PONTO
    # ========================================================

    series_by_codigo = {}
    series_by_ponto_code_by_codigo = {}

    codigos_sem_serie = []
    codigos_sem_decomposicao = []

    for codigo_ponto, nome_ponto in (
        mapa_codigo_nome.items()
    ):
        codigo_texto = str(
            codigo_ponto
        )

        nome_normalizado = normalizar_nome(
            nome_ponto
        )

        dados_serie = series_by_ponto_norm.get(
            nome_normalizado
        )

        if dados_serie is not None:
            series_by_codigo[
                codigo_texto
            ] = dados_serie
        else:
            codigos_sem_serie.append(
                codigo_texto
            )

        dados_decomposicao = (
            series_by_ponto_code_norm.get(
                nome_normalizado
            )
        )

        if dados_decomposicao is not None:
            series_by_ponto_code_by_codigo[
                codigo_texto
            ] = dados_decomposicao
        else:
            codigos_sem_decomposicao.append(
                codigo_texto
            )

    # ========================================================
    # PONTOS ANALÍTICOS SEM MARCADOR GEOGRÁFICO
    # ========================================================

    nomes_com_series = set(
        series_by_ponto_norm.keys()
    )

    nomes_georreferenciados = {
        normalizar_nome(nome)
        for nome in base_codigo_nome[
            "nom_pontoconexao"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    }

    pontos_sem_marcador_geografico = sorted(
        nomes_com_series
        - nomes_georreferenciados
    )

    nomes_originais_sem_marcador = [
        nome_original_by_norm.get(
            nome_normalizado,
            nome_normalizado,
        )
        for nome_normalizado
        in pontos_sem_marcador_geografico
    ]

    # ========================================================
    # RELATÓRIO
    # ========================================================

    relatorio = {
        "pontos_por_nome_original": len(
            series_by_ponto
        ),
        "pontos_por_nome_normalizado": len(
            series_by_ponto_norm
        ),
        "nomes_normalizados_duplicados": (
            nomes_normalizados_duplicados
        ),
        "quantidade_nomes_normalizados_duplicados": len(
            nomes_normalizados_duplicados
        ),
        "colisoes_decomposicao_normalizada": sorted(
            set(
                colisoes_decomposicao_normalizada
            )
        ),
        "codigos_georreferenciados_mapeados": len(
            mapa_codigo_nome
        ),
        "codigos_com_serie": len(
            series_by_codigo
        ),
        "codigos_sem_serie": sorted(
            codigos_sem_serie
        ),
        "codigos_com_decomposicao": len(
            series_by_ponto_code_by_codigo
        ),
        "codigos_sem_decomposicao": sorted(
            codigos_sem_decomposicao
        ),
        "pontos_com_series_sem_marcador": (
            sorted(
                nomes_originais_sem_marcador
            )
        ),
        "quantidade_pontos_com_series_sem_marcador": len(
            nomes_originais_sem_marcador
        ),
    }

    return (series_by_ponto_norm,nome_original_by_norm,series_by_codigo,series_by_ponto_code_norm,series_by_ponto_code_by_codigo,relatorio)

def criar_indices_series_coordenadas(
    gdf_usinas,
    gdf_pontos,
    series_by_usina_nome,
    series_by_usina_code,
    series_by_ponto_norm,
    series_by_codigo,
    series_by_ponto_code_norm,
    series_by_ponto_code_by_codigo,
):
    """
    Associa as séries horárias às coordenadas dos marcadores.

    A função cria dois índices:

    - séries de usinas agrupadas por latitude e longitude;
    - séries de pontos agrupadas por latitude e longitude.

    Mais de uma usina ou ponto pode ocupar a mesma coordenada.
    Nesses casos, os itens são preservados em uma lista.

    Parâmetros
    ----------
    gdf_usinas : geopandas.GeoDataFrame
        GeoDataFrame das usinas georreferenciadas.
    gdf_pontos : geopandas.GeoDataFrame
        GeoDataFrame dos pontos de conexão georreferenciados.
    series_by_usina_nome : dict
        Séries horárias indexadas pelo nome da usina.
    series_by_usina_code : dict
        Decomposição por código de restrição e usina.
    series_by_ponto_norm : dict
        Séries dos pontos indexadas pelo nome normalizado.
    series_by_codigo : dict
        Séries dos pontos indexadas pelo código do ponto.
    series_by_ponto_code_norm : dict
        Decomposição dos pontos por nome normalizado.
    series_by_ponto_code_by_codigo : dict
        Decomposição dos pontos por código do ponto.

    Retorno
    -------
    tuple
        Índice geográfico das usinas, índice geográfico dos
        pontos e relatório da execução.
    """

    if gdf_usinas is None or gdf_pontos is None:
        raise ValueError(
            "Os GeoDataFrames de usinas e pontos "
            "devem ser informados."
        )

    if gdf_usinas.empty:
        raise ValueError(
            "O GeoDataFrame de usinas está vazio."
        )

    if gdf_pontos.empty:
        raise ValueError(
            "O GeoDataFrame de pontos está vazio."
        )

    dicionarios_obrigatorios = {
        "series_by_usina_nome": series_by_usina_nome,
        "series_by_usina_code": series_by_usina_code,
        "series_by_ponto_norm": series_by_ponto_norm,
        "series_by_codigo": series_by_codigo,
        "series_by_ponto_code_norm": (
            series_by_ponto_code_norm
        ),
        "series_by_ponto_code_by_codigo": (
            series_by_ponto_code_by_codigo
        ),
    }

    dicionarios_ausentes = [
        nome
        for nome, valor in dicionarios_obrigatorios.items()
        if valor is None
    ]

    if dicionarios_ausentes:
        raise ValueError(
            "Dicionários de séries não informados: "
            f"{dicionarios_ausentes}"
        )

    colunas_usinas_obrigatorias = [
        "nom_usina",
        "geometry",
    ]

    colunas_usinas_ausentes = [
        coluna
        for coluna in colunas_usinas_obrigatorias
        if coluna not in gdf_usinas.columns
    ]

    if colunas_usinas_ausentes:
        raise ValueError(
            "Colunas ausentes no GeoDataFrame de usinas: "
            f"{colunas_usinas_ausentes}"
        )

    colunas_pontos_obrigatorias = [
        "nom_pontoconexao",
        "geometry",
    ]

    colunas_pontos_ausentes = [
        coluna
        for coluna in colunas_pontos_obrigatorias
        if coluna not in gdf_pontos.columns
    ]

    if colunas_pontos_ausentes:
        raise ValueError(
            "Colunas ausentes no GeoDataFrame de pontos: "
            f"{colunas_pontos_ausentes}"
        )

    possui_codigo_ponto = (
        "cod_pontoconexao"
        in gdf_pontos.columns
    )

    usina_series_map = {}
    usinas_sem_serie = []
    usinas_sem_chave_geografica = []

    for _, linha in gdf_usinas.iterrows():
        nome_usina = str(
            linha["nom_usina"]
        )

        geometria = linha.geometry

        if (
            geometria is None
            or geometria.is_empty
            or not geometria.is_valid
        ):
            usinas_sem_chave_geografica.append(
                nome_usina
            )
            continue

        chave = criar_chave_coordenadas(
            latitude=geometria.y,
            longitude=geometria.x,
        )

        if chave is None:
            usinas_sem_chave_geografica.append(
                nome_usina
            )
            continue

        dados_usina = series_by_usina_nome.get(
            nome_usina
        )

        if dados_usina is None:
            usinas_sem_serie.append(
                nome_usina
            )
            continue

        payload_usina = dados_usina.copy()

        payload_usina["curt_by_code"] = (
            series_by_usina_code.get(
                nome_usina,
                {},
            )
        )

        usina_series_map.setdefault(
            chave,
            [],
        ).append(
            payload_usina
        )

    ponto_series_by_latlon = {}
    pontos_sem_serie = []
    pontos_sem_decomposicao = []
    pontos_sem_chave_geografica = []

    for _, linha in gdf_pontos.iterrows():
        nome_ponto = str(
            linha["nom_pontoconexao"]
        )

        geometria = linha.geometry

        if (
            geometria is None
            or geometria.is_empty
            or not geometria.is_valid
        ):
            pontos_sem_chave_geografica.append(
                nome_ponto
            )
            continue

        chave = criar_chave_coordenadas(
            latitude=geometria.y,
            longitude=geometria.x,
        )

        if chave is None:
            pontos_sem_chave_geografica.append(
                nome_ponto
            )
            continue

        nome_normalizado = normalizar_nome(
            nome_ponto
        )

        codigo_ponto = None

        if possui_codigo_ponto:
            codigo_valor = linha.get(
                "cod_pontoconexao"
            )

            if pd.notna(codigo_valor):
                codigo_ponto = str(
                    codigo_valor
                )

        dados_ponto = None
        dados_decomposicao = None

        if codigo_ponto is not None:
            dados_ponto = series_by_codigo.get(
                codigo_ponto
            )

            dados_decomposicao = (
                series_by_ponto_code_by_codigo.get(
                    codigo_ponto
                )
            )

        if dados_ponto is None:
            dados_ponto = series_by_ponto_norm.get(
                nome_normalizado
            )

        if dados_decomposicao is None:
            dados_decomposicao = (
                series_by_ponto_code_norm.get(
                    nome_normalizado
                )
            )

        if dados_ponto is None:
            pontos_sem_serie.append(
                nome_ponto
            )
            continue

        if dados_decomposicao is None:
            pontos_sem_decomposicao.append(
                nome_ponto
            )

        payload_ponto = {
            "nome_ponto": nome_ponto,
            "horas": dados_ponto.get(
                "horas"
            ),
            "avg_geracao": dados_ponto.get(
                "avg_geracao"
            ),
            "avg_curtailment": dados_ponto.get(
                "avg_curtailment"
            ),
            "avg_geracao_esperada": (
                dados_ponto.get(
                    "avg_geracao_esperada"
                )
            ),
            "curt_by_code": (
                dados_decomposicao
                if dados_decomposicao is not None
                else {}
            ),
        }

        ponto_series_by_latlon.setdefault(
            chave,
            [],
        ).append(
            payload_ponto
        )

    relatorio = {
        "usinas_georreferenciadas": len(
            gdf_usinas
        ),
        "usinas_com_series_geograficas": sum(
            len(lista)
            for lista in usina_series_map.values()
        ),
        "coordenadas_distintas_usinas": len(
            usina_series_map
        ),
        "usinas_sem_serie": sorted(
            set(usinas_sem_serie)
        ),
        "usinas_sem_chave_geografica": sorted(
            set(usinas_sem_chave_geografica)
        ),

        "pontos_georreferenciados": len(
            gdf_pontos
        ),
        "pontos_com_series_geograficas": sum(
            len(lista)
            for lista in ponto_series_by_latlon.values()
        ),
        "coordenadas_distintas_pontos": len(
            ponto_series_by_latlon
        ),
        "pontos_sem_serie": sorted(
            set(pontos_sem_serie)
        ),
        "pontos_sem_decomposicao": sorted(
            set(pontos_sem_decomposicao)
        ),
        "pontos_sem_chave_geografica": sorted(
            set(pontos_sem_chave_geografica)
        ),
    }

    return (usina_series_map,ponto_series_by_latlon,relatorio)
