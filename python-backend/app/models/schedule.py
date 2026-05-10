from typing import List, Optional
from datetime import time, date, datetime, timezone
from sqlmodel import SQLModel, Field, Relationship


class LessonTeacherLink(SQLModel, table=True):
    __tablename__: str = "lesson_teacher_link"  # type: ignore
    lesson_id: Optional[int] = Field(
        default=None, foreign_key="lessons.id", primary_key=True
    )
    teacher_id: Optional[int] = Field(
        default=None, foreign_key="teachers.id", primary_key=True
    )


# 1. Таблица Институтов
class Institute(SQLModel, table=True):
    __tablename__: str = "institutes"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)

    groups: List["Group"] = Relationship(back_populates="institute")


# 2. Таблица групп
class Group(SQLModel, table=True):
    __tablename__: str = "groups"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    course: str
    education_form: str

    # Даты обучения (настоящий тип Date)
    start_education_date: date
    end_education_date: date

    institute_id: int = Field(foreign_key="institutes.id")
    institute: Optional[Institute] = Relationship(back_populates="groups")
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    lessons: List["Lesson"] = Relationship(back_populates="group")


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

    day_of_week: str
    number_of_lesson: int
    is_even_week: bool

    start_time: time
    end_time: time

    lesson_name: str
    type_of_lesson: str
    classroom: str
    educational_place: str

    group: Optional[Group] = Relationship(back_populates="lessons")
    teachers: List[Teacher] = Relationship(
        back_populates="lessons", link_model=LessonTeacherLink
    )


# Микро таблица для глобальных важных конфигов для PWA приложения
# например тут будет лежать инфа
# о неделе с которой надо начать отсчет четности и нечетности
# классические конфиги формата ключ-значение
class AppConfig(SQLModel, table=True):
    __tablename__: str = "app_config"  # type: ignore

    key: str = Field(primary_key=True)

    value: str
