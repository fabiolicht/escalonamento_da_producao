# Escalonador de produção

Simulador de escalonamento para uma linha de produção com múltiplas etapas, tipos
de máquina, tempos de preparação (setup) e prazos por ordem. O programa compara
regras de despacho e gera planilhas, gráficos e resumos para apoiar a análise da
capacidade e dos gargalos.

## Definição do problema

Cada linha da aba `Entrada` representa uma ordem de uma peça. A peça percorre,
na ordem definida na aba `Dados`, uma rota de máquinas. Cada tipo de máquina
tem uma unidade na frota inicial, um tempo de processamento por operação e um
tempo de setup. O setup é aplicado quando a máquina muda o tipo de peça em
relação à operação anterior; repetir o mesmo tipo não requer setup.

As ordens são liberadas conforme a data de entrada e recebem um prazo de 20
dias corridos. Por padrão, a produção ocorre de segunda a sexta-feira, das
08:00 às 12:00 e das 13:00 às 17:00 (480 minutos úteis por dia). O objetivo
prático é reduzir ordens atrasadas e, em seguida, atraso, lead time, setup e
makespan, respeitando a sequência das operações e a disponibilidade das
máquinas.

## Como a solução funciona

1. Lê as ordens e as rotas, tempos de processamento e setups de `pecas.xlsx`.
2. Constrói a frota e converte as datas de liberação e os prazos para o
   calendário de trabalho.
3. Simula as políticas de referência:
   - **FIFO linha**: prioriza a ordem original de entrada;
   - **FIFO máquina**: prioriza o instante em que a ordem entrou na fila da
     máquina.
4. Escolhe uma política proposta entre ATCS, LOTE, EDD e SPT. Para ATCS, busca
   parâmetros com uma população inicial e gerações de busca; a prioridade
   considera urgência do prazo, setup, formação de lotes e espera.
5. Avalia as políticas por lead time, atrasos, setup, makespan e utilização.
   Faz também um teste de robustez embaralhando os tipos de peça entre ordens
   do mesmo dia de entrada, sem alterar a quantidade diária.
6. No modo padrão, consolida as rodadas, aumenta uma unidade do tipo de máquina
   identificado como gargalo para a rodada seguinte e avalia cenários de hora
   extra e dois turnos. `--sem-frota` desativa a projeção de compra e os
   cenários de turnos.

A pontuação usada na busca prioriza fortemente o número de ordens atrasadas:

```text
1.000.000 × ordens atrasadas
+ 1.000 × atraso médio em dias
+ 100 × lead time médio em dias
+ 0,02 × setup total em minutos
+ 10 × makespan em dias úteis
```

## Dados de entrada

O arquivo esperado é `pecas.xlsx`, na pasta do projeto.

| Aba | Colunas utilizadas |
| --- | --- |
| `Entrada` | `Data entrada`, `Tipo de peça` |
| `Dados` | `Peças`, `Rota da Peça`, `Máquinas`, `Tempo de máquina (min)`, `Tempo de troca de peças` |

As colunas de quantidade de máquinas por rodada existentes na aba `Dados` não
são usadas: a frota inicial é uma unidade de cada tipo de máquina citado nas
rotas. Todas as linhas de `Entrada` são tratadas como ordens a simular.

## Dependências e execução

Requer Python e as bibliotecas `pandas`, `numpy`, `scipy`, `matplotlib` e
`openpyxl`. Não há arquivo de dependências com versões fixadas neste projeto.
Instale as bibliotecas com:

```bash
python -m pip install pandas numpy scipy matplotlib openpyxl
```

Execute a partir da pasta que contém `pecas.xlsx`:

```bash
python Producao.py
```

Também é possível executar como módulo:

```bash
python -m producao
```

O comando acima usa os padrões: cinco rodadas, cinco instâncias embaralhadas
por rodada, três gerações e população de cinco indivíduos na busca ATCS. A
busca e os embaralhamentos usam semente `42`.

| Opção | Padrão | Descrição |
| --- | ---: | --- |
| `--rodadas 1,3` | Todas | Rodadas incluídas no consolidado; as anteriores necessárias também são executadas |
| `--instancias N` | `5` | Mixes diários embaralhados no teste pareado |
| `--geracoes N` | `3` | Gerações da busca de parâmetros ATCS |
| `--populacao N` | `5` | Indivíduos por geração |
| `--sem-frota` | Desativada | Não simula projeção de frota nem cenários de turnos |

