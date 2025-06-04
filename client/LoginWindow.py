# Импорт стандартных библиотек
import json
import socket


# Импорт виджетов и оконных компонентов из PyQt5
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QMessageBox,
)

# Импорт других окон и темы оформления
from ChatWindow import ChatWindow
from theme import DarkTheme as T
from SignupWindow import SignupWindow

# Адрес сервера, к которому подключается клиент
SERVER_HOST = "localhost"
SERVER_PORT = 8080


# Класс LoginWindow — отвечает за окно входа пользователя.
# Позволяет ввести логин и пароль, подключиться к серверу,
# обработать ответ и открыть главное окно чата.
class LoginWindow(QWidget):
    # Конструктор: создаёт форму авторизации с нужными стилями и кнопками
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Shichat — Вход")
        self.resize(300, 120)
        self.setStyleSheet(f"background:{T.BG}; color:{T.TEXT_MAIN};")

        # Основной вертикальный контейнер
        layout = QVBoxLayout(self)

        # Поле для ввода логина
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Введите имя")
        self.name_edit.setStyleSheet(T.qss_input())
        layout.addWidget(self.name_edit)

        # Поле для ввода пароля
        self.pass_edit = QLineEdit()
        self.pass_edit.setPlaceholderText("Введите пароль")
        self.pass_edit.setEchoMode(QLineEdit.Password)  # скрывает вводимые символы
        self.pass_edit.setStyleSheet(T.qss_input())
        layout.addWidget(self.pass_edit)

        # Кнопка входа
        self.join_btn = QPushButton("Войти")
        self.join_btn.setStyleSheet(T.qss_button())
        self.join_btn.clicked.connect(self.try_login)
        layout.addWidget(self.join_btn)

        # Кнопка перехода к регистрации
        self.signup_btn = QPushButton("Регистрация")
        self.signup_btn.setStyleSheet(T.qss_button())
        self.signup_btn.clicked.connect(self.open_signup)
        layout.addWidget(self.signup_btn)


    # Выполняет вход пользователя в систему.
    # Проверяет заполненность полей, подключается к серверу, отправляет логин и пароль.
    # В случае успешного ответа — открывает главное окно чата.
    def try_login(self):
        # Считываем и обрезаем пробелы с введённых значений
        username = self.name_edit.text().strip()
        password = self.pass_edit.text().strip()

        # Проверка на обязательные поля
        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Введите имя и пароль")
            return

        # Подготовка JSON-пакета авторизации заранее
        pkt = {
            "type": "signin",
            "from": username,
            "password": password,
        }

        try:
            # Устанавливаем TCP-соединение с сервером
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((SERVER_HOST, SERVER_PORT))

            # Отправляем JSON-пакет, преобразованный в строку + символ новой строки
            sock.sendall((json.dumps(pkt) + "\n").encode())

            # Ждём ответ от сервера
            resp = sock.recv(4096).decode()
            # Преобразуем строку в словарь Python
            data = json.loads(resp)

            if data.get("type") == "login_ok":
                self.main = ChatWindow(username, sock)
                self.main.show()
                self.close()
            else:
                QMessageBox.warning(self, "Ошибка", data.get("content", "Неизвестная ошибка"))
                sock.close()

        except OSError as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться: {e}")


    # Открывает окно регистрации.
    # При нажатии на кнопку "Регистрация" создаётся новое окно SignupWindow,
    # и отображается поверх текущего окна входа.
    def open_signup(self):
        self.signup = SignupWindow()  # создаём окно регистрации
        self.signup.show()            # отображаем его пользователю
