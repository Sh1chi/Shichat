# Импорт стандартных библиотек
import json
import socket
import time
from collections import defaultdict
from typing import Dict

# Импорт компонентов PyQt5
from PyQt5.QtCore import Qt
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
from NewGroupChatDialog import NewGroupChatDialog
from html import escape


# Главное окно чата.
# Отображает список чатов, историю переписки, поле ввода сообщений и заголовок текущего диалога.
# Также обрабатывает сетевые события через NetworkWorker (входящие сообщения, обновления и т.п.).
class ChatWindow(QWidget):
    def __init__(self, username: str, sock: socket.socket):
        super().__init__()
        self.username = username            # имя текущего пользователя
        self.sock = sock                   # сокет подключения к серверу

        # Сохраняем историю сообщений по каждому чату для устранения дубликатов
        self.shown_messages = set()
        # Имя текущего выбранного чата (username или ID группы)
        self.current_peer: str | None = None

        # Заголовок окна и базовые размеры
        self.setWindowTitle(f"Shichat — {self.username}")
        self.resize(900, 600)

        # Задаём общий фон и цвет текста по теме
        self.setStyleSheet(f"background:{T.BG}; color:{T.TEXT_MAIN};")

        # Основной горизонтальный layout с двумя панелями (список и чат)
        main_layout = QHBoxLayout(self)

        # Разделитель между левой и правой панелью
        splitter = QSplitter(self)
        main_layout.addWidget(splitter)

        # ------- Левая панель: кнопки и список чатов -------
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        # Кнопка «Новый чат»
        self.new_chat_btn = QPushButton("+ Новый чат")
        self.new_chat_btn.setStyleSheet(T.qss_button())
        self.new_chat_btn.clicked.connect(self.open_new_chat)
        left_layout.addWidget(self.new_chat_btn)

        # Кнопка «Новая группа»
        self.new_group_btn = QPushButton("+ Группа")
        self.new_group_btn.setStyleSheet(T.qss_button())
        self.new_group_btn.clicked.connect(self.open_new_group)
        left_layout.addWidget(self.new_group_btn)

        # Список чатов
        self.chat_list = QListWidget()
        self.chat_list.setStyleSheet(T.qss_user_list())
        self.chat_list.itemClicked.connect(self.change_chat)
        self.chat_list.itemClicked.connect(self.change_chat)
        self.chat_list.itemSelectionChanged.connect(self.update_selection_styles)
        left_layout.addWidget(self.chat_list, 1)

        splitter.addWidget(left_container)


        # -------- Правая панель (сообщения, ввод, заголовок) --------
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок — отображает имя текущего чата
        self.header = QLabel("Выберите чат")
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setStyleSheet(T.qss_header())
        right_layout.addWidget(self.header)

        # Область отображения сообщений
        self.chat_view = QTextBrowser()
        self.chat_view.setStyleSheet(T.qss_chat_view())
        self.chat_view.setOpenExternalLinks(True)
        right_layout.addWidget(self.chat_view, 1)

        # Нижняя панель: поле ввода + кнопка отправки
        input_panel = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Напишите сообщение…")
        self.input_edit.returnPressed.connect(self.send_message)
        self.input_edit.setStyleSheet(T.qss_input())
        input_panel.addWidget(self.input_edit, 1)

        self.send_btn = QPushButton("➤")
        self.send_btn.setStyleSheet(T.qss_button())
        self.send_btn.clicked.connect(self.send_message)
        input_panel.addWidget(self.send_btn)

        right_layout.addLayout(input_panel)

        splitter.addWidget(right_panel)                  # вставляем в splitter как второй виджет
        splitter.setStretchFactor(0, 1)     # левая панель — 1/4 ширины
        splitter.setStretchFactor(1, 3)     # правая панель — 3/4 ширины

        #Сетевое подключение (работает в фоне)
        self.net = NetworkWorker(sock)
        self.net.message_received.connect(self.on_message)
        self.net.chatlist_received.connect(self.on_chatlist)
        self.net.connection_lost.connect(self.on_disconnect)
        self.net.start()

    # Переключение на выбранный чат из списка.
    # Обновляет заголовок, очищает старые сообщения и отправляет запрос на историю с сервера.
    def change_chat(self, item: QListWidgetItem):
        widget = self.chat_list.itemWidget(item)
        display = widget.lbl_name.text()  # это уже либо title группы, либо display_name собеседника
        self.header.setText(display)

        # Получаем идентификатор чата или собеседника
        peer = item.data(Qt.UserRole)
        self.current_peer = peer

        # Очищаем окно сообщений и сбрасываем кэш
        self.chat_view.clear()
        self.shown_messages.clear()

        # Формируем и отправляем запрос на историю сообщений
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

    # Обработка нового списка чатов от сервера.
    # Обновляет визуальный список, восстанавливает активный чат и применяет стили выбора.
    def on_chatlist(self, chats):
        prev = self.current_peer  # Сохраняем текущий активный чат

        self.chat_list.clear()
        self.current_peer = None

        for c in chats:
            # Создаём виджет превью для чата
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

            # Если это тот же чат, что был открыт — выделяем снова
            if c['peer'] == prev:
                self.current_peer = prev
                self.chat_list.setCurrentItem(item)

        # Обновляем заголовок, если активный чат восстановлен
        if self.current_peer:
            current = self.chat_list.currentItem()
            if current:
                display = current.text().split("\n", 1)[0]
                self.header.setText(display)

        self.update_selection_styles()


    # Применяет стиль выделения к каждому элементу чата.
    # Используется для подсветки выбранного чата в списке.
    def update_selection_styles(self):
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            widget = self.chat_list.itemWidget(item)
            if widget:
                widget.setSelected(item.isSelected())


    # Обрабатывает входящее сообщение от сервера.
    # Проверяет, что сообщение не повторяется и относится к текущему открытому чату.
    # Если это групповой чат — добавляет имя отправителя. Затем выводит сообщение на экран.
    def on_message(self, pkt: dict):
        frm = pkt.get("from")
        to = pkt.get("to")
        content = pkt.get("content")
        ts = pkt.get("timestamp", int(time.time()))  # Если сервер не прислал время — используем текущее
        dispname = pkt.get("display_name", frm)  # Имя для отображения (если есть), иначе логин

        # Определяем, кому принадлежит чат — если сообщение нам, значит peer это отправитель
        peer = to if to != self.username else frm

        # Проверка на дубликат (чтобы одно сообщение не появилось дважды)
        msg_key = (frm, to, ts, content)
        if msg_key in self.shown_messages:
            return
        self.shown_messages.add(msg_key)

        # Если сообщение не для текущего открытого чата — игнорируем
        if peer != self.current_peer:
            return

        outgoing = (frm == self.username)  # Проверяем, мы ли автор сообщения

        # В групповом чате отображаем имя отправителя над сообщением
        if peer.isdigit():
            if not outgoing:
                header_html = (
                    f'<div style="color:#ffffff;font-size:12px;'
                    f'margin:0 8px 2px 8px;">'
                    f'{escape(dispname)}&nbsp;({escape(frm)})'
                    f'</div>'
                )
                self.chat_view.append(header_html)

        # Добавляем само сообщение в виде HTML-пузыря
        self.chat_view.append(Bubble.html(content, outgoing, ts))
        self.chat_view.moveCursor(QTextCursor.End)  # Прокручиваем чат вниз к новому сообщению


    # Отправляет текст из поля ввода на сервер как новое сообщение.
    # Проверяет, что текст не пустой, и отправляет его через сокет.
    def send_message(self):
        text = self.input_edit.text().strip()
        if not text or not self.current_peer:
            return  # Ничего не делаем, если поле пустое или не выбран чат

        pkt = {
            "type": "message",
            "from": self.username,
            "to": self.current_peer,
            "content": text,
            "timestamp": int(time.time()),
        }
        try:
            self.sock.sendall((json.dumps(pkt) + "\n").encode())  # Отправляем JSON-пакет на сервер
        except OSError:
            self.on_disconnect()  # Если соединение прервано — вызываем обработчик отключения
            return

        self.input_edit.clear()  # Очищаем поле ввода после отправки


    # Обработка потери соединения с сервером.
    # Показывает предупреждение и закрывает окно чата.
    def on_disconnect(self):
        QMessageBox.critical(self, "Отключено", "Соединение с сервером потеряно")
        self.close()


    # Обработка закрытия главного окна.
    # Останавливает сетевой поток перед выходом из приложения.
    def closeEvent(self, event):
        self.net.stop()
        super().closeEvent(event)


    # Открытие диалога создания нового приватного чата.
    # После выбора собеседника сервер создаст чат, и его появление будет обработано в on_chat_created.
    def open_new_chat(self):
        dlg = NewChatDialog(self.net, self)
        if dlg.exec_() == QDialog.Accepted:
            # После подтверждения сервер отправит событие 'chat_created'
            pass


    # Открытие диалога создания группового чата.
    # Собирает список пользователей из текущих чатов и передаёт его в диалог создания группы.
    def open_new_group(self):
        # Собираем список всех пользователей из текущего списка чатов
        all_users = []
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            username = item.data(Qt.UserRole)
            displayname = item.text().split("\n", 1)[0]
            all_users.append({
                "username": username,
                "display_name": displayname
            })

        # Открываем модальное окно создания группы
        dlg = NewGroupChatDialog(self.net, all_users, self)

        try:
            result = dlg.exec_()  # Ожидаем результат от пользователя
        except Exception as e:
            print("Ошибка при открытии окна создания группы:", e)
            return

        print(f"Результат диалога: {result}")
        if result == QDialog.Accepted:
            print("Групповой чат создан — ждём события group_created")



    # Обработка события создания нового чата от сервера.
    # Получает данные о созданном чате и может реализовать что-то
    def on_chat_created(self, data: dict):
        pass


    # Обработка события создания группового чата от сервера.
    # Получает данные о созданном групповом чате и может реализовать что-то
    def on_group_created(self, data):
        pass