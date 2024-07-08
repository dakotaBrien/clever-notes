from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QMenuBar, QTextEdit, QLabel, QPushButton,
                             QApplication, QToolBar, QMenu, QFontDialog, QColorDialog,
                             QFileDialog, QDialog, QSlider, QHBoxLayout)
from PyQt5.Qt import QPixmap, QTextCursor, QColor, QIcon, QTextOption, Qt, QFont, QTextCharFormat, QSize
from threading import Thread
from openai import APIConnectionError
from openai import OpenAI
import time
import json
import mmap
import sys
import ast
import os


class CleverNotes(QApplication):
    def __init__(self, argv):
        global location
        file_to_open = None
        if os.name == "nt":
            location_list = argv[0].split("\\")
        elif os.name == "posix":
            location_list = argv[0].split("/")
        else:
            location_list = None
        try:
            location = "/".join(location_list[0:len(location_list) - 1])
        except IndexError:
            exit(1)
        try:
            if argv[-1][len(argv[-1])-4:len(argv[-1])] == ".txt":
                file_list = argv[-1].split("\\")
                file_to_open = "/".join(file_list)
        except ValueError or IndexError:
            pass
        super().__init__(argv)
        self.setWindowIcon(QIcon(f"{location}/icons/clever_notes.png"))
        window = Window()
        window.show()
        if file_to_open:
            window.initial_open(file_to_open)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(0, 0, 1200, 800)
        self.path = ""
        self.file_name = None
        if self.path == "":
            self.setWindowTitle("CleverNotes - Untitled")
        else:
            self.file_name = self.path.split("/")[-1][0:len(self.path.split("/")[-1]) - 4]
            self.setWindowTitle(f"CleverNotes - {self.file_name}")
        self.background = QLabel(self)
        self.background_image = f"{location}/backgrounds/TinyFrog.png"
        self.opacity = "0.94"
        self.font = "Segoe Script,12,-1,5,75,0,0,0,0,0,Bold"
        self.spellcheck = "On"
        self.easyformat = "On"
        self.API_KEY = None
        Thread(target=self.get_api_key).start()
        self.text_color_list = "[255, 255, 255]"
        self.misspelled_color_list = "[255, 0, 0]"
        self.updated_data = None
        self.get_data()
        self.font_list = self.font.split(",")
        self.text_color_list = ast.literal_eval(self.text_color_list)
        self.misspelled_color_list = ast.literal_eval(self.misspelled_color_list)
        self.text_color = QColor(self.text_color_list[0], self.text_color_list[1], self.text_color_list[2])
        self.misspelled_color = QColor(self.misspelled_color_list[0], self.misspelled_color_list[1],
                                       self.misspelled_color_list[2])
        self.background.setPixmap(QPixmap(self.background_image))
        self.setWindowOpacity(float(self.opacity))
        self.text = TextEditor(self)
        self.status = self.statusBar()
        self.status.setAutoFillBackground(True)
        container = QWidget(self)
        container.setLayout(QVBoxLayout())
        container.layout().addWidget(self.text)
        container.layout().addWidget(self.status)
        container.layout().setContentsMargins(0, 0, 0, 0)
        container.layout().setSpacing(0)
        self.setCentralWidget(container)
        self.clever_check = QPushButton(self)
        self.clever_check.setFixedSize(100, 100)
        self.clever_check.setIcon(QIcon(f"{location}/icons/clever_notes.png"))
        self.clever_check.setIconSize(QSize(100, 100))
        self.clever_check.setStyleSheet("QPushButton { background-color: transparent; border: 0px }")
        self.clever_check.setHidden(True)
        self.clever_check.clicked.connect(self.show_clever_report)
        self.menu = MenuBar(self)
        self.setMenuBar(self.menu)
        self.toolbar = ToolBar(self)
        self.addToolBar(self.toolbar)
        self.notified_no_connection = False
        self.initial_font()
        self.cancel_close = False
        self.show()

    def show_clever_report(self, report):
        clever_report = InfoBox(self)
        clever_report.setWindowTitle("CleverCheck Report:")
        clever_report.text.setText(report)

    def initial_open(self, file_to_open):
        with open(file_to_open, "r") as file:
            text = file.read()
            cursor = self.text.textCursor()
            cursor.beginEditBlock()
            char_format = QTextCharFormat()
            char_format.setForeground(QColor(self.text_color))
            cursor.mergeCharFormat(char_format)
            cursor.insertText(text)
            cursor.endEditBlock()
            end = cursor.position()
        self.path = file_to_open
        self.file_name = self.path.split("/")[-1][0:len(self.path.split("/")[-1]) - 4]
        self.setWindowTitle(f"CleverNotes - {self.file_name}")
        self.text.initial_spell_check(0, end)
        self.text.document().clearUndoRedoStacks()

    def get_api_key(self):
        with open(file="docs/api_key.txt") as file:
            content = file.read()
            if content == "Save your api key to this file.":
                self.status.showMessage("Attention: No API key found in api_key.txt")
                time.sleep(5)
                self.status.showMessage("")
            else:
                self.API_KEY = content

    def get_data(self):
        try:
            with open(f"{location}/docs/clever_config.txt", "r") as file:
                data = json.loads(file.read())
        except FileNotFoundError:
            data = {"Background": "default", "Font": "default", "Text Color": "default", "Misspelled Color": "default",
                    "Opacity": "default", "SpellCheck": "On", "EasyFormat": "On", "CleverCheck": "On"}
        if data["Background"] == "default":
            pass
        else:
            self.background_image = data["Background"]
        if data["Font"] == "default":
            pass
        else:
            self.font = data["Font"]
        if data["Text Color"] == "default":
            pass
        else:
            self.text_color_list = data["Text Color"]
        if data["Misspelled Color"] == "default":
            pass
        else:
            self.misspelled_color_list = data["Misspelled Color"]
        if data["Opacity"] == "default":
            pass
        else:
            self.opacity = data["Opacity"]
        self.spellcheck = data["SpellCheck"]
        self.easyformat = data["EasyFormat"]
        self.updated_data = data

    def initial_font(self):
        font = QFont(self.font_list[0], int(self.font_list[1]))
        if self.font_list[6] == "1":
            font.setUnderline(True)
        if self.font_list[7] == "1":
            font.setStrikeOut(True)
        try:
            style = self.font_list[10]
            if style == "Bold Italic":
                font.setBold(True)
                font.setItalic(True)
            elif style == "Black Italic":
                font.setBold(True)
                font.setItalic(True)
            elif style == "Black":
                font.setBold(True)
            elif style == "Bold":
                font.setBold(True)
            elif style[-4:len(style)] == "bold":
                font.setBold(True)
            elif style[-11:len(style)] == "bold Italic":
                font.setBold(True)
                font.setItalic(True)
            elif style[-6:len(style)] == "Italic":
                font.setItalic(True)
        except IndexError:
            pass
        self.text.setFont(font)

    def resizeEvent(self, event):
        self.text.resize(self.width(), self.height())
        self.background.resize(self.width(), self.height())
        self.clever_check.move(self.width() - 180, self.height() - 200)

    def call_no_internet(self):
        self.status.showMessage("No Internet Connection detected. "
                                "Please connect to the internet to enjoy full functionality.")
        time.sleep(5)
        self.status.showMessage("")

    def null_summary(self):
        self.status.showMessage("Selection too short to summarize.")
        time.sleep(5)
        self.status.showMessage("")

    def choose_font(self):
        font_dialog = QFontDialog()
        new_font, set_font = font_dialog.getFont()
        if set_font:
            self.text.setFont(new_font)
            self.font = new_font.toString()
            self.updated_data['Font'] = self.font
        else:
            pass

    def choose_text_color(self):
        color_dialog = QColorDialog()
        new_color = color_dialog.getColor()
        if new_color.isValid():
            color_list = [new_color.red(), new_color.green(), new_color.blue()]
            self.text_color_list = color_list
            self.text_color = QColor(color_list[0], color_list[1], color_list[2])
            cursor = self.text.textCursor()
            cursor.beginEditBlock()
            cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
            cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
            text = cursor.selection().toPlainText()
            cursor.removeSelectedText()
            char_format = QTextCharFormat()
            char_format.setForeground(QColor(self.text_color))
            cursor.mergeCharFormat(char_format)
            cursor.insertText(text)
            cursor.endEditBlock()
            end = cursor.position()
            self.updated_data["Text Color"] = str(self.text_color_list)
            self.text.initial_spell_check(0, end)

    def choose_background(self):
        file_dialog = QFileDialog(directory=f"{location}/backgrounds")
        new_background = file_dialog.getOpenFileName(caption="Choose a background image", filter="Images (*.png)")[0]
        if new_background:
            self.background_image = new_background
            self.background.setPixmap(QPixmap(self.background_image))
            self.updated_data["Background"] = self.background_image
        else:
            pass

    def how_to(self):
        info_box = InfoBox(self)
        info_box.setWindowTitle("How-To")
        info_box.file = f"{location}/docs/How-To.txt"
        info_box.display_text()

    def about(self):
        info_box = InfoBox(self)
        info_box.setWindowTitle("About")
        info_box.file = f"{location}/docs/About.txt"
        info_box.display_text()

    def advanced_settings(self):
        AdvancedSettings(self)

    def open_file(self):
        if self.windowTitle()[-1] == "*":
            save_changes = SaveChanges(self)
            save_changes.exec_()
            if not self.cancel_close:
                file_dialog = QFileDialog(directory="/")
                file_to_open = file_dialog.getOpenFileName(caption="Open...", filter="Text (*.txt)")[0]
                if file_to_open:
                    cursor = self.text.textCursor()
                    cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
                    cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
                    cursor.removeSelectedText()
                    with open(file_to_open) as file:
                        text = file.readAll()
                        cursor = self.text.textCursor()
                        cursor.beginEditBlock()
                        cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
                        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
                        cursor.removeSelectedText()
                        char_format = QTextCharFormat()
                        char_format.setForeground(QColor(self.text_color))
                        cursor.mergeCharFormat(char_format)
                        cursor.insertText(text)
                        cursor.endEditBlock()
                        end = cursor.position()
                    self.path = file_to_open
                    self.file_name = self.path.split("/")[-1][0:len(self.path.split("/")[-1]) - 4]
                    self.setWindowTitle(f"CleverNotes - {self.file_name}")
                    self.text.initial_spell_check(0, end)
                    self.text.document().clearUndoRedoStacks()
            else:
                self.cancel_close = False
        else:
            file_dialog = QFileDialog(directory="/")
            file_to_open = file_dialog.getOpenFileName(caption="Open...", filter="Text (*.txt)")[0]
            if file_to_open:
                with open(file_to_open) as file:
                    text = file.read()
                    cursor = self.text.textCursor()
                    cursor.beginEditBlock()
                    cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
                    cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
                    cursor.removeSelectedText()
                    char_format = QTextCharFormat()
                    char_format.setForeground(QColor(self.text_color))
                    cursor.mergeCharFormat(char_format)
                    cursor.insertText(text)
                    cursor.endEditBlock()
                    end = cursor.position()
                    self.path = file_to_open
                    self.file_name = self.path.split("/")[-1][0:len(self.path.split("/")[-1]) - 4]
                    self.setWindowTitle(f"CleverNotes - {self.file_name}")
                    self.text.initial_spell_check(0, end)
                    self.text.document().clearUndoRedoStacks()
            else:
                pass

    def save_as(self):
        save_file = QFileDialog.getSaveFileName(directory="/", caption="Save as...", filter="Text (*.txt)")[0]
        if save_file:
            if save_file[:-4] != ".txt":
                save_file = save_file + ".txt"
            with open(save_file, "w") as file:
                text = self.text.toPlainText()
                file.write(text)
            self.path = save_file
            self.file_name = self.path.split("/")[-1][0:len(self.path.split("/")[-1]) - 4]
            self.setWindowTitle(f"CleverNotes - {self.file_name}")
        else:
            self.cancel_close = True

    def save_file(self):
        if self.path != "":
            with open(self.path, "w") as file:
                text = self.text.toPlainText()
                file.write(text)
            self.setWindowTitle(f"CleverNotes - {self.file_name}")
        else:
            self.save_as()

    def new_file(self):
        if self.windowTitle()[-1] == "*":
            save_changes = SaveChanges(self)
            save_changes.exec_()
            if not self.cancel_close:
                cursor = self.text.textCursor()
                cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
                cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
                self.path = ""
                self.file_name = ""
                self.setWindowTitle("CleverNotes - Untitled")
                self.text.document().clearUndoRedoStacks()
            else:
                self.cancel_close = False
        else:
            cursor = self.text.textCursor()
            cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
            cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            self.path = ""
            self.file_name = ""
            self.setWindowTitle("CleverNotes - Untitled")
            self.text.document().clearUndoRedoStacks()

    def closeEvent(self, event):
        if self.windowTitle()[-1] == "*":
            save_changes = SaveChanges(self)
            save_changes.exec_()
            if not self.cancel_close:
                with open(f"{location}/docs/clever_config.txt", "w") as file:
                    file.write(json.dumps(self.updated_data))
                event.accept()
            else:
                self.cancel_close = False
                event.ignore()
        else:
            with open(f"{location}/docs/clever_config.txt", "w") as file:
                file.write(json.dumps(self.updated_data))
            event.accept()


