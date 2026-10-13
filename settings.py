from enum import Enum

class PositionSide(Enum):
    LONG = "long"
    SHORT = "short"
    

class ExitReason(Enum):
    TAKE_PROFIT = "Meeting Profit Level"
    STOP_LOSS = "Meeting Loss Level"
    MAVG_INVERSE_CROSSOVER = "Inverse-Crossover in average lines"
    MAVG_CROSSOVER = "Crossover in average lines"
    RSI_OVERBOUGHT = "Cross Overbought level"
    RSI_OVERSOLD = "Cross Oversold level"
    BOLLINGER_UPWARD_REVERSION = "Upward Mean Reversion"
    BOLLINGER_DOWNWARD_REVERSION = "Downward Mean Reversion"
    DONCHIAN_MIDDLE_CROSS_DOWN = "Downward Middle Channel Cross"
    DONCHIAN_MIDDLE_CROSS_UP = "Upward Middle Channel Cross"
    MACD_CROSS_UP = "Upward MACD Cross"
    MACD_CROSS_DOWN = "Downward MACD Cross"
    FINAL_PRICE = "Final Price"