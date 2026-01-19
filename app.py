import streamlit as st
import requests
import json
import PyPDF2
import pandas as pd
import io
import re
from docx import Document

# =========================
# Azure OpenAI configuration
# =========================

api_key = st.secrets["AZURE_OPENAI_API_KEY"]

AZURE_ENDPOINT = "https://mcqchatbot.openai.azure.com"
AZURE_DEPLOYMENT_NAME = "gpt-4.1"
AZURE_API_VERSION = "024-12-01-preview"


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
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
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
    page_texts = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        full_text += f"[PAGE {i + 1}]\n{text}\n\n"
        page_texts.append((i + 1, text))

    return full_text, reader, page_texts


# =========================
# MCQ parser
# =========================

def parse_mcqs(response_text: str):
    mcqs = []
    blocks = re.split(r'(?=\d+\.\s)', response_text)

    for block in blocks:
        if not block.strip():
            continue

        q_match = re.search(r'(\d+)\.\s+(.*?)(?=\nA\)|\Z)', block, re.DOTALL)
        if not q_match:
            continue

        number = q_match.group(1)
        question = q_match.group(2).strip()

        options = {}
        for letter in ["A", "B", "C", "D", "E"]:
            m = re.search(
                rf'{letter}\)\s+(.*?)(?=\n[A-E]\)|\nCorrect|\Z)',
                block,
                re.DOTALL
            )
            if m:
                options[letter] = m.group(1).strip()

        ans_match = re.search(r'Correct Answer:\s*([A-E])', block)
        answer = ans_match.group(1) if ans_match else None

        page_match = re.search(r'Page\s+(\d+)', block, re.IGNORECASE)
        page = page_match.group(1) if page_match else "N/A"

        if len(options) == 5 and answer:
            mcqs.append({
                "number": number,
                "question": question,
                "options": options,
                "answer": answer,
                "page": page
            })

    return mcqs


# =========================
# Streamlit UI
# =========================

st.title("🦷 Prosthodontic MCQ Generator")
st.caption("Clinical scenario-based MCQs for postgraduate assessment")

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

    num_questions = st.slider(
        "Number of MCQs",
        1,
        10,
        5
    )

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

custom_prompt = st.text_area(
    "Additional Instructions (optional)",
    placeholder="Focus on fixed prosthodontics, implant planning, material selection…",
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
        pdf_text, reader, _ = extract_text_from_pdf(uploaded_file)

    cog_code = cognition_level.split(" ")[0]

    prompt = f"""
You are a senior PROSTHODONTIST preparing MCQs for postgraduate residents.

Generate exactly {num_questions} MCQs from the content below.

PDF CONTENT:
{pdf_text}

Target Bloom’s level: {cognition_level}
Difficulty: {difficulty_level}

Rules:
- Start each question with a realistic clinical scenario.
- Provide exactly five options (A–E).
- Only one option is correct.
- Write clearly and professionally.
- Avoid artificial or mechanical phrasing.

{custom_prompt}

FORMAT STRICTLY AS:

1. Clinical scenario...

Question text?

A) Option
B) Option
C) Option
D) Option
E) Option

Correct Answer: A
"""

    with st.spinner("Generating MCQs…"):
        response = call_azure_openai_api(prompt)

    if not response:
        st.stop()

    st.success("MCQs generated")

    with st.expander("Raw model output"):
        st.text(response)

    mcqs = parse_mcqs(response)

    if not mcqs:
        st.error("Parsing failed. Check output format.")
        st.stop()

    for mcq in mcqs:
        st.markdown(f"### Question {mcq['number']}")
        st.write(mcq["question"])
        for k, v in mcq["options"].items():
            st.write(f"{k}) {v}")
        st.markdown(f"**Correct Answer:** {mcq['answer']}")
        st.markdown("---")

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
