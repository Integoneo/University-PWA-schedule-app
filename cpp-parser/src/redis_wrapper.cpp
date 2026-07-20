#include <config.hpp>
#include <redis_wrapper.hpp>

// Создаем единственный на всё приложение объект redis.
// Он сам возьмет строку подключения из вашего конфига.
SafeRedis redis(config::REDIS_URL);
