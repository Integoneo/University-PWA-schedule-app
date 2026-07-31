# ==========================================
# ЭТАП 1: Сборка (Builder - "Тяжелый" контейнер)
# ==========================================
FROM ubuntu:22.04 AS builder

# Отключаем интерактивы (чтобы apt-get не завис с вопросом "выберите часовой пояс")
ENV DEBIAN_FRONTEND=noninteractive

# Устанавливаем компиляторы, CMake и системные зависимости (RE2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    pkg-config \
    libre2-dev \
    && rm -rf /var/lib/apt/lists/*

# Создаем папку для сборки
WORKDIR /src

# Копируем ВЕСЬ исходный код проекта (включая libs, include, src)
COPY . .

# Собираем проект (Докер сам запустит CMake и скомпилирует всё)
# Флаг -j$(nproc) заставит компилятор использовать все ядра процессора для скорости
RUN cmake . && make -j"$(nproc)"


# ==========================================
# ЭТАП 2: Продакшен (Runtime - "Легкий" контейнер)
# ==========================================
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Устанавливаем ТОЛЬКО те системные библиотеки, которые нужны динамически при запуске
# libre2-9 — это рантайм-версия библиотеки RE2 для Ubuntu 22.04
# ca-certificates нужны, если воркер куда-то стучится по HTTPS
RUN apt-get update && apt-get install -y --no-install-recommends \
    libre2-9 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию для бинарника
WORKDIR /app

# МАГИЯ: Забираем только готовый экзешник из первого этапа
# По твоему CMakeLists он падает в папку exec/
COPY --from=builder /src/exec/worker .

# Запускаем чистый бинарник!
CMD ["./worker"]
