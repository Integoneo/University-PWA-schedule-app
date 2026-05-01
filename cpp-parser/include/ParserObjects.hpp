#pragma once

#include <OpenXLSX.hpp>
#include <array>
#include <re2/re2.h>
#include <string>
#include <unordered_set>
#include <vector>
// Словарь возможных вариантов написания колонок, на случай
// если деканат вдруг допустит орфографическую ошибку в колонках за которые я цепляюсь
struct ParserDictionaries {

	enum Index {
		dayOfWeek,
		numberOfLesson,
		timeOfLesson,
		classroom,
		typeOfLesson,
		teacher,
		oddWeek,
		evenWeek,

		ItemCounter,

	};

	std::array<std::unordered_set<std::string>, Index::ItemCounter> storage;
	std::vector<std::string> EducationalPlaces;

	ParserDictionaries();
};

extern const ParserDictionaries dictionaries;

struct cell {
	std::string columnName;
	int columnCoordinate;
	int rowCoordinate;
	cell(int row, int col, OpenXLSX::XLWorksheet &wks);
};

struct columnsMap {
	enum Index {
		dayOfWeek,		 // 0
		numberOfLesson,	 // 1
		timeOfLesson,	 // 2
		classroomOdd,	 // 3
		typeOfLessonOdd, // 4
		teacherOdd,		 // 5
		// ----------- КОЛОНКИ КОТОРЫЕ НОРМАЛЬЕ --Skip=2-------
		// -------- НО ИХ НАДО СКИПАТЬ ДЛЯ УЧЕТА OFFSET --------
		oddWeek,  // 6
		evenWeek, // 7
		// -------------КОЛОНКИ-ДУБЛИКАТЫ---N=3--------------
		classroomEven,	  // 8
		typeOfLessonEven, // 9
		teacherEven,	  // 10
		// -------------КОЛОНКИ-ДУБЛИКАТЫ---N=3--------------
		ItemCounter, // 11
					 // неявное задание размера массива Storage

		Skip = 2,
		N = 3,
		OffsetCol = 5 // OffsetCol = N + Skip = 5
	};

	static constexpr std::array<int, Index::ItemCounter> create_default() {
		std::array<int, Index::ItemCounter> temp{};
		temp.fill(-1);
		return temp;
	};

	std::array<int, Index::ItemCounter> storage = create_default();
	bool oddEvenSwapFlag = false; // в обычном случае идет сначала нечетная потом четная неделя
};

struct ScheduleMetadata {
	std::string groupName = "";
	std::string startDate = "";
	std::string endDate = "";
	std::string educationForm = ""; // Очная/Заочная/Вечерняя/Магистратура
	std::string course = "";
};

struct header {
	int rowCoordinate;
	int rowMax;
	bool readyHeader = false;
	columnsMap map;
	ScheduleMetadata meta;
};

struct checkMap {
	columnsMap &map;

	checkMap(columnsMap &src);

	void verifyName(cell &currentColumn);

	void validateAllheaderColumns(header &currentHeader);
};

header findHeader(OpenXLSX::XLWorksheet &groupSchedule);

struct scanner {
	// Аксиомы моего парсера, если деканат их нарушает,
	// значит такова жизнь, значит мой парсер сломали,
	// далее приведены аксиомы на которые парсер опирается:
	// ----------------------------------------
	// . Расписание само по себе прямоугольное и для шапки и
	// ячеек ниже шапки впринципе вообще
	// обьединение ячеек не используется
	// ---------------------------------------
	// 2. ячейки вне прямоугольника таблицы - мусор
	enum class response {
		Initialized, // статус только созданного сканнера
		LessonRow,	 // Статус строки где записана самая обычная пара
		BlankLessonRow,
		// Учебные площадки записываются в отдельных строках над всеми днями недели обычно
		EducationalPlaces, // одна и та же учебная площадка для четной
		// и нечетной недели в этот день
		// на разных учебных прощадках
		EmptyRow, // сюда пойдут строки которые содержат ничего а так же строки
		// которые указывают что пары в это время нет
		ErrorRow // Строки ошибки - вообще хз что сюда помещать сюда
	};

	OpenXLSX::XLWorksheet &groupSchedule;
	header head;
	response currentStatus;
	int currentRow;

	struct scheduleRow {
		// HACK: Мне вообще не нравится что я постоянно должен думать соответсвуют ли у меня 3 enum друг другу
		// когда буду рефакторить надо как то сделать это лаконично что бы об этом вообще не приходилось думать
		enum Index {
			dayOfWeek,		  // 0
			numberOfLesson,	  // 1
			timeOfLesson,	  // 2
			classroomOdd,	  // 3
			typeOfLessonOdd,  // 4
			teacherOdd,		  // 5
			lessonOdd,		  // 6 (соответствует oddWeek из columnsMap)
			lessonEven,		  // 7 (соответствует evenWeek из columnsMap)
			classroomEven,	  // 8
			typeOfLessonEven, // 9
			teacherEven,	  // 10

			EndOfCommonCells, // 11 - Хак с площадками

			educationalPlaceOdd,  // 12
			educationalPlaceEven, // 13

			ItemCounter,
			// HACK: записали ренжи для цикла который будет делать json
			oddInfoStart = classroomOdd, //  Range указывались включительно до то есть в цикле писать <=
			oddInfoEnd = lessonOdd,
			evenInfoStart = lessonEven,
			evenInfoEnd = teacherEven,
			individualItemCounter =
				oddInfoEnd - oddInfoStart + 1 // просто счтиаю количество индивидуальных полей
											  // мне нужно это число что бы не делать пустых json записей lessons
		};

		static constexpr std::array<std::string_view, Index::ItemCounter> IndexNames = {
			"day_of_week",		 "number_of_lesson", "time_slot", "classroom",
			"type_of_lesson",	 "teacher",			 "lesson",	  "lesson",
			"classroom",		 "type_of_lesson",	 "teacher",	  "plug",
			"educational_place", "educational_place"};
		// HACK: очень грязный способ прописать соответсвенные имена для json полей для отправки на сервер,
		// сделано просто чтобы не плодить if и написать все в цикле
		std::array<std::string, Index::ItemCounter> storage = {};
		std::vector<int> educationalIndexes = {}; // Размер 2 чисто потому что площадки максимум может быть 2
												  // по другому никак
	};

	scheduleRow rowObject;

	static inline const re2::RE2 time_state_reg = {R"(\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})"};

	void extractRow();

	void nextRow();

	void printDebugInfo() const;
};
