import json
import socket
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QMessageBox
from theme import DarkTheme as T

SERVER_HOST = "localhost"
SERVER_PORT = 8080

class SignupWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shichat — Регистрация")
        self.resize(300, 220)
        self.setStyleSheet(f"background:{T.BG}; color:{T.TEXT_MAIN};")

        layout = QVBoxLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Имя пользователя (логин)")
        self.name_edit.setStyleSheet(T.qss_input())

        self.first_edit = QLineEdit()
        self.first_edit.setPlaceholderText("Имя")
        self.first_edit.setStyleSheet(T.qss_input())

        self.last_edit = QLineEdit()
        self.last_edit.setPlaceholderText("Фамилия")
        self.last_edit.setStyleSheet(T.qss_input())

        self.pass_edit = QLineEdit()
        self.pass_edit.setPlaceholderText("Пароль")
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.pass_edit.setStyleSheet(T.qss_input())

        self.signup_btn = QPushButton("Зарегистрироваться")
        self.signup_btn.clicked.connect(self.try_signup)
        self.signup_btn.setStyleSheet(T.qss_button())

        layout.addWidget(self.name_edit)
        layout.addWidget(self.first_edit)
        layout.addWidget(self.last_edit)
        layout.addWidget(self.pass_edit)
        layout.addWidget(self.signup_btn)

    def try_signup(self):
        username = self.name_edit.text().strip()
        first = self.first_edit.text().strip()
        last = self.last_edit.text().strip()
        password = self.pass_edit.text().strip()

        if not username or not first or not password:
            QMessageBox.warning(self, "Ошибка", "Логин, имя и пароль обязательны")
            return

        pkt = {
            "type": "signup",
            "from": username,
            "password": password,
            "first_name": first,
            "last_name": last,
        }

        try:
            sock = socket.socket()
            sock.connect((SERVER_HOST, SERVER_PORT))
            # Отправляем ровно одну JSON-строку с \n в конце
            raw = json.dumps(pkt) + "\n"
            sock.sendall(raw.encode())

            # Читаем ровно до первой \n
            buffer = ""
            while True:
                chunk = sock.recv(1024).decode()
                if not chunk:
                    break
                buffer += chunk
                if "\n" in buffer:
                    break

            line, *_ = buffer.split("\n", 1)
            data = json.loads(line)

            if data.get("type") == "signup_ok":
                QMessageBox.information(self, "Успех", data.get("content", "OK"))
                self.close()
            else:
                QMessageBox.warning(self, "Ошибка", data.get("content", "Неизвестная ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Сбой", str(e))
        finally:
            sock.close()

