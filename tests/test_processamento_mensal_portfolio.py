"""Preserve the calculations while bounding the work done per competence."""
import pandas as pd
import pytest

from src.analise_ativos_elera import ATIVOS_ELERA
from src.analise_cp45 import preparar_analise_fonte_cp45
from src.cenarios_cp45 import montar_base_cenarios_cp45
from src.preparacao_cp45 import montar_base_fontes_cp45, preparar_ativos_horarios_cp45
from src.processamento_mensal_portfolio import (
    COLUNAS_CP45_INTERFACE, carregar_portfolio_mensal, preparar_cp45_mensal,
)

PORTFOLIO_NAME = next(iter(ATIVOS_ELERA))


def curtailment(fonte, ano, inicio, fim):
    assert inicio == fim
    frame = pd.DataFrame({
        "din_instante": pd.to_datetime([f"{ano}-{inicio:02d}-01 00:00", f"{ano}-{inicio:02d}-01 00:30"]),
        "nom_usina": [PORTFOLIO_NAME if fonte == "EOL" else "Solar", "Outro"],
        "id_subsistema": ["NE", "SE"],
        "fonte": [fonte] * 2,
        "cod_razaorestricao": ["ENE", "CNF"],
        "val_curtailment": [12., 6.],
        "val_geracao_esperada": [30., 16.],
        "extra_export": ["preserve", "ignore"],
    })
    return (frame.iloc[:0] if fonte == "UFV" and (ano, inicio) < (2024, 4) else frame), {}


def evt(ano, mes_inicial, mes_final):
    assert mes_inicial == mes_final
    frame = pd.DataFrame({
        "din_instante": [pd.Timestamp(ano, mes_inicial, 1)] * 2, "id_subsistema": ["NE", "SE"],
        "val_geracao": [30., 20.], "val_energiavertidaturbinavel": [4., 0.],
    })
    return frame, {"meses_carregados": [mes_inicial], "meses_ausentes": []}


def pld(periodos):
    return pd.DataFrame({"DIN_INSTANTE": [pd.Timestamp(y,m,1) for y,m in periodos],
                         "DESCOLAMENTO_HORARIO": [True] * len(periodos),
                         "AMPLITUDE_DESCOLAMENTO": [5.] * len(periodos)})


@pytest.mark.parametrize("periodos", [[(2024,3),(2024,4)], [(2024,12),(2025,1)]])
def test_cp45_mensal_preserva_resultado_e_cobertura_mista(periodos):
    chamadas = []
    def loader(fonte, ano, inicio, fim):
        chamadas.append((fonte, ano, inicio, fim))
        return curtailment(fonte, ano, inicio, fim)
    df_pld = pld(periodos)
    periodo = (*periodos[0], *periodos[-1])
    novo = preparar_cp45_mensal(*periodo, df_pld, ler_curtailment=loader, ler_evt=evt)
    assert chamadas == [(f,a,m,m) for a,m in periodos for f in ("EOL","UFV")]
    cur = pd.concat([curtailment(f,a,m,m)[0] for f in ("EOL","UFV") for a,m in periodos], ignore_index=True)
    hid = pd.concat([evt(a,m,m)[0] for a,m in periodos], ignore_index=True)
    antigo = montar_base_cenarios_cp45(montar_base_fontes_cp45(cur,hid,df_pld),
                                       preparar_ativos_horarios_cp45(cur))["ativos"]
    ref = antigo[COLUNAS_CP45_INTERFACE].copy()
    ref.attrs.clear()
    pd.testing.assert_frame_equal(novo.astype(ref.dtypes), ref, check_exact=True)
    for fonte in ("EOL","UFV"):
        antigo_ui, novo_ui = (preparar_analise_fonte_cp45(x, *periodo, fonte) for x in (antigo,novo))
        assert antigo_ui["indicadores"] == novo_ui["indicadores"]
        for key in ("resumo_mensal","resumo_cenarios"):
            pd.testing.assert_frame_equal(antigo_ui[key], novo_ui[key], check_exact=True)


def test_cp45_so_antes_cobertura_mantem_erro():
    with pytest.raises(ValueError, match="fonte UFV"):
        preparar_cp45_mensal(2024,1,2024,3,pld([(2024,1),(2024,2),(2024,3)]),
                              ler_curtailment=curtailment, ler_evt=evt)


def test_portfolio_preserva_grao_e_colunas_para_exportacao():
    result = carregar_portfolio_mensal(2024,12,2025,1,("EOL","UFV"),ler_curtailment=curtailment)
    assert result["nom_usina"].tolist() == [PORTFOLIO_NAME] * 2
    assert result["extra_export"].tolist() == ["preserve"] * 2
    assert result["din_instante"].dt.month.tolist() == [12,1]
