from collections import defaultdict
from typing import List, Tuple, Set
from .schemas import LessonSchema


def can_merge_lessons(lesson1: LessonSchema, lesson2: LessonSchema) -> bool:
    """
    Проверяет, можно ли склеить две пары в одну.
    Условие: стыковка по времени и полное совпадение метаданных.
    Работает с Pydantic объектами.
    """
    # 1. Проверяем непрерывность времени (конец первой == начало второй)
    if lesson1.end_time != lesson2.start_time:
        return False

    # 2. Проверяем строковые поля напрямую через атрибуты
    if lesson1.lesson != lesson2.lesson:
        return False
    if lesson1.classroom != lesson2.classroom:
        return False
    if lesson1.educational_place != lesson2.educational_place:
        return False
    if lesson1.type_of_lesson != lesson2.type_of_lesson:
        return False

    # 3. Проверяем преподавателей (через множества, чтобы игнорировать порядок)
    if set(lesson1.teachers) != set(lesson2.teachers):
        return False

    return True


def merge_lessons_logic(
    lessons: List[LessonSchema],
) -> Tuple[List[LessonSchema], Set[str]]:
    """
    Раскладывает пары по дням недели, сортирует, схлопывает идущие подряд
    и возвращает кортеж: (Итоговый_список_пар, Множество_всех_уникальных_преподавателей).
    """
    lessons_by_week = {
        False: defaultdict(list),
        True: defaultdict(list),
    }

    unique_teachers: Set[str] = set()

    # =================================================================
    # 1. ГРУППИРОВКА И СБОР МЕТАДАННЫХ (Один проход O(N))
    # =================================================================
    for lesson in lessons:
        lessons_by_week[lesson.is_even_week][lesson.day_of_week].append(lesson)
        # Собираем всех преподавателей прямо здесь! Метод update добавляет списки в set
        unique_teachers.update(lesson.teachers)

    # =================================================================
    # 2. СОРТИРОВКА ВНУТРИ ДНЕЙ
    # =================================================================
    for is_even in lessons_by_week:
        for day in lessons_by_week[is_even]:
            # Теперь обращаемся к атрибуту Pydantic модели (lesson.start_time)
            lessons_by_week[is_even][day].sort(key=lambda x: x.start_time)

    # =================================================================
    # 3. СХЛОПЫВАНИЕ ПАР И НУМЕРАЦИЯ (За один проход)
    # =================================================================
    final_merged_lessons: List[LessonSchema] = []

    for is_even in lessons_by_week:
        for day in lessons_by_week[is_even]:
            daily_lessons = lessons_by_week[is_even][day]

            if not daily_lessons:
                continue

            merged_day: List[LessonSchema] = []
            current_lesson = daily_lessons[0]
            current_lesson_number = 1

            for next_lesson in daily_lessons[1:]:
                if can_merge_lessons(current_lesson, next_lesson):
                    # Схлопываем!
                    current_lesson.end_time = next_lesson.end_time
                else:
                    # Схлопывание прервалось.
                    current_lesson.number_of_lesson = current_lesson_number
                    merged_day.append(current_lesson)

                    current_lesson_number += 1
                    # Берем следующую пару за новую основу
                    current_lesson = next_lesson

            # 👈 Не забываем проставить номер самой последней паре в дне!
            current_lesson.number_of_lesson = current_lesson_number
            merged_day.append(current_lesson)

            # Добавляем готовые пары этого дня в общий плоский список
            final_merged_lessons.extend(merged_day)

    return final_merged_lessons, unique_teachers
