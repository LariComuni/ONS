import numpy as np
import pandas as pd
from src.pipeline_mapa_eficiente import reduzir_mes_mapa, combinar_estatisticas_mapa, finalizar_perfis_mapa
from src.enriquecimento_geografico import reduzir_fator_capacidade, enriquecer_curtailment
from src.series_mapa import preparar_base_series_mapa, calcular_perfil_horario_usinas, calcular_decomposicao_curtailment, calcular_perfil_horario_pontos


def fixture():
    # Unequal month lengths, absent hours, missing generation, mixed reasons,
    # simultaneous plants at a common point, and a plant without mapping.
    rng = np.random.default_rng(29)
    frames = []
    for i, n in enumerate([31*48, 28*48, 31*48]):
        t = pd.date_range(f'2025-{i+1:02d}-01', periods=n, freq='30min')
        for name in ['A', 'B', 'unmapped']:
            f = pd.DataFrame({'nom_usina': name, 'din_instante': t,
                              'cod_razaorestricao': rng.choice(['ENE','REL','CNF', None, ''],n),
                              'val_geracao': rng.random(n)*100,
                              'val_curtailment': rng.random(n)*20})
            f['val_geracao_esperada'] = f.val_geracao + f.val_curtailment
            f.loc[f.index % 19 == 0, 'val_geracao'] = np.nan
            f.loc[f.index % 23 == 0, 'val_curtailment'] = np.nan
            if name == 'B': f = f[f.din_instante.dt.hour != 2]
            frames.append(f)
    cadastro = reduzir_fator_capacidade(pd.DataFrame({
        'nom_usina_conjunto':['A','B'], 'cod_pontoconexao':['P1','P1'],
        'nom_pontoconexao':['Point','Point'],
        'val_latitudepontoconexao':[-10.,-10.], 'val_longitudepontoconexao':[-40.,-40.]}))
    return frames, cadastro


def test_incremental_profiles_match_legacy_with_missingness_and_unequal_months():
    frames, cadastro = fixture()
    df, _ = enriquecer_curtailment(pd.concat(frames), cadastro)
    series, _ = preparar_base_series_mapa(df)
    h0, u0, _ = calcular_perfil_horario_usinas(series)
    _, uc0, pc0, _ = calcular_decomposicao_curtailment(series, h0)
    _, p0, _ = calcular_perfil_horario_pontos(h0)
    stats = None
    for f in frames: stats = combinar_estatisticas_mapa(stats, reduzir_mes_mapa(f))
    _, h, u, uc, p, pc = finalizar_perfis_mapa(stats, cadastro)
    pd.testing.assert_frame_equal(h, h0, check_dtype=False, atol=1e-10)
    assert u == u0
    assert uc == uc0
    assert p == p0
    assert pc == pc0
    assert len(stats) <= 3*24*4


def test_partition_order_does_not_change_means():
    frames, cadastro = fixture()
    a = None
    b = None
    for f in frames: a = combinar_estatisticas_mapa(a,reduzir_mes_mapa(f))
    for f in reversed(frames): b = combinar_estatisticas_mapa(b,reduzir_mes_mapa(f))
    oa = finalizar_perfis_mapa(a,cadastro)
    ob = finalizar_perfis_mapa(b,cadastro)
    assert oa[2:] == ob[2:]
