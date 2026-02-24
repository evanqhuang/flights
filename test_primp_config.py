#!/usr/bin/env python3
"""
Comprehensive tests for PrimpConfig proxy functionality.

Tests verify that proxy configuration is properly created, passed through
the call chain, and actually used by the primp HTTP client.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from fast_flights import (
    FlightData,
    Passengers,
    PrimpConfig,
    get_flights,
    get_flights_from_filter,
    create_filter,
)
from fast_flights.core import fetch


class TestPrimpConfigCreation:
    """Test PrimpConfig dataclass instantiation."""

    def test_primp_config_with_proxy(self):
        """Test creating PrimpConfig with a proxy URL."""
        proxy_url = "socks5://127.0.0.1:9150"
        config = PrimpConfig(proxy=proxy_url)

        assert config.proxy == proxy_url
        assert isinstance(config, PrimpConfig)

    def test_primp_config_without_proxy(self):
        """Test creating PrimpConfig without a proxy (defaults to None)."""
        config = PrimpConfig()

        assert config.proxy is None
        assert isinstance(config, PrimpConfig)

    def test_primp_config_explicit_none(self):
        """Test creating PrimpConfig with explicit None."""
        config = PrimpConfig(proxy=None)

        assert config.proxy is None

    def test_primp_config_http_proxy(self):
        """Test creating PrimpConfig with HTTP proxy."""
        proxy_url = "http://proxy.example.com:8080"
        config = PrimpConfig(proxy=proxy_url)

        assert config.proxy == proxy_url

    def test_primp_config_authenticated_proxy(self):
        """Test creating PrimpConfig with authenticated proxy URL."""
        proxy_url = "http://user:pass@proxy.example.com:8080"
        config = PrimpConfig(proxy=proxy_url)

        assert config.proxy == proxy_url


class TestFetchWithPrimpConfig:
    """Test that fetch() properly uses PrimpConfig."""

    @patch('fast_flights.core.Client')
    def test_fetch_without_primp_config(self, mock_client_class):
        """Test fetch() without primp_config uses no proxy."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        # Call fetch without primp_config
        params = {"tfs": "test", "hl": "en"}
        result = fetch(params)

        # Verify Client was created without proxy
        mock_client_class.assert_called_once_with(
            impersonate="chrome_126",
            verify=False,
            proxy=None
        )

        # Verify get was called with correct params
        mock_client_instance.get.assert_called_once_with(
            "https://www.google.com/travel/flights",
            params=params
        )

        # Verify response is returned
        assert result == mock_response

    @patch('fast_flights.core.Client')
    def test_fetch_with_primp_config_no_proxy(self, mock_client_class):
        """Test fetch() with PrimpConfig but no proxy set."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        # Call fetch with empty PrimpConfig
        params = {"tfs": "test", "hl": "en"}
        primp_config = PrimpConfig()
        result = fetch(params, primp_config=primp_config)

        # Verify Client was created without proxy
        mock_client_class.assert_called_once_with(
            impersonate="chrome_126",
            verify=False,
            proxy=None
        )

    @patch('fast_flights.core.Client')
    def test_fetch_with_socks5_proxy(self, mock_client_class):
        """Test fetch() with SOCKS5 proxy configuration."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        # Call fetch with SOCKS5 proxy
        params = {"tfs": "test", "hl": "en"}
        proxy_url = "socks5://127.0.0.1:9150"
        primp_config = PrimpConfig(proxy=proxy_url)
        result = fetch(params, primp_config=primp_config)

        # Verify Client was created WITH the proxy
        mock_client_class.assert_called_once_with(
            impersonate="chrome_126",
            verify=False,
            proxy=proxy_url
        )

        # Verify get was still called correctly
        mock_client_instance.get.assert_called_once_with(
            "https://www.google.com/travel/flights",
            params=params
        )

    @patch('fast_flights.core.Client')
    def test_fetch_with_http_proxy(self, mock_client_class):
        """Test fetch() with HTTP proxy configuration."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        # Call fetch with HTTP proxy
        params = {"tfs": "test", "hl": "en"}
        proxy_url = "http://proxy.example.com:8080"
        primp_config = PrimpConfig(proxy=proxy_url)
        result = fetch(params, primp_config=primp_config)

        # Verify Client was created WITH the proxy
        mock_client_class.assert_called_once_with(
            impersonate="chrome_126",
            verify=False,
            proxy=proxy_url
        )

    @patch('fast_flights.core.Client')
    def test_fetch_with_authenticated_proxy(self, mock_client_class):
        """Test fetch() with authenticated proxy URL."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        # Call fetch with authenticated proxy
        params = {"tfs": "test", "hl": "en"}
        proxy_url = "http://user:password@proxy.example.com:8080"
        primp_config = PrimpConfig(proxy=proxy_url)
        result = fetch(params, primp_config=primp_config)

        # Verify Client was created WITH the authenticated proxy
        mock_client_class.assert_called_once_with(
            impersonate="chrome_126",
            verify=False,
            proxy=proxy_url
        )

    @patch('fast_flights.core.Client')
    def test_fetch_raises_on_non_200_status(self, mock_client_class):
        """Test fetch() raises AssertionError on non-200 status code."""
        # Setup mock to return non-200 status
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text_markdown = "Internal Server Error"
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        # Verify AssertionError is raised
        params = {"tfs": "test", "hl": "en"}
        primp_config = PrimpConfig(proxy="http://proxy:8080")

        with pytest.raises(AssertionError) as exc_info:
            fetch(params, primp_config=primp_config)

        assert "500" in str(exc_info.value)


