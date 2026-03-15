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
"This information is for general nutrition education and is not medical advice."
)

# --------------------
# LOAD MODEL
# --------------------

@st.cache_resource
def load_model():
    model_id = "google/flan-t5-small"
    # Explicitly load the model and tokenizer classes
    model_obj = AutoModelForSeq2SeqLM.from_pretrained(model_id)
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    
    # Pass the objects directly into the pipeline
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

        system_prompt = """You are a friendly nutrition assistant helping families using a food pantry.

Suggest simple healthy meals using pantry foods like: rice, beans, pasta, canned vegetables, oats, peanut butter, tuna.

Use simple language."""
# T5 is very sensitive to structure; use "Answer this question:" 
        formatted_prompt = f"Context: {system_prompt}\n\nQuestion: {prompt}\n\nAnswer:"

        # Call the model
        response = model(
            input_text,
            max_new_tokens=100,
            do_sample=True,
            temperature=0.7,
            clean_up_tokenization_spaces=True
        )

        #Simplified extraction: Seq2Seq models don't return the prompt
        answer = response[0]["generated_text"].strip()

        # If the model returns nothing, provide a fallback
        if not answer:
            answer = "I'm sorry, I couldn't generate a suggestion. Could you try rephrasing?"

    with st.chat_message("assistant"):
        st.write(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
