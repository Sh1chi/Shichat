import sys
import socket
import json
import threading
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLineEdit
from PyQt5.QtCore import pyqtSignal, pyqtSlot

class Client(QWidget):
    new_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Клиент мессенджера")
        self.resize(400, 300)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(('localhost', 8080))

        self.layout = QVBoxLayout()
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Введите сообщение")

        self.send_btn = QPushButton("Отправить")
        self.send_btn.clicked.connect(self.send_message)

        self.layout.addWidget(self.chat)
        self.layout.addWidget(self.input)
        self.layout.addWidget(self.send_btn)
        self.setLayout(self.layout)

        self.new_message.connect(self.display_message)
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def send_message(self):
        msg = self.input.text().strip()
        if msg:
            data = {"from": "Вы", "content": msg}
            self.sock.sendall((json.dumps(data) + "\n").encode())
            self.chat.append(f'Вы: {msg}')
            self.input.clear()

    def receive_messages(self):
        buffer = ""
        while True:
            try:
                part = self.sock.recv(4096).decode()
                if not part:
                    break
                buffer += part
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    msg = json.loads(line)
                    self.new_message.emit(f'{msg["from"]}: {msg["content"]}')
            except (socket.timeout, ConnectionResetError):
                break

    @pyqtSlot(str)
    def display_message(self, text):
        self.chat.append(text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = Client()
    client.show()
    sys.exit(app.exec_())
