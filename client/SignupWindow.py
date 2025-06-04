import json
import socket
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QMessageBox
from theme import DarkTheme as T  # Цветовая тема оформления

# Адрес сервера
SERVER_HOST = "localhost"
SERVER_PORT = 8080

# Класс SignupWindow — отвечает за окно регистрации нового пользователя.
# Пользователь вводит логин, имя, фамилию и пароль.
# После проверки данных отправляется запрос на сервер, и отображается результат регистрации.
class SignupWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shichat — Регистрация")
        self.resize(300, 220)
        # Применяем тёмную тему к окну
        self.setStyleSheet(f"background:{T.BG}; color:{T.TEXT_MAIN};")

        layout = QVBoxLayout(self)  # Вертикальная компоновка элементов

        # Поле ввода логина
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Имя пользователя (логин)")
        self.name_edit.setStyleSheet(T.qss_input())

        # Поле ввода имени
        self.first_edit = QLineEdit()
        self.first_edit.setPlaceholderText("Имя")
        self.first_edit.setStyleSheet(T.qss_input())

        # Поле ввода фамилии
        self.last_edit = QLineEdit()
        self.last_edit.setPlaceholderText("Фамилия")
        self.last_edit.setStyleSheet(T.qss_input())

        # Поле ввода пароля
        self.pass_edit = QLineEdit()
        self.pass_edit.setPlaceholderText("Пароль")
        self.pass_edit.setEchoMode(QLineEdit.Password)  # Скрываем символы
        self.pass_edit.setStyleSheet(T.qss_input())

        # Кнопка регистрации
        self.signup_btn = QPushButton("Зарегистрироваться")
        self.signup_btn.clicked.connect(self.try_signup)  # Привязка обработчика
        self.signup_btn.setStyleSheet(T.qss_button())

        # Добавляем элементы в layout
        layout.addWidget(self.name_edit)
        layout.addWidget(self.first_edit)
        layout.addWidget(self.last_edit)
        layout.addWidget(self.pass_edit)
        layout.addWidget(self.signup_btn)


    # Выполняет регистрацию нового пользователя.
    # Собирает данные из формы, проверяет обязательные поля,
    # подключается к серверу и отправляет запрос.
    # В зависимости от ответа сервера — показывает результат и закрывает окно.
    def try_signup(self):
        # Считываем и обрезаем пробелы с введённых значений
        username = self.name_edit.text().strip()
        first = self.first_edit.text().strip()
        last = self.last_edit.text().strip()
        password = self.pass_edit.text().strip()

        # Проверка на обязательные поля
        if not username or not first or not password:
            QMessageBox.warning(self, "Ошибка", "Логин, имя и пароль обязательны")
            return

        # Составляем JSON-пакет для регистрации
        pkt = {
            "type": "signup",
            "from": username,
            "password": password,
            "first_name": first,
            "last_name": last,
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

            # Проверка типа ответа
            if data.get("type") == "signup_ok":
                QMessageBox.information(self, "Успех", data.get("content", "OK"))
                self.close()  # Закрываем окно регистрации
            else:
                QMessageBox.warning(self, "Ошибка", data.get("content", "Неизвестная ошибка"))

        except Exception as e:
            # Если что-то пошло не так — показываем ошибку
            QMessageBox.critical(self, "Сбой", str(e))
        finally:
            # Всегда закрываем сокет после использования
            sock.close()