class TestGetFlightsFromFilterWithPrimpConfig:
    """Test that get_flights_from_filter() properly passes primp_config to fetch()."""

    @patch('fast_flights.core.fetch')
    def test_get_flights_from_filter_without_primp_config(self, mock_fetch):
        """Test get_flights_from_filter() without primp_config."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.text = '<html><div jsname="IWWDBc"><ul class="Rk10dc"><li><div class="sSHqwe tPgKwe ogfYpf"><span>Test Airline</span></div><span class="mv1WYe"><div>10:00 AM</div><div>2:00 PM</div></span><div class="Ak5kof"><div>4h</div></div><div class="BbR8Ec"><span class="ogfYpf">Nonstop</span></div><span class="YMlIz FpEdX">$100</span></li></ul></div><span class="gOatQ">Typical</span></html>'
        mock_fetch.return_value = mock_response

        # Create filter
        filter_data = create_filter(
            flight_data=[
                FlightData(date="2025-10-04", from_airport="SJC", to_airport="LAX")
            ],
            trip="one-way",
            seat="economy",
            passengers=Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0),
        )

        # Call without primp_config
        result = get_flights_from_filter(filter_data)

        # Verify fetch was called without primp_config
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args

        # fetch is called with positional args: fetch(params, primp_config)
        # call_args[0] contains positional args
        assert len(call_args[0]) == 2
        params_dict = call_args[0][0]
        primp_config_arg = call_args[0][1]

        # Verify params dict is present and primp_config is None
        assert isinstance(params_dict, dict)
        assert primp_config_arg is None

    @patch('fast_flights.core.fetch')
    def test_get_flights_from_filter_with_primp_config(self, mock_fetch):
        """Test get_flights_from_filter() WITH primp_config."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.text = '<html><div jsname="IWWDBc"><ul class="Rk10dc"><li><div class="sSHqwe tPgKwe ogfYpf"><span>Test Airline</span></div><span class="mv1WYe"><div>10:00 AM</div><div>2:00 PM</div></span><div class="Ak5kof"><div>4h</div></div><div class="BbR8Ec"><span class="ogfYpf">Nonstop</span></div><span class="YMlIz FpEdX">$100</span></li></ul></div><span class="gOatQ">Typical</span></html>'
        mock_fetch.return_value = mock_response

        # Create filter
        filter_data = create_filter(
            flight_data=[
                FlightData(date="2025-10-04", from_airport="SJC", to_airport="LAX")
            ],
            trip="one-way",
            seat="economy",
            passengers=Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0),
        )

        # Call with primp_config
        proxy_url = "socks5://127.0.0.1:9150"
        primp_config = PrimpConfig(proxy=proxy_url)
        result = get_flights_from_filter(filter_data, primp_config=primp_config)

        # Verify fetch was called WITH primp_config
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args

        # fetch is called with positional args: fetch(params, primp_config)
        assert len(call_args[0]) == 2
        params_dict = call_args[0][0]
        primp_config_arg = call_args[0][1]

        # Verify the primp_config argument matches what we passed
        assert isinstance(params_dict, dict)
        assert primp_config_arg == primp_config
        assert primp_config_arg.proxy == proxy_url

    @patch('fast_flights.core.fetch')
    def test_get_flights_from_filter_fallback_mode_with_primp_config(self, mock_fetch):
        """Test that primp_config is used in fallback mode's initial fetch attempt."""
        # Setup mock to fail first (trigger fallback), but we're testing it's called with primp_config
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text_markdown = "Error"
        mock_fetch.side_effect = AssertionError("500 Result: Error")

        # Create filter
        filter_data = create_filter(
            flight_data=[
                FlightData(date="2025-10-04", from_airport="SJC", to_airport="LAX")
            ],
            trip="one-way",
            seat="economy",
            passengers=Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0),
        )

        # Call with primp_config in fallback mode
        proxy_url = "http://proxy:8080"
        primp_config = PrimpConfig(proxy=proxy_url)

        # Should raise since we're in "common" mode and it fails
        with pytest.raises(AssertionError):
            get_flights_from_filter(filter_data, mode="common", primp_config=primp_config)

        # Verify fetch was called with primp_config
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args

        # fetch is called with positional args: fetch(params, primp_config)
        assert len(call_args[0]) == 2
        params_dict = call_args[0][0]
        primp_config_arg = call_args[0][1]

        assert isinstance(params_dict, dict)
        assert primp_config_arg == primp_config


