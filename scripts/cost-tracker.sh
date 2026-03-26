#!/bin/bash
# cost-tracker.sh — Simple API usage and cost monitor

TRACKER_DIR="$HOME/.openclaw/workspace/logs/cost"
mkdir -p "$TRACKER_DIR"

TRACKER_FILE="$TRACKER_DIR/usage_$(date +%Y-%m-%d).json"

# Initialize tracker for today if it doesn't exist
if [ ! -f "$TRACKER_FILE" ]; then
  cat > "$TRACKER_FILE" << 'EOF'
{
  "date": "$(date +%Y-%m-%d)",
  "models": {
    "openai-codex/gpt-5.4": { "calls": 0, "tokens": 0, "estimated_cost": 0 },
    "anthropic/claude-sonnet-4-6": { "calls": 0, "tokens": 0, "estimated_cost": 0 },
    "anthropic/claude-haiku-4-5": { "calls": 0, "tokens": 0, "estimated_cost": 0 },
    "grok": { "calls": 0, "tokens": 0, "estimated_cost": 0 },
    "gemini": { "calls": 0, "tokens": 0, "estimated_cost": 0 }
  },
  "dailyBudget": {
    "openai": 10.0,
    "anthropic": 10.0,
    "free": 100.0
  },
  "alerts": []
}
EOF
fi

# Function to log a call
log_call() {
  local model=$1
  local tokens=$2
  local cost=$3
  
  # Update tracker (simplified; real implementation would use jq)
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $model — $tokens tokens (~\$$cost)" >> "$TRACKER_DIR/calls.log"
  
  # Alert if cost exceeds threshold
  if (( $(echo "$cost > 5.0" | bc -l) )); then
    echo "⚠️  High-cost call: $model cost \$$cost" >> "$TRACKER_DIR/alerts.log"
  fi
}

# Function to show daily summary
show_summary() {
  echo "📊 Cost Summary for $(date +%Y-%m-%d)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  tail -20 "$TRACKER_DIR/calls.log" 2>/dev/null | head -10
  echo ""
  echo "Recent alerts:"
  tail -5 "$TRACKER_DIR/alerts.log" 2>/dev/null || echo "None"
}

# CLI interface
case "${1:-summary}" in
  log)
    log_call "$2" "$3" "$4"
    ;;
  summary)
    show_summary
    ;;
  reset)
    rm -f "$TRACKER_FILE"
    echo "Reset tracker for today."
    ;;
  *)
    echo "Usage: cost-tracker.sh {log|summary|reset}"
    echo "  log <model> <tokens> <cost>  — Log an API call"
    echo "  summary                      — Show daily summary"
    echo "  reset                        — Reset today's tracker"
    ;;
esac
