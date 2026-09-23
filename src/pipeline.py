"""
Orquestração do pipeline de preparação dos dados da aplicação.

O módulo integra:

- coleta dos dados EOL e UFV do ONS;
- cálculo do curtailment;
- coleta das bases auxiliares;
- enriquecimento geográfico;
- agregação por instante e ponto;
- preparação da rede de transmissão;
- criação das geometrias;
- criação do índice de busca;
- preparação das séries horárias do mapa.

A função principal é preparar_dados_aplicacao().
"""

from datetime import date

import pandas as pd

from .agregacoes import agregar_por_instante_e_ponto
from .calculo_curtailment import calcular_curtailment
from .coleta_auxiliares import (
    carregar_linhas_transmissao,
    carregar_subestacoes,
    carregar_ultimo_fator_capacidade_completo,
)
from .coleta_ons import carregar_periodo_ons
from .enriquecimento_geografico import (
    enriquecer_curtailment,
    reduzir_fator_capacidade,
)
from .preparacao_geometrias import (
    criar_geometrias_linhas,
    criar_geometrias_pontos,
    criar_geometrias_usinas,
    criar_indice_busca,
    preparar_base_geografica_curtailment,
    preparar_base_geografica_linhas,
)
from .preparacao_rede import (
    enriquecer_linhas_transmissao,
    preparar_subestacoes,
)
from .series_mapa import (
    calcular_decomposicao_curtailment,
    calcular_perfil_horario_pontos,
    calcular_perfil_horario_usinas,
    criar_indices_series_coordenadas,
    criar_indices_series_pontos,
    preparar_base_series_mapa,
)


FONTES_CURTAILMENT_PERMITIDAS = (
    "EOL",
    "UFV",
)


def validar_periodo(
    ano_inicial,
    mes_inicial,
    ano_final,
    mes_final,
):
    """
    Valida um período mensal que pode abranger vários anos.

    Parâmetros
    ----------
    ano_inicial : int
        Ano da primeira competência.
    mes_inicial : int
        Mês da primeira competência.
    ano_final : int
        Ano da última competência.
    mes_final : int
        Mês da última competência.

    Raises
    ------
    TypeError
        Quando algum parâmetro não é inteiro.
    ValueError
        Quando os meses são inválidos ou a competência
        inicial é posterior à competência final.
    """

    parametros = {
        "ano inicial": ano_inicial,
        "mês inicial": mes_inicial,
        "ano final": ano_final,
        "mês final": mes_final,
    }

    for nome, valor in parametros.items():
        if not isinstance(
            valor,
            int,
        ):
            raise TypeError(
                f"O {nome} deve ser informado "
                "como número inteiro."
            )

    if not 1 <= mes_inicial <= 12:
        raise ValueError(
            "O mês inicial deve estar entre 1 e 12."
        )

    if not 1 <= mes_final <= 12:
        raise ValueError(
            "O mês final deve estar entre 1 e 12."
        )

    competencia_inicial = (
        ano_inicial,
        mes_inicial,
    )

    competencia_final = (
        ano_final,
        mes_final,
    )

    if competencia_inicial > competencia_final:
        raise ValueError(
            "A competência inicial não pode ser posterior "
            "à competência final."
        )


def dividir_periodo_por_ano(
    ano_inicial,
    mes_inicial,
    ano_final,
    mes_final,
):
    """
    Divide um período de múltiplos anos em intervalos anuais.

    A divisão é necessária porque carregar_periodo_ons()
    recebe apenas um ano por chamada.

    Retorno
    -------
    list
        Lista de dicionários com ano, mês inicial e mês final.
    """

    validar_periodo(
        ano_inicial=ano_inicial,
        mes_inicial=mes_inicial,
        ano_final=ano_final,
        mes_final=mes_final,
    )

    periodos = []

    for ano in range(
        ano_inicial,
        ano_final + 1,
    ):
        if ano == ano_inicial:
            primeiro_mes = mes_inicial
        else:
            primeiro_mes = 1

        if ano == ano_final:
            ultimo_mes = mes_final
        else:
            ultimo_mes = 12

        periodos.append(
            {
                "ano": ano,
                "mes_inicial": primeiro_mes,
                "mes_final": ultimo_mes,
            }
        )

    return periodos


