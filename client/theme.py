"""theme.py — централизованные цвета и QSS‑генераторы для тёмной темы Shichat."""

class DarkTheme:
    """Палитра и вспомогательные функции стилей (QSS)."""

    # ---------- палитра ----------
    BG            = "#1F1F1F"   # основной фон
    PANEL         = "#2A2A2E"   # правая панель и входящие «пузыри»
    ACCENT        = "#2481CC"   # фирменный голубой
    ACCENT_HOVER  = "#3099E5"
    ACCENT_SOFT = "#2F2F35"
    FIELD         = "#3A3A3C"   # инпут‑бар
    TEXT_MAIN     = "#E0E0E0"   # основной текст
    TEXT_SUB      = "#A0A0A0"   # таймстемпы, второстепенный текст

    # ---------- QSS‑генераторы ----------
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

    @classmethod
    def qss_header(cls) -> str:
        return (
            f"font-size:16px;padding:8px;"
            f"background:{cls.BG};color:#FFFFFF;"
        )

    @classmethod
    def qss_chat_view(cls) -> str:
        return (
            f"background:{cls.PANEL};"
            f"color:{cls.TEXT_MAIN};padding:8px;border:none;"
        )

    @classmethod
    def qss_input(cls) -> str:
        return (
            f"background:{cls.FIELD};color:#FFFFFF;"
            f"border:none;padding:6px;border-radius:6px;"
        )

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
