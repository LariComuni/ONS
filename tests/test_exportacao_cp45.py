from datetime import datetime, time
from io import BytesIO

import pandas as pd
import pytest
from openpyxl import load_workbook

from src.analise_cp45 import CENARIOS_CP45
from src.dados_pld import preparar_pld_aberto
from src.exportacao_cp45 import COLUNAS_EXCEL_CP45, gerar_excel_horario_cp45


def test_excel_cp45_soma_por_hora_e_separa_cenarios():
    horas = pd.to_datetime(["2026-10-01 00:00", "2026-10-01 01:00", "2026-10-01 02:00", "2026-10-01 03:00"])
    base = pd.DataFrame({
        "din_instante": [horas[1], horas[0], horas[0], horas[2], horas[3]],
        "geracao_esperada_mwh": [0, 100, 300, 100, 200],
    })
    for i, cenario in enumerate(CENARIOS_CP45.values()):
        base[cenario["coluna_curtailment"]] = [0, 10 + i, 90 + i, 0, 0]
    pld = preparar_pld_aberto(pd.DataFrame([
        (hora, sub, (100 + i if h == 0 else 100))
        for h, hora in enumerate(horas[:3])
        for i, sub in enumerate(["SUDESTE", "SUL", "NORDESTE", "NORTE"] if h < 2 else ["NORTE"])
    ], columns=["DIN_INSTANTE", "SUBMERCADO", "PLD_HORA"]))

    wb = load_workbook(BytesIO(gerar_excel_horario_cp45(base, pld)), read_only=True)
    assert wb.sheetnames == list(CENARIOS_CP45)
    for i, codigo in enumerate(wb.sheetnames):
        linhas = list(wb[codigo].values)
        assert linhas[0] == COLUNAS_EXCEL_CP45
        assert len(linhas) == 5
        assert linhas[1] == (datetime(2026, 10, 1), time(0), "Sim", 100 + 2 * i, 400, (100 + 2 * i) / 400)
        assert linhas[2] == (datetime(2026, 10, 1), time(1), "Não", 0, 0, None)
        assert linhas[3][2] == linhas[4][2] == "Sem dados"
        assert wb[codigo]["F2"].number_format == "0.00%"


def test_exportacao_cp45_nao_fabrica_horas():
    with pytest.raises(ValueError, match="não tem resultados"):
        gerar_excel_horario_cp45(pd.DataFrame(), pd.DataFrame())
