#pragma once

#include "sw/redis++/errors.h"
#include "sw/redis++/redis.h"
#include <Utils.hpp>
#include <chrono>
#include <config.hpp>
#include <cstdlib>
#include <spdlog/sinks/stdout_color_sinks.h>
#include <spdlog/spdlog.h>
#include <string>
#include <sw/redis++/redis++.h>
#include <thread>
#include <utility>
#include <vector>

class SafeRedis {
  private:
	sw::redis::Redis _redis;
	bool _is_alive = true;

	void wait_for_redis() {
		_is_alive = false;
		while (!_is_alive) {

			// INFO: UPTIME KUMA PING
			if (!config::KUMA_URL.empty()) {
				// Формируем команду curl в сайлент-режиме (-s)
				// и глушим весь вывод (> /dev/null)
				std::string cmd = "curl -s \"" + config::KUMA_URL + "\" > /dev/null";

				// Запускаем системную команду
				std::system(cmd.c_str());
			}

			try {
				_redis.ping();
				_is_alive = true;
				spdlog::info("Связь с Redis восстановлена!");
			} catch (sw::redis::Error &err) {
				spdlog::error("===== Ошибка Redis ===== \n {}", err.what());
				std::this_thread::sleep_for(std::chrono::milliseconds(100));
			}
		}
	}

	void check_connection() {
		if (!_is_alive) {
			wait_for_redis();
		}
	}

	using Item = std::pair<std::string, std::string>;
	using Msg = std::pair<std::string, std::vector<Item>>;
	using StreamMsgs = std::pair<std::string, std::vector<Msg>>;

  public:
	explicit SafeRedis(const std::string &conn_str) : _redis(conn_str) {}
	bool is_keep_alive() const { return _is_alive; }

	std::string ping() {
		while (true) {
			check_connection();
			try {
				std::string res = _redis.ping();
				_is_alive = true;
				return res;
			} catch (sw::redis::Error &err) {
				_is_alive = false;
			}
		}
	}

	void xgroup_create(const std::string &stream_name, const std::string &group_name, const std::string &id,
					   const bool &mkstream) {
		while (true) {
			check_connection();
			try {
				_redis.xgroup_create(stream_name, group_name, id, mkstream);
				_is_alive = true;
				return; // Успешно создали с нуля, выходим

			} catch (sw::redis::ReplyError &err) {
				std::string err_msg = err.what();

				// ПРОВЕРКА НА BUSYGROUP:
				// Если группа уже существует, Redis вернет что-то вроде: "BUSYGROUP Consumer Group name already exists"
				if (err_msg.find("BUSYGROUP") != std::string::npos) {
					spdlog::info("[XGROUP_CREATE] - Группа '{}' для стрима '{}' уже существует. Пропускаем.",
								 group_name, stream_name);
					_is_alive = true;
					return; // Спокойно выходим из метода, всё отлично!
				}

				// Если это любая ДРУГАЯ ReplyError (не BUSYGROUP) — значит стряслось что-то реально плохое
				spdlog::critical("[XGROUP_CREATE] - Фатальная ошибка при создании группы");
				std::string context = ("[" + id + "] " + stream_name + " | " + group_name + " | ");
				fatal_crash(context, err.what());

			} catch (sw::redis::Error &err) {
				_is_alive = false;
				spdlog::error("[XGROUP_CREATE] - {}", err.what());
				std::this_thread::sleep_for(std::chrono::milliseconds(100));
			}
		}
	}
	std::string xadd(const std::string &key, const std::string &id,
					 std::vector<std::pair<std::string, std::string>> &redis_msg) {
		while (true) {
			check_connection();
			try {
				std::string res = _redis.xadd(key, id, redis_msg.begin(), redis_msg.end());
				_is_alive = true;
				return res;
			} catch (sw::redis::ReplyError &err) {
				spdlog::critical("[XADD] - Фатальная ошибка при создании группы");

				std::string context = ("[" + id + "] " + key + " \nDATA: \n");
				for (std::pair<std::string, std::string> item : redis_msg) {
					context += item.first + ": " + item.second + ",\n";
				}
				fatal_crash(context, err.what());

			} catch (sw::redis::Error &err) {
				_is_alive = false;
				spdlog::error("[XADD] - {}", err.what());
				std::this_thread::sleep_for(std::chrono::milliseconds(100));
			}
		}
	}

