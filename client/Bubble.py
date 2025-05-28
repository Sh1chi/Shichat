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
    @classmethod
    def html(cls, text: str, outgoing: bool, ts: int) -> str:
        # Цвета
        bg_out    = T.ACCENT                   # ваш цвет «исходящих»
        bg_in     = T.ACCENT_SOFT                    # цвет «входящих» (можно чуть светлее)
        bg_color  = bg_out if outgoing else bg_in
        txt_color = T.TEXT_MAIN
        sub_color = T.TEXT_SUB
        time_str  = datetime.fromtimestamp(ts).strftime("%H:%M")

        # HTML самого пузыря — inline-block, width:auto, max-width чтобы не расползалось
        bubble_div = (
            f'<div style="display:inline-block;'
            f' width:auto; max-width:60%; white-space:pre-wrap;'
            f' padding:8px 12px; border-radius:16px; overflow:hidden;'
            f' background:{bg_color}; color:{txt_color}; font-size:14px;">'
            f'  {text}'
            f'  <div style="font-size:10px; color:{sub_color}; '
            f'             text-align:right; margin-top:4px;">'
            f'    {time_str}'
            f'  </div>'
            f'</div>'
        )

        # Обёртка-таблица с двумя ячейками
        # Для outgoing — пустая ячейка слева, пузырь справа
        # Для incoming — наоборот
        if outgoing:
            return (
                '<table width="100%" cellpadding="0" cellspacing="0" style="margin:4px 0;">'
                '  <tr>'
                '    <td></td>'
                '    <td align="right" valign="top">'
                f'      {bubble_div}'
                '    </td>'
                '  </tr>'
                '</table>'
            )
        else:
            return (
                '<table width="100%" cellpadding="0" cellspacing="0" style="margin:4px 0;">'
                '  <tr>'
                '    <td align="left" valign="top">'
                f'      {bubble_div}'
                '    </td>'
                '    <td></td>'
                '  </tr>'
                '</table>'
            )





