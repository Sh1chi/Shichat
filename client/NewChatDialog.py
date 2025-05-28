# Импорт компонентов PyQt5
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QDialog,
)

from theme import DarkTheme as T

class NewChatDialog(QDialog):
    def __init__(self, net_worker, parent=None):
        super().__init__(parent)
        self.net = net_worker
        self.setWindowTitle("Новый чат")
        self.resize(400, 300)

        layout = QVBoxLayout(self)
        # Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по нику и имени...")
        layout.addWidget(self.search_input)

        # Список результатов
        self.result_list = QListWidget()
        layout.addWidget(self.result_list, 1)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("Начать чат")
        self.ok_btn.setEnabled(False)
        self.ok_btn.setStyleSheet(T.qss_button())
        self.ok_btn.clicked.connect(self.on_ok)
        btn_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setStyleSheet(T.qss_button_dark())
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        # Сигналы
        self.search_input.textChanged.connect(self.on_search_text)
        self.net.user_search_result.connect(self.on_search_results)
        self.result_list.itemSelectionChanged.connect(self.on_item_selected)
        self.ok_btn.clicked.connect(self.on_ok)
        self.cancel_btn.clicked.connect(self.reject)

    def on_search_text(self, text: str):
        query = text.strip()
        if query:
            self.net.send_user_search(query)

    def on_search_results(self, users: list):
        self.result_list.clear()
        for u in users:
            item = QListWidgetItem(f"{u['display_name']} ({u['username']})")
            item.setData(Qt.UserRole, u['username'])
            self.result_list.addItem(item)

    def on_item_selected(self):
        self.ok_btn.setEnabled(bool(self.result_list.currentItem()))

    def on_ok(self):
        peer = self.result_list.currentItem().data(Qt.UserRole)
        self.net.send_start_chat(peer)
        self.accept()