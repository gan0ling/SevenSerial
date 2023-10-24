from collections import defaultdict
from pykka import ActorRegistry

class ActorManager:

    @staticmethod
    def singleton():
        if not hasattr(ActorManager, '_instance'):
            ActorManager._instance = ActorManager()
        return ActorManager._instance

    def __init__(self):
        self.subscribers = defaultdict(set)

    def subscribe(self, topic, subscriber):
        self.subscribers[topic].add(subscriber)

    def unsubscribe(self, topic, subscriber):
        self.subscribers[topic].discard(subscriber)
    
    def stop_all(self):
        ActorRegistry.stop_all(block=False)
        # for topic in self.subscribers:
        #     for subscriber in self.subscribers[topic]:
        #         if hasattr(subscriber, 'stop'):
        #             subscriber.stop()


    def tell(self, topic, message=None, actor_ref=None):
        #发送消息，不等待返回值
        #如果message字典中不包含topic, 则添加topic
        if not message:
            message = {}
        if 'topic' not in message:
            message['topic'] = topic

        for subscriber in self.subscribers[topic]:
            #当actor_ref不为空时，只发送给指定的actor
            if actor_ref and subscriber != actor_ref:
                continue
            subscriber.tell(message)

        # Handle wildcard subscriptions
        for subscribed_topic in self.subscribers:
            if subscribed_topic.endswith('*') and topic.startswith(subscribed_topic[:-1]):
                for subscriber in self.subscribers[subscribed_topic]:
                    if actor_ref and subscriber != actor_ref:
                        continue
                    subscriber.tell(message)
    
    # def ask(self, topic, message, timeout=2, block=True):
    #     #发送消息，等待返回值
    #     #如果block为True，则阻塞等待timeout秒，如果block为False，则立即返回, future对象
    #     if block:
    #         #发送消息
    #         for subscriber in self.subscribers[topic]:
    #             subscriber.ask(topic, message, timeout=timeout)
