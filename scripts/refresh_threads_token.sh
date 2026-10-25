#!/bin/bash
set -e

if [ -z "$1" ]; then
  echo "Usage: ./scripts/refresh_threads_token.sh <current_access_token>"
  exit 1
fi

CURRENT_TOKEN="$1"

echo "Refreshing Threads token..."
RESPONSE=$(curl -s "https://graph.threads.net/refresh_access_token?grant_type=th_refresh_token&access_token=${CURRENT_TOKEN}")

NEW_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['access_token'])" 2>/dev/null)
EXPIRES_IN=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['expires_in'])" 2>/dev/null)

if [ -z "$NEW_TOKEN" ]; then
  echo "Error: $RESPONSE"
  exit 1
fi

EXPIRY_DATE=$(python3 -c "from datetime import datetime, timedelta; print((datetime.now() + timedelta(seconds=${EXPIRES_IN})).strftime('%Y-%m-%d'))")

echo ""
echo "New token:   $NEW_TOKEN"
echo "Expiry date: $EXPIRY_DATE"
echo ""

if command -v gh &>/dev/null; then
  read -p "Tự động update GitHub Secrets? (y/n): " CONFIRM
  if [ "$CONFIRM" = "y" ]; then
    REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
    gh secret set THREADS_ACCESS_TOKEN --body "$NEW_TOKEN" --repo "$REPO"
    gh secret set THREADS_TOKEN_EXPIRY --body "$EXPIRY_DATE" --repo "$REPO"
    echo "GitHub Secrets updated for $REPO"
  fi
else
  echo "Cập nhật thủ công vào GitHub Secrets:"
  echo "  THREADS_ACCESS_TOKEN = $NEW_TOKEN"
  echo "  THREADS_TOKEN_EXPIRY = $EXPIRY_DATE"
fi
