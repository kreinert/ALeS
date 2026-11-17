#!/bin/bash
# Usage: eval_compare.sh <binary> <tries> <label> <args...>
BIN="$1"; TRIES="$2"; LABEL="$3"; shift 3
OUT="eval_${LABEL}_$(basename "$BIN").log"
ALESC_MAX_TRIES="$TRIES" "$BIN" "$@" >"$OUT" 2>&1
BEST=$(grep -o 'Best sensitivity is [-0-9.]*' "$OUT" | tail -1 | awk '{print $4}')
TIME=$(grep -o 'Computed in [-0-9.]* seconds' "$OUT" | tail -1 | awk '{print $3}')
TOTAL=$(grep -o 'Total time ([^)]*): [-0-9.]* seconds' "$OUT" | tail -1 | sed 's/.*: //; s/ seconds//')
echo "$LABEL $(basename "$BIN") best=$BEST time=${TIME}s total=${TOTAL}s args=[$*]"
