from color_tools import *
import config
import requests
import time
import pandas as pd

# security keys
BASE_URL = "https://api.bitpin.org"
API_KEY = config.API_KEY
SECRET_KEY = config.SECRET_KEY
access_token = None    # 15 mins expireation time
refresh_token = None   # 30 days expiration time
expire_time = 0        # count passed time

def login():
    global access_token, refresh_token, expire_time
    
    EXPIRATION_LIMIT = 900  # seconds
    url = f"{BASE_URL}/api/v1/usr/authenticate/"
    payload = {"api_key": API_KEY, "secret_key": SECRET_KEY}
    
    try:
        rsp = requests.post(url, json=payload)
        
        if rsp.status_code == 200: # successful
            data = rsp.json()
            access_token = data["access"]
            refresh_token = data["refresh"]
            expire_time = time.time() + EXPIRATION_LIMIT
            print(f"✅ Successful Login at {time.strftime("%H:%M:%S")}")
            return True
        else:
            print(f"❌ ERRPR[unsuccessful login]: {rsp.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR[system error]: error {e}")
        return False

def get_valid_header():
    global access_token, expire_time
    
    renew_access = False
        
    if not access_token:
        print("There is no Access-Token.")
        renew_access = True
    elif time.time() > (expire_time - 60):
        print("Access-Token expired.")
        renew_access = True

    if renew_access:
        login()

    output = {
        "Authorization": f"Bearer {access_token}",
        "Content_Type": "application.json"
    }

    return output

def fetch_data(endpoint):
    
    url = f"{BASE_URL}{endpoint}"

    try:
        rsp = requests.get(url, headers=get_valid_header())

        if rsp.status_code == 200: # successful
            return rsp.json()
        elif rsp.status_code == 429:
            print("❗We faced with the error-429 limitation. Wait 5 seconds please.")
            time.sleep(5)
            return fetch_data(endpoint)
        else:
            print(f"❌ ERROR[fatching from {endpoint}]: {rsp.status_code}")

    except Exception as e:
        print(f"❌ ERROR[system error]:")

def get_all_prices():

    url = f"{BASE_URL}/api/v1/mkt/tickers/" 

    rsp = requests.get(url)
    if rsp.status_code == 200:
        df = pd.DataFrame(rsp.json())
        df.set_index("symbol", inplace=True)
        return df

    return None

def get_price(symbol:str="BTC_USDT"):
    if not isinstance(symbol, str) or not symbol:
        return None

    prices = get_all_prices()

    if prices is None or prices.empty or symbol not in prices.index:
        print(f"❌ ERROR: {symbol} is not found")
        return None

    return float(prices.loc[symbol, "price"])

def get_orderbook(symbol, limit=None):

    url = f"{BASE_URL}/api/v1/mth/orderbook/{symbol}/"

    rsp = requests.get(url)
    if rsp.status_code == 200:
        data = rsp.json()

        asks_df = pd.DataFrame(data.get("asks", []), columns=["price", "amount"])
        asks_df["side"] = "ask"
        if limit:
            asks_df = asks_df.head(limit)

        bids_df = pd.DataFrame(data.get("bids", []), columns=["price", "amount"])
        bids_df["side"] = "bid"
        if limit:
            bids_df = bids_df.head(limit)

        df = pd.concat([asks_df, bids_df], ignore_index=True)
                
        return df

    return None

def price_monitor(symbol, target_price, check_interval=10):

    while True:
        symbols = get_all_prices()
        
        if symbol:
            if symbol in symbols.index:
                current_price = float(symbols.loc[symbol, "price"])
                print(f"{time.strftime("%H:%M:%S")} | price: {current_price}")
                if current_price > target_price:
                    print(f"🚨 {symbol} met {target_price}")
                    break
            else:
                print(f"❌ ERROR: {symbol} not found")
        else:
            print("❌ ERROR: getting data from server error")
            
        time.sleep(check_interval)

