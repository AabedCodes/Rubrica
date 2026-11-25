"""Remove active image and raw HTML nodes from model-written Markdown (C07)."""

import re
from html.parser import HTMLParser

from mistune import create_markdown
from mistune.renderers.markdown import MarkdownRenderer

_LITERAL_PUNCTUATION = re.compile(r"([\\!\[\]<>\x60*_])")


def _literal(text: str) -> str:
    return _LITERAL_PUNCTUATION.sub(r"\\\1", text)


class _HTMLText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


class _SafeMarkdown(MarkdownRenderer):
    def text(self, token, state) -> str:
        return _literal(token["raw"])

    def link(self, token, state) -> str:
        # Reference links already contain their parsed URL. Inline them so
        # definitions used only by stripped images can be discarded.
        return super().link({**token, "label": None}, state)

    def render_referrences(self, state):
        return ()

    def image(self, token, state) -> str:
        return "[image removed]"

    def inline_html(self, token, state) -> str:
        return ""

    def block_html(self, token, state) -> str:
        parser = _HTMLText()
        parser.feed(token["raw"])
        parser.close()
        return _literal("".join(parser.parts)).strip() + "\n\n"


_render = create_markdown(renderer=_SafeMarkdown())


def clean_model_text(markdown: str) -> str:
    """Normalize Markdown while retaining ordinary links and literal code."""
    return _render(markdown)
