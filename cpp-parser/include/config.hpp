#pragma once
#include <filesystem>
#include <string>

namespace fs = std::filesystem;

namespace config {
inline const std::string REDIS_URL = "tcp://127.0.0.1:6379";
inline const std::string REDIS_DLQ_KEY = "parser:dlq";
inline const std::string REDIS_ERROR_FILES_DLQ = "parser:error_files";
inline const fs::path archive_directory_path = "/home/integoneo/MyProjects/University-schedule-app/archive";
inline const fs::path dlq_directory_path = "/home/integoneo/MyProjects/University-schedule-app/dlq/schedule_lessons";
inline const std::string stream_name = "parser:ready_schedules";
inline const std::string group_name = "cpp_parsers";
inline const std::string consumer_name = "cpp-worker";
} // namespace config
