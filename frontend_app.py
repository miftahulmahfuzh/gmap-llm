import streamlit as st
import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv
import sys  # Import sys to exit gracefully

# --- 1. Configuration and Initialization ---

# Load API keys from .env file
load_dotenv()


# --- NEW CODE START: Function to load the system prompt from a file ---
def load_system_prompt(filepath="system_prompt.txt"):
    """Reads the system prompt from a text file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        st.error(
            f"Error: The system prompt file was not found at '{filepath}'. Please create it."
        )
        # We stop the app if the core prompt is missing.
        sys.exit()


# --- NEW CODE END ---


# Load the system prompt from the file we just created
SYSTEM_PROMPT = load_system_prompt()


# Configure the DeepSeek/OpenAI client
@st.cache_resource
def get_openai_client():
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com"
    )
    return client


client = get_openai_client()

# URL for our local FastAPI backend
LOCAL_API_URL = "http://127.0.0.1:8000/find-places"

# The description of our custom "tool" for the LLM
tools = [
    {
        "type": "function",
        "function": {
            "name": "find_places_on_map",
            "description": "Searches for places like restaurants, cafes, parks, or points of interest based on a user's query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The user's search query, e.g., 'best pizza in New York' or 'parks near me'",
                    },
                },
                "required": ["query"],
            },
        },
    }
]

# --- 2. Backend Logic Function (This function remains unchanged) ---


def get_llm_response(messages):
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        if tool_calls:
            messages.append(response_message)
            tool_call = tool_calls[0]
            function_name = tool_call.function.name
            if function_name == "find_places_on_map":
                function_args = json.loads(tool_call.function.arguments)
                query = function_args.get("query")
                try:
                    api_response = requests.post(LOCAL_API_URL, json={"query": query})
                    api_response.raise_for_status()
                    function_response_data = api_response.json()
                except requests.exceptions.RequestException as e:
                    return f"Sorry, I couldn't connect to the local mapping service. Error: {e}"
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_response_data),
                    }
                )
                final_response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                )
                return final_response.choices[0].message.content
        else:
            return response_message.content
    except Exception as e:
        return f"An error occurred: {e}"


# --- 3. Streamlit Frontend UI ---

st.title("🗺️ AI Places Finder")
st.caption(
    "Ask me to find places like 'best coffee in Brooklyn' and I'll show you a map link!"
)

# Initialize chat history in session state
if "messages" not in st.session_state:
    # --- CHANGE: Use the variable loaded from the file ---
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

# Display prior chat messages
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Get user input from chat box
if prompt := st.chat_input("What are you looking for?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            full_conversation = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]
            response_content = get_llm_response(full_conversation)
            st.markdown(response_content)

    st.session_state.messages.append({"role": "assistant", "content": response_content})
