# Coleta semanal de curtailment EOL/UFV

Escopo fixo: **2024, 2025 e 2026**, conforme solicitado. Não baixa nem publica competências anteriores ou posteriores.

Implementação inicial para o SINmulator, baseada no commit `7116e9d1a7bd3466278aa7a9a44d0b6287d4fe11`.

## O que muda

Uma rotina independente do Streamlit baixa os CSVs mensais do ONS, usa **a função existente `calcular_curtailment`**, valida os resultados e grava:

```
data/curtailment/
  EOL/2026-10.parquet
  UFV/2026-10.parquet
  manifest.json
```

Cada Parquet contém as 19 colunas do resultado atual, em intervalos de 30 minutos, com compressão Zstandard. Não são alteradas as fórmulas, a granularidade, as abas ou o carregamento atual do aplicativo. **Nesta etapa o app ainda usa os leitores atuais; conectar o app aos Parquets é a etapa seguinte.** EVT, PLD, térmicas e cadastros geográficos não fazem parte desta entrega.

## Arquivos a adicionar na raiz do repositório ONS

- `scripts/atualizar_curtailment.py`
- `requirements-coleta.txt`
- `tests/test_atualizar_curtailment.py`
- `.github/workflows/atualizar-curtailment.yml` (a pasta `.github` pode ficar oculta no explorador)
- `docs/coleta-semanal.md`

Não substituir `app.py`, `src/coleta_ons.py` ou `src/calculo_curtailment.py`. Os scripts importam esses módulos existentes. O arquivo de dependências separado evita instalar Streamlit e bibliotecas geográficas no job.

## Ativação no GitHub

1. Adicione os cinco arquivos preservando os caminhos e faça commit na branch padrão, atualmente `main`.
2. Abra **Actions → Atualizar bases de curtailment → Run workflow**.
3. Para um primeiro teste, informe `inicio = 2026-10`, `fim = 2026-10` e `fontes = EOL UFV`. Confira o resultado verde e os dois arquivos publicados em `data/curtailment`.
4. Para carregar outros períodos, execute novamente com o intervalo desejado, preferencialmente em lotes de poucos meses. **O job semanal não cria automaticamente todo o histórico anterior.** Escolha somente períodos efetivamente disponibilizados pelo ONS para ambas as fontes; um 404 em mês encerrado interrompe o lote.
5. Nas execuções manuais normais, deixe início e fim vazios e escolha `EOL UFV`: serão atualizados o mês corrente e os três meses encerrados imediatamente anteriores. Exemplo em novembro/2026: agosto, setembro, outubro e novembro.

O agendamento semanal sempre usa ambas as fontes (`EOL UFV`), independentemente da seleção feita em uma execução manual anterior. Durante 2026, revisa três meses encerrados mais o corrente. **A partir de janeiro/2027, continua apenas revisando outubro, novembro e dezembro/2026**, sem criar competências de 2027. Para encerrar também essas revisões, desabilite o workflow em Actions quando desejar. O escopo só muda com alteração explícita dos limites no código.

Datas futuras são recusadas mesmo dentro do escopo: dezembro/2026 só poderá ser solicitado a partir de dezembro. Uma pasta de saída cujo manifesto já contenha outros anos é rejeitada, sem apagar dados; use uma pasta nova para este escopo.

O agendamento é segunda-feira, **09:17 UTC / 06:17 Brasília**. O GitHub pode atrasar execuções; não é horário garantido. Schedules rodam na branch padrão; repositórios públicos inativos podem ter o agendamento desativado pelo GitHub após 60 dias.

O workflow solicita `contents: write` para o `GITHUB_TOKEN` temporário do próprio GitHub e faz commit apenas de `data/curtailment`. Não precisa de token pessoal nem senha. Políticas da organização/repositório podem impedir escrita ou commits diretos na branch protegida. Nesse caso, o job falha na publicação; não desative proteções para contornar isso. Adapte a publicação a uma branch de dados ou PR no próximo passo.

**Ao instalar e habilitar o workflow, ele passará a publicar os arquivos por commits automáticos no repositório.** O trabalho entregue não ativou isso no GitHub. Os dados são públicos do ONS. Não adicione dados internos da Elera a esse fluxo sem revisar destino e acesso.

## Executar localmente

