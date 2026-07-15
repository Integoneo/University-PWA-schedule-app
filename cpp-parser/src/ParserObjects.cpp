#include "ParserObjects.hpp"
#include "Utils.hpp"
#include "XLSheet.hpp"
#include <array>
#include <iostream>
#include <re2/re2.h>

ParserDictionaries::ParserDictionaries() {

	storage = {{
		{"день недели", "день", "дни", "дни недели", "день недели", "день", "дн.", "дн", "дн. недели", "день нед.",
		 "день нед", "д. недели", "дни нед."},

		{"№ пары", "№", "номер пары", "номер", "пара", "№ занятия", "пара", "№ пар", "номер", "пар.", "п/п", "№ п/п",
		 "n пары", "n", "№пары"},

		{"время", "время", "часы", "время занятий", "вр.", "вр", "вр.", "время проведения", "часы занятий",
		 "часы проведения", "период"},

		{"ауд.", "ауд", "аудитория", "каб.", "каб", "кабинет", "ауд. №", "место проведения", "место", "помещение",
		 "аудитории", "ауд", "ауд.", "каб."},

		{"вид уч. занятий", "вид занятий", "вид", "тип занятий", "вид учебных занятий", "вид уч.занятий", "вид занятия",
		 "тип", "форма проведения", "форма занятия", "форма занятий", "вид. уч. зан.", "уч. занятие", "вид уч.зан.",
		 "вид занятий"},

		{"преподаватель", "препод", "препод.", "фио преподавателя", "ф.и.о. преподавателя", "преподаватели", "фио",
		 "фио", "ф.и.о.", "преп.", "преп", "ведущий преподаватель", "фио преподавателя", "преподаватель"},

		{"нечетная неделя", "нечетная", "нечет.", "нечет", "нечетн.", "нечетн", "1 неделя", "нечётная неделя",
		 "нечётная", "нечёт.", "нечёт", "нечетная нед.", "нечётная нед.", "(нечетная)", "нечетная неделя", "нечетная"},
		{"четная неделя", "четная", "чет.", "чет", "четн.", "четн", "2 неделя", "чётная неделя", "чётная", "чёт.",
		 "чёт", "четная нед.", "чётная нед.", "(четная)", "четная неделя", "четная"},

	}}; // без двойных фигурных скобок компилятор ругается и не
		// видит внутри множеств мои строки

	EducationalPlaces = {"учебная площадка", "шаболовская", "новокузнецкая", "садовническая", "хибинский",
						 "площадка №1",		 "площадка №2", "площадка №3",	 "площадка №4",	  "edu.rguk.ru",
						 "учебной площадке", "филиал",		"саульского",	 "козлова"};
};

// Глобальный объект, доступный отовсюду (const защитит от случайного изменения)
const ParserDictionaries dictionaries;

cell::cell(int row, int col, OpenXLSX::XLWorksheet &wks)
	: columnName(getSafeString(row, col, wks)), columnCoordinate(col), rowCoordinate(row) {}

checkMap::checkMap(columnsMap &src) : map(src) {};

void checkMap::verifyName(cell &currentColumn) {

	for (int currentDict = 0; currentDict < dictionaries.ItemCounter; currentDict++) {

		if (dictionaries.storage[currentDict].contains(currentColumn.columnName)) {

			if (this->map.storage[currentDict] == -1) {
				this->map.storage[currentDict] = currentColumn.columnCoordinate;
			} else if (this->map.storage[currentDict] > 0 &&
					   currentDict >= int(dictionaries.ItemCounter) - int(this->map.OffsetCol) &&
					   currentDict < int(dictionaries.ItemCounter) - int(this->map.Skip)) {
				this->map.storage[currentDict + this->map.OffsetCol] = currentColumn.columnCoordinate;
			}
		}
	}
};