def get_my_balance():
    data = fetch_data("/api/v1/wlt/wallets/")

    i = 0
    if data:
          for wallet in data:
              balance = float(wallet["balance"])
              frozen = float(wallet["frozen"])
              asset = wallet["asset"]
              
              if (balance > 0 or frozen > 0):
                  i += 1
                  print("{:02}) {:10} balance: {:10}\tfrozen: {}".format(i, asset, balance, frozen))
    else:
        print("❌ ERROR: getting the current balances met with failure")

def get_deposit_address(currency_code, network_id):
    url = f"{BASE_URL}/api/v1/wlt/address/"

    PAYLOAD = {
        "currency": currency_code,
        "network": network_id
    }
    rsp = requests.post(url, json=PAYLOAD, headers=get_valid_header())
    if rsp.status_code == 200:
        return rsp.json()
    else:
        print("❌ ERROR: error in getting deposit address")
        return None

def get_all_networks():
    url = f"{BASE_URL}/api/v1/mkt/networks/"

    rsp = requests.get(url)
    if rsp.status_code == 200:
        networks = rsp.json()
        sorted_networks = sorted(networks, key=lambda x: x["id"])
        return sorted_networks
    else:
        print("❌ ERROR: error in getting all networks")

def place_limit_order(symbol, side, price, amount):
    url = f"{BASE_URL}/api/v1/odr/orders/"

    PAYLOAD = {
        "symbol": symbol,
        "type": "limit",
        "side": side,
        "price": price,
        "base_amount": amount
    }
    rsp = requests.post(url, json=PAYLOAD, 
                        headers=get_valid_header())
    if rsp.status_code in (200, 201):
        rsp_data = rsp.json()

        order_id     = rsp_data["id"]
        order_symb   = rsp_data["symbol"]
        order_side   = rsp_data["side"]
        order_price  = rsp_data["price"]
        order_amount = rsp_data["base_amount"]
        order_state  = rsp_data["state"]
        order_date   = rsp_data["created_at"]

        print(40 * "-")
        print(f"Limit-Order registered successfully")
        print(40 * "-")

        if order_side == "sell":
            give_color = toRed
        else:
            give_color = toGreen

        print(f"Order Kind:  {toYellow("Limit-Order")}")
        print(f"Order ID:    {order_id}")
        print(f"Symbol:      {order_symb}")
        print(f"Side:        {give_color(order_side)}")
        print(f"Price:       {toPurple(order_price)}")
        print(f"Amount:      {order_amount}")
        print(f"Status:      {order_state}")
        print(f"Created At:  {order_date}")
        print(40 * "-")

        return order_id

    else:
        print("❌ ERROR: Place Limit-Order met with failure")
        return None

def place_stop_limit_order(symbol, side, stop_price, price, amount):
    url = f"{BASE_URL}/api/v1/odr/orders/"

    PAYLOAD = {
        "symbol": symbol,
        "type": "stop_limit",
        "side": side,
        "price": price,
        "stop_price": stop_price,
        "base_amount": amount
    }
    rsp = requests.post(url, json=PAYLOAD, 
                        headers=get_valid_header())
    if rsp.status_code in (200, 201):
        rsp_data = rsp.json()

        order_id     = rsp_data["id"]
        order_symb   = rsp_data["symbol"]
        order_side   = rsp_data["side"]
        order_price  = rsp_data["price"]
        order_amount = rsp_data["base_amount"]
        order_state  = rsp_data["state"]
        order_date   = rsp_data["created_at"]

        print(40 * "-")
        print(f"Stop-Limit-Order registered successfully")
        print(40 * "-")

        if order_side == "sell":
            give_color = toRed
        else:
            give_color = toGreen
        
        print(f"Order Kind:  {toYellow("Stop-Limit")}")
        print(f"Order ID:    {order_id}")
        print(f"Symbol:      {order_symb}")
        print(f"Side:        {give_color(order_side)}")
        print(f"Stop Price:  {toPurple(stop_price)}")
        print(f"Limit Price: {toPurple(order_price)}")
        print(f"Amount:      {order_amount}")
        print(f"Status:      {order_state}")
        print(f"Created At:  {order_date}")
        print(40 * "-")

        return order_id

    else:
        print("❌ ERROR: Place Stop_Limit-Order met with failure")
        return None

