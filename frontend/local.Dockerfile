FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build


# ЭТАП 2: Nginx
FROM nginx:alpine
RUN rm /etc/nginx/conf.d/default.conf
# Копируем именно локальный конфиг
COPY nginx.local.conf /etc/nginx/conf.d/default.conf
# Забираем dist
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