void checkMap::validateAllheaderColumns(header &currentHeader) {

	// Если мы нашли обе недели, и Четная оказалась левее Нечетной,
	// значит наши "первые находки" (Odd) на самом деле относятся к
	// Четной неделе. Просто меняем их значения местами!
	if (this->map.storage[this->map.evenWeek] != -1 && this->map.storage[this->map.oddWeek] != -1) {
		if (this->map.storage[this->map.evenWeek] < this->map.storage[this->map.oddWeek]) {
			this->map.oddEvenSwapFlag = true;
			std::swap(this->map.storage[this->map.classroomOdd], this->map.storage[this->map.classroomEven]);
			std::swap(this->map.storage[this->map.typeOfLessonOdd], this->map.storage[this->map.typeOfLessonEven]);
			std::swap(this->map.storage[this->map.teacherOdd], this->map.storage[this->map.teacherEven]);
		}
	}

	// Теперь проверяем, что все нужные колонки заполнены (не равны -1)
	currentHeader.readyHeader =
		(this->map.storage[this->map.dayOfWeek] != -1 && this->map.storage[this->map.timeOfLesson] != -1 &&
		 this->map.storage[this->map.classroomOdd] != -1 && this->map.storage[this->map.classroomEven] != -1 &&
		 this->map.storage[this->map.teacherOdd] != -1 && this->map.storage[this->map.teacherEven] != -1 &&
		 this->map.storage[this->map.oddWeek] != -1 && this->map.storage[this->map.evenWeek] != -1);
};

header findHeader(OpenXLSX::XLWorksheet &groupSchedule) {

	int rowNumberMax = 80;
	int columnNumberMax = groupSchedule.columnCount();

	header excelHeader = {.rowMax = rowNumberMax};

	static const re2::RE2 date_reg(R"((\d{2}[.\s]\d{2}[.\s]\d{4})\s*-{1,2}\s*(\d{2}[.\s]\d{2}[.\s]\d{4}))");
	static const re2::RE2 form_reg(R"((очная|заочная|очно-заочная|вечерняя|магистратура)\s+форма)");
	static const re2::RE2 course_reg(R"((\d+)\s*курс)");
	static const re2::RE2 group_reg(R"(группа\s+([а-я0-9-]+))");
	static const re2::RE2 inst_reg(R"(^((?:учебно-научный\s+)?институт\s+[а-яё\s\-]+))");

	for (int rowNumber = 1; rowNumber <= rowNumberMax; rowNumber++) {
		excelHeader.map = columnsMap{};

		excelHeader.rowCoordinate = rowNumber;

		checkMap headerTruthMap(excelHeader.map);

		for (int columnNumber = 1; columnNumber <= columnNumberMax; columnNumber++) {

			cell currentColumn = cell(rowNumber, columnNumber, groupSchedule);

			if (currentColumn.columnName == "")
				continue; // пустые ячейки сразу же скипаем
			// Если дошли сюда, значит не пустая
			headerTruthMap.verifyName(currentColumn);

			// Скипаем тяжелые регулярки для "пн", "ауд.", "лек" и т.д.
			if (currentColumn.columnName.length() < 6)
				continue;

			// === ЛОВИМ МЕТАДАННЫЕ С ПОМОЩЬЮ RE2 ===

			// Ловим название института
			if (excelHeader.meta.institute.empty()) {
				re2::RE2::PartialMatch(currentColumn.columnName, inst_reg, &excelHeader.meta.institute);
			}

			// Ловим форму обучения
			if (excelHeader.meta.educationForm.empty()) {
				re2::RE2::PartialMatch(currentColumn.columnName, form_reg, &excelHeader.meta.educationForm);
			}

			// Ловим курс
			// МАГИЯ RE2: она сама конвертирует строку в int, так как мы передаем указатель на int!
			if (excelHeader.meta.course.empty()) {
				re2::RE2::PartialMatch(currentColumn.columnName, course_reg, &excelHeader.meta.course);
			}

			// Ловим группу
			if (excelHeader.meta.groupName.empty()) {
				re2::RE2::PartialMatch(currentColumn.columnName, group_reg, &excelHeader.meta.groupName);
			}

			// Ловим даты
			if (excelHeader.meta.startDate.empty() && currentColumn.columnName.length() >= 15) {
				// Новая регулярка: ловит И точки, И пробелы, И двойные тире

				std::string start_date, end_date;

				// Передаем ОРИГИНАЛЬНУЮ строку, не удаляя пробелы заранее!
				if (re2::RE2::PartialMatch(currentColumn.columnName, date_reg, &start_date, &end_date)) {

					// Лечим опечатки секретарши: меняем найденные пробелы на точки
					std::replace(start_date.begin(), start_date.end(), ' ', '.');
					std::replace(end_date.begin(), end_date.end(), ' ', '.');

					excelHeader.meta.startDate = start_date;
					excelHeader.meta.endDate = end_date;
				}
			}
			headerTruthMap.validateAllheaderColumns(excelHeader);
			if (excelHeader.readyHeader) {

				if (excelHeader.meta.groupName.empty()) {
					excelHeader.meta.groupName = groupSchedule.name();
				}

				return excelHeader;
			}
		}
	}
	return excelHeader;
}

