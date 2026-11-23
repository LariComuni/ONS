from datetime import date
import json
from pathlib import Path
from io import BytesIO
import pandas as pd
import pytest
from scripts.atualizar_evt import executar, tratar, recentes, MesIndisponivel
from src.coleta_evt import tratar_base_evt, otimizar_tipos_evt, montar_url_evt


def raw(month='2026-10'):
    return pd.DataFrame({'din_instante':[f'{month}-01 00:00:00',f'{month}-01 01:00:00'],
      'id_subsistema':['NE','NE'],'nom_subsistema':['NORDESTE','NORDESTE'],
      'nom_reservatorio':['A','A'],'cod_usina':[1,1], 'val_geracao':[10.,-2.],
      'val_energiavertidaturbinavel':[3.,-1.]})


def payload(frame):
    return frame.to_csv(sep=';',index=False).encode()


def loader(session, month):
    return payload(raw(f'{month:%Y-%m}')), {'source_url':montar_url_evt(month.year,month.month),'last_modified':'test'}


def test_same_original_monthly_method():
    data=raw(); body=payload(data); expected=tratar_base_evt(pd.read_csv(BytesIO(body),sep=';'))
    for col,value in {'fonte':'EVT','ano_referencia':2026,'mes_referencia':10,'competencia':'2026-10',
        'arquivo_origem':'ENERGIA_VERTIDA_TURBINAVEL_2026_10.csv','granularidade_origem':'1h'}.items():
        expected[col]=value
    expected=otimizar_tipos_evt(expected)
    result,quality=tratar(body,date(2026,10,1))
    pd.testing.assert_frame_equal(result,expected)
    assert result.val_geracao.tolist()==[10.,0.]
    assert quality['dropped_rows_by_original_treatment']==0


def test_dropped_original_rows_reported_not_zero_filled():
    frame=raw();frame.loc[0,'val_energiavertidaturbinavel']=None
    result,q=tratar(payload(frame),date(2026,10,1))
    assert len(result)==1 and q['dropped_rows_by_original_treatment']==1


@pytest.mark.parametrize('problem',['empty','schema','grid','month','subsystem','infinity'])
def test_invalid_source(problem):
    frame=raw()
    if problem=='empty':frame=frame.iloc[:0]
    if problem=='schema':frame=frame.drop(columns='val_geracao')
    if problem=='grid':frame.loc[0,'din_instante']='2026-10-01 00:30:00'
    if problem=='month':frame.loc[0,'din_instante']='2026-09-01 00:00:00'
    if problem=='subsystem':frame.loc[0,'id_subsistema']=None
    if problem=='infinity':frame.loc[0,'val_geracao']=float('inf')
    with pytest.raises(ValueError):tratar(payload(frame),date(2026,10,1))


def test_roundtrip_and_no_churn(tmp_path):
    m=executar(tmp_path,[date(2026,10,1)],date(2026,11,19),loader)
    assert m['files']['2026-10']['rows']==2
    before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    again=executar(tmp_path,[date(2026,10,1)],date(2026,11,20),loader)
    assert m==again
    assert before=={p.name:p.read_bytes() for p in tmp_path.iterdir()}


def test_fail_batch_keeps_snapshot(tmp_path):
    executar(tmp_path,[date(2026,9,1)],date(2026,11,19),loader)
    before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    def fail(s,m):
        if m.month==11:raise RuntimeError('network failure')
        return loader(s,m)
    with pytest.raises(RuntimeError):executar(tmp_path,[date(2026,10,1),date(2026,11,1)],date(2026,11,19),fail)
    assert before=={p.name:p.read_bytes() for p in tmp_path.iterdir()}


def test_current_404_explicit_only(tmp_path):
    def missing(s,m):raise MesIndisponivel('404')
    m=executar(tmp_path,[date(2026,11,1)],date(2026,11,19),missing)
    assert m['files']=={} and m['unavailable_current_month']==['2026-11']
    assert not list(tmp_path.glob('*.parquet'))
    with pytest.raises(MesIndisponivel):executar(tmp_path,[date(2026,10,1)],date(2026,11,19),missing)


def test_published_current_cannot_disappear(tmp_path):
    executar(tmp_path,[date(2026,11,1)],date(2026,11,19),loader)
    def missing(s,m):raise MesIndisponivel('404')
    with pytest.raises(MesIndisponivel):executar(tmp_path,[date(2026,11,1)],date(2026,11,19),missing)


@pytest.mark.parametrize('month',[date(2023,1,1),date(2027,1,1),date(2026,12,1)])
def test_scope(tmp_path,month):
    with pytest.raises(ValueError):executar(tmp_path,[month],date(2026,11,19),loader)


def test_schedule_scope():
    assert recentes(date(2027,5,1))==[date(2026,m,1) for m in [10,11,12]]
    assert recentes(date(2026,11,19))==[date(2026,m,1) for m in [8,9,10,11]]


def test_integrity_of_previous(tmp_path):
    executar(tmp_path,[date(2026,10,1)],date(2026,11,19),loader)
    (tmp_path/'2026-10.parquet').write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='corrompido'):executar(tmp_path,[date(2026,11,1)],date(2026,11,19),loader)


def test_exact_duplicates_only_removed():
    frame=raw()
    # Uma linha repetida integralmente; outra linha na mesma hora mas com valor distinto.
    frame=pd.concat([frame,frame.iloc[:1],frame.iloc[:1]],ignore_index=True)
    frame.loc[3,'val_geracao']=99.
    result,q=tratar(payload(frame),date(2026,10,1))
    assert len(result)==3
    assert q['exact_duplicate_rows_removed']==1
    assert q['dropped_rows_by_original_treatment']==0
    assert len(result[result.din_instante==pd.Timestamp('2026-10-01')])==2


def test_string_categories_roundtrip(tmp_path):
    def category_loader(s,m):
        frame=pd.concat([raw(f'{m:%Y-%m}')]*5,ignore_index=True)
        frame['din_instante']=pd.date_range(f'{m:%Y-%m}-01',periods=10,freq='h')
        return payload(frame),{'source_url':montar_url_evt(m.year,m.month)}
    m=executar(tmp_path,[date(2026,10,1)],date(2026,11,19),category_loader)
    assert m['files']['2026-10']['rows']==10
    assert str(pd.read_parquet(tmp_path/'2026-10.parquet').id_subsistema.dtype)=='category'
