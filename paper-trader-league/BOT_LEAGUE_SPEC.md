# Bot League Spec

## Season rules

- **Season length:** 72 hours (3 days)
- **Starting bankroll:** 0.05 BTC per bot
- **Primary objective:** maximize BTC-denominated ending equity
- **Allowed holdings:** any supported spot asset; bots do not need to rotate back to BTC unless conviction justifies fees
- **Scoring denomination:** BTC mark-to-market using best available spot conversion path
- **Markets:** broad crypto universe; prioritize liquid spot pairs first, expand later
- **Data retention:** persist every market snapshot used for decisions, every order, fill, rationale, and metric sample for final reporting

## Execution assumptions

- **Default fee model:**
  - taker fee = 0.06%
  - maker fee = 0.04%
- **Slippage model:**
  - high liquidity symbols: 1–3 bps
  - mid liquidity symbols: 4–12 bps
  - low liquidity symbols: configurable safety cap or trade ban
- **Capital controls:**
  - no leverage in v1
  - no shorting in v1 unless represented via inverse/hedged spot proxy logic later
  - max exposure and bot-specific sizing rules enforced by trade engine

## Shared operating principles

All bots are intentionally aggressive, but differently aggressive:

1. **Aurora Quanta** – aggressive conviction swings on regime/narrative changes
2. **StormChaser Delta** – aggressive momentum and news shock exploitation
3. **Mercury Vanta** – aggressive short-horizon edge extraction with faster turnover

All bots must:
- reason in BTC terms, not just USD gain
- include fee/friction awareness in every order decision
- log rationale metadata for post-season analysis
- maintain distinct behavior so the league is meaningful
