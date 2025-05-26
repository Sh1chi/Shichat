# Импорт стандартных библиотек
import json
import socket
import time
from datetime import datetime
from collections import defaultdict
from typing import Dict

# Импорт компонентов PyQt5
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QTextBrowser,
    QSplitter,
    QLabel,
    QMessageBox,
)

from NetworkWorker import NetworkWorker


# -------------------------- Главное окно чата ----------------------------
class ChatWindow(QWidget):
    def __init__(self, username: str, sock: socket.socket):
        super().__init__()
        self.username = username
        self.sock = sock
        self.setWindowTitle(f"Shichat — {self.username}")
        self.resize(900, 600)

        # Словарь для хранения истории сообщений
        self.messages: Dict[str, list] = defaultdict(list)
        self.current_peer: str | None = None  # текущий собеседник

        # ---------- Интерфейс ----------

        # Основной разделитель: список слева, чат справа
        splitter = QSplitter(self)

        # Список пользователей
        self.user_list = QListWidget()
        self.user_list.itemClicked.connect(self.change_chat)
        splitter.addWidget(self.user_list)

        # Правая панель — заголовок, переписка и ввод
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок текущего чата
        self.header = QLabel("Выберите чат")
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setStyleSheet("font-size:16px;padding:8px;")
        right_layout.addWidget(self.header)

        # Область для отображения сообщений
        self.chat_view = QTextBrowser()
        self.chat_view.setStyleSheet("background:#F5F5F5;padding:8px;")
        self.chat_view.setOpenExternalLinks(True)
        right_layout.addWidget(self.chat_view, 1)

        # Поле ввода + кнопка отправки
        input_panel = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Напишите сообщение…")
        self.input_edit.returnPressed.connect(self.send_message)

        self.send_btn = QPushButton("➤")
        self.send_btn.clicked.connect(self.send_message)
        input_panel.addWidget(self.input_edit, 1)
        input_panel.addWidget(self.send_btn)
        right_layout.addLayout(input_panel)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 1)

        main_layout = QHBoxLayout(self)
        main_layout.addWidget(splitter)

        # ---------- Подключение к сети ----------
        self.net = NetworkWorker(sock)
        self.net.message_received.connect(self.on_message)
        self.net.userlist_received.connect(self.on_userlist)
        self.net.connection_lost.connect(self.on_disconnect)
        self.net.start()

    def _format_msg_html(self, text: str, outgoing: bool, ts: int) -> str:
        # Форматирование сообщения как HTML "пузыря"
        time_str = datetime.fromtimestamp(ts).strftime("%H:%M")
        align = "right" if outgoing else "left"
        margin = "margin-left:40%;" if outgoing else "margin-right:40%;"
        bg_color = "#DCF8C6" if outgoing else "#FFFFFF"

        html = (
            f'<div style="text-align:{align}; {margin} padding:4px 0;">'
            f'  <div style="background:{bg_color}; '
            f'              border-radius:12px; '
            f'              padding:6px 10px; '
            f'              display:inline-block; '
            f'              font-size:14px; '
            f'              white-space:pre-wrap;">'
            f'    {text}'
            f'    <div style="font-size:10px; color:#555; text-align:right;">{time_str}</div>'
            f'  </div>'
            f'</div>'
        )
        return html

    def change_chat(self, item: QListWidgetItem):
        # Переключение на выбранный чат
        peer = item.text()
        self.current_peer = peer
        self.header.setText(peer)
        self.chat_view.clear()
        for msg in self.messages[peer]:
            outgoing = msg["from"] == self.username
            self.chat_view.append(
                self._format_msg_html(msg["content"], outgoing, msg["timestamp"])
            )
        self.chat_view.moveCursor(QTextCursor.End)

    def on_userlist(self, users: list):
        # Обновление списка пользователей
        current = self.current_peer
        self.user_list.clear()
        for user in sorted(u for u in users if u != self.username):
            self.user_list.addItem(QListWidgetItem(user))
        if current and any(u == current for u in users):
            items = self.user_list.findItems(current, Qt.MatchExactly)
            if items:
                self.user_list.setCurrentItem(items[0])

    def on_message(self, pkt: dict):
        # Обработка входящего сообщения
        frm, to, content = pkt.get("from"), pkt.get("to"), pkt.get("content")
        ts = pkt.get("timestamp", int(time.time()))
        peer = frm if frm != self.username else to

        self.messages[peer].append({
            "from": frm,
            "to": to,
            "content": content,
            "timestamp": ts,
        })

        outgoing = frm == self.username

        if peer == self.current_peer:
            self.chat_view.append(self._format_msg_html(content, outgoing, ts))
            self.chat_view.moveCursor(QTextCursor.End)

    def send_message(self):
        # Отправка сообщения на сервер
        text = self.input_edit.text().strip()
        if not text or not self.current_peer:
            return

        pkt = {
            "type": "message",
            "from": self.username,
            "to": self.current_peer,
            "content": text,
            "timestamp": int(time.time()),
        }
        try:
            self.sock.sendall((json.dumps(pkt) + "\n").encode())
        except OSError:
            self.on_disconnect()
            return
        self.input_edit.clear()  # очищаем поле ввода

    def on_disconnect(self):
        # Обработка потери соединения
        QMessageBox.critical(self, "Отключено", "Соединение с сервером потеряно")
        self.close()

    def closeEvent(self, event):
        # При закрытии окна останавливаем сетевой поток
        self.net.stop()
        super().closeEvent(event)