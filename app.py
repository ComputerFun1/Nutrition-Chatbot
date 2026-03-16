import streamlit as st
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline
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
# LOAD MODEL
# --------------------

@st.cache_resource
def load_model():
    # Using the 1.5B Instruct version for best balance of memory and logic
    model_id = "Qwen/Qwen2.5-1.5B-Instruct" 
    
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    # Use 4-bit or 8-bit here if you have bitsandbytes installed to save even more RAM
    model_obj = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype="auto",
        device_map="auto"
    )
    
    generator = pipeline(
        "text-generation", 
        model=model_obj, 
        tokenizer=tokenizer
    )
    return generator

model = load_model()

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

    foods = [f.strip().lower() for f in foods.split(",")]

    matches = []

    for recipe in PANTRY_RECIPES:

        if all(item in foods for item in recipe["ingredients"]):
            matches.append(recipe)

    return matches

if st.button("Find Meal Ideas"):

    recipes = find_recipe(user_foods)

    if recipes:
        for r in recipes:
            st.write("### " + r["name"])
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

#Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

prompt = st.chat_input("Ask about meals or pantry foods")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    # SAFETY CHECK
    safety = check_guardrails(prompt)

    if safety == "medical":
        answer = (
            "I can only provide general nutrition information. "
            "For medical advice, please speak with a healthcare professional.\n\n"
            "This information is for general nutrition education and is not medical advice."
        )

    elif safety == "diet":
        answer = (
            "I focus on balanced and healthy eating. Extreme dieting or food restriction "
            "can be harmful. Try focusing on balanced meals with the foods you have available."
        )

    else:
            # 1. DEFINE SYSTEM PROMPT (The "Brain" of the bot)
            system_instruction = (
                "You are a precise, evidence-based Nutrition Intelligence Assistant. "
                "Suggest simple healthy meals using pantry foods. "
                "Safety: If medical conditions are mentioned, provide a disclaimer. "
                "Precision: Use 4 kcal/g for protein/carbs and 9 kcal/g for fats if calculating. "
                "Format: Start with a 1-sentence Summary, then a bulleted Breakdown, then a brief 'Why'."
            )
    
            # 2. BUILD CHAT TEMPLATE (Qwen specific format)
            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ]
            
            # Apply the chat template for better instruction following
            formatted_prompt = model.tokenizer.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True
            )
    
            with st.spinner("Analyzing nutrition data..."):
                response = model(
                    formatted_prompt,
                    max_new_tokens=256, # Increased from 100 for better explanations
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                    pad_token_id=model.tokenizer.eos_token_id
                )
                
                # Extract only the newly generated text
                full_text = response[0]["generated_text"]
                answer = full_text.split("<|im_start|>assistant\n")[-1].strip()
    
    with st.chat_message("assistant"):
        st.write(answer)
    
    st.session_state.messages.append({"role": "assistant", "content": answer})
