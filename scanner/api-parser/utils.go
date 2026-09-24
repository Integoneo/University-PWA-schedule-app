package main

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"time"

	"github.com/enetx/g"
	"github.com/enetx/surf"
)

// Результат запроса
type FetchResult struct {
	StatusCode int
	Body       []byte
	ETag       string
}

// Универсальный клиент с ретраями
func fetchWithRetry(url string, etag string, maxRetries int) (*FetchResult, error) {
	client := surf.NewClient().Builder().
		Impersonate().RandomOS().Firefox().
		Proxy(g.String(AppConfig.ProxyURL)).
		DisableKeepAlive().
		Build().Unwrap()

	var lastErr error

	for attempt := 1; attempt <= maxRetries; attempt++ {
		req := client.Get(g.String(url))
		if etag != "" {
			req.AddHeaders(g.Map[g.String, g.String]{
				"If-None-Match": g.String(etag),
			})
		}

		resp := req.Do()

		// 1. Ошибка сетевого соединения (таймаут, DNS, прокси разорвал соединение)
		if resp.IsErr() {
			lastErr = fmt.Errorf("ошибка сети: %v", resp.Err())
			slog.Warn("сбой сетевого запроса, пробуем снова", "attempt", attempt, "err", lastErr)
			time.Sleep(time.Duration(attempt*2) * time.Second) // пауза: 2с, 4с...
			continue
		}

		httpResp := resp.Ok()
		statusCode := httpResp.StatusCode

		// 2. Успешные ответы
		if statusCode == 200 || statusCode == 304 {
			return &FetchResult{
				StatusCode: int(statusCode),
				Body:       []byte(httpResp.Body.Bytes().Unwrap()),
				ETag:       string(httpResp.Headers.Get("ETag")),
			}, nil
		}

		// 3. Фатальные ошибки конфигурации/банов — ретраить бессмысленно, глушим сразу!
		if statusCode == 407 {
			Notify("DEAD", "Ошибка авторизации в прокси (407)", "Проверьте логин/пароль к прокси-пулу")
			slog.Error("407 Proxy Authentication Required. Завершение работы.")
			os.Exit(1)
		}
		if statusCode == 401 || statusCode == 403 {
			Notify("CRITICAL", fmt.Sprintf("Доступ к API заблокирован (%d)", statusCode), url)
			slog.Error("Доступ запрещен сайтом. Завершение работы.", "status", statusCode)
			os.Exit(1)
		}
		if statusCode == 404 {
			Notify("CRITICAL", "API эндпоинт не найден (404)", url)
			slog.Error("Эндпоинт 404. Завершение работы.")
			os.Exit(1)
		}

		// 4. Ошибки сервера (500, 502, 503, 504) или Rate Limit (429) — пробуем снова
		lastErr = fmt.Errorf("сервер вернул статус: %d", statusCode)
		slog.Warn("ошибка сервера, ретрай через паузу", "attempt", attempt, "status", statusCode)
		time.Sleep(time.Duration(attempt*2) * time.Second)
	}

	// Если все попытки исчерпаны
	Notify("ERROR", "Исчерпаны ретраи сетевых запросов", fmt.Sprintf("URL: %s | Ошибка: %v", url, lastErr))
	return nil, lastErr
}

type GroupsResponse struct {
	Data []GroupItem `json:"data"`
}

type GroupItem struct {
	ID   int      `json:"id"`
	Name string   `json:"name"`
	Plan PlanItem `json:"plan"`
}

type PlanItem struct {
	YearStart int         `json:"year_start"`
	Faculty   FacultyItem `json:"faculty"`
}

type FacultyItem struct {
	Name string `json:"name"`
}

type GroupRedisItem struct {
	ID        int    `json:"id"`
	Name      string `json:"name"`
	YearStart int    `json:"year_start"`
	Faculty   string `json:"faculty"`
}

