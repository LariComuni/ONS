"""Coleta somente as competências EVT solicitadas, sem aceitar meses ausentes."""
import pandas as pd


class DadosEVTIndisponiveis(ValueError):
    """Ausência de uma ou mais competências necessárias à análise."""


def carregar_evt_selecionado(ano_inicial, mes_inicial, ano_final, mes_final, carregar_periodo):
    if not (2024 <= ano_inicial <= ano_final <= 2026
            and 1 <= mes_inicial <= 12 and 1 <= mes_final <= 12
            and (ano_inicial, mes_inicial) <= (ano_final, mes_final)):
        raise ValueError("Período EVT inválido: selecione meses entre 2024 e 2026.")
    partes = []
    for ano in range(ano_inicial, ano_final + 1):
        inicio = mes_inicial if ano == ano_inicial else 1
        fim = mes_final if ano == ano_final else 12
        df, relatorio = carregar_periodo(ano=ano, mes_inicial=inicio, mes_final=fim)
        esperados = set(range(inicio, fim + 1))
        ausentes = esperados - set(relatorio.get("meses_carregados", []))
        ausentes |= set(relatorio.get("meses_ausentes", [])) & esperados
        if ausentes or df.empty:
            competencias = ", ".join(f"{m:02d}/{ano}" for m in sorted(ausentes or esperados))
            raise DadosEVTIndisponiveis(
                f"Base EVT indisponível ou incompleta para {competencias}. "
                "A análise CP45 foi interrompida: ausência de dados não significa EVT zero. "
                "Tente novamente quando a base do ONS estiver disponível."
            )
        partes.append(df)
    return pd.concat(partes, ignore_index=True)
