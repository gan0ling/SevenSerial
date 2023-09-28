from circuits import Component, Event
from circuits.core.events import started
import PySimpleGUI as sg
import atexit
from threading import current_thread
from signal import SIGINT, SIGTERM, signal as set_signal_handler
from sys import exc_info as _exc_info, stderr

class UIEvent(Event):
    """UiEvent Event"""

class BaseUIComponent(Component):
    def __init__(self, title, layout):
        super().__init__()
        sg.theme("DarkAmber")
        self.title = title
        self.layout = layout
        self.window = None
        self.window = sg.Window(self.title, self.layout, resizable=True, use_ttk_buttons=True)
    
    def run(self, socket=None):
        """
        在原有Manager的run方法上，增加pySimpleGUI的事件循环
        """

        atexit.register(self.stop)

        if current_thread().name == "MainThread":
            try:
                set_signal_handler(SIGINT, self._signal_handler)
                set_signal_handler(SIGTERM, self._signal_handler)
            except ValueError:
                # Ignore if we can't install signal handlers
                pass

        self._running = True
        self.root._executing_thread = current_thread()

        # Setup Communications Bridge

        if socket is not None:
            from circuits.core.bridge import Bridge
            Bridge(socket, channel=socket.channel).register(self)

        self.fire(started(self))

        try:
            while True:
                # event,values = self.window.read(timeout=50)
                event,values = self.window.read()
                if event == sg.WIN_CLOSED or event == "Exit":
                    break
                if event != "__TIMEOUT__":
                    self.fire(UIEvent(event, values))
                # if not self.running or not len(self._queue):
                    # break
                self.tick(0.05)
            self.window.close()
            # Fading out, handle remaining work from stop event
            for _ in range(3):
                self.tick(0.1)
        except Exception as exc:
            stderr.write("Unhandled ERROR: {}\n".format(exc))
            stderr.write(format_exc())
        finally:
            try:
                self.tick(0.5)
            except Exception:
                pass

        self.root._executing_thread = None
        self.__thread = None
        self.__process = None
