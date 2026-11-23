"""Coletor mensal EVT independente, com tratamento original do SINmulator."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.coleta_evt import montar_url_evt, tratar_base_evt, otimizar_tipos_evt


class MesIndisponivel(RuntimeError):
    pass


def mes(value):
    try:
        result = datetime.strptime(value, '%Y-%m').date()
        if result.strftime('%Y-%m') != value:
            raise ValueError()
        return result
    except ValueError as exc:
        raise argparse.ArgumentTypeError('Use YYYY-MM') from exc


def deslocar(value, delta):
    n = value.year * 12 + value.month - 1 + delta
    return date(n // 12, n % 12 + 1, 1)


def periodo(inicio, fim):
    if inicio > fim:
        raise ValueError('Início posterior ao fim')
    values = []
    while inicio <= fim:
        values.append(inicio)
        inicio = deslocar(inicio, 1)
    return values


def recentes(hoje, fechados=3, incluir_atual=True):
    if fechados < 1:
        raise ValueError('Quantidade de meses fechados deve ser positiva')
    atual = hoje.replace(day=1)
    ultimo = min(deslocar(atual, -1), date(2026, 12, 1))
    inicio = max(deslocar(ultimo, 1-fechados), date(2024, 1, 1))
    values = periodo(inicio, ultimo) if inicio <= ultimo else []
    if incluir_atual and date(2024, 1, 1) <= atual <= date(2026, 12, 1):
        values.append(atual)
    return values


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def baixar(session, competencia):
    url = montar_url_evt(competencia.year, competencia.month)
    response = session.get(url, timeout=(15, 180))
    if response.status_code == 404:
        raise MesIndisponivel(f'EVT {competencia:%Y-%m}: HTTP 404 ({url})')
    response.raise_for_status()
    return response.content, {'source_url': url, 'last_modified': response.headers.get('Last-Modified')}


def tratar(payload, competencia):
    # Mesma leitura CSV e mesmas funções de carregar_mes_evt.
    raw = pd.read_csv(BytesIO(payload), sep=';', encoding='utf-8', decimal='.', low_memory=False)
    frame = tratar_base_evt(raw)
    dt = frame['din_instante']
    if not ((dt.dt.year == competencia.year) & (dt.dt.month == competencia.month)).all():
        raise ValueError('EVT contém registros fora da competência')
    if not ((dt.dt.minute == 0) & (dt.dt.second == 0) & (dt.dt.microsecond == 0)).all():
        raise ValueError('EVT contém instantes fora da grade horária')
    if frame['id_subsistema'].isna().any() or frame['id_subsistema'].eq('').any():
        raise ValueError('EVT contém subsistema ausente')
    for col in ['val_geracao', 'val_energiavertidaturbinavel']:
        if not np.isfinite(frame[col]).all():
            raise ValueError(f'EVT contém valor não finito em {col}')
    frame['fonte'] = 'EVT'
    frame['ano_referencia'] = competencia.year
    frame['mes_referencia'] = competencia.month
    frame['competencia'] = f'{competencia:%Y-%m}'
    frame['arquivo_origem'] = montar_url_evt(competencia.year, competencia.month).rsplit('/', 1)[-1]
    frame['granularidade_origem'] = '1h'
    treated_rows = len(frame)
    frame = otimizar_tipos_evt(frame)
    # Mesma remoção de duplicatas completas do carregar_periodo_evt.
    # Metadados de competência impedem duplicatas completas entre meses distintos.
    before_dedup = len(frame)
    frame = frame.drop_duplicates(ignore_index=True)
    frame = otimizar_tipos_evt(frame)
    return frame, {'raw_rows': len(raw),
        'dropped_rows_by_original_treatment': len(raw)-treated_rows,
        'exact_duplicate_rows_removed': before_dedup-len(frame)}


def executar(output, meses, hoje, loader=baixar):
    atual = hoje.replace(day=1)
    if not meses or any(m.year not in [2024, 2025, 2026] or m.day != 1 for m in meses):
        raise ValueError('Escopo EVT permitido: 2024, 2025 e 2026')
    if any(m > atual for m in meses):
        raise ValueError('Competência futura não permitida')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output/'manifest.json'
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    if old and (old.get('schema_version') != 1 or old.get('dataset') != 'EVT'):
        raise ValueError('Manifesto incompatível com EVT')
    entries = dict(old.get('files', {}))
    for key, entry in entries.items():
        if mes(key).year not in [2024, 2025, 2026] or entry['path'] != f'{key}.parquet':
            raise ValueError('Entrada de manifesto fora do contrato EVT')
        path = output/entry['path']
        if not path.is_file() or sha(path) != entry['sha256']:
            raise ValueError(f'Snapshot anterior ausente/corrompido: {key}')
    method = sha(ROOT/'src/coleta_evt.py')
    collector = sha(Path(__file__))
    missing = []
    with tempfile.TemporaryDirectory(prefix='evt-stage-') as tempdir, requests.Session() as session:
        session.headers.update({'User-Agent': 'Mozilla/5.0 SINmulator/1.0', 'Accept': 'text/csv,application/octet-stream;q=0.9,*/*;q=0.8'})
        session.mount('https://', HTTPAdapter(max_retries=Retry(total=3, backoff_factor=2, status_forcelist=[429,500,502,503,504], allowed_methods=['GET'])))
        stage = Path(tempdir)
        for competencia in meses:
            key = f'{competencia:%Y-%m}'
            print(f'EVT {key}', flush=True)
            try:
                payload, source = loader(session, competencia)
            except MesIndisponivel:
                if competencia == atual and key not in entries and not (output/f'{key}.parquet').exists():
                    missing.append(key)
                    print(f'EVT {key} ainda não publicada; ausência registrada', flush=True)
                    continue
                raise
            source_hash = hashlib.sha256(payload).hexdigest()
            previous = entries.get(key, {})
            if (previous.get('source_sha256') == source_hash and previous.get('treatment_sha256') == method
                    and previous.get('collector_sha256') == collector
                    and previous.get('month_in_progress') == (competencia == atual)):
                print('Fonte e tratamento sem alteração; mantendo arquivo e metadados', flush=True)
                continue
            frame, quality = tratar(payload, competencia)
            dest = stage/f'{key}.parquet'
            frame.to_parquet(dest, engine='pyarrow', compression='zstd', index=False)
            restored = pd.read_parquet(dest)
            expected = frame.copy()
            # Arrow preserva categorias/valores mas pode mudar string->object
            # no índice interno de categorias. Normaliza somente para comparação.
            for col in expected.select_dtypes(include=['category']).columns:
                expected[col] = expected[col].cat.rename_categories(expected[col].cat.categories.astype(object))
                restored[col] = restored[col].cat.rename_categories(restored[col].cat.categories.astype(object))
            pd.testing.assert_frame_equal(expected, restored)
            del expected
            if dest.stat().st_size >= 95*1024**2:
                raise ValueError('Parquet EVT excede limite preventivo de 95 MiB')
            entries[key] = {**source, **quality, 'path': dest.name, 'competencia': key,
                'rows': len(frame), 'bytes': dest.stat().st_size, 'sha256': sha(dest),
                'source_bytes': len(payload), 'source_sha256': source_hash,
                'treatment_sha256': method, 'collector_sha256': collector,
                'min_timestamp': frame.din_instante.min().isoformat(), 'max_timestamp': frame.din_instante.max().isoformat(),
                'month_in_progress': competencia == atual,
                'columns': list(frame.columns), 'dtypes': {c:str(t) for c,t in frame.dtypes.items()},
                'null_counts': {c:int(n) for c,n in frame.isna().sum().items()},
                'exact_duplicate_rows': int(frame.duplicated().sum()),
                'generated_at': datetime.now(timezone.utc).isoformat()}
        # Ausência do corrente pode gerar manifesto vazio explícito; não produz Parquet fictício.
        manifest = {'schema_version':1, 'dataset':'EVT', 'allowed_years':[2024,2025,2026],
            'interval_minutes':60, 'files': entries, 'unavailable_current_month':missing,
            'note':'Tratamento original preservado; ausência não é zero. Cobertura estrutural não certifica completude por usina.'}
        old_comparable = {k:v for k,v in old.items() if k != 'updated_at'}
        if manifest == old_comparable:
            print('Snapshot sem alterações; nenhum arquivo regravado', flush=True)
            return old
        manifest['updated_at'] = datetime.now(timezone.utc).isoformat()
        # Só promove após validar todo o lote. Publicação remota conjunta é o commit Git.
        for candidate in stage.glob('*.parquet'):
            dest = output/candidate.name
            with tempfile.NamedTemporaryFile(dir=output, delete=False) as temp:
                temp.write(candidate.read_bytes()); tmp = Path(temp.name)
            os.replace(tmp, dest)
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=output,delete=False) as temp:
            json.dump(manifest,temp,ensure_ascii=False,indent=2); temp.write('\n'); tmp=Path(temp.name)
        os.replace(tmp, manifest_path)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inicio', type=mes)
    parser.add_argument('--fim', type=mes)
    parser.add_argument('--meses-fechados', type=int, default=3)
    parser.add_argument('--incluir-atual', action='store_true')
    parser.add_argument('--output',type=Path,default=ROOT/'data/evt')
    args=parser.parse_args()
    if bool(args.inicio) != bool(args.fim):
        parser.error('Informe início e fim juntos')
    hoje=datetime.now(timezone.utc).date()
    meses=periodo(args.inicio,args.fim) if args.inicio else recentes(hoje,args.meses_fechados,args.incluir_atual)
    executar(args.output,meses,hoje)


if __name__ == '__main__':
    main()
