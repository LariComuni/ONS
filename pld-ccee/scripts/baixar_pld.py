from pathlib import Path
import sys
import requests


URLS_PLD = {
    2023: ("https://pda-download.ccee.org.br/HH4Xegm7R56M_H4qPNOvaw/content"),
    2024: ("https://pda-download.ccee.org.br/rMsBwN6TT-WUW2_LbGUvkw/content"),
    2025: ("https://pda-download.ccee.org.br/korJMXwpSLGyVlpRMQWduA/content"),
    2026: ("https://pda-download.ccee.org.br/6A5wq97KTCWv_bvs3CqsQQ/content"),
}


BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_SAIDA = BASE_DIR / "dados"

PASTA_SAIDA.mkdir(parents=True,exist_ok=True)

def baixar_pld(ano, url):
    caminho = (PASTA_SAIDA / f"pld_horario_{ano}.csv")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        ),
        "Accept": ("text/csv,text/plain,application/octet-stream,*/*"),
        "Accept-Language": ("pt-BR,pt;q=0.9,en;q=0.8")
    }

    resposta = requests.get(url,headers=headers,timeout=180,allow_redirects=True)

    content_type = (resposta.headers.get("Content-Type", "").lower())

    print(f"{ano}: status={resposta.status_code}, tipo={content_type}, tamanho={len(resposta.content):,} bytes")

    if resposta.status_code != 200:
        print(resposta.text[:500],file=sys.stderr)
        return False

    if "text/html" in content_type:
        print(f"{ano}: o servidor retornou HTML, possivelmente uma página de bloqueio.",file=sys.stderr)
        print(resposta.text[:500],file=sys.stderr)
        return False

    caminho.write_bytes(resposta.content)

    # Verificação simples do cabeçalho do CSV
    primeira_linha = (resposta.content.decode("utf-8-sig", errors="replace").splitlines()[0])

    colunas_esperadas = {
        "MES_REFERENCIA",
        "SUBMERCADO",
        "PERIODO_COMERCIALIZACAO",
        "DIA",
        "HORA",
        "PLD_HORA",
    }

    colunas_recebidas = set(primeira_linha.split(";"))

    if not colunas_esperadas.issubset(
        colunas_recebidas
    ):
        print(
            f"{ano}: o conteúdo recebido não parece "
            "ser o CSV de PLD esperado.",
            file=sys.stderr,
        )

        caminho.unlink(
            missing_ok=True
        )

        return False

    print(
        f"{ano}: arquivo salvo em {caminho}"
    )

    return True


resultados = {ano: baixar_pld(ano, url) for ano, url in URLS_PLD.items()}


sucessos = [ano for ano, sucesso in resultados.items() if sucesso]

falhas = [ano for ano, sucesso in resultados.items() if not sucesso]


print("\nResumo:")
print("Sucessos:", sucessos)
print("Falhas:", falhas)


if not sucessos:
    raise SystemExit(
        "Nenhum arquivo foi baixado. "
        "O acesso do GitHub Actions também pode "
        "estar sendo bloqueado pela CCEE."
    )
