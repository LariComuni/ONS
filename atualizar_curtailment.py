"""Snapshot mensal EOL/UFV. Não modifica as fórmulas nem a interface do app."""
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

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ANO_INICIAL = 2024
ANO_FINAL = 2026
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.coleta_ons import montar_url_ons
from src.calculo_curtailment import (
    COLUNAS_NUMERICAS, COLUNAS_RESULTADO, calcular_curtailment, validar_colunas,
)


class MesIndisponivel(RuntimeError):
    pass


def mes(value: str) -> date:
    try:
        result = datetime.strptime(value, "%Y-%m").date()
        if result.strftime("%Y-%m") != value:
            raise ValueError()
        return result
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use YYYY-MM, por exemplo 2026-10") from exc


def deslocar_mes(value: date, delta: int) -> date:
    n = value.year * 12 + value.month - 1 + delta
    return date(n // 12, n % 12 + 1, 1)


def periodo(inicio: date, fim: date) -> list[date]:
    if inicio > fim:
        raise ValueError("O mês inicial deve ser menor ou igual ao final")
    out = []
    while inicio <= fim:
        out.append(inicio)
        inicio = deslocar_mes(inicio, 1)
    return out


def meses_recentes(hoje: date, fechados: int, incluir_atual: bool) -> list[date]:
    """Atualiza somente competências dentro do escopo fixo 2024–2026."""
    if fechados < 1:
        raise ValueError("Quantidade de meses fechados deve ser positiva")
    atual = hoje.replace(day=1)
    limite_inicial = date(ANO_INICIAL, 1, 1)
    limite_final = date(ANO_FINAL, 12, 1)
    ultimo_fechado = min(deslocar_mes(atual, -1), limite_final)
    if ultimo_fechado < limite_inicial:
        selecionados = []
    else:
        selecionados = periodo(max(deslocar_mes(ultimo_fechado, 1 - fechados), limite_inicial), ultimo_fechado)
    if incluir_atual and limite_inicial <= atual <= limite_final:
        selecionados.append(atual)
    if not selecionados:
        raise ValueError("Nenhuma competência disponível no escopo 2024–2026")
    return selecionados


def sessao() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET"])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers["User-Agent"] = "SINmulator-coletor/1.0"
    return s


def baixar(s: requests.Session, fonte: str, competencia: date):
    url = montar_url_ons(fonte, competencia.year, competencia.month)
    response = s.get(url, timeout=(15, 180))
    if response.status_code == 404:
        raise MesIndisponivel(url)
    response.raise_for_status()
    payload = response.content
    df = pd.read_csv(BytesIO(payload), sep=";", encoding="utf-8-sig", low_memory=False)
    return df, {
        "url": url,
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "source_bytes": len(payload),
        "last_modified": response.headers.get("Last-Modified"),
    }


def tratar(df: pd.DataFrame, fonte: str, competencia: date) -> pd.DataFrame:
    validar_colunas(df)
    if df.empty:
        raise ValueError("Arquivo vazio")
    df = df.copy()
    df["din_instante"] = pd.to_datetime(df["din_instante"], errors="raise")
    dt = df["din_instante"]
    if dt.isna().any() or not ((dt.dt.year == competencia.year) & (dt.dt.month == competencia.month)).all():
        raise ValueError("Datas ausentes ou fora da competência")
    if not ((dt.dt.minute.isin([0, 30])) & (dt.dt.second == 0) & (dt.dt.microsecond == 0)).all():
        raise ValueError("Instantes fora da grade de 30 minutos")
    if df["id_ons"].isna().any() or df["id_ons"].astype(str).str.strip().eq("").any():
        raise ValueError("id_ons ausente")
    # Nulos existentes são preservados. Texto inválido não vira NaN silenciosamente.
    for col in COLUNAS_NUMERICAS:
        values = df[col].astype("string").str.strip().str.replace(",", ".", regex=False)
        invalid = df[col].notna() & pd.to_numeric(values, errors="coerce").isna()
        if invalid.any():
            raise ValueError(f"Valor numérico inválido em {col}: {int(invalid.sum())} linhas")
    result = calcular_curtailment(df, fonte=fonte)
    if result.duplicated().any():
        raise ValueError("Linhas tratadas integralmente duplicadas; revisar origem antes de publicar")
    # Não deduplicar por id_ons/data: a chave pode não ser única na origem.
    return result.reset_index(drop=True)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def executar(output: Path, meses: list[date], fontes: list[str], hoje: date,
             loader=baixar) -> dict:
    if not meses or any(m.year < ANO_INICIAL or m.year > ANO_FINAL for m in meses):
        raise ValueError("Escopo permitido: somente competências de 2024, 2025 e 2026")
    if any(m > hoje.replace(day=1) for m in meses):
        raise ValueError("Não é permitido solicitar meses futuros")
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    if old and old.get("schema_version") != 1:
        raise ValueError("Versão de manifesto não suportada")
    entries = dict(old.get("files", {}))
    for key, entry in entries.items():
        if mes(entry["competencia"]).year not in range(ANO_INICIAL, ANO_FINAL + 1):
            raise ValueError(f"Snapshot contém competência fora do escopo: {key}; use uma pasta de saída nova")
    now = datetime.now(timezone.utc).isoformat()
    atual = hoje.replace(day=1)
    missing = []
    # Valida TODOS os arquivos selecionados antes de alterar o snapshot de saída.
    with tempfile.TemporaryDirectory(prefix="ons-staging-") as directory, sessao() as s:
        stage = Path(directory)
        for competencia in meses:
            for fonte in fontes:
                key = f"{fonte}/{competencia:%Y-%m}.parquet"
                print(f"Processando {key}", flush=True)
                try:
                    raw, source = loader(s, fonte, competencia)
                except MesIndisponivel:
                    # Só uma competência corrente ainda nunca publicada pode faltar.
                    if competencia == atual and key not in entries and not (output / key).exists():
                        missing.append(key)
                        print(f"Mês corrente ainda não publicado: {key}", flush=True)
                        continue
                    raise
                frame = tratar(raw, fonte, competencia)
                target = stage / key
                target.parent.mkdir(parents=True, exist_ok=True)
                frame.to_parquet(target, engine="pyarrow", compression="zstd", index=False)
                restored = pd.read_parquet(target)
                # Arrow pode representar nulos de colunas object como None em vez de NaN.
                # Compara valores e máscaras de nulos sem alterar os dados gravados.
                expected = frame.copy()
                for col in expected.select_dtypes(include=["object"]).columns:
                    expected[col] = expected[col].where(expected[col].notna(), None)
                    restored[col] = restored[col].where(restored[col].notna(), None)
                pd.testing.assert_frame_equal(expected, restored)
                del expected
                size = target.stat().st_size
                if size >= 95 * 1024**2:
                    raise ValueError(f"{key} excede limite preventivo de 95 MiB; dividir antes de usar Git")
                entries[key] = {
                    **source, "fonte": fonte, "competencia": f"{competencia:%Y-%m}",
                    "rows": len(frame), "bytes": size, "sha256": sha(target),
                    "checked_at": now, "min_timestamp": frame.din_instante.min().isoformat(),
                    "max_timestamp": frame.din_instante.max().isoformat(),
                    "null_counts": {c: int(n) for c, n in frame.isna().sum().items()},
                    "duplicate_id_timestamp_rows": int(frame.duplicated(["id_ons", "din_instante"], keep=False).sum()),
                    "month_in_progress": competencia == atual,
                    "calculation_sha256": sha(ROOT / "src/calculo_curtailment.py"),
                }
                del raw, frame, restored
        if not entries:
            raise ValueError("Nenhum arquivo disponível para publicar")
        # Verifica que entradas antigas continuam existindo e íntegras.
        for key, entry in entries.items():
            candidate = stage / key if (stage / key).exists() else output / key
            if not candidate.is_file() or sha(candidate) != entry["sha256"]:
                raise ValueError(f"Snapshot anterior ausente/corrompido: {key}")
        manifest = {
            "schema_version": 1, "updated_at": now, "allowed_years": [2024, 2025, 2026],
            "columns": COLUNAS_RESULTADO, "interval_minutes": 30,
            "requested_months": [f"{m:%Y-%m}" for m in meses],
            "unavailable_current_month": missing, "files": entries,
            "note": "Validações estruturais; não certificam completude por usina nem ausência de revisões futuras.",
        }
        for candidate in stage.rglob("*.parquet"):
            dest = output / candidate.relative_to(stage)
            dest.parent.mkdir(parents=True, exist_ok=True)
            # Substituição de arquivo individual; a publicação conjunta é o commit Git.
            with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as temp:
                temp.write(candidate.read_bytes())
                temp_path = Path(temp.name)
            os.replace(temp_path, dest)
        with tempfile.NamedTemporaryFile(mode="w", dir=output, delete=False, encoding="utf-8") as temp:
            json.dump(manifest, temp, ensure_ascii=False, indent=2)
            temp.write("\n")
            temp_path = Path(temp.name)
        os.replace(temp_path, manifest_path)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inicio", type=mes, help="Primeiro mês de uma carga histórica")
    parser.add_argument("--fim", type=mes, help="Último mês da carga histórica")
    parser.add_argument("--meses-fechados", type=int, default=3)
    parser.add_argument("--incluir-atual", action="store_true")
    parser.add_argument("--fontes", nargs="+", choices=["EOL", "UFV"], default=["EOL", "UFV"])
    parser.add_argument("--output", type=Path, default=ROOT / "data/curtailment")
    args = parser.parse_args()
    hoje = datetime.now(timezone.utc).date()
    atual = hoje.replace(day=1)
    if bool(args.inicio) != bool(args.fim):
        parser.error("Informe --inicio e --fim juntos")
    if args.meses_fechados < 1:
        parser.error("--meses-fechados deve ser positivo")
    if args.inicio:
        if args.inicio.year < ANO_INICIAL or args.fim.year > ANO_FINAL:
            parser.error("Escopo permitido: somente 2024, 2025 e 2026")
        if args.fim > atual:
            parser.error("Não é permitido solicitar meses futuros")
        meses = periodo(args.inicio, args.fim)
    else:
        meses = meses_recentes(hoje, args.meses_fechados, args.incluir_atual)
    executar(args.output, meses, list(dict.fromkeys(args.fontes)), hoje)


if __name__ == "__main__":
    main()
