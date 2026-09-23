# Deploying TellMom

```
push to main ─► CI ─► build proxy/playground/web ─► GHCR ─► ssh deploy@vps deploy.sh
                                                              │
                     pull ─► up -d ─► proxy + web healthy, reachable via Traefik? ─┬─ yes: done
                                                                                  └─ no: previous tag back up, run fails
```

This deploys the public half of TellMom only. Parents' servers (backend,
classifier, adapters) run at home and dial out to the proxy deployed here.

| Service | Image | What it is |
|---|---|---|
| `web` | `deploy/web.Dockerfile` | the website (`site/`) at `/`, the dashboard (`frontend/`) at `/app/` |
| `proxy` | `deploy/proxy.Dockerfile` | the Leesin proxy: relays sealed traffic, stores server accounts |
| `postgres` | `postgres:16-alpine` | the proxy's one table, `servers`: id, username, bcrypt hash |
| `playground` | `deploy/playground.Dockerfile` | the website's demo classifier (`classifier/serve.py`) |

Traefik runs beside the stack, installed and kept running by
`deploy/ansible/`. It owns 80/443, gets Let's Encrypt certificates, and routes
by the labels in `docker-compose.prod.yml`:

| Path on `SITE_DOMAIN` | Goes to |
|---|---|
| `/session/`, `/auth/`, `/stream`, `/health` | `proxy` (WebSockets included) |
| `/api/playground/` | `playground`, prefix stripped, rate-limited to 2 req/s per visitor (burst 10) |
| everything else | `web` |

## First-time setup

1. Point DNS for your domain at the VPS.
2. Create a deploy key: `ssh-keygen -t ed25519 -f ~/.ssh/tellmom-deploy -C tellmom-deploy`.
3. Provision the VPS (Docker, the `deploy` user, `/opt/tellmom`, Traefik):
   ```sh
   cd deploy/ansible
   cp inventory.example.ini inventory.ini   # host, Let's Encrypt email, key path
   ansible-galaxy collection install -r requirements.yml
   ansible-playbook -i inventory.ini playbook.yml
   ```
   Re-run it any time; it starts Traefik only if Traefik isn't running or its
   config changed.
4. In GitHub → Settings → Environments → `production`:

   | kind | name | value |
   |---|---|---|
   | secret | `VPS_SSH_KEY` | contents of `~/.ssh/tellmom-deploy` |
   | secret | `VPS_KNOWN_HOSTS` | `ssh-keyscan -p 22 <host>` |
   | secret | `PROD_ENV_FILE` | `deploy/.env.example`, filled in |
   | var | `VPS_HOST` | host or IP |
   | var | `VPS_PORT` | optional, default 22 |
   | var | `PUBLIC_URL` | `https://<SITE_DOMAIN>`, baked into the dashboard |

5. Push to `main`, or run **Deploy** by hand.

## Day to day

- **Release**: merge to `main`.
- **Roll back**: Actions → Deploy → Run workflow → `image_tag` = an earlier commit SHA.
- **Change a setting**: edit `PROD_ENV_FILE`, re-run the latest Deploy.
- **Logs**: `ssh deploy@vps 'cd /opt/tellmom && docker compose -f docker-compose.prod.yml logs -f proxy'`.
- **Tag a release**: `git tag -a v1.0.0 -m v1.0.0 && git push origin v1.0.0`.

## Worth knowing

- **The playground never gates a release.** Its first start downloads the
  SimCSE encoder into the `models` volume (a few minutes); `deploy.sh` waits on
  `proxy` and `web` only. It keeps no data and logs no request bodies.
- **A redeploy drops live sessions briefly.** Home servers reconnect on their
  own; an open dashboard has to connect again.
- **Back up the `tellmom_pgdata` volume** if you don't want home servers to
  register again after losing the box. It never holds chats or alerts.
- **Step recordings** for the build guide go in `site/public/media/` as
  `01-server` … `05-monitor`, `.webm` and/or `.mp4`.
- **Run the playground locally**: `cd classifier && uv run serve.py`, serve
  `site/`, and open it with `?playground=http://localhost:8090`.
