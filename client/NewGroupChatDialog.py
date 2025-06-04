# Импорт компонентов PyQt5
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QListView,
    QDialog,
    QLabel,
)

from theme import DarkTheme as T


# Диалог создания группового чата
# Позволяет задать название, выбрать участников и отправить запрос серверу
class NewGroupChatDialog(QDialog):
    def __init__(self, net_worker, current_user: str, parent=None):
        super().__init__(parent)

        self.net = net_worker                   # сетевой обработчик
        self.current_user = current_user        # имя текущего пользователя
        self.selected_users: set[str] = set()   # выбранные участники (username'ы)

        self.setWindowTitle("Создать групповой чат")
        self.resize(520, 420)
        self.setStyleSheet(f"background:{T.PANEL}; border-radius:8px;")

        root = QVBoxLayout(self)  # основной вертикальный layout всего окна
        root.setContentsMargins(16, 16, 16, 16)  # отступы от краёв окна (слева, сверху, справа, снизу)
        root.setSpacing(12)  # расстояние между элементами внутри layout

        # Заголовок
        title = QLabel("Создать группу")
        title.setStyleSheet(
            f"color:{T.TEXT_MAIN}; font-size:18px; font-weight:bold;"
        )
        root.addWidget(title)

        # Поле ввода названия группы
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название группы")
        self.name_input.setStyleSheet(T.qss_input())
        root.addWidget(self.name_input)

        # Блок с выбранными участниками (чипы)
        lbl_participants = QLabel("Участники:")
        lbl_participants.setStyleSheet(f"color:{T.TEXT_SUB}; font-size:13px;")
        root.addWidget(lbl_participants)

        # Список выбранных участников (отображаются как «чипы» в одну строку)
        self.chosen_list = QListWidget()
        self.chosen_list.setFlow(QListView.LeftToRight)  # горизонтальное отображение
        self.chosen_list.setWrapping(True)       # перенос строк
        self.chosen_list.setFixedHeight(60)
        self.chosen_list.setStyleSheet(T.qss_user_list() + "QListWidget {font-size:13px;}")
        root.addWidget(self.chosen_list)

        # Поле поиска пользователей
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по нику или имени…")
        self.search_input.setStyleSheet(T.qss_input())
        root.addWidget(self.search_input)

        # Список результатов поиска
        self.result_list = QListWidget()
        self.result_list.setStyleSheet(T.qss_user_list() + T.qss_user_list_large(size=14))
        root.addWidget(self.result_list, 1)

        # Кнопки "Создать" и "Отмена"
        btns = QHBoxLayout()
        self.ok_btn = QPushButton("Создать")
        self.ok_btn.setEnabled(False)
        self.ok_btn.setStyleSheet(T.qss_button())
        btns.addWidget(self.ok_btn)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet(T.qss_button_dark())
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        root.addLayout(btns)

        # Сигналы
        self.name_input.textChanged.connect(self._update_ok_enabled)
        self.search_input.textChanged.connect(self._on_search_text)
        self.result_list.itemDoubleClicked.connect(self._add_selected)
        self.chosen_list.itemDoubleClicked.connect(self._remove_selected)
        self.ok_btn.clicked.connect(self._on_ok)

        self.net.user_search_result.connect(self._on_search_results)


    # Отправка запроса на поиск, если строка непустая
    def _on_search_text(self, text: str):
        query = text.strip()
        if query:
            self.net.send_user_search(query)   # отправляем запрос на сервер
        else:
            self.result_list.clear()   # если поле пустое — очищаем список


    # Обработка результатов поиска от сервера
    def _on_search_results(self, users: list):
        self.result_list.clear()
        for u in users:
            if u["username"] == self.current_user:
                continue    # исключаем самого себя из результатов
            item = QListWidgetItem(f"{u['display_name']} ({u['username']})")
            item.setData(Qt.UserRole, u["username"])      # сохраняем username в item
            if u["username"] in self.selected_users:
                item.setSelected(True)       # выделяем уже выбранных участников
            self.result_list.addItem(item)   # добавляем в список результатов


    # Добавление пользователя в список участников
    def _add_selected(self, item: QListWidgetItem):
        uname = item.data(Qt.UserRole)
        if uname not in self.selected_users:
            self.selected_users.add(uname)  # добавляем в набор выбранных
            chip = QListWidgetItem(item.text())  # создаём «чип» для отображения
            chip.setData(Qt.UserRole, uname)
            self.chosen_list.addItem(chip)  # добавляем в панель выбранных
            self._update_ok_enabled()  # проверяем, можно ли включить кнопку


    # Удаление участника из списка (по двойному клику на «чип»)
    def _remove_selected(self, chip_item: QListWidgetItem):
        uname = chip_item.data(Qt.UserRole)
        self.selected_users.discard(uname)  # удаляем из набора
        row = self.chosen_list.row(chip_item)
        self.chosen_list.takeItem(row)  # удаляем чип из списка
        self._update_ok_enabled()

        # Снимаем выделение в списке поиска, если этот пользователь там есть
        for i in range(self.result_list.count()):
            it = self.result_list.item(i)
            if it.data(Qt.UserRole) == uname:
                it.setSelected(False)
                break


    # Проверка, можно ли активировать кнопку "Создать"
    def _update_ok_enabled(self):
        has_name = bool(self.name_input.text().strip())   # введено ли название
        has_users = bool(self.selected_users)             # выбран ли хотя бы один пользователь
        self.ok_btn.setEnabled(has_name and has_users)    # активируем кнопку, если оба условия выполнены


    # Подтверждение создания группы и отправка данных на сервер
    def _on_ok(self):
        name = self.name_input.text().strip()
        participants = list(self.selected_users)        # преобразуем set в список
        self.net.send_create_group(name, participants)   # отправляем запрос
        self.accept()   # закрываем диалог
