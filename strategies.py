import pandas as pd
import matplotlib.pyplot as plt
from binance.client import Client
from settings import *
from dataclasses import dataclass
from enum import Enum


@dataclass
class Position:

    side: PositionSide
    entry_price: float
    size: float
    margin: float
    entry_commission: float

    def unrealized_pnl(self, price: float) -> float:
        if self.side == PositionSide.LONG:
            return self.size * (price - self.entry_price)

        return self.size * (self.entry_price - price)

    def gross_pnl(self, exit_price: float) -> float:
        if self.side == PositionSide.LONG:
            return self.size * exit_price - self.margin

        return self.size * (self.entry_price - exit_price)


@dataclass
class TradeResult:

    exit_price: float
    gross_pnl: float
    entry_commission: float
    exit_commission: float
    net_pnl: float
    trade_return: float
    account_impact: float
    reason: str


class ConnectBinance:

    TIMEFRAMES = {
        "1s": Client.KLINE_INTERVAL_1SECOND,
    
        "1min": Client.KLINE_INTERVAL_1MINUTE,
        "3min": Client.KLINE_INTERVAL_3MINUTE,
        "5min": Client.KLINE_INTERVAL_5MINUTE,
        "15min": Client.KLINE_INTERVAL_15MINUTE,
        "30min": Client.KLINE_INTERVAL_30MINUTE,
    
        "1h": Client.KLINE_INTERVAL_1HOUR,
        "2h": Client.KLINE_INTERVAL_2HOUR,
        "4h": Client.KLINE_INTERVAL_4HOUR,
        "6h": Client.KLINE_INTERVAL_6HOUR,
        "8h": Client.KLINE_INTERVAL_8HOUR,
    
        "1d": Client.KLINE_INTERVAL_1DAY,
        "3d": Client.KLINE_INTERVAL_3DAY,
    
        "1w": Client.KLINE_INTERVAL_1WEEK,
        "1m": Client.KLINE_INTERVAL_1MONTH,
    }
    
    def __init__(self, currency:str="BTCUSDT", start_time:str="2024-01-01", stop_time:str="2025-01-01", timeframe="1h"):
        print("🔄️ Downloading Data from Binance ...")
        self._ready = False
        self._currency = currency
        self._start_time = start_time
        self._stop_time = stop_time
        self.data = None
        self._client = Client()
        if self._check_timeframe(timeframe):
            self._ready = True
            self._get_data()
            self._modify_columns()
            print("✅ Data downloaded from Binance successfully.")
        else:
            print("❌ ERROR: Data was not downloaded.")

    def _get_data(self):
        if not self._ready:
            return
        KLINES = self._client.get_historical_klines(self._currency, interval=self._timeframe, start_str=self._start_time, end_str=self._stop_time)
        self.data = pd.DataFrame(KLINES, columns=["Open Time",
                                           "Open", "High", "Low", "Close",
                                           "Volume",
                                           "Close Time",
                                           "Quote Asset Volume",
                                           "Number of Trades",
                                           "Taker Buy Base Asset Volume",
                                           "Taker Buy Quote Asset Volume",
                                           "Ignore"
                                     ])
        
    def _modify_columns(self):
        if not self._ready:
            return
            
        self.data["Date"] = pd.to_datetime(self.data["Open Time"], unit="ms")
        self.data.index = pd.to_datetime(self.data["Open Time"], unit="ms")
        self.data.index.name = "Date"
        for column in ("Open", "High", "Low", "Close", "Volume"):
            self.data[column] = self.data[column].astype(float)

    def _check_timeframe(self, timeframe):
        if timeframe not in ConnectBinance.TIMEFRAMES:
            print("❌ ERROR: timeframe is not supported")
            return False

        self._timeframe = ConnectBinance.TIMEFRAMES[timeframe]
        return True

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["_client"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)


