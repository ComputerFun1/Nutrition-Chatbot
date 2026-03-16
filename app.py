import streamlit as st
import requests
import json
from recipes import PANTRY_RECIPES
from guardrails import check_guardrails

# --------------------
# PAGE SETUP
# --------------------

st.set_page_config(
    page_title="Pantry Nutrition Assistant",
    page_icon="🥗"
)

st.title("🥗 Pantry Nutrition Assistant")

st.write(
    "This assistant helps you make simple meals using common pantry foods."
)

st.caption(
    "Disclaimer: This information is for general nutrition education and is not medical advice."
)

# --------------------
# CONFIG & API SETUP
# --------------------

# Hugging Face OpenAI-compatible API URL
API_URL = "https://router.huggingface.co/v1/chat/completions"

# Check for HF_TOKEN in Streamlit Secrets
if "HF_TOKEN" in st.secrets:
    headers = {
        "Authorization": f"Bearer {st.secrets['HF_TOKEN']}",
       
    }
else:
    st.error("Missing HF_TOKEN! Go to Settings > Secrets and add: HF_TOKEN = 'your_token'")
    st.stop()

def get_streaming_response(messages):
    """Sends a request to HF and yields content chunks for Streamlit."""
    payload = {
        "model": "Qwen/Qwen2.5-1.5B-Instruct",
        "messages": messages,
        "stream": True,
        "max_tokens": 500,
        "temperature": 0.7
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, stream=True)
        response.raise_for_status()

        for line in response.iter_lines():
            if not line:
                continue
            
            line_str = line.decode("utf-8")
            
            if line_str.startswith("data: "):
                data_content = line_str[6:].strip()
                
                if data_content == "[DONE]":
                    break
                
                try:
                    chunk = json.loads(data_content)
                    content = chunk["choices"][0].get("delta", {}).get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue
                    
    except Exception as e:
        yield f"⚠️ Connection Error: {str(e)}"

# --------------------
# SUGGESTED MEAL BUTTONS
# --------------------

st.subheader("Quick Meal Ideas")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Rice & Beans Meal"):
        st.write("Cook rice. Warm beans. Add canned vegetables if available.")

with col2:
    if st.button("Tuna Pasta"):
        st.write("Cook pasta. Mix with canned tuna and vegetables.")

with col3:
    if st.button("Peanut Butter Oatmeal"):
        st.write("Cook oats and stir in peanut butter.")

# --------------------
# SMART RECIPE GENERATOR
# --------------------

st.subheader("What foods do you have?")

user_foods = st.text_input(
    "Enter foods you have (example: rice, beans, tuna)"
)

def find_recipe(foods):
    foods_list = [f.strip().lower() for f in foods.split(",")]
    matches = []
    for recipe in PANTRY_RECIPES:
        if all(item in foods_list for item in recipe["ingredients"]):
            matches.append(recipe)
    return matches

if st.button("Find Meal Ideas"):
    recipes = find_recipe(user_foods)
    if recipes:
        for r in recipes:
            st.write(f"### {r['name']}")
            st.write("Ingredients:", ", ".join(r["ingredients"]))
            st.write("How to make it:", r["instructions"])
    else:
        st.write("No exact match found. Try asking the assistant below!")

# --------------------
# CHATBOT SECTION
# --------------------

st.subheader("Ask the Nutrition Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

user_input = st.chat_input("Ask about meals or pantry foods")

if user_input:
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # SAFETY CHECK
    safety = check_guardrails(user_input)

    if safety == "medical":
        answer = (
            "I can only provide general nutrition information. "
            "For medical advice, please speak with a healthcare professional.\n\n"
            "This information is for general nutrition education and is not medical advice."
        )
        with st.chat_message("assistant"):
            st.write(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

    elif safety == "diet":
        answer = (
            "I focus on balanced and healthy eating. Extreme dieting or food restriction "
            "can be harmful. Try focusing on balanced meals with the foods you have available."
        )
        with st.chat_message("assistant"):
            st.write(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

    else:
        # Define the system instruction if it's the first message
        system_instruction = (
            "You are a precise, evidence-based Nutrition Intelligence Assistant. "
            "Suggest simple healthy meals using pantry foods. "
            "Safety: If medical conditions are mentioned, provide a disclaimer. "
            "Precision: Use 4 kcal/g for protein/carbs and 9 kcal/g for fats. "
            "Output Format: Start with a 1-sentence Summary, then a bulleted Breakdown, then a brief 'Why'."
        )
        
        # Prepare the messages list for the streaming API
        api_messages = [{"role": "system", "content": system_instruction}]
        # Add history to context
        for m in st.session_state.messages:
            api_messages.append(m)

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            
            # Start streaming
            for chunk in get_streaming_response(api_messages):
                full_response += chunk
                response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})
