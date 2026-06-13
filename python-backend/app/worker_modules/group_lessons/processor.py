from sqlmodel import select, delete, func, col
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schedule import Institute, Group, Teacher, Lesson, GroupStatus
from .schemas import SchedulePayloadSchema
from .utils import merge_lessons_logic


class ORMStateError(Exception):
    pass


async def process_schedule(
    session: AsyncSession, schedule: SchedulePayloadSchema, raw_hash: str
):
    """
    Основная логика обновления расписания.
    Принимает УЖЕ валидированные данные от Pydantic.
    """
    # ❌ Удален вызов normalize_name, так как Pydantic уже сгенерировал
    # schedule.institute и schedule.institute_short_name

    # === БЛОК 1: ИНСТИТУТ И ГРУППА ===
    request = select(Institute).where(
        func.similarity(Institute.name, schedule.institute) >= 0.90,
        Institute.short_name == schedule.institute_short_name,
    )
    inst_match = (await session.scalars(request)).first()

    if not inst_match:
        inst_match = Institute(
            name=schedule.institute, short_name=schedule.institute_short_name
        )
        session.add(inst_match)
        await session.flush()

    # 🛡 TYPE GUARD: Успокаиваем Pyright, доказывая, что ID точно есть
    if inst_match.id is None:
        raise ORMStateError(
            f"Аномалия БД: Институту '{schedule.institute}' не присвоен ID"
        )

    request = select(Group).where(
        col(Group.institute_id) == inst_match.id,
        Group.name == schedule.group,
    )
    group_match = (await session.scalars(request)).first()

    if not group_match:
        group_match = Group(
            name=schedule.group,
            course=schedule.course,
            education_form=schedule.education_form,
            start_education_date=schedule.start_education_date,
            end_education_date=schedule.end_education_date,
            institute_id=inst_match.id,
            data_hash=raw_hash,
        )
        session.add(group_match)
        await session.flush()
    else:
        # Если хэши совпали - расписание не менялось
        if group_match.data_hash == raw_hash:
            return

        # 🛡 TYPE GUARD: Защита перед delete запросом
        if group_match.id is None:
            raise ORMStateError(
                f"Аномалия БД: Группе '{schedule.group}' не присвоен ID"
            )

        # Удаляем старые пары
        await session.execute(
            delete(Lesson).where(col(Lesson.group_id) == group_match.id)
        )
        group_match.data_hash = raw_hash
        group_match.start_education_date = schedule.start_education_date
        group_match.end_education_date = schedule.end_education_date
        session.add(group_match)
        await session.flush()

    if group_match.id is None:
        raise ORMStateError("Аномалия БД: Потерян ID группы перед сохранением пар")

    # === БЛОК 2: СОРТИРОВКА И СХЛОПЫВАНИЕ ПАР ===
    merged_lessons_list, unique_teacher_names = merge_lessons_logic(schedule.lessons)

    teacher_cache = {}
    if unique_teacher_names:
        request = select(Teacher).where(col(Teacher.name).in_(unique_teacher_names))
        existing_teachers = await session.scalars(request)
        teacher_cache = {t.name: t for t in existing_teachers if t.name}

        missing_names = unique_teacher_names - set(teacher_cache.keys())

        if missing_names:
            new_teachers = [Teacher(name=name) for name in missing_names]
            session.add_all(new_teachers)
            await session.flush()
            for t in new_teachers:
                if t.name:
                    teacher_cache[t.name] = t

    # === БЛОК 4: ДОБАВЛЕНИЕ ПАР В БД ===
    for lesson in merged_lessons_list:
        lesson_teacher_objs = [teacher_cache[name] for name in lesson.teachers]

        # 🛡 УСПОКАИВАЕМ PYRIGHT: Гарантируем, что алгоритм выше отработал верно
        assert lesson.number_of_lesson is not None, (
            "Логическая ошибка: паре не был присвоен номер!"
        )

        new_lesson = Lesson(
            day_of_week=lesson.day_of_week,
            start_time=lesson.start_time,
            end_time=lesson.end_time,
            lesson_name=lesson.lesson,
            educational_place=lesson.educational_place,
            is_even_week=lesson.is_even_week,
            number_of_lesson=lesson.number_of_lesson,
            classroom=lesson.classroom,
            type_of_lesson=lesson.type_of_lesson,
            group_id=group_match.id,
            teachers=lesson_teacher_objs,
        )
        session.add(new_lesson)

    group_match.status = GroupStatus.READY
    await session.commit()


