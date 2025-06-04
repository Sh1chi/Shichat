# Импорт компонентов PyQt5
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QDialog, QLabel,
)

from theme import DarkTheme as T


# Диалог создания нового чата с пользователем
# Отображает поле поиска, список найденных пользователей и кнопки управления
class NewChatDialog(QDialog):
    def __init__(self, net_worker, parent=None):
        super().__init__(parent)
        self.net = net_worker   # сетевой обработчик, через него отправляются запросы на сервер

        self.setWindowTitle("Новый чат")
        self.resize(400, 300)
        self.setStyleSheet(f"background:{T.PANEL}; border-radius:8px;")   # тёмный фон окна

        layout = QVBoxLayout(self)  # основной вертикальный layout для элементов окна
        layout.setContentsMargins(16, 16, 16, 16)  # внутренние отступы от краёв (слева, сверху, справа, снизу)
        layout.setSpacing(10)  # расстояние между элементами внутри layout

        # Заголовок окна
        title = QLabel("Поиск пользователя")
        title.setStyleSheet(f"color:{T.TEXT_MAIN}; font-size:16px; font-weight:bold;")
        layout.addWidget(title)

        # Поле ввода запроса для поиска пользователей
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по нику и имени...")
        self.search_input.setStyleSheet(T.qss_input())
        layout.addWidget(self.search_input)

        # Список найденных пользователей
        self.result_list = QListWidget()
        self.result_list.setStyleSheet(
            T.qss_user_list() + T.qss_user_list_large(size=14)
        )
        layout.addWidget(self.result_list, 1)

        # Кнопки действия (Начать чат / Отмена)

        btn_layout = QHBoxLayout()

        self.ok_btn = QPushButton("Начать чат")
        self.ok_btn.setEnabled(False)   # по умолчанию кнопка отключена
        self.ok_btn.setStyleSheet(T.qss_button())
        self.ok_btn.clicked.connect(self.on_ok)
        btn_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setStyleSheet(T.qss_button_dark())
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

        # Подключение сигналов
        self.search_input.textChanged.connect(self.on_search_text)
        self.net.user_search_result.connect(self.on_search_results)
        self.result_list.itemSelectionChanged.connect(self.on_item_selected)
        self.ok_btn.clicked.connect(self.on_ok)
        self.cancel_btn.clicked.connect(self.reject)


    # Обработка изменения текста в поле поиска
    def on_search_text(self, text: str):
        query = text.strip()
        if query:
            self.net.send_user_search(query)   # отправляем запрос на сервер


    # Обработка полученного списка пользователей от сервера
    def on_search_results(self, users: list):
        self.result_list.clear()
        for u in users:
            item = QListWidgetItem(f"{u['display_name']} ({u['username']})")
            item.setData(Qt.UserRole, u['username'])  # сохраняем username
            self.result_list.addItem(item)


    # Разрешаем кнопку "Начать чат" только при выборе пользователя
    def on_item_selected(self):
        self.ok_btn.setEnabled(bool(self.result_list.currentItem()))


    # При подтверждении — отправляем запрос на создание чата и закрываем окно
    def on_ok(self):
        peer = self.result_list.currentItem().data(Qt.UserRole)
        self.net.send_start_chat(peer)
        self.accept()