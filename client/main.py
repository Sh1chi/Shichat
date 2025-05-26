# Импорт стандартных библиотек
import sys
import json
import socket
import threading
import time
from datetime import datetime
from collections import defaultdict
from typing import Dict

# Импорт компонентов PyQt5
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (
    QApplication,
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
    QMessageBox,
)

from LoginWindow import LoginWindow


# ------------------------- Точка входа -------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = LoginWindow()
    w.show()
    sys.exit(app.exec_())
