package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"time"

	"github.com/joho/godotenv"
	"github.com/redis/go-redis/v9"
)

type Config struct {
	ProxyURL      string
	RedisURL      string
	APIURL_GROUPS string
}

const (
	GroupsListKey              = "db:api:groups:list"
	GroupsListETagKey          = "db:api:groups:ETag"
	GroupsSchedulesKey         = "db:api:groups_schedules:list"
	GroupsSchedulesETagKey     = "db:api:groups_schedules:ETag"
	GroupsEmptySchedulesKey    = "db:api:groups_schedules:empty"
	GroupsSchedulesHashKey     = "db:api:groups_schedules:Hash"
	GroupsSchedulesHasActivity = "db:api:groups_schedules:Activity_detected"
	SleepDuration              = 5 * time.Minute
)

// const GroupsSchedulesKey = "db:api:groups_schedules:list"
// const GroupsSchedulesETagKey = "db:api:groups_schedules:ETag"

var (
	AppConfig *Config
	Log       *slog.Logger
	RDB       *redis.Client
	Ctx       = context.Background()
)

func InitLogger() {
	opts := &slog.HandlerOptions{
		Level: slog.LevelDebug,
	}

	logger := slog.New(slog.NewTextHandler(os.Stdout, opts))

	// Делаем его дефолтным для всей программы:
	slog.SetDefault(logger)
}

func getEnv(key string, defValue string) string {
	val := os.Getenv(key)
	if val == "" {
		return defValue
	}
	return val
}

func InitConfig() {
	err := godotenv.Load()

	if err != nil {
		slog.Info("Запуск парсера в Docker контейнере (.env файл не найден)")
	} else {
		slog.Info("Запуск в dev режиме (.env файл найден)")
	}

	host := getEnv("PROXY_HOST", "")
	port := getEnv("PROXY_PORT", "")
	login := getEnv("PROXY_LOGIN_PARSING", "")
	password := getEnv("PROXY_PASSWORD_PARSING", "")

	var proxy string

	if host == "" || port == "" || login == "" || password == "" {
		proxy = ""
		slog.Warn("Данные для подключения к прокси неполные! Парсинг будет осуществлен с вашего IP")

	} else {
		proxy = fmt.Sprintf("http://%s:%s@%s:%s", login, password, host, port)
	}

	AppConfig = &Config{
		ProxyURL:      proxy,
		RedisURL:      getEnv("REDIS_URL", "redis://127.0.0.1:6379/0"),
		APIURL_GROUPS: getEnv("APIURL_GROUPS", "https://timetable.rguk.ru/api/items/groups?fields=id,name,plan.year_start,plan.faculty.name&limit=-1"),
	}
}

func InitRedis() {
	opt, err := redis.ParseURL(AppConfig.RedisURL)
	if err != nil {
		slog.Error("невалидный REDIS_URL", "err", err)
		os.Exit(1)
	}
	opt.Protocol = 3

	RDB = redis.NewClient(opt)

	// Проверяем доступность базы сразу
	if err := RDB.Ping(Ctx).Err(); err != nil {
		slog.Error("не удалось достучаться до Redis", "err", err)
		os.Exit(1)
	}
	slog.Info("успешное подключение к Redis")
}

func Notify(level, msg, detail string) {
	// 1. Упаковываем в JSON-строку только массив details: ["Новый эксель файл"]
	detailsArr := []string{detail}
	detailsJSON, err := json.Marshal(detailsArr)
	if err != nil {
		slog.Error("ошибка сериализации details для алерта", "err", err)
		return
	}

	// 2. Пушим поля прямо в стрим (ровно так, как показал XRANGE)
	err = RDB.XAdd(Ctx, &redis.XAddArgs{
		Stream: "notifier:queue",
		Values: map[string]interface{}{
			"service":   "API-Parser",
			"msg_level": level,
			"msg":       msg,
			"details":   string(detailsJSON),
		},
	}).Err()
	if err != nil {
		slog.Error("не удалось отправить алерт в Redis Stream", "err", err)
	}
}
