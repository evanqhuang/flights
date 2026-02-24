import re
import json
from dataclasses import dataclass
from typing import List, Literal, Optional, Union, overload

from selectolax.lexbor import LexborHTMLParser, LexborNode
from playwright.async_api import ProxySettings

from .decoder import DecodedResult, ResultDecoder
from .schema import Flight, Result
from .flights_impl import FlightData, Passengers
from .filter import TFSData
from .fallback_playwright import fallback_playwright_fetch
from .bright_data_fetch import bright_data_fetch
from .primp import Client, Response
from .cookies_impl import Cookies


DataSource = Literal["html", "js"]


@dataclass
class PlaywrightConfig:
    """Configuration for Playwright browser automation.

    Args:
        url: WebSocket endpoint (ws:// or wss://) for remote Playwright instance.
        proxy: Optional proxy configuration with server, username, password.
    """

    url: str
    proxy: Optional[ProxySettings] = None


@dataclass
class PrimpConfig:
    """Configuration for primp HTTP client.

    Args:
        proxy: Optional proxy URL string (e.g., "socks5://127.0.0.1:9150",
               "http://user:pass@proxy:8080").
    """
    proxy: Optional[str] = None


def fetch(params: dict, primp_config: Optional[PrimpConfig] = None, impersonate: str = "chrome_128") -> Response:
    proxy = primp_config.proxy if primp_config else None
    cookies = Cookies.new(locale="en").to_dict()
    client = Client(impersonate=impersonate, verify=False, proxy=proxy)
    res = client.get("https://www.google.com/travel/flights", params=params, cookies=cookies)
    assert res.status_code == 200, f"{res.status_code} Result: {res.text_markdown}"
    return res


@overload
def get_flights_from_filter(
    filter: TFSData,
    currency: str = "",
    *,
    mode: Literal[
        "common", "fallback", "force-fallback", "local", "bright-data"
    ] = "common",
    data_source: Literal["js"] = ...,
    playwright_config: Optional[PlaywrightConfig] = None,
    primp_config: Optional[PrimpConfig] = None,
) -> Union[DecodedResult, None]: ...


@overload
def get_flights_from_filter(
    filter: TFSData,
    currency: str = "",
    *,
    mode: Literal[
        "common", "fallback", "force-fallback", "local", "bright-data"
    ] = "common",
    data_source: Literal["html"],
    playwright_config: Optional[PlaywrightConfig] = None,
    primp_config: Optional[PrimpConfig] = None,
) -> Result: ...


def get_flights_from_filter(
    filter: TFSData,
    currency: str = "",
    *,
    mode: Literal[
        "common", "fallback", "force-fallback", "local", "bright-data"
    ] = "common",
    data_source: DataSource = "html",
    playwright_config: Optional[PlaywrightConfig] = None,
    primp_config: Optional[PrimpConfig] = None,
) -> Union[Result, DecodedResult, None]:
    data = filter.as_b64()

    params = {
        "tfs": data.decode("utf-8"),
        "hl": "en",
        "tfu": "EgQIABABIgA",
        "curr": currency,
    }

    if mode in {"common", "fallback"}:
        res = None
        last_primp_error = None
        for fingerprint in ["chrome_128", "safari_17.5"]:
            try:
                res = fetch(params, primp_config, impersonate=fingerprint)
                break
            except AssertionError as e:
                last_primp_error = e

        if res is None:
            if mode == "fallback":
                playwright_url = playwright_config.url if playwright_config else None
                proxy = playwright_config.proxy if playwright_config else None
                res = fallback_playwright_fetch(params, playwright_url, proxy)
            else:
                raise last_primp_error

    elif mode == "local":
        from .local_playwright import local_playwright_fetch

        playwright_url = playwright_config.url if playwright_config else None
        proxy = playwright_config.proxy if playwright_config else None
        res = local_playwright_fetch(params, playwright_url, proxy)

    elif mode == "bright-data":
        res = bright_data_fetch(params)

    else:
        playwright_url = playwright_config.url if playwright_config else None
        proxy = playwright_config.proxy if playwright_config else None
        res = fallback_playwright_fetch(params, playwright_url, proxy)

    try:
        return parse_response(res, data_source)
    except RuntimeError as e:
        if mode == "fallback":
            return get_flights_from_filter(
                filter, mode="force-fallback", playwright_config=playwright_config, primp_config=primp_config
            )
        raise e


