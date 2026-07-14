#include "ParserObjects.hpp"
#include "Utils.hpp"
#include "XLSheet.hpp"
#include <OpenXLSX.hpp>
#include <atomic>
#include <chrono>
#include <csignal>
#include <nlohman-json/json.hpp>
#include <re2/re2.h>
#include <spdlog/sinks/stdout_color_sinks.h>
#include <spdlog/spdlog.h>
#include <string>
#include <sw/redis++/redis++.h>
#include <thread>
#include <utility>
#include <vector>
using namespace std;
using json = nlohmann::json;
using namespace OpenXLSX;

std::atomic<bool> keep_running(true);

void signal_handler(int signal) {
	if (signal == SIGINT) {
		// Писать тяжелые логи прямо внутри обработчика сигналов небезопасно (вызовет undefined behavior),
		// поэтому мы просто меняем флаг и выходим из него.
		keep_running = false;
	}
}

// Функция парсинга одного файла. Принимает путь, метаданные из Python и ссылку на пулл Redis
void process_excel_file(const string &filepath, const json &python_meta, sw::redis::Redis &redis) {
	XLDocument doc;
	doc.open(filepath);

	string instituteState = "";

	for (size_t i = 1; i <= doc.workbook().worksheetCount(); ++i) {
		auto wks = doc.workbook().worksheet(i);

		string checkNameList = toLowerUTF8Cyrillic(wks.name());

		if (checkNameList.find("майнор") != std::string::npos || checkNameList.find("профмодул") != std::string::npos ||
			checkNameList.find("курс") != std::string::npos) {
			spdlog::warn("Пропускаем лист с минорами,профмодулями и прочий мусор, парсинг этих расписаний под "
						 "вопросом, название листа: '{}'",
						 wks.name());
			continue;
		}

		header checkedHead = findHeader(wks);

		if (!checkedHead.readyHeader) {
			spdlog::warn("Пропуск листа '{}': Нестандартная структура таблицы (шапка не найдена)", wks.name());
			continue; // Сразу прыгаем к следующему листу, не трогаем JSON и Redis!
		}

		if (checkedHead.meta.institute == "") {
			checkedHead.meta.institute = instituteState;
		} else {
			instituteState = checkedHead.meta.institute;
		}

		auto safe_get_str = [](const json &j, const std::string &key, const std::string &def) -> std::string {
			if (j.contains(key) && j[key].is_string()) {
				return j[key].get<std::string>();
			}
			return def;
		};

		json root;

		string parsedGroupName = checkedHead.meta.groupName;
		// INFO: Лежит тут на всякий случай, я считаю нужным для названий пока использовать названия листов
		// пускай лежит ту на всякий пожарный случай

		// === ГИБРИДНЫЙ ИСТОЧНИК ИСТИНЫ ===
		// Институты и Форму берем из Python (если их нет в Python - фоллбэк на C++)
		root["institute"] = safe_get_str(python_meta, "institute", checkedHead.meta.institute);
		root["education-form"] = safe_get_str(python_meta, "study_form", checkedHead.meta.educationForm);

		root["course"] = checkedHead.meta.course;
		root["group"] = wks.name();
		root["start-education-date"] = checkedHead.meta.startDate;
		root["end-education-date"] = checkedHead.meta.endDate;

		root["view_url"] = safe_get_str(python_meta, "view_url", "");
		root["logo_url"] = safe_get_str(python_meta, "logo_url", "");
		root["lessons"] = json::array();

		spdlog::info("Обработка расписания: Институт '{}' | Курс '{}' | Группа '{}'",
					 safe_get_str(root, "institute", "Неизвестно"), safe_get_str(root, "course", "Неизвестно"),
					 safe_get_str(root, "group", "Неизвестно"));

		static const re2::RE2 time_reg(R"((\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2}))");
		static const re2::RE2 teachers_reg(
			R"((?i)([а-яё]+(?:['\-][а-яё]+)*[\s\xA0]*[а-яё][\s\xA0]*\.(?:[\s\xA0]*[а-яё][\s\xA0]*\.)?))");

		if (checkedHead.readyHeader) {
			scanner wideScan = {
				.groupSchedule = wks, .head = std::move(checkedHead), .currentRow = checkedHead.rowCoordinate};

			string educationalPlaceOddState = "";
			string educationalPlaceEvenState = "";
			string dayOfWeekState = "";

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

					if (currentDayOfWeek != "" && currentDayOfWeek != dayOfWeekState) {
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
								if (SR::IndexNames[i] == "time_slot") {
									string start_time, end_time;
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
									oddLesson[SR::IndexNames[i]] = s;
									evenLesson[SR::IndexNames[i]] = s;
								}
							}
						}

						if (oddPayLoadFlag)
							root["lessons"].push_back(std::move(oddLesson));
						if (evenPayLoadFlag)
							root["lessons"].push_back(std::move(evenLesson));
					}
				}
			}
		}

		// === ИНТЕГРАЦИЯ С REDIS (ОТПРАВЛЯЕМ ГОТОВОЕ РАСПИСАНИЕ) ===
		// Используем очередь "db:parsed_lessons" для готовых данных
		string payload = root.dump(4); // TODO: Убрать 4 для продакшена
		vector<pair<string, string>> redis_msg = {{"payload", payload}, {"type", "lessons"}};
		redis.xadd("db:parsed_lessons", "*", redis_msg.begin(), redis_msg.end());

		spdlog::info("Лист '{}' успешно отправлен. Институт: '{}', Курс: '{}', Группа: '{}'", wks.name(),
					 root["institute"].get<std::string>(), root["course"].get<std::string>(),
					 root["group"].get<std::string>());
	}

	doc.close();
}