class TestGetFlightsWithPrimpConfig:
    """Test that get_flights() properly passes primp_config through the call chain."""

    @patch('fast_flights.core.fetch')
    def test_get_flights_without_primp_config(self, mock_fetch):
        """Test get_flights() backward compatibility - works without primp_config."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.text = '<html><div jsname="IWWDBc"><ul class="Rk10dc"><li><div class="sSHqwe tPgKwe ogfYpf"><span>Test Airline</span></div><span class="mv1WYe"><div>10:00 AM</div><div>2:00 PM</div></span><div class="Ak5kof"><div>4h</div></div><div class="BbR8Ec"><span class="ogfYpf">Nonstop</span></div><span class="YMlIz FpEdX">$100</span></li></ul></div><span class="gOatQ">Typical</span></html>'
        mock_fetch.return_value = mock_response

        # Call get_flights without primp_config
        result = get_flights(
            flight_data=[
                FlightData(date="2025-10-04", from_airport="SJC", to_airport="LAX")
            ],
            trip="one-way",
            seat="economy",
            passengers=Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0),
        )

        # Verify fetch was called (backward compatibility maintained)
        mock_fetch.assert_called_once()

        # Result should be valid
        assert result is not None

    @patch('fast_flights.core.fetch')
    def test_get_flights_with_primp_config(self, mock_fetch):
        """Test get_flights() passes primp_config through to fetch()."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.text = '<html><div jsname="IWWDBc"><ul class="Rk10dc"><li><div class="sSHqwe tPgKwe ogfYpf"><span>Test Airline</span></div><span class="mv1WYe"><div>10:00 AM</div><div>2:00 PM</div></span><div class="Ak5kof"><div>4h</div></div><div class="BbR8Ec"><span class="ogfYpf">Nonstop</span></div><span class="YMlIz FpEdX">$100</span></li></ul></div><span class="gOatQ">Typical</span></html>'
        mock_fetch.return_value = mock_response

        # Call get_flights WITH primp_config
        proxy_url = "socks5://127.0.0.1:9150"
        primp_config = PrimpConfig(proxy=proxy_url)

        result = get_flights(
            flight_data=[
                FlightData(date="2025-10-04", from_airport="SJC", to_airport="LAX")
            ],
            trip="one-way",
            seat="economy",
            passengers=Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0),
            primp_config=primp_config,
        )

        # Verify fetch was called with the primp_config
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args

        # fetch is called with positional args: fetch(params, primp_config)
        assert len(call_args[0]) == 2
        params_dict = call_args[0][0]
        primp_config_arg = call_args[0][1]

        assert isinstance(params_dict, dict)
        assert primp_config_arg == primp_config
        assert primp_config_arg.proxy == proxy_url


