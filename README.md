# Cryptocurrency Strategy Backtester

A desktop application for downloading historical cryptocurrency market data from Binance and backtesting technical-analysis strategies. It displays the resulting account statistics and an equity curve; it does not place live trades through the GUI.

## Strategies

- Moving Average
- RSI
- MACD
- Bollinger Bands
- Donchian Channel
- Hybrid (MACD, RSI, and moving-average filters)

## Requirements

- Python 3
- An internet connection to download historical Binance market data

The GUI and strategy modules use PyQt5, pandas, matplotlib, and python-binance. Install them with:

```bash
python -m pip install PyQt5 pandas matplotlib python-binance
```

## Run

From the project directory:

```bash
python gui.py
```

## Using the application

1. In **Connect Binance**, enter a market symbol such as `BTCUSDT`, a start and end date in `YYYY-MM-DD` format, and a timeframe. Select **Connect** to load historical candles.
2. Data is saved as a local `.pkl` file for the selected symbol, date range, and timeframe. Reconnecting with the same values loads that cached file; otherwise the application downloads the data from Binance.
3. In **Settings**, set the initial capital, margin portion, take-profit level, stop-loss level, and commission rate.
4. Open a strategy tab, set its parameters, and select **Start Trading**. The Hybrid strategy combines MACD crossover signals with RSI and moving-average filters.
5. Review the report and equity curve shown in the strategy tab.

## Backtest results

The report includes final capital, profit or loss, total return, trade counts, and win rate. Results are calculated from historical candle data using the configured settings and commission rate. They are estimates, not a guarantee of future performance; the GUI is a backtesting tool, not a live-trading interface.
