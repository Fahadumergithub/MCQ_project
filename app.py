import streamlit as st
import requests
import json
import PyPDF2
import pandas as pd

# =========================
# Azure OpenAI configuration
# =========================

api_key = st.secrets["AZURE_OPENAI_API_KEY"]

AZURE_ENDPOINT = "https://mcqchatbot.openai.azure.com"
AZURE_DEPLOYMENT_NAME = "gpt-4.1"
AZURE_API_VERSION = "2024-12-01-preview"


# =========================
# Azure OpenAI call
# =========================

def call_azure_openai_api(prompt: str) -> str | None:
    url = (
        f"{AZURE_ENDPOINT}/openai/deployments/"
        f"{AZURE_DEPLOYMENT_NAME}/chat/completions"
        f"?api-version={AZURE_API_VERSION}"
    )

    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }

    body = {
        "messages": [
            {"role": "system", "content": "You are a precise JSON generator. Always return valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4,
        "max_tokens": 8192
    }

    response = requests.post(url, headers=headers, json=body)

    if response.status_code != 200:
        st.error(f"Azure OpenAI error ({response.status_code})")
        st.code(response.text)
        return None

    data = response.json()
    return data["choices"][0]["message"]["content"]


# =========================
# PDF utilities
# =========================

def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    full_text = ""

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        full_text += f"[PAGE {i + 1}]\n{text}\n\n"

    return full_text


# =========================
# JSON Parser (Robust)
# =========================

def parse_json_mcqs(response_text):
    try:
        # Remove markdown if model adds it
        if "```" in response_text:
            response_text = response_text.split("```")[1]

        data = json.loads(response_text)

        validated = []

        for i, item in enumerate(data):
            if (
                "question" in item and
                "options" in item and
                "answer" in item and
                len(item["options"]) == 5
            ):
                validated.append(item)

        return validated

    except Exception as e:
        st.error("JSON parsing failed")
        st.code(str(e))
        st.text(response_text)
        return None


# =========================
# Streamlit UI
# =========================

st.title("🦷 MCQ Generator")
st.caption("Clinical scenario-based MCQ")

with st.sidebar:
    st.header("Configuration")

    cognition_level = st.selectbox(
        "Bloom’s Cognitive Level",
        [
            "C1 - Knowledge",
            "C2 - Comprehension",
            "C3 - Application",
            "C4 - Analysis",
            "C5 - Synthesis",
            "C6 - Evaluation"
        ],
        index=2
    )

    difficulty_level = st.selectbox(
        "Difficulty",
        ["Easy", "Moderate", "Hard"],
        index=1
    )

    num_questions = st.slider("Number of MCQs", 1, 10, 5)

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

custom_prompt = st.text_area(
    "Additional Instructions (optional)",
    height=90
)


# =========================
# Generate MCQs
# =========================

if st.button("Generate MCQs", type="primary"):

    if not uploaded_file:
        st.warning("Please upload a PDF.")
        st.stop()

    with st.spinner("Extracting PDF content…"):
        pdf_text = extract_text_from_pdf(uploaded_file)

    prompt = f"""
Generate exactly {num_questions} dentistry MCQs from the content below.

PDF CONTENT:
{pdf_text}

Requirements:
- Clinical scenario based
- Bloom’s level: {cognition_level}
- Difficulty: {difficulty_level}
- Exactly five options (A–E)
- Only one correct answer

IMPORTANT:
- Distribute correct answers across A–E (avoid repeating same answer)
- Keep all options similar in length and plausibility

Return ONLY valid JSON in this format:

[
  {{
    "question": "Clinical scenario...",
    "options": {{
      "A": "...",
      "B": "...",
      "C": "...",
      "D": "...",
      "E": "..."
    }},
    "answer": "C"
  }}
]

{custom_prompt}
"""

    with st.spinner("Generating MCQs…"):
        response = call_azure_openai_api(prompt)

    if not response:
        st.stop()

    mcqs = parse_json_mcqs(response)

    if not mcqs:
        st.error("Parsing failed. Model did not return valid JSON.")
        st.stop()

    st.success("MCQs generated")

    # =========================
    # Display MCQs
    # =========================

    for i, mcq in enumerate(mcqs, 1):
        st.markdown(f"### Question {i}")
        st.write(mcq["question"])

        for key, value in mcq["options"].items():
            st.write(f"{key}) {value}")

        st.markdown(f"**Correct Answer:** {mcq['answer']}")
        st.markdown("---")

    # =========================
    # DataFrame + Download
    # =========================

    df = pd.DataFrame([
        {
            "Question": m["question"],
            "A": m["options"]["A"],
            "B": m["options"]["B"],
            "C": m["options"]["C"],
            "D": m["options"]["D"],
            "E": m["options"]["E"],
            "Answer": m["answer"]
        }
        for m in mcqs
    ])

    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download CSV",
        csv,
        "mcqs.csv",
        "text/csv"
    )


# =========================
# Footer
# =========================

st.markdown("---")
st.markdown(
    "<center>Powered by Medentec · Dr. Fahad Umer</center>",
    unsafe_allow_html=True
)
