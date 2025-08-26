# gmap-llm/main_tool.py

# for gmaps tool
import os
from dotenv import load_dotenv
import googlemaps
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# --- Initialization ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not API_KEY:
    raise ValueError("Google Maps API key not found in .env file.")
if not DEEPSEEK_API_KEY:
    raise ValueError("DeepSeek API key not found in .env file.")

# Initialize FastAPI app, Google Maps client, and OpenAI client
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

gmaps = googlemaps.Client(key=API_KEY)
llm_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")


# Load system prompt from file
def load_system_prompt():
    try:
        with open("system_prompt.txt", "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        raise ValueError("system_prompt.txt file not found")
    except Exception as e:
        raise ValueError(f"Error reading system_prompt.txt: {e}")


SYSTEM_PROMPT = load_system_prompt()


# --- Pydantic Models ---
class PlaceRequest(BaseModel):
    query: str
    top_n: Optional[int] = 5
    page: Optional[int] = 1


class PlaceInfo(BaseModel):
    name: str
    address: str
    rating: Optional[float] = None
    place_id: str
    maps_embed_url: str
    maps_direction_url: str


class PaginationInfo(BaseModel):
    current_page: int
    total_results: int
    results_per_page: int
    total_pages: int
    has_next_page: bool
    has_prev_page: bool


class ApiResponse(BaseModel):
    status: str
    results: List[PlaceInfo]
    pagination: PaginationInfo
    original_query: Optional[str] = None
    processed_query: Optional[str] = None


# --- Helper Functions ---
def preprocess_query_with_llm(user_query: str) -> str:
    """
    Use LLM to preprocess and optimize the user query for Google Maps search.
    """
    try:
        response = llm_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_query},
            ],
            stream=False,
        )
        processed_query = response.choices[0].message.content.strip()
        return processed_query
    except Exception as e:
        print(f"LLM preprocessing error: {e}")
        # Fallback to original query if LLM fails
        return user_query


def get_all_places(query: str, max_results: int = 60) -> List[dict]:
    """
    Get all available places from Google Places API with pagination support.
    Google Places API returns up to 20 results per request and supports up to 3 pages (60 total).
    """
    all_places = []
    next_page_token = None
    requests_made = 0
    max_requests = 3  # Google Places API limit

    try:
        while requests_made < max_requests and len(all_places) < max_results:
            if next_page_token:
                # Add a small delay for next_page_token requests as recommended by Google
                import time

                time.sleep(2)
                places_result = gmaps.places(query=query, page_token=next_page_token)
            else:
                places_result = gmaps.places(query=query)

            requests_made += 1

            if places_result["status"] not in ["OK", "ZERO_RESULTS"]:
                break

            current_results = places_result.get("results", [])
            all_places.extend(current_results)

            next_page_token = places_result.get("next_page_token")

            # Break if no more results or reached max
            if not next_page_token or len(all_places) >= max_results:
                break

    except Exception as e:
        print(f"Error fetching additional pages: {e}")

    return all_places[:max_results]


def search_places(query: str, top_n: int = 5, page: int = 1) -> ApiResponse:
    """
    Core function to search places using Google Maps API with pagination.
    """
    print(f"Searching for: {query} (top_n: {top_n}, page: {page})")

    # Validate parameters
    if top_n < 1 or top_n > 60:
        raise HTTPException(status_code=400, detail="top_n must be between 1 and 60")
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be 1 or greater")

    try:
        # Get all available places (up to 60 from Google API)
        all_places = get_all_places(query, max_results=60)

        if not all_places:
            return ApiResponse(
                status="ZERO_RESULTS",
                results=[],
                pagination=PaginationInfo(
                    current_page=page,
                    total_results=0,
                    results_per_page=top_n,
                    total_pages=0,
                    has_next_page=False,
                    has_prev_page=False,
                ),
            )

        # Calculate pagination
        total_results = len(all_places)
        total_pages = (total_results + top_n - 1) // top_n  # Ceiling division
        start_idx = (page - 1) * top_n
        end_idx = min(start_idx + top_n, total_results)

        # Check if requested page exists
        if start_idx >= total_results:
            raise HTTPException(
                status_code=404,
                detail=f"Page {page} not found. Total pages available: {total_pages}",
            )

        # Get places for current page
        page_places = all_places[start_idx:end_idx]

        formatted_results = []
        for place in page_places:
            place_id = place["place_id"]

            embed_url = f"https://www.google.com/maps/embed/v1/place?key={API_KEY}&q=place_id:{place_id}"
            direction_url = f"https://www.google.com/maps/dir/?api=1&destination_place_id={place_id}&destination={place.get('formatted_address')}"

            place_info = PlaceInfo(
                name=place.get("name"),
                address=place.get("formatted_address"),
                rating=place.get("rating"),
                place_id=place_id,
                maps_embed_url=embed_url,
                maps_direction_url=direction_url,
            )
            formatted_results.append(place_info)

        pagination_info = PaginationInfo(
            current_page=page,
            total_results=total_results,
            results_per_page=top_n,
            total_pages=total_pages,
            has_next_page=page < total_pages,
            has_prev_page=page > 1,
        )

        return ApiResponse(
            status="OK", results=formatted_results, pagination=pagination_info
        )

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


# --- API Endpoints ---
@app.post("/find-places", response_model=ApiResponse)
def find_places(request: PlaceRequest):
    """
    Original endpoint: directly searches for places without LLM preprocessing.
    Supports top_n parameter (1-60) and pagination.
    """
    return search_places(request.query, request.top_n, request.page)


@app.post("/find-places-llm", response_model=ApiResponse)
def find_places_llm(request: PlaceRequest):
    """
    New endpoint: preprocesses user query with LLM, then searches for places.
    Supports top_n parameter (1-60) and pagination.
    """
    original_query = request.query
    processed_query = preprocess_query_with_llm(original_query)

    result = search_places(processed_query, request.top_n, request.page)
    result.original_query = original_query
    result.processed_query = processed_query

    return result


@app.get("/")
def read_root():
    return {
        "message": "LLM Maps API is running. Use /find-places or /find-places-llm endpoints."
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "API is running normally"}