Exemplo de execução rápida de uma rodada, sem cenários adicionais de frota e
turno:

```bash
python Producao.py --rodadas 1 --sem-frota
```

Para consultar todas as opções:

```bash
python Producao.py --help
```

## Resultados de uma execução

Execução de referência feita com Python 3.13.9 e o comando:

```bash
python Producao.py --rodadas 1 --sem-frota
```

Foram simuladas 1.000 ordens, com média de 20 ordens por dia e uma frota inicial
de 11 máquinas (uma por tipo). A política selecionada foi ATCS, com estes
parâmetros:

```text
k1=4.0, k2=1.7718, w_batch=1.8267, w_wait=0.3144
```

| Indicador | Proposta (ATCS) | FIFO linha | FIFO máquina |
| --- | ---: | ---: | ---: |
| Lead time médio (dias corridos) | 47,64 | 55,13 | 54,34 |
| Ordens atrasadas | 696 (69,6%) | 789 (78,9%) | 738 (73,8%) |
| Setup total (min) | 44.870 | 70.655 | 67.070 |
| Makespan (dias úteis) | 128,15 | — | — |

O ganho de lead time da proposta foi de 13,6% contra FIFO linha e 12,3% contra
FIFO máquina. O gargalo identificado foi a **Machine 2**, com uma unidade e
99,5% de utilização no makespan. A próxima rodada do fluxo padrão acrescenta
uma unidade desse tipo.

Nos cinco mixes embaralhados, o lead time médio foi:

| Comparação pareada | Proposta | Referência | Teste t pareado | Wilcoxon |
| --- | ---: | ---: | ---: | ---: |
| Proposta × FIFO linha | 47,67 ± 0,07 dias | 55,04 ± 0,27 dias | p = 3,27 × 10⁻⁷ | p = 0,0625 |
| Proposta × FIFO máquina | 47,67 ± 0,07 dias | 54,12 ± 0,20 dias | p = 7,10 × 10⁻⁸ | p = 0,0625 |

Os valores após `±` são desvios-padrão amostrais. Embora o teste t indique
diferenças entre as médias, cinco instâncias são uma amostra pequena e o teste
de Wilcoxon não atinge o limiar de 5%. Portanto, estes resultados são evidência
inicial, não uma conclusão estatística robusta.

## Análise e limitações

- A proposta melhora o lead time, reduz atrasos e reduz setups frente às duas
  referências nesta execução, mas **não atende ao prazo**: 696 das 1.000 ordens
  continuam atrasadas.
- A utilização próxima de 100% na Machine 2 indica restrição de capacidade.
  Aumentar a frota nesse tipo ou ampliar o calendário são cenários a investigar;
  o resultado não garante que uma única unidade adicional resolva os atrasos.
- Lead time é medido em dias corridos; makespan é expresso em dias úteis.
- O código compara o instante de conclusão com o prazo definido à meia-noite
  da data que ocorre 20 dias após a entrada. Assim, concluir durante esse dia
  também é contado como atraso. Confirme se essa interpretação do prazo
  corresponde à regra de negócio desejada.
- O teste de robustez altera somente a associação dos tipos às ordens dentro de
  cada dia de chegada. Ele não representa variações de volume, tempos de
  processo, falhas ou indisponibilidade de máquinas.
- A função objetivo privilegia o número de atrasos; a política escolhida não é
  necessariamente a que minimiza isoladamente setup ou lead time.

## Arquivos gerados

Os resultados são gravados nas pastas `Execucao_Rodada_Round_N/` e
`Execucao_Consolidada/`, criadas na pasta do projeto. Entre os principais
artefatos estão:

- `resumo.txt`: resumo textual de cada rodada;
- `parts_updated_round_n.xlsx`: dados de entrada atualizados, comparação de
  políticas, sequência de produção, gargalo, capacidade e Gantt;
- `sequencia_producao_round_n.xlsx`: sequência por política e gráficos diários;
- `consolidated_multiround_report.xlsx`: consolidação das rodadas, requisitos
  de capacidade, mixes embaralhados e, no modo padrão, cenários de frota e
  calendário;
- arquivos PNG com Gantt, utilização/ociosidade, setups e comparações.

Os números apresentados neste README correspondem à execução de uma rodada
descrita acima; uma execução completa pode produzir valores diferentes ao
acrescentar máquinas nas rodadas seguintes.
