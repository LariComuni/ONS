"""EVT local publicada pelo workflow; nunca consulta a rede nem supõe ausência zero."""
from pathlib import Path
import hashlib
import json
import pandas as pd
from .coleta_evt import COLUNAS_OBRIGATORIAS_EVT, COLUNAS_NUMERICAS_EVT, otimizar_tipos_evt
from .periodo_evt_cp45 import DadosEVTIndisponiveis

DIRETORIO = Path(__file__).resolve().parents[1] / "data" / "evt"


def _manifesto(raiz):
    try:
        manifest = json.loads((raiz / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DadosEVTIndisponiveis(
            "Histórico EVT local indisponível. Execute primeiro a coleta EVT no GitHub Actions. "
            "A CP45 não faz download automático nem considera ausência como zero."
        ) from exc
    if (not isinstance(manifest, dict)
            or manifest.get("schema_version") != 1
            or manifest.get("dataset") != "EVT"
            or not isinstance(manifest.get("files"), dict)):
        raise DadosEVTIndisponiveis("Manifesto EVT incompatível. Reexecute a coleta EVT.")
    return manifest


def identidade_snapshot_evt(diretorio=None):
    raiz = Path(diretorio) if diretorio is not None else DIRETORIO
    _manifesto(raiz)
    h = hashlib.sha256((raiz / "manifest.json").read_bytes())
    for path in sorted(raiz.glob("*.parquet")):
        stat = path.stat()
        h.update(f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}".encode())
    return h.hexdigest()


def carregar_periodo_evt_parquet(ano, mes_inicial=1, mes_final=12, diretorio=None):
    if ano not in (2024, 2025, 2026) or not 1 <= mes_inicial <= mes_final <= 12:
        raise ValueError("Período EVT inválido: use meses entre 2024 e 2026.")
    raiz = Path(diretorio) if diretorio is not None else DIRETORIO
    manifest = _manifesto(raiz)
    frames, arquivos = [], []
    for mes in range(mes_inicial, mes_final + 1):
        competencia = f"{ano:04d}-{mes:02d}"
        nome = f"{competencia}.parquet"
        meta = manifest.get("files", {}).get(competencia)
        path = raiz / nome
        if meta is None or not path.is_file():
            raise DadosEVTIndisponiveis(
                f"Base EVT de {mes:02d}/{ano} ainda não publicada localmente. "
                "Execute a coleta desse período no GitHub Actions; ausência não significa EVT zero."
            )
        if not isinstance(meta, dict):
            raise DadosEVTIndisponiveis(f"Entrada inválida no manifesto EVT: {competencia}.")
        try:
            if meta.get("path") != nome or meta.get("competencia") != competencia:
                raise ValueError("competência/caminho divergente")
            if path.stat().st_size != meta["bytes"]:
                raise ValueError("tamanho divergente")
            if hashlib.sha256(path.read_bytes()).hexdigest() != meta["sha256"]:
                raise ValueError("checksum divergente")
            df = pd.read_parquet(path, engine="pyarrow")
            if COLUNAS_OBRIGATORIAS_EVT - set(df.columns):
                raise ValueError("colunas obrigatórias ausentes")
            if df.empty or len(df) != meta["rows"]:
                raise ValueError("quantidade de registros divergente")
            df["din_instante"] = pd.to_datetime(df["din_instante"], errors="raise")
            if (df["din_instante"].isna().any()
                    or not df["din_instante"].dt.strftime("%Y-%m").eq(competencia).all()):
                raise ValueError("datas fora da competência")
            for col in COLUNAS_NUMERICAS_EVT:
                if col in df and not pd.api.types.is_numeric_dtype(df[col]):
                    raise ValueError(f"tipo não numérico em {col}")
        except (ValueError, TypeError, KeyError, OSError) as exc:
            raise DadosEVTIndisponiveis(
                f"Parquet EVT inconsistente ({competencia}): {exc}. Reexecute a coleta EVT."
            ) from exc
        frames.append(df)
        arquivos.append(nome)
    df = pd.concat(frames, ignore_index=True).drop_duplicates(ignore_index=True)
    df = otimizar_tipos_evt(df)
    return df, {"fonte": "EVT", "origem": "parquet_local", "ano": ano,
                "mes_inicial": mes_inicial, "mes_final": mes_final,
                "meses_carregados": list(range(mes_inicial, mes_final + 1)),
                "meses_ausentes": [], "arquivos": arquivos,
                "quantidade_linhas": len(df), "atualizado_em": manifest.get("updated_at")}
