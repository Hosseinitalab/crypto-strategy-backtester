import math
import numpy as np
from bitpin_utils import *
from color_tools import *


class TradeBot:

    def __init__(self, symbol, tp, sl, trade_amount, update_interval):
        self._symbol = symbol
        self._tp = tp
        self._sl = sl
        self._trade_amount = trade_amount
        self._update_interval = update_interval

    def _validate_inputs(self):

        if (not self._symbol or
            not isinstance(self._symbol, str) or
            "_" not in self._symbol or
            len(list(self._symbol.split("_"))) != 2):
            print("❌ ERROR: symbol must be a string like BTC_USDT")
            return False
        
        if 0 >= self._tp or self._tp >= 1:
            print("❌ ERROR: tp must be between 0 and 1")
            return False
        
        if 0 >= self._sl or self._sl >= 1:
            print("❌ ERROR: sl must be between 0 and 1")
            return False

        if not isinstance(self._trade_amount, (float, int)) or self._trade_amount <= 0:
            print("❌ ERROR: trade amount must be a positive float number ")
            return False
        
        if self._update_interval <= 0:
            print("❌ ERROR: update_interval must be between greater than Zero")
            return False

        return True


class ScalperBot(TradeBot):

    def __init__(self, buy_threshold, symbol:str="BTC_USDT", tp:float=0.15, sl:float=0.05, trade_amount:float=0.0001, update_interval:int=30):
        super().__init__(symbol, tp, sl, trade_amount, update_interval)
        self._buy_threshold = buy_threshold
        self._ready = self._validate_inputs() and self.__validate_threshold()

    def trade(self):

        if not self._ready:
            return

        while True:

            try:

                current_price = get_price(self._symbol)
                
                if current_price == 0.0:
                    print("❌ ERROR: could not find price data. Retrying ...")
                    print(40*'-')
                    time.sleep(self._update_interval)
                    continue

                print(f"Current Price: {current_price}")
                print(40*'-')

                active_orders = get_active_orders(self._symbol, False)

                if len(active_orders) > 0:
                    print(f"❌ ERROR: please wait. there is already {len(active_orders)} active orders")

                else:

                    if current_price >= self._buy_threshold:
                        print("\033[91mACTION: price is above thereshold. placing BUY order\033[0m")
                        print(40*'-')

                        order_id = place_limit_order(
                            symbol=self._symbol,
                            side="buy",
                            price=current_price*0.9,
                            amount=self._trade_amount
                        )

                        if order_id:
                            print(f"\033[91mSUCCESS\033[0m: Buy order {order_id} places")


                            sell_price = current_price * (1 + self._tp)
                            print(f"\033[91mACTION: placing SELL order at {sell_price}\033[0m")

                            place_limit_order(
                                symbol=self._symbol,
                                side="sell",
                                price=sell_price,
                                amount=self._trade_amount)

                    else:
                        print(f"IDLE: price is {current_price} and below {self._buy_threshold}")
                        print(40*'-')

                print(f"Sleep: waiting for {self._update_interval} seconds.")
                print(40*'-')
                time.sleep(self._update_interval)

                
            except KeyboardInterrupt:
                print("Bot Stoppped by user")
                break

            except Exception as e:
                print(f"❌ ERROR: {e}")
                time.sleep(self._update_interval)

    def __validate_threshold(self):

        if not isinstance(self._buy_threshold, int) or self._buy_threshold <= 0:
            print("❌ ERROR: buy_threshold amount must be a positive integer number")
            return False

        return True


