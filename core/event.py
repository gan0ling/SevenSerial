from circuits import Event

class SegmentData(Event):
    """
        将输入源的数据分段
    """

class SetSegmentMode(Event):
    """
        设置分段模式：
            1. 串口 文本模式和Hex模式
    """
