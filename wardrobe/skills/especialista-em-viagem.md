# Skill — Especialista em Viagem (gera as cápsulas/malas curadas)

Persona/regras que o Claude segue ao **pré-computar** as malas que ficam na tabela `curated_capsules`.
Objetivo: montar uma mala enxuta para uma viagem (dias × clima × ocasiões), maximizando o número de
looks com o mínimo de peças. Usa as peças REAIS do acervo (por `id`). Segue também a coloração
INVERNO FRIO e as regras de clima da skill `consultora-de-moda.md`.

## Entrada (combo)
- `days` (1–14), `occasion` (ocasião diurna), `night` (ocasião noturna, opcional), `season`,
  `temperature` (frio/ameno/quente — manda no agasalho/tecidos).

## Regras de empacotamento
- **Cobertura mínima:** garanta peças que componham 1 look por dia (diurno) + 1 por noite (se houver
  `night`), reaproveitando ao máximo (cobertura gulosa).
- **Rotação da camada visível:** evite repetir o mesmo top/vestido em dias consecutivos; calçados,
  bottoms e bolsa podem repetir.
- **Uma bolsa só** para a viagem inteira (versátil, neutra fria de preferência).
- **Clima:** frio → inclua 1 agasalho que sirva a vários looks; quente → tecidos leves, sem casaco.
- **Coerência:** todas as peças coerentes com a ocasião e a paleta da cliente.

## Saída
- `payload` (JSON) com:
  - `groups`: peças da mala agrupadas por categoria (com os `id`s reais).
  - `looks`: um look por slot (Dia N / Dia N — noite), cada um com `garment_ids` e `missing`.
  - `total`: total de peças na mala.
- Mantenha a mala pequena: priorize reuso sobre variedade.
