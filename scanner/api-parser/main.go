package main

import (
	"log/slog"
	"sync"
	"sync/atomic"
	"time"
)

// runScoutCycle запускает параллельный обход с лимитом в 3 одновременных запроса
func runScoutCycle(groupList []GroupRedisItem, dateGTE, dateLT string) {
	const maxConcurrency = 3
	semaphore := make(chan struct{}, maxConcurrency)

	var wg sync.WaitGroup
	var completed atomic.Int32
	total := int32(len(groupList))

	for _, group := range groupList {
		wg.Add(1)

		// Блокируется, если уже занято 3 слота
		semaphore <- struct{}{}

		// Передаем group параметром в горутину во избежание захвата переменной цикла
		go func(g GroupRedisItem) {
			defer wg.Done()
			defer func() {
				<-semaphore // Освобождаем слот для следующей группы
			}()

			// Обрабатываем группу
			ProcessGroupSchedule(g, dateGTE, dateLT)

			// Даем серверу Directus микропаузу перед следующим запросом в этом слоте
			time.Sleep(500 * time.Millisecond)

			// Потокобезопасно инкрементируем счетчик завершенных задач
			done := completed.Add(1)
			if done%50 == 0 || done == total {
				slog.Info("Прогресс обхода", "done", done, "total", total)
			}
		}(group)
	}

	// Ждем, пока все группы дойдут до конца
	wg.Wait()
}

func main() {
	InitLogger()
	InitConfig()
	InitRedis()
	defer RDB.Close()

	for {
		slog.Info("=== Старт круга разведки ===")

		// 1. Получаем список групп
		groupList := fetchGroups()
		if len(groupList) == 0 {
			slog.Warn("Список групп пуст. Пауза 5 минут.")
			time.Sleep(5 * time.Minute)
			continue
		}

		// 2. Рассчитываем актуальное двухнедельное окно
		dateGTE, dateLT := GetDirectusDateRange(time.Now())
		slog.Info("Окно парсинга", "gte", dateGTE, "lt", dateLT)

		startTime := time.Now()

		// 3. Запускаем контролируемый 3-поточный обход
		runScoutCycle(groupList, dateGTE, dateLT)

		duration := time.Since(startTime).Round(time.Second)
		slog.Info("=== Круг завершен ===", "duration", duration, "total_groups", len(groupList))

		// 4. Засыпаем перед следующим обходом
		slog.Info("Засыпаем...", "duration", SleepDuration)
		time.Sleep(SleepDuration)
	}
}
