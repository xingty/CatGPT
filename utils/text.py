MAX_TEXT_LENGTH = 3900


def messages_to_segments(messages: list, max_length: int = MAX_TEXT_LENGTH):
    segment = ''
    total_len = 0
    segments = []
    for m in messages:
        if m['role'] == 'system':
            continue

        text = f'### {m["role"]}\n{m["content"]}\n\n'
        text_len = len(text)
        if total_len + text_len > max_length:
            segments.append(segment)
            segment = ''
            total_len = 0

        segment += text
        total_len += text_len

    if total_len > max_length:
        segment = segment[0:max_length - 3] + '...'

    if len(segment) > 0:
        segments.append(segment)

    return segments


def split_by_length(text: str, length: int = MAX_TEXT_LENGTH):
    return [text[i:i + length] for i in range(0, len(text), length)]


def split_to_segments(text: str, search_result: str, length: int = MAX_TEXT_LENGTH):
    segments = split_by_length(text, length)
    if (len(segments[-1]) + len(search_result)) > length:
        segments.append(search_result)
    elif search_result:
        segments[-1] = segments[-1] + '\n\n' + search_result

    return segments
