#include "ParserObjects.hpp"
#include "Utils.hpp"
#include "XLDocument.hpp"
#include "XLSheet.hpp"
#include <chrono>
#include <config.hpp>
#include <cstdlib>
#include <exception>
#include <filesystem>
#include <nlohman-json/json.hpp>
#include <re2/re2.h>
#include <redis_wrapper.hpp>
#include <spdlog/sinks/dup_filter_sink.h>
#include <spdlog/sinks/stdout_color_sinks.h>
#include <spdlog/spdlog.h>
#include <string>
#include <sw/redis++/redis++.h>
#include <thread>
#include <type_traits>
#include <unistd.h>
#include <vector>
using namespace std;
using json = nlohmann::json;
using namespace OpenXLSX;
namespace fs = std::filesystem;

// Функция парсинга одного файла. Принимает путь, метаданные из Python
void process_excel_file(const string &filepath, json &payload, const string msg_id) {

	json &python_meta = payload["meta_info"];
	vector<string> successful_lists;
	// Буду сюда названия листов которые имели логические ошибки в своей структуре и отправлять эти листы в
	// DLQ
	bool file_has_trash_lists = false;
	// Если мусорных листов не было, удаляем файл без зазрения совести

	string href = safe_get_str(python_meta, "view_url", "URL_NOT_FOUND");

	bool file_is_fine = safe_copy_file(filepath, config::archive_directory_path, true, python_meta, href);

	// ЕСЛИ ОШИБКА ФАЙЛОВОЙ СИСТЕМЫ ПРИ АРХИВАЦИИ
	if (!file_is_fine) {
		send_tg_alert("CRITICAL", "Ошибка файловой системы", "Ошибка при копировании файла в архив");

		spdlog::error("Не удалось скопировать файл в архив: {}", filepath);
		redis.xdel(config::stream_name, msg_id); // Удаляем из очереди (1-й и единственный раз)

		// Удаляем мусор из /dev/shm
		std::error_code remove_ec;
		fs::remove(filepath, remove_ec);

		// ПРЕРЫВАЕМ ФУНКЦИЮ! Дальше код парсинга не пойдет.
		return;
	}
	XLDocument doc;
	doc.open(filepath);

	string filename = fs::path(filepath).filename();

	// Коробка для сообщения в DLQ
	vector<string> dlq_msg;

	doc.setProperty(OpenXLSX::XLProperty::LastModifiedBy, "C++");
	doc.save();

	string instituteState = "";

	for (size_t i = 1; i <= doc.workbook().worksheetCount(); ++i) {
		auto wks = doc.workbook().worksheet(i);

		bool list_has_human_errors = false;

		string checkNameList = toLowerUTF8Cyrillic(wks.name());

		if (checkNameList.find("майнор") != std::string::npos || checkNameList.find("профмодул") != std::string::npos ||
			checkNameList.find("курс") != std::string::npos) {
			spdlog::warn("Пропускаем лист с минорами,профмодулями и прочий мусор, парсинг этих расписаний под "
						 "вопросом, название листа: '{}'",
						 wks.name());
			successful_lists.emplace_back(wks.name()); // Будем эти мусорные листы пока что просто скипать

			send_tg_alert("INFO", "Успешный парсинг группы", "Мусорный лист миноров - Пропускаю");
			continue;
		}

		header checkedHead = findHeader(wks);

		if (!checkedHead.readyHeader) {
			spdlog::warn("Пропуск листа '{}': Нестандартная структура таблицы (шапка не найдена)", wks.name());

			file_has_trash_lists = true;
			dlq_msg.emplace_back(std::to_string(dlq_msg.size()) +
								 ". Нестандартная структура таблицы (шапка не найдена)");
			send_tg_alert("WARN", "Группа отправлена в DLQ", "Нестандартная структура таблицы (шапка не найдена)");
			continue; // Сразу прыгаем к следующему листу, не
					  // трогаем JSON и Redis!
		}

		if (checkedHead.meta.institute == "") {
			checkedHead.meta.institute = instituteState;
		} else {
			instituteState = checkedHead.meta.institute;
		}

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

		if (checkedHead.meta.startDate == "" || checkedHead.meta.endDate == "") {
			list_has_human_errors = true;
			file_has_trash_lists = true;
			spdlog::warn("Не найдена дата начала или конца семестра");
			send_tg_alert("WARN", "Группа отправлена в DLQ", "Не найдена дата начала или конца семестра");
			checkedHead.readyHeader = false;
			// Меняю состояние шапки что бы не парсить дальше этот лист
			dlq_msg.emplace_back(std::to_string(dlq_msg.size()) + "Не найдена дата начала или конца семестра");
			continue;
		}

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

						if (oddLesson[SR::IndexNames[SR::Index::educationalPlaceOdd]] == "" &&
							evenLesson[SR::IndexNames[SR::Index::educationalPlaceEven]] == "") {
							list_has_human_errors = true;
							file_has_trash_lists = true;
							spdlog::warn("У пары не найдена учебная площадка - логическая ошибка");
							dlq_msg.emplace_back(std::to_string(dlq_msg.size()) +
												 ". У пары не найдена учебная площадка - логическая ошибка");
							// Очищаем уже собранные пары, этот лист мы в БД не пустим!

							send_tg_alert("WARN", "Группа отправлена в DLQ",
										  "У пары не найдена учебная площадка - логическая ошибка");
							root["lessons"].clear();
							break;
						}

						bool odd_has_discipline = false;
						bool odd_has_other_text = false;

						bool even_has_discipline = false;
						bool even_has_other_text = false;

						for (int i = 0; i < SR::Index::EndOfCommonCells; i++) {
							string s = wideScan.rowObject.storage[i];
							bool stringIsntEmpty = !s.empty();

							if (i >= SR::Index::oddInfoStart && i <= SR::Index::oddInfoEnd) {
								if (stringIsntEmpty) {
									if (i == SR::Index::lessonOdd) {
										odd_has_discipline = true;
									} else {
										odd_has_other_text = true;
									}
								}

								if (SR::IndexNames[i] == "teachers") {
									oddLesson[SR::IndexNames[i]] = extractToJsonArray(s, teachers_reg);
								} else {
									oddLesson[SR::IndexNames[i]] = s;
								}

							} else if (i >= SR::Index::evenInfoStart && i <= SR::Index::evenInfoEnd) {
								if (stringIsntEmpty) {
									if (i == SR::Index::lessonEven) {
										even_has_discipline = true;
									} else {
										even_has_other_text = true;
									}
								}

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

						// === ПРОВЕРКА НА ШИЗУ ДЕКАНАТА (АНОМАЛИЮ) ===
						if ((odd_has_other_text && !odd_has_discipline) ||
							(even_has_other_text && !even_has_discipline)) {

							list_has_human_errors = true;

							file_has_trash_lists = true;
							spdlog::warn("АНОМАЛИЯ: Группа {}. Висящая ячейка без названия пары! Отправляем в DLQ.",
										 wks.name());
							dlq_msg.emplace_back(std::to_string(dlq_msg.size()) + ". Группа " + wks.name() +
												 " Висящая ячейка без названия пары!");

							send_tg_alert("WARN", "Группа отправлена в DLQ",
										  "Найдена висящая ячейка без названия пары");

							// Очищаем уже собранные пары, этот лист мы в БД не пустим!
							root["lessons"].clear();

							// Выходим из цикла сканирования строк (нет смысла парсить битый лист дальше)
							break;
						}

						if (odd_has_discipline)
							root["lessons"].push_back(std::move(oddLesson));
						if (even_has_discipline)
							root["lessons"].push_back(std::move(evenLesson));
					}
				}
			}
		}

		if (list_has_human_errors) {

			spdlog::warn("Лист '{}' Имеет логические ошибки. Институт: '{}', Курс: '{}', Группа: '{}'", wks.name(),
						 root["institute"].get<std::string>(), root["course"].get<std::string>(),
						 root["group"].get<std::string>());

		} else {

			successful_lists.emplace_back(wks.name());

			string payload = root.dump(4);
			vector<pair<string, string>> redis_msg = {{"payload", payload}, {"type", "lessons"}};

			redis.xadd(config::python_worker_stream, "*", redis_msg);

			send_tg_alert("INFO", "Успешный парсинг группы", "Группа отправлена на обработку");
			spdlog::info("Лист '{}' успешно отправлен. Институт: '{}', Курс: '{}', Группа: '{}'", wks.name(),
						 root["institute"].get<std::string>(), root["course"].get<std::string>(),
						 root["group"].get<std::string>());
		}
	}

	if (file_has_trash_lists) {
		// Сначала удаляем успешно прошедшие листы
		for (const auto &s_name : successful_lists) {
			try {
				doc.workbook().deleteSheet(s_name);
			} catch (std::exception &e) {
				spdlog::warn("Ошибка удаления листа");

				send_tg_alert("ERROR", "Ошибка удаления листа", static_cast<std::string>(e.what()));
			} // Безопасное игнорирование ошибок OpenXLSX
		}

		// 1. Сохраняем файл прямо там, где он открыт (в /dev/shm)
		doc.save();
		// 2. Закрываем документ ДО манипуляций с файлами
		doc.close();

		file_is_fine = safe_copy_file(filepath, config::dlq_directory_path, false, python_meta, href);

		if (!file_is_fine) {
			spdlog::error("Не удалось скопировать файл в DLQ: {}", filepath);
			redis.xdel(config::stream_name, msg_id);
			send_tg_alert("CRITICAL", "Ошибка файловой системы", "Ошибка при копировании файла в DLQ");
			// Удаляем мусор из /dev/shm
			std::error_code remove_ec;
			fs::remove(filepath, remove_ec);

			// ПРЕРЫВАЕМ ФУНКЦИЮ! Дальше код парсинга не пойдет.
			return;
		}
		payload["msg"] = dlq_msg;

		// Хэш который читает питоновский микроскрипт
		redis.hset(config::REDIS_DLQ_KEY, filename, payload.dump());

		spdlog::warn("DLQ файл обновлен и записан в HASH {}: {}", config::REDIS_DLQ_KEY, filename);
	} else {
		// Если ошибок нет, просто закрываем
		doc.close();

		// АВТО-ОЧИСТКА DLQ! Если файл пришел из ретрая и вылечился на 100%
		fs::path filename = fs::path(filepath).filename();
		fs::path dlq_path = config::dlq_directory_path / filename;
		std::error_code check_ec;

		if (fs::exists(dlq_path, check_ec)) {
			// Удаляем файл с диска
			fs::remove(dlq_path, check_ec);
			// Удаляем запись из хэша Redis
			redis.hdel(config::REDIS_DLQ_KEY, filename.string());
			spdlog::info("Файл {} полностью ВЫЛЕЧЕН! Удален из карантина и Redis.", filename.string());
		}
	}

	// В самом конце удаляем временный файл из /dev/shm
	std::error_code remove_ec;
	fs::remove(filepath, remove_ec);
	if (remove_ec) {
		spdlog::error("Не удалось удалить временный файл {}: {}", filepath, remove_ec.message());

		send_tg_alert("CRITICAL", "Ошибка файловой системы", "Ошибка при удалении файла");
	}
}