class Strategy:

    _PRICE_TYPE = ("Open", "Close", "High", "Low")

    _TRADE = {
        "position-type": None,
        "entry-date": None,
        "entry-price": 0.0,
        "exit-date": None,
        "exit-price": 0.0,
        "reason": "",
        "trade-return": 0.0,
        "account-impact": 0.0,
    }

    def __init__(self, info:ConnectBinance):
        self._data = info.data.copy()
        self._trade_df = None
        self._ready = info._ready
        self._trades_info = []
        self._statistics = dict()
        self.position = None
        self._price = None

    def report(self):
        if not self._ready:
            print("❌ ERROR: Data is not ready")
            return
            
        print(f"===================  Final Backtest Result of {self._STRATEGY_NAME} Strategy ===================")
        print(f"❇️ Initial Capital: {self._statistics['initial-capital']:.2f} USD")
        print(f"❇️ Final Capital: {self._statistics['capital']:.2f} USD")
        print(f"❇️ Profit-Loss: {self._statistics['capital'] - self._statistics['initial-capital']:.2f} USD")
        print(f"❇️ Total Return: {self._statistics['total-return']:.2f} %")
        print(f"❇️ Total Trades: {self._statistics['total-trade']} (Winning: {self._statistics['winning-trade']} | Losing: {self._statistics['losing-trade']})")
        print(f"❇️ Win-Rate: {self._statistics['win-rate']:.2f} %")
    
        # plot capital Trend
        plt.figure(figsize=(14, 7))
        plt.plot(self._trade_df.index, self._trade_df["Equity"], label="Equity Curve", color="green", linewidth=2)
        plt.axhline(y=self._statistics["initial-capital"], color="red", linestyle="--", label="Initial Capital")
    
        plt.title(f"Equity Curve of {self._STRATEGY_NAME} Strategy", fontsize="14")
        plt.xlabel("Date", fontsize=12)
        plt.ylabel("Equity (USD)", fontsize=12)
        plt.legend(loc="best")
        plt.grid(True, alpha=0.5)
    
        plt.tight_layout()
        plt.show()

    def _run_backtest(self, margin_portion: float, tp: float, sl: float, commission_rate: float):
        if len(self._trade_df) < 2:
            print("❌ ERROR: Not enough data for trading")
            return
        
        prices = self._trade_df[self._price].to_numpy()
        dates = self._trade_df.index

        for i in range(1, len(self._trade_df)):

            current_price = prices[i]
            date = dates[i]

            if self.in_position:
                exit_reason = self._get_exit_signal(i, current_price, tp, sl)

                if exit_reason:
                    result = self._close_position(current_price, exit_reason, commission_rate)
                    self._record_trade(result, date)

            else:
                signal = self._get_entry_signal(i)
                if signal:
                    self.position = self._open_position(signal, current_price, margin_portion, commission_rate)
                    self._record_entry(current_price, date, signal)

            self._update_equity(current_price)

        self._trade_df["Equity"] = self._equity_curve

        # Force-close an open position at the final price
        if self.in_position:

            final_date = dates[-1]
            final_price = prices[-1]

            result = self._close_position(final_price, ExitReason.FINAL_PRICE, commission_rate)

            self._record_trade(result, final_date)

            self._trade_df.loc[self._trade_df.index[-1], "Equity"] = self._statistics["capital"]

        self._finalize_backtest()
    
    def _open_position(self, side: PositionSide, price: float, margin_portion: float, commission_rate: float):
        margin = self._statistics["capital"] * margin_portion
        commission = margin * commission_rate
        size = margin / price

        self._statistics["capital"] -= margin + commission
        self._statistics["commission-paid"] += commission

        return Position(
            side=side,
            entry_price=price,
            size=size,
            margin=margin,
            entry_commission=commission
        )    

    def _close_position(self, exit_price: float, exit_reason: ExitReason, commission_rate: float):

        if not self.in_position:
            raise RuntimeError("Cannot close a position when no position is open")


        position = self.position
        exit_value = position.size * exit_price
        exit_commission = exit_value * commission_rate
        gross_pnl = position.gross_pnl(exit_price)
        net_pnl = gross_pnl - position.entry_commission - exit_commission


        if position.side == PositionSide.LONG:
            new_margin = exit_value - exit_commission

        else:
            new_margin = position.margin + gross_pnl - exit_commission

        self._statistics["commission-paid"] += exit_commission
        self._statistics["capital"] += new_margin

        trade_return = (net_pnl / position.margin) * 100
        account_impact = (net_pnl / self._statistics["initial-capital"]) * 100

        if trade_return > 0:
            self._statistics["winning-trade"] += 1
        elif trade_return < 0:
            self._statistics["losing-trade"] += 1
        else:
            self._statistics["breakeven-trade"] += 1

        self.position = None

        return TradeResult(
            exit_price=exit_price,
            gross_pnl=gross_pnl,
            entry_commission=position.entry_commission,
            exit_commission=exit_commission,
            net_pnl=net_pnl,
            trade_return=trade_return,
            account_impact=account_impact,
            reason=exit_reason
        )

    def _record_entry(self, entry_price: float, date, side: PositionSide):
        self._statistics["total-trade"] += 1
        self._current_trade["entry-date"] = date
        self._current_trade["entry-price"] = entry_price
        self._current_trade["position-type"] = side.value

    def _record_trade(self, result: TradeResult, date):
        self._current_trade["exit-date"] = date
        self._current_trade["exit-price"] = result.exit_price
        self._current_trade["reason"] = result.reason.value
        self._current_trade["trade-return"] = result.trade_return
        self._current_trade["account-impact"] = result.account_impact

        self._trades_info.append(self._current_trade.copy())
        self._current_trade = self._TRADE.copy()

    def _update_equity(self, current_price: float):
        if self.in_position:
            unrealized_pnl = self.position.unrealized_pnl(current_price)
            current_equity = self._statistics["capital"] + self.position.margin + unrealized_pnl
        
        else:
            current_equity = self._statistics["capital"]
        
        self._equity_curve.append(current_equity)

    def _reset_backtest(self):
        self._statistics = {
            "initial-capital": 0,
            "capital": 0,
            "tp": 0.0,
            "sl": 0.0,
            "commission-rate": 0.0,
            "commission-paid": 0.0,
            "win-rate": 0.0,
            "total-trade": 0,
            "winning-trade": 0,
            "losing-trade": 0,
            "breakeven-trade": 0,
            "total-return": 0.0,
        }

        self._equity_curve = []
        self._trades_info = []
        self._current_trade = self._TRADE.copy()
        self.position = None

    def _init_backtest(self, initial_capital: float, tp: float, sl: float, commission_rate: float) -> bool:

        if not self._ready:
            print("❌ ERROR: Data is not ready")
            return False

        self._reset_backtest()

        self._statistics["initial-capital"] = initial_capital
        self._statistics["capital"] = initial_capital
        self._statistics["tp"] = tp
        self._statistics["sl"] = sl
        self._statistics["commission-rate"] = commission_rate

        self._equity_curve.append(initial_capital)

        return True

    def _finalize_backtest(self):
        total_trades = (self._statistics["winning-trade"] + self._statistics["losing-trade"] + self._statistics["breakeven-trade"])
        initial_capital = self._statistics["initial-capital"]
        self._statistics["total-return"] = ((self._statistics["capital"] - initial_capital) / initial_capital) * 100 if initial_capital > 0 else 0
        self._statistics["win-rate"] = (self._statistics["winning-trade"] / total_trades) * 100 if total_trades > 0 else 0

    @property
    def trades_info(self):
        trades = pd.DataFrame(self._trades_info)
        return trades

    @property
    def statistics(self):
        return self._statistics
    
    @property
    def in_position(self):
        return self.position is not None

    @staticmethod
    def check_inputs(initial_capital, margin_portion, tp, sl, commission_rate):
        if not 0 < margin_portion <= 1:
            print("❌ ERROR: margin_portion must be between 0 and 1")
            return False

        if initial_capital <= 0:
            print("❌ ERROR: initial_capital must be greater than Zero")
            return False

        if not 0 < tp <= 1:
            print("❌ ERROR: tp must be between 0 and 1")
            return False

        if not 0 < sl <= 1:
            print("❌ ERROR: sl must be between 0 and 1")
            return False

        if not 0 < commission_rate < 1:
            print("❌ ERROR: commission_rate must be between 0 and 1")
            return False

        return True


