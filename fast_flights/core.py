import re
import json
from typing import List, Literal, Optional, Union, overload

from selectolax.lexbor import LexborHTMLParser, LexborNode

from .decoder import DecodedResult, ResultDecoder
from .schema import Flight, Result
from .flights_impl import FlightData, Passengers
from .filter import TFSData
from .fallback_playwright import fallback_playwright_fetch
from .bright_data_fetch import bright_data_fetch
from .primp import Client, Response


DataSource = Literal['html', 'js']

def fetch(params: dict) -> Response:
    client = Client(impersonate="chrome_126", verify=False)
    res = client.get("https://www.google.com/travel/flights", params=params)
    assert res.status_code == 200, f"{res.status_code} Result: {res.text_markdown}"
    return res

@overload
def get_flights_from_filter(
    filter: TFSData,
    currency: str = "",
    *,
    mode: Literal["common", "fallback", "force-fallback", "local", "bright-data"] = "common",
    data_source: Literal['js'] = ...,
) -> Union[DecodedResult, None]: ...

@overload
def get_flights_from_filter(
    filter: TFSData,
    currency: str = "",
    *,
    mode: Literal["common", "fallback", "force-fallback", "local", "bright-data"] = "common",
    data_source: Literal['html'],
) -> Result: ...

def get_flights_from_filter(
    filter: TFSData,
    currency: str = "",
    *,
    mode: Literal["common", "fallback", "force-fallback", "local", "bright-data"] = "common",
    data_source: DataSource = 'html',
) -> Union[Result, DecodedResult, None]:
    data = filter.as_b64()

    params = {
        "tfs": data.decode("utf-8"),
        "hl": "en",
        "tfu": "EgQIABABIgA",
        "curr": currency,
    }

    if mode in {"common", "fallback"}:
        try:
            res = fetch(params)
        except AssertionError as e:
            if mode == "fallback":
                res = fallback_playwright_fetch(params)
            else:
                raise e

    elif mode == "local":
        from .local_playwright import local_playwright_fetch

        res = local_playwright_fetch(params)

    elif mode == "bright-data":
        res = bright_data_fetch(params)

    else:
        res = fallback_playwright_fetch(params)

    try:
        return parse_response(res, data_source)
    except RuntimeError as e:
        if mode == "fallback":
            return get_flights_from_filter(filter, mode="force-fallback")
        raise e


def get_flights(
    *,
    flight_data: List[FlightData],
    trip: Literal["round-trip", "one-way", "multi-city"],
    passengers: Passengers,
    seat: Literal["economy", "premium-economy", "business", "first"],
    fetch_mode: Literal["common", "fallback", "force-fallback", "local", "bright-data"] = "common",
    max_stops: Optional[int] = None,
    data_source: DataSource = 'html',
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
    )


_DAY_ABBREVS = {
    'Monday': 'Mon', 'Tuesday': 'Tue', 'Wednesday': 'Wed',
    'Thursday': 'Thu', 'Friday': 'Fri', 'Saturday': 'Sat', 'Sunday': 'Sun',
}
_MONTH_ABBREVS = {
    'January': 'Jan', 'February': 'Feb', 'March': 'Mar', 'April': 'Apr',
    'May': 'May', 'June': 'Jun', 'July': 'Jul', 'August': 'Aug',
    'September': 'Sep', 'October': 'Oct', 'November': 'Nov', 'December': 'Dec',
}


def _shorten_date(date_str: str) -> str:
    """Convert 'Sunday, February 15' to 'Sun, Feb 15'."""
    for full, abbr in _DAY_ABBREVS.items():
        date_str = date_str.replace(full, abbr)
    for full, abbr in _MONTH_ABBREVS.items():
        date_str = date_str.replace(full, abbr)
    return date_str


def _parse_aria_label(label: str) -> dict:
    """Extract flight fields from aria-label when CSS selectors fail.

    Google always includes structured flight data in aria-label attributes
    regardless of how it obfuscates CSS class names per browser fingerprint.
    """
    result = {}
    m = re.search(r'flight with (.+?)\.\s*Leaves', label)
    result['name'] = m.group(1) if m else ""
    m = re.search(r'Leaves .+ at (\d+:\d+\s*(?:AM|PM)) on (.+?) and arrives', label)
    if m:
        time_str, date_str = m.group(1), m.group(2)
        result['departure'] = f"{re.sub(r'\\s+', ' ', time_str)} on {_shorten_date(date_str)}"
    else:
        result['departure'] = ""
    m = re.search(r'arrives .+ at (\d+:\d+\s*(?:AM|PM)) on (.+?)\.\s*Total', label)
    if m:
        time_str, date_str = m.group(1), m.group(2)
        result['arrival'] = f"{re.sub(r'\\s+', ' ', time_str)} on {_shorten_date(date_str)}"
    else:
        result['arrival'] = ""
    m = re.search(r'Total duration (.+?)\.', label)
    result['duration'] = m.group(1) if m else ""
    m = re.search(r'(Nonstop|\d+ stops?)\s+flight', label)
    if m:
        stops_text = m.group(1)
        result['stops'] = 0 if stops_text == "Nonstop" else int(stops_text.split()[0])
    else:
        result['stops'] = "Unknown"
    return result


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

    if data_source == 'js':
        script = parser.css_first(r'script.ds\:1').text()

        match = re.search(r'^.*?\{.*?data:(\[.*\]).*\}', script)
        assert match, 'Malformed js data, cannot find script data'
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

            # Fallback: if CSS selectors missed any key fields, parse from aria-label.
            # Google obfuscates class names differently per browser fingerprint, but
            # aria-label always contains structured flight data.
            if not name or not departure_time or not arrival_time or not duration or stops_fmt == "Unknown":
                aria = item.attributes.get("aria-label", "") or ""
                if not aria or "flight" not in aria:
                    aria_el = item.css_first("[aria-label*='flight']")
                    if aria_el:
                        aria = aria_el.attributes.get("aria-label", "") or ""
                if aria and "flight" in aria:
                    parsed = _parse_aria_label(aria)
                    if not name:
                        name = parsed.get('name', '')
                    if not departure_time:
                        departure_time = parsed.get('departure', '')
                    if not arrival_time:
                        arrival_time = parsed.get('arrival', '')
                    if not duration:
                        duration = parsed.get('duration', '')
                    if stops_fmt == "Unknown":
                        stops_fmt = parsed.get('stops', 'Unknown')

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
