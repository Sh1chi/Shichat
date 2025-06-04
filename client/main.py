# Импорт стандартных библиотек
import sys

# Импорт основных классов из PyQt5 для запуска GUI-приложения
from PyQt5.QtWidgets import QApplication

# Импорт окна входа в систему
from LoginWindow import LoginWindow


if __name__ == "__main__":
    # QApplication — основной объект приложения PyQt, необходим для запуска интерфейса
    app = QApplication(sys.argv)

    # Создаём и отображаем окно входа
    w = LoginWindow()
    w.show()

    # Запускаем главный цикл обработки событий (окно будет работать, пока не будет закрыто)
    sys.exit(app.exec_())
