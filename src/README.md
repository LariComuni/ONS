# Código-fonte

Esta pasta contém o código Python responsável pela coleta, validação, tratamento e preparação dos dados utilizados pela aplicação.

O objetivo é manter as regras de processamento separadas da interface visual desenvolvida em Streamlit.

## Estrutura prevista

- `coleta_ons.py`: monta URLs, consulta o ONS, carrega os meses, consolida períodos e otimiza os tipos.
- `calculo_curtailment.py`: aplica a metodologia de cálculo da geração de referência ajustada, do curtailment e da geração esperada para fontes eólicas e fotovoltaicas.
- `indicadores.py`: cálculo dos indicadores apresentados na aplicação.
- `mapa.py`: preparação das camadas e informações exibidas no mapa.

## Fluxo de processamento

1. O usuário seleciona a fonte e o período na aplicação.
2. O código monta automaticamente as URLs dos arquivos mensais do ONS.
3. Os arquivos são lidos diretamente da fonte pública.
4. Os dados são validados, tratados e consolidados.
5. Os resultados são preparados para os indicadores, gráficos e mapas.
6. A aplicação Streamlit apresenta as informações ao usuário.

## Fontes de geração

Inicialmente, o projeto considera:

- `EOL`: geração eólica;
- `UFV`: geração solar fotovoltaica.

## Princípios de organização

- As bases completas não devem ser armazenadas nesta pasta.
- Credenciais e informações sensíveis não devem ser incluídas no código.
- Caminhos pessoais do Google Drive não devem ser utilizados.
- As funções devem funcionar independentemente do Google Colab.
- Cada arquivo deve possuir uma responsabilidade bem definida.
- As funções de tratamento devem ser reutilizáveis pela aplicação e pelos testes.

## Status

A estrutura ainda está em desenvolvimento.

A primeira funcionalidade a ser implementada será a leitura direta dos dados mensais de curtailment do ONS para fontes eólicas e fotovoltaicas.
