package main

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"sort"
	"strings"
	"time"

	"github.com/cespare/xxhash/v2"
)

// Вес дней недели для строгой сортировки
var dayPriority = map[string]int{
	"ПН": 0,
	"ВТ": 1,
	"СР": 2,
	"ЧТ": 3,
	"ПТ": 4,
	"СБ": 5,
	"ВС": 6,
}

// Хелпер детерминированной сортировки пар
func sortLessons(lessons []LessonSchema) {
	sort.SliceStable(lessons, func(i, j int) bool {
		a, b := lessons[i], lessons[j]

		// 1. Сначала ВСЕ нечетные (false), потом четные (true)
		if a.IsEvenWeek != b.IsEvenWeek {
			return !a.IsEvenWeek // false (< true) идет раньше
		}

		// 2. Сортировка по дням недели (ПН -> ВС)
		if dayPriority[a.DayOfWeek] != dayPriority[b.DayOfWeek] {
			return dayPriority[a.DayOfWeek] < dayPriority[b.DayOfWeek]
		}

		// 3. Сортировка по времени начала ("09:15" < "12:25")
		if a.StartTime != b.StartTime {
			return a.StartTime < b.StartTime
		}

		// 4. Если в одно время начинаются разные подгруппы — сортируем по предмету и кабинету
		if a.Lesson != b.Lesson {
			return a.Lesson < b.Lesson
		}
		return a.Classroom < b.Classroom
	})
}

// Очистка стоп-слов из ФИО преподавателя
func cleanTeacherName(name string) string {
	t := strings.ToLower(name)
	t = strings.ReplaceAll(t, "\u00a0", "")
	t = strings.ReplaceAll(t, ".", "")
	t = strings.TrimSpace(t)

	banSet := []string{"препод", "ст", "стар", "стр", "доцент"}
	for _, ban := range banSet {
		if t == ban {
			return ""
		}
	}
	return strings.TrimSpace(name)
}

func calculateCourse(yearStart int) string {
	if yearStart <= 0 {
		return ""
	}
	now := time.Now().In(MSKLocation)
	currentYear := now.Year()

	// Если сейчас до сентября (весенний семестр), учебный год начался в прошлом календарном году
	academicStartYear := currentYear
	if now.Month() < time.September {
		academicStartYear = currentYear - 1
	}

	course := academicStartYear - yearStart + 1
	if course < 1 || course > 6 {
		return fmt.Sprintf("%d курс", course)
	}
	return fmt.Sprintf("%d", course) // Вернет "4" (или "4 курс" при желании)
}

// Нормализация ответа Directus в схему Pydantic
func normalizeSchedule(group GroupRedisItem, raw []DirectusLessonItem) *SchedulePayloadSchema {
	var lessons []LessonSchema

	for _, item := range raw {
		tStart, err := time.ParseInLocation("2006-01-02T15:04:05", item.DateStart, MSKLocation)
		if err != nil {
			continue
		}
		tEnd, _ := time.ParseInLocation("2006-01-02T15:04:05", item.DateEnd, MSKLocation)

		var teachers []string
		for _, t := range item.Teachers {
			cleaned := cleanTeacherName(t.TeachersID.Name)
			if cleaned != "" {
				teachers = append(teachers, cleaned)
			}
		}

		classroom := ""
		if len(item.Auditories) > 0 {
			classroom = item.Auditories[0].AuditoriesID.Name
		}

		discipline := "Не указано"
		if len(item.GroupsPlansDisciplines) > 0 {
			name := item.GroupsPlansDisciplines[0].GroupsPlansDisciplinesID.PlanDiscipline.Discipline.Name
			if name != "" {
				discipline = name
			}
		}

		typeOfLesson := ""
		if item.TypeOfEmployment != nil {
			typeOfLesson = item.TypeOfEmployment.ShortName
		}

		lessons = append(lessons, LessonSchema{
			DayOfWeek:        DayMapping[tStart.Weekday()],
			StartTime:        tStart.Format("15:04"),
			EndTime:          tEnd.Format("15:04"),
			EducationalPlace: "РГУ им. А.Н. Косыгина",
			Lesson:           discipline,
			IsEvenWeek:       IsEvenWeek(tStart),
			Classroom:        classroom,
			TypeOfLesson:     typeOfLesson,
			Teachers:         teachers,
		})
	}

	// ГАРАНТИЯ ДЕТЕРМИНИРОВАННОСТИ:
	// Сортируем пары перед отдачей и расчетом хэша
	sortLessons(lessons)

	return &SchedulePayloadSchema{
		Institute:          "",
		InstituteShortName: group.Faculty,
		Group:              group.Name,
		EducationForm:      "",
		Lessons:            lessons,
		Type:               "lessons",
	}
}

