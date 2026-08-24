from utils import copy_files_build_msgs, mock_meta_info, push_messages_to_redis
import asyncio


async def main():

    copy_files_build_msgs()

    await push_messages_to_redis()


if __name__ == "__main__":
    asyncio.run(main())
