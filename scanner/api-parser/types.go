package main

import "time"

// Результат запроса
type FetchResult struct {
	StatusCode int
	Body       []byte
	ETag       string
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

type DirectusScheduleResponse struct {
	Data []DirectusLessonItem `json:"data"`
}

type DirectusLessonItem struct {
	DateStart              string                `json:"date_start"`
	DateEnd                string                `json:"date_end"`
	Description            *string               `json:"description"`
	TypeOfEmployment       *TypeOfEmployment     `json:"type_of_employment"`
	Auditories             []AuditoryContainer   `json:"auditories"`
	Teachers               []TeacherContainer    `json:"teachers"`
	GroupsPlansDisciplines []DisciplineContainer `json:"groups_plans_disciplines"`
}

type TypeOfEmployment struct {
	ShortName string `json:"short_name"`
}

type AuditoryContainer struct {
	AuditoriesID struct {
		Name string `json:"name"`
	} `json:"auditories_id"`
}

type TeacherContainer struct {
	TeachersID struct {
		Name string `json:"name"`
	} `json:"teachers_id"`
}

type DisciplineContainer struct {
	GroupsPlansDisciplinesID struct {
		PlanDiscipline struct {
			Discipline struct {
				Name string `json:"name"`
			} `json:"discipline"`
		} `json:"plan_discipline"`
	} `json:"groups_plans_disciplines_id"`
}

// --- Целевая Pydantic-схема ---

type LessonSchema struct {
	DayOfWeek        string   `json:"day_of_week"` // Строка "ПН", "ВТ" для Pydantic
	StartTime        string   `json:"start_time"`  // "09:15"
	EndTime          string   `json:"end_time"`    // "10:35"
	EducationalPlace string   `json:"educational_place"`
	Lesson           string   `json:"lesson"`
	IsEvenWeek       bool     `json:"is_even_week"`
	Classroom        string   `json:"classroom"`
	TypeOfLesson     string   `json:"type_of_lesson"`
	Teachers         []string `json:"teachers"`
	NumberOfLesson   *int     `json:"number_of_lesson"`
}

type SchedulePayloadSchema struct {
	Institute          string         `json:"institute"`
	InstituteShortName string         `json:"institute_short_name"`
	Group              string         `json:"group"`
	Course             *string        `json:"course"`
	EducationForm      string         `json:"education-form"` // Именно с дефисом (alias в Pydantic)
	StartEducationDate *string        `json:"start-education-date"`
	EndEducationDate   *string        `json:"end-education-date"`
	Lessons            []LessonSchema `json:"lessons"`
	ViewURL            string         `json:"view_url"`
	LogoURL            string         `json:"logo_url"`
	Type               string         `json:"type"` // "lessons"
}

type GroupActivityTrackSchema struct {
	InstituteShortName string    `json:"institute_short_name"`
	Group              string    `json:"group"`
	Course             string    `json:"course"`
	LastUploadTime     time.Time `json:"last_upload_time"`
}
