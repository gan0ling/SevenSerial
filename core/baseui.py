from circuits import Component, Event, Debugger
from circuits.core.events import started
from nicegui import ui

class UIEvent(Event):
    """UiEvent Event"""

class BaseUIComponent(Component):
    def __init__(self, title, debug=False):
        print("BaseUIComponent init")
        super().__init__()
        self.title = title
        if debug:
            self += Debugger()

    def uiRun(self):
        self.start(process=False, link=self)
        ui.run(native=True)
        self.stop()
        self.join()
        