class MovingAverage(Strategy):

    _STRATEGY_NAME = "Simple Moving Average"

    def __init__(self, info:ConnectBinance):
        super().__init__(info)
        self._sma = self.__init_sma()
        
    def trade(self, price:str, windows:tuple[int, int], margin_portion:float=0.2, initial_capital:int=1000, tp:float=0.05, sl:float=0.02, commission_rate:float=0.001):
        
        print("✨ Start Trading ....")

        if not self.check_inputs(initial_capital, margin_portion, tp, sl, commission_rate):
            return
        
        if not self.__init_backtest(initial_capital, price, windows, tp, sl, commission_rate):
            return

        self._run_backtest(margin_portion, tp, sl, commission_rate)
        
        print("✅ Trading Finished Successfully.")

    def add_sma(self, sma_list:dict):

        if not isinstance(sma_list, dict):
            return

        if not self._ready:
            return

        for price, window_list in sma_list.items():
            if price not in self._PRICE_TYPE:
                print("❌ ERROR: Unsupported price type: Something")
                return
            
            for window in window_list:
                try:
                    w = int(window)
                    if w <= 0:
                        print("❌ ERROR: Window must be greater than Zero")
                        return
                    
                    if f"SMA-{price}-{w}" in self._data.columns:
                        continue

                    self._data[f"SMA-{price}-{w}"] = MovingAverage.__calculate_sma(self._data[price], w)
                    self._sma[price].append(w)
                    self._sma[price].sort()

                except (TypeError, ValueError):
                    continue

    def _get_entry_signal(self, i):

        short_window = f"SMA-{self._price}-{self._windows[0]}"
        long_window = f"SMA-{self._price}-{self._windows[1]}"

        old_sma_short = self._trade_df[short_window].iloc[i-1]
        new_sma_short = self._trade_df[short_window].iloc[i]
        old_sma_long = self._trade_df[long_window].iloc[i-1]
        new_sma_long = self._trade_df[long_window].iloc[i]

        if old_sma_short <= old_sma_long and new_sma_short > new_sma_long:
            return PositionSide.LONG

        if old_sma_short >= old_sma_long and new_sma_short < new_sma_long:
            return PositionSide.SHORT

        return None

    def _get_exit_signal(self, i, current_price, tp, sl):

        position = self.position

        short_window = f"SMA-{self._price}-{self._windows[0]}"
        long_window = f"SMA-{self._price}-{self._windows[1]}"

        old_sma_short = self._trade_df[short_window].iloc[i-1]
        new_sma_short = self._trade_df[short_window].iloc[i]
        old_sma_long = self._trade_df[long_window].iloc[i-1]
        new_sma_long = self._trade_df[long_window].iloc[i]

        if position.side == PositionSide.LONG:

            if current_price >= position.entry_price * (1 + tp):
                return ExitReason.TAKE_PROFIT

            if current_price <= position.entry_price * (1 - sl):
                return ExitReason.STOP_LOSS

            if old_sma_short >= old_sma_long and new_sma_short < new_sma_long:
                return ExitReason.MAVG_INVERSE_CROSSOVER

        else:

            if current_price <= position.entry_price * (1 - tp):
                return ExitReason.TAKE_PROFIT

            if current_price >= position.entry_price * (1 + sl):
                return ExitReason.STOP_LOSS

            if old_sma_short <= old_sma_long and new_sma_short > new_sma_long:
                return ExitReason.MAVG_CROSSOVER

        return None   

    def __init_backtest(self, initial_capital, price, windows, tp, sl, commission_rate):

        if not self._ready:
            print("❌ ERROR: Data is not ready")
            return False

        if not self.__test_crossover(price, windows):
            return False

        if not self._init_backtest(initial_capital, tp, sl, commission_rate):
            return False

        short_window, long_window = sorted(windows)
        sma_short = f"SMA-{price}-{short_window}"
        sma_long = f"SMA-{price}-{long_window}"

        self._trade_df = self._data.dropna(subset=[sma_short, sma_long]).copy()

        self._price = price
        self._windows = sorted(windows)

        self._statistics["crossover"] = f"{price} {short_window}-{long_window}"

        return True
        
    def __test_crossover(self, price:str, windows:tuple[int, int]):
        if price not in self._PRICE_TYPE:
            print("❌ ERROR: prediction failed. crossover-type must be of Low, High, Open or Close")
            return False 

        if not isinstance(windows, tuple):
            print("❌ ERROR: windows must be a tuple")
            return False

        if len(windows) != 2:
            print("❌ ERROR: prediction failed. crossover must have 2 elements")
            return False

        short_window, long_window = sorted(windows)
        short_column = f"SMA-{price}-{short_window}"
        long_column = f"SMA-{price}-{long_window}"

        if short_column not in self._data.columns:
            print(f"❌ ERROR: {short_column} does not exist")
            return False

        if long_column not in self._data.columns:
            print(f"❌ ERROR: {long_column} does not exist")
            return False

        if short_window <= 0 or long_window <= 0:
            print("❌ ERROR: SMA must be greater than Zero")
            return False

        if short_window == long_window:
            print("❌ ERROR: SMA windows must be different")
            return False

        return True

    def __init_sma(self):
        return {"Low": [], "High": [], "Open": [], "Close": []}

    @property
    def sma(self):
        return self._sma
                    
    @staticmethod
    def __calculate_sma(price, window):
        return price.rolling(window=window).mean()