def validar_fontes(
    fontes,
):
    """
    Valida as fontes selecionadas para o pipeline.

    Parâmetros
    ----------
    fontes : list ou tuple
        Fontes que serão coletadas. São aceitas EOL e UFV.

    Retorno
    -------
    tuple
        Fontes validadas, sem duplicidades.
    """

    if fontes is None:
        return FONTES_CURTAILMENT_PERMITIDAS

    if not isinstance(
        fontes,
        (list, tuple),
    ):
        raise TypeError(
            "As fontes devem ser informadas como "
            "lista ou tupla."
        )

    if not fontes:
        raise ValueError(
            "Pelo menos uma fonte deve ser selecionada."
        )

    fontes_normalizadas = tuple(
        dict.fromkeys(
            str(fonte)
            .strip()
            .upper()
            for fonte in fontes
        )
    )

    fontes_invalidas = [
        fonte
        for fonte in fontes_normalizadas
        if fonte
        not in FONTES_CURTAILMENT_PERMITIDAS
    ]

    if fontes_invalidas:
        raise ValueError(
            "Foram encontradas fontes inválidas: "
            f"{fontes_invalidas}. "
            "As fontes permitidas são EOL e UFV."
        )

    return fontes_normalizadas


def validar_timeout(
    timeout,
):
    """
    Valida o timeout usado nas coletas auxiliares.
    """

    if not isinstance(
        timeout,
        (int, float),
    ):
        raise TypeError(
            "O timeout deve ser numérico."
        )

    if timeout <= 0:
        raise ValueError(
            "O timeout deve ser maior que zero."
        )


def validar_dataframe(
    dataframe,
    nome,
):
    """
    Valida um DataFrame obrigatório do pipeline.

    Parâmetros
    ----------
    dataframe : pandas.DataFrame
        DataFrame que será validado.
    nome : str
        Nome descritivo usado nas mensagens de erro.
    """

    if dataframe is None:
        raise RuntimeError(
            f"Não foi possível carregar {nome}."
        )

    if not isinstance(
        dataframe,
        pd.DataFrame,
    ):
        raise TypeError(
            f"{nome} deve ser um DataFrame."
        )

    if dataframe.empty:
        raise ValueError(
            f"A base {nome} está vazia."
        )


def validar_resultados_finais(
    gdf_usinas,
    gdf_pontos,
    gdf_linhas_desenhaveis,
    gdf_busca,
    usina_series_map,
    ponto_series_by_latlon,
    df_agregado_ponto,
):
    """
    Valida as relações estruturais entre os produtos finais.

    As validações não dependem de quantidades fixas, pois
    as bases do ONS podem ser atualizadas.
    """

    quantidade_esperada_busca = (
        len(gdf_usinas)
        + len(gdf_pontos)
    )

    if len(gdf_busca) != quantidade_esperada_busca:
        raise ValueError(
            "O índice de busca não corresponde à soma "
            "de usinas e pontos de conexão. "
            f"Esperado: {quantidade_esperada_busca}. "
            f"Encontrado: {len(gdf_busca)}."
        )

    if gdf_linhas_desenhaveis.empty:
        raise ValueError(
            "A camada de linhas desenháveis está vazia."
        )

    if not isinstance(
        usina_series_map,
        dict,
    ):
        raise TypeError(
            "O índice de séries das usinas deve ser "
            "um dicionário."
        )

    if not usina_series_map:
        raise ValueError(
            "O índice de séries das usinas está vazio."
        )

    if not isinstance(
        ponto_series_by_latlon,
        dict,
    ):
        raise TypeError(
            "O índice de séries dos pontos deve ser "
            "um dicionário."
        )

    if not ponto_series_by_latlon:
        raise ValueError(
            "O índice de séries dos pontos está vazio."
        )

    if df_agregado_ponto.empty:
        raise ValueError(
            "A agregação por instante e ponto resultou "
            "em uma base vazia."
        )