class TextEditor(QTextEdit):
    def __init__(self, parent):
        super(QTextEdit, self).__init__(parent)
        self.parent = parent
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.viewport().setAutoFillBackground(False)
        if os.name == "nt":
            self.setStyleSheet("QTextEdit {border : 1px solid white}")
        self.setAcceptRichText(False)
        self.setTextColor(self.parent.text_color)
        self.ignored_word_list = []

    def keyPressEvent(self, event):
        self.setTextColor(self.parent.text_color)
        if event.modifiers() & Qt.ControlModifier and event.modifiers() & Qt.ShiftModifier:
            if event.key() == Qt.Key_Z:
                self.redo()
        elif event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_V:
                self.paste()
            if event.key() == Qt.Key_X:
                self.cut()
            if event.key() == Qt.Key_C:
                self.copy()
            if event.key() == Qt.Key_Z:
                self.undo()
        else:
            cursor = self.textCursor()
            cursor_position = cursor.position()
            cursor.beginEditBlock()
            super().keyPressEvent(event)
            if not event.modifiers() & Qt.ControlModifier:
                if event.key() == Qt.Key_Shift:
                    pass
                elif event.key() == Qt.Key_Return:
                    self.easy_format()
                elif event.key() == Qt.Key_Home:
                    self.moveCursor(QTextCursor.StartOfLine, QTextCursor.MoveAnchor)
                    pass
                elif event.key() == Qt.Key_End:
                    self.moveCursor(QTextCursor.EndOfLine, QTextCursor.MoveAnchor)
                    pass
                elif event.key() == Qt.Key_Left or event.key() == Qt.Key_Right:
                    pass
                elif event.key() == Qt.Key_Up or event.key() == Qt.Key_Down:
                    pass
                elif event.key() == Qt.Key_Backspace and cursor_position == 0:
                    self.setTextColor(self.parent.text_color)
                    pass
                else:
                    if self.parent.file_name:
                        self.parent.setWindowTitle(f"CleverNotes - {self.parent.file_name}*")
                    else:
                        self.parent.setWindowTitle("CleverNotes - Untitled*")
                    self.setTextColor(self.parent.text_color)
                    self.spell_check()
            if event.modifiers() & Qt.ShiftModifier:
                if event.key() == Qt.Key_Home:
                    self.moveCursor(QTextCursor.Start, QTextCursor.MoveAnchor)
                    for _ in range(cursor_position):
                        self.moveCursor(QTextCursor.Right, QTextCursor.MoveAnchor)
                    self.moveCursor(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
                elif event.key() == Qt.Key_End:
                    self.moveCursor(QTextCursor.Start, QTextCursor.MoveAnchor)
                    for _ in range(cursor_position):
                        self.moveCursor(QTextCursor.Right, QTextCursor.MoveAnchor)
                    self.moveCursor(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
                else:
                    pass
            cursor.endEditBlock()

    def contextMenuEvent(self, event):
        cursor = self.textCursor()
        menu = QMenu(self)
        undo_action = menu.addAction("Undo")
        undo_action.setShortcut("Ctrl+Z")
        if not self.document().isUndoAvailable():
            undo_action.setDisabled(True)
        undo_action.triggered.connect(self.undo)
        redo_action = menu.addAction("Redo")
        redo_action.setShortcut("Ctrl+Shift+Z")
        if not self.document().isRedoAvailable():
            redo_action.setDisabled(True)
        redo_action.triggered.connect(self.redo)
        menu.addSeparator()
        cut_action = menu.addAction("Cut")
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(self.cut)
        copy_action = menu.addAction("Copy")
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy)
        paste_action = menu.addAction("Paste")
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.paste)
        menu.addSeparator()
        select_all_action = menu.addAction("Select All")
        select_all_action.triggered.connect(self.selectAll)
        summarize_action = menu.addAction("Summarize")
        summarize_action.setShortcut("Ctrl+D")
        summarize_action.triggered.connect(self.summarize)
        menu.addSeparator()
        cursor.select(QTextCursor.WordUnderCursor)
        word = cursor.selection().toPlainText()
        with open(rf"{location}/docs/words.txt", "rb", 0) as word_file:
            search = mmap.mmap(word_file.fileno(), 0, access=mmap.ACCESS_READ)
            if search.find(bytes(word.lower(), encoding="utf-8")) != -1:
                pass
            else:
                add_word_action = menu.addAction("Add to WordList")
                add_word_action.triggered.connect(self.add_word)
                ignore_word_action = menu.addAction("Ignore")
                ignore_word_action.triggered.connect(self.ignore_word)
        menu.exec_(self.mapToGlobal(event.pos()))

    def paste(self):
        self.setTextColor(QColor(self.parent.text_color))
        cursor = self.textCursor()
        cursor.beginEditBlock()
        start = cursor.position()
        super().paste()
        end = cursor.position()
        self.initial_spell_check(start, end)
        cursor.endEditBlock()

    def initial_spell_check(self, start, end):
        if self.parent.spellcheck == "On":
            cursor = self.textCursor()
            cursor.beginEditBlock()
            cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
            for _ in range(start):
                cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor)
            while cursor.position() < end:
                cursor.movePosition(QTextCursor.StartOfWord, QTextCursor.MoveAnchor)
                cursor.movePosition(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)
                word = cursor.selection().toPlainText()
                if word.isnumeric():
                    cursor.removeSelectedText()
                    char_format = QTextCharFormat()
                    char_format.setForeground(QColor(self.parent.text_color))
                    cursor.mergeCharFormat(char_format)
                    cursor.insertText(word)
                else:
                    with open(rf"{location}/docs/words.txt", "rb", 0) as word_file:
                        search = mmap.mmap(word_file.fileno(), 0, access=mmap.ACCESS_READ)
                        if search.find(bytes(word.lower(), encoding="utf-8")) != -1 or word in self.ignored_word_list:
                            cursor.removeSelectedText()
                            char_format = QTextCharFormat()
                            char_format.setForeground(QColor(self.parent.text_color))
                            cursor.mergeCharFormat(char_format)
                            cursor.insertText(word)
                        else:
                            cursor.removeSelectedText()
                            char_format = QTextCharFormat()
                            char_format.setForeground(QColor(self.parent.misspelled_color))
                            cursor.mergeCharFormat(char_format)
                            cursor.insertText(word)
                            self.setTextColor(QColor(self.parent.text_color))
                cursor.movePosition(QTextCursor.NextWord, QTextCursor.MoveAnchor)
            cursor.endEditBlock()
        else:
            pass

    def add_word(self):
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        word = cursor.selection().toPlainText()
        with open(f"{location}/docs/words.txt", "a") as add_file:
            add_file.write("\n" + word.lower())
        self.initial_spell_check(0, len(self.toPlainText()))

    def ignore_word(self):
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        word = cursor.selection().toPlainText()
        self.ignored_word_list.append(word)
        self.initial_spell_check(0, len(self.toPlainText()))

    def summarize(self):
        cursor = self.textCursor()
        text = cursor.selection().toPlainText()
        if len(text) < 500:
            null_summary = Thread(target=self.parent.null_summary)
            null_summary.start()
        else:
            if self.parent.API_KEY is None:
                pass
            else:
                try:
                    prompt = f"Summarize the following text: {text}"
                    client = OpenAI(api_key=self.parent.API_KEY)
                    stream = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        stream=True,
                    )
                    response = []
                    for chunk in stream:
                        if chunk.choices[0].delta.content is not None:
                            response.append(chunk.choices[0].delta.content)
                    summary = "".join(response)
                    cursor.beginEditBlock()
                    cursor.removeSelectedText()
                    self.setTextColor(QColor(self.parent.text_color))
                    self.insertPlainText(summary)
                    cursor.endEditBlock()
                except APIConnectionError:
                    if not self.parent.notified_no_connection:
                        Thread(target=self.parent.call_no_internet).start()
                        self.parent.notified_no_connection = True

    def spell_check(self):
        if self.parent.spellcheck == "On":
            cursor = self.textCursor()
            position = cursor.position()
            cursor.beginEditBlock()
            cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
            if cursor.selection().toPlainText() == " ":
                cursor.movePosition(QTextCursor.StartOfWord, QTextCursor.MoveAnchor)
                cursor.movePosition(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)
                word = cursor.selection().toPlainText()
                if word.isnumeric():
                    cursor.removeSelectedText()
                    char_format = QTextCharFormat()
                    char_format.setForeground(QColor(self.parent.text_color))
                    cursor.mergeCharFormat(char_format)
                    cursor.insertText(word)
                else:
                    with open(rf"{location}/docs/words.txt", "rb", 0) as word_file:
                        search = mmap.mmap(word_file.fileno(), 0, access=mmap.ACCESS_READ)
                        if search.find(bytes(word.lower(), encoding="utf-8")) != -1 or word in self.ignored_word_list:
                            cursor.removeSelectedText()
                            char_format = QTextCharFormat()
                            char_format.setForeground(QColor(self.parent.text_color))
                            cursor.mergeCharFormat(char_format)
                            cursor.insertText(word)
                        else:
                            cursor.removeSelectedText()
                            char_format = QTextCharFormat()
                            char_format.setForeground(QColor(self.parent.misspelled_color))
                            cursor.mergeCharFormat(char_format)
                            cursor.insertText(word)
                cursor.movePosition(QTextCursor.NextWord, QTextCursor.MoveAnchor)
                cursor.movePosition(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)
                word = cursor.selection().toPlainText()
                if word.isnumeric():
                    cursor.removeSelectedText()
                    char_format = QTextCharFormat()
                    char_format.setForeground(QColor(self.parent.text_color))
                    cursor.mergeCharFormat(char_format)
                    cursor.insertText(word)
                else:
                    with open(rf"{location}/docs/words.txt", "rb", 0) as word_file:
                        search = mmap.mmap(word_file.fileno(), 0, access=mmap.ACCESS_READ)
                        if search.find(bytes(word.lower(), encoding="utf-8")) != -1 or word in self.ignored_word_list:
                            cursor.removeSelectedText()
                            char_format = QTextCharFormat()
                            char_format.setForeground(QColor(self.parent.text_color))
                            cursor.mergeCharFormat(char_format)
                            cursor.insertText(word)
                        else:
                            cursor.removeSelectedText()
                            char_format = QTextCharFormat()
                            char_format.setForeground(QColor(self.parent.misspelled_color))
                            cursor.mergeCharFormat(char_format)
                            cursor.insertText(word)
            else:
                cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor)
                cursor.movePosition(QTextCursor.StartOfWord, QTextCursor.MoveAnchor)
                cursor.movePosition(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)
                word = cursor.selection().toPlainText()
                if word.isnumeric():
                    cursor.removeSelectedText()
                    char_format = QTextCharFormat()
                    char_format.setForeground(QColor(self.parent.text_color))
                    cursor.mergeCharFormat(char_format)
                    cursor.insertText(word)
                else:
                    with open(rf"{location}/docs/words.txt", "rb", 0) as word_file:
                        search = mmap.mmap(word_file.fileno(), 0, access=mmap.ACCESS_READ)
                        if search.find(bytes(word.lower(), encoding="utf-8")) != -1 or word in self.ignored_word_list:
                            cursor.removeSelectedText()
                            char_format = QTextCharFormat()
                            char_format.setForeground(QColor(self.parent.text_color))
                            cursor.mergeCharFormat(char_format)
                            cursor.insertText(word)
                        else:
                            cursor.removeSelectedText()
                            char_format = QTextCharFormat()
                            char_format.setForeground(QColor(self.parent.misspelled_color))
                            cursor.mergeCharFormat(char_format)
                            cursor.insertText(word)
            self.moveCursor(QTextCursor.Start, QTextCursor.MoveAnchor)
            for _ in range(position):
                self.moveCursor(QTextCursor.Right, QTextCursor.MoveAnchor)
            cursor.endEditBlock()
        else:
            pass

    def easy_format(self):
        selection = None
        if self.parent.easyformat == "On":
            cursor = self.textCursor()
            cursor.beginEditBlock()
            cursor.movePosition(QTextCursor.Up, QTextCursor.MoveAnchor)
            cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.MoveAnchor)
            position = cursor.position()
            cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
            line_text = cursor.selection().toPlainText()
            if line_text == "":
                pass
            elif line_text[0:3] == "---":
                cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.MoveAnchor)
                cursor.insertText("                -  ")
                for _ in range(3):
                    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
                cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
            elif line_text[0:3] == "...":
                num_uncertain = True
                while num_uncertain:
                    cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.MoveAnchor)
                    cursor.movePosition(QTextCursor.Up, QTextCursor.MoveAnchor)
                    cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
                    selection = cursor.selection().toPlainText()
                    cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.MoveAnchor)
                    if cursor.position() == 0:
                        break
                    if selection == "":
                        continue
                    if selection[0:11] == "           ":
                        continue
                    else:
                        num_uncertain = False
                cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
                for _ in range(position):
                    cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor)
                try:
                    try:
                        try:
                            num = str(int(selection[10:13]) + 1)
                        except ValueError:
                            num = str(int(selection[10:12]) + 1)
                    except ValueError:
                        num = str(int(selection[10:11]) + 1)
                except ValueError:
                    cursor.insertText("          1.  ")
                else:
                    if selection[0:10] == "          ":
                        cursor.insertText(f"          {num}.  ")
                    else:
                        cursor.insertText("          1.  ")
                finally:
                    for _ in range(3):
                        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
                    cursor.removeSelectedText()
                    cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
            elif line_text[0:2] == "..":
                num_uncertain = True
                while num_uncertain:
                    cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.MoveAnchor)
                    cursor.movePosition(QTextCursor.Up, QTextCursor.MoveAnchor)
                    cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
                    selection = cursor.selection().toPlainText()
                    cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.MoveAnchor)
                    if cursor.position() == 0:
                        break
                    if selection == "":
                        continue
                    if selection[0:7] == "       ":
                        continue
                    else:
                        num_uncertain = False
                cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
                for _ in range(position):
                    cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor)
                try:
                    try:
                        try:
                            num = str(int(selection[6:9]) + 1)
                        except ValueError:
                            num = str(int(selection[6:8]) + 1)
                    except ValueError:
                        num = str(int(selection[6:7]) + 1)
                except ValueError:
                    cursor.insertText("      1.  ")
                else:
                    if selection[0:6] == "      ":
                        cursor.insertText(f"      {num}.  ")
                    else:
                        cursor.insertText("      1.  ")
                finally:
                    for _ in range(2):
                        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
                    cursor.removeSelectedText()
                    cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
            elif line_text[0:2] == "--":
                cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.MoveAnchor)
                cursor.insertText("          •  ")
                for _ in range(2):
                    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
                cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
            elif line_text[0:1] == "-":
                cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.MoveAnchor)
                cursor.insertText("      -  ")
                cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
                cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
            elif line_text[0:1] == ".":
                num_uncertain = True
                while num_uncertain:
                    cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.MoveAnchor)
                    cursor.movePosition(QTextCursor.Up, QTextCursor.MoveAnchor)
                    cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
                    selection = cursor.selection().toPlainText()
                    cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.MoveAnchor)
                    if cursor.position() == 0:
                        break
                    if selection == "":
                        continue
                    elif selection[0] == " ":
                        continue
                    else:
                        num_uncertain = False
                cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
                for _ in range(position):
                    cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor)
                try:
                    try:
                        try:
                            num = str(int(selection[0:3]) + 1)
                        except ValueError:
                            num = str(int(selection[0:2]) + 1)
                    except ValueError:
                        num = str(int(selection[0]) + 1)
                except ValueError:
                    cursor.insertText("1.  ")
                else:
                    cursor.insertText(f"{num}.  ")
                finally:
                    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
                    cursor.removeSelectedText()
                    cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
            else:
                pass
            cursor.endEditBlock()
        else:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.Up, QTextCursor.MoveAnchor)
            cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)

    def clever_check(self):
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.Up, QTextCursor.MoveAnchor)
        cursor.movePosition(QTextCursor.Start, QTextCursor.MoveAnchor)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        text = cursor.selection().toPlainText()
        if self.parent.API_KEY is None:
            pass
        else:
            try:
                prompt = (
                    f"Determine whether the information in the following notes is true or false. If everything is true"
                    f", say 'Everything looks good!' and if anything is false, say 'Here's what's false:' "
                    f"and explain which parts are false and why. Additionally, if anything is misleading, say "
                    f"'Here's what's misleading:' and explain which parts are misleading and why. Notes: {text}")
                client = OpenAI(api_key=self.parent.API_KEY)
                stream = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                )
                response = []
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        response.append(chunk.choices[0].delta.content)
                report = "".join(response)
                self.parent.show_clever_report(report)
            except APIConnectionError:
                if not self.parent.notified_no_connection:
                    Thread(target=self.parent.call_no_internet).start()
                    self.parent.notified_no_connection = True