int main() {
	// 1. Инициализация spdlog
	auto logger = spdlog::stdout_color_mt("console");
	spdlog::set_default_logger(logger);
	spdlog::set_pattern("%Y-%m-%d %H:%M:%S.%e [%^%l%$] %v");

	spdlog::info("Запуск C++ Парсера (Worker)...");

	std::signal(SIGINT, signal_handler);

	// 2. Инициализация Redis (Одно соединение на весь скрипт!)
	auto redis = sw::redis::Redis("tcp://127.0.0.1:6379");
	string stream_name = "parser:ready_schedules"; // Куда пишет Python
	string group_name = "cpp_parsers";
	string consumer_name = "cpp-worker";

	try {
		redis.xgroup_create(stream_name, group_name, "0", true);
	} catch (const sw::redis::ReplyError &e) {
		// Игнорируем BUSYGROUP
	}

	// --- ПЕРЕД ЦИКЛОМ ЗАДАЕМ ТИПЫ ДАННЫХ ---
	using Item = std::pair<std::string, std::string>;
	using Msg = std::pair<std::string, std::vector<Item>>;
	using StreamMsgs = std::pair<std::string, std::vector<Msg>>;

	spdlog::info("Ожидание файлов в очереди {}...", stream_name);

	// --- САМ ЦИКЛ ---
	while (keep_running) {
		try {
			// Создаем пустой вектор для ответов
			std::vector<StreamMsgs> reply;

			// Передаем параметры напрямую: timeout (2000ms) и count (1)
			redis.xreadgroup(group_name, consumer_name, stream_name, ">",
							 std::chrono::milliseconds(2000), // BLOCK
							 1,								  // COUNT
							 std::back_inserter(reply));	  // Куда складывать

			if (reply.empty()) {
				// Если за 2 секунды никто ничего не прислал - спим и пробуем снова
				std::this_thread::sleep_for(std::chrono::milliseconds(500));
				continue;
			}

			// ... дальше пошел твой старый цикл for (const auto& stream_data : reply) ...

			for (const auto &stream_data : reply) {
				for (const auto &msg : stream_data.second) {
					string msg_id = msg.first;
					string payload_str;

					for (const auto &field : msg.second) {
						if (field.first == "payload")
							payload_str = field.second;
					}

					if (!payload_str.empty()) {
						// Разбираем JSON от Питона
						auto payload = json::parse(payload_str);
						string filepath = payload["filepath"];

						// ИСПРАВЛЕННАЯ СТРОКА: просто забираем вложенный JSON-объект
						auto meta_info = payload["meta_info"];

						spdlog::info("Взят в работу файл: {}", filepath);

						// Запускаем парсинг
						process_excel_file(filepath, meta_info, redis);

						spdlog::info("Файл успешно обработан: {}", filepath);
					}

					// Подтверждаем выполнение задачи Питону
					redis.xack(stream_name, group_name, msg_id);
					// redis.xdel(stream_name, msg_id);  - Закомментируем для тестов
				}
			}
		} catch (const std::exception &e) {
			spdlog::error("Критическая ошибка (Краш при парсинге): {}", e.what());
			// TODO: Можно здесь добавить удаление битого файла с диска
			std::this_thread::sleep_for(std::chrono::seconds(3));
		}
	}

	spdlog::warn("Получен сигнал прерывания (Ctrl+C)!");
	spdlog::info("Завершение работы, Пока!");

	return 0;
}
