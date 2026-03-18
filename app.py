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

st.title("🥗 Pantry Nutrition Assistant")

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
# INGREDIENT SELECTION
# --------------------
if "selected_ingredients" not in st.session_state:
    st.session_state.selected_ingredients = set()
if "messages" not in st.session_state:
    st.session_state.messages = []

st.subheader("Pantry Inventory")
st.write("Select ingredients to highlight them:")

# Scrollable container with reduced spacing logic
with st.container(height=280):
    for category, items in PANTRY_ITEMS.items():
        st.markdown(f"**{category}**", help=None)
        # Use more columns to reduce horizontal spacing
        cols = st.columns(5) 
        for i, item in enumerate(items):
            is_selected = item in st.session_state.selected_ingredients
            # Visual distinction: Orange for selected
            label = f"🟠 {item}" if is_selected else item
            
            if cols[i % 5].button(label, key=f"btn_{item}"):
                if is_selected:
                    st.session_state.selected_ingredients.remove(item)
                else:
                    st.session_state.selected_ingredients.add(item)
                st.rerun()

# Functional Buttons for Recipe Generation
col_rec, col_res = st.columns([1, 1])
with col_rec:
    generate_recipe = st.button("👨‍🍳 Generate Healthy Recipe", use_container_width=True)
with col_res:
    if st.button("Reset Selection", use_container_width=True):
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

user_input = st.chat_input("Ask the Nutrition Assistant")

# Determine which bot is acting
active_mode = None
final_prompt = ""

if generate_recipe:
    if not st.session_state.selected_ingredients:
        st.warning("Please select some ingredients first!")
    else:
        active_mode = "Recipe"
        ing_list = ", ".join(st.session_state.selected_ingredients)
        final_prompt = f"Please generate a detailed healthy recipe using: {ing_list}."

elif user_input:
    active_mode = "Nutrition"
    final_prompt = user_input

if active_mode:
        
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": final_prompt})
    with st.chat_message("user"):
        st.write(final_prompt)

    # GUARDRAIL TRIGGER (Modified: Warn but continue)
    safety_issue = check_guardrails(final_prompt)
    if safety_issue == "medical":
        st.warning("⚠️ Note: I can only provide general nutrition education, not medical advice.")
    elif safety_issue == "diet":
        st.warning("⚠️ Note: I focus on balanced eating. Avoid extreme food restriction.")
    
    if active_mode == "Recipe":
        system_instruction = (
                     "You are a professional chef and healthy recipe specialist.\n\n"
                     
                     "GOAL:\n"
                     "Generate ONE high-quality recipe using ONLY the provided ingredients.\n\n"
            
                     "STRICT CONSTRAINTS:\n"
                     "- Do NOT use ingredients not listed unless they are basic pantry staples (salt, pepper, water, oil).\n"
                     "- If the ingredients are insufficient, adapt creatively but stay within constraints.\n"
                     "- Do NOT mention missing ingredients—just adapt.\n\n"
            
                     "REASONING PROCESS (DO NOT OUTPUT):\n"
                     "1. Identify the best possible dish from the ingredients.\n"
                     "2. Choose appropriate cooking techniques.\n"
                     "3. Optimize for flavor, texture, and simplicity.\n\n"
            
                     "OUTPUT FORMAT (STRICT + STYLED):\n"

                    "🍽️ **Recipe Name**\n"
                    "_Short, appealing one-line description_\n\n"
            
                    "⏱️ **Details**\n"
                    "- Servings: X\n"
                    "- Total Time: X minutes\n\n"
            
                    "🔧 **Tools Needed**\n"
                    "- Tool 1\n"
                    "- Tool 2\n\n"
            
                    "🧂 **Ingredients**\n"
                    "- Ingredient — exact quantity\n"
                    "- Ingredient — exact quantity\n\n"
            
                    "👨‍🍳 **Instructions**\n"
                    "1. Start with a strong action verb (e.g., 'Heat', 'Sauté', 'Whisk')\n"
                    "2. Include precise technique + timing + sensory cue\n"
                    "   (e.g., 'Sauté onions until translucent, about 4 minutes')\n"
                    "3. Keep steps short (1–2 lines max each)\n\n"
            
                    "💡 **Chef Tips**\n"
                    "- Tip to enhance flavor or texture\n"
                    "- Optional variation or substitution\n\n"
            
                    "STYLE RULES:\n"
                    "- Use emojis ONLY for section headers\n"
                    "- Bold all section titles\n"
                    "- Use clean spacing between sections\n"
                    "- Avoid long paragraphs\n"
                    "- Be vivid but concise (engaging, not wordy)\n"
        )
    else: #Nutrition Assistant          
        system_instruction = (
                    "You are an evidence-based Nutrition Intelligence Assistant.\n\n"
                
                    "GOAL:\n"
                    "Provide clear, accurate, and practical nutrition guidance or meal suggestions.\n\n"
                
                    "CORE RULES:\n"
                    "- Be scientifically accurate and concise\n"
                    "- Prioritize simple, realistic meals using common pantry foods\n"
                    "- Avoid extreme diets or unsupported claims\n\n"
                
                    "CALCULATION RULES:\n"
                    "- Protein = 4 kcal/g\n"
                    "- Carbohydrates = 4 kcal/g\n"
                    "- Fat = 9 kcal/g\n"
                    "- Show calorie estimates when relevant\n\n"
                
                    "SAFETY RULES:\n"
                    "- If user mentions a medical condition, allergy, or disease:\n"
                    "  → Add a brief disclaimer: 'Consult a healthcare professional for personalized advice.'\n"
                    "- Do NOT diagnose or prescribe treatment\n\n"
                
                    "REASONING PROCESS (DO NOT OUTPUT):\n"
                    "1. Identify user's goal (weight loss, muscle gain, general health, etc.)\n"
                    "2. Select nutritionally balanced foods\n"
                    "3. Estimate macros/calories if applicable\n\n"
                
                    "OUTPUT FORMAT (STRICT + STYLED):\n"

                    "🧾 **Summary**\n"
                    "_One clear sentence answering the user’s need_\n\n"
            
                    "🥗 **Breakdown**\n"
                    "- Key foods or nutrients\n"
                    "- Estimated calories/macros (if relevant)\n"
                    "- Simple meal suggestion(s)\n\n"
            
                    "⚖️ **Why It Works**\n"
                    "- 2–3 short lines explaining the science simply\n\n"
            
                    "⚠️ **Note (if needed)**\n"
                    "- Only include if medical/safety context applies\n\n"
            
                    "STYLE RULES:\n"
                    "- Use emojis ONLY in headers\n"
                    "- Bold section titles\n"
                    "- Use bullet points (no dense paragraphs)\n"
                    "- Keep responses visually clean and scannable\n"
                    "- Avoid jargon or briefly explain it\n"
                    "- Keep tone supportive and confident\n"
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