class MenuBar(QMenuBar):
    def __init__(self, parent):
        super(QMenuBar, self).__init__(parent)
        self.parent = parent
        file_menu = self.addMenu("&File")
        new_action = file_menu.addAction(QIcon(f"{location}/icons/new_file.png"), "&New")
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.parent.new_file)
        open_action = file_menu.addAction(QIcon(f"{location}/icons/open_file.png"), "&Open...")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.parent.open_file)
        save_action = file_menu.addAction(QIcon(f"{location}/icons/save_file.png"), "&Save")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.parent.save_file)
        save_as_action = file_menu.addAction(QIcon(f"{location}/icons/save_file.png"), "&Save As...")
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.parent.save_as)
        file_menu.addSeparator()
        exit_action = file_menu.addAction(QIcon(f"{location}/icons/exit.png"), "&Exit")
        exit_action.setShortcut("Escape")
        exit_action.triggered.connect(self.parent.close)
        edit_menu = self.addMenu("&Edit")
        cut_action = edit_menu.addAction(QIcon(f"{location}/icons/cut.png"), "&Cut")
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(self.parent.text.cut)
        copy_action = edit_menu.addAction(QIcon(f"{location}/icons/copy.png"), "&Copy")
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.parent.text.copy)
        paste_action = edit_menu.addAction(QIcon(f"{location}/icons/paste.png"), "&Paste")
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.parent.text.paste)
        edit_menu.addSeparator()
        summarize_action = edit_menu.addAction(QIcon(f"{location}/icons/summarize.png"), "&Summarize...")
        summarize_action.setShortcut("Ctrl+D")
        summarize_action.triggered.connect(self.parent.text.summarize)
        preferences_menu = self.addMenu("&Preferences")
        font_action = preferences_menu.addAction(QIcon(f"{location}/icons/font.png"), "&Font...")
        font_action.triggered.connect(self.parent.choose_font)
        text_color_action = preferences_menu.addAction(QIcon(f"{location}/icons/text_color.png"), "&Text Color...")
        text_color_action.triggered.connect(self.parent.choose_text_color)
        background_action = preferences_menu.addAction(QIcon(f"{location}/icons/background_image.png"),
                                                       "&Background...")
        background_action.triggered.connect(self.parent.choose_background)
        preferences_menu.addSeparator()
        settings_action = preferences_menu.addAction(QIcon(f"{location}/icons/settings.png"), "&Advanced Settings...")
        settings_action.triggered.connect(self.parent.advanced_settings)
        help_menu = self.addMenu("&Help")
        how_to_action = help_menu.addAction(QIcon(f"{location}/icons/how_to.png"), "&How-to...")
        how_to_action.triggered.connect(self.parent.how_to)
        about_action = help_menu.addAction(QIcon(f"{location}/icons/about.png"), "&About...")
        about_action.triggered.connect(self.parent.about)
        help_menu.addSeparator()