# Почитать при рефакторинге анализ моего алгоритма от нейронки:
# Анализ алгоритма `process_schedule` показывает, что мы имеем дело с задачей, где **алгоритмическая сложность вторична по сравнению с задержками ввода-вывода (I/O bound)**.
#
# Однако, если оценивать чисто вычислительную составляющую и работу с памятью относительно количества пар ($N$ — количество уроков в payload), расклад следующий.
#
# ---
#
# ### 1. Асимптотическая сложность
#
# Пусть $N$ — количество записей (уроков) в `schedule.lessons`, а $T$ — количество уникальных преподавателей.
#
# #### Временная сложность: $O(N \log N)$
#
# 1. **Блок 1 (Институты/Группы):** Здесь выполняются SQL-запросы к БД. Для алгоритма это $O(1)$ относительно количества уроков $N$, так как сложность зависит от размера индекса в БД, а не от количества входящих данных.
# 2. **Блок 2 (Сортировка/Схлопывание):** Вызов `merge_lessons_logic`. Большинство алгоритмов группировки и сортировки требуют $O(N \log N)$. Это самый "тяжелый" этап для CPU.
# 3. **Блок 3 (Работа с учителями):**
# * Поиск учителей (`select...in_`): $O(T \cdot \log T)$ (в зависимости от реализации индекса в БД).
# * Создание кэша учителей: $O(T)$.
#
#
# 4. **Блок 4 (Вставка пар):** Цикл по $N$ элементов. Внутри цикла — операции в памяти, $O(N)$.
#
# **Итог:** Доминирующим фактором является сортировка/группировка, поэтому общая сложность — **$O(N \log N)$**.
#
# #### Пространственная сложность: $O(N)$
#
# Алгоритм требует памяти для хранения промежуточных структур:
#
# * `merged_lessons_list`: хранит $N$ объектов.
# * `teacher_cache`: хранит $T$ объектов.
# * Объекты ORM перед коммитом: создается $N$ объектов `Lesson`.
#
# По мере роста $N$, потребление оперативной памяти будет расти **линейно**.
#
# ---
#
# ### 2. Главный «бутылочное горлышко» (Bottleneck)
#
# В реальном мире **Big O notation здесь почти бесполезна**, так как ваш алгоритм является **I/O-bound** (зависит от сети и диска).
#
# **Основные потери производительности:**
#
# 1. **Многократные `await session.flush()**`: В коде встречается несколько вызовов `flush()`. Каждый `flush` — это сетевой запрос к базе данных. Если данных много, это превращает алгоритм в последовательную цепочку "ожидание-запись-ожидание".
# 2. **Цикличный `session.add(new_lesson)**`: В 4-м блоке вы вызываете `session.add` внутри цикла. Хотя `session.add` лишь помечает объект как "отслеживаемый" (не делает запрос), при `session.commit()` ORM будет отправлять огромное количество `INSERT` запросов.
#
# ---
#
# ### 3. Рекомендации по оптимизации
#
# Если вы хотите, чтобы код работал быстрее при большом количестве уроков (например, 1000+ пар):
#
# 1. **Массовая вставка (Bulk Insert):**
# Вместо добавления через `session.add` в цикле, используйте `session.execute` с `insert(Lesson).values([...])`. Это выполнит одну операцию вставки вместо $N$ запросов.
# ```python
# # Примерно так:
# from sqlalchemy import insert
# stmt = insert(Lesson).values([lesson_dict1, lesson_dict2, ...])
# await session.execute(stmt)
#
# ```
#
#
# 2. **Минимизация Flush:**
# Постарайтесь свести к минимуму `await session.flush()`. В идеале:
# * Вытащить всё необходимое (Институт, Группа, Учителя).
# * Сформировать все объекты данных.
# * Один раз выполнить удаление старых данных (`delete`).
# * Один раз выполнить массовую вставку новых данных (`bulk_insert`).
# * Один раз `commit`.
#
#
# 3. **Индексы:**
# Убедитесь, что у вас стоят индексы на `Teacher.name`, `Group.name` и `Group.institute_id`, иначе операции `select` превратятся из почти мгновенных в $O(M)$ (где $M$ — число всех записей в таблице), что замедлит работу алгоритма на порядки при росте БД.
#
# **Резюме:** Алгоритм написан чисто, но с точки зрения производительности базы данных он "болтливый" (много мелких запросов). Переход на `bulk operations` сделает его значительно эффективнее при больших объемах данных.