def get_flights(
    *,
    flight_data: List[FlightData],
    trip: Literal["round-trip", "one-way", "multi-city"],
    passengers: Passengers,
    seat: Literal["economy", "premium-economy", "business", "first"],
    fetch_mode: Literal[
        "common", "fallback", "force-fallback", "local", "bright-data"
    ] = "common",
    max_stops: Optional[int] = None,
    data_source: DataSource = "html",
    playwright_config: Optional[PlaywrightConfig] = None,
    primp_config: Optional[PrimpConfig] = None,
) -> Union[Result, DecodedResult, None]:
    return get_flights_from_filter(
        TFSData.from_interface(
            flight_data=flight_data,
            trip=trip,
            passengers=passengers,
            seat=seat,
            max_stops=max_stops,
        ),
        mode=fetch_mode,
        data_source=data_source,
        playwright_config=playwright_config,
        primp_config=primp_config,
    )


async def async_get_flights_with_page(
    *,
    flight_data: List[FlightData],
    trip: Literal["round-trip", "one-way", "multi-city"],
    passengers: Passengers,
    seat: Literal["economy", "premium-economy", "business", "first"],
    max_stops: Optional[int] = None,
    data_source: DataSource = "html",
    playwright_page=None,
) -> Union[Result, DecodedResult, None]:
    """Async entry point that uses a pre-acquired Playwright page.

    This function is designed for use with a PlaywrightContextPool.
    It skips primp and uses the provided page directly for fetching.
    """
    from .local_playwright import fetch_with_playwright_page

    tfs = TFSData.from_interface(
        flight_data=flight_data,
        trip=trip,
        passengers=passengers,
        seat=seat,
        max_stops=max_stops,
    )
    data = tfs.as_b64()
    params = {
        "tfs": data.decode("utf-8"),
        "hl": "en",
        "tfu": "EgQIABABIgA",
    }
    url = "https://www.google.com/travel/flights?" + "&".join(
        f"{k}={v}" for k, v in params.items()
    )

    body = await fetch_with_playwright_page(playwright_page, url)

    class DummyResponse:
        status_code = 200
        text = body
        text_markdown = body

    return parse_response(DummyResponse(), data_source)


def parse_response(
    r: Response,
    data_source: DataSource,
    *,
    dangerously_allow_looping_last_item: bool = False,
) -> Union[Result, DecodedResult, None]:
    class _blank:
        def text(self, *_, **__):
            return ""

        def iter(self):
            return []

    blank = _blank()

    def safe(n: Optional[LexborNode]):
        return n or blank

    parser = LexborHTMLParser(r.text)

    if data_source == "js":
        script = parser.css_first(r"script.ds\:1").text()

        match = re.search(r"^.*?\{.*?data:(\[.*\]).*\}", script)
        assert match, "Malformed js data, cannot find script data"
        data = json.loads(match.group(1))
        return ResultDecoder.decode(data) if data is not None else None

    flights = []

    for i, fl in enumerate(parser.css('div[jsname="IWWDBc"], div[jsname="YdtKid"]')):
        is_best_flight = i == 0

        for item in fl.css("ul.Rk10dc li")[
            : (None if dangerously_allow_looping_last_item or i == 0 else -1)
        ]:
            # Flight name
            name = safe(item.css_first("div.sSHqwe.tPgKwe.ogfYpf span")).text(
                strip=True
            )

            # Get departure & arrival time
            dp_ar_node = item.css("span.mv1WYe div")
            try:
                departure_time = dp_ar_node[0].text(strip=True)
                arrival_time = dp_ar_node[1].text(strip=True)
            except IndexError:
                # sometimes this is not present
                departure_time = ""
                arrival_time = ""

            # Get arrival time ahead
            time_ahead = safe(item.css_first("span.bOzv6")).text()

            # Get duration
            duration = safe(item.css_first("li div.Ak5kof div")).text()

            # Get flight stops
            stops = safe(item.css_first(".BbR8Ec .ogfYpf")).text()

            # Get delay
            delay = safe(item.css_first(".GsCCve")).text() or None

            # Get prices
            price = safe(item.css_first(".YMlIz.FpEdX")).text() or "0"

            # Stops formatting
            try:
                stops_fmt = 0 if stops == "Nonstop" else int(stops.split(" ", 1)[0])
            except ValueError:
                stops_fmt = "Unknown"

            flights.append(
                {
                    "is_best": is_best_flight,
                    "name": name,
                    "departure": " ".join(departure_time.split()),
                    "arrival": " ".join(arrival_time.split()),
                    "arrival_time_ahead": time_ahead,
                    "duration": duration,
                    "stops": stops_fmt,
                    "delay": delay,
                    "price": price.replace(",", ""),
                }
            )

    current_price = safe(parser.css_first("span.gOatQ")).text()
    if not flights:
        raise RuntimeError("No flights found:\n{}".format(r.text_markdown))

    return Result(current_price=current_price, flights=[Flight(**fl) for fl in flights])  # type: ignore
