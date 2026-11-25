import os

import numpy as np
import pandas as pd
import pytest

from src import analise_subsistemas as a
from src.subsistemas_monthly import compactar_subsistemas, preparar_dados_subsistemas

TOTAL = "Curtailment Todos médio (MW)"
CONTAGEM = "Intervalos de 30 min observados"


def base(perfis):
    df = pd.DataFrame(perfis, columns=[
        "din_instante", "id_subsistema", "cod_razaorestricao", "val_curtailment",
    ])
    df["val_geracao_esperada"] = 100
    return df


@pytest.mark.parametrize("compactar", [False, True])
def test_perfil_usa_intervalos_observados_e_alinha_pico(compactar):
    registros = []
    for dia, valor in (("01", 60), ("02", 0)):
        registros += [(f"2026-10-{dia} 12:00", "N", "ENE", 20)] * 4
        registros += [(f"2026-10-{dia} 19:00", "N", "REL" if valor else None, valor)]
    df = base(registros)
    if compactar:
        df = compactar_subsistemas(df)

    excel = a.preparar_download_perfil_horario(df)
    norte = excel.set_index(["Subsistema", "Hora"]).loc["N"]
    heatmap = a.preparar_perfil_horario_curtailment(df, "TODOS", perfil=excel)
    assert norte.loc["19:00", CONTAGEM] == 2
    assert norte.loc["19:00", TOTAL] == heatmap.loc["N", 19] == 30
    assert heatmap.loc["N", 12] == 80
    assert norte.loc["12:00", CONTAGEM] == 2
    assert norte.loc["18:00", CONTAGEM] == 0
    assert np.isnan(heatmap.loc["N", 18])
    assert np.isnan(heatmap.loc["S", 19])
    assert a.preparar_resumo_subsistemas(df, perfil=excel)["Hora Crítica"].iat[0] == "12:00"
    assert a.preparar_resumo_subsistemas(df)["Curtailment (GWh)"].iat[0] == 0.11
    assert np.isclose((norte[TOTAL] * norte[CONTAGEM]).sum() * 0.5, 110)


def test_zero_sem_codigo_ausencia_e_empate():
    df = base([
        ("2026-10-01 08:00", "N", None, 10),
        ("2026-10-01 08:30", "N", "ENE", 5),
        ("2026-10-01 08:30", "N", "REL", 5),
        ("2026-10-01 09:00", "N", "CNF", 10),
        ("2026-10-01 10:00", "N", None, None),
        ("2026-10-01 11:00", "NE", "", 0),
    ])
    perfil = a.preparar_download_perfil_horario(df).set_index(["Subsistema", "Hora"])
    oito = perfil.loc[("N", "08:00")]
    assert oito[TOTAL] == 10
    assert oito[CONTAGEM] == 2
    assert oito["Curtailment sem classificação médio (MW)"] == 5
    assert oito["Curtailment ENE médio (MW)"] == oito["Curtailment REL médio (MW)"] == 2.5
    assert np.isnan(perfil.loc[("N", "10:00"), TOTAL])
    assert perfil.loc[("NE", "11:00"), TOTAL] == 0
    assert perfil.loc[("NE", "11:00"), CONTAGEM] == 1
    picos = a.preparar_resumo_subsistemas(df).set_index("Subsistema")["Hora Crítica"]
    assert picos["N"] == "08:00"
    assert picos["NE"] == "Não disponível"


def test_perfil_sem_medidas_validas():
    df = base([("2026-10-01 10:00", "N", "ENE", float("inf"))])
    perfil = a.preparar_download_perfil_horario(df)
    assert perfil[TOTAL].isna().all()
    assert perfil[CONTAGEM].eq(0).all()


@pytest.mark.skipif(not os.getenv("SINMULATOR_QA_CURTAILMENT"), reason="requer Parquets de 2025")
def test_regressao_norte_2025():
    dados = preparar_dados_subsistemas(2025, 1, 2025, 12, ("EOL", "UFV"))
    df = dados["df_curtailment"]
    perfil = a.preparar_download_perfil_horario(df)
    norte = perfil.set_index(["Subsistema", "Hora"]).loc["N"]
    assert norte.loc["22:00", CONTAGEM] == 730
    assert norte.loc["22:00", TOTAL] == pytest.approx(2.396393150684932)
    assert norte.loc["11:00", TOTAL] == pytest.approx(73.33201780821919)
    resumo = a.preparar_resumo_subsistemas(df, perfil=perfil).set_index("Subsistema")
    assert resumo.loc["N", "Hora Crítica"] == "11:00"