def coletar_e_calcular_curtailment(
    ano_inicial,
    mes_inicial,
    ano_final,
    mes_final,
    fontes,
):
    """
    Coleta e calcula o curtailment das fontes EOL e UFV.

    O período pode abranger vários anos. Cada intervalo
    anual é coletado separadamente e posteriormente
    consolidado.

    Retorno
    -------
    tuple
        DataFrame consolidado e relatórios das coletas e
        dos cálculos.
    """
    fontes_validadas = validar_fontes(
        fontes
    )
    periodos_anuais = dividir_periodo_por_ano(
        ano_inicial=ano_inicial,
        mes_inicial=mes_inicial,
        ano_final=ano_final,
        mes_final=mes_final,
    )

    dados_curtailment = []
    relatorios = {}

    for fonte in fontes_validadas:
        dados_fonte = []
        relatorios_periodos = {}

        for periodo in periodos_anuais:
            ano_periodo = periodo[
                "ano"
            ]

            mes_inicial_periodo = periodo[
                "mes_inicial"
            ]

            mes_final_periodo = periodo[
                "mes_final"
            ]

            (
                df_bruto,
                relatorio_coleta,
            ) = carregar_periodo_ons(
                fonte=fonte,
                ano=ano_periodo,
                mes_inicial=mes_inicial_periodo,
                mes_final=mes_final_periodo,
            )

            validar_dataframe(
                dataframe=df_bruto,
                nome=(
                    "os dados brutos de curtailment "
                    f"da fonte {fonte} para "
                    f"{mes_inicial_periodo:02d}/"
                    f"{ano_periodo} a "
                    f"{mes_final_periodo:02d}/"
                    f"{ano_periodo}"
                ),
            )

            df_fonte_periodo = calcular_curtailment(
                df=df_bruto,
                fonte=fonte,
            )

            validar_dataframe(
                dataframe=df_fonte_periodo,
                nome=(
                    "o curtailment calculado "
                    f"da fonte {fonte} para "
                    f"{ano_periodo}"
                ),
            )

            dados_fonte.append(
                df_fonte_periodo
            )

            relatorios_periodos[
                str(ano_periodo)
            ] = {
                "ano": ano_periodo,
                "mes_inicial": (
                    mes_inicial_periodo
                ),
                "mes_final": (
                    mes_final_periodo
                ),
                "registros_entrada": len(
                    df_bruto
                ),
                "registros_saida": len(
                    df_fonte_periodo
                ),
                "coleta": relatorio_coleta,
            }

        df_fonte = pd.concat(
            dados_fonte,
            ignore_index=True,
        )

        validar_dataframe(
            dataframe=df_fonte,
            nome=(
                "o curtailment consolidado "
                f"da fonte {fonte}"
            ),
        )

        dados_curtailment.append(
            df_fonte
        )

        relatorios[
            f"fonte_{fonte.lower()}"
        ] = {
            "fonte": fonte,
            "registros": len(
                df_fonte
            ),
            "periodos": (
                relatorios_periodos
            ),
        }

    df_curtailment = pd.concat(
        dados_curtailment,
        ignore_index=True,
    )

    validar_dataframe(
        dataframe=df_curtailment,
        nome="o curtailment consolidado",
    )

    relatorios[
        "consolidacao_curtailment"
    ] = {
        "fontes": list(
            fontes_validadas
        ),
        "ano_inicial": ano_inicial,
        "mes_inicial": mes_inicial,
        "ano_final": ano_final,
        "mes_final": mes_final,
        "periodo_inicial": (
            f"{mes_inicial:02d}/{ano_inicial}"
        ),
        "periodo_final": (
            f"{mes_final:02d}/{ano_final}"
        ),
        "quantidade_anos": len(
            periodos_anuais
        ),
        "periodos_anuais": (
            periodos_anuais
        ),
        "registros": len(
            df_curtailment
        ),
    }

    return (
        df_curtailment,
        relatorios,
    )


def carregar_bases_auxiliares(
    data_referencia,
    timeout,
):
    """
    Carrega fator de capacidade, subestações e linhas.

    Retorno
    -------
    tuple
        Bases auxiliares e relatório da coleta.
    """

    (
        df_fator_capacidade,
        ano_fator_capacidade,
        mes_fator_capacidade,
    ) = carregar_ultimo_fator_capacidade_completo(
        data_referencia=data_referencia,
        timeout=timeout,
    )

    validar_dataframe(
        dataframe=df_fator_capacidade,
        nome="o fator de capacidade",
    )

    df_subestacoes = carregar_subestacoes(
        timeout=timeout,
    )

    validar_dataframe(
        dataframe=df_subestacoes,
        nome="o cadastro de subestações",
    )

    df_linhas = carregar_linhas_transmissao(
        timeout=timeout,
    )

    validar_dataframe(
        dataframe=df_linhas,
        nome="o cadastro de linhas de transmissão",
    )

    relatorio = {
        "ano_fator_capacidade": (
            ano_fator_capacidade
        ),
        "mes_fator_capacidade": (
            mes_fator_capacidade
        ),
        "registros_fator_capacidade": len(
            df_fator_capacidade
        ),
        "registros_subestacoes": len(
            df_subestacoes
        ),
        "registros_linhas": len(
            df_linhas
        ),
    }

    return (
        df_fator_capacidade,
        df_subestacoes,
        df_linhas,
        relatorio,
    )


