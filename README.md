# 🗺️ AI Places Finder with Google Maps

This project demonstrates how to build a powerful, interactive web application that uses a Large Language Model (LLM) to understand user requests and the Google Maps API to find real-world locations. The application is built with a robust, separated architecture: a FastAPI backend for reliable data fetching and a clean HTML frontend for an intuitive user interface.

## Features

-   **Natural Language Understanding**: Ask for places in plain English (or other languages), like "find me some good ramen spots in downtown san francisco".
-   **Real-time Google Maps Integration**: Fetches up-to-date information on locations, including names, addresses, and ratings.
-   **Embedded Maps**: View locations directly in the interface with interactive Google Maps embeds.
-   **Reliable Map Links**: Generates clickable Google Maps links for directions to each location.
-   **Separation of Concerns**:
    -   **LLM (Intent Engine)**: Determines what the user wants.
    -   **FastAPI Backend (Data Engine)**: Acts as a secure "tool" to get structured data from Google.
    -   **HTML Frontend (Presentation Engine)**: Renders the data in a user-friendly, responsive web interface.
-   **Secure API Key Handling**: Uses environment variables to keep your secret keys safe.
-   **Easy Customization**: The AI's behavior and personality can be easily modified by editing a simple text file.
-   **Modern Web Interface**: Clean, responsive design that works on desktop and mobile devices.

## How It Works
1. **User Input**: The user types a natural language request into the HTML frontend (e.g., "best pizza in Brooklyn").
2. **Search Mode Selection**: The user chooses between:
  - **Standard Search**: Direct query to Google Places API
  - **AI Enhanced Search**: LLM preprocesses the query for better results
3. **Backend Processing**:
  - **Standard Mode** (`/find-places`): FastAPI sends the original query directly to Google Maps API
  - **AI Enhanced Mode** (`/find-places-llm`): FastAPI first sends the query to the LLM (DeepSeek) to optimize it, then searches Google Maps with the improved query
4. **Data Retrieval**: The backend fetches up to 60 results from Google Places API with pagination support (10 results per page)
5. **Response & Caching**: The frontend receives structured JSON data including:
  - Place information (name, address, rating, maps links)
  - Pagination metadata
  - Query processing details (for AI mode)
  - Search duration metrics
6. **Display & Navigation**: Results are displayed in interactive cards with embedded maps, and users can navigate through pages while comparing performance between search modes
7. **Smart Caching**: Results are cached client-side for instant comparison when toggling between Standard and AI Enhanced modes

---

## Setup and Installation

Follow these steps to get the project running on your local machine.

### Step 1: Obtain API Keys

You will need a Google Maps API key for this project.

#### Google Maps API Key

