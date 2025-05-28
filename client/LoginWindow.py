# Импорт стандартных библиотек
import json
import socket


# Импорт компонентов PyQt5
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QMessageBox,
)


from ChatWindow import ChatWindow
from theme import DarkTheme as T
from SignupWindow import SignupWindow

# Константы для подключения к серверу
SERVER_HOST = "localhost"
SERVER_PORT = 8080


# -------------------------- Окно входа ----------------------------
class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shichat — Вход")
        self.resize(300, 120)
        self.setStyleSheet(f"background:{T.BG}; color:{T.TEXT_MAIN};")

        layout = QVBoxLayout(self)

        # Поле для ввода имени
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Введите имя")
        self.name_edit.setStyleSheet(T.qss_input())

        # Поле для ввода пароля
        self.pass_edit = QLineEdit()
        self.pass_edit.setPlaceholderText("Введите пароль")
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.pass_edit.setStyleSheet(T.qss_input())

        # Кнопка "Войти"
        self.join_btn = QPushButton("Войти")
        self.join_btn.clicked.connect(self.try_login)
        self.join_btn.setStyleSheet(T.qss_button())

        self.signup_btn = QPushButton("Регистрация")
        self.signup_btn.clicked.connect(self.open_signup)
        self.signup_btn.setStyleSheet(T.qss_button())

        layout.addWidget(self.name_edit)
        layout.addWidget(self.pass_edit)
        layout.addWidget(self.join_btn)
        layout.addWidget(self.signup_btn)

    def try_login(self):
        username = self.name_edit.text().strip()
        password = self.pass_edit.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Введите имя и пароль")
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((SERVER_HOST, SERVER_PORT))

            # Отправляем пакет входа
            pkt = {
                "type": "signin",
                "from": username,
                "password": password,
            }
            sock.sendall((json.dumps(pkt) + "\n").encode())

            # Ожидаем ответ сервера
            resp = sock.recv(4096).decode()
            data = json.loads(resp)
            if data.get("type") == "login_ok":
                # Открываем окно чата
                self.main = ChatWindow(username, sock)
                self.main.show()
                self.close()
            else:
                QMessageBox.warning(self, "Ошибка", data.get("content", "Неизвестная ошибка"))
                sock.close()
        except OSError as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться: {e}")

    def open_signup(self):
        self.signup = SignupWindow()
        self.signup.show()
