# Kosyga.Space — Frontend PWA

> **Для AI-агентов:** Этот файл является полным справочником кодовой базы. Он описывает все компоненты, composables, сервисы, маршруты, store, API и конфигурации проекта. Используйте его как источник истины при навигации по коду.

---

## Содержание

1. [Общее описание](#1-общее-описание)
2. [Стек технологий](#2-стек-технологий)
3. [Структура проекта](#3-структура-проекта)
4. [NPM-скрипты](#4-npm-скрипты)
5. [Зависимости](#5-зависимости)
6. [Переменные окружения и localStorage](#6-переменные-окружения-и-localstorage)
7. [Маршрутизация (`router/index.ts`)](#7-маршрутизация)
8. [Глобальный стор (`store.ts`)](#8-глобальный-стор)
9. [API-сервис (`api/index.ts`)](#9-api-сервис)
10. [Vue-компоненты](#10-vue-компоненты)
    - [Оболочка приложения](#оболочка-приложения)
    - [Онбординг](#онбординг)
    - [Расписание студента](#расписание-студента)
    - [Подкомпоненты расписания](#подкомпоненты-расписания)
    - [Расписание преподавателя](#расписание-преподавателя)
    - [Поиск](#поиск)
    - [Настройки, профиль, прочее](#настройки-профиль-прочее)
11. [Composables (кастомные хуки)](#11-composables)
12. [Конфигурация PWA](#12-конфигурация-pwa)
13. [Конфигурационные файлы](#13-конфигурационные-файлы)
14. [Docker и Nginx](#14-docker-и-nginx)
15. [Типы и интерфейсы](#15-типы-и-интерфейсы)
16. [Архитектурные решения](#16-архитектурные-решения)
17. [Известные заглушки и ограничения](#17-известные-заглушки-и-ограничения)

---

## 1. Общее описание

**Kosyga.Space** — прогрессивное веб-приложение (PWA) для просмотра расписания занятий РГУ им. А.Н. Косыгина. Предоставляет нативный мобильный UX: офлайн-режим, установка на экран, обновление через сервис-воркер.

- **Язык интерфейса:** русский
- **Целевая аудитория:** студенты и преподаватели РГУ им. А.Н. Косыгина
- **Домен:** kosyga.ru 

---

## 2. Стек технологий

| Слой | Технология |
|------|-----------|
| UI-фреймворк | Vue 3 (`<script setup>` Composition API) + TypeScript |
| Маршрутизация | Vue Router 5 (`createWebHistory`) |
| Стилизация | Tailwind CSS v4 (с кастомными CSS-токенами) |
| Сборка | Vite 8 |
| PWA | `vite-plugin-pwa` (Workbox под капотом) |
| Состояние | Единый `reactive` стор (без Pinia/Vuex) + localStorage |
| HTTP | Нативный `fetch` с офлайн-кешированием |
| Deploy | Docker (multi-stage) → Nginx → Статика + reverse proxy к FastAPI `:8000` |

---

## 3. Структура проекта

```
frontend/
├── index.html                      # Точка входа: мета PWA, иконки, <div id="app">
├── package.json
├── package-lock.json
├── vite.config.ts                  # Vue + Tailwind v4 + VitePWA + dev-proxy
├── tsconfig.json                   # Ссылки на tsconfig.app.json и tsconfig.node.json
├── tsconfig.app.json               # TS для приложения (DOM, vite/client, pwa-client)
├── tsconfig.node.json              # TS для vite.config.ts (NodeNext)
├── prod.Dockerfile                 # Multi-stage: npm ci → build → nginx alpine
├── local.Dockerfile                # Аналог для локальной разработки
├── nginx.conf                      # Prod: HTTPS, HSTS, bot-фильтр, no-cache для SW
├── nginx.local.conf                # Local: HTTP, no-cache для SW, proxy к backend
└── src/
    ├── main.ts                     # Точка входа Vue: createApp + router + overlayManager.init
    ├── App.vue                     # Корневой компонент: навбар, тосты, модалки, PWA-баннер
    ├── style.css                   # CSS-токены + Tailwind @theme + PWA-локи прокрутки
    ├── store.ts                    # Глобальный reactive стор + localStorage
    ├── api/
    │   └── index.ts                # HTTP-клиент, кеширование, device ID
    ├── router/
    │   └── index.ts                # Маршруты + навигационный guard
    ├── config/
    │   └── changelog.ts            # CURRENT_VERSION + история изменений
    ├── assets/
    │   ├── vue.svg
    │   └── vite.svg
    ├── components/
    │   ├── App.vue                 # (см. src/App.vue)
    │   ├── Welcome.vue             # Лендинг/приветствие
    │   ├── Onboarding.vue          # Выбор группы (многошаговый)
    │   ├── Schedule.vue            # Расписание студента (оркестратор)
    │   ├── TeacherSchedule.vue     # Расписание преподавателя (вложен в Schedule)
    │   ├── Exams.vue               # Заглушка «Экзамены в разработке»
    │   ├── Search.vue              # Поиск групп и преподавателей
    │   ├── Settings.vue            # Настройки: профиль, шаринг, о приложении
    │   ├── Profile.vue             # Профиль: группы, избранное, кеш
    │   ├── Changelog.vue           # Полный список изменений (страница)
    │   ├── ChangelogModal.vue      # Модальное окно изменений (через overlayManager)
    │   ├── Modal.vue               # Глобальный диалог подтверждения
    │   ├── BottomSheet.vue         # Нижний лист (drag-to-dismiss)
    │   ├── schedule/               # Подкомпоненты расписания (см. §10)
    │   │   ├── ScheduleHeader.vue
    │   │   ├── WeekDayPicker.vue
    │   │   ├── ScheduleBody.vue
    │   │   ├── LessonCard.vue
    │   │   ├── SwipeGuide.vue
    │   │   ├── GroupInfoSheet.vue
    │   │   ├── ExcelModal.vue
    │   │   ├── TeacherScheduleHeader.vue
    │   │   ├── TeacherScheduleBody.vue
    │   │   └── TeacherLessonCard.vue
    │   └── search/
    │       └── SearchResultList.vue
    └── composables/
        ├── useOverlayManager.ts         # Очередь оверлеев (FIFO singleton)
        ├── useChangelogDetector.ts      # Детектор новых версий
        └── schedule/
            ├── useScheduleData.ts       # Данные расписания студента
            ├── useTeacherScheduleData.ts # Данные расписания преподавателя
            ├── useWeekNavigation.ts     # Навигация по неделям + свайп + клавиши
            ├── useMidnightReset.ts      # Сброс даты в полночь
            └── useTeacherMath.ts        # Группировка и расчёт накладок у преподавателя
```

---

## 4. NPM-скрипты

| Скрипт | Команда | Описание |
|--------|---------|----------|
| `dev` | `vite` | Запуск dev-сервера с HMR |
| `build` | `vue-tsc -b && vite build` | Тайпчек + production-сборка в `dist/` |
| `preview` | `vite preview` | Предпросмотр production-сборки |

---

## 5. Зависимости

### Runtime (`dependencies`)

| Пакет | Версия | Роль |
|-------|--------|------|
| `vue` | ^3.5.39 | UI-фреймворк |
| `vue-router` | ^5.1.0 | SPA-маршрутизация |
| `@tailwindcss/vite` | ^4.3.2 | Tailwind v4 как Vite-плагин |

### Dev (`devDependencies`)

| Пакет | Версия | Роль |
|-------|--------|------|
| `vite` | ^8.1.1 | Сборщик |
| `@vitejs/plugin-vue` | ^6.0.7 | Поддержка Vue SFC |
| `vite-plugin-pwa` | ^1.3.0 | Сервис-воркер + web manifest |
| `vite-plugin-mkcert` | — | Локальный HTTPS (опционально) |
| `@vitejs/plugin-basic-ssl` | — | Альтернативный локальный HTTPS |
| `typescript` | ~6.0.2 | Типизация |
| `vue-tsc` | ^3.3.5 | Тайпчек Vue SFC |
| `tailwindcss` | ^4.3.2 | CSS-утилиты |
| `postcss` / `autoprefixer` | — | CSS-постобработка |
| `@types/node` | — | Node.js типы |
| `@vue/tsconfig` | — | Базовый tsconfig для Vue |

---

## 6. Переменные окружения и localStorage

### Переменные окружения (`.env`)

| Переменная | По умолчанию | Назначение |
|------------|-------------|------------|
| `VITE_API_URL` | `/api/v1/client` | Базовый URL API. В проде — через nginx proxy; в dev — через `vite.config.ts` proxy |

> Файл `.env` не хранится в репозитории (`.clineignore`).

### Ключи localStorage (персистентное состояние)

| Ключ | Тип | Назначение |
|------|-----|-----------|
| `app_data_version` | string | Версия схемы данных; при изменении `DATA_VERSION` в `store.ts` — чистит пользовательские данные |
| `user_group` | JSON | Основная группа пользователя (объект группы) |
| `user_favorites` | JSON | Массив избранных групп |
| `user_favorite_teachers` | JSON | Массив избранных преподавателей |
| `user_device_id` | UUID | Идентификатор устройства (из `/stats/install`) |
| `api_config` | JSON | Кеш конфигурации семестра |
| `api_institutes` | JSON | Кеш списка институтов с группами |
| `api_teachers` | JSON | Кеш списка преподавателей |
| `api_schedule_{groupId}` | JSON | Кеш расписания группы |
| `api_teacher_schedule_{teacherId}` | JSON | Кеш расписания преподавателя |
| `pwa_install_pending` | boolean | Ожидает синхронизации статистики установки |
| `pwa_install_retry_after` | timestamp | Когда повторить синхронизацию |
| `pwa_prompt_count` | number | Счётчик показов предложения установки |
| `pwa_prompt_ignored` | boolean | Пользователь отклонил установку |
| `has_seen_swipe_guide` | boolean | Показывалась ли подсказка по свайпу |
| `last_seen_version` | string | Последняя виденная версия (для changelog) |
| `changelog_v1_shown` | boolean | Специальный флаг для v1.0.0 |

---

## 7. Маршрутизация

**Файл:** `src/router/index.ts`  
**Режим истории:** `createWebHistory`

| Путь | Имя | Компонент | `meta.hideNavbar` |
|------|-----|-----------|:-----------------:|
| `/` | — | redirect → `/lessons` | — |
| `/welcome` | `Welcome` | `Welcome.vue` | ✓ |
| `/onboarding` | `Onboarding` | `Onboarding.vue` | ✓ |
| `/lessons` | `Schedule` | `Schedule.vue` | — |
| `/exams` | `Exams` | `Exams.vue` | — |
| `/search` | `Search` | `Search.vue` | — |
| `/settings` | `Settings` | `Settings.vue` | — |
| `/profile` | `Profile` | `Profile.vue` | ✓ |
| `/changelog` | `Changelog` | `Changelog.vue` | ✓ |

### Навигационный guard (`beforeEach`)

- **Группа выбрана** (`store.groupInfo` != null):
  - Попытка перейти на `/welcome` или `/onboarding` → редирект на `/lessons`
- **Группа не выбрана:**
  - Разрешены только `/welcome` и `/onboarding`
  - Любой другой маршрут → редирект на `/welcome`

---

## 8. Глобальный стор

**Файл:** `src/store.ts`

Реализован как единый Vue `reactive` объект. Нет Pinia/Vuex. Персистентность через `localStorage`.

### Константа `DATA_VERSION = '1'`

При несовпадении сохранённой версии стор очищает все пользовательские данные (кроме `api_*` и `user_device_id`), затем перезаписывает версию.

### Поля состояния

| Поле | Тип | Описание |
|------|-----|----------|
| `groupInfo` | `GroupInfo \| null` | Основная группа (персистентна) |
| `currentViewingGroup` | `GroupInfo \| null` | Группа, просматриваемая сейчас (может отличаться от основной) |
| `viewContext` | `'main' \| 'favorite' \| 'guest'` | Контекст просмотра расписания |
| `currentViewingTeacher` | `{ id, name } \| null` | Если задан — Schedule показывает TeacherSchedule |
| `favorites` | `GroupInfo[]` | Избранные группы (персистентны) |
| `favoriteTeachers` | `{ id, name }[]` | Избранные преподаватели (персистентны) |
| `deferredPrompt` | `BeforeInstallPromptEvent \| null` | Перехваченное событие установки PWA |
| `toasts` | `Toast[]` | Очередь тостов (макс. 3, авто-удаление через 3 с) |
| `modal` | `ModalConfig \| null` | Конфиг глобального диалога подтверждения |

### Методы стора

| Метод | Описание |
|-------|----------|
| `setGroup(group)` | Установить основную группу; сохранить в localStorage |
| `setViewingGroup(group, context)` | Установить просматриваемую группу |
| `resetToMainGroup()` | Сбросить к основной группе |
| `setViewingTeacher(teacher)` | Включить режим просмотра преподавателя |
| `clearViewingTeacher()` | Выйти из режима преподавателя |
| `clearGroup()` | Очистить основную группу (для смены группы) |
| `toggleFavorite(group)` | Добавить/удалить группу из избранного |
| `isFavorite(groupId)` | Проверить, в избранном ли группа |
| `toggleFavoriteTeacher(teacher)` | Добавить/удалить преподавателя из избранного |
| `isFavoriteTeacher(teacherId)` | Проверить, в избранном ли преподаватель |
| `addToast(message, type?)` | Показать тост-уведомление |
| `removeToast(id)` | Удалить тост |
| `showModal(config)` | Показать глобальный диалог |
| `closeModal()` | Закрыть диалог |

### Объект группы (`GroupInfo`)

```ts
{
  group_id: number
  group_name: string
  institute_full_name: string
  institute_short_name: string
  study_form: string           // нормализуется через normalizeStudyForm()
  file_title: string
  logo_url: string
}
```

---

## 9. API-сервис

**Файл:** `src/api/index.ts`

- **Базовый URL:** `import.meta.env.VITE_API_URL` или `/api/v1/client`
- **Заголовок:** `X-Device-ID` (UUID из `localStorage.user_device_id`), кроме `/stats/install`
- **Офлайн-стратегия:** сначала сеть; при ошибке — возврат из localStorage-кеша (кроме 404)

### Методы API

| Метод | HTTP | Endpoint | Кеш-ключ | Описание |
|-------|------|----------|----------|----------|
| `syncInstallStats()` | POST | `/stats/install` | — | Синхронизация статистики установки; возвращает `device_id` |
| `getConfig()` | GET | `/config` | `api_config` | Конфиг семестра: `{ anchorDate, isEven }` |
| `getInstitutes()` | GET | `/institutes` | `api_institutes` | Список институтов с вложенными группами |
| `getGroupSchedule(groupId)` | GET | `/groups/{id}/lessons` | `api_schedule_{id}` | Расписание группы + даты + `view_url`; `meta: updated\|actual\|offline` |
| `getTeachers()` | GET | `/teachers` | `api_teachers` | Список преподавателей `{ id, name }[]` |
| `getTeacherSchedule(teacherId)` | GET | `/teachers/{id}/schedule` | `api_teacher_schedule_{id}` | Расписание преподавателя |
| `clearInstitutesCache()` | — | — | удаляет `api_institutes` | Вспомогательный метод |

### Вспомогательная функция `normalizeStudyForm(form: string): string`

Нормализует строковое обозначение формы обучения (очная/заочная/очно-заочная) для единообразного отображения.

---

## 10. Vue-компоненты

### Оболочка приложения

#### `src/App.vue`

**Роль:** Корневой компонент-оболочка.

**Логика:**
- Регистрирует сервис-воркер (`useRegisterSW`) с часовой проверкой обновлений; при наличии обновления ставит в очередь оверлей `pwa_update`
- Вызывает `useChangelogDetector().check()` при монтировании
- Вызывает `api.syncInstallStats()` при монтировании, событиях `appinstalled`, `online`, `visibilitychange`
- Перехватывает `beforeinstallprompt` → `store.deferredPrompt`
- Вызывает `store.resetToMainGroup()` при рестарте

**Вкладки нижней навигации:**

| Путь | Иконка | Видимость |
|------|--------|-----------|
| `/lessons` | 📅 | Всегда (если `!route.meta.hideNavbar`) |
| `/exams` | 📝 | То же |
| `/search` | 🔍 | То же |
| `/settings` | ⚙️ | То же |

**Отображает глобально:** `<Modal>`, `<ChangelogModal>`, тост-уведомления.

---

#### `src/components/Modal.vue`

**Роль:** Глобальный диалог подтверждения действий.

**Источник данных:** `store.modal`

**Конфиг модала (`ModalConfig`):**

```ts
{
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  confirmStyle?: 'primary' | 'danger'
  checkbox?: { label: string; required?: boolean }
  onConfirm: () => void
  onCancel?: () => void
}
```

---

#### `src/components/BottomSheet.vue`

**Роль:** Универсальный нижний лист с жестом смахивания.

**Props:**

| Prop | Тип | Описание |
|------|-----|----------|
| `isOpen` | `boolean` | Открыт ли лист |

**Emits:** `close`

**Поведение:** drag вниз на >100px закрывает лист; телепортируется в `<body>`; использует слоты `#header` и `#default`.

---

#### `src/components/ChangelogModal.vue`

**Роль:** Модальное окно с новыми записями changelog.

**Показывается** когда `overlayManager.state.activeItem?.id === 'changelog'`.  
Читает `payload.entries` (массив `ChangelogEntry`).  
Закрывается через `overlayManager.dismiss('changelog')`.

---

### Онбординг

#### `src/components/Welcome.vue`

**Роль:** Лендинг/приветственный экран.

**Логика:**
- Кнопка «Начать» → навигация на `/onboarding`
- Скрывает декоративную иконку на старых iOS/Safari UA

---

#### `src/components/Onboarding.vue`

**Роль:** Многошаговый выбор учебной группы.

**Шаги** (управляются параметром URL `?step=`):

| Шаг | Описание |
|-----|----------|
| 1 | Выбор института + глобальный поиск по всем группам |
| 2 | Выбор формы обучения |
| 3 | Выбор курса |
| 4 | Сетка групп |

**Логика:**
- Загружает `api.getInstitutes()`
- Нормализует форму обучения через `normalizeStudyForm`
- При выборе группы → `store.setGroup(group)` → навигация на `/lessons` (с очисткой истории)
- Поиск с пагинацией: 30 элементов + «загрузить ещё»

---

### Расписание студента

#### `src/components/Schedule.vue`

**Роль:** Основной оркестратор расписания студента.

**Composables:** `useScheduleData`, `useWeekNavigation`, `useMidnightReset`

**Локальное состояние:**

| Переменная | Описание |
|------------|----------|
| `selectedDate` | Выбранная дата |
| `realToday` | Реальная дата сегодня (для сравнения с `selectedDate`) |
| `currentMinutes` | Текущее время в минутах от полуночи (обновляется каждые 10 с) |

**Конечный автомат UI (`currentState`):**

| Состояние | Описание |
|-----------|----------|
| `loading` | Идёт загрузка |
| `offline` | Нет сети и нет кеша |
| `before` | До начала семестра |
| `after` | После окончания семестра |
| `empty` | Нет занятий на выбранный день |
| `lessons` | Есть занятия |

**Функциональность:**
- Переключается на `<TeacherSchedule>` при `store.currentViewingTeacher != null`
- Оверлеи: подсказка по свайпу (`swipe_guide`), предложение установки (`pwa_install`)
- Переключение в избранное, копирование дня в буфер обмена
- DevTools-хелперы в консоли: `window.setMockTime(h, m)`, `window.debugSetDate(date)`

**Дочерние компоненты:** `ScheduleHeader`, `WeekDayPicker`, `ScheduleBody`, `GroupInfoSheet`, `ExcelModal`, `TeacherSchedule`

---

### Подкомпоненты расписания

#### `src/components/schedule/ScheduleHeader.vue`

| Props | Тип | Описание |
|-------|-----|----------|
| `groupInfo` | `GroupInfo` | Информация о группе |
| `isEvenWeek` | `boolean` | Чётность недели |
| `viewContext` | `string` | Контекст просмотра |
| `isLoading` | `boolean` | Состояние загрузки |
| `selectedDate` | `Date` | Выбранная дата |

**Emits:** `openGroupSheet`, `refresh`, `addToFavorites`, `goHome`

**Отображает:** чип группы, бейдж чётности, месяц, кнопки действий.

---

#### `src/components/schedule/WeekDayPicker.vue`

| Props | Тип | Описание |
|-------|-----|----------|
| `selectedDate` | `Date` | Выбранная дата |
| `currentWeekDates` | `Date[]` | Даты текущей недели (7 элементов) |
| `showCopyButton` | `boolean` | Показывать ли кнопку копирования |
| `today` | `Date` | Реальная сегодняшняя дата |

**Emits:** `selectDate(date)`, `copy`

**Отображает:** полоска с 7 днями недели, кнопка копирования дня.

---

#### `src/components/schedule/ScheduleBody.vue`

| Props | Тип | Описание |
|-------|-----|----------|
| `currentState` | `string` | Состояние из конечного автомата |
| `lessons` | `Lesson[]` | Занятия на выбранный день |
| `selectedDate` | `Date` | Выбранная дата |
| `currentMinutes` | `number` | Текущее время (минуты) |
| `realToday` | `Date` | Реальная сегодняшняя дата |
| `transitionName` | `string` | Анимация перехода (влево/вправо) |
| `showSwipeGuide` | `boolean` | Показывать ли подсказку по свайпу |
| `isTouchDevice` | `boolean` | Сенсорное ли устройство |

**Emits:** `touchstart`, `touchend`, `retry`, `swipeGuideDismiss`

**Отображает:** содержимое дня, анимация свайпа, состояния (офлайн, пусто, и т.д.).

---

#### `src/components/schedule/LessonCard.vue`

| Props | Тип | Описание |
|-------|-----|----------|
| `lesson` | `Lesson` | Данные занятия |
| `state` | `'future' \| 'past' \| 'soon' \| 'now'` | Временное состояние занятия |
| `timeLeft` | `number \| null` | Минут до начала/окончания |

**Используемые поля занятия:** `start_time`, `end_time`, `number_of_lesson`, `type_of_lesson`, название, аудитория, место, преподаватели.

---

#### `src/components/schedule/SwipeGuide.vue`

| Props | Тип | Описание |
|-------|-----|----------|
| `isTouchDevice` | `boolean` | Тип устройства (влияет на текст подсказки) |

**Emits:** `dismiss`

**Отображает:** подсказку по свайпу (тач) или клавишам ←/→ (десктоп) при первом запуске.

---

#### `src/components/schedule/GroupInfoSheet.vue`

| Props | Тип | Описание |
|-------|-----|----------|
| `isOpen` | `boolean` | Открыт ли лист |
| `groupInfo` | `GroupInfo` | Информация о группе |
| `formattedSemesterDates` | `string` | Отформатированные даты семестра |
| `excelUrl` | `string \| null` | Ссылка на Excel-расписание |
| `viewContext` | `string` | Контекст просмотра |
| `isFavorite` | `boolean` | В избранном ли группа |

**Emits:** `close`, `toggleFavorite`, `openExcel`

---

#### `src/components/schedule/ExcelModal.vue`

| Props | Тип | Описание |
|-------|-----|----------|
| `isOpen` | `boolean` | Открыт ли модал |
| `url` | `string` | URL официального Excel-расписания |

**Emits:** `close`

**Отображает:** полноэкранный iframe для просмотра официального расписания.

---

### Расписание преподавателя

#### `src/components/TeacherSchedule.vue`

**Роль:** Просмотр расписания преподавателя (вложен в `Schedule.vue`, не является самостоятельным маршрутом).

**Источник данных:** `store.currentViewingTeacher`

**Composables:** `useTeacherScheduleData`, `useWeekNavigation`, `useMidnightReset`

**Дополнительная логика:**
- Группировка накладок через `groupLessonsWithOverlaps` и `computeGaps` из `useTeacherMath`
- Кнопка «домой» → `store.clearViewingTeacher()`

**Дочерние компоненты:** `TeacherScheduleHeader`, `TeacherScheduleBody`

---

#### `src/components/schedule/TeacherScheduleHeader.vue`

| Props | Тип | Описание |
|-------|-----|----------|
| `teacherName` | `string` | Имя преподавателя |
| `isEvenWeek` | `boolean` | Чётность недели |
| `isLoading` | `boolean` | Состояние загрузки |
| `selectedDate` | `Date` | Выбранная дата |
| `isFavorite` | `boolean` | В избранном ли преподаватель |

**Emits:** `refresh`, `goHome`, `toggleFavorite`

---

#### `src/components/schedule/TeacherScheduleBody.vue`

| Props | Тип | Описание |
|-------|-----|----------|
| `currentState` | `string` | Состояние из конечного автомата |
| `lessonGroups` | `LessonGroup[]` | Сгруппированные занятия (с учётом накладок) |
| `gaps` | `Gap[]` | Промежутки между занятиями |
| `selectedDate` | `Date` | Выбранная дата |
| `currentMinutes` | `number` | Текущее время (минуты) |
| `realToday` | `Date` | Реальная сегодняшняя дата |
| `transitionName` | `string` | Анимация перехода |

**Emits:** `touchstart`, `touchend`, `retry`

---

#### `src/components/schedule/TeacherLessonCard.vue`

| Props | Тип | Описание |
|-------|-----|----------|
| `lesson` | `TeacherLesson \| null` | Обычное занятие (или null при конфликте) |
| `state` | `string \| null` | Временное состояние |
| `timeLeft` | `number \| null` | Минут до начала/конца |
| `conflictLessons` | `TeacherLesson[] \| null` | Накладывающиеся занятия |

**Отображает:** одно занятие или кластер конфликтующих занятий.

---

### Поиск

#### `src/components/Search.vue`

**Роль:** Поиск групп и преподавателей.

**Вкладки:** «Группы» | «Преподаватели» (горизонтальный свайп).

**Логика:**
- Параллельная загрузка: `api.getInstitutes()`, `api.getTeachers()`
- Выбор группы → `store.setViewingGroup` или `store.resetToMainGroup` → `/lessons`
- Выбор преподавателя → `store.setViewingTeacher` → `/lessons`
- При пустом запросе → показывает избранное

---

#### `src/components/search/SearchResultList.vue`

| Props | Тип | Описание |
|-------|-----|----------|
| `visibleItems` | `any[]` | Отображаемые элементы |
| `remainingCount` | `number` | Количество оставшихся элементов |
| `nextLoadLabel` | `string` | Текст кнопки «загрузить ещё» |
| `emptyIcon` | `string?` | Иконка при пустом результате |
| `emptyText` | `string?` | Текст при пустом результате |

**Emits:** `loadMore`

**Слоты:** `#default="{ item }"` — шаблон одного элемента списка.

---

### Настройки, профиль, прочее

#### `src/components/Settings.vue`

**Роль:** Экран настроек.

**Пункты меню:**
- Профиль → `/profile`
- Поделиться приложением (QR-код `/qr.png`, ссылка на приложение)
- О разработчике (контакты, Telegram, телефон — хардкод)
- Changelog → `/changelog`
- О приложении

**Отображает:** `CURRENT_VERSION` из `config/changelog.ts`.

---

#### `src/components/Profile.vue`

**Роль:** Управление профилем пользователя.

**Функциональность:**
- Показывает основную группу
- Список избранных групп с навигацией
- Список избранных преподавателей с навигацией
- Смена группы → `store.showModal` + `store.clearGroup` → `/onboarding`
- Очистка кеша расписания (удаляет ключи `api_*` из localStorage; показывает тост)

---

#### `src/components/Exams.vue`

**Роль:** Заглушка — экран «Экзамены в разработке». API не вызывает.

---

#### `src/components/Changelog.vue`

**Роль:** Полная страница истории изменений.

**Источник данных:** `changelogHistory` из `src/config/changelog.ts`.

**Навигация:** кнопка «Назад» через `router.back()`.

---

## 11. Composables

### `src/composables/useOverlayManager.ts`

**Роль:** Централизованная FIFO-очередь для всех оверлеев (баннеры, подсказки, changelog, предложение установки).

**Типы:**

```ts
type OverlayScope = 'local' | 'global'
type OverlayType = 'swipe_guide' | 'pwa_update' | 'pwa_install' | 'changelog' | ...
interface OverlayItem {
  id: string
  type: OverlayType
  scope: OverlayScope
  payload?: any
}
```

**API:**

| Метод | Описание |
|-------|----------|
| `init(router)` | Инициализация; подписка на маршруты (блокировка на `/welcome`, `/onboarding`) |
| `enqueue(item)` | Добавить оверлей в очередь |
| `dismiss(id)` | Закрыть оверлей и перейти к следующему |
| `cancel(id)` | Отменить оверлей без обработки |
| `pause()` | Приостановить очередь (при смене вкладки) |
| `resume()` | Возобновить очередь |
| `state` | Реактивное состояние: `{ activeItem, queue, isPaused }` |

**Поведение по scope:**
- `local` — замораживается при выходе с вкладки
- `global` — сохраняется между вкладками

---

### `src/composables/useChangelogDetector.ts`

**Роль:** Определяет, есть ли новые записи changelog с последнего визита.

**Логика:**
- Сравнивает `last_seen_version` с `CURRENT_VERSION`
- Специальный кейс для v1.0.0 через `changelog_v1_shown`
- Ставит в очередь до 3 новых записей через `overlayManager.enqueue`

**API:** `{ check: () => void }`

---

### `src/composables/schedule/useScheduleData.ts`

**Роль:** Загрузка и кеширование расписания студента.

**Аргументы:** `{ selectedDate: Ref<Date>, realToday: Ref<Date> }`

**Возвращает:**

| Поле | Тип | Описание |
|------|-----|----------|
| `isLoading` | `Ref<boolean>` | Идёт загрузка |
| `allLessons` | `Ref<Lesson[]>` | Все занятия семестра |
| `isOffline` | `Ref<boolean>` | Офлайн-режим |
| `originalExcelUrl` | `Ref<string \| null>` | Ссылка на Excel |
| `fetchScheduleData` | `() => Promise<void>` | Принудительная перезагрузка (антиспам 5 с) |
| `semesterAnchor` | `Ref<...>` | Якорная дата семестра |
| `educationDates` | `Ref<...>` | Даты начала/конца обучения |

**Наблюдает за:** `store.currentViewingGroup` — перезагружает при смене.

---

### `src/composables/schedule/useTeacherScheduleData.ts`

**Роль:** Аналог `useScheduleData` для расписания преподавателя.

**Источник:** `api.getTeacherSchedule(teacherId)`

**Отличие:** нет дат учебного периода (API не предоставляет).

---

### `src/composables/schedule/useWeekNavigation.ts`

**Роль:** Навигация по неделям с определением чётности.

**Функциональность:**
- Вычисляет чётность недели от якорной даты семестра
- Формирует массив из 7 дат (Пн–Вс)
- Свайп влево/вправо
- Клавиши: `←`/`→`, `A`/`D`, `Ф`/`В` (русская раскладка)

**Возвращает:** `{ isEvenWeek, currentWeekDates, transitionName, goToPrevDay, goToNextDay }`

---

### `src/composables/schedule/useMidnightReset.ts`

**Роль:** Обнаружение смены суток в PWA (надёжно работает при фоновом режиме).

**Механизм:** `visibilitychange` + интервал 60 с.

**Логика:** Сдвигает `selectedDate` только если пользователь был на «сегодня».

**Dev-хелперы:** `setMockDateSource(fn)`, `getCurrentDate()`

---

### `src/composables/schedule/useTeacherMath.ts`

**Роль:** Математика для расписания преподавателя (накладки, промежутки).

**Типы:**

```ts
interface TeacherLesson {
  id: number
  start_time: string   // "HH:MM"
  end_time: string     // "HH:MM"
  // ... остальные поля занятия
}

interface LessonGroup {
  lessons: TeacherLesson[]
  hasConflict: boolean
}
```

**Функции:**

| Функция | Описание |
|---------|----------|
| `parseTeacherTime(time)` | Парсинг "HH:MM" → минуты от полуночи |
| `groupLessonsWithOverlaps(lessons)` | Группировка занятий с временны́ми накладками |
| `computeGaps(groups)` | Вычисление промежутков между группами занятий |

---

## 12. Конфигурация PWA

### `vite.config.ts` (плагин VitePWA)

```ts
VitePWA({
  registerType: 'prompt',          // Пользователь сам решает обновляться
  injectRegister: 'auto',
  devOptions: { enabled: true },   // SW работает в dev-режиме
  manifest: {
    name: 'Kosyga.Space',
    short_name: 'Kosyga.Space',
    theme_color: '#020617',        // Тёмная тема
    display: 'standalone',
    icons: [
      { src: '/icons/android/android-launchericon-192-192.png', sizes: '192x192' },
      { src: '/icons/android/android-launchericon-512-512.png', sizes: '512x512' },
    ]
  }
})
```

### Runtime (в `App.vue`)

- `useRegisterSW({ onNeedRefresh })` — при доступном обновлении → `overlayManager.enqueue({ id: 'pwa_update' })`
- Перехват `beforeinstallprompt` → `store.deferredPrompt`
- Кнопка установки в `Schedule.vue` (через `store.deferredPrompt.prompt()`)

### `index.html`

- `viewport` заблокирован (`user-scalable=no`)
- `theme-color: #020617`
- `color-scheme: dark`
- Иконки для iOS (`apple-touch-icon`), Android, favicon

### Nginx

- `sw.js` и `manifest.webmanifest` → `Cache-Control: no-store` (обновления всегда свежие)
- `assets/` → `Cache-Control: max-age=31536000` (год, immutable)

---

## 13. Конфигурационные файлы

### `vite.config.ts`

- **Плагины:** `vue()`, `tailwindcss()`, `VitePWA(...)`
- **Dev proxy:** `/api/v1/client` → `http://localhost:8000`
- `server.allowedHosts: true`

### `tsconfig.app.json`

- Таргеты: DOM, DOM.Iterable, `vite/client`, `vite-plugin-pwa/client`
- Строгий режим: `noUnusedLocals`, `noUnusedParameters`

### `tsconfig.node.json`

- ModuleResolution: NodeNext (для `vite.config.ts`)

### `src/config/changelog.ts`

```ts
export const CURRENT_VERSION = 'X.Y.Z'

export interface ChangelogItem {
  type: 'major' | 'minor' | 'patch'
  text: string
}

export interface ChangelogEntry {
  version: string
  date: string
  items: ChangelogItem[]
}

export const changelogHistory: ChangelogEntry[] = [ ... ]
```

### `src/style.css`

CSS-токены (используются в Tailwind `@theme inline`):

| Токен | Назначение |
|-------|-----------|
| `--bg-page` | Фон страницы |
| `--accent` | Акцентный цвет |
| (и др.) | Полная тема тёмного режима |

Глобальные PWA-локи: блокировка прокрутки за пределы, блокировка выделения текста (кроме input).

---

## 14. Docker и Nginx

### `prod.Dockerfile` / `local.Dockerfile`

**Стадия 1 (builder):** `node:alpine` → `npm ci` → `npm run build`  
**Стадия 2 (server):** `nginx:alpine` → копирует `dist/` → копирует конфиг nginx

### `nginx.conf` (production)

| Функция | Описание |
|---------|----------|
| HTTPS + HSTS | Принудительный HTTPS |
| Bot-фильтр | Блокировка по User-Agent |
| UUID-валидация | Проверка заголовка `X-Device-ID` |
| SW no-cache | `Cache-Control: no-store` для `sw.js` / `manifest.webmanifest` |
| Assets cache | `max-age=31536000` для `/assets/` |
| SPA fallback | `try_files $uri /index.html` |
| API proxy | `/api/` → `http://backend:8000` с rate limit |

### `nginx.local.conf` (локальная разработка)

Аналог без HTTPS и без долгого кеша ассетов; длинные таймауты для API proxy.

---

## 15. Типы и интерфейсы

Отдельной директории `types/` нет. Типы определены рядом с использованием.

| Файл | Типы |
|------|------|
| `config/changelog.ts` | `ChangelogItem`, `ChangelogEntry` |
| `composables/useOverlayManager.ts` | `OverlayScope`, `OverlayType`, `OverlayItem` |
| `composables/useChangelogDetector.ts` | `ChangelogPayload` |
| `composables/schedule/useTeacherMath.ts` | `TeacherLesson`, `LessonGroup` |
| `store.ts` | Инлайн-шейпы для `GroupInfo`, `TeacherInfo`, `Toast`, `ModalConfig` |
| Компоненты | `defineProps<{...}>()` — пропсы определены инлайн |

---

## 16. Архитектурные решения

| Решение | Обоснование |
|---------|------------|
| Единый `reactive` стор вместо Pinia | Простота; нет нужды в devtools-интеграции |
| Офлайн-кеш в localStorage | PWA без IndexedDB; простой key-value достаточно |
| `overlayManager` как singleton-очередь | Предотвращает одновременный показ нескольких оверлеев |
| `TeacherSchedule` вложен в `Schedule`, а не отдельный маршрут | Сохраняет состояние навигации; Back возвращает к расписанию студента |
| Composables для данных расписания | Переиспользование логики между студенческим и преподавательским режимами |
| `useMidnightReset` через `visibilitychange` + интервал | PWA может быть заморожен браузером; нельзя полагаться только на `setTimeout` |
| Docker multi-stage + nginx | Минимальный образ; nginx обрабатывает кеширование и прокси |

---

## 17. Известные заглушки и ограничения

- **`/exams`** — полная заглушка, API не реализован
- **Иконки PWA** (`/icons/android/`, `/icons/ios/`) — referenced в `index.html` и `vite.config.ts`, но могут отсутствовать в `public/`
- **Контакты в `Settings.vue`** — Telegram, телефон, ссылка на шаринг хардкодированы
- **Нет `.env.example`** — переменная `VITE_API_URL` нигде не задокументирована в репозитории
- **README.md** (этот файл) — заменяет стандартный Vite-шаблон

---

*Этот README сгенерирован автоматически на основе анализа кодовой базы. Версия актуальна на момент создания.*
