#pragma once
#include <cstdlib>
#include <filesystem>
#include <string>

namespace fs = std::filesystem;

namespace config {

// Безопасная читалка переменных окружения с дефолтным значением
inline std::string get_env(const std::string &key, const std::string &def_val) {
	const char *val = std::getenv(key.c_str());
	return val ? std::string(val) : def_val;
}

inline const std::string REDIS_URL = get_env("REDIS_URL", "tcp://127.0.0.1:6379");
inline const std::string REDIS_DLQ_KEY = "parser:dlq";
inline const std::string REDIS_ERROR_FILES_DLQ = "parser:error_files";
inline const std::string python_worker_stream = "db:parsed_lessons";
inline const std::string stream_name = "parser:ready_schedules";
inline const std::string group_name = "cpp_parsers";
inline const std::string consumer_name = "cpp-worker";

// === ДИРЕКТОРИИ ===
inline const fs::path archive_directory_path = get_env("ARCHIVE_DIR", "app/archive/schedule_lessons");
inline const fs::path dlq_directory_path = get_env("DLQ_DIR", "app/dlq/schedule_lessons");
inline const fs::path shared_ram_dir = get_env("DOWNLOAD_DIR", "/dev/shm");
// UPTIME KUMA
inline const std::string KUMA_URL = get_env("KUMA_URL", "");
} // namespace config