int main() {
	// 1. Инициализация spdlog
	init_spdlogger();

	spdlog::info("Запуск C++ Парсера (Worker)...");

	// 2. Инициализация Redis

	redis.ping();
	redis.xgroup_create(config::stream_name, config::group_name, "0", true);

	spdlog::info("Ожидание файлов в очереди {}...", config::stream_name);

	while (true) {

		// INFO: UPTIME KUMA PING

		if (!config::KUMA_URL.empty()) {
			// Формируем команду curl в сайлент-режиме (-s)
			// и глушим весь вывод (> /dev/null)
			std::string cmd = "curl -s \"" + config::KUMA_URL + "\" > /dev/null";

			// Запускаем системную команду
			std::system(cmd.c_str());
		}

		json payload;
		std::string msg_id = "";

		// 1. ИЩЕМ ЗАВИСШИЕ ЗАДАЧИ ("0")
		msg_id = redis.xreadgroup(config::group_name, config::consumer_name, config::stream_name, "0",
								  std::chrono::milliseconds(0), 1, payload);

		if (msg_id.empty()) {
			// Если зависших нет, ждем новые (">")
			msg_id = redis.xreadgroup(config::group_name, config::consumer_name, config::stream_name, ">",
									  std::chrono::milliseconds(2000), 1, payload);
		} else {
			spdlog::info("Выполняю незавершенную задачу...");
		}

		if (msg_id.empty()) {
			spdlog::info("Нахожусь в ожидании эксель файлов");
			std::this_thread::sleep_for(std::chrono::milliseconds(500));
			continue;
		}

		// --- ОБРАБОТКА ---
		string filepath = payload["filepath"];
		auto meta_info = payload["meta_info"];
		std::string filename = fs::path(filepath).filename();
		auto view_url = safe_get_str(meta_info, "view_url", "URL_NOT_FOUND");

		spdlog::info("Взят в работу файл: {}", filepath);

		try {
			// Пытаемся спарсить
			process_excel_file(filepath, payload, msg_id);

			// Если функция process_excel_file отработала и НЕ ВЫБРОСИЛА исключений:
			spdlog::info("Цикл работы с файлом завершен: {}", filepath);
			redis.xack(config::stream_name, config::group_name, msg_id);
			redis.xdel(config::stream_name, msg_id); // Удаляем успешно обработанное сообщение

		} catch (std::exception &e) {
			// ФАТАЛЬНЫЙ КРАШ (на уровне самого парсера/библиотеки)
			spdlog::error("Фатальная ошибка (Exception) при парсинге файла {}: {}", filepath, e.what());

			bool file_is_fine = safe_copy_file(filepath, config::dlq_directory_path, false, payload, view_url);

			send_tg_alert("CRITICAL", "Ошибка при парсинге", static_cast<std::string>(e.what()));
			if (!file_is_fine) {
				// Если даже в DLQ не смогли скопировать (проблемы с диском)
				redis.xdel(config::stream_name, msg_id);
			} else {
				payload["msg"] = e.what();

				// Пишем в Hash
				redis.hset(config::REDIS_DLQ_KEY, filename, payload.dump());
				spdlog::warn("Крашнутый файл отправлен в DLQ: {}", filename);

				// Обязательно удаляем мусор из /dev/shm
				std::error_code ec;
				fs::remove(filepath, ec);

				// Удаляем из исходной очереди, так как задача теперь живет в DLQ
				redis.xdel(config::stream_name, msg_id);
			}
		}
	}

	return 0;
}
