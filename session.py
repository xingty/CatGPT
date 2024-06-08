from telebot.types import Message

from pathlib import Path

import json
import uuid


class Session:
    def __init__(self):
        self.context = {}
        self._init_context()

    def _init_context(self):
        self.session_path = Path(__file__).parent.joinpath("sessions")
        if not self.session_path.exists():
            self.session_path.mkdir(parents=True, exist_ok=True)

        for item in self.session_path.iterdir():
            if not item.is_file():
                continue

            segments = item.name.split('.')
            if len(segments) != 2:
                print('ignore ' + item.name)
                continue

            uid = segments[0]
            file_extension = segments[1]

            if file_extension == 'json':
                messages = json.loads(item.read_text())
                messages.reverse()
                self.context[uid] = messages

    def append_message(self, user_msg: Message, replies: list):
        uid = str(user_msg.from_user.id)
        if uid not in self.context:
            self.context[uid] = []

        conversation = self.context.get(uid)
        messages = [
            {
                "role": 'user',
                "text": user_msg.text,
                "message_id": user_msg.message_id,
                "chat_id": user_msg.chat.id,
                "ts": user_msg.date,
            }
        ]

        messages += replies

        messages = conversation.context + messages
        self.append_to_disk(uid, messages)

    def get_conversations(self, uid: str):
        file = self.session_path.joinpath(uid + '.json')
        convo_list = []
        if file.exists():
            convo_list = json.loads(file.read_text())

        return file, convo_list

    def append_to_disk(self, uid, conversations):
        file, convo_list = self.get_conversations(uid)
        convo_list += conversations

        file.write_text(json.dumps(convo_list, ensure_ascii=False))

    def list_conversation(self, uid: str, chat_id: int):
        convo_list = self.context.get(uid, [])
        return [item for item in convo_list if item.get('chat_id') == chat_id]

    def get_convo(self, uid: str, convo_id: str):
        if not convo_id:
            return None

        for convo in self.context.get(uid, []):
            if convo.get('id') == convo_id:
                return convo

        return None

    def save_convo(self, uid: str, convo: dict):
        file, convo_list = self.get_conversations(uid)
        for index, item in enumerate(convo_list):
            if item.get('id') == convo.get('id'):
                convo_list[index] = convo
                break

        self.context[uid] = convo_list

        file.write_text(json.dumps(convo_list, ensure_ascii=False))

    def delete_convo(self, uid: str, convo_id: str):
        convo_list = self.context[uid]
        for index, item in enumerate(convo_list):
            if item.get('id') == convo_id:
                del convo_list[index]
                break

        if len(convo_list) == 0:
            label = str(uuid.uuid4())
            convo_list.append(
                {
                    "id": label.replace("-", "")[:10],
                    "label": label,
                    "title": "Convo 1",
                    "generate_title": True,
                    "context": [],
                }
            )

        self.context[uid] = convo_list
        self.sync_convo(uid)

    def create_convo(self, uid: str, chat_id: int, title: str = None, messages: list = None) -> dict:
        label = str(uuid.uuid4())
        generate_title = False
        if not title:
            size = len(self.context[uid]) + 1
            title = f"Convo {size}"
            generate_title = True

        convo = {
            "id": label.replace("-", "")[:10],
            "label": label,
            "chat_id": chat_id,
            "title": title,
            "generate_title": generate_title,
            "context": messages if messages else [],
        }
        self.context[uid].append(convo)
        self.append_to_disk(uid, [convo])

        return convo

    def sync_convo(self, uid: str):
        convo_list = self.context[uid]
        file = self.session_path.joinpath(uid + '.json')
        file.write_text(json.dumps(convo_list, ensure_ascii=False))

    def enroll(self, uid: str, messages=None) -> list:
        convo = []
        self.context[uid] = convo
        self.append_to_disk(uid, convo)

        return convo

    def is_enrolled(self, uid: str) -> bool:
        data = self.context.get(uid, None)
        if data is not None:
            return True

        file = self.session_path.joinpath(uid + '.json')
        return file.exists()
