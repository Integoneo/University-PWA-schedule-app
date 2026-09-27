package main

import (
	"time"
)

var (
	MSKLocation, _ = time.LoadLocation("Europe/Moscow")
	// Якорная дата: 7 сентября 2026 года (Четная)
	AnchorDate   = time.Date(2026, time.September, 7, 0, 0, 0, 0, MSKLocation)
	AnchorIsEven = true
)

// Дни недели для Pydantic
var DayMapping = map[time.Weekday]string{
	time.Monday:    "ПН",
	time.Tuesday:   "ВТ",
	time.Wednesday: "СР",
	time.Thursday:  "ЧТ",
	time.Friday:    "ПТ",
	time.Saturday:  "СБ",
	time.Sunday:    "ВС",
}

// GetCurrentMonday возвращает 00:00:00 понедельника текущей недели
func GetCurrentMonday(t time.Time) time.Time {
	t = t.In(MSKLocation)
	daysToSubtract := 0
	if t.Weekday() == time.Sunday {
		daysToSubtract = 6
	} else {
		daysToSubtract = int(t.Weekday()) - 1
	}

	year, month, day := t.Date()
	midnight := time.Date(year, month, day, 0, 0, 0, 0, MSKLocation)
	return midnight.AddDate(0, 0, -daysToSubtract)
}

// GetDirectusDateRange возвращает строки для фильтра _gte и _lt на 2 недели вперед
func GetDirectusDateRange(now time.Time) (string, string) {
	monday := GetCurrentMonday(now)
	// Добавляем ровно 14 дней (до начала понедельника через 2 недели)
	twoWeeksLater := monday.AddDate(0, 0, 14)

	dateGTE := monday.Format("2006-01-02T15:04:05")
	dateLT := twoWeeksLater.Format("2006-01-02T15:04:05")

	return dateGTE, dateLT
}

// IsEvenWeek определяет четность недели по якорю
func IsEvenWeek(targetDate time.Time) bool {
	targetMonday := GetCurrentMonday(targetDate)
	hoursDiff := targetMonday.Sub(AnchorDate).Hours()
	weeksDiff := int(hoursDiff / (24 * 7))

	if weeksDiff%2 == 0 {
		return AnchorIsEven
	}
	return !AnchorIsEven
}
