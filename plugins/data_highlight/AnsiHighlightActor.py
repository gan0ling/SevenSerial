from core.plugintype import HighlightActor
import customtkinter

class AnsiHighlightActor(HighlightActor):
    def __init__(self, words=None):
        super().__init__()


class AnsiSearchHighlightActor(HighlightActor, customtkinter.CTk):
    def __init__(self, words=None):
        super().__init__()
        #setup ui

