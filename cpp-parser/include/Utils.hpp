#pragma once
#include <OpenXLSX.hpp>
#include <nlohman-json/json.hpp>
#include <re2/re2.h>
#include <string>

void init_spdlogger();

std::string toLowerUTF8Cyrillic(const std::string &str);

std::string getSafeString(uint32_t row, uint32_t col, OpenXLSX::XLWorksheet &wks, bool skip_case = false);

nlohmann::json extractToJsonArray(const std::string &s, const re2::RE2 &reg);

bool safe_copy_file(const std::filesystem::path source_filepath, const std::filesystem::path target_dir,
					bool is_archive, const nlohmann::json &python_meta, std::string &view_url);

std::string safe_get_str(const nlohmann::json &j, const std::string &key, const std::string &def);

void send_tg_alert(const std::string &msg_level, const std::string &msg, const std::string &details);

void fatal_crash(const std::string &context, const std::string &error_msg);