class BollingerBand(Strategy):

    _STRATEGY_NAME = "Bollinger Band"

    def __init__(self, info:ConnectBinance):
        super().__init__(info)
            
    def trade(self, price:str="Close", margin_portion:float=0.2, window:int=20, num_std_dev:float=2, initial_capital:int=1000, tp:float=0.05, sl:float=0.02, commission_rate:float=0.001):
        
        print("✨ Start Trading ....")
        
        if not self.check_inputs(initial_capital, margin_portion, tp, sl, commission_rate):
            return

        if not self.__init_backtest(initial_capital, price, window, num_std_dev, tp, sl, commission_rate):
            return

        self._run_backtest(margin_portion, tp, sl, commission_rate)

        print("✅ Trading Finished Successfully.")

    def add_bands(self, price:str="Close", window:int=20, num_std_dev:float=2):

        if not isinstance(window, int) or window <= 0:
            print("❌ ERROR: window must be a positive integer")
            return False

        if num_std_dev <= 0:
            print("❌ ERROR: num_std_dev must be greater than Zero")
            return False

        if self._ready:
            if price in self._PRICE_TYPE:
                sma = self._data[price].rolling(window=window).mean()
                rolling_std = self._data[price].rolling(window=window).std()
            
                upper_band = sma + (num_std_dev * rolling_std)
                lower_band = sma - (num_std_dev * rolling_std)
    
                self._data[f"SMA-{price}-{window}"] = sma
                self._data[f"Uband-{price}{window}-Dev{num_std_dev}"] = upper_band
                self._data[f"Lband-{price}{window}-Dev{num_std_dev}"] = lower_band
                return True

            print("❌ ERROR: price must be of Close, Open, High or Low")

        return False
        
    def _get_entry_signal(self, i):

        current_price = self._trade_df.iloc[i][self._price]

        lband_column = f"Lband-{self._price}{self._window}-Dev{self._num_std_dev}"
        uband_column = f"Uband-{self._price}{self._window}-Dev{self._num_std_dev}"

        current_lband = self._trade_df.iloc[i][lband_column]
        current_uband = self._trade_df.iloc[i][uband_column]

        if current_price < current_lband:
            return PositionSide.LONG

        if current_price > current_uband:
            return PositionSide.SHORT

        return None

    def _get_exit_signal(self, i, current_price, tp, sl):

        position = self.position

        sma_column = f"SMA-{self._price}-{self._window}"
        current_sma = self._trade_df.iloc[i][sma_column]

        if position.side == PositionSide.LONG:

            if current_price >= position.entry_price * (1 + tp):
                return ExitReason.TAKE_PROFIT

            if current_price <= position.entry_price * (1 - sl):
                return ExitReason.STOP_LOSS

            if current_price >= current_sma:
                return ExitReason.BOLLINGER_UPWARD_REVERSION

        else:

            if current_price <= position.entry_price * (1 - tp):
                return ExitReason.TAKE_PROFIT

            if current_price >= position.entry_price * (1 + sl):
                return ExitReason.STOP_LOSS

            if current_price <= current_sma:
                return ExitReason.BOLLINGER_DOWNWARD_REVERSION

        return None

    def __check_sma_dev(self, price:str, window:int, num_std_dev:float):
        sma_column = f"SMA-{price}-{window}"
        uband_column = f"Uband-{price}{window}-Dev{num_std_dev}"
        lband_column = f"Lband-{price}{window}-Dev{num_std_dev}"

        if sma_column not in self._data.columns:
            print(f"❌ ERROR: there is no {sma_column}")
            return False

        if uband_column not in self._data.columns:
            print(f"❌ ERROR: there is no {uband_column}")
            return False

        if lband_column not in self._data.columns:
            print(f"❌ ERROR: there is no {lband_column}")
            return False

        return True

    def __init_backtest(self, initial_capital, price, window, num_std_dev, tp, sl, commission_rate):
        if not self._ready:
            print("❌ ERROR: Data is not ready")
            return False

        if not self.__check_sma_dev(price, window, num_std_dev):
            return False

        if not self._init_backtest(initial_capital, tp, sl, commission_rate):
            return False

        sma_column = f"SMA-{price}-{window}"
        uband_column = f"Uband-{price}{window}-Dev{num_std_dev}"
        lband_column = f"Lband-{price}{window}-Dev{num_std_dev}"    
            
        self._trade_df = self._data.dropna(subset=[sma_column, lband_column, uband_column]).copy()
        
        self._price = price
        self._window = window
        self._num_std_dev = num_std_dev

        self._statistics["num-std-dev"] = num_std_dev
        self._statistics["sma"] = f"{price}{window}"

        return True