	std::string xreadgroup(const std::string &group_name, const std::string &consumer_name,
						   const std::string &stream_name, const std::string &id,
						   const std::chrono::milliseconds timeout, const long long count, nlohmann::json &payload) {
		std::vector<StreamMsgs> reply;

		while (true) {
			check_connection();
			try {
				reply.clear();
				payload.clear(); // Очищаем json перед новым чтением

				_redis.xreadgroup(group_name, consumer_name, stream_name, id, timeout, count,
								  std::back_inserter(reply));
				_is_alive = true;

				// Если Redis вернул пустой массив, reply будет абсолютно пустым.
				if (reply.empty() || reply[0].second.empty()) {
					return ""; // Возвращаем пустой ID, main поймет, что данных нет
				}

				const auto &msg = reply[0].second[0];
				std::string msg_id = msg.first;
				std::string payload_str;

				// Ищем конкретно поле "payload"
				for (const auto &field : msg.second) {
					if (field.first == "payload") {
						payload_str = field.second;
						break;
					}
				}

				// Превращаем строку в JSON объект
				try {
					payload = nlohmann::json::parse(payload_str);
				} catch (const nlohmann::json::parse_error &e) {
					spdlog::error("[XREADGROUP] - Битый JSON в сообщении {}: {}", msg_id, e.what());
					this->xack(stream_name, group_name, msg_id);
					this->xdel(stream_name, msg_id);
					continue;
				}

				// Если дошли сюда и msg_id не пустой — значит сообщение успешно обработано
				return msg_id;

			} catch (sw::redis::ReplyError &err) {
				std::string err_msg = err.what();
				if (err_msg.find("NOGROUP") != std::string::npos) {
					spdlog::warn("[XREADGROUP] - Стрим или группа отсутствуют, выполняю пересоздание...");

					// Пересоздаем группу
					this->xgroup_create(stream_name, group_name, "0", true);
					continue;
				} else {
					spdlog::critical("[XREADGROUP] - Фатальная ошибка при чтении очереди");
					std::string context = ("[" + id + "] stream_name - " + stream_name +
										   " | group_name: " + group_name + " | consumer_name: " + consumer_name);
					fatal_crash(context, err.what());
				}
			} catch (sw::redis::Error &err) {
				_is_alive = false;
				spdlog::error("[XREADGROUP] - {}", err.what());
				std::this_thread::sleep_for(std::chrono::milliseconds(100));
			}
		}
	}
	long long xack(const std::string &stream_name, const std::string &group_name, const std::string &msg_id) {

		while (true) {
			check_connection();
			try {
				long long res = _redis.xack(stream_name, group_name, msg_id);
				_is_alive = true;
				return res;
			} catch (sw::redis::ReplyError &err) {
				spdlog::critical("[XACK] - Фатальная ошибка при подтверждении сообщения");
				std::string context =
					("[" + msg_id + "] stream_name - " + stream_name + " | group_name: " + group_name);
				fatal_crash(context, err.what());

			} catch (sw::redis::Error &err) {
				_is_alive = false;
				spdlog::error("[XACK] - {}", err.what());
				std::this_thread::sleep_for(std::chrono::milliseconds(100));
			}
		}
	}

	long long xdel(const std::string &key, const std::string &msg_id) {
		while (true) {
			check_connection();
			try {
				long long res = _redis.xdel(key, msg_id);
				_is_alive = true;
				return res;
			} catch (sw::redis::ReplyError &err) {
				spdlog::critical("[XDEL] - Фатальная ошибка при удалении сообщения");
				std::string context = ("[" + msg_id + "] " + key);
				fatal_crash(context, err.what());

			} catch (sw::redis::Error &err) {
				_is_alive = false;
				spdlog::error("[XDEL] - {}", err.what());
				std::this_thread::sleep_for(std::chrono::milliseconds(100));
			}
		}
	}

	long long hset(const std::string &key, const std::string &field, const std::string &val) {
		while (true) {
			check_connection();
			try {
				long long res = _redis.hset(key, field, val);
				_is_alive = true;
				return res;
			} catch (sw::redis::ReplyError &err) {
				spdlog::critical("[HSET] - Фатальная ошибка при создании ключа");
				std::string context = ("[" + key + "]\n" + field + ": " + val);
				fatal_crash(context, err.what());

			} catch (sw::redis::Error &err) {
				_is_alive = false;
				spdlog::error("[HSET] - {}", err.what());
				std::this_thread::sleep_for(std::chrono::milliseconds(100));
			}
		}
	}

	long long hdel(const std::string &key, const std::string &field) {
		while (true) {
			check_connection();
			try {
				long long res = _redis.hdel(key, field);
				_is_alive = true;
				return res;
			} catch (sw::redis::ReplyError &err) {
				spdlog::critical("[HDEL] - Фатальная ошибка при удалении ключа");
				std::string context = ("[" + key + "]\n" + field);
				fatal_crash(context, err.what());

			} catch (sw::redis::Error &err) {
				_is_alive = false;
				spdlog::error("[HDEL] - {}", err.what());
				std::this_thread::sleep_for(std::chrono::milliseconds(100));
			}
		}
	}
};

// Объявляем, что глобальный объект под именем `redis` существует.
extern SafeRedis redis;
