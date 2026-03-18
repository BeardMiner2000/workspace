# Bot Strategy Specs

## Shared constraints

- Starting capital: 0.05 BTC each
- Objective: maximize BTC-denominated ending equity after fees/slippage
- Universe: broad spot market, but v1 should prefer liquid symbols first while leaving room for opportunistic expansion
- Every order must include a rationale payload with feature values used in the decision

---

## Aurora Quanta — spec

### Objective
Capture major BTC-relative repricing moves driven by regime change, macro shifts, and narrative rotation.

### Trade frequency target
- Low to medium
- ~2 to 10 meaningful position changes per day

### Position sizing behavior
- Base risk unit: 12% of bankroll
- Can pyramid up to 60–75% gross exposure when conviction stack is strong
- Prefers concentrated exposure in top-ranked opportunities

### Preferred setups
- sustained BTC-relative breakout with sector confirmation
- macro risk-on/risk-off regime break
- narrative rotation confirmed by breadth and volume
- oversold major with strong reversal + supportive macro catalyst

### Avoid
- random microcaps with no narrative support
- low-liquidity names with excessive slippage
- choppy directionless market regimes

### Stop logic
- thesis invalidation stop, volatility-adjusted trailing stop, time stop if expected rotation fails to materialize

---

## StormChaser Delta — spec

### Objective
Exploit fast repricing after headlines, panic, euphoria, social attention bursts, and liquidation cascades.

### Trade frequency target
- Medium to high
- ~6 to 30 trades per day depending on volatility regime

### Position sizing behavior
- Base risk unit: 5% of bankroll
- Can scale to 35–50% on extreme-quality event setups
- Must reduce size automatically as slippage/fee burn increases

### Preferred setups
- headline-driven breakout with abnormal volume
- shock event followed by clean continuation
- extreme negative event with high-probability relief reversal
- fast-moving sector sympathy trades after anchor asset move

### Avoid
- low-quality rumor noise without tape confirmation
- dead markets with no attention flow
- overtrading during flat news cycles

### Stop logic
- tight volatility stops
- momentum failure exits
- hard churn guardrail if fee burn exceeds threshold

---

## Mercury Vanta — spec

### Objective
Compound BTC through repeated short-horizon edges using execution quality and microstructure signals.

### Trade frequency target
- Medium to high
- ~10 to 40 actions per day depending on liquidity and signal quality

### Position sizing behavior
- Base risk unit: 3% of bankroll
- Can stack several concurrent low-correlation tactical positions
- Gross exposure typically capped lower than Aurora, but turnover can be higher

### Preferred setups
- spread compression/expansion transitions
- order-book imbalance with short-horizon follow-through
- micro mean reversion after overextension
- BTC-conversion-efficient alt moves with strong near-term expectancy

### Avoid
- thin order books
- signals where expected edge is smaller than fees + slippage
- major news spikes before tape stabilizes

### Stop logic
- very short time-based exits
- microstructure invalidation
- immediate cut if expected edge deteriorates below friction threshold