class RSI(Strategy):

    _STRATEGY_NAME = "RSI"

    def __init__(self, info:ConnectBinance):
        super().__init__(info)

    def trade(self, price:str="Close", margin_portion:float=0.2, window:int=14, initial_capital:int=1000, tp:float=0.05, sl:float=0.02, commission_rate:float=0.001, oversold_level:int=30, overbought_level:int=70):
        
        print("✨ Start Trading ....")
        
        if not self.check_inputs(initial_capital, margin_portion, tp, sl, commission_rate):
            return

        if not self.__init_backtest(initial_capital, price, window, overbought_level, oversold_level, tp, sl, commission_rate):
            return

        self._run_backtest(margin_portion, tp, sl, commission_rate)
        
        print("✅ Trading Finished Successfully.")

    def add_rsi(self, price:str="Close", window:int=14):

        if not isinstance(window, int) or window <= 0:
            print("❌ ERROR: window must be a positive integer")
            return False

        if self._ready:
            if price in self._PRICE_TYPE:
                delta = self._data[price].diff()
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)
                
                average_gain = gain.ewm(alpha=1/window, adjust=False).mean()
                average_loss = loss.ewm(alpha=1/window, adjust=False).mean()
                
                rs = average_gain / average_loss
                rsi = 100 - (100 / (1 + rs))

                self._data[f"RSI-{price}-{window}"] = rsi
                return True
            
            print("❌ ERROR: price must be of Close, Open, High or Low")
        
        return False

    def _get_entry_signal(self, i):

        rsi_column = f"RSI-{self._price}-{self._window}"

        previous_rsi = self._trade_df.iloc[i - 1][rsi_column]
        current_rsi = self._trade_df.iloc[i][rsi_column]

        if previous_rsi <= self._oversold_level and current_rsi > self._oversold_level:
            return PositionSide.LONG

        if previous_rsi >= self._overbought_level and current_rsi < self._overbought_level:
            return PositionSide.SHORT

        return None

    def _get_exit_signal(self, i, current_price, tp, sl):

        position = self.position

        rsi_column = f"RSI-{self._price}-{self._window}"
        current_rsi = self._trade_df.iloc[i][rsi_column]

        if position.side == PositionSide.LONG:

            if current_price >= position.entry_price * (1 + tp):
                return ExitReason.TAKE_PROFIT

            if current_price <= position.entry_price * (1 - sl):
                return ExitReason.STOP_LOSS

            if current_rsi >= self._overbought_level:
                return ExitReason.RSI_OVERBOUGHT

        else:

            if current_price <= position.entry_price * (1 - tp):
                return ExitReason.TAKE_PROFIT

            if current_price >= position.entry_price * (1 + sl):
                return ExitReason.STOP_LOSS

            if current_rsi <= self._oversold_level:
                return ExitReason.RSI_OVERSOLD

        return None   
    
    def __check_rsi(self, price:str, window:int):
        if f"RSI-{price}-{window}" not in self._data.columns:
            print(f"❌ ERROR: there is no RSI-{price}-{window}")
            return False

        return True

    def __init_backtest(self, initial_capital, price, window, overbought_level, oversold_level, tp, sl, commission_rate):

        if not self._ready:
            print("❌ ERROR: Data is not ready")
            return False

        if not self.__check_rsi(price, window):
            return False

        if not 0 <= oversold_level <= 100:
            print("❌ ERROR: oversold_level must be between 0 and 100")
            return False

        if not 0 <= overbought_level <= 100:
            print("❌ ERROR: overbought_level must be between 0 and 100")
            return False

        if overbought_level <= oversold_level:
            print("❌ ERROR: The level of overbought must be greater than oversold one")
            return False

        if not self._init_backtest(initial_capital, tp, sl, commission_rate):
            return False
        
        rsi_column = f"RSI-{price}-{window}"
        self._trade_df = self._data.dropna(subset=[rsi_column]).copy()
        self._price = price
        self._window = window
        self._oversold_level = oversold_level
        self._overbought_level = overbought_level

        self._statistics["rsi"] = rsi_column
        self._statistics["rsi-window"] = window
        self._statistics["oversold-level"] = oversold_level
        self._statistics["overbought-level"] = overbought_level

        return True


