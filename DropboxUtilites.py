##Creating By Pr1me_StRel0k##

import sys
import os
import json
import webbrowser
from functools import partial

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QListWidget,
    QProgressBar,
    QMessageBox,
    QStackedWidget,
    QCheckBox,
)
from PySide6.QtGui import QFont, QPalette, QColor


import dropbox
from dropbox.oauth import DropboxOAuth2FlowNoRedirect

CONFIG_PATH = "config.json"


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


class AnimatedStackedWidget(QStackedWidget):
    

    def __init__(self, parent=None):
        super().__init__(parent)
        self._anim_duration = 450

    def setCurrentIndex(self, index: int):
        if index == self.currentIndex():
            return
        old_widget = self.currentWidget()
        new_widget = self.widget(index)
        if not old_widget or not new_widget:
            super().setCurrentIndex(index)
            return

        geo = self.geometry()
        new_widget.setGeometry(geo)
        new_widget.show()

        direction = 1 if index > self.currentIndex() else -1
        offset = direction * geo.width()

        anim_old = QPropertyAnimation(old_widget, b"geometry")
        anim_old.setDuration(self._anim_duration)
        anim_old.setStartValue(geo)
        anim_old.setEndValue(QRect(geo.x() - offset, geo.y(), geo.width(), geo.height()))
        anim_old.setEasingCurve(QEasingCurve.InOutCubic)

        anim_new = QPropertyAnimation(new_widget, b"geometry")
        anim_new.setDuration(self._anim_duration)
        anim_new.setStartValue(QRect(geo.x() + offset, geo.y(), geo.width(), geo.height()))
        anim_new.setEndValue(geo)
        anim_new.setEasingCurve(QEasingCurve.InOutCubic)

        from PySide6.QtWidgets import QGraphicsOpacityEffect
        old_op = QGraphicsOpacityEffect()
        new_op = QGraphicsOpacityEffect()
        old_widget.setGraphicsEffect(old_op)
        new_widget.setGraphicsEffect(new_op)

        fade_old = QPropertyAnimation(old_op, b"opacity")
        fade_old.setDuration(self._anim_duration)
        fade_old.setStartValue(1.0)
        fade_old.setEndValue(0.0)

        fade_new = QPropertyAnimation(new_op, b"opacity")
        fade_new.setDuration(self._anim_duration)
        fade_new.setStartValue(0.0)
        fade_new.setEndValue(1.0)

        anim_old.start()
        anim_new.start()
        fade_old.start()
        fade_new.start()

        super().setCurrentIndex(index)


class FancyButton(QPushButton):
    

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(120)
        self._scale_px = 6

    def enterEvent(self, event):
        r = self.geometry()
        self._anim.stop()
        self._anim.setStartValue(r)
        self._anim.setEndValue(QRect(r.x() - self._scale_px//2, r.y() - self._scale_px//2,
                                     r.width() + self._scale_px, r.height() + self._scale_px))
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        r = self.geometry()
        self._anim.stop()
        self._anim.setStartValue(r)
        self._anim.setEndValue(QRect(r.x() + self._scale_px//2, r.y() + self._scale_px//2,
                                     r.width() - self._scale_px, r.height() - self._scale_px))
        self._anim.start()
        super().leaveEvent(event)


class DropboxApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DropboxUtilites")
        self.resize(780, 520)

        self.cfg = load_config()
        self.dbx = None
        self.oauth_result = None

        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QLabel("DropboxUtilites")
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        layout.addWidget(header)

        self.stack = AnimatedStackedWidget()
        layout.addWidget(self.stack)

        self.page_auth = self._build_auth_page()
        self.page_main = self._build_main_page()

        self.stack.addWidget(self.page_auth)
        self.stack.addWidget(self.page_main)

        if self.cfg.get("app_key") and self.cfg.get("app_secret"):
            self._fill_auth_fields()
        else:
            self.stack.setCurrentIndex(0)


    def _build_auth_page(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(8)

        desc = QLabel("Введите App Key и App Secret. "
                      "После авторизации вставьте код.")
        desc.setWordWrap(True)
        v.addWidget(desc)

        self.input_app_key = QLineEdit()
        self.input_app_key.setPlaceholderText("App Key")
        v.addWidget(self.input_app_key)

        self.input_app_secret = QLineEdit()
        self.input_app_secret.setPlaceholderText("App Secret")
        v.addWidget(self.input_app_secret)

        self.checkbox_save = QCheckBox("Сохранить ключи в локальный конфиг")
        self.checkbox_save.setChecked(True)
        v.addWidget(self.checkbox_save)

        row = QHBoxLayout()
        btn_open = FancyButton("Открыть страницу авторизации")
        btn_open.clicked.connect(self._open_auth_url)
        row.addWidget(btn_open)

        btn_gen = FancyButton("Генерировать токен (вставить код)")
        btn_gen.clicked.connect(self._start_oauth_flow)
        row.addWidget(btn_gen)

        v.addLayout(row)

        self.label_auth_url = QLabel("")
        self.label_auth_url.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self.label_auth_url)

        self.input_auth_code = QLineEdit()
        self.input_auth_code.setPlaceholderText("Вставьте код авторизации")
        v.addWidget(self.input_auth_code)

        btn_finish = FancyButton("Завершить авторизацию и войти")
        btn_finish.clicked.connect(self._finish_auth)
        v.addWidget(btn_finish)

        return w

    def _build_main_page(self):
        w = QWidget()
        v = QVBoxLayout(w)

        top_row = QHBoxLayout()
        btn_refresh = FancyButton("Обновить список")
        btn_refresh.clicked.connect(self.refresh_file_list)
        top_row.addWidget(btn_refresh)

        btn_upload = FancyButton("Загрузить файл")
        btn_upload.clicked.connect(self.upload_file_dialog)
        top_row.addWidget(btn_upload)

        btn_download = FancyButton("Скачать выбранный")
        btn_download.clicked.connect(self.download_selected)
        top_row.addWidget(btn_download)

        btn_logout = FancyButton("Выход / Сбросить ключи")
        btn_logout.clicked.connect(self.logout_and_reset)
        top_row.addWidget(btn_logout)

        v.addLayout(top_row)

        self.file_list = QListWidget()
        v.addWidget(self.file_list)

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        v.addWidget(self.progress)

        return w

   
    def _fill_auth_fields(self):
        self.input_app_key.setText(self.cfg.get("app_key", ""))
        self.input_app_secret.setText(self.cfg.get("app_secret", ""))
        self.stack.setCurrentIndex(0)

    def _open_auth_url(self):
        app_key = self.input_app_key.text().strip()
        app_secret = self.input_app_secret.text().strip()
        if not app_key or not app_secret:
            QMessageBox.warning(self, "Ошибка", "Введите App Key и App Secret")
            return
        flow = DropboxOAuth2FlowNoRedirect(app_key, app_secret, token_access_type="offline")
        url = flow.start()
        self.label_auth_url.setText(url)
        webbrowser.open(url)

    def _start_oauth_flow(self):
        self._open_auth_url()
        QMessageBox.information(self, "Дальше",
                                "Открыл браузер. Скопируйте код и вставьте его в поле.")

    def _finish_auth(self):
        app_key = self.input_app_key.text().strip()
        app_secret = self.input_app_secret.text().strip()
        auth_code = self.input_auth_code.text().strip()
        if not (app_key and app_secret and auth_code):
            QMessageBox.warning(self, "Ошибка", "Все поля обязательны")
            return
        try:
            flow = DropboxOAuth2FlowNoRedirect(app_key, app_secret, token_access_type="offline")
            oauth_result = flow.finish(auth_code)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка OAuth", f"Не удалось: {e}")
            return

        try:
            dbx = dropbox.Dropbox(oauth_result.access_token)
            dbx.users_get_current_account()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться: {e}")
            return

        self.dbx = dbx
        self.oauth_result = oauth_result

        if self.checkbox_save.isChecked():
            self.cfg["app_key"] = app_key
            self.cfg["app_secret"] = app_secret
            self.cfg["access_token"] = oauth_result.access_token
            if hasattr(oauth_result, "refresh_token"):
                self.cfg["refresh_token"] = oauth_result.refresh_token
            save_config(self.cfg)

        self.stack.setCurrentIndex(1)
        self.refresh_file_list()

    
    def refresh_file_list(self):
        if not self.dbx:
            if self.cfg.get("access_token"):
                try:
                    self.dbx = dropbox.Dropbox(self.cfg.get("access_token"))
                    self.dbx.users_get_current_account()
                except Exception:
                    QMessageBox.warning(self, "Внимание",
                                        "Сохранённый токен недействителен, повторите авторизацию.")
                    self.stack.setCurrentIndex(0)
                    return
            else:
                QMessageBox.warning(self, "Внимание", "Неавторизовано")
                self.stack.setCurrentIndex(0)
                return

        self.file_list.clear()
        try:
            res = self.dbx.files_list_folder("")
            for entry in res.entries:
                self.file_list.addItem(entry.name)
            self.progress.setValue(100)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def upload_file_dialog(self):
        if not self.dbx:
            QMessageBox.warning(self, "Ошибка", "Сначала авторизуйтесь")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Выберите файл для загрузки")
        if not path:
            return
        self._upload_file(path)

    def _upload_file(self, local_path: str):
        try:
            dest = "/" + os.path.basename(local_path)
            with open(local_path, "rb") as f:
                data = f.read()
            self.progress.setValue(10)
            QApplication.processEvents()
            self.dbx.files_upload(data, dest, mode=dropbox.files.WriteMode.overwrite)
            self.progress.setValue(100)
            QMessageBox.information(self, "Успех", f"Файл загружен: {dest}")
            self.refresh_file_list()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка загрузки", str(e))

    def download_selected(self):
        if not self.dbx:
            QMessageBox.warning(self, "Ошибка", "Сначала авторизуйтесь")
            return
        item = self.file_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Ошибка", "Выберите файл")
            return
        name = item.text()
        local, _ = QFileDialog.getSaveFileName(self, "Сохранить как", name)
        if not local:
            return
        try:
            self.progress.setValue(5)
            QApplication.processEvents()
            metadata, res = self.dbx.files_download(path=f"/{name}")
            with open(local, "wb") as f:
                f.write(res.content)
            self.progress.setValue(100)
            QMessageBox.information(self, "Готово", f"Файл сохранён: {local}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка скачивания", str(e))

    def logout_and_reset(self):
        confirm = QMessageBox.question(self, "Подтвердите", "Удалить ключи и выйти?")
        if confirm != QMessageBox.Yes:
            return
        try:
            if os.path.exists(CONFIG_PATH):
                os.remove(CONFIG_PATH)
        except Exception:
            pass
        self.cfg = {}
        self.dbx = None
        self.oauth_result = None
        QMessageBox.information(self, "Сброшено", "Ключи удалены. Перезапустите приложение.")
        self.stack.setCurrentIndex(0)


def main():
    app = QApplication(sys.argv)

    
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(20, 25, 40))          
    pal.setColor(QPalette.WindowText, QColor(230, 230, 230))   
    pal.setColor(QPalette.Base, QColor(25, 30, 50))            
    pal.setColor(QPalette.AlternateBase, QColor(20, 25, 40))
    pal.setColor(QPalette.ToolTipBase, QColor(250, 250, 250))
    pal.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    pal.setColor(QPalette.Text, QColor(230, 230, 230))
    pal.setColor(QPalette.Button, QColor(35, 40, 60))          
    pal.setColor(QPalette.ButtonText, QColor(220, 50, 50))     
    pal.setColor(QPalette.BrightText, QColor(255, 0, 0))       
    pal.setColor(QPalette.Highlight, QColor(220, 50, 50))      
    pal.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(pal)

    win = DropboxApp()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
