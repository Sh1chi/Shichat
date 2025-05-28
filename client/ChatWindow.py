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
    QMessageBox, QDialog,
)

from NetworkWorker import NetworkWorker
from Bubble import Bubble
from theme import DarkTheme as T
from ChatItem import ChatItem
from NewChatDialog import NewChatDialog


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
        self.setStyleSheet(f"background:{T.BG}; color:{T.TEXT_MAIN};")

        # Основной разделитель: список слева, чат справа
        splitter = QSplitter(self)


        # Список пользователей
        self.chat_list = QListWidget()
        self.chat_list.itemClicked.connect(self.change_chat)
        self.chat_list.setStyleSheet(T.qss_user_list())
        self.chat_list.itemSelectionChanged.connect(self.update_selection_styles)
        splitter.addWidget(self.chat_list)

        # Правая панель — заголовок, переписка и ввод
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок текущего чата
        self.header = QLabel("Выберите чат")
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setStyleSheet(T.qss_header())
        right_layout.addWidget(self.header)

        # Область для отображения сообщений
        self.chat_view = QTextBrowser()
        self.chat_view.setStyleSheet(T.qss_chat_view())
        self.chat_view.setOpenExternalLinks(True)
        right_layout.addWidget(self.chat_view, 1)

        # Поле ввода + кнопка отправки
        input_panel = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Напишите сообщение…")
        self.input_edit.returnPressed.connect(self.send_message)
        self.input_edit.setStyleSheet(T.qss_input())

        self.send_btn = QPushButton("➤")
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setStyleSheet(T.qss_button())

        input_panel.addWidget(self.input_edit, 1)
        input_panel.addWidget(self.send_btn)
        right_layout.addLayout(input_panel)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 1)

        main_layout = QHBoxLayout(self)
        main_layout.addWidget(splitter)


        # Добавляем кнопку "Новый чат" над списком
        self.new_chat_btn = QPushButton("+ Новый чат")
        self.new_chat_btn.setStyleSheet(T.qss_button())
        self.new_chat_btn.clicked.connect(self.open_new_chat)
        # Предполагаем, что chat_list обёрнут в layout, вставляем кнопку
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.new_chat_btn)
        left_layout.addWidget(self.chat_list)
        splitter.insertWidget(0, QWidget())  # очистить первый виджет
        splitter.widget(0).setLayout(left_layout)


        # ---------- Подключение к сети ----------
        self.net = NetworkWorker(sock)
        self.net.message_received.connect(self.on_message)
        self.net.chatlist_received.connect(self.on_chatlist)
        self.net.connection_lost.connect(self.on_disconnect)
        self.net.start()


    def change_chat(self, item: QListWidgetItem):
        # Переключение на выбранный чат
        peer = item.data(Qt.UserRole)
        self.current_peer = peer
        self.header.setText(item.text().split("\n", 1)[0])
        self.chat_view.clear()
        self.messages[peer].clear()

        # Запрашиваем историю сообщений с сервера
        pkt = {
            "type": "history",
            "from": self.username,
            "to": peer,
        }
        try:
            self.sock.sendall((json.dumps(pkt) + "\n").encode())
        except OSError:
            self.on_disconnect()
            return


    def on_chatlist(self, chats):
        # Сохраним текущее открытое peer
        prev = self.current_peer

        self.chat_list.clear()
        self.current_peer = None

        for c in chats:
            widget = ChatItem(
                display_name=c['display_name'],
                last_msg=c['last_msg'][:100],
                last_ts=c['last_ts']
            )
            item = QListWidgetItem(self.chat_list)
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.UserRole, c['peer'])
            self.chat_list.addItem(item)
            self.chat_list.setItemWidget(item, widget)

            # Если это тот же peer, что сейчас открыт — помечаем его
            if c['peer'] == prev:
                self.current_peer = prev
                # выставляем его выделенным в QListWidget
                self.chat_list.setCurrentItem(item)

        # Если prev не None, то обновим хедер на display_name
        if self.current_peer:
            # найдём widget/text для текущего айтема
            current = self.chat_list.currentItem()
            if current:
                # текст першей строки — display_name
                display = current.text().split("\n", 1)[0]
                self.header.setText(display)

        # Наконец, обновляем стили всех элементов
        self.update_selection_styles()


    def update_selection_styles(self):
        # для каждого элемента включаем/выключаем selected-стиль
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            widget = self.chat_list.itemWidget(item)
            if widget:
                widget.setSelected(item.isSelected())


    """
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
"""


    def on_message(self, pkt: dict):
        # Обработка входящего сообщения
        frm, to, content = pkt.get("from"), pkt.get("to"), pkt.get("content")
        ts = pkt.get("timestamp", int(time.time()))
        peer = to if to != self.username else frm

        self.messages[peer].append({
            "from": frm,
            "to": to,
            "content": content,
            "timestamp": ts,
        })

        outgoing = frm == self.username

        if peer == self.current_peer:
            self.chat_view.append(Bubble.html(content, outgoing, ts))
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


    def open_new_chat(self):
        dlg = NewChatDialog(self.net, self)
        if dlg.exec_() == QDialog.Accepted:
            # После server response в on_chat_created
            pass


    def on_chat_created(self, data: dict):
        # Сервер отправляет:
        # {type: 'chat_created', chat_id:..., peer:..., display_name:..., last_msg:'', last_ts:...}
        # Просто запросим обновлённый список чатов:
        self.net.send_request_chatlist()
