FROM nginx:alpine

LABEL org.opencontainers.image.source=https://github.com/gurghet/github-deploy-key-operator

COPY README.md /usr/share/nginx/html/index.html
