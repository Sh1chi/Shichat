# Импорт стандартных библиотек
from datetime import datetime

# Импорт компонентов PyQt5
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
)

from theme import DarkTheme as T

# Элемент списка чатов — отображает имя, время и последнее сообщение
class ChatItem(QWidget):
    def __init__(self, display_name: str, last_msg: str, last_ts: int):
        super().__init__()

        self.default_bg = T.BG         # фон по умолчанию (не выбран)
        self.sel_bg = T.ACCENT         # фон при выделении (выбран чат)
        self.setAutoFillBackground(True)

        # Основной вертикальный layout: верх — имя и время, низ — превью сообщения
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(8, 4, 8, 4)  # отступы от краёв
        vbox.setSpacing(2)

        # Верхний ряд: имя + время
        row = QHBoxLayout()

        self.lbl_name = QLabel(display_name)  # имя пользователя или название чата
        self.lbl_name.setStyleSheet(f"color:{T.TEXT_MAIN}; font-weight:bold; font-size:15px;")
        row.addWidget(self.lbl_name, 1)  # растягивается по ширине

        ts_str = datetime.fromtimestamp(last_ts).strftime("%H:%M")    # формат времени
        self.lbl_time = QLabel(ts_str)
        self.lbl_time.setStyleSheet( f"color:{T.TEXT_SUB}; font-size:11px;")

        row.addWidget(self.lbl_time, 0, Qt.AlignRight)   # время справа
        vbox.addLayout(row)

        # Нижний ряд: превью последнего сообщения
        self.lbl_preview = QLabel(last_msg)
        self.lbl_preview.setStyleSheet(f"color:{T.TEXT_SUB}; font-size:13px;")
        # Одна строка в высоту
        self.lbl_preview.setFixedHeight(self.lbl_preview.fontMetrics().lineSpacing()) # ограничиваем одной строкой
        vbox.addWidget(self.lbl_preview)

        self._selected = False  # флаг выделения
        self._update_style()  # применяем стиль


    # Устанавливает флаг выделения и обновляет стиль
    def setSelected(self, sel: bool):
        self._selected = sel
        self._update_style()


    # Обновляет фон и цвет текста в зависимости от состояния (выбран/не выбран)
    def _update_style(self):
        bg = self.sel_bg if self._selected else self.default_bg  # выбираем фон
        self.setStyleSheet(f"background:{bg};")  # применяем фон

        # Цвета текста: при выделении — белый, иначе стандартные из темы
        name_col = "#FFFFFF" if self._selected else T.TEXT_MAIN
        preview_col = "#FFFFFF" if self._selected else T.TEXT_SUB
        time_col = "#FFFFFF" if self._selected else T.TEXT_SUB

        self.lbl_name.setStyleSheet(
            f"color:{name_col}; font-weight:bold; font-size:15px;"
        )
        self.lbl_preview.setStyleSheet(
            f"color:{preview_col}; font-size:13px;"
        )
        self.lbl_time.setStyleSheet(
            f"color:{time_col}; font-size:11px;"
        )

