#pragma once
#include <OpenXLSX.hpp>
#include <nlohman-json/json.hpp>
#include <re2/re2.h>
#include <string>

std::string toLowerUTF8Cyrillic(const std::string &str);

std::string getSafeString(uint32_t row, uint32_t col, OpenXLSX::XLWorksheet &wks, bool skip_case = false);

nlohmann::json extractToJsonArray(const std::string &s, const re2::RE2 &reg);
