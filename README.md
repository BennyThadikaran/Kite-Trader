# Kite-Trader

Unofficial Python Client for Zerodha Kite with built-in request throttling so you never exceed Kite's API limits.

If you :heart: my work so far, please :star2: this repo.

## Installation

Download or clone the repository.

Install the dependencies: `pip install requests`

## Usage

```python
from Kite import Kite

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

`kite = Kite()`

On first initialization, Kite will check for user authentication. If no arguments are provided, the script prompts for username, password, and OTP.

On successful login, an `enctoken` is generated and stored in a cookie file.

If the cookie file exists on subsequent initialization, the `enctoken` is reused, eliminating the need to log in again.

This method will logout all Kite web (browser) sessions. (You can continue to use the Kite Mobile App).

**Passing credentials file path**

You could store your username and password in a JSON file and pass the file path as an argument to Kite. You will only need to input the OTP.

`kite = Kite(credentials_path='/home/Ashok/.config/Kite/credentials.json')`

```json
{
  "user_id": "<YOUR USER ID>",
  "password": "<YOUR PASSWORD>"
}
```

**WARNING**: Do not store the credentials.json in the repository folder or on your Desktop. Do not use this option unless you alone have access to the computer.
There is always the risk of exposing your credentials.

**Passing a enctoken**

You can reuse the browser `enctoken`, passing it to Kite. This way, you can use Kite-Trader without getting logged out.

`kite = Kite(enctoken='<token string>')`

To access the browser `enctoken`, login to kite.zerodha.com and press `SHIFT + F9` to open the Storage inspector (On Firefox). You will find the info under cookies.

## Available Methods

Almost all methods defined on the Kite Connect 3 api have been covered except Webhooks and Websocket streaming. You can refer to the [Kite Connect Docs](https://kite.trade/docs/connect/v3/) for more information

**NOTE** The methods may return None in case of API or network errors. Be sure take this into consideration when writing your scripts.

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
from Kite import Kite
from pandas import DataFrame, to_datetime

'''An example to load historical candle data in Pandas DataFrame'''

def to_dataframe(data, oi=False):
    '''Returns a pandas DataFrame with Date as Index'''

    columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']

    if oi:
        columns.append('OpenInterest')

    df = DataFrame(data, columns=columns)

    df['Date'] = to_datetime(df['Date'])
    return df.set_index('Date')


from_dt = '2023-10-04 09:15:00'
to_dt = '2023-10-04 15:30:00'
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
from Kite import Kite
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
```

### API limits and Throttling
When making large number of requests its essential to respect the [API limits set by Zerodha](https://kite.trade/docs/connect/v3/exceptions/#api-rate-limit).

The Throttle class ensures you do not exceed these limits.

In the `Kite.py` file you will find the `throttle_config` dictionary which defines the limits. I have set the limits conservatively. You can free to experiment with these values.

Here, `RPS` stands for requests per second and`RPM` stands for requests per minute. Limits are set for each end point.

When the API limits are exceeded, a 429 HTTP status code is returned. If the limits are exceeded too many times during the lifetime of a session, a runtime error is thrown.

Current limit is 15.
