from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import time, date


class Groups_PWA_schema(BaseModel):
    id: int
    name: str
    course: str | None
    education_form: str | None

    model_config = ConfigDict(from_attributes=True)


class Institutes_PWA_schema(BaseModel):
    id: int
    name: str
    short_name: str
    logo_url: str | None
    groups: List[Groups_PWA_schema]

    model_config = ConfigDict(from_attributes=True)


class TeacherPWA(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class LessonPWA(BaseModel):
    id: int
    day_of_week: int
    number_of_lesson: int
    is_even_week: bool
    start_time: time
    end_time: time
    lesson_name: str
    type_of_lesson: Optional[str] = None
    classroom: Optional[str] = None
    educational_place: str
    teachers: List[TeacherPWA]  # Вложенные преподаватели

    model_config = ConfigDict(from_attributes=True)


class GroupScheduleResponse(BaseModel):
    status: str
    start_education_date: Optional[date]
    end_education_date: Optional[date]
    view_url: Optional[str]
    lessons: List[LessonPWA]

    model_config = ConfigDict(from_attributes=True)


class InstallPWAPayload(BaseModel):
    screen_width: int = Field(gt=0, le=99999)
    screen_height: int = Field(gt=0, le=99999)
    device_ram_GB: int = Field(gt=0, le=128)
    device_cpu_count: int = Field(gt=0, le=64)

    model_config = ConfigDict(from_attributes=True)


# INFO: Для эндпоинтов с учителями


class TeacherLessonPWA(BaseModel):
    day_of_week: int
    is_even_week: bool
    lesson_name: str
    type_of_lesson: Optional[str]
    classroom: Optional[str]
    educational_place: str
    start_time: time
    end_time: time
    groups: List[str]  # Массив групп, которые мы собрали через array_agg

    model_config = ConfigDict(from_attributes=True)


class TeacherScheduleResponse(BaseModel):
    # Оборачиваем в словарь {"lessons": [...]}, чтобы сохранить
    # консистентность с эндпоинтом групп, где тоже есть корневые ключи
    lessons: List[TeacherLessonPWA]
