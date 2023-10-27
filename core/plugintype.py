from typing import Any
import serial
from pykka import ThreadingActor, Actor, ActorRegistry
import logging
import sys
import queue
from core.manager import ActorManager
from datetime import datetime
import time
from stransi import Ansi, SetColor, SetAttribute
import time


pykka_logger = logging.getLogger("pykka")

class MyThreadActor(ThreadingActor):
    def __init__(self):
        super().__init__()
        self.is_activated = False
        self.topic_manager = ActorManager.singleton()

    def activate(self):
        """
            Called at plugin activation. start the actor thread
        """
        self.is_activated = True
        assert self.actor_ref is not None, (
            "Actor.__init__() have not been called. "
            "Did you forget to call super() in your override?"
        )
        ActorRegistry.register(self.actor_ref)
        pykka_logger.debug(f"Starting {self}")
        self._start_actor_loop()  # noqa: SLF001

    def deactivate(self):
        """
            Called when the plugin is disabled.
        """
        self.is_activated = False
        self.stop()

class LoopActor(MyThreadActor):
    def __init__(self, timeout=0.05, block=True):
        super().__init__()
        self.timeout = timeout
        self.block = block
    
    def on_poll(self) -> None:
        """
        Called on every loop iteration.
        """
        raise NotImplementedError

    def _actor_loop_running(self) -> None:
        while not self.actor_stopped.is_set():
            if not self.block:
                self.on_poll()
            try:
                envelope = self.actor_inbox.get(timeout=self.timeout, block=self.block)
            except queue.Empty:
                continue
            try:
                response = self._handle_receive(envelope.message)
                if envelope.reply_to is not None:
                    envelope.reply_to.set(response)
            except Exception:
                if envelope.reply_to is not None:
                    pykka_logger.info(
                        f"Exception returned from {self} to caller:",
                        exc_info=sys.exc_info(),
                    )
                    envelope.reply_to.set_exception()
                else:
                    self._handle_failure(*sys.exc_info())
                    try:
                        self.on_failure(*sys.exc_info())
                    except Exception:
                        self._handle_failure(*sys.exc_info())
            except BaseException:
                exception_value = sys.exc_info()[1]
                pykka_logger.debug(f"{exception_value!r} in {self}. Stopping all actors.")
                self._stop()
                ActorRegistry.stop_all()

class SourceActor(LoopActor):
    def __init__(self, timeout=0.1, block=True):
        """
            block: 读取数据时，是否blcok
            timeout: 当block为False时，timeout有效
        """
        super().__init__(timeout=timeout, block=block)

    def activate(self):
        super().activate() 
    
    def deactivate(self):
        super().deactivate() 

class FilterActor(MyThreadActor):
    def __init__(self):
        super().__init__()

    def activate(self):
        super().activate() 
    
    def deactivate(self):
        super().deactivate() 

class ConvertActor(MyThreadActor):
    def __init__(self):
        super().__init__()

    def activate(self):
        super().activate() 
    
    def deactivate(self):
        super().deactivate() 

class HighlightActor(MyThreadActor):
    def __init__(self):
        super().__init__()

    def activate(self):
        super().activate() 
    
    def deactivate(self):
        super().deactivate() 


class StorageActor(MyThreadActor):
    def __init__(self):
        super().__init__()

    def activate(self):
        super().activate() 
    
    def deactivate(self):
        super().deactivate() 