def preparar_curtailment_geografico(
    df_curtailment,
    df_fator_capacidade,
):
    """
    Enriquece e prepara o curtailment geograficamente.

    Retorno
    -------
    tuple
        Cadastro reduzido, curtailment enriquecido,
        curtailment preparado, curtailment georreferenciado
        e relatórios.
    """

    cadastro_geografico = reduzir_fator_capacidade(
        df_fator_capacidade
    )

    validar_dataframe(
        dataframe=cadastro_geografico,
        nome="o cadastro geográfico reduzido",
    )

    (
        df_curtailment_enriquecido,
        relatorio_enriquecimento,
    ) = enriquecer_curtailment(
        df_curtailment=df_curtailment,
        cadastro_geografico=cadastro_geografico,
    )

    validar_dataframe(
        dataframe=df_curtailment_enriquecido,
        nome="o curtailment enriquecido",
    )

    (
        df_curtailment_preparado,
        df_curtailment_georreferenciado,
        relatorio_geografia,
    ) = preparar_base_geografica_curtailment(
        df_curtailment_enriquecido
    )

    validar_dataframe(
        dataframe=df_curtailment_preparado,
        nome="o curtailment preparado",
    )

    validar_dataframe(
        dataframe=df_curtailment_georreferenciado,
        nome="o curtailment georreferenciado",
    )

    relatorios = {
        "enriquecimento_curtailment": (
            relatorio_enriquecimento
        ),
        "geografia_curtailment": (
            relatorio_geografia
        ),
    }

    return (
        cadastro_geografico,
        df_curtailment_enriquecido,
        df_curtailment_preparado,
        df_curtailment_georreferenciado,
        relatorios,
    )


def preparar_rede_transmissao(
    df_subestacoes,
    df_linhas,
):
    """
    Enriquece e prepara geograficamente a rede de transmissão.

    Retorno
    -------
    tuple
        Subestações preparadas, linhas enriquecidas,
        linhas preparadas, linhas georreferenciadas e
        relatórios.
    """

    subestacoes_preparadas = preparar_subestacoes(
        df_subestacoes
    )

    validar_dataframe(
        dataframe=subestacoes_preparadas,
        nome="as subestações preparadas",
    )

    (
        df_linhas_enriquecidas,
        relatorio_enriquecimento_linhas,
    ) = enriquecer_linhas_transmissao(
        df_linhas=df_linhas,
        subestacoes_preparadas=(
            subestacoes_preparadas
        ),
    )

    validar_dataframe(
        dataframe=df_linhas_enriquecidas,
        nome="as linhas de transmissão enriquecidas",
    )

    (
        df_linhas_preparadas,
        df_linhas_georreferenciadas,
        relatorio_geografia_linhas,
    ) = preparar_base_geografica_linhas(
        df_linhas_enriquecidas
    )

    validar_dataframe(
        dataframe=df_linhas_preparadas,
        nome="as linhas preparadas",
    )

    validar_dataframe(
        dataframe=df_linhas_georreferenciadas,
        nome="as linhas georreferenciadas",
    )

    relatorios = {
        "enriquecimento_linhas": (
            relatorio_enriquecimento_linhas
        ),
        "geografia_linhas": (
            relatorio_geografia_linhas
        ),
    }

    return (
        subestacoes_preparadas,
        df_linhas_enriquecidas,
        df_linhas_preparadas,
        df_linhas_georreferenciadas,
        relatorios,
    )


