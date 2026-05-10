#include "Utils.hpp"
#include <OpenXLSX.hpp>
#include <nlohman-json/json.hpp>
#include <re2/re2.h>
#include <string>

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

	} catch (...) {
		// Ловим любые исключения библиотеки OpenXLSX
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
