#pragma once
#include <OpenXLSX.hpp>
#include <nlohman-json/json.hpp>
#include <re2/re2.h>
#include <string>

std::string toLowerUTF8Cyrillic(const std::string &str);

std::string getSafeString(uint32_t row, uint32_t col, OpenXLSX::XLWorksheet &wks, bool skip_case = false);

nlohmann::json extractToJsonArray(const std::string &s, const re2::RE2 &reg);

bool copy_file_to_new_directories(std::filesystem::path source_filepath, std::filesystem::path target_dir,
								  bool is_archive, std::string view_url = "URL_NOT_FOUND");

std::string safe_get_str(const nlohmann::json &j, const std::string &key, const std::string &def);
