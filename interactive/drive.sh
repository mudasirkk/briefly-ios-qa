#!/usr/bin/env bash
# Thin client for the interactive iOS control server (see control_server.py).
# Usage: drive.sh <TUNNEL_URL> <cmd> [args...]
#   shot <out.png>              GET /screenshot -> file (then Read it)
#   describe                    GET /describe   -> a11y tree JSON (frames in points)
#   tap <x> <y>                 POST /tap       (PIXEL coords, matches the screenshot)
#   text <string>              POST /text
#   swipe <x1> <y1> <x2> <y2> [dur]
#   openurl <url>              POST /openurl
#   appearance <light|dark>    POST /appearance
#   button <HOME|LOCK|...>     POST /button
#   health                     GET /health
#
# Token: reads $INTERACTIVE_TOKEN, else the local scratchpad itoken.txt if present.
set -euo pipefail

URL="${1:?tunnel url required}"; shift
CMD="${1:?command required}"; shift || true

TOKEN="${INTERACTIVE_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  for f in "$HOME"/AppData/Local/Temp/claude/*/*/scratchpad/itoken.txt; do
    [ -f "$f" ] && TOKEN="$(cat "$f")" && break
  done
fi
H=(-H "X-Token: $TOKEN")

case "$CMD" in
  shot)      curl -s "${H[@]}" "$URL/screenshot" -o "${1:?out.png required}" && echo "saved ${1}" ;;
  describe)  curl -s "${H[@]}" "$URL/describe" ;;
  health)    curl -s "${H[@]}" "$URL/health"; echo ;;
  tap)       curl -s "${H[@]}" -X POST "$URL/tap" -d "{\"x\":${1:?x},\"y\":${2:?y}}"; echo ;;
  text)      curl -s "${H[@]}" -X POST "$URL/text" -d "{\"text\":\"${1:?text}\"}"; echo ;;
  swipe)     curl -s "${H[@]}" -X POST "$URL/swipe" -d "{\"x1\":${1:?},\"y1\":${2:?},\"x2\":${3:?},\"y2\":${4:?},\"duration\":${5:-0.3}}"; echo ;;
  openurl)   curl -s "${H[@]}" -X POST "$URL/openurl" -d "{\"url\":\"${1:?url}\"}"; echo ;;
  appearance)curl -s "${H[@]}" -X POST "$URL/appearance" -d "{\"value\":\"${1:?light|dark}\"}"; echo ;;
  button)    curl -s "${H[@]}" -X POST "$URL/button" -d "{\"name\":\"${1:?name}\"}"; echo ;;
  *) echo "unknown command: $CMD" >&2; exit 2 ;;
esac