class DonchianChannel(Strategy):

    _STRATEGY_NAME = "Donchian Channel"

    def __init__(self, info:ConnectBinance):
        super().__init__(info)

    def trade(self, price:str="Close", margin_portion:float=0.2, window:int=14, initial_capital:int=1000, tp:float=0.05, sl:float=0.02, commission_rate:float=0.001):
        
        print("✨ Start Trading ....")
        
        if not self.check_inputs(initial_capital, margin_portion, tp, sl, commission_rate):
            return

        if not self.__init_backtest(initial_capital, price, window, tp, sl, commission_rate):
            return

        self._run_backtest(margin_portion, tp, sl, commission_rate)
        
        print("✅ Trading Finished Successfully.")

    def add_channels(self, window:int=14):

        if not isinstance(window, int) or window <= 0:
            print("❌ ERROR: window must be a positive integer")
            return False

        if self._ready:

            upper_band = self._data["High"].rolling(window=window).max()
            lower_band = self._data["Low"].rolling(window=window).min()
            middle_band = (upper_band + lower_band) / 2

            self._data[f"UpperChannel-{window}"] = upper_band
            self._data[f"LowerChannel-{window}"] = lower_band
            self._data[f"MiddleChannel-{window}"] = middle_band

            return True

        return False

    def _get_entry_signal(self, i):

        uband = f"UpperChannel-{self._window}"
        lband = f"LowerChannel-{self._window}"

        current_uband = self._trade_df.iloc[i - 1][uband]
        current_lband = self._trade_df.iloc[i - 1][lband]
        current_price = self._trade_df.iloc[i][self._price]

        if current_price > current_uband:
            return PositionSide.LONG

        if current_price < current_lband:
            return PositionSide.SHORT

        return None

    def _get_exit_signal(self, i, current_price, tp, sl):

        position = self.position
        mband = f"MiddleChannel-{self._window}"
        current_mband = self._trade_df.iloc[i - 1][mband]

        if position.side == PositionSide.LONG:

            if current_price >= position.entry_price * (1 + tp):
                return ExitReason.TAKE_PROFIT

            if current_price <= position.entry_price * (1 - sl):
                return ExitReason.STOP_LOSS

            if current_price < current_mband:
                return ExitReason.DONCHIAN_MIDDLE_CROSS_DOWN

        else:

            if current_price <= position.entry_price * (1 - tp):
                return ExitReason.TAKE_PROFIT

            if current_price >= position.entry_price * (1 + sl):
                return ExitReason.STOP_LOSS

            if current_price > current_mband:
                return ExitReason.DONCHIAN_MIDDLE_CROSS_UP

        return None   
    
    def __check_channels(self, window:int):

        upper_channel = f"UpperChannel-{window}"
        lower_channel = f"LowerChannel-{window}"
        middle_channel = f"MiddleChannel-{window}"

        if upper_channel not in self._data.columns:
            print(f"❌ ERROR: there is no {upper_channel}")
            return False

        if lower_channel not in self._data.columns:
            print(f"❌ ERROR: there is no {lower_channel}")
            return False

        if middle_channel not in self._data.columns:
            print(f"❌ ERROR: there is no {middle_channel}")
            return False

        return True

    def __init_backtest(self, initial_capital, price, window, tp, sl, commission_rate):

        if not self._ready:
            print("❌ ERROR: Data is not ready")
            return False

        if not self.__check_channels(window):
            return False

        if price not in self._PRICE_TYPE:
            print("❌ ERROR: price must be of Close, Open, High or Low")
            return False

        if not self._init_backtest(initial_capital, tp, sl, commission_rate):
            return False
        
        upper_channel = f"UpperChannel-{window}"
        lower_channel = f"LowerChannel-{window}"
        middle_channel = f"MiddleChannel-{window}"

        self._trade_df = self._data.dropna(subset=[upper_channel, lower_channel, middle_channel]).copy()
        self._price = price
        self._window = window

        self._statistics["window"] = window

        return True


