# Deploy pipeline

## How changes reach production

```
Filippo (claude.ai/code)          Max
        │                          │
        ▼                          │
   PR on GitHub ──── review ───────┤
                                   ▼
                        merge into `staging`
                                   │
                     GitHub Action │ ssh → sito-deploy staging
                                   ▼
                 https://staging.filipporadiceosteopata.com
                                   │
                    Filippo approves the preview
                                   │
                                   ▼
                          merge into `main`
                                   │
                     GitHub Action │ ssh → sito-deploy prod
                                   ▼
                     https://filipporadiceosteopata.com
```

- `main` = production, `staging` = preview. Both auto-deploy on push
  (`.github/workflows/deploy.yml`).
- Nobody pushes to `main` directly; changes arrive as PRs and Max merges.

## Pieces

| File | Purpose | Lives at (VPS) |
|---|---|---|
| `sito-filippo.service` | prod gunicorn unit, port 8080 | `/etc/systemd/system/` |
| `sito-filippo-staging.service` | staging gunicorn unit, port 8081 | `/etc/systemd/system/` |
| `sito-deploy` | pull + install + restart + health check | `/usr/local/bin/sito-deploy` |
| `vps-setup.sh` | one-time provisioning (run as root) | — |
| `Caddyfile` | prod + staging site blocks | `/etc/caddy/Caddyfile` |

## Keys (least privilege)

- **GitHub Actions → VPS**: SSH key locked in `authorized_keys` with
  `command="/usr/local/bin/sito-deploy",restrict` — it can only trigger a
  deploy, no shell, no forwarding. Restart rights granted via a sudoers
  entry scoped to the two service restarts.
- **VPS → GitHub**: read-only repo deploy key, fetch only.
- Max's personal key/access is unchanged and remains the only interactive
  SSH access.

## One-time setup

1. Copy `vps-setup.sh` to the VPS, run `sudo bash vps-setup.sh`, follow the
   prompts (it prints the GitHub deploy key to register, then the three
   Actions secrets to set: `DEPLOY_HOST`, `DEPLOY_SSH_KEY`,
   `DEPLOY_KNOWN_HOSTS`).
2. Cloudflare: add DNS record `staging` → VPS IP.
3. GitHub: branch protection on `main` (require PR review). Note: on a free
   plan this requires the repo to be public.
4. Onboard Filippo: GitHub account → add as repo collaborator → he connects
   it in claude.ai/code (Claude Pro needed).

## Day-to-day

- Deploy fails → check the Actions run log; on the VPS:
  `journalctl -u sito-filippo -e` (or `-staging`).
- Manual deploy from the VPS: `sudo -u deploy sito-deploy prod|staging`.
- Roll back: revert the merge commit on `main`, push — the Action redeploys.
- Refresh `staging` after prod changes: merge `main` into `staging`, push.
