from circuits import Event

class SegmentData(Event):
    """
        将输入源的数据分段
    """
    def __init__(self, data, ts, mode):
        super(SegmentData, self).__init__(data, ts, mode)

class SetSegmentMode(Event):
    """
        设置分段模式：
            1. 串口 文本模式和Hex模式
    """
    def __init__(self, mode):
        super(SetSegmentMode, self).__init__(mode)

class DisplayData(Event):
    """
        显示数据, 带有颜色信息
    """
    def __init__(self, data, ts, bg_color, fg_color):
        super(DisplayData, self).__init__(data, ts, bg_color, fg_color)
