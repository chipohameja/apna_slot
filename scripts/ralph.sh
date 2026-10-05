#!/usr/bin/env bash
# Runs an implementer agent (prompt.md) then a QA agent (qa_prompt.md) up to N times,
# stopping early as soon as either agent prints COMPLETE.
set -euo pipefail

if [[ $# -ne 1 || ! $1 =~ ^[0-9]+$ ]]; then
  echo "Usage: $0 <max-iterations>" >&2
  exit 1
fi

max_iterations=$1
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$script_dir/.."
source /workspace/development/frappe-bench/env/bin/activate

run_agent() {
  local name=$1 prompt_file=$2 output
  echo "--- $name agent ---"
  output=$(claude -p --dangerously-skip-permissions < "$prompt_file" | tee >(cat >&2))
  if grep -qE '^[[:space:]]*COMPLETE[[:space:]]*$' <<< "$output"; then
    echo "=== $name agent reported COMPLETE after $iteration iteration(s) ==="
    exit 0
  fi
}

for ((iteration = 1; iteration <= max_iterations; iteration++)); do
  echo "=== Iteration $iteration of $max_iterations ==="
  run_agent "Implementer" "$script_dir/prompt.md"
  run_agent "QA" "$script_dir/qa_prompt.md"
done

echo "=== Reached $max_iterations iteration(s) without COMPLETE ==="
