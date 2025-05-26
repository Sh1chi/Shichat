"""bubble.py
~~~~~~~~~~~~
Формирует HTML‑разметку одного сообщения‑«пузыря».

Использование:
    from bubble import Bubble
    html = Bubble.html("Привет!", outgoing=True, ts=time.time())
"""

from datetime import datetime
from theme import DarkTheme as T


class Bubble:
    """Статический генератор HTML‑«пузырей», цвета берутся из Theme."""

    @classmethod
    def html(cls, text: str, outgoing: bool, ts: int) -> str:
        """Вернёт HTML «пузыря» (как строку)."""
        side = "right" if outgoing else "left"
        bg_color = T.ACCENT if outgoing else T.PANEL
        time_str = datetime.fromtimestamp(ts).strftime("%H:%M")

        return (
            f'<div style="width:100%; overflow:hidden; margin:4px 0;">'
            f'  <div style="float:{side}; background:{bg_color}; '
            f'              color:{T.TEXT_MAIN}; border-radius:12px; '
            f'              padding:6px 10px; max-width:60%; '
            f'              display:inline-block; font-size:14px; '
            f'              white-space:pre-wrap;">'
            f'    {text}'
            f'    <div style="font-size:10px; color:{T.TEXT_SUB}; '
            f'                text-align:right;">{time_str}</div>'
            f'  </div>'
            f'</div>'
        )
