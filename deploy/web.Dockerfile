# The public website (site/) at / and the parent dashboard (frontend/) at /app/,
# served by a small nginx behind Traefik.
#
#   docker build -f deploy/web.Dockerfile --build-arg PUBLIC_URL=https://tellmom.example.com -t tellmom-web .

FROM node:22-slim AS build

# Baked into the dashboard bundle: the proxy it tunnels through, which is the
# site's own origin. Changing it is a rebuild rather than a restart.
ARG PUBLIC_URL=http://localhost:8080
ENV VITE_API_URL=$PUBLIC_URL \
    VITE_BASE=/app/

WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM nginx:1.27-alpine AS runtime

COPY deploy/web.nginx.conf /etc/nginx/conf.d/default.conf
COPY site/ /usr/share/nginx/html/
COPY --from=build /src/dist /usr/share/nginx/html/app

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
