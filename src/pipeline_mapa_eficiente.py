"""Mapa com memória limitada a um mês e perfis compactos de 24 horas.

Os gráficos existentes são perfis médios do dia, não séries cronológicas de
um ano. Somamos numeradores/contagens mensalmente (nunca médias de médias),
materializando apenas esses perfis e os cadastros, sem guardar bases anuais.
"""
from datetime import date
import pandas as pd
from .leitura_parquet import carregar_periodo_parquet
from .enriquecimento_geografico import reduzir_fator_capacidade, enriquecer_curtailment
from .pipeline import (validar_periodo, validar_fontes, carregar_bases_auxiliares,
                       preparar_rede_transmissao, criar_camadas_geograficas)
from .preparacao_geometrias import preparar_base_geografica_curtailment
from .series_mapa import (calcular_perfil_horario_usinas, calcular_perfil_horario_pontos,
                          criar_indices_series_pontos, criar_indices_series_coordenadas,
                          criar_serie_24, COLUNA_CODIGO_RESTRICAO)

METRICAS = ['val_geracao', 'val_curtailment', 'val_geracao_esperada']
CHAVES = ['nom_usina', 'hora', COLUNA_CODIGO_RESTRICAO]


def reduzir_mes_mapa(df):
    """Estatísticas suficientes; contagem distinta para cada métrica nula."""
    slim = df[['nom_usina', 'din_instante', 'cod_razaorestricao', *METRICAS]].copy()
    slim['hora'] = pd.to_datetime(slim.pop('din_instante')).dt.hour
    slim[COLUNA_CODIGO_RESTRICAO] = slim.pop('cod_razaorestricao').astype('string').str.strip().fillna('SEM_CODIGO').replace('', 'SEM_CODIGO')
    for c in METRICAS:
        slim[c] = pd.to_numeric(slim[c], errors='coerce').astype('float64')
    agg = {f'{c}_soma': (c, 'sum') for c in METRICAS}
    agg.update({f'{c}_n': (c, 'count') for c in METRICAS})
    agg['n_registros'] = ('val_curtailment', 'size')
    return slim.groupby(CHAVES, observed=True, dropna=True).agg(**agg).reset_index()


def combinar_estatisticas_mapa(atual, novo):
    if atual is None:
        return novo
    return pd.concat([atual, novo], ignore_index=True).groupby(CHAVES, observed=True, dropna=True).sum(numeric_only=True).reset_index()


def finalizar_perfis_mapa(stats, cadastro):
    """Mesma semântica do mapa legado: média/usina e soma/médias no ponto."""
    enriched, _ = enriquecer_curtailment(stats, cadastro)
    keys = ['nom_usina', 'nom_pontoconexao', 'hora']
    totals = enriched.groupby(keys, observed=True, dropna=True).sum(numeric_only=True).reset_index()
    for c in METRICAS:
        totals[c] = totals[f'{c}_soma'] / totals[f'{c}_n'].replace(0, float('nan'))
    hourly, by_usina, _ = calcular_perfil_horario_usinas(totals)
    # O denominador legado conta todos os registros da usina/hora.
    denominators = enriched.groupby(['nom_usina', 'hora'], observed=True)['n_registros'].sum().rename('n_total')
    codes = enriched.merge(denominators, on=['nom_usina', 'hora'], validate='many_to_one')
    codes = codes[codes['nom_pontoconexao'].notna()].copy()
    codes['contribuicao'] = ((codes['val_curtailment_soma'] / codes['val_curtailment_n'].replace(0, float('nan')))
                             * codes['n_registros'] / codes['n_total'])
    by_usina_code = {}
    for (nome, codigo), grupo in codes.groupby(['nom_usina', COLUNA_CODIGO_RESTRICAO], observed=True):
        by_usina_code.setdefault(str(nome), {})[str(codigo)] = criar_serie_24(grupo, 'contribuicao')
    point_codes = codes.groupby(['nom_pontoconexao', COLUNA_CODIGO_RESTRICAO, 'hora'], observed=True)['contribuicao'].sum().reset_index()
    by_ponto_code = {}
    for (nome, codigo), grupo in point_codes.groupby(['nom_pontoconexao', COLUNA_CODIGO_RESTRICAO], observed=True):
        by_ponto_code.setdefault(str(nome), {})[str(codigo)] = criar_serie_24(grupo, 'contribuicao')
    _, by_ponto, _ = calcular_perfil_horario_pontos(hourly)
    return enriched, hourly, by_usina, by_usina_code, by_ponto, by_ponto_code