class TestPrimpConfigEdgeCases:
    """Test edge cases for PrimpConfig."""

    def test_primp_config_with_empty_string_proxy(self):
        """Test creating PrimpConfig with empty string proxy."""
        config = PrimpConfig(proxy="")

        # Empty string should be preserved (not converted to None)
        assert config.proxy == ""

    def test_primp_config_dataclass_immutability(self):
        """Test that PrimpConfig attributes can be set after creation."""
        config = PrimpConfig(proxy="http://proxy:8080")

        # Dataclass should allow attribute modification
        config.proxy = "socks5://newproxy:9150"
        assert config.proxy == "socks5://newproxy:9150"


class TestProxyStringFormats:
    """Test that various proxy string formats are correctly handled."""

    @patch('fast_flights.core.Client')
    def test_socks5_proxy_format(self, mock_client_class):
        """Test SOCKS5 proxy URL format is correctly passed to Client."""
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        proxy_formats = [
            "socks5://127.0.0.1:9150",
            "socks5://localhost:9050",
            "socks5://proxy.example.com:1080",
        ]

        for proxy_url in proxy_formats:
            mock_client_class.reset_mock()
            primp_config = PrimpConfig(proxy=proxy_url)
            fetch({}, primp_config=primp_config)

            mock_client_class.assert_called_once_with(
                impersonate="chrome_126",
                verify=False,
                proxy=proxy_url
            )

    @patch('fast_flights.core.Client')
    def test_http_proxy_format(self, mock_client_class):
        """Test HTTP proxy URL format is correctly passed to Client."""
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        proxy_formats = [
            "http://proxy.example.com:8080",
            "http://localhost:8888",
            "http://192.168.1.1:3128",
        ]

        for proxy_url in proxy_formats:
            mock_client_class.reset_mock()
            primp_config = PrimpConfig(proxy=proxy_url)
            fetch({}, primp_config=primp_config)

            mock_client_class.assert_called_once_with(
                impersonate="chrome_126",
                verify=False,
                proxy=proxy_url
            )

    @patch('fast_flights.core.Client')
    def test_authenticated_proxy_format(self, mock_client_class):
        """Test authenticated proxy URL format is correctly passed to Client."""
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        proxy_formats = [
            "http://user:pass@proxy.example.com:8080",
            "http://admin:secret123@localhost:8888",
            "socks5://user:pass@proxy.example.com:1080",
        ]

        for proxy_url in proxy_formats:
            mock_client_class.reset_mock()
            primp_config = PrimpConfig(proxy=proxy_url)
            fetch({}, primp_config=primp_config)

            mock_client_class.assert_called_once_with(
                impersonate="chrome_126",
                verify=False,
                proxy=proxy_url
            )


