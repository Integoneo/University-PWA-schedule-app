import asyncio
import functools
from time import perf_counter
import aiohttp
from collections import Counter
from shared import config, NewMessage, OldMessageHash, OldMessage, logger
import html


PROXY_URL_TG = f"http://{config.PROXY_LOGIN_TG}:{config.PROXY_PASSWORD_TG}@{config.PROXY_HOST_TG}:{config.PROXY_PORT_TG}"
TG_API_URL = f"https://api.telegram.org/bot{config.TG_BOT_TOKEN}"

last_time_sended = 0.0


async def ping_kuma(session: aiohttp.ClientSession | None) -> None:
    if session is None and config.KUMA_URL:
        conn = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=conn) as session:
            async with session.get(config.KUMA_URL):
                pass
    elif config.KUMA_URL and session:
        try:
            # Просто делаем легкий запрос и даже не читаем ответ
            async with session.get(config.KUMA_URL):
                pass
        except Exception as e:
            logger.error(f"Не удалось пингануть Kuma: {e}")


# --- КАСТОМНЫЕ ИСКЛЮЧЕНИЯ ---


class TgClientError(Exception):
    """400-499 ошибки (кривой JSON, плохой HTML), кроме 429"""

    pass


class TgRateLimit(Exception):
    """429 Too Many Requests"""

    def __init__(self, retry_after: float):
        self.retry_after = retry_after


class TgServerError(Exception):
    """500+ ошибки сервера Телеграм"""

    pass


async def _throttle():
    global last_time_sended
    now = perf_counter()
    if now - last_time_sended < 1.0:
        await asyncio.sleep(1.0 - (now - last_time_sended))
    last_time_sended = perf_counter()


def with_tg_retries(func):
    """
    Асинхронный декоратор для обработки отвалов сети, лимитов ТГ и битых запросов.
    Возвращает -1 в случае фатальной логической ошибки (400+), которую нет смысла ретраить бесконечно.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        attempt = 0
        while True:
            try:
                return await func(*args, **kwargs)

            except TgClientError as e:
                attempt += 1
                logger.error(f"⚠️ Ошибка клиента TG (4xx): {e} | Попытка {attempt}/3")
                if attempt >= 3:
                    return -1  # Провал отправки -> уйдет в DLQ в main.py
                await asyncio.sleep(1)

            except TgRateLimit as e:
                logger.warning(
                    f"⏳ ТГ просит притормозить (429). Ждем {e.retry_after} сек..."
                )
                await asyncio.sleep(e.retry_after)

            except (TgServerError, aiohttp.ClientError, asyncio.TimeoutError) as e:
                # API лежит или нет сети. Скрипт просто зависает и долбится до победного.
                logger.error(
                    f"🔴 Телеграм недоступен (500+ / Сеть): {e}. Ждем 5 сек..."
                )
                await asyncio.sleep(5)

    return wrapper


def build_beautiful_message(message: NewMessage | OldMessage) -> str:
    emojis = {"INFO": "🟢", "WARN": "🟡", "ERROR": "🔴", "CRITICAL": "🚨", "DEAD": "💀"}
    emoji = emojis.get(message.msg_level, "⚪️")

    text = f"{emoji} <b>[{message.msg_level}] | {message.service}</b>\n"

    # Эскейпим основное сообщение на случай, если туда попадет кривой символ
    safe_msg = html.escape(message.msg)
    text += f"<b>Событие:</b> {safe_msg}\n\n"

    message_dict = (
        Counter(message.details) if isinstance(message, NewMessage) else message.sub_msg
    )

    text += "<b>Контекст:</b>\n"
    for detail, count in message_dict.items():
        # Жестко эскейпим детали из хэша
        safe_detail = html.escape(detail)
        text += f"▪️ <b>{count}x</b> | <code>{safe_detail}</code>\n"

    if len(text) > 4000:
        text = text[:4000] + "\n... [СООБЩЕНИЕ ОБРЕЗАНО ИЗ-ЗА ЛИМИТОВ TG]"

    return text


@with_tg_retries
async def send_message(session: aiohttp.ClientSession, message: NewMessage) -> int:
    await ping_kuma(session)
    await _throttle()
    url = f"{TG_API_URL}/sendMessage"
    payload = {
        "chat_id": config.TG_CHAT_ID,
        "text": build_beautiful_message(message),
        "parse_mode": "HTML",
    }

    async with session.post(url, json=payload, proxy=PROXY_URL_TG) as response:
        if response.status == 200:
            data = await response.json()
            return data["result"]["message_id"]

        text = await response.text()

        if response.status == 429:
            data = await response.json()
            retry_after = data.get("parameters", {}).get("retry_after", 5.0)
            raise TgRateLimit(retry_after)
        elif 400 <= response.status < 500:
            raise TgClientError(text)
        else:
            raise TgServerError(text)


@with_tg_retries
async def edit_message(session: aiohttp.ClientSession, message: OldMessageHash) -> int:
    await ping_kuma(session)
    await _throttle()
    url = f"{TG_API_URL}/editMessageText"
    payload = {
        "chat_id": config.TG_CHAT_ID,
        "message_id": message.tg_id_msg,
        "text": build_beautiful_message(message.payload),
        "parse_mode": "HTML",
    }

    async with session.post(url, json=payload, proxy=PROXY_URL_TG) as response:
        if response.status == 200:
            return message.tg_id_msg

        text = await response.text()

        # Фича ТГ: если попытаться обновить текст на точно такой же, он кинет 400
        # Это не ошибка бизнес-логики, просто игнорируем
        if "message is not modified" in text:
            return message.tg_id_msg

        if response.status == 429:
            data = await response.json()
            retry_after = data.get("parameters", {}).get("retry_after", 5.0)
            raise TgRateLimit(retry_after)
        elif 400 <= response.status < 500:
            raise TgClientError(text)
        else:
            raise TgServerError(text)
