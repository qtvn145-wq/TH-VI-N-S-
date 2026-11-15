FROM nginx:stable-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/ /usr/share/nginx/html/ui/
RUN cp /usr/share/nginx/html/ui/index.html /usr/share/nginx/html/index.html
