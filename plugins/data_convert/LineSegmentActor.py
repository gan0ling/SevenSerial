from core.plugintype import ConvertActor
from datetime import datetime


class LineSegmentActor(ConvertActor):
    """
    将数据分段：
    1. 文本模式下，按照行来分段，并且增加时间戳
    2. Hex模式下， 按照时间来分段, 默认50ms
    Output Topic：
        /data/segment_data
    """
    def __init__(self, mode="text"):
        super().__init__()
        self._mode = mode
        self._last_hex_time = None
        #订阅消息
        self.topic_manager.subscribe('/cmd', self.actor_ref)
        self.topic_manager.subscribe('/SerialSourceActor/output', self.actor_ref)
    
    def on_receive(self, message): 
        topic = message.get('topic')
        if topic == '/SerialSourceActor/output':
            self.on_data(message.get('data'), message.get('ts'))
        elif topic == '/cmd':
            cmd = message.get('cmd')
            if cmd == 'set_mode':
                self._mode = message.get('mode')
    
    def on_data(self, data, ts):
        if self._mode == "text":
            #文本模式
            for line in data.splitlines(keepends=True):
                #为每行数据增加时间戳
                line = "[" + ts + "] " + line
                self.topic_manager.tell('/LineSegmentActor/output', {'data':line, 'ts':ts, 'mode':'text'})

        else :
            #HEX模式,将数据转为hex string
            #每隔50ms分段
            #TODO: 使用component来实现Hex数据的分段
            if self._last_hex_time:
                datetime.now() - self._last_hex_time > 0.05
                self.topic_manager.tell('/LineSegmentActor/output', {'data':'\n'+ts, 'ts':ts, 'mode':'hex'})
            data = data.hex()
            self.topic_manager.tell('/LineSegmentActor/output', {'data':data, 'ts':ts, 'mode':'hex'})
            self._last_hex_time = datetime.now()
    
