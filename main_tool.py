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


def search_places(query: str) -> ApiResponse:
    """
    Core function to search places using Google Maps API.
    """
    print(f"Searching for: {query}")
    try:
        places_result = gmaps.places(query=query)

        if places_result["status"] != "OK":
            return ApiResponse(status=places_result["status"], results=[])

        formatted_results = []
        for place in places_result.get("results", [])[:5]:
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

        return ApiResponse(status="OK", results=formatted_results)

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
    """
    return search_places(request.query)


@app.post("/find-places-llm", response_model=ApiResponse)
def find_places_llm(request: PlaceRequest):
    """
    New endpoint: preprocesses user query with LLM, then searches for places.
    """
    original_query = request.query
    processed_query = preprocess_query_with_llm(original_query)

    result = search_places(processed_query)
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
