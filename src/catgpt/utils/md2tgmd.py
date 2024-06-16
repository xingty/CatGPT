import telegramify_markdown


def escape(markdown_text: str):
    return telegramify_markdown.convert(markdown_text)
