#!/usr/bin/env bash
# Restrict HTTP/HTTPS ingress to Cloudflare's published IP ranges so the
# origin cannot be reached directly (Cloudflare WAF/proxy becomes mandatory).
# Run as root on the VPS:  sudo bash cloudflare-ufw.sh
# Idempotent: re-run any time to refresh the ranges (they change rarely).
# Touches ONLY ports 80/443 — SSH and everything else are left alone.
# TLS issuance is unaffected: Caddy uses the DNS-01 challenge, which needs
# no inbound connection from Let's Encrypt.
set -Eeuo pipefail

TAG="cloudflare-origin"

command -v ufw >/dev/null 2>&1 || { echo "ufw not installed" >&2; exit 1; }
ufw status | grep -q "Status: active" || { echo "ufw not active, aborting" >&2; exit 1; }

echo "==> fetching Cloudflare IP ranges"
V4="$(curl -fsS https://www.cloudflare.com/ips-v4)"
V6="$(curl -fsS https://www.cloudflare.com/ips-v6)"
[ -n "$V4" ] && [ -n "$V6" ] || { echo "empty range list, aborting" >&2; exit 1; }

echo "==> removing previous '$TAG' rules"
# Delete highest-numbered first so remaining rule numbers stay valid.
ufw status numbered \
	| grep -F "$TAG" \
	| sed -E 's/^\[ *([0-9]+)\].*/\1/' \
	| sort -rn \
	| while read -r num; do ufw --force delete "$num" >/dev/null; done

echo "==> allowing 80,443 only from Cloudflare"
for cidr in $V4 $V6; do
	ufw allow proto tcp from "$cidr" to any port 80,443 comment "$TAG" >/dev/null
done

echo "==> removing world-open 80/443 rules (if present)"
for rule in "80/tcp" "443/tcp" "80,443/tcp" "80" "443" "Caddy" "Nginx Full" "Apache Full" "WWW Full"; do
	ufw delete allow "$rule" >/dev/null 2>&1 || true
done

echo
ufw status | grep -E "(80|443)" || echo "WARN: no 80/443 rules found — check 'ufw status' manually"
echo
echo "DONE. Verify the site still loads: https://filipporadiceosteopata.com"
echo "Then confirm direct origin access is blocked: curl -m 5 http://<VPS_IP>/ (should time out)"
