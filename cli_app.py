import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv

# --- 1. Configuration ---
# Load API keys from .env file
load_dotenv()

# Configure the DeepSeek client
# It uses the OpenAI library but points to the DeepSeek API endpoint.
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com"
)

# The URL of our local FastAPI backend
LOCAL_API_URL = "http://127.0.0.1:8000/find-places"

# --- 2. Define the "Tool" for the LLM ---
# This is a JSON schema that describes our API endpoint to the LLM.
# It tells the LLM what the tool is called, what it does, and what parameters it needs.
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


# --- 3. The Main Application Logic ---
def run_conversation():
    """
    The main loop that handles the conversation with the user.
    """
    # Start with the user's first message
    user_prompt = input("You: ")
    messages = [{"role": "user", "content": user_prompt}]

    # --- First LLM Call: Decide if a tool is needed ---
    print("\nLLM is thinking...")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        tool_choice="auto",  # Let the model decide when to call a function
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    # --- 4. Check if the LLM wants to use our tool ---
    if tool_calls:
        # The LLM decided to call our function!
        print("LLM wants to search for a place. Calling our local API...")

        # In this simple case, we'll only handle the first tool call
        tool_call = tool_calls[0]
        function_name = tool_call.function.name

        if function_name == "find_places_on_map":
            # Extract the arguments the LLM generated
            function_args = json.loads(tool_call.function.arguments)
            query = function_args.get("query")

            # --- 5. Call our FastAPI Backend ---
            try:
                print(f"Searching for: '{query}'")
                api_response = requests.post(LOCAL_API_URL, json={"query": query})
                api_response.raise_for_status()  # Raise an exception for bad status codes
                function_response_data = api_response.json()
            except requests.exceptions.RequestException as e:
                print(f"Error calling local API: {e}")
                function_response_data = {"status": "ERROR", "results": []}

            # --- 6. Send the API results back to the LLM ---
            # Append the tool call and its result to the conversation history
            messages.append(response_message)  # Add the assistant's tool-calling reply
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(
                        function_response_data
                    ),  # The content is the JSON from our API
                }
            )

            # --- Second LLM Call: Generate a natural language response ---
            print("LLM is formatting the final answer...")
            final_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
            )
            print("\nAssistant:")
            print(final_response.choices[0].message.content)
    else:
        # The LLM decided not to call a tool and just chatted instead
        print("\nAssistant:")
        print(response_message.content)


# --- Run the application in a loop ---
if __name__ == "__main__":
    print("Welcome! Ask me to find a place. Type 'quit' to exit.")
    while True:
        try:
            run_conversation()
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