func fetchGroups() []GroupRedisItem {
	slog.Info("Запрос списка групп...")

	// 1. Достаем сохраненный ETag
	savedETag, _ := RDB.HGet(Ctx, GroupsListETagKey, "ETag").Result()

	// 2. Делаем запрос через надежный сетевой модуль
	res, err := fetchWithRetry(AppConfig.APIURL_GROUPS, savedETag, 3)

	var parsingResponse []GroupRedisItem

	if err != nil {
		slog.Error("Не удалось получить группы после всех ретраев", "err", err)
		return parsingResponse
	}

	// 3. Данные не менялись — выходим
	//
	if res.StatusCode == 304 {
		slog.Info("Список групп не изменился (304 Not Modified). Пропускаем.")
		savedGroups, err := RDB.HGetAll(Ctx, GroupsListKey).Result()
		if err != nil {
			slog.Error("Не удалось достать группы из Redis", "err", err)
		} else {
			for key, val := range savedGroups {
				var item GroupRedisItem
				err := json.Unmarshal([]byte(val), &item)
				if err != nil {
					slog.Error("Битый JSON группы в Redis", "id", key, "err", err)
					continue
				}
				parsingResponse = append(parsingResponse, item)
			}

			return parsingResponse
		}
	}

	// 4. Парсинг JSON и проверка на сломанную схему
	var response GroupsResponse
	err = json.Unmarshal(res.Body, &response)
	if err != nil {
		// Сервер вернул не JSON (например HTML страницу с ошибкой) или синтаксис битый
		Notify("CRITICAL", "Сломался JSON в ответе API групп", err.Error())
		slog.Error("Ошибка парсинга json ответа", "err", err)
		os.Exit(1)
	}

	// 5. Валидация бизнес-логики схемы
	// Если массив пустой или ключевые поля у первой группы пустые — схема изменена!
	if len(response.Data) == 0 {
		Notify("WARN", "API групп вернул пустой список", "data: []")
		slog.Warn("Список групп пуст")
		return parsingResponse
	}

	sample := response.Data[0]
	if sample.ID == 0 || sample.Name == "" || sample.Plan.Faculty.Name == "" {
		Notify("CRITICAL", "Схема данных API групп изменилась!",
			fmt.Sprintf("Проверьте поля: ID=%d, Name=%s, Faculty=%s",
				sample.ID, sample.Name, sample.Plan.Faculty.Name))
		slog.Error("Критические поля в схеме отсутствуют или пусты. Остановка.")
		os.Exit(1)
	}

	// 6. Всё валидно — сохраняем ETag и кэш в Redis
	pipe := RDB.Pipeline()
	if res.ETag != "" {
		pipe.HSet(Ctx, GroupsListETagKey, "ETag", res.ETag)
	}

	for _, group := range response.Data {
		item := &GroupRedisItem{
			ID:        group.ID,
			Name:      group.Name,
			YearStart: group.Plan.YearStart,
			Faculty:   group.Plan.Faculty.Name,
		}
		data, err := json.Marshal(item)
		if err != nil {
			slog.Error("Ошибка парсинга", "err", err)
			Notify("ERROR", "Ошибка парсинга JSON", err.Error())
			continue
		}
		pipe.HSet(Ctx, GroupsListKey, group.ID, data)
	}

	_, err = pipe.Exec(Ctx)
	if err != nil {
		slog.Error("Не удалось сохранить группы в Redis", "err", err)
	}

	slog.Info("Группы успешно получены и проверены", "count", len(response.Data))

	// INFO: Убрать в проде
	Notify("INFO", "Спарсен список групп", fmt.Sprintf("Успешно получено %d групп", len(response.Data)))

	slog.Info("Список групп не изменился (304 Not Modified). Пропускаем.")
	savedGroups, err := RDB.HGetAll(Ctx, GroupsListKey).Result()
	if err != nil {
		slog.Error("Не удалось достать группы из Redis", "err", err)
	} else {
		for key, val := range savedGroups {
			var item GroupRedisItem
			err := json.Unmarshal([]byte(val), &item)
			if err != nil {
				slog.Error("Битый JSON группы в Redis", "id", key, "err", err)
				continue
			}
			parsingResponse = append(parsingResponse, item)
		}
	}
	return parsingResponse
}