class ToolBar(QToolBar):
    def __init__(self, parent):
        super(QToolBar, self).__init__(parent)
        self.parent = parent
        self.setAutoFillBackground(True)
        self.setMovable(False)
        new_button = self.addAction(QIcon(f"{location}/icons/new_file.png"), "New")
        new_button.triggered.connect(self.parent.new_file)
        open_button = self.addAction(QIcon(f"{location}/icons/open_file.png"), "Open")
        open_button.triggered.connect(self.parent.open_file)
        save_button = self.addAction(QIcon(f"{location}/icons/save_file.png"), "Save")
        save_button.triggered.connect(self.parent.save_file)
        undo_button = self.addAction(QIcon(f"{location}/icons/undo.png"), "Undo")
        undo_button.triggered.connect(self.parent.text.undo)
        redo_button = self.addAction(QIcon(f"{location}/icons/redo.png"), "Redo")
        redo_button.triggered.connect(self.parent.text.redo)
        summarize_button = self.addAction(QIcon(f"{location}/icons/summarize.png"), "Summarize")
        summarize_button.triggered.connect(self.parent.text.summarize)
        clever_button = self.addAction(QIcon(f"{location}/icons/clever_notes.png"), "CleverCheck")
        clever_button.triggered.connect(self.parent.text.clever_check)