class MarketSentimentBot(TradeBot):

    def __init__(self, symbol:str="BTC_USDT", tp:float=0.15, sl:float=0.05, trade_amount:float=0.0001, imbalance_threshold:float=0.5, update_interval:int=30):
        super().__init__(symbol, tp, sl, trade_amount, update_interval)
        self._imbalance_threshold = imbalance_threshold
        self._ready = self._validate_inputs() and self.__validate_threshold()

    def trade(self):

        if not self._ready:
            return
        
        while True:

            try:
                imbalance = self.__caculate_imbalance()
                active_orders = get_active_orders(self._symbol, False)

                if len(active_orders) > 0:
                    print(f"❌ ERROR: please wait. there is already {len(active_orders)} active orders")
                    time.sleep(self._update_interval)
                    continue

                print(f"Analysed imbalance is: {imbalance:.2f}")

                if imbalance > self._imbalance_threshold:

                    current_price = get_price(self._symbol)

                    print(f"\033[91mACTION: high BUY Pressure detected. entering long at {current_price}\033[0m")
                    buy_id = place_limit_order(
                        symbol=self._symbol,
                        side="buy",
                        price=current_price,
                        amount=self._trade_amount)
                    
                    if buy_id:
                        target_price = current_price * (1 + self._tp)
                        print(f"\033[91mACTION: place Take Profit order at {target_price}\033[0m")
                        sell_id = place_limit_order(
                            symbol=self._symbol,
                            side="sell",
                            price=target_price,
                            amount=self._trade_amount)
                        
                elif imbalance < -self._imbalance_threshold:
                    print(f"\033[91mACTION: high SELL Pressure detected.\033[0m")

                time.sleep(self._update_interval)

            except KeyboardInterrupt:
                print("Bot Stoppped by user")
                break

            except Exception as e:
                print(f"❌ ERROR: {e}")
                time.sleep(self._update_interval)
    
    def __caculate_imbalance(self):

        try:
            book = get_orderbook(self._symbol)
                
            ask_vol = book[book["side"] == "ask"]["amount"].astype(float).sum()
            bid_vol = book[book["side"] == "bid"]["amount"].astype(float).sum()

            total_vol = bid_vol + ask_vol
            imbalance = (bid_vol - ask_vol) / total_vol if total_vol > 0 else 0

            return imbalance 
        
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return 0.0

    def __validate_threshold(self):

        if -1 >= self._imbalance_threshold or self._imbalance_threshold >= 1:
            print("❌ ERROR: sl must be between -1 and 1")
            return False
        
        return True


class RsiMaBot(TradeBot):

    def __init__(self, symbol:str="BTC_USDT", tp:float=0.15, sl:float=0.05, trade_amount:float=0.0001, rsi_window:int=14, rsi_overbought:int=70, rsi_oversold:int=30, ma_window:int=20, update_interval:int=30):
        super().__init__(symbol, tp, sl, trade_amount, update_interval)
        self._rsi_window = rsi_window
        self._ma_window = ma_window
        self._overbought_level = rsi_overbought
        self._oversold_level = rsi_oversold
        self._historical_data = []
        self._ready = self._validate_inputs() and self.__validate_windows() and self.__validate_rsi_levels()

    def trade(self):

        if not self._ready:
            return

        max_space = 2 * max(self._ma_window + 1, self._rsi_window + 1)

        self.__warmup()

        if not self._historical_data:
            return

        while True:

            try:

                current_price = get_price(self._symbol)

                if len(self._historical_data) == max_space:
                    self._historical_data.pop(0)

                self._historical_data.append(current_price)

                ma = self.__calculate_ma(self._historical_data)
                rsi = self.__calculate_rsi(self._historical_data)
                print(f"Price: {current_price:} | Ma: {ma:.2f} | RSI: {rsi:.2f}")

                active_orders = get_active_orders(self._symbol, False)
                active_len = len(active_orders)
                if active_len > 0:
                    print(f"Waiting for {active_len} active orders to be filled")
                    time.sleep(self._update_interval)
                    continue

                if current_price > ma and rsi < self._oversold_level:

                    print("Signal Buy: Place Buy Order")

                    buy_id = place_limit_order(
                        symbol=self._symbol,
                        side="buy",
                        price=current_price,
                        amount=self._trade_amount
                    )

                    if buy_id:
                        target_price = current_price * (1 + self._tp)
                        print(f"Traget Price is: {target_price}")
                        
                        place_limit_order(
                            symbol=self._symbol,
                            side="sell",
                            price=target_price,
                            amount=self._trade_amount
                        )

                time.sleep(self._update_interval)

            except KeyboardInterrupt:
                print("Bot Stoppped by user")
                break

            except Exception as e:
                print(f"❌ ERROR: {e}")
                time.sleep(self._update_interval)
                    
    def __warmup(self):

        print("Getting Warmup Data Started ...")

        max_warmup_data = max(self._rsi_window + 1, self._ma_window + 1)

        while True:
            
            if len(self._historical_data) == max_warmup_data:
                break

            current_price = get_price(self._symbol)

            self._historical_data.append(current_price)
            print(f"Warmup Data Gathering: {len(self._historical_data):02d} / {max_warmup_data}")
            time.sleep(self._update_interval)

        print("Warmup Data Gathering successfully finished.")

    def __calculate_rsi(self, prices):

        if len(prices) < self._rsi_window + 1:
            return 50.0

        recent_prices = prices[-(self._rsi_window + 1):]
        delta = np.diff(recent_prices)

        gains = delta[delta > 0].sum()
        losses = -delta[delta < 0].sum()

        average_gain = gains / self._rsi_window
        average_loss = losses / self._rsi_window

        if average_gain == 0 and average_loss == 0:
            return 50.0

        if average_loss == 0:
            return 100.0

        rs = average_gain / average_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def __calculate_ma(self, prices):
        sum_data = sum(prices[-self._ma_window:])
        mean_data = sum_data / self._ma_window
        return mean_data

    def __validate_windows(self):

        if not isinstance(self._rsi_window, int) or self._rsi_window <= 0:
            print("❌ ERROR: rsi_window must be a positive integer number")
            return False
        
        if not isinstance(self._ma_window, int) or self._ma_window <= 0:
            print("❌ ERROR: ma_window must be a positive integer number")
            return False

        return True

    def __validate_rsi_levels(self):

        if not 0 <= self._oversold_level <= 100:
            print("❌ ERROR: oversold_level must be between 0 and 100")
            return False

        if not 0 <= self._overbought_level <= 100:
            print("❌ ERROR: overbought_level must be between 0 and 100")
            return False

        if self._overbought_level <= self._oversold_level:
            print("❌ ERROR: The level of overbought must be greater than oversold one")
            return False

        return True