class MACD(Strategy):

    _STRATEGY_NAME = "MACD"

    def __init__(self, info:ConnectBinance):
        super().__init__(info)

    def trade(self, price:str="Close", slow_ema:int=26, fast_ema:int=12, signal_ema:int=9, margin_portion:float=0.2, initial_capital:int=1000, tp:float=0.05, sl:float=0.02, commission_rate:float=0.001):
        
        print("✨ Start Trading ....")
        
        if not self.check_inputs(initial_capital, margin_portion, tp, sl, commission_rate):
            return

        if not self.__init_backtest(initial_capital, price, slow_ema, fast_ema, signal_ema, tp, sl, commission_rate):
            return

        self._run_backtest(margin_portion, tp, sl, commission_rate)
        
        print("✅ Trading Finished Successfully.")

    def _get_entry_signal(self, i):

        new_signal = self._trade_df.iloc[i]["Signal"]
        old_signal = self._trade_df.iloc[i - 1]["Signal"]
        new_macd = self._trade_df.iloc[i]["MACD"]
        old_macd = self._trade_df.iloc[i - 1]["MACD"]

        if old_macd <= old_signal and new_macd > new_signal:
            return PositionSide.LONG

        if old_macd >= old_signal and new_macd < new_signal:
            return PositionSide.SHORT

        return None

    def _get_exit_signal(self, i, current_price, tp, sl):

        position = self.position
        new_signal = self._trade_df.iloc[i]["Signal"]
        old_signal = self._trade_df.iloc[i - 1]["Signal"]
        new_macd = self._trade_df.iloc[i]["MACD"]
        old_macd = self._trade_df.iloc[i - 1]["MACD"]

        if position.side == PositionSide.LONG:

            if current_price >= position.entry_price * (1 + tp):
                return ExitReason.TAKE_PROFIT

            if current_price <= position.entry_price * (1 - sl):
                return ExitReason.STOP_LOSS

            if old_signal <= old_macd and new_signal > new_macd:
                return ExitReason.MACD_CROSS_DOWN

        else:

            if current_price <= position.entry_price * (1 - tp):
                return ExitReason.TAKE_PROFIT

            if current_price >= position.entry_price * (1 + sl):
                return ExitReason.STOP_LOSS

            if old_signal >= old_macd and new_signal < new_macd:
                return ExitReason.MACD_CROSS_UP

        return None   

    def __init_backtest(self, initial_capital, price, slow_ema, fast_ema, signal_ema, tp, sl, commission_rate):

        if not self._ready:
            print("❌ ERROR: Data is not ready")
            return False

        if price not in self._PRICE_TYPE:
            print("❌ ERROR: price must be of Close, Open, High or Low")
            return False

        if not self.__add_macd(price, slow_ema, fast_ema, signal_ema):
            return False

        if not self._init_backtest(initial_capital, tp, sl, commission_rate):
            return False
        
        self._trade_df = self._data.dropna(subset=["MACD", "Signal"]).copy()
        self._price = price

        self._statistics["fast ema"] = fast_ema
        self._statistics["slow ema"] = slow_ema
        self._statistics["signal ema"] = signal_ema


        return True

    def __add_macd(self, price, slow_ema, fast_ema, signal_ema):

        if not isinstance(slow_ema, int) or slow_ema <= 0:
            print("❌ ERROR: slow_ema must be a positive integer")
            return False

        if not isinstance(fast_ema, int) or fast_ema <= 0:
            print("❌ ERROR: fast_ema must be a positive integer")
            return False

        if not isinstance(signal_ema, int) or signal_ema <= 0:
            print("❌ ERROR: signal_ema must be a positive integer")
            return False

        if fast_ema >= slow_ema:
            print("❌ ERROR: fast_ema must be smaller than slow_ema")
            return False


        fast = self._data[price].ewm(span=fast_ema, adjust=False).mean()
        slow = self._data[price].ewm(span=slow_ema, adjust=False).mean()
        macd = fast - slow
        signal = macd.ewm(span=signal_ema, adjust=False).mean()

        self._data[f"MACD"] = macd
        self._data[f"Signal"] = signal

        return True


