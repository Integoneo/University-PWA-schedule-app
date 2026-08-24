FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci 
COPY . .
RUN npm run build

# ЭТАП 2: Раздаем через Nginx
FROM nginx:alpine
# Удаляем стандартный конфиг Nginx
RUN rm /etc/nginx/conf.d/default.conf
# Копируем наш конфиг
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Забираем собранный dist из первого этапа
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
