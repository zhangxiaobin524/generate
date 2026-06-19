FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
COPY list.html /usr/share/nginx/html/list.html
COPY login.html /usr/share/nginx/html/login.html
COPY account-generator.html /usr/share/nginx/html/account-generator.html
COPY report-list.html /usr/share/nginx/html/report-list.html
COPY mobile-verify.html /usr/share/nginx/html/mobile-verify.html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
