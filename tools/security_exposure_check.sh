#!/usr/bin/env bash
# security_exposure_check.sh - checks whether a live domain exposes sensitive files.
# Usage: ./security_exposure_check.sh peticila.ro [aponia.ro ...]
# Exit 1 if ANY sensitive path returns 200. Run after every deploy.

set -u
PATHS=(.env .git/config .git/HEAD wp-config.php config.json composer.json .env.local backup.sql .DS_Store)
fail=0

for host in "$@"; do
  host="${host#https://}"; host="${host#http://}"; host="${host%/}"
  echo "→ $host"
  for p in "${PATHS[@]}"; do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "https://$host/$p" 2>/dev/null)
    if [ "$code" = "200" ]; then
      echo "  ❌ EXPOSED: /$p (HTTP 200)"
      fail=1
    elif [ "$code" = "000" ]; then
      echo "  ⚠️  INCONCLUSIVE: /$p (no connection: firewall/DNS/offline)"
      fail=2
    else
      echo "  ✅ /$p → $code"
    fi
  done
done

[ "$fail" -eq 1 ] && { echo "FAIL: sensitive files exposed."; exit 1; }
[ "$fail" -eq 2 ] && { echo "INCONCLUSIVE: no connection, could not test. Do NOT declare clean."; exit 2; }
echo "OK: nothing exposed."
