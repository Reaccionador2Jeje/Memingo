"""Desktop shell for Gold & Diamond Browser.

Memingo owns the product configuration and app identity in app.mgo.
This Python module is the thin Qt host that embeds Qt WebEngine.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus

from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QLineEdit, QMainWindow, QMessageBox, QTabWidget,
    QToolBar, QVBoxLayout, QWidget,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from memingo.interpreter import execute

ROOT = Path(__file__).resolve().parent.parent
MGO_ENTRY = ROOT / "app.mgo"
CONFIG_FILE = ROOT / "browser-config.json"


def load_memingo_config() -> dict:
    """Execute the Memingo app definition and load its generated config."""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
    source = MGO_ENTRY.read_text(encoding="utf-8")
    # The .mgo program writes browser-config.json using Memingo's own file API.
    list(execute(source, project_directory=ROOT))
    if not CONFIG_FILE.exists():
        raise RuntimeError("Memingo did not generate browser-config.json")
    data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("Memingo browser configuration must be an object")
    return data


class BrowserWindow(QMainWindow):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.setWindowTitle(f"{config.get('name', 'Gold & Diamond Browser')} — {config.get('version', '0.1.0')}")
        self.resize(1280, 820)
        self.setMinimumSize(760, 520)
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #10131b; color: #f4f0e6; }
            QToolBar { background: #171c28; border: 0; spacing: 7px; padding: 9px; }
            QToolButton { color: #f2c75c; background: #222a39; border: 1px solid #394255;
                          border-radius: 9px; padding: 7px 11px; }
            QToolButton:hover { background: #30394b; }
            QLineEdit { background: #0d1119; color: #fff7df; border: 1px solid #b88a2e;
                        border-radius: 12px; padding: 10px 14px; selection-background-color: #b88a2e; }
            QTabWidget::pane { border: 0; }
            QTabBar::tab { background: #171c28; color: #b9c0ce; padding: 10px 18px;
                           border-top-left-radius: 8px; border-top-right-radius: 8px; }
            QTabBar::tab:selected { background: #252c3b; color: #f4c95d; }
            QTabBar::close-button { image: none; }
        """)

        toolbar = QToolBar("Navigation")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        back = QAction("←", self)
        back.setToolTip("Back")
        back.triggered.connect(lambda: self.current_view().back())
        toolbar.addAction(back)

        forward = QAction("→", self)
        forward.setToolTip("Forward")
        forward.triggered.connect(lambda: self.current_view().forward())
        toolbar.addAction(forward)

        reload_action = QAction("↻", self)
        reload_action.setToolTip("Reload")
        reload_action.triggered.connect(lambda: self.current_view().reload())
        toolbar.addAction(reload_action)

        home_action = QAction("⌂", self)
        home_action.setToolTip("Home")
        home_action.triggered.connect(self.go_home)
        toolbar.addAction(home_action)

        self.address = QLineEdit()
        self.address.setPlaceholderText("Search or enter a website address")
        self.address.returnPressed.connect(self.navigate)
        toolbar.addWidget(self.address)

        new_tab = QAction("+", self)
        new_tab.setToolTip("New tab")
        new_tab.triggered.connect(lambda: self.add_tab(self.config.get("home", "https://duckduckgo.com")))
        toolbar.addAction(new_tab)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.sync_address)
        self.setCentralWidget(self.tabs)

        self.add_tab(self.config.get("home", "https://duckduckgo.com"))
        self._install_shortcuts()

    def current_view(self) -> QWebEngineView:
        return self.tabs.currentWidget()

    def add_tab(self, url: str | None = None):
        view = QWebEngineView()
        index = self.tabs.addTab(view, "New tab")
        self.tabs.setCurrentIndex(index)
        view.urlChanged.connect(lambda value, browser=view: self.update_address(value, browser))
        view.titleChanged.connect(lambda title, browser=view: self.update_title(title, browser))
        view.load(QUrl(url or self.config.get("home", "https://duckduckgo.com")))
        return view

    def close_tab(self, index: int):
        if self.tabs.count() <= 1:
            self.current_view().load(QUrl(self.config.get("home", "https://duckduckgo.com")))
            return
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        widget.deleteLater()

    def resolve_address(self, text: str) -> str:
        """Ask the Memingo app logic to classify an address or search query."""
        value = text.strip()
        if not value:
            return self.config.get("home", "https://duckduckgo.com")

        previous = os.environ.get("GDB_ADDRESS")
        os.environ["GDB_ADDRESS"] = value
        try:
            source = MGO_ENTRY.read_text(encoding="utf-8")
            list(execute(source, project_directory=ROOT))
            resolved_file = ROOT / "resolved-address.txt"
            if not resolved_file.exists():
                raise RuntimeError("Memingo did not resolve the address")
            result = resolved_file.read_text(encoding="utf-8").strip()
        finally:
            if previous is None:
                os.environ.pop("GDB_ADDRESS", None)
            else:
                os.environ["GDB_ADDRESS"] = previous

        if result.startswith("SEARCH:"):
            query = result[len("SEARCH:"):]
            return self.config.get("search_engine", "https://duckduckgo.com/?q=") + quote_plus(query)
        return result

    def navigate(self):
        target = self.resolve_address(self.address.text())
        self.current_view().load(QUrl(target))

    def go_home(self):
        self.current_view().load(QUrl(self.config.get("home", "https://duckduckgo.com")))

    def update_address(self, url: QUrl, view: QWebEngineView):
        if view is self.current_view():
            self.address.setText(url.toString())

    def update_title(self, title: str, view: QWebEngineView):
        index = self.tabs.indexOf(view)
        if index >= 0:
            self.tabs.setTabText(index, (title or "New tab")[:24])

    def sync_address(self, _index: int):
        view = self.current_view()
        if view:
            self.address.setText(view.url().toString())

    def _install_shortcuts(self):
        new_tab = QAction(self)
        new_tab.setShortcut(QKeySequence("Ctrl+T"))
        new_tab.triggered.connect(lambda: self.add_tab())
        self.addAction(new_tab)

        close_tab = QAction(self)
        close_tab.setShortcut(QKeySequence("Ctrl+W"))
        close_tab.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        self.addAction(close_tab)

        focus_address = QAction(self)
        focus_address.setShortcut(QKeySequence("Ctrl+L"))
        focus_address.triggered.connect(self.address.setFocus)
        self.addAction(focus_address)

        reload_page = QAction(self)
        reload_page.setShortcut(QKeySequence("Ctrl+R"))
        reload_page.triggered.connect(lambda: self.current_view().reload())
        self.addAction(reload_page)


def main() -> int:
    try:
        config = load_memingo_config()
    except Exception as error:
        print(f"Gold & Diamond Browser: Memingo startup failed: {error}", file=sys.stderr)
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName(config.get("name", "Gold & Diamond Browser"))
    app.setOrganizationName("AtDev")
    window = BrowserWindow(config)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
