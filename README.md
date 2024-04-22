# Kite-Trader

Unofficial Python library for Zerodha Kite with built-in throttling, so you never exceed Kite's API limits.

If you :heart: my work so far, please :star2: this repo.

## Installation

Supports Python version >= 3.8

`pip install kitetrader`

## Breaking changes in v3.0.0: 22nd April 2024

Methods return the entire JSON response unmodified. Previously only the `data` portion of the response was returned.

This allows the library user to code defensively. For example the trying to access `data` on the below response would result in a KeyError.

```
{
    "status": "error",
    "message": "Error message",
    "error_type": "GeneralException"
}
```

User can instead check if `response['status'] == 'success'` before accessing the `data` key. Otherwise log the error.

## Usage

```python
from kitetrader import Kite

# Using with statement (context manager)
with Kite() as kite:
  kite.profile() # user profile
  kite.holdings() # user portfolio

# or
kite = Kite()
kite.profile()
kite.holdings()

# close the requests session
kite.close()
```

## Login

**Update v2.2.0 - 19th April 2024** - Support both KiteConnect login and Web login

**For KiteConnect login:**

1. Pass the `api_key`, `api_secret` and `request_token` during initialization. Once authorized, the `access_token` can be accessed as `kite.access_token`

```python
kite = Kite(
    api_key=credentials['api_key'],
    api_secret=credentials['api_secret'],
    request_token=credentials['request_token'],
)

# On successful authentication, save the kite.access_token to database or file
# for future use
print(kite.access_token)
```

2. On subsequent attempts, simply pass the `access_token` and `api_key`

```python
kite = Kite(
    access_token=credentials["access_token"],
    api_key=credentials["api_key"],
)
```

**For Web Login:**

1. Web login is the default, if no arguments are passed. It will start an interactive prompt, requesting `user_id`, `password` and `twofa`.

```python
# Interactive prompt
kite = Kite()

# Once auth is completed, save the enctoken for later use
print(kite.enctoken)
```

2. You may pass some or all three arguments. Any missing info, will need to be entered, when prompted.

```python
kite = Kite(
    user_id: credentials['user_id'],
    password: credentials['password'],
    twofa: twofa,
)
```

3. On successful authorization, the enctoken is saved to a cookie file. On subsequent attempts, the `enctoken` is loaded from the cookie file.

4. Using the web login, will log you out of any Kite web browser sessions. You can reuse the browser `enctoken`, passing it to Kite. This way, you can use Kite Web, without getting logged out.

`kite = Kite(enctoken=credentials['enctoken'])`

To access the browser `enctoken`, login to kite.zerodha.com and press `SHIFT + F9` to open the Storage inspector (On Firefox). You will find the info under cookies.

## IMPORTANT NOTES and WARNINGs

- Hard coding password and credentials can be risky. Take appropriate measure to safeguard your credentials from accidental uploads or exposure on shared computers. Stick to defaults or use enctoken if unsure.

- Web login credentials are meant to be used on your PC (For personal use). Use of Web login credentials on a public facing server can put your account at high risk.

- Methods may raise the following errors:
  - A `RuntimeError` is raised if too many (>15) 429 reponse codes are returned.
  - A `TimeoutError` is raised if server takes too long to respond.
  - A `ConnectionError` is raised if:
    - Session expired
    - Bad request or invalid parameters
    - Internal server error

## Available Methods

