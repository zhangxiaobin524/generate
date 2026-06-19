FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
COPY list.html /usr/share/nginx/html/list.html
COPY libs /usr/share/nginx/html/libs

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