def place_market_order(symbol, side, amount):
    url = f"{BASE_URL}/api/v1/odr/orders/"

    PAYLOAD = {
        "symbol": symbol,
        "type": "market",
        "side": side,
        "base_amount": amount
    }
    rsp = requests.post(url, json=PAYLOAD, headers=get_valid_header())
    if rsp.status_code in (200, 201):
        rsp_data = rsp.json()

        order_id     = rsp_data["id"]
        order_symb   = rsp_data["symbol"]
        order_side   = rsp_data["side"]
        order_price  = rsp_data["price"]
        order_amount = rsp_data["base_amount"]
        order_state  = rsp_data["state"]
        order_date   = rsp_data["created_at"]

        print(40 * "-")
        print(f"Market-Order registered successfully")
        print(40 * "-")

        if order_side == "sell":
            give_color = toRed
        else:
            give_color = toGreen

        print(f"Order Kind:  {toYellow("Market")}")
        print(f"Order ID:    {order_id}")
        print(f"Symbol:      {order_symb}")
        print(f"Side:        {give_color(order_side)}")
        print(f"Price:       {toPurple(order_price)}")
        print(f"Amount:      {order_amount}")
        print(f"Status:      {order_state}")
        print(f"Created At:  {order_date}")
        print(40 * "-")

        return order_id

    else:
        print(rsp.status_code)
        print("❌ ERROR: Place Market-Order met with failure")
        return None

def place_bulk_orders(symbol, orderlist):
    if not orderlist:
        print("Orderlist is empty")
        return []

    MAX_ORDERS = 10  # maximum number of orders announced by Bitpin
    if len(orderlist) > MAX_ORDERS:
        print(f"❌ ERROR: you are forbidden to send more than {MAX_ORDERS} orders at once")
        return []
        
    url = f"{BASE_URL}/api/v1/odr/orders/bulk/"

    payload = [] 

    for order in orderlist:
        payload.append({
            "symbol": symbol,
            "base_amount": order["base_amount"],
            "price": order["price"],
            "side": order["side"],
            "type": order.get("type", "limit"),
        })

    ids = []

    rsp = requests.post(url, json=payload, headers=get_valid_header())
    if rsp.status_code in (200, 201):
        result = rsp.json()
        orders_result = result.get("orders", [])
        print(f"Bulk-Order registered successfully: {len(orders_result)}")

        for i, order in enumerate(orders_result):
            order_id     = order["id"]
            order_symb   = order["symbol"]
            order_side   = order["side"]
            order_price  = order["price"]
            order_amount = order["base_amount"]
            order_state  = order["state"]
            order_date   = order["created_at"]
            order_type   = order["type"]
    
            print(50 * "-")
            print(f"Order: {i + 1}")
            print(50 * "-")

            if order_side == "sell":
                give_color = toRed
            else:
                give_color = toGreen
    
            print(f"Order Kind:  {toYellow(order_type)}")
            print(f"Order ID:    {order_id}")
            print(f"Symbol:      {order_symb}")
            print(f"Side:        {give_color(order_side)}")
            print(f"Price:       {toPurple(order_price)}")
            print(f"Amount:      {order_amount}")
            print(f"Status:      {order_state}")
            print(f"Created At:  {order_date}")
            print(50 * "-")

            ids.append(order_id)
        
        return ids
    
    else:
        print(f"❌ ERROR: Bulk-Order placement met with failure with code {rsp.status_code}")
        print(f"Detail: {rsp.text}")
        return []

