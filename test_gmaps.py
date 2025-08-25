import googlemaps
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the API key from the environment variable
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not API_KEY:
    raise ValueError("Google Maps API key not found. Please set it in the .env file.")

# Initialize the client
try:
    gmaps = googlemaps.Client(key=API_KEY)
    print("Successfully connected to Google Maps API.")
except Exception as e:
    print(f"Error connecting to Google Maps API: {e}")
    exit()

# --- Test Case: Find Places ---
print("\n--- Testing Places API ---")
try:
    # A simple search query
    query = "sushi restaurants near Times Square NYC"
    places_result = gmaps.places(query=query)

    # Check if we got any results
    if places_result and places_result["status"] == "OK":
        print(f"Found {len(places_result['results'])} results for '{query}':")
        # Print the top 3 results
        for place in places_result["results"][:3]:
            name = place.get("name")
            address = place.get("formatted_address")
            rating = place.get("rating", "N/A")
            print(f"- Name: {name}\n  Address: {address}\n  Rating: {rating}\n")
    else:
        print(f"Could not find places. Status: {places_result.get('status')}")
        print(f"Error message: {places_result.get('error_message')}")

except googlemaps.exceptions.ApiError as e:
    print(f"An API Error occurred: {e}")
