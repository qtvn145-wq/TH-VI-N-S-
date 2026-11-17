FROM nginx:stable-alpine
COPY devops/deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/index.html frontend/config.js /usr/share/nginx/html/ui/
COPY frontend/src/ /usr/share/nginx/html/ui/src/
COPY frontend/styles/ /usr/share/nginx/html/ui/styles/
RUN cp /usr/share/nginx/html/ui/index.html /usr/share/nginx/html/index.html