class InfoBox(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.file = ""
        self.setFixedSize(600, 500)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setStyleSheet("QTextEdit {border : 1px solid white; color: black}")
        self.setWindowOpacity(float(self.parent.opacity))
        self.background = QLabel(self)
        self.background_image = f"{location}/backgrounds/CleverNotes.png"
        self.background.setPixmap(QPixmap(self.background_image))
        self.text = QTextEdit(self)
        self.text.viewport().setAutoFillBackground(False)
        self.text.setReadOnly(True)
        self.text.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.text.setFont(QFont("Segoe UI"))
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.text)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.text.setFontPointSize(10)
        self.show()

    def resizeEvent(self, event):
        self.text.resize(self.width(), self.height())
        self.background.resize(self.width(), self.height())

    def display_text(self):
        with open(self.file, "r") as file:
            info_text = file.read()
            self.text.setText(info_text)


class AdvancedSettings(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setFixedSize(360, 250)
        self.setWindowTitle("Advanced Settings")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.spellcheck_on_off = QLabel(f"SpellCheck: {self.parent.spellcheck}", self)
        if self.parent.spellcheck == "On":
            self.change_spellcheck = "Turn Off"
        elif self.parent.spellcheck == "Off":
            self.change_spellcheck = "Turn On"
        self.change_spellcheck_button = QPushButton(f"{self.change_spellcheck}", self)
        self.change_spellcheck_button.clicked.connect(self.change_spellcheck_attribute)
        self.easyformat_on_off = QLabel(f"EasyFormat: {self.parent.easyformat}", self)
        if self.parent.easyformat == "On":
            self.change_easyformat = "Turn Off"
        elif self.parent.easyformat == "Off":
            self.change_easyformat = "Turn On"
        self.change_easyformat_button = QPushButton(f"{self.change_easyformat}", self)
        self.change_easyformat_button.clicked.connect(self.change_easyformat_attribute)
        self.misspelled_label = QLabel("Misspelled Text:", self)
        self.misspelled_button = QPushButton("Choose Color", self)
        self.misspelled_button.clicked.connect(self.change_misspelled_color)
        self.opacity_label = QLabel("Opacity:", self)
        self.opacity_slider = QSlider(Qt.Horizontal, self)
        self.opacity_slider.setFixedSize(200, 30)
        self.opacity_slider.setMinimum(20)
        self.opacity_position = int(self.parent.opacity[2:4])
        self.opacity_slider.setSliderPosition(self.opacity_position)
        self.opacity_slider.valueChanged[int].connect(self.change_opacity)
        spell_h_layout = QHBoxLayout()
        spell_h_layout.addStretch()
        spell_h_layout.addWidget(self.spellcheck_on_off)
        spell_h_layout.addStretch()
        spell_h_layout.addWidget(self.change_spellcheck_button)
        spell_h_layout.addStretch()
        spell_container = QWidget(self)
        spell_container.setLayout(spell_h_layout)
        easy_h_layout = QHBoxLayout()
        easy_h_layout.addStretch()
        easy_h_layout.addWidget(self.easyformat_on_off)
        easy_h_layout.addStretch()
        easy_h_layout.addWidget(self.change_easyformat_button)
        easy_h_layout.addStretch()
        easy_container = QWidget(self)
        easy_container.setLayout(easy_h_layout)
        color_h_layout = QHBoxLayout()
        color_h_layout.addStretch()
        color_h_layout.addWidget(self.misspelled_label)
        color_h_layout.addStretch()
        color_h_layout.addWidget(self.misspelled_button)
        color_h_layout.addStretch()
        color_container = QWidget(self)
        color_container.setLayout(color_h_layout)
        opacity_h_layout = QHBoxLayout()
        opacity_h_layout.addStretch()
        opacity_h_layout.addWidget(self.opacity_label)
        opacity_h_layout.addStretch()
        opacity_h_layout.addWidget(self.opacity_slider)
        opacity_h_layout.addStretch()
        opacity_container = QWidget(self)
        opacity_container.setLayout(opacity_h_layout)
        v_layout = QVBoxLayout()
        v_layout.addWidget(spell_container)
        v_layout.addWidget(easy_container)
        v_layout.addWidget(color_container)
        v_layout.addWidget(opacity_container)
        self.setLayout(v_layout)
        self.show()

    def change_opacity(self):
        value = self.opacity_slider.value()
        new_opacity = "0." + str(value)
        self.parent.opacity = new_opacity
        self.parent.setWindowOpacity(float(self.parent.opacity))
        self.parent.updated_data["Opacity"] = new_opacity

    def change_misspelled_color(self):
        cursor = self.parent.text.textCursor()
        cursor.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
        end = cursor.position()
        color_dialog = QColorDialog()
        new_color = color_dialog.getColor()
        if new_color.isValid():
            color_list = [new_color.red(), new_color.green(), new_color.blue()]
            self.parent.misspelled_color_list = color_list
            self.parent.misspelled_color = QColor(color_list[0], color_list[1], color_list[2])
            self.parent.updated_data["Misspelled Color"] = str(self.parent.misspelled_color_list)
            self.parent.text.initial_spell_check(0, end)
            self.parent.activateWindow()

    def change_spellcheck_attribute(self):
        if self.change_spellcheck == "Turn Off":
            self.change_spellcheck = "Turn On"
            self.parent.spellcheck = "Off"
            self.change_spellcheck_button.setText(f"{self.change_spellcheck}")
            self.spellcheck_on_off.setText(f"SpellCheck: {self.parent.spellcheck}")
            self.parent.updated_data["SpellCheck"] = "Off"
        else:
            self.parent.spellcheck = "On"
            self.change_spellcheck = "Turn Off"
            self.change_spellcheck_button.setText(f"{self.change_spellcheck}")
            self.spellcheck_on_off.setText(f"SpellCheck: {self.parent.spellcheck}")
            self.parent.updated_data["SpellCheck"] = "On"

    def change_easyformat_attribute(self):
        if self.change_easyformat == "Turn Off":
            self.change_easyformat = "Turn On"
            self.parent.easyformat = "Off"
            self.change_easyformat_button.setText(f"{self.change_easyformat}")
            self.easyformat_on_off.setText(f"EasyFormat: {self.parent.easyformat}")
            self.parent.updated_data["EasyFormat"] = "Off"
        else:
            self.parent.easyformat = "On"
            self.change_easyformat = "Turn Off"
            self.change_easyformat_button.setText(f"{self.change_easyformat}")
            self.easyformat_on_off.setText(f"EasyFormat: {self.parent.easyformat}")
            self.parent.updated_data["EasyFormat"] = "On"


class SaveChanges(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Save Changes?")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setFixedSize(425, 140)
        self.save_label = QLabel("Save unsaved changes?", self)
        self.yes_button = QPushButton("Yes", self)
        self.yes_button.clicked.connect(self.yes_save_changes)
        self.no_button = QPushButton("No", self)
        self.no_button.clicked.connect(self.no_save_changes)
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self.cancel_close)
        self.save_option_chosen = False
        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addWidget(self.yes_button)
        h_layout.setAlignment(self.yes_button, Qt.AlignLeft)
        h_layout.addWidget(self.no_button)
        h_layout.setAlignment(self.no_button, Qt.AlignCenter)
        h_layout.addWidget(self.cancel_button)
        h_layout.setAlignment(self.cancel_button, Qt.AlignRight)
        h_layout.addStretch()
        button_container = QWidget(self)
        button_container.setLayout(h_layout)
        v_layout = QVBoxLayout()
        v_layout.addWidget(self.save_label)
        v_layout.setAlignment(self.save_label, Qt.AlignCenter)
        v_layout.addWidget(button_container)
        v_layout.setAlignment(button_container, Qt.AlignCenter)
        self.setLayout(v_layout)
        self.show()

    def closeEvent(self, event):
        self.close()

    def close(self):
        if self.save_option_chosen:
            super().close()
        elif not self.save_option_chosen:
            self.parent.cancel_close = True
            print("true")
            super().close()

    def cancel_close(self):
        self.parent.cancel_close = True
        self.close()

    def yes_save_changes(self):
        self.save_option_chosen = True
        self.close()
        if self.parent.path == "" and self.parent.windowTitle()[-1] == "*":
            self.parent.save_as()
        else:
            self.parent.save_file()

    def no_save_changes(self):
        self.save_option_chosen = True
        self.close()


location = None
app = CleverNotes(sys.argv)
sys.exit(app.exec_())
