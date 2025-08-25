import streamlit as st
import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv
import sys

# --- 1. Configuration and Initialization (Unchanged) ---

load_dotenv()


def load_system_prompt(filepath="system_prompt.txt"):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        st.error(
            f"Error: The system prompt file was not found at '{filepath}'. Please create it."
        )
        sys.exit()


SYSTEM_PROMPT = load_system_prompt()


@st.cache_resource
def get_openai_client():
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com"
    )
    return client


client = get_openai_client()
LOCAL_API_URL = "http://127.0.0.1:8000/find-places"

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


# --- 2. REFACTORED Backend Logic Function ---
def get_llm_decision(messages):
    """
    This function's ONLY job is to decide if a tool should be used.
    If yes, it calls our API and returns the structured JSON DATA.
    If no, it returns a standard chat response STRING.
    """
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
            # The LLM wants to use our tool.
            tool_call = tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            query = function_args.get("query")

            # Call our local API and return its direct, structured response.
            try:
                api_response = requests.post(LOCAL_API_URL, json={"query": query})
                api_response.raise_for_status()
                return api_response.json()  # <-- RETURN THE RAW JSON
            except requests.exceptions.RequestException as e:
                # Return an error dictionary if the API call fails
                return {
                    "status": "ERROR",
                    "detail": f"Could not connect to the mapping service: {e}",
                }
        else:
            # The LLM just wants to chat. Return the string content.
            return response_message.content  # <-- RETURN A STRING

    except Exception as e:
        return f"An error occurred with the AI model: {e}"


# --- 3. REFACTORED Streamlit Frontend UI ---

st.title("🗺️ AI Places Finder")
st.caption(
    "Ask me to find places like 'best coffee in Brooklyn' and I'll show you a map link!"
)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

# Display prior chat messages
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            # The history now contains formatted Markdown, so we just render it.
            st.markdown(message["content"])

# Get user input from chat box
if prompt := st.chat_input("What are you looking for?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Finding places..."):
            full_conversation = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]

            # This 'response_data' can be a STRING or a DICTIONARY (JSON)
            response_data = get_llm_decision(full_conversation)

            # We now check the TYPE of the response to decide how to render it.
            if isinstance(response_data, str):
                # It's a simple chat message.
                st.markdown(response_data)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response_data}
                )

            elif isinstance(response_data, dict):
                # It's structured data from our API!
                if response_data.get("status") == "OK":
                    results = response_data.get("results", [])

                    # We build a response string for the history, AND render it live.
                    response_for_history = (
                        "Berikut adalah beberapa pilihan yang saya temukan:\n\n"
                    )

                    for i, place in enumerate(results):
                        # Use Streamlit components for reliable, code-based rendering
                        st.subheader(f"{i + 1}. {place['name']}")
                        st.write(f"**Alamat:** {place['address']}")
                        st.write(f"**Rating:** {place.get('rating', 'N/A')} ⭐")

                        # This Markdown link is now built by Python, so it's always correct.
                        st.markdown(f"**[View on Map]({place['maps_direction_url']})**")
                        st.divider()

                        # Also append this formatted text to our history string
                        response_for_history += (
                            f"**{i + 1}. {place['name']}**\n"
                            f"- **Alamat:** {place['address']}\n"
                            f"- **Rating:** {place.get('rating', 'N/A')} ⭐\n"
                            f"- **[View on Map]({place['maps_direction_url']})**\n\n"
                        )
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response_for_history}
                    )

                else:
                    # Handle API errors or cases with no results
                    error_detail = response_data.get(
                        "detail", "Tidak ada hasil yang ditemukan."
                    )
                    st.error(error_detail)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_detail}
                    )
