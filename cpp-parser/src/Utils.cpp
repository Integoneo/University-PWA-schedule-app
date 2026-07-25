#include "Utils.hpp"
#include "config.hpp"
#include <OpenXLSX.hpp>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <exception>
#include <filesystem>
#include <iomanip>
#include <nlohman-json/json.hpp>
#include <re2/re2.h>
#include <redis_wrapper.hpp>
#include <spdlog/sinks/dup_filter_sink.h>
#include <spdlog/sinks/stdout_color_sinks.h>
#include <spdlog/spdlog.h>
#include <sstream>
#include <string>
#include <system_error>
namespace fs = std::filesystem;

using json = nlohmann::json;
void init_spdlogger() {
	auto color_sink = std::make_shared<spdlog::sinks::stderr_color_sink_mt>();
	auto dup_filter = std::make_shared<spdlog::sinks::dup_filter_sink_mt>(std::chrono::hours(12));
	dup_filter->add_sink(color_sink);
	auto logger = std::make_shared<spdlog::logger>("console", dup_filter);

	spdlog::register_logger(logger);
	spdlog::set_default_logger(logger);
	spdlog::set_pattern("%Y-%m-%d %H:%M:%S.%e [%^%l%$] %v");
}

std::string toLowerUTF8Cyrillic(const std::string &str) {
	std::string result;
	result.reserve(str.size()); // Выделяем память заранее для скорости

	for (size_t i = 0; i < str.length(); ++i) {
		unsigned char c = str[i];

		// 1. Обычная латиница (A-Z)
		if (c >= 'A' && c <= 'Z') {
			result += c + 32;
		}
		// 2. Проверяем двухбайтовые символы UTF-8
		else if (i + 1 < str.length()) {
			unsigned char c2 = str[i + 1];

			// Проверяем диапазон А-Я (первый байт всегда D0)
			if (c == 0xD0 && c2 >= 0x90 && c2 <= 0xAF) {
				if (c2 <= 0x9F) {
					// Буквы от А до П (меняем второй байт)
					result += 0xD0;
					result += c2 + 0x20;
				} else {
					// Буквы от Р до Я (меняется и первый, и второй байт)
					result += 0xD1;
					result += c2 - 0x20;
				}
				i++; // Пропускаем второй байт, так как мы его уже обработали
			}
			// Отдельно обрабатываем букву Ё
			else if (c == 0xD0 && c2 == 0x81) {
				result += 0xD1;
				result += 0x91; // ё
				i++;
			}
			// Если это не заглавная кириллица — просто копируем как есть
			else {
				result += c;
			}
		}
		// 3. Остальные символы (цифры, знаки, пробелы)
		else {
			result += c;
		}
	}
	// cout << result << endl;
	return result;
}

/**
 * Безопасно извлекает текст из ячейки, очищает его от пробелов и приводит к
 * нижнему регистру (с поддержкой кириллицы).
 */
std::string getSafeString(uint32_t row, uint32_t col, OpenXLSX::XLWorksheet &wks, bool skip_case) {
	try {
		//  Защита от пустых ячеек
		auto cell = wks.cell(row, col);
		auto type = cell.value().type();

		if (type == OpenXLSX::XLValueType::Empty) {
			return "";
		}

		//  Безопасное извлечение с учетом типа данных Excel
		std::string raw = "";

		switch (type) {
		case OpenXLSX::XLValueType::String:
			raw = cell.value().get<std::string>();
			break;
		case OpenXLSX::XLValueType::Integer:
			raw = std::to_string(cell.value().get<int64_t>());
			break;
		case OpenXLSX::XLValueType::Float: {
			double val = cell.value().get<double>();
			// Excel часто хранит целые числа как 1.0. Убираем лишние нули:
			if (val == std::floor(val)) {
				raw = std::to_string(static_cast<long long>(val));
			} else {
				raw = std::to_string(val);
			}
			break;
		}
		case OpenXLSX::XLValueType::Boolean:
			raw = cell.value().get<bool>() ? "1" : "0";
			break;
		default:
			return ""; // Если попался какой-то странный формат (ошибка и т.д.)
		}

		// 3. Обрезка мусора (Trim)
		const std::string whitespace = " \t\n\r\f\v";
		size_t first = raw.find_first_not_of(whitespace);

		if (std::string::npos == first) {
			return ""; // Если в ячейке были только пробелы
		}

		size_t last = raw.find_last_not_of(whitespace);
		std::string trimmed = raw.substr(first, (last - first + 1));

		// 4. самописный нижний регистр для кириллицы -- используется только для поиска колонок и метаданных
		// данные из самой таблицы извлекаются в таком регистре - как есть
		if (skip_case) {
			return trimmed;
		}

		return toLowerUTF8Cyrillic(trimmed);

	} catch (std::exception &e) {
		spdlog::error("Произошла ошибка при форматировании строки в функции getSafeString, \n Детали \n {}", e.what());
		return "";
	}
}

nlohmann::json extractToJsonArray(const std::string &str, const re2::RE2 &reg) {
	// Инициализируем пустой JSON-массив
	nlohmann::json result = nlohmann::json::array();

	re2::StringPiece input(str);
	std::string match;

	// Ищем все вхождения, пока они не закончатся в строке
	while (re2::RE2::FindAndConsume(&input, reg, &match)) {
		result.push_back(match);
	}

	return result;
}

