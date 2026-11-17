#!/bin/bash
# Aggregate best sensitivity from evaluation logs.
for prefix in "$@"; do
  vals=""
  for f in eval_${prefix}*_ALeSc*.log; do
    [ -f "$f" ] || continue
    b=$(grep -o 'Best sensitivity is [-0-9.]*' "$f" | tail -1 | awk '{print $4}')
    [ -n "$b" ] && vals="$vals $b"
  done
  mean=$(echo $vals | awk '{s=0; for(i=1;i<=NF;i++) s+=$i; printf "%.6f", s/NF}')
  echo "$prefix: n=$(echo $vals | wc -w | tr -d ' ') mean=$mean vals:$vals"
done
