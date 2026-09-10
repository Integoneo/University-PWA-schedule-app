from typing import List, Optional, Any
from datetime import time, date, datetime, timezone
from uuid import UUID
from uuid6 import uuid7  # type: ignore
from sqlmodel import JSON, SQLModel, Field, Relationship, asc, ForeignKey, table, true
from enum import Enum
from zoneinfo import ZoneInfo


def get_moscow_now() -> datetime:
    return datetime.now(ZoneInfo("Europe/Moscow")).replace(tzinfo=None)


class GroupStatus(str, Enum):
    # Воркер начал работу над расписанием, но еще не закончил
    # (или расписание в процессе пересборки)
    UPDATING = "updating"

    # Всё успешно спарсилось, сохранено, готово к выдаче в PWA
    READY = "ready"

    # Расписание пришло сломанным
    ERROR = "error"


class LessonTeacherLink(SQLModel, table=True):
    __tablename__: str = "lesson_teacher_link"  # type: ignore
    lesson_id: Optional[int] = Field(
        default=None,
        foreign_key="lessons.id",
        primary_key=True,
        sa_column_args=[ForeignKey("lessons.id", ondelete="CASCADE")],
    )

    teacher_id: Optional[int] = Field(
        default=None,
        foreign_key="teachers.id",
        primary_key=True,
        sa_column_args=[ForeignKey("teachers.id", ondelete="CASCADE")],
    )


# 1. Таблица Институтов
class Institute(SQLModel, table=True):
    __tablename__: str = "institutes"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    short_name: str | None
    logo_url: Optional[str] = Field(default=None)
    groups: List["Group"] = Relationship(
        back_populates="institute",
        sa_relationship_kwargs={"order_by": "asc(Group.id)"},
    )


class Educational_form(SQLModel, table=True):
    __tablename__: str = "educational_forms"  # type: ignore
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)

    # Добавляем обратную связь для удобства
    groups: List["Group"] = Relationship(back_populates="educational_form_obj")


# 2. Таблица групп
class Group(SQLModel, table=True):
    __tablename__: str = "groups"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    course: Optional[str] = Field(default=None)
    education_form_id: int = Field(foreign_key="educational_forms.id")
    educational_form_obj: Optional[Educational_form] = Relationship(
        back_populates="groups"
    )

    start_education_date: date | None = Field(default=None)
    end_education_date: date | None = Field(default=None)

    view_url: str | None
    institute_id: int = Field(foreign_key="institutes.id")
    institute: Institute = Relationship(back_populates="groups")

    @property
    def education_form(self) -> str | None:
        return self.educational_form_obj.name if self.educational_form_obj else None

    updated_at: datetime = Field(
        default_factory=get_moscow_now, sa_column_kwargs={"onupdate": get_moscow_now}
    )

    lessons: List["Lesson"] = Relationship(
        back_populates="group",
        # Сортируем пары по дню недели (0-6), а внутри дня — по номеру пары
        sa_relationship_kwargs={
            "order_by": "asc(Lesson.is_even_week), asc(Lesson.day_of_week), asc(Lesson.number_of_lesson)"
        },
    )

    status: GroupStatus = Field(default=GroupStatus.UPDATING)
    data_hash: str = Field(index=True, max_length=16, min_length=16)


# 3. Таблица Преподавателей
class Teacher(SQLModel, table=True):
    __tablename__: str = "teachers"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    canonical_id: Optional[int] = Field(
        index=True, default=None, foreign_key="teachers.id"
    )

    lessons: List["Lesson"] = Relationship(
        back_populates="teachers", link_model=LessonTeacherLink
    )


# 4. Основная таблица Расписания
class Lesson(SQLModel, table=True):
    __tablename__: str = "lessons"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="groups.id")

    day_of_week: int = Field(ge=0, le=6)
    number_of_lesson: int
    is_even_week: bool

    start_time: time
    end_time: time

    lesson_name: str
    type_of_lesson: Optional[str] = Field(default=None)
    classroom: Optional[str] = Field(default=None)
    educational_place: str

    group: Group = Relationship(back_populates="lessons")
    teachers: List[Teacher] = Relationship(
        back_populates="lessons",
        link_model=LessonTeacherLink,
        # Сортируем преподов по алфавиту (на случай если их два на одной паре)
        sa_relationship_kwargs={"order_by": "asc(Teacher.name)"},
    )


# Микро таблица для глобальных важных конфигов для PWA приложения
# например тут будет лежать инфа
# о неделе с которой надо начать отсчет четности и нечетности
# классические конфиги формата ключ-значение
class AppConfig(SQLModel, table=True):
    __tablename__: str = "app_config"  # type: ignore

    key: str = Field(primary_key=True, index=True, max_length=32)

    value: Any = Field(sa_type=JSON)


class PWAInstalls(SQLModel, table=True):
    __tablename__: str = "pwa_installs"  # type: ignore
    device_id: UUID = Field(
        primary_key=True, unique=True, index=True, default_factory=uuid7
    )
    ip_hash: str = Field(min_length=16, max_length=16)
    os: str = Field(max_length=64)
    browser: str = Field(max_length=64)
    device_model: str = Field(max_length=64)
    device_type: str = Field(max_length=16)
    screen_resolution: str = Field(max_length=16)
    device_cpu_count: int = Field(gt=0)
    device_ram_GB: int = Field(gt=0)
    last_activity: datetime | None = Field(
        sa_column_kwargs={"onupdate": get_moscow_now}
    )
    created_at: datetime = Field(default_factory=get_moscow_now)
