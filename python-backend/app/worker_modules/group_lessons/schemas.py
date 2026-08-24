from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime, date, time
from typing import List, Optional

# Маппинг дней недели (выносим константу)
DAY_MAPPING = {
    "ПН": 0,
    "ПО": 0,
    "MO": 0,
    "ВТ": 1,
    "TU": 1,
    "СР": 2,
    "WE": 2,
    "ЧТ": 3,
    "ЧЕ": 3,
    "TH": 3,
    "ПТ": 4,
    "ПЯ": 4,
    "FR": 4,
    "СБ": 5,
    "СУ": 5,
    "SA": 5,
    "ВС": 6,
    "ВО": 6,
    "SU": 6,
}


class LessonSchema(BaseModel):
    day_of_week: int
    start_time: time
    end_time: time
    educational_place: str
    lesson: str
    is_even_week: bool
    classroom: str = ""  # Значение по умолчанию (если поля нет, Pydantic подставит "")
    type_of_lesson: str = ""
    teachers: List[str] = Field(default_factory=list)
    number_of_lesson: Optional[int] = None

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def fix_short_time(cls, v):
        if isinstance(v, str) and v.strip():
            v = v.strip()
            parts = v.split(":")
            # Если время "9:15", делаем "09:15"
            if len(parts) == 2 and len(parts[0]) == 1:
                return f"0{v}"
        return v

    # Учим Pydantic конвертировать строку "ПН" в int 0 ПЕРЕД валидацией
    @field_validator("day_of_week", mode="before")
    @classmethod
    def parse_day(cls, v):
        if not isinstance(v, str):
            raise ValueError("day_of_week должен быть строкой")
        prefix = v.strip().upper()[:2]
        if prefix not in DAY_MAPPING:
            raise ValueError(f"Неизвестный формат дня недели: {prefix}")
        return DAY_MAPPING[prefix]

    # Если в educational_place или lesson прислали "", Pydantic выдаст ошибку
    @field_validator("educational_place", "lesson", mode="after")
    @classmethod
    def not_empty(cls, v: str):
        if not v.strip():
            raise ValueError("Обязательное строковое поле не может быть пустым")
        return v.strip()


class SchedulePayloadSchema(BaseModel):
    # Ожидаем сырую строку из JSON, например "институт мехатроники..."
    institute: str = Field(alias="institute")

    # Этого поля НЕТ в JSON! Мы сгенерируем его сами внутри валидатора
    institute_short_name: str = ""

    group: str = Field(alias="group")

    # Проглотит отсутствие поля или подставит None
    course: Optional[str] = Field(default=None, alias="course")
    education_form: Optional[str] = Field(default=None, alias="education-form")

    start_education_date: date = Field(alias="start-education-date")
    end_education_date: date = Field(alias="end-education-date")

    # ❗️ Ключ обязан быть в JSON, и в списке должна быть минимум 1 пара
    lessons: List[LessonSchema] = Field(min_length=1)
    view_url: str = ""
    logo_url: str = ""

    @field_validator("start_education_date", "end_education_date", mode="before")
    @classmethod
    def parse_dates(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v, "%d.%m.%Y").date()
        return v

    @field_validator("group", mode="after")
    @classmethod
    def normalize_group(cls, v: str):
        return v.strip().upper().replace(" ", "")

    @field_validator("education_form", mode="before")
    @classmethod
    def normalize_educational_form(cls, v: str):
        return v.strip().title()
