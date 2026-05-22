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
    day_of_week: int  # Обрати внимание: мы ожидаем int в итоге
    start_time: time
    end_time: time
    educational_place: str
    lesson: str
    is_even_week: bool
    classroom: str = ""  # Значение по умолчанию (если поля нет, Pydantic подставит "")
    type_of_lesson: str = ""
    teachers: List[str] = Field(default_factory=list)
    number_of_lesson: Optional[int] = None

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
    institute: str = Field(alias="Institute")

    # Этого поля НЕТ в JSON! Мы сгенерируем его сами внутри валидатора
    institute_short_name: str = ""

    group: str = Field(alias="Group")

    # Проглотит отсутствие поля или подставит None
    course: Optional[str] = Field(default=None, alias="Course")
    education_form: Optional[str] = Field(default=None, alias="Education-form")

    start_education_date: date = Field(alias="Start-education-date")
    end_education_date: date = Field(alias="End-education-date")

    # ❗️ Ключ обязан быть в JSON, и в списке должна быть минимум 1 пара
    lessons: List[LessonSchema] = Field(min_length=1)

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

    # 💥 А ВОТ ТВОЯ НОРМАЛИЗАЦИЯ ИНСТИТУТА 💥
    # mode='after' означает, что Pydantic уже проверил типы полей,
    # и теперь мы можем безопасно менять сам объект (self)
    @model_validator(mode="after")
    def normalize_institute_names(self) -> "SchedulePayloadSchema":
        IGNORED_WORDS = {
            "И",
            "В",
            "НА",
            "С",
            "К",
            "ПО",
            "ЗА",
            "О",
            "ОБ",
            "У",
            "А",
            "НО",
        }

        raw_split = self.institute.split()
        short_name_chars = []

        for i, word in enumerate(raw_split):
            if word.upper() in IGNORED_WORDS:
                raw_split[i] = word.lower()
                short_name_chars.append(raw_split[i][0])
            else:
                raw_split[i] = word.capitalize()
                short_name_chars.append(raw_split[i][0])

        # Перезаписываем полное имя красивым (с заглавными буквами)
        self.institute = " ".join(raw_split)

        # Заполняем наше новое поле аббревиатурой (ИМиР)
        self.institute_short_name = "".join(short_name_chars)

        return self
