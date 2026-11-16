from datetime import date
import json

import pandas as pd
import pytest

from scripts.atualizar_curtailment import (
    MesIndisponivel, executar, periodo, tratar, deslocar_mes,
)
from src.calculo_curtailment import COLUNAS_OBRIGATORIAS, calcular_curtailment


def dados(month=date(2026, 10, 1)):
    frame = pd.DataFrame({c: [None, None] for c in COLUNAS_OBRIGATORIAS})
    frame['id_ons'] = ['A', 'A']
    frame['din_instante'] = pd.to_datetime([f'{month:%Y-%m}-01 00:00', f'{month:%Y-%m}-01 00:30'])
    for c in ['val_geracao', 'val_geracaolimitada', 'val_disponibilidade', 'val_geracaoreferencia']:
        frame[c] = [10., 20.]
    frame['cod_razaorestricao'] = ['ENE', None]
    return frame


def loader(s, fonte, competencia):
    return dados(competencia), {'url': 'https://example.test', 'source_sha256': 'test'}


def test_calendar():
    assert deslocar_mes(date(2026, 1, 1), -1) == date(2025, 12, 1)
    assert len(periodo(date(2025, 12, 1), date(2026, 2, 1))) == 3
    with pytest.raises(ValueError):
        periodo(date(2026, 2, 1), date(2026, 1, 1))


def test_preserve_calculation():
    raw = dados()
    pd.testing.assert_frame_equal(tratar(raw, 'EOL', date(2026, 10, 1)), calcular_curtailment(raw, 'EOL'))


@pytest.mark.parametrize('error', ['empty', 'date', 'month', 'grid', 'numeric', 'id', 'schema', 'duplicate'])
def test_reject_bad_data(error):
    raw = dados()
    if error == 'empty': raw = raw.iloc[:0]
    if error == 'date': raw.loc[0, 'din_instante'] = pd.NaT
    if error == 'month': raw.loc[0, 'din_instante'] = pd.Timestamp('2026-09-01')
    if error == 'grid': raw.loc[0, 'din_instante'] = pd.Timestamp('2026-10-01 00:15')
    if error == 'numeric': raw['val_geracao'] = ['bad', '20']
    if error == 'id': raw.loc[0, 'id_ons'] = None
    if error == 'schema': raw = raw.drop(columns='val_disponibilidade')
    if error == 'duplicate': raw = pd.concat([raw, raw.iloc[:1]], ignore_index=True)
    with pytest.raises((ValueError, TypeError)):
        tratar(raw, 'EOL', date(2026, 10, 1))


def test_snapshot_roundtrip(tmp_path):
    manifest = executar(tmp_path, [date(2026, 10, 1)], ['EOL', 'UFV'], date(2026, 11, 12), loader)
    assert len(manifest['files']) == 2
    assert pd.read_parquet(tmp_path / 'EOL/2026-10.parquet').shape == (2, 19)
    assert json.loads((tmp_path / 'manifest.json').read_text())['schema_version'] == 1


