"""Leitura local dos snapshots publicados pela coleta semanal, sem rede."""
from pathlib import Path
import hashlib
import json
import pandas as pd
from .calculo_curtailment import COLUNAS_RESULTADO

DIRETORIO = Path(__file__).resolve().parents[1] / "data" / "curtailment"

INICIO_COBERTURA_UFV = (2024, 4)


def identidade_snapshot(diretorio=None):
    """Hash do manifesto e estado dos arquivos para invalidar caches."""
    raiz = Path(diretorio) if diretorio is not None else DIRETORIO
    manifesto = raiz / "manifest.json"
    if not manifesto.is_file():
        raise FileNotFoundError("Manifesto de curtailment ausente. Execute a coleta no GitHub Actions.")
    h = hashlib.sha256(manifesto.read_bytes())
    for arquivo in sorted(raiz.glob("*/*.parquet")):
        s = arquivo.stat()
        h.update(f"{arquivo.relative_to(raiz)}:{s.st_size}:{s.st_mtime_ns}".encode())
    return h.hexdigest()

def carregar_periodo_parquet(fonte, ano, mes_inicial, mes_final, diretorio=None):
    if fonte not in ("EOL", "UFV") or ano not in (2024, 2025, 2026):
        raise ValueError("Fonte/ano inválido: use EOL ou UFV, entre 2024 e 2026.")
    if not 1 <= mes_inicial <= mes_final <= 12:
        raise ValueError("Período mensal inválido.")
    raiz = Path(diretorio) if diretorio is not None else DIRETORIO
    with (raiz / "manifest.json").open(encoding="utf-8") as f:
        manifesto = json.load(f)
    if manifesto.get("schema_version") != 1:
        raise ValueError("Versão do manifesto não suportada.")
    frames, ignorados, arquivos = [], [], []
    for mes in range(mes_inicial, mes_final + 1):
        competencia = f"{ano:04d}-{mes:02d}"
        if fonte == "UFV" and (ano, mes) < INICIO_COBERTURA_UFV:
            ignorados.append(competencia)
            continue
        chave = f"{fonte}/{competencia}.parquet"
        caminho = raiz / chave
        meta = manifesto.get("files", {}).get(chave)
        if meta is None or not caminho.is_file():
            raise FileNotFoundError(
                f"Base {fonte} de {competencia} ainda não publicada. "
                "Execute a coleta desse período no GitHub Actions; ausência não significa zero."
            )
        if caminho.stat().st_size != meta["bytes"]:
            raise ValueError(f"Tamanho divergente do manifesto: {chave}")
        df = pd.read_parquet(caminho, engine="pyarrow")
        if set(COLUNAS_RESULTADO) - set(df.columns):
            raise ValueError(f"Colunas obrigatórias ausentes: {chave}")
        df = df[COLUNAS_RESULTADO].copy()
        for coluna in (c for c in COLUNAS_RESULTADO if c.startswith("val_")):
            if not pd.api.types.is_numeric_dtype(df[coluna]):
                raise ValueError(f"Tipo não numérico em {coluna}: {chave}")
        df["din_instante"] = pd.to_datetime(df["din_instante"], errors="raise")
        if (df.empty or len(df) != meta["rows"]
                or df["din_instante"].isna().any()
                or not df["din_instante"].dt.strftime("%Y-%m").eq(competencia).all()
                or not df["fonte"].eq(fonte).all()
                or df[["id_ons", "din_instante"]].duplicated().any()):
            raise ValueError(f"Conteúdo inconsistente: {chave}")
        frames.append(df)
        arquivos.append(chave)
    dados = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUNAS_RESULTADO)
    return dados, {"origem": "parquet_local", "arquivos": arquivos,
                   "meses_sem_cobertura_historica": ignorados,
                   "atualizado_em": manifesto.get("updated_at")}
