import telegramify_markdown


def escape(markdown_text: str):
    return telegramify_markdown.markdownify(
        content=markdown_text,
        max_line_length=256
    )