class GridBot(TradeBot):

    def __init__(self, symbol:str="BTC_USDT", trade_amount:float=0.0001, grid_level:int=4, range_percent:float=0.04, update_interval:int=30):
        super().__init__(symbol, 0.15, 0.5, trade_amount, update_interval)
        self._grid_level = grid_level
        self._range_percent = range_percent
        self._ready = self._validate_inputs() and self.__validate_grid() and self.__calculate_bands()

    def trade(self):

        if not self._ready:
            return

        active_grids = []

        try:

            order_size = self.__place_orders(active_grids)
            
            if not order_size:
                return 

            while True:

                time.sleep(self._update_interval)

                active_orders = get_active_orders(self._symbol, False) 
                active_order_ids = [order["id"] for order in active_orders]
                filled_orders = [grid for grid in active_grids if grid["id"] not in active_order_ids]
                in_progress_orders = [grid for grid in active_grids if grid["id"] in active_order_ids]

                for p in in_progress_orders:
                    print(f"symbol: {self._symbol} | {'order: '+str(p["side"]):12s} | id: {p["id"]} | price: {p["price"]:10.4f} | is in progress...")

                for filled in filled_orders:

                    status = self.__get_order_status(self._symbol, filled["id"], filled["side"])

                    print(f"symbol: {self._symbol} | {'order: '+str(filled['side']):12s} | id: {filled['id']} | price: {filled['price']:10.4f} | is {status}")

                    if status == "filled":

                        if filled["side"] == "buy":
                            new_price = filled["price"] + order_size
                            new_side = "sell"

                        else:
                            new_price = filled["price"] - order_size
                            new_side = "buy"

                        # Make sure we don't create a grid outside the boundaries
                        if self._lower_price <= new_price <= self._upper_price:

                            order_id = place_limit_order(
                                        symbol=self._symbol,
                                        side = new_side,
                                        price=new_price,
                                        amount = self._trade_amount
                            )

                            if order_id:
                                active_grids.append({
                                    "id": order_id,
                                    "side": new_side,
                                    "price": new_price,
                                    "base_amount": self._trade_amount}
                                )

                    # Remove the old grid       
                    active_grids.remove(filled)

                if not active_grids:
                    break

            print("Grid Trading Successfully finished.")
                
        except KeyboardInterrupt:
            print("Bot Stoppped by user")

        except Exception as e:
            print(f"❌ ERROR: {e}")
            time.sleep(self._update_interval)

    def __calculate_bands(self):
        current_price = get_price(self._symbol)
        if current_price is None:
            return False
        
        self._lower_price = (1 - self._range_percent) * current_price
        self._upper_price = (1 + self._range_percent) * current_price

        return True

    def __calculate_grids(self, current_price):

        step_size = (self._upper_price - self._lower_price) / self._grid_level

        grid_orders = []

        for i in range(1 + self._grid_level):
            target_price = self._lower_price + (i * step_size)

            if target_price < current_price:
                side = "buy"

            elif target_price > current_price:
                side = "sell"

            else:
                continue
                
            grid_orders.append(
                {
                    "side": side,
                    "price": target_price,
                    "base_amount": self._trade_amount
                }
            )

        return grid_orders, step_size

    def __place_orders(self, active_grids):

        current_price = get_price(self._symbol)

        orders, orders_size = self.__calculate_grids(current_price)

        buy_count = sum(1 for i in orders if i["side"] == "buy")
        sell_count = sum(1 for i in orders if i["side"] == "sell")

        required_usdt = buy_count * self._trade_amount * current_price
        required_symbol_amount = sell_count * self._trade_amount

        print(f"CHECKING: need {required_usdt} usdt and {required_symbol_amount} {self._symbol}")
        print(f"EXECUTE: Placing {len(orders)} levels on {self._symbol}")

        active_grid_orders = place_bulk_orders(self._symbol, orders)

        if not active_grid_orders:
            print("❌ ERROR: Orders placement failed. Check your API or Wallet")
            return None

        for i, _id in enumerate(active_grid_orders):
            active_grids.append({
                "id": _id,
                "side": orders[i]["side"],
                "price": orders[i]["price"],
                "base_amount": orders[i]["base_amount"]
            })  


        return orders_size   

    def __get_order_status(self, symbol, order_id, side):
        history = get_order_history(symbol, self._grid_level + 1, False)

        if history:
            for order in history:
                _id = order["id"]
                _is_cancel = order["req_to_cancel"]
                _side = order["side"]
                _amount = float(order["base_amount"])

                if order_id == _id and _side == side and _amount == self._trade_amount:

                    if _is_cancel:
                        return "cancelled"
                    
                    return "filled"

        return "reject"

    def __validate_grid(self):

        if (
            isinstance(self._range_percent, bool)
            or not isinstance(self._range_percent, (int, float))
            or not math.isfinite(self._range_percent)
            or not 0 < self._range_percent < 1
        ):
            print("❌ ERROR: range_percent must be between 0 and 1")
            return False

        if not isinstance(self._grid_level, int) or self._grid_level <= 0:
            print("❌ ERROR: grid_level must be a positive integer")
            return False

        return True


