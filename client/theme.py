# theme.py — централизованные цвета и генераторы QSS для тёмной темы интерфейса

# Класс описывает цветовую схему приложения и возвращает строки стилей (QSS)
class DarkTheme:
    # Цветовая палитра
    BG = "#1F1F1F"           # основной фон интерфейса
    PANEL = "#2A2A2E"        # фон правой панели
    ACCENT = "#2481CC"       # исходящие сообщения, кнопки, активные элементы
    ACCENT_HOVER = "#3099E5" # цвет при наведении на кнопки
    ACCENT_SOFT = "#2F2F35"  # входящие сообщения
    FIELD = "#3A3A3C"        # фон поля ввода текста
    TEXT_MAIN = "#E0E0E0"    # основной цвет текста
    TEXT_SUB = "#A0A0A0"     # второстепенный текст (время, подписи)

    # Стиль для списка пользователей (QListWidget)
    @classmethod
    def qss_user_list(cls) -> str:
        return f"""
        QListWidget {{
            background:{cls.BG};
            color:{cls.TEXT_MAIN};
            border:none;
        }}
        QListWidget::item:selected {{
            background:{cls.ACCENT};
            color:#FFFFFF;
        }}
        """


    # Стиль списка с увеличенным шрифтом
    @classmethod
    def qss_user_list_large(cls, *, size: int = 14) -> str:
        return f"""
            QListWidget {{
                font-size:{size}px;
            }}
            """


    # Стиль заголовка окна (название чата)
    @classmethod
    def qss_header(cls) -> str:
        return (
            f"font-size:16px;padding:8px;"
            f"background:{cls.BG};color:#FFFFFF;"
        )


    # Стиль области сообщений (chat_view)
    @classmethod
    def qss_chat_view(cls) -> str:
        return (
            f"background:{cls.PANEL};"
            f"color:{cls.TEXT_MAIN};padding:8px;border:none;"
        )


    # Стиль поля ввода текста
    @classmethod
    def qss_input(cls) -> str:
        return (
            f"background:{cls.FIELD};color:#FFFFFF;"
            f"border:none;padding:6px;border-radius:6px;"
        )

    # Стиль кнопки (синий)
    @classmethod
    def qss_button(cls, *, accent: str | None = None) -> str:
        acc = accent or cls.ACCENT
        return f"""
        QPushButton {{
            background:{acc};
            color:#FFFFFF;
            border:none;
            padding:6px 12px;
            border-radius:6px;
            font-weight:bold;
        }}
        QPushButton:hover {{
            background:{cls.ACCENT_HOVER};
        }}
        """

    # Стиль кнопки (серый)
    @classmethod
    def qss_button_dark(cls, *, accent: str | None = None) -> str:
        acc = accent or cls.ACCENT_SOFT
        return f"""
        QPushButton {{
            background:{acc};
            color:#FFFFFF;
            border:none;
            padding:6px 12px;
            border-radius:6px;
            font-weight:bold;
        }}
        QPushButton:hover {{
            background:{cls.FIELD};
        }}
        """

    @staticmethod
    def qss_sender_label():
        return (
            f"padding:4px 8px; "
            f"font-size:12px; "
            f"font-weight:bold; "
            f"color:#FFFFFF;"
        )