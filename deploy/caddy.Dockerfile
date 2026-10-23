# Caddy do perfil lan, como UID 1000 (SEC-23).
# Volume novo herda o dono de /data da imagem; por isso o chown aqui.
# O binário da imagem oficial já tem cap_net_bind_service para escutar na 443.
FROM caddy:2.11-alpine@sha256:eb4d35b7452d1ab6171fbdbe8d9275b2301dad6dad92115d91e19fb9b24d510f
RUN chown -R 1000:1000 /data /config
USER 1000:1000
