FROM node:24-alpine AS build

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
ENV VITE_API_BASE_URL=/api
RUN npm run build

FROM nginx:1.29-alpine
ENV BACKEND_UPSTREAM=backend:8000
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
