import asyncio
import storage

from topic import Topic
from pathlib import Path
import json
import os


async def main():
    if os.path.exists("data.db"):
        return

    print("Doing migration")
    await migrate()


async def migrate():
    from storage.sqlite3_session_storage import Sqlite3Datasource, Sqlite3TopicStorage, Sqlite3ProfileStorage
    from user_profile import UserProfile

    datasource = Sqlite3Datasource("data.db")
    storage.datasource = datasource
    topic_storage = Sqlite3TopicStorage()
    topic_service = Topic(topic_storage)

    profile_storage = Sqlite3ProfileStorage()

    from storage import tx

    @tx.transactional(tx_type="write")
    async def do_migration():
        path = Path("sessions")
        for file in path.iterdir():
            if file.is_file() and file.name.endswith(".json"):
                with open(file) as f:
                    topics = json.load(f)
                    await create_topics(topics, int(file.name.replace(".json", "")), topic_service)
            elif file.is_dir() and file.name == "profiles":
                await create_profile(file, UserProfile(profile_storage))

    await do_migration()


async def create_topics(topics, uid, topic_service):
    for item in topics:
        t = storage.types.Topic(
            tid=-1,
            user_id=uid,
            chat_id=item["chat_id"],
            title=item["title"],
            generate_title=item.get("generate_title", False),
            label=item["label"],
        )

        messages = []
        for msg in item.get("context", []):
            messages.append(
                storage.types.Message(
                    role=msg["role"],
                    content=msg["content"],
                    message_id=msg.get("message_id", 0),
                    chat_id=msg.get("chat_id", 0),
                    topic_id=0,
                    ts=msg.get("ts", 0),
                )
            )

        t.messages = messages
        await topic_service.create_topic(t)


async def create_profile(directory, profile_service):
    path = Path(directory)
    for file in path.iterdir():
        if file.is_file() and file.name.endswith(".json"):
            uid = int(file.name.replace(".json", ""))
            profile = json.loads(file.read_text())
            conversation = profile.get("conversation", {})
            current = conversation.get(str(uid), 0)

            await profile_service.create(
                uid=uid,
                model=profile.get("model", ""),
                endpoint=profile.get("endpoint", ""),
                prompt="",
                private=current,
                channel=0,
                groups=0,
            )


if __name__ == '__main__':
    asyncio.run(main())

