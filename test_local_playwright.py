#!/usr/bin/env python3
"""
Test script for local Playwright Docker functionality using "local" mode.

This script tests the local Playwright integration with Docker containers
as documented in the README.md file.
"""

import asyncio
import time
from datetime import datetime, timedelta
from fast_flights import FlightData, Passengers, get_flights, PlaywrightConfig

def test_local_playwright_with_docker():
    """
    Test local Playwright functionality with Docker container.
    
    Tests the integration with a Playwright Docker container running on port 3000
    using the "local" fetch mode.
    """
    print("🧪 Testing Local Playwright with Docker Container")
    print("=" * 50)
    
    # Configure remote Playwright connection to Docker container
    playwright_config = PlaywrightConfig(url="ws://localhost:3000")
    
    # Set up test flight data for tomorrow
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    test_data = {
        "flight_data": [
            FlightData(date=tomorrow, from_airport="TPE", to_airport="NRT")
        ],
        "trip": "one-way",
        "seat": "economy", 
        "passengers": Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0),
        "fetch_mode": "local",
        "playwright_config": playwright_config,
    }
    
    print(f"📅 Test Date: {tomorrow}")
    print(f"✈️  Route: TPE → NRT") 
    print(f"👥 Passengers: {test_data['passengers'].adults} adult(s)")
    print(f"🎭 Playwright URL: {playwright_config.url}")
    print()
    
    try:
        print("🚀 Starting flight search...")
        start_time = time.time()
        
        result = get_flights(**test_data)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Search completed in {duration:.2f} seconds")
        print()
        
        if result:
            print("📊 Results:")
            print(f"   Current Price Trend: {result.current_price}")
            print(f"   Number of Flights Found: {len(result.flights)}")
            print()
            
            # Display first few flights
            for i, flight in enumerate(result.flights[:3]):
                print(f"   Flight {i+1}:")
                print(f"      Airline: {flight.name}")
                print(f"      Departure: {flight.departure}")
                print(f"      Arrival: {flight.arrival}")
                print(f"      Duration: {flight.duration}")
                print(f"      Stops: {flight.stops}")
                print(f"      Price: {flight.price}")
                print(f"      Best Deal: {'Yes' if flight.is_best else 'No'}")
                if flight.delay:
                    print(f"      Delay: {flight.delay}")
                print()
            
            if len(result.flights) > 3:
                print(f"   ... and {len(result.flights) - 3} more flights")
            
            print("✅ LOCAL PLAYWRIGHT TEST PASSED")
            return True
            
        else:
            print("❌ No results returned")
            print("❌ LOCAL PLAYWRIGHT TEST FAILED")
            return False
            
    except ConnectionError as e:
        print(f"❌ Connection Error: {e}")
        print("💡 Make sure Docker container is running:")
        print("   docker run -it --rm -p 3000:3000 mcr.microsoft.com/playwright:v1.53.0-noble /bin/bash -c \"cd /home/pwuser && npx playwright install && npx -y playwright@1.53.0 run-server --port=3000\"")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("❌ LOCAL PLAYWRIGHT TEST FAILED")
        return False

def test_local_playwright_without_docker():
    """
    Test local Playwright functionality without Docker (fallback to local browser).
    
    Tests the local mode without a Docker container by passing None for playwright_config,
    which should launch a local Chromium instance.
    """
    print("🧪 Testing Local Playwright without Docker (Local Browser)")
    print("=" * 60)
    
    # Set up test flight data for tomorrow
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    test_data = {
        "flight_data": [
            FlightData(date=tomorrow, from_airport="LAX", to_airport="SFO")
        ],
        "trip": "one-way",
        "seat": "economy",
        "passengers": Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0),
        "fetch_mode": "local",
        "playwright_config": None,  # Use local browser
    }
    
    print(f"📅 Test Date: {tomorrow}")
    print(f"✈️  Route: LAX → SFO")
    print(f"👥 Passengers: {test_data['passengers'].adults} adult(s)")
    print(f"🎭 Playwright Mode: Local Browser")
    print()
    
    try:
        print("🚀 Starting flight search...")
        start_time = time.time()
        
        result = get_flights(**test_data)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Search completed in {duration:.2f} seconds")
        print()
        
        if result:
            print("📊 Results:")
            print(f"   Current Price Trend: {result.current_price}")
            print(f"   Number of Flights Found: {len(result.flights)}")
            print()
            
            # Display first flight
            if result.flights:
                flight = result.flights[0]
                print(f"   Sample Flight:")
                print(f"      Airline: {flight.name}")
                print(f"      Departure: {flight.departure}")
                print(f"      Arrival: {flight.arrival}")
                print(f"      Duration: {flight.duration}")
                print(f"      Price: {flight.price}")
                print()
            
            print("✅ LOCAL BROWSER TEST PASSED")
            return True
            
        else:
            print("❌ No results returned")
            print("❌ LOCAL BROWSER TEST FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("❌ LOCAL BROWSER TEST FAILED")
        return False

def run_all_tests():
    """Run all local Playwright tests."""
    print("🎯 Fast-Flights Local Playwright Test Suite")
    print("=" * 50)
    print()
    
    # Test 1: Docker container
    docker_test_passed = test_local_playwright_with_docker()
    print()
    print("-" * 50)
    print()
    
    # Test 2: Local browser
    local_test_passed = test_local_playwright_without_docker()
    print()
    print("=" * 50)
    
    # Summary
    print("📋 Test Summary:")
    print(f"   Docker Container Test: {'PASSED' if docker_test_passed else 'FAILED'}")
    print(f"   Local Browser Test: {'PASSED' if local_test_passed else 'FAILED'}")
    print()
    
    if docker_test_passed and local_test_passed:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)