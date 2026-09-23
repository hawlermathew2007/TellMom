#!/usr/bin/env bash
# Rolls the stack at /opt/tellmom forward to the IMAGE_TAG in .env. Run by the
# deploy workflow over SSH, after it has uploaded docker-compose.prod.yml and a
# fresh .env.
#
#   Usage: deploy.sh <ghcr-user>   (a registry token is read from stdin; empty = no login)
#
# On a failed check it puts the previous tag back and exits non-zero, so the
# workflow run goes red while the last good release keeps serving. The proxy's
# database lives on a volume; the proxy creates its table on start.
set -euo pipefail

cd "$(dirname "$0")"

compose=(docker compose -f docker-compose.prod.yml)
ghcr_user="${1:-}"

# Last assignment wins, and everything after the first '=' is the value.
env_value() {
    grep -E "^$1=" .env | tail -n1 | cut -d= -f2-
}

new_tag="$(env_value IMAGE_TAG)"
previous_tag="$(cat .current-tag 2>/dev/null || true)"
site_domain="$(env_value SITE_DOMAIN)"

echo "==> Deploying ${new_tag} (previous: ${previous_tag:-none})"

docker inspect -f '{{.State.Running}}' traefik 2>/dev/null | grep -qx true \
    || { echo "!! Traefik is not running; run the Ansible playbook first"; exit 1; }

# Read from stdin rather than $1, so the token never appears in `ps` or a log.
token="$(cat)"
if [[ -n "$token" ]]; then
    echo "$token" | docker login ghcr.io -u "$ghcr_user" --password-stdin >/dev/null
fi

pull_started=$SECONDS
pull_status=0
"${compose[@]}" pull --quiet || pull_status=$?
[[ -n "$token" ]] && docker logout ghcr.io >/dev/null
(( pull_status == 0 )) || { echo "!! pull failed"; exit "$pull_status"; }
echo "==> Pull took $((SECONDS - pull_started))s"

health() {
    local id
    id="$("${compose[@]}" ps --quiet "$1")"
    [[ -n "$id" ]] && docker inspect -f '{{.State.Health.Status}}' "$id"
}

# The proxy is what parents depend on, and the site is what visitors see; both
# gate the release. The playground is a demo: on a cold volume it spends minutes
# downloading its encoder, and a broken demo must not roll back a working proxy.
healthy() {
    for _ in $(seq 1 60); do
        if [[ "$(health proxy)" == healthy && "$(health web)" == healthy ]]; then
            return 0
        fi
        sleep 2
    done
    return 1
}

# Through Traefik, as a visitor would arrive. -k: the certificate is Traefik's
# self-signed default until DNS points here.
reachable() {
    local path
    for path in / /app/ /health; do
        curl -fsSk -o /dev/null --max-time 10 \
            --resolve "${site_domain}:443:127.0.0.1" "https://${site_domain}${path}" || return 1
    done
}

rollback() {
    echo "!! Release ${new_tag} failed"
    "${compose[@]}" logs --tail 80 proxy web || true

    if [[ -z "$previous_tag" || "$previous_tag" == "$new_tag" ]]; then
        echo "!! No previous release to roll back to"
        exit 1
    fi

    echo "==> Rolling back to ${previous_tag}"
    sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=${previous_tag}/" .env
    "${compose[@]}" up -d --remove-orphans
    exit 1
}

"${compose[@]}" up -d --remove-orphans || rollback
healthy || rollback
reachable || rollback

echo "$new_tag" > .current-tag

# Only this stack's images (labelled at build time) that no container uses.
docker image prune --all --force \
    --filter "label=org.opencontainers.image.vendor=tellmom" \
    --filter "until=240h" >/dev/null

echo "==> Playground: $(health playground || echo missing) (a cold start downloads the encoder; 'starting' is normal for a few minutes)"
echo "==> ${new_tag} is live"