// ProcessGroupSchedule обрабатывает одну группу и отправляет алерты при изменениях
func ProcessGroupSchedule(group GroupRedisItem, dateGTE, dateLT string) {
	idStr := fmt.Sprintf("%d", group.ID)

	// 1. Берем сохраненный ETag
	savedETag, _ := RDB.HGet(Ctx, GroupsSchedulesETagKey, idStr).Result()

	// 2. Сетевой запрос
	res, err := fetchGroupSchedule(group.ID, dateGTE, dateLT, savedETag)
	if err != nil {
		slog.Warn("Не удалось получить расписание группы", "group", group.Name, "err", err)
		return
	}

	// 3. 304 Not Modified — пропускаем без действий
	if res.StatusCode == 304 {
		return
	}

	// 4. Парсим ответ
	var directusResp DirectusScheduleResponse
	if err := json.Unmarshal(res.Body, &directusResp); err != nil {
		slog.Error("Ошибка парсинга расписания Directus", "group", group.Name, "err", err)
		return
	}

	// Проверяем прошлые состояния группы в Redis
	hadSchedule, _ := RDB.HExists(Ctx, GroupsSchedulesKey, idStr).Result()
	wasEmpty, _ := RDB.HExists(Ctx, GroupsEmptySchedulesKey, idStr).Result()

	// 5. ВЕТКА А: Расписание пустое
	if len(directusResp.Data) == 0 {
		// АЛЕРТИМ ТОЛЬКО ЕСЛИ: у группы РЕАЛЬНО было расписание в базе, а теперь его удалили!
		if hadSchedule {
			Notify("WARN", "Расписание группы очищено (стало пустым)",
				fmt.Sprintf("Группа: %s (%s)", group.Name, group.Faculty))
		}

		// Если это холодный старт (первый прогон) или группа уже была пустой:
		// Просто тихо фиксируем факт пустоты в Redis и чистим старые ключи расписаний
		pipe := RDB.Pipeline()
		pipe.HSet(Ctx, GroupsEmptySchedulesKey, idStr, "1")
		pipe.HDel(Ctx, GroupsSchedulesHashKey, idStr)
		pipe.HDel(Ctx, GroupsSchedulesKey, idStr)
		if res.ETag != "" {
			pipe.HSet(Ctx, GroupsSchedulesETagKey, idStr, res.ETag)
		}
		pipe.Exec(Ctx)
		return
	}

	// 6. ВЕТКА Б: Расписание не пустое — нормализуем и детерминированно сортируем
	payload := normalizeSchedule(group, directusResp.Data)
	normalizedJSON, err := json.Marshal(payload)
	if err != nil {
		slog.Error("Ошибка маршалинга нормализованной схемы", "group", group.Name, "err", err)
		return
	}

	// 7. Считаем xxhash от идеально упорядоченного JSON
	currentHash := fmt.Sprintf("%x", xxhash.Sum64(normalizedJSON))
	savedHash, _ := RDB.HGet(Ctx, GroupsSchedulesHashKey, idStr).Result()

	// Если хэш совпал — контент не изменился, просто обновился ETag Directus
	if savedHash == currentHash {
		if res.ETag != "" {
			RDB.HSet(Ctx, GroupsSchedulesETagKey, idStr, res.ETag)
		}
		return
	}

	// 8. Детекция реальных изменений
	hasActivity := false

	if wasEmpty {
		// Группа РАНЕЕ была пустой, а теперь у нее появились пары!
		hasActivity = true
		Notify("INFO", "Появилось новое расписание у группы!",
			fmt.Sprintf("%s | Пар: %d | %s", group.Name, len(payload.Lessons), group.Faculty))
	} else if savedHash != "" {
		// У группы уже было расписание, но контент изменился (хэши разные)
		hasActivity = true
		Notify("INFO", "Обновлено расписание группы",
			fmt.Sprintf("%s | %s", group.Name, group.Faculty))
	}

	// 9. Сохраняем актуальные данные в Redis
	pipe := RDB.Pipeline()
	pipe.HDel(Ctx, GroupsEmptySchedulesKey, idStr) // Снимаем флаг пустоты
	pipe.HSet(Ctx, GroupsSchedulesHashKey, idStr, currentHash)
	pipe.HSet(Ctx, GroupsSchedulesKey, idStr, string(normalizedJSON))
	if res.ETag != "" {
		pipe.HSet(Ctx, GroupsSchedulesETagKey, idStr, res.ETag)
	}

	// Если было зафиксировано реальное движение — записываем группу на "радар активности"
	if hasActivity {
		activityItem := GroupActivityTrackSchema{
			InstituteShortName: group.Faculty,
			Group:              group.Name,
			Course:             calculateCourse(group.YearStart),
			LastUploadTime:     time.Now().In(MSKLocation),
		}

		activityJSON, err := json.Marshal(activityItem)
		if err == nil {
			pipe.HSet(Ctx, GroupsSchedulesHasActivity, idStr, string(activityJSON))
		}
	}

	_, err = pipe.Exec(Ctx)
	if err != nil {
		slog.Error("Ошибка сохранения расписания в Redis", "group", group.Name, "err", err)
	}
}
