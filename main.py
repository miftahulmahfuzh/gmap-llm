# gmap-llm/main.py
# for gmaps tool

import os
from dotenv import load_dotenv
import googlemaps
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# --- Initialization ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not API_KEY:
    raise ValueError("Google Maps API key not found in .env file.")

# Initialize FastAPI app and Google Maps client
app = FastAPI()
gmaps = googlemaps.Client(key=API_KEY)


# --- Pydantic Models (for request and response validation) ---
class PlaceRequest(BaseModel):
    query: str


class PlaceInfo(BaseModel):
    name: str
    address: str
    rating: Optional[float] = None
    place_id: str
    maps_embed_url: str
    maps_direction_url: str


class ApiResponse(BaseModel):
    status: str
    results: List[PlaceInfo]


# --- API Endpoint ---
@app.post("/find-places", response_model=ApiResponse)
def find_places(request: PlaceRequest):
    """
    Accepts a user query, searches for it using the Google Places API,
    and returns a formatted list of results including embed and direction links.
    """
    print(f"Received query: {request.query}")
    try:
        # Use the places API to search for the query
        places_result = gmaps.places(query=request.query)

        if places_result["status"] != "OK":
            # Handle cases where Google API returns an error (e.g., ZERO_RESULTS)
            return {"status": places_result["status"], "results": []}

        # Process and format the results
        formatted_results = []
        for place in places_result.get("results", [])[:5]:  # Limit to top 5 results
            place_id = place["place_id"]

            # Construct URLs using best practices
            embed_url = f"https://www.google.com/maps/embed/v1/place?key={API_KEY}&q=place_id:{place_id}"
            direction_url = f"https://www.google.com/maps/dir/?api=1&destination_place_id={place_id}&destination={place.get('formatted_address')}"

            # Create a PlaceInfo object for each result
            place_info = PlaceInfo(
                name=place.get("name"),
                address=place.get("formatted_address"),
                rating=place.get("rating"),
                place_id=place_id,
                maps_embed_url=embed_url,
                maps_direction_url=direction_url,
            )
            formatted_results.append(place_info)

        return {"status": "OK", "results": formatted_results}

    except googlemaps.exceptions.ApiError as e:
        print(f"Google Maps API Error: {e}")
        raise HTTPException(
            status_code=500, detail=f"An error occurred with the Google Maps API: {e}"
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=500, detail="An unexpected server error occurred."
        )


# A simple root endpoint to confirm the server is running
@app.get("/")
def read_root():
    return {"message": "LLM Maps API is running. Use the /find-places endpoint."}