// мне нужна функция которая будет записывать файлы и для архива и для dlq
//  Давай деконструируем требования к работе этой функции, у нас всего 2 случая и общие требования
//  ===== ОБЩИЕ ТРЕБОВАНИЯ ======
//  Сначала функция создает папку для записи гарантируя что она:
//   - Создаст папку только если ее еще нет
//   - Не перезапишет папку если она уже существует
//   - гарантирует обработку ошибок с файловой системой
//   - если возникнут ошибки с файловой системой, то вернет false
//   - Для копирования должен использоваться только алгоритм
//     гарантирующий атомарную перезапись файла:
//        1. Скопировать исходный файл в папку назначения с
//           называнием temp_filename(skip_existing)
//        2. Сделать fs::rename: temp_filename -> filename,
//           тем самым гарантируя атомарность
//   - При любых проблемах с диском должен писать в свою очередь
//     filesystem_problem
//   * при возврате false этой функцией в main цикле нужна логика
//     обработки этой ошибки, поскольку нельзя пушить этот файл в
//     DLQ, DLQ яно требует наличия файла по заданному filepath
//  1 ====== ЗАПИСЬ В АРХИВ =====
//  Нужно создать директорию archive, создать там папку с датой и не перезаписать уже существующую директорию
//  Так же нельзя перезаписать файл в архиве если он меньше чем уже существующий файл - это защита от перезаписи
//  архивных файлов если они пришли из DLQ
//
//  2 ====== ЗАПИСЬ ФАЙЛА В АВТОМАТИЗИРОВАННЫЙ DLQ ==========
//  - Атомарная перезапись через fs::rename

// Не буду ловить ошибки работы с файловой системой через перегрузки
// оберну все в один try и буду отправлять в redis hash при проблемами с файловой системой

bool safe_copy_file(const fs::path source_filepath, const fs::path target_dir, bool is_archive, const json &python_meta,
					std::string &view_url) {
	try {
		// 1. Ручная генерация исключения, если исходного файла нет
		if (!fs::exists(source_filepath)) {
			throw fs::filesystem_error("Исходный файл не найден", source_filepath,
									   std::make_error_code(std::errc::no_such_file_or_directory));
		}

		fs::path final_dir = target_dir;
		fs::path original_filename = source_filepath.filename();

		// Cобираем имя temp файла (например: temp_schedule.xlsx)
		fs::path temp_filename = "temp_" + original_filename.string();
		fs::path final_filepath;

		// 2. Модификация пути для архива и проверка размера
		if (is_archive) {
			// === НАДЕЖНЫЙ C-STYLE ПОДХОД ===
			auto now = std::chrono::system_clock::now();
			auto in_time_t = std::chrono::system_clock::to_time_t(now);

			std::stringstream ss;
			ss << std::put_time(std::localtime(&in_time_t), "%d.%m.%Y");
			final_dir /= ss.str();
			// ==========================================

			final_filepath = final_dir / original_filename;

			// Защита от перезаписи: если новый файл меньше старого - пропускаем
			if (fs::exists(final_filepath)) {
				if (fs::file_size(source_filepath) < fs::file_size(final_filepath)) {
					return true;
				}
			}
		} else {
			final_filepath = final_dir / original_filename;
		}

		fs::path temp_filepath = final_dir / temp_filename;

		// 3. Создаем директории. Выбросит ошибку при отсутствии прав
		fs::create_directories(final_dir);

		// 4. Копируем во временный файл с ГАРАНТИРОВАННОЙ перезаписью старых огрызков
		fs::copy_file(source_filepath, temp_filepath, fs::copy_options::overwrite_existing);

		// 5. Атомарное переименование
		fs::rename(temp_filepath, final_filepath);

	} catch (const fs::filesystem_error &err) {
		// Ловим конкретно ошибки диска

		spdlog::critical("Ошибка файловой системы: {} | Проблемный путь: {}", err.what(), err.path1().string());
		spdlog::critical("Ссылка для быстрого просмотра: {}", view_url);

		redis.hset(config::REDIS_ERROR_FILES_DLQ, source_filepath.string(), python_meta.dump());
		return false;

	} catch (const std::exception &err) {
		// Fallback для любых других ошибок
		spdlog::critical("Неожиданная ошибка при записи файла: {}", err.what());
		redis.hset(config::REDIS_ERROR_FILES_DLQ, source_filepath.string(), view_url);
		return false;
	}

	return true;
}
std::string safe_get_str(const json &j, const std::string &key, const std::string &def) {
	if (j.contains(key) && j[key].is_string()) {
		return j[key].get<std::string>();
	}
	return def;
}

void send_tg_alert(const std::string &msg_level, const std::string &msg, const std::string &details) {
	std::vector<std::pair<std::string, std::string>> redis_msg = {
		{"service", "cpp_parser"}, {"msg_level", msg_level}, {"msg", msg}, {"details", details}};

	redis.xadd("notifier:queue", "*", redis_msg);
}
void fatal_crash(const std::string &context, const std::string &error_msg) {

	spdlog::critical("ФАТАЛЬНАЯ ОШИБКА! Контекст {} \n Ошибка {}", context, error_msg);

	std::exit(EXIT_FAILURE);
}