def criar_camadas_geograficas(
    df_curtailment_georreferenciado,
    df_linhas_georreferenciadas,
):
    """
    Cria os GeoDataFrames utilizados pelo mapa.

    Retorno
    -------
    tuple
        GeoDataFrames de usinas, pontos, linhas, linhas
        desenháveis e índice de busca, além dos relatórios.
    """

    (
        gdf_usinas,
        relatorio_usinas,
    ) = criar_geometrias_usinas(
        df_curtailment_georreferenciado
    )

    (
        gdf_pontos,
        relatorio_pontos,
    ) = criar_geometrias_pontos(
        df_curtailment_georreferenciado
    )

    (
        gdf_linhas,
        gdf_linhas_desenhaveis,
        relatorio_linhas,
    ) = criar_geometrias_linhas(
        df_linhas_georreferenciadas
    )

    (
        gdf_busca,
        relatorio_busca,
    ) = criar_indice_busca(
        gdf_usinas=gdf_usinas,
        gdf_pontos=gdf_pontos,
    )

    relatorios = {
        "geometrias_usinas": (
            relatorio_usinas
        ),
        "geometrias_pontos": (
            relatorio_pontos
        ),
        "geometrias_linhas": (
            relatorio_linhas
        ),
        "indice_busca": (
            relatorio_busca
        ),
    }

    return (
        gdf_usinas,
        gdf_pontos,
        gdf_linhas,
        gdf_linhas_desenhaveis,
        gdf_busca,
        relatorios,
    )


def preparar_series_interativas(
    df_curtailment_enriquecido,
    df_curtailment_georreferenciado,
    gdf_usinas,
    gdf_pontos,
):
    """
    Prepara os perfis horários e índices usados pelo painel.

    Retorno
    -------
    tuple
        Índices por coordenada, bases intermediárias e
        relatórios da preparação das séries.
    """

    (
        df_series,
        relatorio_base_series,
    ) = preparar_base_series_mapa(
        df_curtailment_enriquecido
    )

    validar_dataframe(
        dataframe=df_series,
        nome="a base das séries do mapa",
    )

    (
        usina_hourly,
        series_by_usina_nome,
        relatorio_perfil_usinas,
    ) = calcular_perfil_horario_usinas(
        df_series
    )

    validar_dataframe(
        dataframe=usina_hourly,
        nome="o perfil horário das usinas",
    )

    (
        contribuicoes,
        series_by_usina_code,
        series_by_ponto_code,
        relatorio_decomposicao,
    ) = calcular_decomposicao_curtailment(
        df_series=df_series,
        usina_hourly=usina_hourly,
    )

    (
        perfil_pontos,
        series_by_ponto,
        relatorio_perfil_pontos,
    ) = calcular_perfil_horario_pontos(
        usina_hourly
    )

    validar_dataframe(
        dataframe=perfil_pontos,
        nome="o perfil horário dos pontos",
    )

    (
        series_by_ponto_norm,
        nome_original_by_norm,
        series_by_codigo,
        series_by_ponto_code_norm,
        series_by_ponto_code_by_codigo,
        relatorio_indices_pontos,
    ) = criar_indices_series_pontos(
        df_series=df_series,
        df_pontos_georreferenciados=(
            df_curtailment_georreferenciado
        ),
        series_by_ponto=series_by_ponto,
        series_by_ponto_code=(
            series_by_ponto_code
        ),
    )

    (
        usina_series_map,
        ponto_series_by_latlon,
        relatorio_indices_coordenadas,
    ) = criar_indices_series_coordenadas(
        gdf_usinas=gdf_usinas,
        gdf_pontos=gdf_pontos,
        series_by_usina_nome=(
            series_by_usina_nome
        ),
        series_by_usina_code=(
            series_by_usina_code
        ),
        series_by_ponto_norm=(
            series_by_ponto_norm
        ),
        series_by_codigo=(
            series_by_codigo
        ),
        series_by_ponto_code_norm=(
            series_by_ponto_code_norm
        ),
        series_by_ponto_code_by_codigo=(
            series_by_ponto_code_by_codigo
        ),
    )

    relatorios = {
        "base_series": (
            relatorio_base_series
        ),
        "perfil_usinas": (
            relatorio_perfil_usinas
        ),
        "decomposicao_curtailment": (
            relatorio_decomposicao
        ),
        "perfil_pontos": (
            relatorio_perfil_pontos
        ),
        "indices_pontos": (
            relatorio_indices_pontos
        ),
        "indices_coordenadas": (
            relatorio_indices_coordenadas
        ),
    }

    intermediarios = {
        "df_series": df_series,
        "usina_hourly": usina_hourly,
        "contribuicoes": contribuicoes,
        "perfil_pontos": perfil_pontos,
        "series_by_usina_nome": (
            series_by_usina_nome
        ),
        "series_by_usina_code": (
            series_by_usina_code
        ),
        "series_by_ponto": (
            series_by_ponto
        ),
        "series_by_ponto_code": (
            series_by_ponto_code
        ),
        "series_by_ponto_norm": (
            series_by_ponto_norm
        ),
        "nome_original_by_norm": (
            nome_original_by_norm
        ),
        "series_by_codigo": (
            series_by_codigo
        ),
        "series_by_ponto_code_norm": (
            series_by_ponto_code_norm
        ),
        "series_by_ponto_code_by_codigo": (
            series_by_ponto_code_by_codigo
        ),
    }

    return (
        usina_series_map,
        ponto_series_by_latlon,
        intermediarios,
        relatorios,
    )


