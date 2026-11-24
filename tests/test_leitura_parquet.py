import hashlib
import json
import pandas as pd
import pytest
from src.calculo_curtailment import COLUNAS_RESULTADO
from src.leitura_parquet import carregar_periodo_parquet, identidade_snapshot

def salvar(root, fonte="EOL", competencia="2024-04"):
    df = pd.DataFrame({c: [0.] for c in COLUNAS_RESULTADO})
    df["id_ons"] = ["teste"]
    df["fonte"] = [fonte]
    df["din_instante"] = pd.to_datetime([competencia+"-01"])
    key = f"{fonte}/{competencia}.parquet"
    path = root / key
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    manifest = root / "manifest.json"
    meta = json.loads(manifest.read_text()) if manifest.exists() else {"schema_version":1,"files":{}}
    meta["files"][key] = {"bytes":path.stat().st_size,"rows":1}
    manifest.write_text(json.dumps(meta))
    return df

def test_roundtrip(tmp_path):
    expected = salvar(tmp_path)
    actual, report = carregar_periodo_parquet("EOL",2024,4,4,tmp_path)
    pd.testing.assert_frame_equal(expected,actual)
    assert report["origem"] == "parquet_local"

def test_missing_is_not_zero(tmp_path):
    salvar(tmp_path)
    with pytest.raises(FileNotFoundError,match="ausência não significa zero"):
        carregar_periodo_parquet("EOL",2024,4,5,tmp_path)

def test_solar_precoverage(tmp_path):
    salvar(tmp_path,"UFV")
    df, report = carregar_periodo_parquet("UFV",2024,1,4,tmp_path)
    assert len(df)==1
    assert report["meses_sem_cobertura_historica"] == ["2024-01","2024-02","2024-03"]

def test_snapshot_changes(tmp_path):
    salvar(tmp_path)
    before = identidade_snapshot(tmp_path)
    salvar(tmp_path,competencia="2024-05")
    assert identidade_snapshot(tmp_path) != before

@pytest.mark.parametrize("fonte,ano,ini,fim",[("X",2024,1,1),("EOL",2023,1,1),("EOL",2024,4,3)])
def test_invalid(tmp_path,fonte,ano,ini,fim):
    with pytest.raises(ValueError):
        carregar_periodo_parquet(fonte,ano,ini,fim,tmp_path)

def test_corrupt_size(tmp_path):
    salvar(tmp_path)
    with (tmp_path/"EOL/2024-04.parquet").open("ab") as f:
        f.write(b"bad")
    with pytest.raises(ValueError,match="Tamanho"):
        carregar_periodo_parquet("EOL",2024,4,4,tmp_path)

def test_pipeline_multiyear_and_sources(tmp_path,monkeypatch):
    import src.leitura_parquet as leitura
    from src.pipeline import coletar_e_calcular_curtailment
    monkeypatch.setattr(leitura,"DIRETORIO",tmp_path)
    for fonte in ("EOL","UFV"):
        salvar(tmp_path,fonte,"2024-12")
        salvar(tmp_path,fonte,"2025-01")
    df,report=coletar_e_calcular_curtailment(2024,12,2025,1,("EOL","UFV"))
    assert len(df)==4
    assert report["consolidacao_curtailment"]["registros"]==4

def test_numeric_dtype_rejected(tmp_path):
    salvar(tmp_path)
    path = tmp_path/"EOL/2024-04.parquet"
    df = pd.read_parquet(path)
    df["val_curtailment"] = ["invalido"]
    df.to_parquet(path,index=False)
    manifest = tmp_path/"manifest.json"
    meta = json.loads(manifest.read_text())
    meta["files"]["EOL/2024-04.parquet"]["bytes"] = path.stat().st_size
    manifest.write_text(json.dumps(meta))
    with pytest.raises(ValueError,match="Tipo não numérico"):
        carregar_periodo_parquet("EOL",2024,4,4,tmp_path)

def test_ui_coverage_notice_and_cache_contract():
    import ast
    from pathlib import Path
    app = (Path(__file__).resolve().parents[1]/"app.py").read_text()
    tree = ast.parse(app)
    funcs = {n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    wrapper = ast.get_source_segment(app,funcs["executar_pipeline_aplicacao"])
    assert "st.warning(" in wrapper
    assert "identidade_snapshot()" in wrapper
    cached = funcs["_executar_pipeline_snapshot"]
    assert "snapshot_id" in [a.arg for a in cached.args.args]
    cp45 = ast.get_source_segment(app, funcs["renderizar_pagina_cp45"])
    assert "preparar_cp45_mensal(" in cp45
    assert "executar_pipeline_aplicacao(" not in cp45

def test_pyarrow_python_version_markers():
    from pathlib import Path
    from packaging.requirements import Requirement
    entries = [Requirement(line) for line in
               (Path(__file__).resolve().parents[1]/"requirements.txt").read_text().splitlines()
               if line.startswith("pyarrow")]
    for version, pin in [("3.11", "==19.0.1"),("3.12", "==19.0.1"),("3.14", "==24.0.0")]:
        selected = [r for r in entries if r.marker.evaluate({"python_version":version})]
        assert len(selected) == 1
        assert str(selected[0].specifier) == pin

def test_year_filters_capped():
    from pathlib import Path
    app = (Path(__file__).resolve().parents[1]/"app.py").read_text()
    import ast
    filters = [n.value for n in ast.walk(ast.parse(app)) if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "anos_disponiveis" for t in n.targets)]
    assert filters
    bound = ast.parse("min(ultimo_ano_completo, 2026) + 1", mode="eval").body
    for expression in filters:
        ranges = [n for n in ast.walk(expression) if isinstance(n, ast.Call)
                  and isinstance(n.func, ast.Name) and n.func.id == "range"]
        assert ranges
        assert all(len(n.args) > 1 and ast.dump(n.args[1]) == ast.dump(bound) for n in ranges)