void scanner::extractRow() {
	std::array<int, scanner::scheduleRow::Index::EndOfCommonCells> &headerIndexes = this->head.map.storage;
	this->rowObject = scheduleRow{};

	int counterOfValiableCells = 0;
	int counterOfEducationalStrings = 0;

	bool has_payload = false; // флаг наличия полезной информационной нагрузки в строке
							  // этим являются:
							  //
							  // classroomOdd,	  // 3
							  // typeOfLessonOdd,  // 4
							  // teacherOdd,		  // 5
							  // lessonOdd,		  // 6
							  // lessonEven,		// 7
							  // classroomEven,	  // 8
							  // typeOfLessonEven, // 9
							  // teacherEven,	  // 10

	for (int currentCell = 0; currentCell < this->rowObject.Index::EndOfCommonCells; currentCell++) {
		bool doesColumnExist = headerIndexes[currentCell] > 0;
		std::string currentString = "";
		if (doesColumnExist) {
			currentString = getSafeString(this->currentRow, headerIndexes[currentCell], this->groupSchedule, true);

			if (currentString != "") {
				// Я считаю количество значащих ячеек, что бы вычислить строчки обозначающие учебные площадки
				// если количество значащих ячеек == количеству ячеек которые говорят о учебных площадках
				// то это строка статуса EducationalPlaces
				counterOfValiableCells += 1;

				// 2. Локальный флаг: считаем, что пока это НЕ площадка
				bool is_educational_place = false;

				for (std::string s : dictionaries.EducationalPlaces) {

					std::string lowerForCheck = toLowerUTF8Cyrillic(currentString);
					// приводим для проверки к малому регистру, просто что бы не раздувать словарь учебных площадок
					if (lowerForCheck.find(s) != std::string::npos) {
						counterOfEducationalStrings += 1;
						is_educational_place = true; // 3. Нашли площадку! Меняем флаг.
						if (this->rowObject.educationalIndexes.size() < 2) {
							this->rowObject.educationalIndexes.emplace_back(currentCell);
						} else {
							// TODO: в будущем в логгере выдвать предупреждение
							// но посути используем те 2 площадки которые уже нашли
						}
						break;
					}
				}

				if (!is_educational_place && currentCell >= scanner::scheduleRow::Index::classroomOdd) {
					has_payload = true; // Засекли полезную нагрузку
				}
			}

			this->rowObject.storage[currentCell] = currentString;
		}
	}

	std::string &time = this->rowObject.storage[this->rowObject.Index::timeOfLesson];
	std::string &number = this->rowObject.storage[this->rowObject.Index::numberOfLesson];
	// будем выдавать статус LessonRow по валидному наличию строк timeOfLesson и numberOfLesson
	// вывел их в сыллочнные переменные что бы было не громоздким при проверке этих условий

	// 1. Проверка number на число (все символы - цифры)
	bool is_num = !number.empty() && std::ranges::all_of(number, ::isdigit);

	// 2. Проверка time на ЧЧ:ММ по регулярке  \d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}
	bool is_time = re2::RE2::PartialMatch(time, this->time_state_reg);
	if (counterOfValiableCells == 0) {
		this->currentStatus = scanner::response::EmptyRow;
	} else if (counterOfValiableCells == counterOfEducationalStrings && counterOfValiableCells < 3) {

		// ------------------------------------------------------------------------------------------
		// выдача строки с учебными площадками, логика простая, если она одна, то она идет на
		// четную и нечетную неделю, если их 2 то левая на нечетную, правая на четную
		// загвоздка в том что я хз как использовать oddEvenFlagSwap - потому что если использую его
		// то это будет некорректо работать даже если деканат реально решит свапнуть расположение недель
		// ------------------------------------------------------------------------------------------
		if (counterOfEducationalStrings == 1) {
			this->rowObject.storage[this->rowObject.Index::educationalPlaceEven] =
				this->rowObject.storage[this->rowObject.educationalIndexes[0]];

			this->rowObject.storage[this->rowObject.Index::educationalPlaceOdd] =
				this->rowObject.storage[this->rowObject.educationalIndexes[0]];
		}

		if (counterOfEducationalStrings == 2) {
			this->rowObject.storage[this->rowObject.Index::educationalPlaceEven] =
				this->rowObject.storage[this->rowObject.educationalIndexes[0]];

			this->rowObject.storage[this->rowObject.Index::educationalPlaceOdd] =
				this->rowObject.storage[this->rowObject.educationalIndexes[1]];
		}

		// TODO: можно сделать это лаконичнее но я хз как пересоздать мой массив в rowObject и одновременно
		// забрать оттуда ячейки с площадками, можно исправить позже, пока пускай будет так
		for (int currentCell = 0; currentCell < this->rowObject.Index::EndOfCommonCells; currentCell++) {
			this->rowObject.storage[currentCell] = "";
		}

		this->currentStatus = scanner::response::EducationalPlaces;
	} else if (is_time) {

		if (has_payload) {
			this->currentStatus = scanner::response::LessonRow;
		} else {
			this->currentStatus = scanner::response::BlankLessonRow;
		}
	} else {
		this->currentStatus = scanner::response::ErrorRow;
	}
};

