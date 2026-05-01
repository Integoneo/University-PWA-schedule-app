#pragma once
#include <OpenXLSX.hpp>
#include <string>

std::string toLowerUTF8Cyrillic(const std::string &str);

std::string getSafeString(uint32_t row, uint32_t col, OpenXLSX::XLWorksheet &wks);
