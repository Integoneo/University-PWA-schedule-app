package main

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"net/url"
	"os"
	"regexp"
	"strings"
	"time"

	"github.com/enetx/g"
	"github.com/enetx/surf"
)

// simplifyError вытаскивает короткую суть сетевого сбоя
func simplifyError(err error) string {
	if err == nil {
		return "unknown error"
	}
	msg := err.Error()

	switch {
	case strings.Contains(msg, "i/o timeout"):
		return "i/o timeout"
	case strings.Contains(msg, "context deadline exceeded"):
		return "context deadline exceeded"
	case strings.Contains(msg, "client connection lost"):
		return "client connection lost"
	case strings.Contains(msg, "connection reset by peer"):
		return "connection reset"
	case strings.Contains(msg, "connection refused"):
		return "connection refused"
	default:
		// Для ошибок статуса сервера (502, 503) или других непредвиденных
		if len(msg) > 50 {
			return msg[:50] + "..."
		}
		return msg
	}
}

// shortenTarget вытаскивает только ID группы вместо 400-символьного URL
func shortenTarget(rawURL string) string {
	// Достаем ID группы из закодированного или обычного JSON фильтра
	re := regexp.MustCompile(`(?:%22_eq%22%3A|"_eq":)(\d+)`)
	if match := re.FindStringSubmatch(rawURL); len(match) > 1 {
		return fmt.Sprintf("group_id: %s", match[1])
	}

	// Если это другой эндпоинт (например, получение списка групп), отрезаем query
	if idx := strings.Index(rawURL, "?"); idx != -1 {
		return rawURL[:idx]
	}
	return rawURL
}

// Универсальный клиент с ретраями
func fetchWithRetry(url string, etag string, maxRetries int) (*FetchResult, error) {
	var lastErr error

	for attempt := 1; attempt <= maxRetries; attempt++ {
		// Создаем клиент внутри попытки, чтобы при обрыве HTTP/2 соединение не залипало
		client := surf.NewClient().Builder().
			Impersonate().RandomOS().Firefox().
			Proxy(g.String(AppConfig.ProxyURL)).
			DisableKeepAlive().
			// ForceHTTP1().              // Никаких капризных фреймов HTTP/2
			Timeout(45 * time.Second). // Даем Directus время собрать тяжелый SQL-запрос
			Build().Unwrap()

		req := client.Get(g.String(url))
		if etag != "" {
			req.AddHeaders(g.Map[g.String, g.String]{
				"If-None-Match": g.String(etag),
			})
		}

		resp := req.Do()

		// 1. Ошибка отправки запроса или получения заголовков
		if resp.IsErr() {
			lastErr = fmt.Errorf("ошибка сети: %v", resp.Err())
			slog.Warn("сбой сетевого запроса, пробуем снова", "attempt", attempt, "err", lastErr)
			time.Sleep(time.Duration(attempt*2) * time.Second)
			continue
		}

		httpResp := resp.Ok()
		statusCode := int(httpResp.StatusCode)

		// 2. Статус 304 Not Modified — тела нет по стандарту HTTP, сразу выходим
		if statusCode == 304 {
			return &FetchResult{
				StatusCode: 304,
				Body:       nil,
				ETag:       string(httpResp.Headers.Get("ETag")),
			}, nil
		}

		// 3. Статус 200 OK — БЕЗОПАСНО вычитываем тело (без паник)
		if statusCode == 200 {
			bodyRes := httpResp.Body.Bytes()
			if bodyRes.IsErr() {
				// Вот тут и ловится http2: client connection lost
				lastErr = fmt.Errorf("обрыв соединения при скачивании тела: %v", bodyRes.Err())
				slog.Warn("соединение разорвано при чтении данных, ретрай", "attempt", attempt, "err", lastErr)
				time.Sleep(time.Duration(attempt*2) * time.Second)
				continue
			}

			return &FetchResult{
				StatusCode: 200,
				Body:       []byte(bodyRes.Ok()),
				ETag:       string(httpResp.Headers.Get("ETag")),
			}, nil
		}

		// 4. Фатальные ошибки авторизации / банов — глушим бинарник
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

		// 5. Ошибки сервера (500, 502, 503, 504) или Rate Limit (429)
		lastErr = fmt.Errorf("сервер вернул статус: %d", statusCode)
		slog.Warn("ошибка сервера, ретрай через паузу", "attempt", attempt, "status", statusCode)
		time.Sleep(time.Duration(attempt*4) * time.Second)
	}

	// Если все 3 попытки исчерпаны
	Notify("ERROR", "Исчерпаны ретраи сетевых запросов", fmt.Sprintf("%s | %s", shortenTarget(url), simplifyError(lastErr)))
	return nil, lastErr
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
		item := GroupRedisItem{
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

		// Сразу наполняем возвращаемый массив без повторного похода в Redis!
		parsingResponse = append(parsingResponse, item)
	}

	_, err = pipe.Exec(Ctx)
	if err != nil {
		slog.Error("Не удалось сохранить группы в Redis", "err", err)
	}

	slog.Info("Группы успешно получены и сохранены", "count", len(parsingResponse))
	// Notify("INFO", "Спарсен список групп", fmt.Sprintf("Успешно получено %d групп", len(parsingResponse)))

	return parsingResponse
}

func fetchGroupSchedule(groupID int, dateGTE, dateLT, etag string) (*FetchResult, error) {
	filterJSON := fmt.Sprintf(`{"groups":{"groups_id":{"id":{"_eq":%d}}},"date_start":{"_gte":"%s","_lt":"%s"}}`,
		groupID, dateGTE, dateLT)
	fields := "date_start,date_end,description,type_of_employment.short_name,auditories.auditories_id.name,teachers.teachers_id.name,groups_plans_disciplines.groups_plans_disciplines_id.plan_discipline.discipline.name"

	apiURL := fmt.Sprintf("https://timetable.rguk.ru/api/items/timetable_entries?filter=%s&fields=%s",
		url.QueryEscape(filterJSON), fields)

	return fetchWithRetry(apiURL, etag, 3)
}