void scanner::nextRow() { this->currentRow += 1; };

void scanner::printDebugInfo() const {
	std::cout << "------------------------------\n";

	// Преобразуем статус в строку для читаемости
	std::string statusStr;
	switch (currentStatus) {
	case response::Initialized:
		statusStr = "Инициализация";
		break;
	case response::LessonRow:
		statusStr = "Строка с парой";
		break;
	case response::BlankLessonRow:
		statusStr = "Строка пустой пары";
		break;
	case response::EducationalPlaces:
		statusStr = "Учебные площадки";
		break;
	case response::EmptyRow:
		statusStr = "Пустая строка";
		break;
	case response::ErrorRow:
		statusStr = "Ошибка";
		break;
	default:
		statusStr = "НЕИЗВЕСТНО";
		break;
	}

	std::cout << "статус: " << statusStr << ", номер строки: " << currentRow << "\n";

	// Массив с русскими именами ячеек (порядок строго совпадает с enum Index)
	const std::string indexNames[] = {"День недели",
									  "Номер пары",
									  "Время",
									  "Аудитория (нечетная)",
									  "Тип занятия (нечетная)",
									  "Преподаватель (нечетная)",
									  "Предмет (нечетная)",
									  "Предмет (четная)",
									  "Аудитория (четная)",
									  "Тип занятия (четная)",
									  "Преподаватель (четная)",
									  "Маркер конца общих ячеек",
									  "Площадка (нечетная)",
									  "Площадка (четная)"};

	// Выводим все ячейки из storage
	for (int i = 0; i < scheduleRow::Index::ItemCounter; ++i) {
		if (i == scheduleRow::Index::EndOfCommonCells)
			continue; // Пропускаем маркер

		std::cout << indexNames[i] << ": " << rowObject.storage[i] << "\n";
	}

	std::cout << "------------------------------\n";
}