class RsiMacdEma(Strategy):

    _STRATEGY_NAME = "Hybrid (RSI_MACD_EMA)"

    def __init__(self, info:ConnectBinance):
        super().__init__(info)

    def trade(self, price:str="Close", rsi_threshold:int=50, rsi_window:int=14, slow_ema:int=26, fast_ema:int=12, signal_ema:int=9, ema_window:int=50, margin_portion:float=0.2, initial_capital:int=1000, tp:float=0.05, sl:float=0.02, commission_rate:float=0.001):
        
        print("✨ Start Trading ....")
        
        if not self.check_inputs(initial_capital, margin_portion, tp, sl, commission_rate):
            return

        if not self.__init_backtest(initial_capital, price, rsi_window, rsi_threshold, ema_window, slow_ema, fast_ema, signal_ema, tp, sl, commission_rate):
            return

        self._run_backtest(margin_portion, tp, sl, commission_rate)
        
        print("✅ Trading Finished Successfully.")

    def _get_entry_signal(self, i):

        new_signal = self._trade_df.iloc[i]["Signal"]
        old_signal = self._trade_df.iloc[i - 1]["Signal"]
        new_macd = self._trade_df.iloc[i]["MACD"]
        old_macd = self._trade_df.iloc[i - 1]["MACD"]

        current_price = self._trade_df.iloc[i][self._price]
        current_ema = self._trade_df.iloc[i][f"EMA-{self._ema_window}"]
        current_rsi = self._trade_df.iloc[i][f"RSI-{self._rsi_window}"]

        if old_macd <= old_signal and new_macd > new_signal and current_rsi > self._rsi_threshold and current_price > current_ema:
            return PositionSide.LONG

        if old_macd >= old_signal and new_macd < new_signal and current_rsi < self._rsi_threshold and current_price < current_ema:
            return PositionSide.SHORT

        return None

    def _get_exit_signal(self, i, current_price, tp, sl):

        position = self.position
        new_signal = self._trade_df.iloc[i]["Signal"]
        old_signal = self._trade_df.iloc[i - 1]["Signal"]
        new_macd = self._trade_df.iloc[i]["MACD"]
        old_macd = self._trade_df.iloc[i - 1]["MACD"]

        if position.side == PositionSide.LONG:

            if current_price >= position.entry_price * (1 + tp):
                return ExitReason.TAKE_PROFIT

            if current_price <= position.entry_price * (1 - sl):
                return ExitReason.STOP_LOSS

            if old_signal <= old_macd and new_signal > new_macd:
                return ExitReason.MACD_CROSS_DOWN

        else:

            if current_price <= position.entry_price * (1 - tp):
                return ExitReason.TAKE_PROFIT

            if current_price >= position.entry_price * (1 + sl):
                return ExitReason.STOP_LOSS

            if old_signal >= old_macd and new_signal < new_macd:
                return ExitReason.MACD_CROSS_UP

        return None   

    def __init_backtest(self, initial_capital, price, rsi_window, rsi_threshold, ema_window, slow_ema, fast_ema, signal_ema, tp, sl, commission_rate):

        if not self._ready:
            print("❌ ERROR: Data is not ready")
            return False

        if price not in self._PRICE_TYPE:
            print("❌ ERROR: price must be of Close, Open, High or Low")
            return False

        if not isinstance(rsi_threshold, int) or not 0 <= rsi_threshold <= 100:
            print("❌ ERROR: rsi_threshold must be an integer between 0 and 100")
            return False

        if not self.__add_rsi(price, rsi_window):
            return False

        if not self.__add_macd(price, slow_ema, fast_ema, signal_ema):
            return False

        if not self.__add_ema(price, ema_window):
            return False

        if not self._init_backtest(initial_capital, tp, sl, commission_rate):
            return False
        
        self._trade_df = self._data.dropna(subset=["MACD", "Signal", f"RSI-{rsi_window}", f"EMA-{ema_window}"]).copy()
        self._price = price
        self._ema_window = ema_window
        self._rsi_threshold = rsi_threshold
        self._rsi_window = rsi_window

        self._statistics["fast ema"] = fast_ema
        self._statistics["slow ema"] = slow_ema
        self._statistics["signal ema"] = signal_ema

        self._statistics["rsi window"] = rsi_window
        self._statistics["rsi threshold"] = rsi_threshold

        self._statistics["trend ema"] = ema_window
        
        return True

    def __add_macd(self, price, slow_ema, fast_ema, signal_ema):

        if not isinstance(slow_ema, int) or slow_ema <= 0:
            print("❌ ERROR: slow_ema must be a positive integer")
            return False

        if not isinstance(fast_ema, int) or fast_ema <= 0:
            print("❌ ERROR: fast_ema must be a positive integer")
            return False

        if not isinstance(signal_ema, int) or signal_ema <= 0:
            print("❌ ERROR: signal_ema must be a positive integer")
            return False

        if fast_ema >= slow_ema:
            print("❌ ERROR: fast_ema must be smaller than slow_ema")
            return False


        fast = self._data[price].ewm(span=fast_ema, adjust=False).mean()
        slow = self._data[price].ewm(span=slow_ema, adjust=False).mean()
        macd = fast - slow
        signal = macd.ewm(span=signal_ema, adjust=False).mean()

        self._data[f"MACD"] = macd
        self._data[f"Signal"] = signal

        return True

    def __add_rsi(self, price, rsi_window):

        if not isinstance(rsi_window, int) or rsi_window <= 0:
            print("❌ ERROR: rsi_window must be a positive integer")
            return False

        if price in self._PRICE_TYPE:
            delta = self._data[price].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            average_gain = gain.ewm(alpha=1/rsi_window, adjust=False).mean()
            average_loss = loss.ewm(alpha=1/rsi_window, adjust=False).mean()
            
            rs = average_gain / average_loss
            rsi = 100 - (100 / (1 + rs))

            self._data[f"RSI-{rsi_window}"] = rsi

            return True
            
        print("❌ ERROR: price must be of Close, Open, High or Low")
        
        return False

    def __add_ema(self, price, ema_window):

        if not isinstance(ema_window, int) or ema_window <= 0:
            print("❌ ERROR: ema_window must be a positive integer")
            return False

        if price in self._PRICE_TYPE:

            self._data[f"EMA-{ema_window}"] = self._data[price].ewm(span=ema_window, adjust=False).mean()

            return True
        
        print("❌ ERROR: price must be of Close, Open, High or Low")
        
        return False
