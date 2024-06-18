from ..storage import types

MAX_TEXT_LENGTH = 4096


def messages_to_segments(
    messages: list[types.Message], max_length: int = MAX_TEXT_LENGTH
):
    segment = ""
    total_len = 0
    segments = []
    for m in messages:
        if m.role == "system":
            continue

        text = f"## {m.role}\n{m.content}\n\n"
        text_len = len(text)
        if total_len + text_len > max_length:
            segments.append(segment)
            segment = ""
            total_len = 0

        segment += text
        total_len += text_len

    if total_len > max_length:
        segment = segment[0 : max_length - 3] + "..."

    if len(segment) > 0:
        segments.append(segment)

    return segments


def split_by_length(text: str, length: int = MAX_TEXT_LENGTH):
    return [text[i : i + length] for i in range(0, len(text), length)]


def split_to_segments(text: str, search_result: str, length: int = MAX_TEXT_LENGTH):
    segments = split_by_length(text, length)
    if (len(segments[-1]) + len(search_result)) > length:
        segments.append(search_result)
    elif search_result:
        segments[-1] = segments[-1] + "\n\n" + search_result

    return segments


def get_timeout_from_text(text: str) -> int:
    text = text.strip()
    try:
        index = text.rfind(" ")
        return int(text[index + 1 :])
    except ValueError:
        return -1


def decode_message_id(msg_id_str: str) -> list[int]:
    ids = msg_id_str.split(",")
    message_id = int(ids[0])
    real_message_ids = [message_id]

    for i in range(1, len(ids)):
        real_message_ids.append(int(ids[i]) + message_id)

    return real_message_ids


def encode_message_id(message_ids: list[int]) -> str:
    assert len(message_ids) > 0, "message ids cannot be empty"

    first_id = message_ids[0]
    encoded_message_ids = str(first_id)
    for i in range(1, len(message_ids)):
        offset = message_ids[i] - first_id
        encoded_message_ids = encoded_message_ids + "," + str(offset)

    return encoded_message_ids