def preparar_dados_mapa(ano_inicial, mes_inicial, ano_final, mes_final,
                        fontes=None, data_referencia=None, timeout=120,
                        diretorio=None, bases_auxiliares=None):
    """Entrada exclusiva da aba Mapa; nunca retém observações anuais."""
    validar_periodo(ano_inicial, mes_inicial, ano_final, mes_final)
    fontes = validar_fontes(fontes)
    stats, metadata, n = None, [], 0
    for fonte in fontes:
        for ano in range(ano_inicial, ano_final + 1):
            lo = mes_inicial if ano == ano_inicial else 1
            hi = mes_final if ano == ano_final else 12
            for mes in range(lo, hi + 1):
                df, _ = carregar_periodo_parquet(fonte, ano, mes, mes, diretorio=diretorio)
                if df.empty:
                    continue
                n += len(df)
                # Marcadores só precisam de um registro representativo por nome.
                metadata.append(df.drop_duplicates('nom_usina').copy())
                stats = combinar_estatisticas_mapa(stats, reduzir_mes_mapa(df))
                del df
    if stats is None:
        raise ValueError('Não há dados disponíveis para o período e fontes selecionados.')
    metadata = pd.concat(metadata, ignore_index=True).drop_duplicates('nom_usina')
    fcap, subestacoes, linhas, rel_aux = bases_auxiliares if bases_auxiliares is not None else carregar_bases_auxiliares(data_referencia or date.today(), timeout)
    cadastro = reduzir_fator_capacidade(fcap)
    del fcap
    enriched_meta, _ = enriquecer_curtailment(metadata, cadastro)
    _, georef, _ = preparar_base_geografica_curtailment(enriched_meta)
    _, _, _, linhas_geo, rel_rede = preparar_rede_transmissao(subestacoes, linhas)
    usinas, pontos, _, linhas_desenhaveis, busca, rel_camadas = criar_camadas_geograficas(georef, linhas_geo)
    compact, _, by_usina, by_usina_code, by_ponto, by_ponto_code = finalizar_perfis_mapa(stats, cadastro)
    indices = criar_indices_series_pontos(compact, georef, by_ponto, by_ponto_code)
    usina_map, ponto_map, rel_indices = criar_indices_series_coordenadas(
        usinas, pontos, by_usina, by_usina_code, indices[0], indices[2], indices[3], indices[4])
    return {'gdf_usinas': usinas, 'gdf_pontos': pontos,
            'gdf_linhas_desenhaveis': linhas_desenhaveis, 'gdf_busca': busca,
            'usina_series_map': usina_map, 'ponto_series_by_latlon': ponto_map,
            'relatorios': {'bases_auxiliares': rel_aux, **rel_rede, **rel_camadas,
                'indices_coordenadas': rel_indices,
                'resumo_pipeline': {'registros_curtailment': n, 'usinas': len(usinas),
                    'pontos': len(pontos), 'linhas_desenhaveis': len(linhas_desenhaveis),
                    'periodo_inicial': f'{mes_inicial:02d}/{ano_inicial}',
                    'periodo_final': f'{mes_final:02d}/{ano_final}',
                    'registros_compactos': len(stats), 'modo': 'mapa_mensal_compacto'}}}