class TestProxySpecialCharacters:
    """Test proxy URLs with special characters in credentials."""

    @patch('fast_flights.core.Client')
    def test_proxy_with_special_chars_in_credentials(self, mock_client_class):
        """Test proxy URL with special characters in username/password."""
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        # URL-encoded special characters in credentials
        proxy_url = "http://user%40name:pass%21word@proxy.example.com:8080"
        primp_config = PrimpConfig(proxy=proxy_url)
        fetch({}, primp_config=primp_config)

        # Verify the URL is passed as-is to the Client
        mock_client_class.assert_called_once_with(
            impersonate="chrome_126",
            verify=False,
            proxy=proxy_url
        )

    @patch('fast_flights.core.Client')
    def test_proxy_with_at_sign_in_password(self, mock_client_class):
        """Test proxy URL with @ sign in password (URL encoded)."""
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        proxy_url = "http://admin:p%40ssw0rd@proxy.com:8080"
        primp_config = PrimpConfig(proxy=proxy_url)
        fetch({}, primp_config=primp_config)

        mock_client_class.assert_called_once_with(
            impersonate="chrome_126",
            verify=False,
            proxy=proxy_url
        )


class TestProxyProtocolVariations:
    """Test proxy URL protocol variations."""

    @patch('fast_flights.core.Client')
    def test_uppercase_socks5_protocol(self, mock_client_class):
        """Test SOCKS5 proxy with uppercase protocol."""
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        proxy_url = "SOCKS5://127.0.0.1:9150"
        primp_config = PrimpConfig(proxy=proxy_url)
        fetch({}, primp_config=primp_config)

        # Proxy URL should be passed as-is
        mock_client_class.assert_called_once_with(
            impersonate="chrome_126",
            verify=False,
            proxy=proxy_url
        )

    @patch('fast_flights.core.Client')
    def test_uppercase_http_protocol(self, mock_client_class):
        """Test HTTP proxy with uppercase protocol."""
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        proxy_url = "HTTP://proxy.example.com:8080"
        primp_config = PrimpConfig(proxy=proxy_url)
        fetch({}, primp_config=primp_config)

        mock_client_class.assert_called_once_with(
            impersonate="chrome_126",
            verify=False,
            proxy=proxy_url
        )


class TestProxyIPv6Addresses:
    """Test proxy URLs with IPv6 addresses."""

    @patch('fast_flights.core.Client')
    def test_ipv6_localhost_proxy(self, mock_client_class):
        """Test proxy URL with IPv6 localhost address."""
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        proxy_url = "http://[::1]:8080"
        primp_config = PrimpConfig(proxy=proxy_url)
        fetch({}, primp_config=primp_config)

        mock_client_class.assert_called_once_with(
            impersonate="chrome_126",
            verify=False,
            proxy=proxy_url
        )

    @patch('fast_flights.core.Client')
    def test_ipv6_full_address_proxy(self, mock_client_class):
        """Test proxy URL with full IPv6 address."""
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        proxy_url = "socks5://[2001:0db8::1]:1080"
        primp_config = PrimpConfig(proxy=proxy_url)
        fetch({}, primp_config=primp_config)

        mock_client_class.assert_called_once_with(
            impersonate="chrome_126",
            verify=False,
            proxy=proxy_url
        )


class TestProxyUnusualPorts:
    """Test proxy URLs with unusual but valid port numbers."""

    @patch('fast_flights.core.Client')
    def test_high_port_number(self, mock_client_class):
        """Test proxy URL with maximum valid port number."""
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        proxy_url = "http://proxy.example.com:65535"
        primp_config = PrimpConfig(proxy=proxy_url)
        fetch({}, primp_config=primp_config)

        mock_client_class.assert_called_once_with(
            impersonate="chrome_126",
            verify=False,
            proxy=proxy_url
        )

    @patch('fast_flights.core.Client')
    def test_low_port_number(self, mock_client_class):
        """Test proxy URL with low port number."""
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        proxy_url = "http://proxy.example.com:1"
        primp_config = PrimpConfig(proxy=proxy_url)
        fetch({}, primp_config=primp_config)

        mock_client_class.assert_called_once_with(
            impersonate="chrome_126",
            verify=False,
            proxy=proxy_url
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
