from collections import defaultdict
from pykka import ActorRegistry, ActorRef
import logging
from yapsy.ConfigurablePluginManager import ConfigurablePluginManager

class TopicManager:

    @staticmethod
    def singleton():
        if not hasattr(TopicManager, '_instance'):
            TopicManager._instance = TopicManager()
        return TopicManager._instance

    def __init__(self):
        self.subscribers = defaultdict(set)
        self.connections = defaultdict(set)
        self.logger = logging.getLogger('TopicManager')

    def subscribe(self, topic, subscriber):
        self.subscribers[topic].add(subscriber)

    def unsubscribe(self, topic, subscriber):
        self.subscribers[topic].discard(subscriber)
    
    def stop_all(self):
        ActorRegistry.stop_all(block=False)

    def connect(self, output, input):
        """
        将output actor的/output topic 连接到 input actor的input topic上
        output topic中的数据，会转发到input topic中
        """
        output_topic = None
        if hasattr(output, 'data_output_topic'):
            output_topic = output.data_output_topic()
        elif type(output) == str:
            output_topic = output
        else:
            raise TypeError('output must be MyThreadActor or str')
        
        input_topic = set()
        if hasattr(input, 'data_input_topic'):
            input_topic.add(input.data_input_topic())
        elif type(input) == str:
            input_topic.add(input)
        elif type(input) == list:
            for i in input:
                if hasattr(i, 'data_input_topic'):
                    input_topic.add(i.data_input_topic())
                elif type(i) == str:
                    input_topic.add(i)
                else:
                    raise TypeError('input must be MyThreadActor or str')
        else:
            raise TypeError('input must be MyThreadActor or str or list')
        
        self.connections[output_topic].update(input_topic)


    def tell(self, topic, message=None, actor_ref=None):
        #发送消息，不等待返回值
        #如果message字典中不包含topic, 则添加topic
        self.logger.debug(f'topic: {topic}, message: {message}, actor_ref: {actor_ref}')
        if not message:
            message = {}
        if 'topic' not in message:
            message['topic'] = topic
        
        self._tell(topic, message, actor_ref)

        if topic in self.connections:
            for input_topic in self.connections[topic]:
                #修改message中的topic
                message['topic'] = input_topic
                self._tell(input_topic, message, actor_ref)

    def _tell(self, topic, message=None, actor_ref=None):
        # 检查actor_ref是否为ActorRef对象,或者list
        if actor_ref:
            if isinstance(actor_ref, list):
                for subscriber in actor_ref:
                    #如果actor_ref订阅了该消息，则发送
                    if self.subscribers[topic].__contains__(subscriber):
                        subscriber.tell(message)
            elif isinstance(actor_ref, ActorRef):
                if self.subscribers[topic].__contains__(actor_ref):
                    actor_ref.tell(message)
            return
        for subscriber in self.subscribers[topic]:
            subscriber.tell(message)

        # Handle wildcard subscriptions
        for subscribed_topic in self.subscribers:
            if subscribed_topic.endswith('*') and topic.startswith(subscribed_topic[:-1]):
                for subscriber in self.subscribers[subscribed_topic]:
                    subscriber.tell(message)
    
    # def ask(self, topic, message, timeout=2, block=True):
    #     #发送消息，等待返回值
    #     #如果block为True，则阻塞等待timeout秒，如果block为False，则立即返回, future对象
    #     if block:
    #         #发送消息
    #         for subscriber in self.subscribers[topic]:
    #             subscriber.ask(topic, message, timeout=timeout)

class MyConfigurablePluginManager(ConfigurablePluginManager):
    def getPluginByName(self, name, category='Default'):
        """
        Get a plugin by its name and category
        """
        return self._component.getPluginByName(name, category)
    
    def getPluinByCategory(self, category):
        return self._component.getPluginsOfCategory(category)
    
    def getActorRefByName(self, name, category='Default'):
        plugin= self.getPluginByName(name, category)
        if plugin:
            return plugin.plugin_object.actor_ref
        else:
            return None
    
    def getActorByName(self, name, category='Default'):
        plugin= self.getPluginByName(name, category)
        if plugin:
            return plugin.plugin_object
        else:
            return None
