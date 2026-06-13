#include "ParserObjects.hpp"
#include "Utils.hpp"
#include "XLSheet.hpp"
#include "sw/redis++/redis.h"
#include <OpenXLSX.hpp>
#include <iostream>
#include <nlohman-json/json.hpp>
#include <ostream>
#include <re2/re2.h>
#include <string>
#include <sw/redis++/redis++.h>
#include <utility>
#include <vector>

using namespace std;
using json = nlohmann::json;
using namespace OpenXLSX;

int main() {
	cout << "Начинаем сканировать расписание" << endl;

	// 1. Открываем файл расписания
	XLDocument doc;
	doc.open("./Schedule.xlsx");

	string instituteState = "";

	for (size_t i = 1; i <= doc.workbook().worksheetCount(); ++i) {
		auto workbook = doc.workbook();
		auto wks = doc.workbook().worksheet(i);
		char alphabet[] = {'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
						   'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'};

		if (wks.name().find("майноры") != std::string::npos) {
			continue;
		}

		header checkedHead;

		checkedHead = findHeader(wks);
		if (checkedHead.meta.institute == "") {
			checkedHead.meta.institute = instituteState;
		} else {
			instituteState = checkedHead.meta.institute;
		}

		json root;

		root["Institute"] = checkedHead.meta.institute;
		root["Group"] = checkedHead.meta.groupName;
		root["Course"] = checkedHead.meta.course;
		root["Start-education-date"] = checkedHead.meta.startDate;
		root["End-education-date"] = checkedHead.meta.endDate;
		root["Education-form"] = checkedHead.meta.educationForm;
		// TODO: Сюда потом добавим кафедру, даты из шапки и т.д.
		//  Создаем пустой массив для пар
		root["lessons"] = json::array();

		static const re2::RE2 time_reg(
			R"((\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2}))"); // регулярка для того что бы достать время начала
														 // и концка пары из ячейки времени
		static const re2::RE2 teachers_reg(
			R"((?i)([а-яё]+(?:['\-][а-яё]+)*[\s\xA0]*[а-яё][\s\xA0]*\.(?:[\s\xA0]*[а-яё][\s\xA0]*\.)?))");

		if (checkedHead.readyHeader) {
			scanner wideScan = {
				.groupSchedule = wks, .head = std::move(checkedHead), .currentRow = checkedHead.rowCoordinate};

			string educationalPlaceOddState = ""; // если площадка ни разу не указана ну и черт с ними
			string educationalPlaceEvenState = "";
			// если площадка ни разу не указана ну и черт с ними

			string dayOfWeekState = "";
			// я буду считать что таблица закончилась, если встретил 5 подряд идуших
			// пустых или ошибочных ячеек

			using SR = scanner::scheduleRow;

			for (int endCounter = 0; endCounter < 6; wideScan.nextRow()) {

				wideScan.extractRow();

				if (wideScan.currentStatus == scanner::response::EmptyRow or
					wideScan.currentStatus == scanner::response::ErrorRow) {
					endCounter += 1;
				} else if (wideScan.currentStatus == scanner::response::EducationalPlaces) {
					endCounter = 0;
					educationalPlaceOddState = wideScan.rowObject.storage[SR::Index::educationalPlaceOdd];
					educationalPlaceEvenState = wideScan.rowObject.storage[SR::Index::educationalPlaceEven];
				} else if (wideScan.currentStatus == scanner::response::LessonRow ||
						   wideScan.currentStatus == scanner::response::BlankLessonRow) {
					endCounter = 0;

					string currentDayOfWeek = wideScan.rowObject.storage[SR::Index::dayOfWeek];

					if (currentDayOfWeek != "" &&
						currentDayOfWeek !=
							dayOfWeekState) { // Если значение дня недели отлично от прошлого стейта и
											  // не равно пустой строке будем считать что это новый день недели
						dayOfWeekState = currentDayOfWeek;
					} else if (currentDayOfWeek == "") {
						wideScan.rowObject.storage[SR::Index::dayOfWeek] = dayOfWeekState;
					}

					wideScan.rowObject.storage[SR::Index::educationalPlaceOdd] = educationalPlaceOddState;

					wideScan.rowObject.storage[SR::Index::educationalPlaceEven] = educationalPlaceEvenState;

					if (wideScan.currentStatus == scanner::response::LessonRow) {
						json oddLesson;
						json evenLesson;

						oddLesson["is_even_week"] = false;
						evenLesson["is_even_week"] = true;

						// Делаем короткий псевдоним, чтобы не писать длинные scanner::scheduleRow

						oddLesson[SR::IndexNames[SR::Index::educationalPlaceOdd]] =
							wideScan.rowObject.storage[SR::Index::educationalPlaceOdd];

						evenLesson[SR::IndexNames[SR::Index::educationalPlaceEven]] =
							wideScan.rowObject.storage[SR::Index::educationalPlaceEven];

						bool oddPayLoadFlag = false;
						bool evenPayLoadFlag = false;

						for (int i = 0; i < SR::Index::EndOfCommonCells; i++) {
							string s = wideScan.rowObject.storage[i];
							bool stringIsntEmpty = !s.empty();

							if (i >= SR::Index::oddInfoStart && i <= SR::Index::oddInfoEnd) {
								if (stringIsntEmpty)
									oddPayLoadFlag = true;

								if (SR::IndexNames[i] == "teachers") {
									oddLesson[SR::IndexNames[i]] = extractToJsonArray(s, teachers_reg);
								} else {
									oddLesson[SR::IndexNames[i]] = s;
								}

							} else if (i >= SR::Index::evenInfoStart && i <= SR::Index::evenInfoEnd) {
								if (stringIsntEmpty)
									evenPayLoadFlag = true;

								if (SR::IndexNames[i] == "teachers") {
									evenLesson[SR::IndexNames[i]] = extractToJsonArray(s, teachers_reg);
								} else {
									evenLesson[SR::IndexNames[i]] = s;
								}
							} else {

								// Общие ячейки (время, день недели) пишем в обе недели
								//
								// Отдельный if для поомежутка времени пары
								if (SR::IndexNames[i] ==
									"time_slot") {				 // Заполнеяем не time_slot, а делаем нормальные 2 поля
									string start_time, end_time; // start_time и end_time
									if (re2::RE2::PartialMatch(s, time_reg, &start_time, &end_time)) {
										oddLesson["start_time"] = start_time;
										oddLesson["end_time"] = end_time;
										evenLesson["start_time"] = start_time;
										evenLesson["end_time"] = end_time;
									} else {
										oddLesson["start_time"] = s;
										oddLesson["end_time"] = "";
										evenLesson["start_time"] = s;
										evenLesson["end_time"] = "";
									}
								} else {
									// сюда попадают колонки "номер пары" и "день недели"
									oddLesson[SR::IndexNames[i]] = s;
									evenLesson[SR::IndexNames[i]] = s;
								}
							}
						}

						if (oddPayLoadFlag) {
							root["lessons"].push_back(std::move(oddLesson));
						}

						if (evenPayLoadFlag) {
							root["lessons"].push_back(std::move(evenLesson));
						}
					}
				}
			}
		}

		// === ИНТЕГРАЦИЯ С REDIS ===
		try {
			// Подключаемся к локальному серверу Redis по стандартному порту
			auto redis = sw::redis::Redis("tcp://127.0.0.1:6379");

			// TODO: Сделать 0 отступов для продакшена, пока висит 4 для удобства чтения
			std::string payload = root.dump(4);

			std::vector<std::pair<std::string, std::string>> redis_msg = {{"payload", payload}, {"type", "lessons"}};

			redis.xadd("ready_schedules", "*", redis_msg.begin(), redis_msg.end());

			std::cout << "Успешно отправлено в Redis Streams (Ключ ready_schedules)!" << std::endl;
		} catch (const sw::redis::Error &e) {
			// Ловим сетевые ошибки (например, если сервер Redis упал)
			std::cerr << "Ошибка Redis: " << e.what() << std::endl;
		}
	}

	doc.close();

	cout << "Парсинг расписания завершен!" << endl;

	return 0;
}
