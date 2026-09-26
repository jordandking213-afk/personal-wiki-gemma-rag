#!/bin/bash
# Offline demonstration: run with Wi-Fi OFF, inside a screen recording.
#   ./tools/offline_demo.sh
# Everything printed is also saved to evidence/offline-run/terminal-log.txt.
cd "$(dirname "$0")/.." || exit 1
OUT=evidence/offline-run
mkdir -p "$OUT"

if [ -z "$OFFLINE_DEMO_LOGGING" ]; then
  export OFFLINE_DEMO_LOGGING=1
  exec script -q "$OUT/terminal-log.txt" "$0" "$@"
fi

step() { printf '\n\033[1m==== %s ====\033[0m\n' "$1"; }
run() { printf '\n$ %s\n' "$*"; "$@"; }

step "1. Internet check (must be OFFLINE)"
date
if curl -s -m 5 -o /dev/null https://ollama.com; then
  echo "INTERNET IS CONNECTED. Turn Wi-Fi off and run this script again."
  exit 1
fi
echo "OFFLINE confirmed: https://ollama.com is unreachable."
route -n get default 2>&1 | grep -E "interface|not in table" || true

step "2. Device and model"
sw_vers
sysctl -n machdep.cpu.brand_string
echo "RAM: $(( $(sysctl -n hw.memsize) / 1073741824 )) GB unified memory"
df -h ~ | tail -1 | awk '{print "Free disk: " $4}'
memory_pressure | tail -1
ollama --version 2>/dev/null
python3 --version

step "3. Restart Ollama (local server only)"
pkill -f "ollama serve" 2>/dev/null; pkill -f "ollama/llama-server" 2>/dev/null; sleep 2
ollama serve > data/logs/ollama-offline.log 2>&1 &
for i in $(seq 1 30); do curl -s -o /dev/null localhost:11434 && break; sleep 1; done
run ollama list

step "4. Help"
run ./wiki --help

step "5. Ingest (Gemma re-reads every source; reviewed pages are kept, drafts saved)"
run ./wiki ingest vault/raw --force

step "6. Search mode (no model call)"
run ./wiki search "living sacrifice"

step "7. Ask-mode tests"
run ./wiki ask "What are the three groans in Romans 8:18-30?"
run ./wiki ask "Why couldn't the Jewish law bring Israel to salvation?"
run ./wiki ask "How does Romans 8:1 fit into the \"therefore\" passages in Romans, and what does Romans 8 say that freedom looks like?"
run ./wiki ask "Who wrote the book of Romans?"

step "8. Chat mode checks (you type these)"
cat <<'EOF'
Type each line below, one at a time, waiting for each reply:
  1) what can we do?
  2) what can you help me with?
  3) Give me a short 3-step plan for a small group discussion on Romans 12.
  4) make that shorter
  5) Just so you know, our study group meets on Tuesdays.
  6) /exit
EOF
run ./wiki chat

step "9. Chat claim is not ask evidence"
run ./wiki ask "When does the study group meet?"

step "10. Memory after the run"
python3 -c "from wiki_cli import llm; print(llm.memory_snapshot())"
echo
echo "Done. Stop the screen recording. Log: $OUT/terminal-log.txt"