def get_active_orders(symbol=None, verbose:bool=True):
    endpoint = "/api/v1/odr/orders/?state=active"

    if symbol:
        endpoint += f"&symbol={symbol}"

    orders = fetch_data(endpoint)
    
    if not orders:
        return []

    if verbose:
        print(f"{len(orders)} Order was found")
        print(100 * "-")

        print(" #)      ID    |  Symbol  | Side | State |    Amount    |    Price    |        Datetime  ")
        print(100 * "-")
        
        for i, odr in enumerate(orders):
            print(f" {i + 1}) {odr["id"]} | {odr["symbol"]} | {odr["side"]} | {odr["state"]} | {odr["base_amount"]} | {odr["price"]} | {odr["created_at"]}")
        
    return orders

def get_order_history(symbol=None, limit=20, verbose:bool=True):
    endpoint = f"/api/v1/odr/orders/?limit={limit}"

    if symbol:
        endpoint += f"&symbol={symbol}"

    rsp = fetch_data(endpoint)
    
    if not rsp:
        print(f"No Order-History found")
        return []

    if verbose:
        print(f"{len(rsp)} Order-History was found")
        print(100 * "-")

        print(" #)     ID      |  Symbol  | Side | State |   Amount   | Cancel Request |   Datetime")
        print(100 * "-")

        for i, odr in enumerate(rsp):
            _id = odr.get("id", "unknown")
            state = odr.get("id", "unknown")
            sym = odr.get("symbol", "unknown")
            side = odr.get("side", "unknown")
            amount = odr.get("base_amount", "unknown")
            is_cancel = odr.get("req_to_cancel", "unknown")
            close_time = odr.get("closed_at", "unknown")
            print(f" {i + 1}) {_id} | {sym} | {side} | {state} | {amount} | {is_cancel} | {close_time}")
    
    return rsp

def cancel_order(order_id):
    url = f"{BASE_URL}/api/v1/odr/orders/{order_id}/"

    rsp = requests.delete(url, headers=get_valid_header())

    success = False
    print("*"*45)
    
    if rsp.status_code == 204:
        print(f"🗑️ Order \033[91m{order_id}\033[0m deleted successfully")
        print("✅ Funds are now unfreezed")
        success = True
    else:
        print(f"❌ ERROR: Order \033[91m{order_id}\033[0m couldn't get deleted")
        
    print("*"*45)

    return success

def get_withdraw_history(currency=None, limit=10):
    endpoint = f"/api/v1/wlt/withdraws/by-currency-code/"

    if currency:
        endpoint += f"?currency={currency}"
    
    rsp = fetch_data(endpoint)

    if not rsp or not (records:=rsp.get("results", [])):
        print(f"No Withdraw-History found for {currency if currency else "all currencies"}")
        return []
    
    print(f"{len(records)} Withdraw-History was found for {currency if currency else "all currencies"}")
    print(60 * "-")
    print(" #)     ID       | Amount |  Address  |     Datetime")
    print(60 * "-")

    for i, record in enumerate(records):
        if (i + 1 > limit):
            break
        print(f" {i + 1})   {record["id"]}   | {record["amount"]} | {record["address"]} | {record["closed_at"]}")

    return records

def get_commission(symbol):
    data = fetch_data("/api/v1/mkt/commissions/")

    taker_fee = None
    maker_free = None

    if data:

        commission = pd.DataFrame(data)
        commission.drop(["market"], axis=1, inplace=True)
        commission.set_index("symbol", inplace=True)
        return commission

        for i in data:

            if i["symbol"] == symbol:
                taker_fee = i["taker"]
                maker_free = i["maker"]
                break

        if taker_fee is None:
            print("❌ ERROR: getting the commission met with failure")
            return None

        commission = {
            "taker": taker_fee,
            "maker": maker_free
        }

        return commission

    else:
        print("❌ ERROR: getting the commission met with failure")
        return None