def test_failed_batch_keeps_previous_snapshot(tmp_path):
    executar(tmp_path, [date(2026, 10, 1)], ['EOL', 'UFV'], date(2026, 11, 12), loader)
    before = {str(p): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    def failed(s, fonte, competencia):
        if fonte == 'UFV': raise RuntimeError('network unavailable')
        return loader(s, fonte, competencia)
    with pytest.raises(RuntimeError):
        executar(tmp_path, [date(2026, 10, 1)], ['EOL', 'UFV'], date(2026, 11, 12), failed)
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


def test_current_missing_is_explicit(tmp_path):
    def missing_current(s, fonte, competencia):
        if competencia.month == 11: raise MesIndisponivel('404')
        return loader(s, fonte, competencia)
    result = executar(tmp_path, [date(2026, 10, 1), date(2026, 11, 1)], ['EOL'], date(2026, 11, 12), missing_current)
    assert result['unavailable_current_month'] == ['EOL/2026-11.parquet']
    with pytest.raises(MesIndisponivel):
        executar(tmp_path, [date(2026, 11, 1)], ['EOL'], date(2026, 12, 1), missing_current)


def test_corrupt_previous_is_not_published(tmp_path):
    executar(tmp_path, [date(2026, 10, 1)], ['EOL'], date(2026, 11, 12), loader)
    (tmp_path / 'EOL/2026-10.parquet').write_bytes(b'bad')
    with pytest.raises(ValueError, match='corrompido'):
        executar(tmp_path, [date(2026, 11, 1)], ['EOL'], date(2026, 11, 12), loader)


def test_initial_failure_publishes_nothing(tmp_path):
    def failed(s, fonte, competencia):
        if fonte == 'UFV': raise MesIndisponivel('404')
        return loader(s, fonte, competencia)
    with pytest.raises(MesIndisponivel):
        executar(tmp_path, [date(2026, 10, 1)], ['EOL', 'UFV'], date(2026, 11, 12), failed)
    assert not list(tmp_path.rglob('*'))


def test_existing_current_cannot_disappear(tmp_path):
    executar(tmp_path, [date(2026, 11, 1)], ['EOL'], date(2026, 11, 12), loader)
    def missing(s, fonte, competencia):
        raise MesIndisponivel('404')
    with pytest.raises(MesIndisponivel):
        executar(tmp_path, [date(2026, 11, 1)], ['EOL'], date(2026, 11, 12), missing)


def test_decimal_comma_and_nulls_preserved():
    raw = dados()
    raw['val_geracao'] = ['10,5', None]
    result = tratar(raw, 'UFV', date(2026, 10, 1))
    assert result.loc[0, 'val_geracao'] == 10.5
    assert pd.isna(result.loc[1, 'val_geracao'])


def test_single_source_keeps_other_source(tmp_path):
    executar(tmp_path, [date(2026, 10, 1)], ['EOL', 'UFV'], date(2026, 11, 12), loader)
    solar_before = (tmp_path / 'UFV/2026-10.parquet').read_bytes()
    result = executar(tmp_path, [date(2026, 11, 1)], ['EOL'], date(2026, 11, 12), loader)
    assert 'UFV/2026-10.parquet' in result['files']
    assert 'EOL/2026-11.parquet' in result['files']
    assert (tmp_path / 'UFV/2026-10.parquet').read_bytes() == solar_before


@pytest.mark.parametrize('year', [2023, 2027])
def test_reject_outside_fixed_scope(tmp_path, year):
    with pytest.raises(ValueError, match='Escopo permitido'):
        executar(tmp_path, [date(year, 1, 1)], ['EOL'], date(2028, 1, 1), loader)
    assert not list(tmp_path.iterdir())


def test_recent_scope_never_expands_to_2027():
    from scripts.atualizar_curtailment import meses_recentes
    assert meses_recentes(date(2026, 11, 12), 3, True) == [date(2026,m,1) for m in [8,9,10,11]]
    assert meses_recentes(date(2026, 12, 12), 3, True) == [date(2026,m,1) for m in [9,10,11,12]]
    for future in [date(2027,1,12),date(2027,7,1),date(2028,1,1)]:
        assert meses_recentes(future, 3, True) == [date(2026,m,1) for m in [10,11,12]]
    assert meses_recentes(date(2024, 1, 12), 3, True) == [date(2024,1,1)]


def test_reject_future_within_scope(tmp_path):
    with pytest.raises(ValueError, match='futuros'):
        executar(tmp_path, [date(2026, 12, 1)], ['EOL'], date(2026,11,12), loader)


def test_old_out_of_scope_snapshot_not_silently_kept(tmp_path):
    (tmp_path/'manifest.json').write_text(json.dumps({'schema_version':1,'files':{'EOL/2023-01.parquet':{'competencia':'2023-01'}}}))
    with pytest.raises(ValueError, match='fora do escopo'):
        executar(tmp_path, [date(2026,10,1)], ['EOL'], date(2026,11,12), loader)
