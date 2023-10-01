from circuits import Component, Event, Debugger
from circuits.core.events import started
import PySimpleGUI as sg
import atexit
from threading import current_thread
from signal import SIGINT, SIGTERM, signal as set_signal_handler
from sys import exc_info as _exc_info, stderr

class UIEvent(Event):
    """UiEvent Event"""

class BaseUIComponent(Component):
    def __init__(self, title, layout, debug=False):
        super().__init__()
        sg.theme("DarkAmber")
        self.title = title
        self.layout = layout
        self.window = None
        self.window = sg.Window(self.title, self.layout, resizable=True, use_ttk_buttons=True)
        if debug:
            self += Debugger()

    def uiRun(self):
        self.start(process=False, link=self)
        while True:
            event,values = self.window.read()
            if event == sg.WIN_CLOSED or event == "Exit":
                break
            self.fire(UIEvent(event, values))
        self.window.close()
        self.stop()
        self.join()
        