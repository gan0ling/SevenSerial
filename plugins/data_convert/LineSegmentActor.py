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
    
    def on_input(self, msg):
        if 'data' in msg and 'ts' in msg:
            self.on_data(msg.get('data'), msg.get('ts'))
    
    def on_cmd(self, msg):
        if 'cmd' in msg:
            cmd = msg.get('cmd')
            if cmd == 'set_mode':
                self._mode = msg.get('mode')
    
    def on_data(self, data, ts):
        if self._mode == "text":
            #文本模式
            for line in data.splitlines(keepends=True):
                #为每行数据增加时间戳
                line = "[" + ts + "] " + line
                self.tell({'data':line, 'ts':ts, 'mode':'text'})

        else :
            #HEX模式,将数据转为hex string
            #每隔50ms分段
            #TODO: 使用component来实现Hex数据的分段
            if self._last_hex_time:
                datetime.now() - self._last_hex_time > 0.05
                self.tell({'data':'\n'+ts, 'ts':ts, 'mode':'hex'})
            data = data.hex()
            self.tell({'data':data, 'ts':ts, 'mode':'hex'})
            self._last_hex_time = datetime.now()
    