Na raiz de ONS, com Python 3.11:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate
python -m pip install -r requirements-coleta.txt pytest==8.3.5
python -m pytest tests/test_atualizar_curtailment.py -q
python scripts/atualizar_curtailment.py --inicio 2026-10 --fim 2026-10
```

Atualização recente incluindo o mês corrente:

```bash
python scripts/atualizar_curtailment.py --meses-fechados 3 --incluir-atual
```

Apenas eólica, ou saída temporária para teste:

```bash
python scripts/atualizar_curtailment.py --inicio 2026-10 --fim 2026-10 --fontes EOL --output teste-curtailment
```

## Validações e limites

- HTTP com timeout e tentativas para falhas transitórias. Ausência de mês encerrado, erro HTTP, CSV vazio/inválido ou esquema incompleto abortam o lote.
- Datas precisam ser válidas, dentro da competência e na grade de 30 minutos. Identificador ONS é obrigatório. Texto inválido em medidas utilizadas no cálculo não é convertido silenciosamente para nulo.
- Nulos genuínos são preservados; contagens constam no manifesto. A metodologia atual permanece intacta, inclusive seu comportamento para medidas nulas.
- Linhas tratadas integralmente duplicadas impedem publicação. Repetições de `id_ons + din_instante` são registradas, sem exclusão automática, porque a chave deve ser analisada antes de deduplicar.
- O Parquet é lido de volta e comparado com o DataFrame antes da publicação. Arquivos acima de 95 MiB são bloqueados preventivamente.
- Um 404 do mês **corrente**, se ele nunca foi publicado neste snapshot, é registrado explicitamente como indisponível. Outros erros não são ignorados. O mês corrente sempre é sinalizado como em andamento; não representa um mês completo.
- O manifesto registra origem, hashes, tamanho, quantidade de linhas, cobertura temporal, nulos e hash da função de cálculo para cada arquivo. Com apenas esses controles **não é possível garantir completude por usina** nem detectar todas as omissões da fonte.
- Todos os arquivos selecionados são preparados antes de substituir a saída local. O conjunto fica publicado no remoto em um único commit somente após sucesso. Substituições locais são atômicas por arquivo, não uma transação de diretório; não use a pasta local simultaneamente como servidor de dados em produção. O snapshot remoto só muda após o push.
- Se outra pessoa atualizar a branch durante a coleta, o push pode falhar com segurança. Execute novamente; o workflow nunca usa force-push.
- A janela de três meses é uma premissa inicial, não um limite das revisões do ONS. Faça reconciliações históricas manuais por intervalo e reexecute o histórico se a metodologia de cálculo mudar.

## Armazenamento

O teste de outubro/2026 indicou cerca de 8 MiB para EOL+UFV tratados, contra aproximadamente 63 MiB em CSV bruto. Isso não dimensiona todo o histórico. Antes de grandes cargas, meça os arquivos e o crescimento do repositório. O histórico Git guarda versões antigas de binários; substituir um Parquet não elimina suas versões anteriores. Se o volume crescer muito, migre a publicação para armazenamento de objetos ou Releases sem alterar o tratamento.

Não guardar CSVs brutos no Git e não usar Git LFS automaticamente. O limite preventivo por arquivo não substitui planejamento do tamanho total do repositório.

## Verificação desta entrega

- 23 testes automatizados aprovados, cobrindo preservação das fórmulas, mudança de ano, arquivos vazios, datas inválidas, esquema ausente, texto numérico inválido, duplicidades, nulos, falha parcial de lote, corrupção prévia e mês corrente indisponível.
- Coleta real de outubro/2026 e gravação/leitura dos dois Parquets concluídas: EOL 226.128 linhas e 5,99 MiB; UFV 124.992 linhas e 2,12 MiB. O tamanho pode variar com representação dos tipos e versão das bibliotecas.
- Estrutura YAML e compilação Python verificadas. O workflow não foi executado no GitHub; permissões, política de branch e agendamento só podem ser verificados após instalação.
- Não foi medido todo o histórico, nem o pico de RAM do Streamlit; o aplicativo não foi alterado.


## Carga histórica 2024–2026 por fonte

O seletor **fontes** no formulário manual oferece `EOL UFV`, `EOL` e `UFV`. Os períodos disponíveis diferem por fonte. Não presuma que um período válido para eólica também exista para solar.

Verificação em 12/11/2026 por requisição HTTP HEAD a cada URL mensal oficial:

- **EOL:** janeiro/2024 a novembro/2026 retornaram HTTP 200 (35 URLs).
- **UFV:** janeiro, fevereiro e março/2024 retornaram HTTP 404. Abril/2024 a novembro/2026 retornaram HTTP 200 (32 URLs).
- **Dezembro/2026:** futuro; não consultado nem baixado nesta verificação.

HTTP 200 confirma a resposta da URL, não valida as linhas, esquema ou completude do CSV. Não foram processados todos os 67 arquivos disponíveis. Os testes reais de conteúdo estão discriminados na seção de verificação. A indisponibilidade dessas três URLs UFV não prova que o ONS não possua dados históricos em outro formato ou conjunto; não foram inventados nem preenchidos registros para elas.

### Plano inicial de carga manual

Execute na ordem que preferir, em lotes menores se o tamanho/tempo exigir:

1. **EOL:** início `2024-01`, fim `2024-12`, fontes `EOL`.
2. **UFV:** início `2024-04`, fim `2024-12`, fontes `UFV`.
3. **Ambas:** início `2025-01`, fim `2025-12`, fontes `EOL UFV`.
4. **Ambas:** início `2026-01`, fim `2026-10`, fontes `EOL UFV` (meses encerrados na data desta entrega).
5. **Ambas:** início `2026-11`, fim `2026-11`, fontes `EOL UFV` para incluir o mês em andamento, ou executar sem datas para a atualização recente.

Não solicitar dezembro/2026 antes do mês começar. O agendamento o incluirá quando chegar dezembro, mantendo a marca de mês em andamento até a revisão de janeiro/2027. A atualização semanal não faz automaticamente a carga completa acima.

Não selecione ambas as fontes para janeiro–março/2024: uma ausência UFV em mês encerrado abortará o lote inteiro e nenhum commit será publicado. A execução de uma fonte preserva os arquivos e as entradas do manifesto das outras fontes já publicados. Arquivos ausentes não viram linhas de zero. O único caso tolerado é um 404 no mês corrente ainda nunca publicado, explicitamente registrado no manifesto; HTTP 403, falhas de rede e erros de tratamento continuam interrompendo o lote.

O seletor de fontes também foi verificado com seis cenários de encaminhamento dos argumentos Bash. Foram adicionados testes para rejeitar anos fora do escopo, recusar competências futuras, limitar a virada de 2026 para 2027 e impedir a manutenção silenciosa de um manifesto com outros anos.

Verificação real adicional do início do escopo: EOL/2024-01.parquet: 231,984 linhas; UFV/2024-04.parquet: 79,776 linhas. Ambos passaram na validação, cálculo e comparação após leitura do Parquet. Também foram processadas anteriormente as amostras EOL/UFV de outubro/2024 e outubro/2025; não se trata de validação integral do histórico.
