#!/usr/bin/env bash
# One-time VPS setup for the sito-filippo auto-deploy pipeline.
# Run as root on the Oracle VPS:  sudo bash vps-setup.sh
# Idempotent: safe to re-run. Interactive: pauses so you can register
# the GitHub deploy key before cloning.
set -Eeuo pipefail

REPO_SSH="git@github.com:Max-Pare/sito-filippo.git"
PROD_DIR=/srv/sito-filippo
STAGING_DIR=/srv/sito-filippo-staging
DEPLOY_USER=deploy

echo "==> 1/7 deploy user"
if ! id -u "$DEPLOY_USER" >/dev/null 2>&1; then
	useradd -m -s /bin/bash "$DEPLOY_USER"
fi
install -d -m 700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"

echo "==> 2/7 read-only GitHub deploy key (VPS -> GitHub, fetch only)"
GH_KEY="/home/$DEPLOY_USER/.ssh/github_deploy"
if [ ! -f "$GH_KEY" ]; then
	sudo -u "$DEPLOY_USER" ssh-keygen -t ed25519 -N '' -C "sito-filippo-vps-readonly" -f "$GH_KEY"
fi
cat > "/home/$DEPLOY_USER/.ssh/config" <<EOF
Host github.com
	IdentityFile $GH_KEY
	IdentitiesOnly yes
EOF
chown "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh/config"
chmod 600 "/home/$DEPLOY_USER/.ssh/config"
echo
echo "    Add this PUBLIC key on GitHub: repo -> Settings -> Deploy keys -> Add"
echo "    (title: vps-readonly, leave 'Allow write access' UNCHECKED)"
echo
cat "$GH_KEY.pub"
echo
read -rp "    Press enter once the deploy key is registered on GitHub... "

echo "==> 3/7 clones"
sudo -u "$DEPLOY_USER" ssh -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1 | head -1 || true
if [ ! -d "$PROD_DIR/.git" ]; then
	install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$PROD_DIR"
	sudo -u "$DEPLOY_USER" git clone --branch main "$REPO_SSH" "$PROD_DIR"
fi
if [ ! -d "$STAGING_DIR/.git" ]; then
	install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$STAGING_DIR"
	sudo -u "$DEPLOY_USER" git clone --branch staging "$REPO_SSH" "$STAGING_DIR"
fi
# Pre-existing clones may be owned by another user (e.g. ubuntu); deploy must own them
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$PROD_DIR" "$STAGING_DIR"
sudo -u "$DEPLOY_USER" bash "$PROD_DIR/install.sh"
sudo -u "$DEPLOY_USER" bash "$STAGING_DIR/install.sh"

echo "==> 4/7 deploy trigger script + sudoers"
install -m 755 "$PROD_DIR/deploy/sito-deploy" /usr/local/bin/sito-deploy
cat > /etc/sudoers.d/sito-deploy <<EOF
$DEPLOY_USER ALL=(root) NOPASSWD: /usr/bin/systemctl restart sito-filippo.service, /usr/bin/systemctl restart sito-filippo-staging.service, /usr/bin/systemctl status sito-filippo.service --no-pager, /usr/bin/systemctl status sito-filippo-staging.service --no-pager
EOF
chmod 440 /etc/sudoers.d/sito-deploy
visudo -c >/dev/null

echo "==> 5/7 systemd units"
install -m 644 "$PROD_DIR/deploy/sito-filippo.service" /etc/systemd/system/
install -m 644 "$PROD_DIR/deploy/sito-filippo-staging.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now sito-filippo.service sito-filippo-staging.service

echo "==> 6/7 GitHub Actions SSH key (GitHub -> VPS, deploy trigger only)"
GHA_KEY="/root/sito-filippo-actions-key"
if [ ! -f "$GHA_KEY" ]; then
	ssh-keygen -t ed25519 -N '' -C "sito-filippo-github-actions" -f "$GHA_KEY"
fi
AUTH_LINE="command=\"/usr/local/bin/sito-deploy\",restrict $(cat "$GHA_KEY.pub")"
AUTH_FILE="/home/$DEPLOY_USER/.ssh/authorized_keys"
touch "$AUTH_FILE"
grep -qF "$(cat "$GHA_KEY.pub")" "$AUTH_FILE" || echo "$AUTH_LINE" >> "$AUTH_FILE"
chown "$DEPLOY_USER:$DEPLOY_USER" "$AUTH_FILE"
chmod 600 "$AUTH_FILE"

echo "==> 7/7 caddy config"
install -m 644 "$PROD_DIR/deploy/Caddyfile" /etc/caddy/Caddyfile
systemctl reload caddy || echo "    WARN: caddy reload failed, check: journalctl -u caddy"

echo
echo "DONE. Now set these GitHub Actions secrets (repo -> Settings -> Secrets -> Actions):"
echo
echo "  DEPLOY_HOST        = this VPS public IP or hostname"
echo "  DEPLOY_SSH_KEY     = contents of $GHA_KEY   (the PRIVATE key, then delete it from the VPS)"
echo "  DEPLOY_KNOWN_HOSTS = output of: ssh-keyscan -t ed25519 <DEPLOY_HOST>"
echo
echo "And add a Cloudflare DNS record: staging.filipporadiceosteopata.com -> this VPS."
echo
echo "Test locally on the VPS:  sudo -u $DEPLOY_USER sito-deploy staging"
