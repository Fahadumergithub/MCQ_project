import streamlit as st
from openai import AzureOpenAI
import pandas as pd
from docx import Document
import io

# -------------------------
# Azure OpenAI Configuration
# -------------------------
AZURE_OPENAI_ENDPOINT = "https://YOUR-RESOURCE-NAME.openai.azure.com/"  # e.g., https://medentec-openai.openai.azure.com/
AZURE_OPENAI_API_KEY = "YOUR-API-KEY"
AZURE_DEPLOYMENT_NAME = "gpt-4o-mini"  # replace with your deployment name

client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2024-08-01-preview"
)

# -------------------------
# Helper functions
# -------------------------

def generate_mcqs_with_azure(pdf_text, special_prompt, cog_level, diff_level):
    """
    Calls Azure OpenAI to generate MCQs in free text format (same as Gemini output).
    """
    system_prompt = (
        "You are an assistant that generates exam-style multiple-choice questions (MCQs) "
        "from provided academic text. Return output in plain text with the following format:\n\n"
        "Q: <question>\n"
        "A. <option1>\n"
        "B. <option2>\n"
        "C. <option3>\n"
        "D. <option4>\n"
        "E. <option5>\n"
        "Answer: <correct option letter>\n"
    )

    user_prompt = f"""
    Generate MCQs from the following text.

    Text: {pdf_text}

    Special Instructions: {special_prompt}
    Cognitive Level: {cog_level}
    Difficulty Level: {diff_level}

    Return ONLY the MCQs in the format shown above.
    """

    response = client.chat.completions.create(
        model=AZURE_DEPLOYMENT_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=1500,
    )

    return response.choices[0].message.content.strip()

def parse_mcqs(raw_text, pdf_name):
    """
    Parses raw MCQ text into a DataFrame with the same columns as before.
    """
    questions = []
    lines = raw_text.split("\n")
    q, opts, ans = None, [], None

    for line in lines:
        line = line.strip()
        if line.startswith("Q:"):
            if q:
                questions.append([q, opts, ans, "", "", "", pdf_name])
            q = line[2:].strip()
            opts = []
            ans = None
        elif line.startswith(("A.", "B.", "C.", "D.", "E.")):
            opts.append(line)
        elif line.startswith("Answer:"):
            ans = line.replace("Answer:", "").strip()

    # Add last question
    if q:
        questions.append([q, opts, ans, "", "", "", pdf_name])

    # Build DataFrame
    df = pd.DataFrame(questions, columns=[
        "Question",
        "Options",
        "Answer",
        "Cognitive Level",
        "Difficulty Level",
        "Page Number",
        "PDF Document Name"
    ])
    return df

def convert_df_to_word(df):
    """
    Converts DataFrame into a Word file.
    """
    doc = Document()
    for _, row in df.iterrows():
        doc.add_paragraph(f"Q: {row['Question']}")
        for opt in row['Options']:
            doc.add_paragraph(opt, style="List Bullet")
        doc.add_paragraph(f"Answer: {row['Answer']}")
        doc.add_paragraph("")  # blank line
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# -------------------------
# Streamlit UI
# -------------------------

st.set_page_config(page_title="MCQ Generator", layout="wide")

st.title("📘 Medentec MCQ Generator")
st.write("Upload a PDF, select parameters, and generate MCQs using Azure OpenAI.")

uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")

special_prompt = st.text_area("Special Prompt (optional)")
cog_level = st.selectbox("Cognitive Level", ["", "Recall", "Application", "Analysis", "Synthesis", "Evaluation"])
diff_level = st.selectbox("Difficulty Level", ["", "Easy", "Medium", "Hard"])

if st.button("Generate MCQs"):
    if uploaded_file is not None:
        pdf_name = uploaded_file.name
        # For now, skipping actual PDF text extraction
        # You can add PyPDF2 or pdfplumber if needed
        pdf_text = f"Sample text extracted from {pdf_name}"

        with st.spinner("Generating MCQs..."):
            raw_mcqs = generate_mcqs_with_azure(pdf_text, special_prompt, cog_level, diff_level)
            df = parse_mcqs(raw_mcqs, pdf_name)

        st.success("MCQs generated!")
        st.dataframe(df)

        # Download buttons
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download as CSV", csv, "mcqs.csv", "text/csv")

        word_file = convert_df_to_word(df)
        st.download_button("📥 Download as Word", word_file, "mcqs.docx")

        if st.button("Generate New MCQs"):
            st.experimental_rerun()

st.markdown("---")
st.markdown("**MediDentec | Developed by Fahad Umer**")
