from typing import Any
import serial
from pykka import ThreadingActor, Actor, ActorRegistry
import logging
import sys
import queue
from core.manager import TopicManager
from datetime import datetime
import time
from stransi import Ansi, SetColor, SetAttribute
import time


pykka_logger = logging.getLogger("pykka")

class MyThreadActor(ThreadingActor):
    def __init__(self):
        super().__init__()
        self.is_activated = False
        self.topic_manager = TopicManager.singleton()
        #默认订阅topic：/cmd, /class_name/input
        self.topic_manager.subscribe('/cmd', self.actor_ref)
        self.topic_manager.subscribe(f'/{self.__class__.__name__}/input', self.actor_ref)
        self.__topics = {
            'sub': set(['/cmd', f'/{self.__class__.__name__}/input']),
            'pub': set([f'/{self.__class__.__name__}/output'])
        }
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def __get_topics(self):
        return self.__topics
    
    def __set_topics(self, topics):
        #topic 可以重复订阅
        #先取消原来的订阅
        self.__topics['pub'].clear()

        if 'sub' in topics:
            for topic in self.__topics['sub']:
                self.topic_manager.unsubscribe(topic, self.actor_ref)
            self.__topics['sub'].clear()
            for topic in topics['sub']:
                self.topic_manager.subscribe(topic, self.actor_ref)
                self.__topics['sub'].add(topic)
        if 'pub' in topic:
            self.__topics['pub'].clear()
            self.__topics['pub'].update(topics['pub'])
    topics = property(fget=__get_topics, fset=__set_topics)

    def add_sub_topic(self, topic):
        self.__topics['sub'].add(topic)
        self.topic_manager.subscribe(topic, self.actor_ref)
    
    def add_pub_topic(self, topic):
        self.__topics['pub'].add(topic)

    def remove_sub_topic(self, topic):
        self.__topics['sub'].discard(topic)
        self.topic_manager.unsubscribe(topic, self.actor_ref)
    
    def remove_pub_topic(self, topic):
        self.__topics['pub'].discard(topic)

    def data_input_topic(self):
        return f'/{self.__class__.__name__}/input'
    
    def data_output_topic(self):
        return f'/{self.__class__.__name__}/output'

    def tell(self, msg):
        for topic in self.topics['pub']:
            self.topic_manager.tell(topic, msg)


    def activate(self):
        """
            Called at plugin activation. start the actor thread
        """
        if self.is_activated:
            return
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
        if not self.is_activated:
            return
        self.is_activated = False
        self.stop()
    
    def on_input(self, msg):
        raise NotImplementedError
    
    def on_cmd(self, msg):
        raise NotImplementedError
    
    def on_receive(self, message):
        self.logger.debug(f'on_receive {message}')
        if 'topic' not in message:
            return
        topic = message['topic']
        if topic.endswith('/input'):
            return self.on_input(message)
        elif topic == '/cmd':
            return self.on_cmd(message)
        return None


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


