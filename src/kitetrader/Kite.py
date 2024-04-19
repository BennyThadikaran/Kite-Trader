from collections.abc import Collection
from typing import Optional, Union, Any
from requests import Session
from requests.exceptions import ReadTimeout
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
from pathlib import Path
from mthrottle import Throttle
from datetime import datetime
import pickle, hashlib, logging


throttle_config = {
    "quote": {
        "rps": 1,
    },
    "historical": {
        "rps": 3,
    },
    "order": {
        "rps": 8,
        "rpm": 180,
    },
    "default": {
        "rps": 8,
    },
}

th = Throttle(throttle_config, 15)


def configure_default_logger(name):
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    return logging.getLogger(name)


class Kite:
    """Unofficial implementation of Zerodha Kite api"""

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

    base_dir = Path(__file__).parent
    base_url = "https://api.kite.trade"
    cookies = None
    config = None

    def __init__(
        self,
        user_id: Optional[str] = None,
        password: Optional[str] = None,
        twofa: Optional[str] = None,
        enctoken: Optional[str] = None,
        access_token: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        request_token: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):

        self.cookie_path = self.base_dir / "kite_cookies"

        self.session = Session()
        self.session.headers.update({"X-Kite-version": "3"})

        self.enctoken = enctoken
        self.access_token = access_token

        retries = Retry(
            total=None,
            connect=3,
            read=3,
            redirect=0,
            status=3,
            other=0,
            backoff_factor=0.1,
            status_forcelist=[502, 503, 504],
            raise_on_status=False,
        )

        self.session.mount("https://", HTTPAdapter(max_retries=retries))

        self.log = logger if logger else configure_default_logger(__name__)

        if self.enctoken:
            return self._set_enc_token(self.enctoken)

        if self.access_token:
            if not api_key:
                raise ValueError(
                    "api_key is required, when access_token is passed"
                )

            return self._set_access_token(api_key, self.access_token)

        if self.cookie_path.exists():
            self.cookies = self._get_cookie()

            # get enctoken from cookies
            self.enctoken = self.cookies.get("enctoken")

            if self.enctoken:
                return self._set_enc_token(self.enctoken)

        # initiate login
        self._authorize(
            user_id, password, twofa, api_key, request_token, api_secret
        )

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.session.close()
        return False

    def _set_enc_token(self, token):
        self.session.headers.update({"Authorization": f"enctoken {token}"})
        self.log.info("Auth headers updated with enctoken")

    def _set_access_token(self, api_key, token):
        self.session.headers.update(
            {"Authorization": f"token {api_key}:{token}"}
        )
        self.log.info("Auth headers updated with access_token")

    def close(self):
        """Close the Requests session"""

        self.session.close()

    def _get_cookie(self):
        """Load the pickle format cookie file"""

        return pickle.loads(self.cookie_path.read_bytes())

    def _set_cookie(self, cookies):
        """Save the cookies to pickle formatted file"""

        self.cookie_path.write_bytes(pickle.dumps(cookies))

    def _req(self, url, method, payload=None, timeout=15, hint=None) -> Any:
        """Make an HTTP request"""

        try:
            if method == "PUT":
                r = self.session.put(url, data=payload, timeout=timeout)
            elif method == "DELETE":
                r = self.session.delete(url)
            elif method == "POST":
                r = self.session.post(url, data=payload, timeout=timeout)
            else:
                r = self.session.get(url, params=payload, timeout=timeout)

        except ReadTimeout:
            raise TimeoutError(f"{hint} | Request timed out")

        if r.ok:
            return r

        code = r.status_code

        if code == 429:
            if th.penalise():
                raise RuntimeError(f"{code}: {r.reason}")

        if code == 403:
            if self.cookie_path.exists():
                self.cookie_path.unlink()

            reason = "Session expired or invalid. Must relogin"
            raise ConnectionError(f"{hint} | {code}: {reason}")

        if code == 400:
            reason = "Missing or bad request parameters or values"
            raise ConnectionError(f"{hint} | {code}: {reason}")

        raise ConnectionError(f"{hint} | {code}: {r.reason}")

    def _authorize(
        self,
        user_id: Optional[str] = None,
        password: Optional[str] = None,
        twofa: Optional[str] = None,
        api_key: Optional[str] = None,
        request_token: Optional[str] = None,
        secret: Optional[str] = None,
    ):
        """Authenthicate the user"""

        login_url = "https://kite.zerodha.com"

        if request_token and secret:
            # API LOGIN
            if not api_key:
                raise ValueError("No api_key provided during initialization")

            checksum = hashlib.sha256(
                f"{api_key}{request_token}{secret}".encode("utf-8")
            ).hexdigest()

            response = self._req(
                f"{login_url}/session/token",
                "POST",
                payload={
                    "api_key": api_key,
                    "request_token": request_token,
                    "checksum": checksum,
                },
                hint="API_LOGIN",
            ).json()

            self.access_token = response["access_token"]
            self.log.info("KiteConnect login success")
            return self._set_access_token(api_key, self.access_token)

        # WEB LOGIN
        if not user_id:
            user_id = input("Enter User id\n> ")

        if not password:
            password = input("Enter Password\n> ")

        response = self._req(
            f"{login_url}/api/login",
            "POST",
            payload=dict(user_id=user_id, password=password),
            hint="WEB_LOGIN",
        ).json()

        request_id = response["data"]["request_id"]
        twofa_type = response["data"]["twofa_type"]

        if not twofa:
            twofa = input(f"Please enter {twofa_type} code\n> ")

        response = self._req(
            f"{login_url}/api/twofa",
            "POST",
            payload=dict(
                user_id=user_id,
                request_id=request_id,
                twofa_value=twofa,
                twofa_type=twofa_type,
                skip_session="",
            ),
            hint="TwoFA",
        )

        self.enctoken = response.cookies["enctoken"]
        self._set_cookie(response.cookies)

        self._set_enc_token(self.enctoken)

        self.log.info("Web Login Succces")

    def instruments(self, exchange: Optional[str] = None):
        """return a CSV dump of all tradable instruments"""

        th.check()
        url = f"{self.base_url}/instruments"

        if exchange:
            url += f"/{exchange}"

        return self._req(url, "GET", hint="Instruments")

    def quote(self, instruments: Union[str, Collection]):
        """Return the full market quotes - ohlc, OI, bid/ask etc"""

        if not isinstance(instruments, str) and len(instruments) > 500:
            raise ValueError("Instruments length cannot exceed 500")

        th.check("quote")

        res = self._req(
            f"{self.base_url}/quote",
            "GET",
            payload={"i": instruments},
            hint="Quote",
        )

        return res.json()["data"]

    def ohlc(self, instruments: Union[str, Collection]):
        """Returns ohlc and last traded price"""

        if not isinstance(instruments, str) and len(instruments) > 1000:
            raise ValueError("Instruments length cannot exceed 1000")

        th.check("quote")

        res = self._req(
            f"{self.base_url}/quote/ohlc",
            method="GET",
            payload={"i": instruments},
            hint="Quote/OHLC",
        )

        return res.json()["data"]

    def ltp(self, instruments: Union[str, Collection]):
        """Returns the last traded price"""

        if not isinstance(instruments, str) and len(instruments) > 1000:
            raise ValueError("Instruments length cannot exceed 1000")

        th.check("quote")

        return self._req(
            f"{self.base_url}/quote/ltp",
            method="GET",
            payload={"i": instruments},
            hint="LTP",
        ).json()["data"]

    def holdings(self):
        """Return the list of long term equity holdings"""

        th.check()

        return self._req(
            f"{self.base_url}/portfolio/holdings",
            method="GET",
            hint="Portfolio/holdings",
        ).json()["data"]

    def positions(self):
        """Retrieve the list of short term positions"""

        th.check()

        return self._req(
            f"{self.base_url}/portfolio/positions",
            method="GET",
            hint="Portfolio/positions",
        ).json()["data"]

    def auctions(self):
        """Retrieve the list of auctions that are currently being held"""

        th.check()

        return self._req(
            f"{self.base_url}/portfolio/auctions",
            method="GET",
            hint="Portfolio/auctions",
        ).json()["data"]

    def margins(self, segment: Optional[str] = None):
        """Returns funds, cash, and margin information for the user
        for equity and commodity segments"""

        url = f"{self.base_url}/user/margins"

        if segment:
            url += f"/{segment}"

        th.check()

        return self._req(url, method="GET", hint="Margins").json()["data"]

    def profile(self):
        """Retrieve the user profile"""

        th.check()

        return self._req(
            f"{self.base_url}/user/profile", "GET", hint="Profile"
        ).json()["data"]

    def historical_data(
        self,
        instrument_token: str,
        from_dt: Union[datetime, str],
        to_dt: Union[datetime, str],
        interval: str,
        continuous=False,
        oi=False,
    ):
        """return historical candle records for a given instrument."""

        url = f"{self.base_url}/instruments/historical/{instrument_token}/{interval}"

        if isinstance(from_dt, str):
            from_dt = datetime.fromisoformat(from_dt)

        if isinstance(to_dt, str):
            to_dt = datetime.fromisoformat(to_dt)

        payload = {
            "from": from_dt,
            "to": to_dt,
            "continuous": int(continuous),
            "oi": int(oi),
        }

        th.check("historical")

        return self._req(
            url, method="GET", payload=payload, hint="Historical"
        ).json()["data"]["candles"]

    def place_order(
        self,
        variety,
        exchange,
        tradingsymbol,
        transaction_type,
        quantity,
        product,
        order_type,
        price=None,
        validity=None,
        validity_ttl=None,
        disclosed_quantity=None,
        trigger_price=None,
        iceberg_legs=None,
        iceberg_quantity=None,
        auction_number=None,
        tag=None,
    ):
        """Place an order of a particular variety"""

        params = {k: v for k, v in locals().items() if v is not None}

        params.pop("self")

        th.check("order")

        return self._req(
            f"{self.base_url}/orders/{variety}",
            "POST",
            payload=params,
            hint="Place Order",
        ).json()["data"]["order_id"]

    def modify_order(
        self,
        variety,
        order_id,
        quantity=None,
        price=None,
        order_type=None,
        trigger_price=None,
        validity=None,
        disclosed_quantity=None,
    ):
        """Modify an open order."""

        params = {k: v for k, v in locals().items() if v is not None}

        params.pop("self")

        th.check("order")

        return self._req(
            f"{self.base_url}/orders/{variety}/{order_id}",
            "PUT",
            payload=params,
            hint="Modify order",
        ).json()["data"]["order_id"]

    def cancel_order(self, variety, order_id):
        """Cancel an order."""

        url = f"{self.base_url}/orders/{variety}/{order_id}"

        th.check("order")

        return self._req(url, "DELETE", hint="Cancel order").json()["data"]

    def orders(self):
        """Get list of all orders for the day"""

        th.check("order")

        return self._req(
            f"{self.base_url}/orders", "GET", hint="Orders"
        ).json()["data"]

    def order_history(self, order_id):
        """Get history of individual orders"""

        url = f"{self.base_url}/orders/{order_id}"

        th.check("order")

        return self._req(url, "GET", hint="Order history").json()["data"]

    def trades(self):
        """Get the list of all executed trades for the day"""

        url = f"{self.base_url}/trades"

        th.check()

        return self._req(url, "GET", hint="Trades").json()["data"]

    def order_trades(self, order_id):
        """Get the the trades generated by an order"""

        url = f"{self.base_url}/orders/{order_id}/trades"

        th.check("orders")

        return self._req(url, "GET", hint="Order Trades").json()["data"]
