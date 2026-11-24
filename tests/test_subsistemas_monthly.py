import os
from pathlib import Path

import pandas as pd
from unittest.mock import patch

from src import analise_subsistemas as a
from src.subsistemas_monthly import compactar_subsistemas


def confirmar_equivalencia(base, compacto):
    assert a.calcular_kpis_curtailment(base) == a.calcular_kpis_curtailment(compacto)
    pd.testing.assert_frame_equal(
        a.preparar_resumo_subsistemas(base), a.preparar_resumo_subsistemas(compacto),
        check_dtype=False, rtol=1e-9,
    )
    for f, args in [
        (a.preparar_download_curtailment_mensal, ()),
        (a.preparar_download_perfil_horario, ()),
        (a.preparar_corte_subsistema_tipo, ()),
        *((a.preparar_curtailment_mensal_subsistemas, (tipo,)) for tipo in ("TODOS","ENE","REL","CNF")),
        *((a.preparar_perfil_horario_curtailment, (tipo,)) for tipo in ("TODOS","ENE","REL","CNF")),
        *((a.preparar_exportacao_subsistemas, (g,)) for g in
          ("DIA_HORA","MES_HORA","ANO_HORA","DIA","MES","ANO")),
    ]:
        pd.testing.assert_frame_equal(
            f(base, *args), f(compacto, *args), check_dtype=False, rtol=1e-9,
            obj=f.__name__ + str(args),
        )


def test_ano_2025_com_dados_reais():
    raiz = os.environ.get("SINMULATOR_QA_CURTAILMENT")
    if not raiz:
        return
    from src import leitura_parquet
    from src.subsistemas_monthly import preparar_dados_subsistemas

    colunas = ["din_instante", "id_subsistema", "cod_razaorestricao",
               "val_curtailment", "val_geracao_esperada"]

    def carregar(ano_i, mes_i, ano_f, mes_f, fontes):
        assert (ano_i, mes_i) == (ano_f, mes_f)
        return pd.concat([pd.read_parquet(
            Path(raiz) / f / f"{ano_i}-{mes_i:02d}.parquet",
            columns=colunas,
        ) for f in fontes], ignore_index=True), {}

    fontes = ("EOL", "UFV")
    with patch.object(leitura_parquet, "DIRETORIO", Path(raiz)):
        resultado = preparar_dados_subsistemas(2025,1,2025,12,fontes)
    base = pd.concat([carregar(2025,m,2025,m,fontes)[0] for m in range(1,13)],
                     ignore_index=True)
    compacto = resultado["df_curtailment"]
    assert len(compacto) < len(base) / 10
    assert resultado["relatorios"]["resumo_pipeline"]["registros_curtailment"] == len(base)
    confirmar_equivalencia(base, compacto)