Almost all methods defined on the Kite Connect 3 api have been covered except Webhooks and Websocket streaming. You can refer to the [Kite Connect Docs](https://kite.trade/docs/connect/v3/) for more information

```python
# User
kite.profile()
kite.margins(segment=kite.MARGIN_EQUITY) # or kite.MARGIN_COMMODITY

# Portfolio
kite.holdings() # long-term holdings
kite.positions() # short-term positions
kite.auctions() # list all auctions

# Orders
kite.orders() # list all orders for the day
kite.order_history('171229000724687') # order_id
kite.trades() # list all executed trades
kite.order_trades('171229000724687') # order_id

kite.place_order(kite.VARIETY_REGULAR,
                 kite.EXCHANGE_NSE,
                 'INFY',
                 kite.TRANSACTION_TYPE_BUY,
                 1,
                 kite.PRODUCT_NRML,
                 kite.ORDER_TYPE_MARKET) # Buy INFY at market price from NSE with product type NRML

kite.modify_order(kite.VARIETY_REGULAR, '171229000724687', 5) # order_id with quantity 5

kite.cancel_order(kite.VARIETY_REGULAR, '171229000724687')
```

### Market Quotes

```python
# Get the full market quotes - ohlc, OI, bid/ask, etc

instruments = ['NSE:INFY', 'NSE:RELIANCE', 'NSE:HDFCBANK', 'NSE:TCS']

kite.quote(instruments) # accepts list or a single string

# or

kite.quote('NSE:INFY')

kite.ohlc(instruments) # Get OHLCV and last traded price

kite.ltp(instruments) # Last traded price of all instruments
```

### Historical Candle data

```python
from kitetrader import Kite
from pandas import DataFrame, to_datetime
from datetime import datetime

'''An example to load historical candle data in Pandas DataFrame'''

def to_dataframe(data, oi=False):
    '''Returns a pandas DataFrame with Date as Index'''

    columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']

    if oi:
        columns.append('OpenInterest')

    df = DataFrame(data, columns=columns)

    df['Date'] = to_datetime(df['Date'])
    return df.set_index('Date')


from_dt = datetime(2023, 10, 4, 9, 15)
to_dt = datetime(2023, 10, 4, 15, 30)
instrument_token = '8979970' # banknifty oct futures

with Kite() as kite:
    data = kite.historical_data(instrument_token,
                                from_dt,
                                to_dt,
                                interval='15minute', oi=True)

df = to_dataframe(data, oi=True)

print(df.head())

df.to_csv(kite.base_dir / 'BANKNIFTY_OCT_FUT.csv')
```

### Instruments

Instruments method will return a dump of all tradable instruments. This is a large file of 7MB with 10k+ records. Only download what is required by specifying the exchange.

```python
from kitetrader import Kite
from io import BytesIO
from pandas import read_csv

'''Example to load and save instruments to csv file. '''

with Kite() as kite:
    # returns data in binary format
    data = kite.instruments(kite.EXCHANGE_NSE)

# Save as csv file using pathlib.path
(kite.base_dir / 'instruments.csv').write_bytes(data)

# or using file open with write binary
with open('instruments.csv', 'wb') as f:
    f.write(data)

# To convert data to Pandas DataFrame
df = read_csv(BytesIO(data), index_col='tradingsymbol')

# or load the saved csv file as DataFrame
df = read_csv('instruments.csv', index_col='tradingsymbol')

# to query an instrument token
instrument_token = df.loc['INFY', 'instrument_token']
```

### Constants

The below contants have been defined on the Kite class. You can use them as arguments to the various methods.

```python
# Exchanges
EXCHANGE_NSE = "NSE"
EXCHANGE_BSE = "BSE"
EXCHANGE_NFO = "NFO"
EXCHANGE_CDS = "CDS"
EXCHANGE_BFO = "BFO"
EXCHANGE_MCX = "MCX"
EXCHANGE_BCD = "BCD"

# Products
PRODUCT_MIS = "MIS"
PRODUCT_CNC = "CNC"
PRODUCT_NRML = "NRML"
PRODUCT_CO = "CO"

# Order types
ORDER_TYPE_MARKET = "MARKET"
ORDER_TYPE_LIMIT = "LIMIT"
ORDER_TYPE_SLM = "SL-M"
ORDER_TYPE_SL = "SL"

# Varities
VARIETY_REGULAR = "regular"
VARIETY_CO = "co"
VARIETY_AMO = "amo"
VARIETY_ICEBERG = "iceberg"
VARIETY_AUCTION = "auction"

# Transaction type
TRANSACTION_TYPE_BUY = "BUY"
TRANSACTION_TYPE_SELL = "SELL"

# Validity
VALIDITY_DAY = "DAY"
VALIDITY_IOC = "IOC"
VALIDITY_TTL = "TTL"

# Position Type
POSITION_TYPE_DAY = "day"
POSITION_TYPE_OVERNIGHT = "overnight"

# Margins segments
MARGIN_EQUITY = "equity"
MARGIN_COMMODITY = "commodity"

# GTT order type
GTT_TYPE_OCO = "two-leg"
GTT_TYPE_SINGLE = "single"

# Status constants
STATUS_COMPLETE = "COMPLETE"
STATUS_REJECTED = "REJECTED"
STATUS_CANCELLED = "CANCELLED"

# GTT order status
GTT_STATUS_ACTIVE = "active"
GTT_STATUS_TRIGGERED = "triggered"
GTT_STATUS_DISABLED = "disabled"
GTT_STATUS_EXPIRED = "expired"
GTT_STATUS_CANCELLED = "cancelled"
GTT_STATUS_REJECTED = "rejected"
GTT_STATUS_DELETED = "deleted"
```

### API limits and Throttling

When making large number of requests its essential to respect the [API limits set by Zerodha](https://kite.trade/docs/connect/v3/exceptions/#api-rate-limit).

The Throttle class ensures you do not exceed these limits. Its takes two arguments - a dictionary configuration and an integer max_penalty_count.

The `max_penalty_count` is maximum number of 429 HTTP error code, allowed to be returned during a session. Exceeding this limit will result in a runtime error.

The configuration is a dictionary which defines the limits for each endpoint. Here, `RPS` stands for Requests Per Second and`RPM` stands for Requests Per Minute. Limits are set for each end point.

```python
throttle_config = {
    'quote': {
        'rps': 1,
    },
    'historical': {
        'rps': 3,
    },
    'order': {
        'rps': 8,
        'rpm': 180,
    },
    'default': {
        'rps': 8,
    }
}

max_penalty_count = 15

th = Throttle(throttle_config, max_penalty_count)
```

### Class and Method signature

```python
class Kite(builtins.object)
 |  Kite(enctoken: Optional[str] = None)
 |  
 |  Unofficial implementation of Zerodha Kite api
 |  
 |  Methods defined here:
 |  
 |  __init__(self, user_id: Optional[str] = None, password: Optional[str] = None, twofa: Optional[str] = None, enctoken: Optional[str] = None)
 |      Initialize self.  See help(type(self)) for accurate signature.
 |  
 |  auctions(self)
 |      Retrieve the list of auctions that are currently being held
 |  
 |  cancel_order(self, variety, order_id)
 |      Cancel an order.
 |  
 |  close(self)
 |      Close the Requests session
 |  
 |  historical_data(self, instrument_token: str, from_dt: Union[datetime.datetime, str], to_dt: Union[datetime.datetime, str], interval: str, continuous=False, oi=False)
 |      return historical candle records for a given instrument.
 |  
 |  holdings(self)
 |      Return the list of long term equity holdings
 |  
 |  instruments(self, exchange: Optional[str] = None)
 |      return a CSV dump of all tradable instruments
 |  
 |  ltp(self, instruments: Union[str, collections.abc.Collection])
 |      Returns the last traded price
 |  
 |  margins(self, segment: Optional[str] = None)
 |      Returns funds, cash, and margin information for the user
 |      for equity and commodity segments
 |  
 |  modify_order(self, variety, order_id, quantity=None, price=None, order_type=None, trigger_price=None, validity=None, disclosed_quantity=None)
 |      Modify an open order.
 |  
 |  ohlc(self, instruments: Union[str, collections.abc.Collection])
 |      Returns ohlc and last traded price
 |  
 |  order_history(self, order_id)
 |      Get history of individual orders
 |  
 |  order_trades(self, order_id)
 |      Get the the trades generated by an order
 |  
 |  orders(self)
 |      Get list of all orders for the day
 |  
 |  place_order(self, variety, exchange, tradingsymbol, transaction_type, quantity, product, order_type, price=None, validity=None, validity_ttl=None, disclosed_quantity=None, trigger_price=None, iceberg_legs=None, iceberg_quantity=None, auction_number=None, tag=None)
 |      Place an order of a particular variety
 |  
 |  positions(self)
 |      Retrieve the list of short term positions
 |  
 |  profile(self)
 |      Retrieve the user profile
 |  
 |  quote(self, instruments: Union[str, collections.abc.Collection])
 |      Return the full market quotes - ohlc, OI, bid/ask etc
 |  
 |  trades(self)
 |      Get the list of all executed trades for the day
 |  
 |  Data and other attributes defined here:
 |  
 |  EXCHANGE_BCD = 'BCD'
 |  
 |  EXCHANGE_BFO = 'BFO'
 |  
 |  EXCHANGE_BSE = 'BSE'
 |  
 |  EXCHANGE_CDS = 'CDS'
 |  
 |  EXCHANGE_MCX = 'MCX'
 |  
 |  EXCHANGE_NFO = 'NFO'
 |  
 |  EXCHANGE_NSE = 'NSE'
 |  
 |  GTT_TYPE_OCO = 'two-leg'
 |  
 |  GTT_TYPE_SINGLE = 'single'
 |  
 |  MARGIN_COMMODITY = 'commodity'
 |  
 |  MARGIN_EQUITY = 'equity'
 |  
 |  ORDER_TYPE_LIMIT = 'LIMIT'
 |  
 |  ORDER_TYPE_MARKET = 'MARKET'
 |  
 |  ORDER_TYPE_SL = 'SL'
 |  
 |  ORDER_TYPE_SLM = 'SL-M'
 |  
 |  POSITION_TYPE_DAY = 'day'
 |  
 |  POSITION_TYPE_OVERNIGHT = 'overnight'
 |  
 |  PRODUCT_CNC = 'CNC'
 |  
 |  PRODUCT_CO = 'CO'
 |  
 |  PRODUCT_MIS = 'MIS'
 |  
 |  PRODUCT_NRML = 'NRML'
 |  
 |  TRANSACTION_TYPE_BUY = 'BUY'
 |  
 |  TRANSACTION_TYPE_SELL = 'SELL'
 |  
 |  VALIDITY_DAY = 'DAY'
 |  
 |  VALIDITY_IOC = 'IOC'
 |  
 |  VALIDITY_TTL = 'TTL'
 |  
 |  VARIETY_AMO = 'amo'
 |  
 |  VARIETY_AUCTION = 'auction'
 |  
 |  VARIETY_CO = 'co'
 |  
 |  VARIETY_ICEBERG = 'iceberg'
 |  
 |  VARIETY_REGULAR = 'regular'
 |  
```
