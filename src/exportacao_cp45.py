"""Exportação horária dos resultados já calculados da CP45."""
from io import BytesIO

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell

from .analise_cp45 import CENARIOS_CP45
from .dados_pld import MAPA_COLUNAS_SUBMERCADO

COLUNAS_EXCEL_CP45 = (
    "Dia", "Hora", "Descolamento PLD", "Curtailment (MWh)",
    "Geração Esperada (MWh)", "Corte (%)",
)


def _classificar_pld(pld, horas):
    """Usa a mesma indicação da CP45, distinguindo horas sem os quatro PLDs."""
    colunas_pld = list(MAPA_COLUNAS_SUBMERCADO.values())
    instantes = pd.to_datetime(pld["DIN_INSTANTE"], errors="raise")
    numeros = pld[colunas_pld].apply(pd.to_numeric, errors="coerce")
    completo = np.isfinite(numeros.to_numpy(dtype=float, na_value=np.nan)).all(axis=1)
    existe_descolamento = pld["DESCOLAMENTO_HORARIO"].fillna(False).to_numpy(dtype=bool)
    situacao = np.where(completo, np.where(existe_descolamento, "Sim", "Não"), "Sem dados")
    return pd.Series(situacao, index=instantes).reindex(horas).fillna("Sem dados")


def gerar_excel_horario_cp45(base_horaria, pld_aberto):
    """Uma linha por hora observada e uma folha por cenário para o recorte atual."""
    if base_horaria.empty:
        raise ValueError("O recorte selecionado não tem resultados horários.")
    geracao = "geracao_esperada_mwh"
    cortes = [cenario["coluna_curtailment"] for cenario in CENARIOS_CP45.values()]
    instantes = pd.to_datetime(base_horaria["din_instante"], errors="raise")
    if instantes.isna().any() or not instantes.eq(instantes.dt.floor("h")).all():
        raise ValueError("A base da CP45 contém instantes que não estão na frequência horária.")

    # MWh já estão integrados por hora. Some antes de calcular o percentual.
    valores = base_horaria[[geracao, *cortes]].apply(pd.to_numeric, errors="coerce")
    horario = valores.groupby(instantes, sort=True).sum()
    situacao_pld = _classificar_pld(pld_aberto, horario.index).tolist()
    instantes_excel = [(ts.date(), ts.time()) for ts in horario.index]
    geracoes = horario[geracao].tolist()

    arquivo = Workbook(write_only=True)
    for codigo, cenario in CENARIOS_CP45.items():
        folha = arquivo.create_sheet(codigo)
        folha.freeze_panes = "C2"
        folha.auto_filter.ref = f"A1:F{len(horario) + 1}"
        for letra, largura in zip("ABCDEF", (14, 10, 21, 23, 27, 15)):
            folha.column_dimensions[letra].width = largura
        folha.append(COLUNAS_EXCEL_CP45)

        for (dia, hora), pld, corte, esperado in zip(
            instantes_excel, situacao_pld, horario[cenario["coluna_curtailment"]], geracoes
        ):
            dia_excel = WriteOnlyCell(folha, value=dia)
            dia_excel.number_format = "dd/mm/yyyy"
            hora_excel = WriteOnlyCell(folha, value=hora)
            hora_excel.number_format = "hh:mm"
            percentual = WriteOnlyCell(folha, value=(corte / esperado if esperado > 0 else None))
            percentual.number_format = "0.00%"
            folha.append((dia_excel, hora_excel, pld, corte, esperado, percentual))

    buffer = BytesIO()
    arquivo.save(buffer)
    return buffer.getvalue()
