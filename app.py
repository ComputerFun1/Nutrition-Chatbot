import streamlit as st
import requests
import json
from ingredients import PANTRY_ITEMS
from guardrails import check_guardrails

# --------------------
# PAGE SETUP
# --------------------

st.set_page_config(
    page_title="Pantry Nutrition Assistant",
    page_icon="🥗"
)

# --- CUSTOM CSS FOR SCROLLABLE WINDOW ---
st.markdown("""
    <style>
    .scroll-container {
        height: 300px;
        overflow-y: scroll;
        padding: 10px;
        border: 1px solid #ccc;
        border-radius: 5px;
    }
    </style>
    """, unsafe_content_code=True)

# --------------------
# SIDEBAR - BOT SELECTION
# --------------------
with st.sidebar:
    st.title("Settings")
    bot_mode = st.radio(
        "Choose Assistant Mode:",
        ["Healthy Recipe Specialist", "Nutrition Assistant"],
        help="Switch between getting detailed recipes or general nutrition advice."
    )
    
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

st.title(f"🥗 {bot_mode}")

# --------------------
# CONFIG & API SETUP
# --------------------

# FOLLOWING DOCUMENTATION EXACTLY
API_URL = "https://router.huggingface.co/v1/chat/completions"

if "HF_TOKEN" in st.secrets:
    headers = {
        "Authorization": f"Bearer {st.secrets['HF_TOKEN']}",
    }
else:
    st.error("Missing HF_TOKEN in Secrets!")
    st.stop()

def query(payload):
    # Following the doc's stream=True logic
    response = requests.post(API_URL, headers=headers, json=payload, stream=True)
    # Basic error handling to catch the 400 error before the loop
    if response.status_code != 200:
        st.error(f"API Error {response.status_code}: {response.text}")
        return

    for line in response.iter_lines():
        if not line.startswith(b"data:"):
            continue
        if line.strip() == b"data: [DONE]":
            return
        # Yielding the json decode as per documentation
        yield json.loads(line.decode("utf-8").lstrip("data:").rstrip("\n"))

# --------------------
# INGREDIENT SELECTION (Scrollable)
# --------------------
st.subheader("Available Pantry Items")
st.write("Click ingredients to add them to your request:")

if "selected_ingredients" not in st.session_state:
    st.session_state.selected_ingredients = set()

# Scrollable container using Streamlit columns for buttons
with st.container(height=250):
    for category, items in PANTRY_ITEMS.items():
        st.markdown(f"**{category}**")
        cols = st.columns(4)
        for i, item in enumerate(items):
            if cols[i % 4].button(item, key=f"btn_{item}"):
                st.session_state.selected_ingredients.add(item)

if st.session_state.selected_ingredients:
    st.info(f"Selected: {', '.join(st.session_state.selected_ingredients)}")
    if st.button("Reset Selection"):
        st.session_state.selected_ingredients = set()
        st.rerun()


# --------------------
# CHATBOT SECTION
# --------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

user_input = st.chat_input("Type here")

if user_input or (st.session_state.selected_ingredients and st.button("Generate from Selected Items")):
    
    # Merge selected ingredients into the final prompt
    final_prompt = user_input if user_input else "What can I make with these ingredients?"
    if st.session_state.selected_ingredients:
        ing_string = ", ".join(st.session_state.selected_ingredients)
        final_prompt = f"Selected Pantry Items: {ing_string}. \nUser Question: {final_prompt}"
        
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": final_prompt})
    with st.chat_message("user"):
        st.write(final_prompt)

    # SAFETY CHECK
    safety = check_guardrails(final_prompt)

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
        if bot_mode == "Healthy Recipe Specialist":
            system_instruction = (
                        "You are a Professional Chef and Healthy Recipe Specialist. "
                        "For every recipe: 1. List specific tools needed. 2. Give precise time for each step. "
                        "3. Be extremely specific on cooking techniques (e.g., 'sauté until translucent, about 4 mins'). "
                        "Only suggest recipes using the provided ingredients."
                    )
        else: #Nutrition Assistant          
            system_instruction = (
                "You are a precise, evidence-based Nutrition Intelligence Assistant. "
                "Suggest simple healthy meals using pantry foods. "
                "Safety: If medical conditions are mentioned, provide a disclaimer. "
                "Precision: Use 4 kcal/g for protein/carbs and 9 kcal/g for fats. "
                "Output Format: Start with a 1-sentence Summary, then a bulleted Breakdown, then a brief 'Why'."
            )
        
        # Build the message history for the payload
        messages_for_api = [{"role": "system", "content": system_instruction}]
        for m in st.session_state.messages:
            messages_for_api.append(m)

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            
            # CALLING THE EXACT PAYLOAD STRUCTURE FROM DOCS
            chunks = query({
                "messages": messages_for_api,
                "model": "Qwen/Qwen2.5-1.5B-Instruct:featherless-ai",
                "stream": True,
            })

            if chunks:
                for chunk in chunks:
                    # Check if 'choices' exists and has at least one item
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        # Extract content safely
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        
                        if content:
                            full_response += content
                            response_placeholder.markdown(full_response + "▌")
                
                response_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
