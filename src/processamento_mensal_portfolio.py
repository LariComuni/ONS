"""Leitura incremental para CP45 e Portfólio, sem intermediação geográfica."""
import pandas as pd

from .analise_ativos_elera import ATIVOS_ELERA
from .analise_cp45 import CENARIOS_CP45
from .cenarios_cp45 import montar_base_cenarios_cp45
from .leitura_evt_parquet import carregar_periodo_evt_parquet
from .leitura_parquet import carregar_periodo_parquet
from .periodo_evt_cp45 import carregar_evt_selecionado
from .preparacao_cp45 import montar_base_fontes_cp45, preparar_ativos_horarios_cp45


COLUNAS_CP45_INTERFACE = [
    "din_instante", "ativo", "subsistema", "fonte", "geracao_esperada_mwh",
    *(c["coluna_curtailment"] for c in CENARIOS_CP45.values()),
]
COLUNAS_INPUT_CP45 = [
    "din_instante", "nom_usina", "id_subsistema", "fonte", "cod_razaorestricao",
    "val_curtailment", "val_geracao_esperada",
]
COLUNAS_CATEGORICAS_CP45 = ["ativo", "subsistema", "fonte"]


def _competencias(ano_inicial, mes_inicial, ano_final, mes_final):
    inicio = (ano_inicial, mes_inicial)
    fim = (ano_final, mes_final)
    if not (2024 <= ano_inicial <= ano_final <= 2026 and
            1 <= mes_inicial <= 12 and 1 <= mes_final <= 12 and inicio <= fim):
        raise ValueError("Selecione um período válido entre 2024 e 2026.")
    for ano in range(ano_inicial, ano_final + 1):
        for mes in range(mes_inicial if ano == ano_inicial else 1,
                         (mes_final if ano == ano_final else 12) + 1):
            yield ano, mes


def carregar_portfolio_mensal(ano_inicial, mes_inicial, ano_final, mes_final,
                              fontes, *, ler_curtailment=carregar_periodo_parquet):
    """Retém o grão original e a ordem fonte/mês para análises e exportações."""
    competencias = list(_competencias(ano_inicial, mes_inicial, ano_final, mes_final))
    partes = []
    tem_cobertura = False
    for fonte in fontes:
        for ano, mes in competencias:
            bruto, _ = ler_curtailment(fonte, ano, mes, mes)
            tem_cobertura |= not bruto.empty
            mascara = bruto["nom_usina"].astype("string").str.strip().isin(ATIVOS_ELERA)
            if mascara.any():
                partes.append(bruto.loc[mascara].copy())
            del bruto
    if not tem_cobertura:
        raise ValueError("Sem cobertura solar antes de abril de 2024. Selecione outro período.")
    if not partes:
        raise ValueError("Nenhum ativo da Elera foi encontrado na base processada.")
    return pd.concat(partes, ignore_index=True)


def _mes_cp45(ano, mes, pld, historico_misto, ler_curtailment, ler_evt):
    curtailment = pd.concat([
        ler_curtailment(fonte, ano, mes, mes)[0][COLUNAS_INPUT_CP45]
        for fonte in ("EOL", "UFV")
    ], ignore_index=True)
    evt = carregar_evt_selecionado(ano, mes, ano, mes, ler_evt)
    base = montar_base_fontes_cp45(
        curtailment, evt, pld, permitir_ufv_antes_cobertura=historico_misto and (ano, mes) < (2024, 4),
    )
    del evt
    ativos = preparar_ativos_horarios_cp45(curtailment)
    del curtailment
    resultado = montar_base_cenarios_cp45(base, ativos)["ativos"][COLUNAS_CP45_INTERFACE]
    for coluna in COLUNAS_CATEGORICAS_CP45:
        resultado[coluna] = resultado[coluna].astype("category")
    # O diagnóstico mensal já foi validado, e não é consumido pela interface.
    resultado.attrs.clear()
    return resultado


def preparar_cp45_mensal(ano_inicial, mes_inicial, ano_final, mes_final, pld,
                          *, ler_curtailment=carregar_periodo_parquet,
                          ler_evt=carregar_periodo_evt_parquet):
    """Calcula as taxas por hora como antes, sem reter insumos de mais de um mês."""
    historico_misto = (ano_final, mes_final) >= (2024, 4)
    partes = [_mes_cp45(ano, mes, pld, historico_misto, ler_curtailment, ler_evt)
              for ano, mes in _competencias(ano_inicial, mes_inicial, ano_final, mes_final)]
    # Unificar categorias evita que o concat transforme códigos compactos em strings.
    for coluna in COLUNAS_CATEGORICAS_CP45:
        categorias = partes[0][coluna].cat.categories
        for parte in partes[1:]:
            categorias = categorias.union(parte[coluna].cat.categories, sort=False)
        for parte in partes:
            parte[coluna] = parte[coluna].cat.set_categories(categorias)
    return pd.concat(partes, ignore_index=True)
