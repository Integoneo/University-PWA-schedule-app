from typing import List, Optional, Any
from datetime import time, date, datetime, timezone
from sqlmodel import JSON, SQLModel, Field, Relationship, asc, ForeignKey
from enum import Enum


def get_utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class GroupStatus(str, Enum):
    # Воркер начал работу над расписанием, но еще не закончил
    # (или расписание в процессе пересборки)
    UPDATING = "updating"

    # Всё успешно спарсилось, сохранено, готово к выдаче в PWA
    READY = "ready"

    # Расписание пришло сломанным, деканат накосячил, нужна ручная проверка
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
    short_name: str
    logo_url: Optional[str] = Field(default=None)
    groups: List["Group"] = Relationship(
        back_populates="institute",
        sa_relationship_kwargs={"order_by": "asc(Group.id)"},
    )


# 2. Таблица групп
class Group(SQLModel, table=True):
    __tablename__: str = "groups"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    course: Optional[str] = Field(default=None)
    education_form: Optional[str] = Field(default=None)

    start_education_date: date
    end_education_date: date

    view_url: str | None
    institute_id: int = Field(foreign_key="institutes.id")
    institute: Institute = Relationship(back_populates="groups")
    updated_at: datetime = Field(
        default_factory=get_utc_now, sa_column_kwargs={"onupdate": get_utc_now}
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