def preparar_dados_aplicacao(
    ano_inicial,
    mes_inicial,
    ano_final,
    mes_final,
    fontes=None,
    data_referencia=None,
    timeout=120,
):
    """
    Executa o pipeline completo de preparação da aplicação.

    Parâmetros
    ----------
    ano_inicial : int
        Ano da primeira competência do curtailment.
    mes_inicial : int
        Mês da primeira competência do curtailment.
    ano_final : int
        Ano da última competência do curtailment.
    mes_final : int
        Mês da última competência do curtailment.
    fontes : list ou tuple, opcional
        Fontes que serão processadas. São permitidas EOL e UFV. Quando não informada, utiliza ambas.
    data_referencia : datetime.date, opcional
        Data usada para determinar a última competência
        completa do fator de capacidade. Quando ausente,
        utiliza a data atual.
    timeout : int ou float, opcional
        Tempo máximo, em segundos, para cada coleta auxiliar.

    Retorno
    -------
    dict
        Produtos finais, produtos analíticos intermediários
        e relatórios de todas as etapas.
    """

    validar_periodo(
        ano_inicial=ano_inicial,
        mes_inicial=mes_inicial,
        ano_final=ano_final,
        mes_final=mes_final,
    )

    fontes_validadas = validar_fontes(
        fontes
    )
    
    validar_timeout(
        timeout
    )

    if data_referencia is None:
        data_referencia = date.today()

    if not isinstance(
        data_referencia,
        date,
    ):
        raise TypeError(
            "A data de referência deve ser uma instância "
            "de datetime.date."
        )

    relatorios = {}

    (
        df_curtailment,
        relatorios_curtailment,
    ) = coletar_e_calcular_curtailment(
        ano_inicial=ano_inicial,
        mes_inicial=mes_inicial,
        ano_final=ano_final,
        mes_final=mes_final,
        fontes=fontes_validadas,
    )

    relatorios.update(
        relatorios_curtailment
    )

    (
        df_fator_capacidade,
        df_subestacoes,
        df_linhas,
        relatorio_auxiliares,
    ) = carregar_bases_auxiliares(
        data_referencia=data_referencia,
        timeout=timeout,
    )

    relatorios[
        "bases_auxiliares"
    ] = relatorio_auxiliares

    (
        cadastro_geografico,
        df_curtailment_enriquecido,
        df_curtailment_preparado,
        df_curtailment_georreferenciado,
        relatorios_geografia_curtailment,
    ) = preparar_curtailment_geografico(
        df_curtailment=df_curtailment,
        df_fator_capacidade=(
            df_fator_capacidade
        ),
    )

    relatorios.update(
        relatorios_geografia_curtailment
    )

    (
        df_agregado_ponto,
        relatorio_agregacao_ponto,
    ) = agregar_por_instante_e_ponto(
        df_curtailment_enriquecido
    )

    validar_dataframe(
        dataframe=df_agregado_ponto,
        nome="a agregação por instante e ponto",
    )

    relatorios[
        "agregacao_ponto"
    ] = relatorio_agregacao_ponto

    (
        subestacoes_preparadas,
        df_linhas_enriquecidas,
        df_linhas_preparadas,
        df_linhas_georreferenciadas,
        relatorios_rede,
    ) = preparar_rede_transmissao(
        df_subestacoes=df_subestacoes,
        df_linhas=df_linhas,
    )

    relatorios.update(
        relatorios_rede
    )

    (
        gdf_usinas,
        gdf_pontos,
        gdf_linhas,
        gdf_linhas_desenhaveis,
        gdf_busca,
        relatorios_geometrias,
    ) = criar_camadas_geograficas(
        df_curtailment_georreferenciado=(
            df_curtailment_georreferenciado
        ),
        df_linhas_georreferenciadas=(
            df_linhas_georreferenciadas
        ),
    )

    relatorios.update(
        relatorios_geometrias
    )

    (
        usina_series_map,
        ponto_series_by_latlon,
        intermediarios_series,
        relatorios_series,
    ) = preparar_series_interativas(
        df_curtailment_enriquecido=(
            df_curtailment_enriquecido
        ),
        df_curtailment_georreferenciado=(
            df_curtailment_georreferenciado
        ),
        gdf_usinas=gdf_usinas,
        gdf_pontos=gdf_pontos,
    )

    relatorios.update(
        relatorios_series
    )

    validar_resultados_finais(
        gdf_usinas=gdf_usinas,
        gdf_pontos=gdf_pontos,
        gdf_linhas_desenhaveis=(
            gdf_linhas_desenhaveis
        ),
        gdf_busca=gdf_busca,
        usina_series_map=(
            usina_series_map
        ),
        ponto_series_by_latlon=(
            ponto_series_by_latlon
        ),
        df_agregado_ponto=(
            df_agregado_ponto
        ),
    )
    
    periodos_anuais = dividir_periodo_por_ano(
        ano_inicial=ano_inicial,
        mes_inicial=mes_inicial,
        ano_final=ano_final,
        mes_final=mes_final,
    )
    
    relatorios[
        "resumo_pipeline"
    ] = {
        "ano_inicial": ano_inicial,
        "mes_inicial": mes_inicial,
        "ano_final": ano_final,
        "mes_final": mes_final,
        "periodo_inicial": (
            f"{mes_inicial:02d}/{ano_inicial}"
        ),
        "periodo_final": (
            f"{mes_final:02d}/{ano_final}"
        ),
        "fontes": list(
            fontes_validadas
        ),
        "quantidade_anos": len(
            periodos_anuais
        ),
        "periodos_anuais": (
            periodos_anuais
        ),
        "data_referencia": (
            data_referencia.isoformat()
        ),
        "registros_curtailment": len(
            df_curtailment
        ),
        "registros_curtailment_enriquecido": len(
            df_curtailment_enriquecido
        ),
        "registros_agregados_ponto": len(
            df_agregado_ponto
        ),
        "usinas": len(
            gdf_usinas
        ),
        "pontos": len(
            gdf_pontos
        ),
        "linhas": len(
            gdf_linhas
        ),
        "linhas_desenhaveis": len(
            gdf_linhas_desenhaveis
        ),
        "registros_busca": len(
            gdf_busca
        ),
        "coordenadas_usinas": len(
            usina_series_map
        ),
        "coordenadas_pontos": len(
            ponto_series_by_latlon
        ),
    }

    return {
        "gdf_usinas": gdf_usinas,
        "gdf_pontos": gdf_pontos,
        "gdf_linhas": gdf_linhas,
        "gdf_linhas_desenhaveis": (
            gdf_linhas_desenhaveis
        ),
        "gdf_busca": gdf_busca,
        "usina_series_map": (
            usina_series_map
        ),
        "ponto_series_by_latlon": (
            ponto_series_by_latlon
        ),
        "df_agregado_ponto": (
            df_agregado_ponto
        ),
        "df_curtailment": (
            df_curtailment
        ),
        "df_curtailment_enriquecido": (
            df_curtailment_enriquecido
        ),
        "df_curtailment_preparado": (
            df_curtailment_preparado
        ),
        "df_curtailment_georreferenciado": (
            df_curtailment_georreferenciado
        ),
        "cadastro_geografico": (
            cadastro_geografico
        ),
        "subestacoes_preparadas": (
            subestacoes_preparadas
        ),
        "df_linhas_enriquecidas": (
            df_linhas_enriquecidas
        ),
        "df_linhas_preparadas": (
            df_linhas_preparadas
        ),
        "df_linhas_georreferenciadas": (
            df_linhas_georreferenciadas
        ),
        **intermediarios_series,
        "relatorios": relatorios,
    }
