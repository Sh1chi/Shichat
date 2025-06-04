from datetime import datetime
from theme import DarkTheme as T

# Класс Bubble отвечает за создание HTML-блока для одного сообщения
class Bubble:
    # Возвращает HTML-представление сообщения
    # text — текст сообщения
    # outgoing — True, если сообщение исходящее (от нас)
    # ts — метка времени (timestamp)
    @classmethod
    def html(cls, text: str, outgoing: bool, ts: int) -> str:
        bg_out = T.ACCENT  # цвет исходящих сообщений
        bg_in = T.ACCENT_SOFT  # цвет входящих сообщений
        bg_color = bg_out if outgoing else bg_in  # выбираем нужный фон
        txt_color = T.TEXT_MAIN  # цвет текста
        sub_color = T.TEXT_SUB  # цвет времени
        time_str = datetime.fromtimestamp(ts).strftime("%H:%M")  # формат времени для подписи

        # HTML-блок самого пузыря — прямоугольник с текстом и временем
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

        # Вся обёртка — таблица с двумя ячейками (для выравнивания по краям)
        # Исходящие сообщения — справа, входящие — слева
        if outgoing:
            return (
                '<table width="100%" cellpadding="0" cellspacing="0" style="margin:4px 0;">'
                '  <tr>'
                '    <td></td>'   # пустое пространство слева
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
                '    <td></td>'   # пустое пространство справа
                '  </tr>'
                '</table>'
            )





