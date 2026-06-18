FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html
COPY list.html /usr/share/nginx/html/list.html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
