# Contexto de build = raiz do repo: docker build -f frontend/Dockerfile .
# Build Node + runtime nginx. Bases fixadas por digest (SEC-21).
FROM node:24-alpine@sha256:06d7adf3e0ef61a13f1d28682726366f97a15aa1888c934d3ecec86c33918b53 AS build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json frontend/.npmrc ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

FROM nginx:1.29-alpine@sha256:5616878291a2eed594aee8db4dade5878cf7edcb475e59193904b198d9b830de

# UID 1000 sem root (SEC-23). Só o nginx.conf e o build entram; /tmp guarda pid e temporários.
COPY deploy/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html

USER 1000:1000
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