class TriangleArbitage(TradeBot):

    def __init__(self, investment_irt:float, min_profit_irt:float, symbol:str="BTC_USDT", multi_coins:bool=False, number_of_coins:int=1, update_interval:int=30):
        super().__init__(symbol, 0.15, 0.5, 1000, update_interval)
        self._investment_irt = investment_irt
        self._min_profit_irt = min_profit_irt
        self._multi_coins = multi_coins
        self._number_of_coins= number_of_coins
        self._ready = self._validate_inputs() and self.__validate_irt()

    def trade(self):

        if not self._ready:
            return

        currencies = []
        if self._multi_coins:
            currencies = self.__detect_currencies()

        while True:

            try:
                df = self.__check_arbitage(currencies)
                if df is None:
                    time.sleep(self._update_interval)
                    continue

                for currency_name, currency in df.iterrows():

                    profit = currency["profit_irt"] if not currency.empty else 0

                    if not currency.empty and currency["is_profitable"]:

                        print(50 * "-")
                        print("Arbitage Detected")
                        print(f"Estimated net profit: {profit:.3f} IRT")
                        print(50 * "-")

                        ############################## First Order #############################
                        target_usdt = round(self._investment_irt / currency["ask_usdt_irt"], 3)
                        print(f">>> [1/3] Buying {target_usdt} USDT ...")
                        order_1 = place_market_order(
                            symbol="USDT_IRT",
                            side="buy",
                            amount=target_usdt)
                        if not order_1:
                            break
                        print(f">>> [1/3] Bought {target_usdt} USDT.")
                        usdt_after_commission = target_usdt * (1 - self.__get_commission("USDT_IRT"))

                        ############################# Second Order ############################
                        target_currency = round(usdt_after_commission / currency["ask_currency_usdt"], 6)
                        print(f">>> [2/3] Buying {target_currency} {currency_name} ...")
                        order_2 = place_market_order(
                            symbol=currency_name + "_USDT",
                            side="buy",
                            amount=target_currency)
                        if not order_2:
                            break
                        print(f">>> [2/3] Bought {target_currency} {currency_name}.")
                        currency_after_commission = target_currency * (1 - self.__get_commission(currency_name + "_USDT"))

                        ############################# Third Order ############################
                        print(f">>> [3/3] Selling {currency_after_commission} {currency_name} ...")
                        order_3 = place_market_order(
                            symbol=f"{currency_name}_IRT",
                            side="sell",
                            amount=currency_after_commission)
                        if not order_3:
                            break
                        print(f">>> [3/3] Sold {currency_after_commission} {currency_name}.")

                        print("cycle completed successfully")

                    else:
                        p = f"{profit:.0f}"
                        print(f"{toCyan(currency_name):17s} Net profit estimate:" + toRed(p) + " IRT")

                print(42 * "-")
                time.sleep(self._update_interval)



            except KeyboardInterrupt:
                print("Bot Stoppped by user")
                break

            except Exception as e:
                print(f"❌ ERROR: {e}")
                time.sleep(self._update_interval)

    def __check_arbitage(self, currency_list):

        try:

            if not currency_list:
                c = self._symbol.split("_")
                if c[1] != "USDT":
                    return None
                
                currency_list = [c[0]]

            symbols = []
            is_profitable = []
            profit_irt = []
            final_irt = []

            ask_usdt_irt = []
            ask_currency_usdt = []
            bid_currency_irt = []

            for currency in currency_list:

                ob_usdt_irt = get_orderbook("USDT_IRT")
                ob_currency_usdt = get_orderbook(currency + "_USDT")
                ob_currency_irt = get_orderbook(currency + "_IRT")

                
                if ob_usdt_irt is None or ob_currency_usdt is None or ob_currency_irt is None:
                    if len(currency_list) == 1:
                        return None
                    
                    else:
                        continue

                best_ask_usdt_irt = float(ob_usdt_irt[ob_usdt_irt["side"] == "ask"].loc[0]["price"])
                best_ask_currency_usdt = float(ob_currency_usdt[ob_currency_usdt["side"] == "ask"].loc[0]["price"])
                best_bid_currency_irt = float(ob_currency_irt[ob_currency_irt["side"] == "bid"].iloc[0]["price"])

                usdt_bought = (self._investment_irt / best_ask_usdt_irt) * (1 - self.__get_commission("USDT_IRT"))
                currency_bought = (usdt_bought / best_ask_currency_usdt) * (1 - self.__get_commission(currency + "_USDT"))
                final_price = (currency_bought * best_bid_currency_irt) * (1 - self.__get_commission(currency + "_IRT"))

                net_profit = final_price - self._investment_irt

                symbols.append(currency)
                is_profitable.append(net_profit > self._min_profit_irt)
                profit_irt.append(net_profit)
                final_irt.append(final_price)

                ask_usdt_irt.append(best_ask_usdt_irt)
                ask_currency_usdt.append(best_ask_currency_usdt)
                bid_currency_irt.append(best_bid_currency_irt)

            details = {
                "symbol": symbols,
                "is_profitable": is_profitable,
                "profit_irt": profit_irt,
                "final_irt": final_irt,
                "ask_usdt_irt": ask_usdt_irt,
                "ask_currency_usdt": ask_currency_usdt,
                "bid_currency_irt": bid_currency_irt, 
            }

            info = pd.DataFrame(details)
            info.set_index("symbol", inplace=True)

            return info 


        except Exception as e:
            print(f"❌ ERROR: Orderbook parsing failed. {e}")
            return None
    
    def __get_commission(self, symbol):

        commission = get_commission(symbol)
        if commission is None:
            return None

        taker_fee = commission.loc[symbol, "taker"]

        return taker_fee
     
    def __detect_currencies(self):

        prices = get_all_prices()
        if prices.empty:
            return None

        return self.__get_currencies(prices.index)

    def __get_currencies(self, currencies_list):
        if currencies_list.empty:
            return []

        usdt_list = []
        irt_list = []

        added = 0

        for currency in currencies_list:

            c1, c2 = currency.split("_")

            if c2 == "USDT" and c1 not in usdt_list:
                usdt_list.append(c1)

            elif c2 == "IRT" and c1 not in irt_list:
                irt_list.append(c1)

        bigger_list = usdt_list if len(usdt_list) >= len(irt_list) else irt_list
        smaller_list = usdt_list if bigger_list is irt_list else irt_list

        mutual_currencies = []

        for i in smaller_list: 
            if i in bigger_list:
                if self._multi_coins and added + 1 > self._number_of_coins:
                    break
                mutual_currencies.append(i)
                added += 1

        return mutual_currencies
    
    def __validate_irt(self):

        if (
            isinstance(self._investment_irt, bool) or
            not isinstance(self._investment_irt, (float, int)) or 
            not math.isfinite(self._investment_irt) or
            self._investment_irt <= 0):
            print("❌ ERROR: investment_irt must be a positive number")
            return False

        if (
            isinstance(self._min_profit_irt, bool) or
            not isinstance(self._min_profit_irt, (float, int)) or 
            not math.isfinite(self._min_profit_irt) or
            self._min_profit_irt <= 0):
            print("❌ ERROR: min_profit_irt must be a positive number")
            return False

        if not isinstance(self._multi_coins, bool):
            print("❌ ERROR: all_coin must be True/False")
            return False

        if self._multi_coins:
            if not isinstance(self._number_of_coins, int) and self._number_of_coins >= 1:
                print("❌ ERROR: number_of_coins must be a positive number")
                return False

        return True
