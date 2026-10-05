# =============================================================================
# Frontend: React (Vite) single-page app.
# Multi-stage build: Node builds static files, nginx serves them (no Node and
# no dev server in the final image).
#
#   docker build -t traffic-law-frontend \
#       --build-arg VITE_API_URL=http://localhost:8000 ./frontend
#   docker run -p 3000:80 traffic-law-frontend
# =============================================================================

# ---- Stage 1: build ---------------------------------------------------------
# Debian-based (glibc) Node image: matches the @rollup/rollup-linux-x64-gnu
# native binary recorded in package-lock.json.
FROM node:20-slim AS build

WORKDIR /app

# Install exact versions from package-lock.json; cached until these files change.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Backend URL as seen from the *user's browser* (not from inside Docker).
# Vite inlines it into the JS bundle at build time, so changing it needs a rebuild.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# ---- Stage 2: serve ---------------------------------------------------------
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
