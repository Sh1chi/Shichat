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

class ChatItem(QWidget):
    def __init__(self, display_name: str, last_msg: str, last_ts: int):
        super().__init__()
        self.default_bg = T.BG             # "#1F1F1F" :contentReference[oaicite:0]{index=0}
        self.sel_bg     = T.ACCENT         # "#2481CC" :contentReference[oaicite:1]{index=1}
        self.setAutoFillBackground(True)

        # Вертикальный лэйаут: вверху — имя+время, внизу — превью
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(8, 4, 8, 4)
        vbox.setSpacing(2)

        # — Верхний ряд: display_name (T.TEXT_MAIN) + время (T.TEXT_SUB)
        row = QHBoxLayout()
        self.lbl_name = QLabel(display_name)
        self.lbl_name.setStyleSheet(
            f"color:{T.TEXT_MAIN}; font-weight:bold; font-size:15px;"
        )
        row.addWidget(self.lbl_name, 1)

        ts_str = datetime.fromtimestamp(last_ts).strftime("%H:%M")
        self.lbl_time = QLabel(ts_str)
        self.lbl_time.setStyleSheet(
            f"color:{T.TEXT_SUB}; font-size:11px;"
        )
        row.addWidget(self.lbl_time, 0, Qt.AlignRight)
        vbox.addLayout(row)

        # — Нижний ряд: превью (T.TEXT_SUB)
        self.lbl_preview = QLabel(last_msg)
        self.lbl_preview.setStyleSheet(
            f"color:{T.TEXT_SUB}; font-size:13px;"
        )
        # Одна строка в высоту
        self.lbl_preview.setFixedHeight(
            self.lbl_preview.fontMetrics().lineSpacing()
        )
        vbox.addWidget(self.lbl_preview)

        self._selected = False
        self._update_style()

    def setSelected(self, sel: bool):
        self._selected = sel
        self._update_style()

    def _update_style(self):
        bg = self.sel_bg if self._selected else self.default_bg
        # фон блока
        self.setStyleSheet(f"background:{bg};")
        # текст при выборе белый, иначе T.TEXT_MAIN / T.TEXT_SUB
        name_col    = "#FFFFFF" if self._selected else T.TEXT_MAIN
        preview_col = "#FFFFFF" if self._selected else T.TEXT_SUB
        time_col    = "#FFFFFF" if self._selected else T.TEXT_SUB

        self.lbl_name.setStyleSheet(
            f"color:{name_col}; font-weight:bold; font-size:15px;"
        )
        self.lbl_preview.setStyleSheet(
            f"color:{preview_col}; font-size:13px;"
        )
        self.lbl_time.setStyleSheet(
            f"color:{time_col}; font-size:11px;"
        )