1.  **Go to Google Cloud Console**: Navigate to the [Google Cloud Console](https://cloud.google.com/) and sign in with your Google account.
2.  **Create a New Project**: If you don't have one already, create a new project (e.g., `ai-places-finder`).
3.  **Enable Billing**: You must enable billing for your project. Google Cloud provides a generous free trial with credits, so you will not be charged unless you exceed the free tier limits.
4.  **Enable APIs**: In the navigation menu, go to **APIs & Services > Library** and search for and **enable** the following APIs:
    -   `Places API`
    -   `Maps Embed API`
    -   `Geocoding API`
5.  **Create API Key**: Go to **APIs & Services > Credentials**, click **"+ CREATE CREDENTIALS"**, and select **"API key"**. Copy the generated key immediately.
6.  **Secure Your Key (Important!)**: Click on the new API key to edit it. Under **"API restrictions"**, select **"Restrict key"** and check the boxes for the `Places API`, `Maps Embed API`, and `Geocoding API`. This is a crucial security step.

### Step 2: Setup Python Environment and Install Dependencies

It is highly recommended to use a Python virtual environment.

1.  **Create a Virtual Environment**:
    ```bash
    python -m venv venv
    ```
2.  **Activate the Environment**:
    -   **On Windows**: `.\venv\Scripts\activate`
    -   **On macOS/Linux**: `source venv/bin/activate`

3.  **Create `requirements.txt`**: Create a file named `requirements.txt` in your project folder and add the following lines:
    ```txt
    fastapi
    uvicorn[standard]
    googlemaps
    python-dotenv
    ```
4.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### Step 3: Configure Environment Variables

1.  Create a file named `.env` in the root of your project directory. **This file should never be committed to Git.**
2.  Add your Google Maps API key to this file:

    ```
    GOOGLE_MAPS_API_KEY="PASTE_YOUR_GOOGLE_MAPS_API_KEY_HERE"
    ```
3.  Add your Deepseek API key to this file:

    ```
    DEEPSEEK_API_KEY="PASTE_YOUR_DEEPSEEK_API_KEY_HERE"
    ```

---

## Running the Application

You need to run both the backend API and the HTML frontend. You can do this in two separate terminals or use the provided server script.

### Method 1: Using the Provided Server Script (Recommended)

1. **Start the FastAPI Backend**:
   In your **first terminal**, run:
   ```bash
   uvicorn main_tool:app --reload
   ```
   This will start the API server on `http://127.0.0.1:8000`

2. **Start the HTML Frontend**:
   In your **second terminal**, run:
   ```bash
   python server.py
   ```
   This will start the HTML server on `http://localhost:3000` and automatically open your browser.

### Method 2: Manual Setup

#### 1. Start the Backend API

In your **first terminal**, run:
```bash
uvicorn main_tool:app --reload
```
You should see a message indicating the server is running on `http://127.0.0.1:8000`. Leave this terminal running.

#### 2. Start the HTML Frontend

In your **second terminal**, serve the HTML file using Python's built-in server:
```bash
python -m http.server 3000
```
Then open your browser and navigate to `http://localhost:3000/index.html`.

---

## Project Structure

```
gmap-llm/
├── .env                 # Stores your GMaps & Deepseek API key
├── cli_app.py           # Command line interface
├── index.html           # The HTML frontend application
├── main_tool.py         # The FastAPI backend API
├── README.md            # Comprehensive documentation
├── requirements.txt     # List of Python dependencies (create this)
├── server.py            # Simple HTTP server for HTML frontend
├── system_prompt.txt    # AI behavior instructions
└── test_gmaps.py        # Testing utilities
```

## API Endpoints
The FastAPI backend provides the following endpoints:
- **POST `/find-places`**: Standard search endpoint that queries Google Places API directly
 - Request body: `{"query": "your search query", "top_n": 10, "page": 1}`
 - Returns: JSON with place information, pagination metadata, and search duration
- **POST `/find-places-llm`**: AI-enhanced search endpoint that preprocesses queries using LLM before searching
 - Request body: `{"query": "your search query", "top_n": 10, "page": 1}`
 - Returns: JSON with place information, pagination metadata, original/processed queries, and search duration
- **GET `/`**: Root endpoint with API status and available endpoints information
- **GET `/health`**: Health check endpoint for monitoring API availability

### Request Parameters
- `query` (required): Natural language search query
- `top_n` (optional): Number of results per page (1-60, default: 5)
- `page` (optional): Page number for pagination (default: 1)

### Response Format
Both endpoints return structured JSON containing:
- Place details (name, address, rating, Google Maps URLs)
- Pagination information (current page, total results, navigation flags)
- Performance metrics (search duration)
- Query processing details (LLM endpoint only)

## Usage

1. Open your browser to `http://localhost:3000/index.html`
2. Type your search query in the input field (e.g., "best coffee in Brooklyn")
3. Click "Find Places" or press Enter
4. View the results with embedded maps and get directions

## Example Queries

- "best pizza in New York"
- "coffee shops near Times Square"
- "parks in San Francisco"
- "restaurants in downtown Chicago"
- "gas stations near me" (if location services are enabled)

## Troubleshooting

### CORS Errors
If you see CORS errors in the browser console, make sure your FastAPI server includes the CORS middleware (it should be included in `main_tool.py`).

### Maps Not Loading
If the embedded maps don't load:
1. Check that your Google Maps API key is correct in the `.env` file
2. Verify that the Maps Embed API is enabled in your Google Cloud Console
3. Check the browser console for any API key errors

### API Connection Issues
If the frontend can't connect to the backend:
1. Make sure the FastAPI server is running on `http://127.0.0.1:8000`
2. Check that the API URL in `index.html` matches your backend server address
3. Verify that both servers are running simultaneously

## Security Notes

- Never commit your `.env` file to version control
- Restrict your Google Maps API key to only the necessary APIs
- In production, consider implementing rate limiting and authentication
- Replace `allow_origins=["*"]` in the CORS middleware with specific domains in production

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the [MIT License](LICENSE).
