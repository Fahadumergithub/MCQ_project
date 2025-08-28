import os
import requests
import pandas as pd
from io import StringIO
from flask import Flask, render_template, request

app = Flask(__name__)

# Azure OpenAI config
AZURE_OPENAI_ENDPOINT = "https://mcqgpt.openai.azure.com"
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")  # set in your environment
DEPLOYMENT_NAME = "o4-mini"
API_VERSION = "2024-12-01-preview"

def generate_mcqs(prompt: str):
    """
    Calls Azure OpenAI to generate MCQs in CSV format
    """
    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version={API_VERSION}"

    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_KEY
    }

    body = {
        "messages": [
            {"role": "system", "content": "You are an assistant that generates multiple-choice questions (MCQs) for dental education."},
            {"role": "user", "content": f"""
Generate 5 MCQs from the following text. 
Return the output ONLY as a CSV table with these exact columns:
Question | Options | Answer | Cognitive Level | Difficulty Level | Page Number | PDF Document Name

Text: {prompt}
"""}
        ],
        "temperature": 1.0,
        "max_completion_tokens": 800  # safe buffer
    }

    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()
    response_json = response.json()

    # Get model reply
    raw_output = response_json["choices"][0]["message"]["content"]
    print("RAW RESPONSE:\n", raw_output)  # 🔍 Debugging step

    # Try parsing as CSV
    try:
        # Remove markdown fences if present
        cleaned_output = raw_output.strip().replace("```csv", "").replace("```", "")
        df = pd.read_csv(StringIO(cleaned_output), sep="|")
        df = df.applymap(lambda x: str(x).strip())  # clean spaces
        return df
    except Exception as e:
        print("Parsing error:", e)
        return pd.DataFrame(columns=[
            "Question", "Options", "Answer",
            "Cognitive Level", "Difficulty Level",
            "Page Number", "PDF Document Name"
        ])

@app.route("/", methods=["GET", "POST"])
def index():
    mcq_table = None
    if request.method == "POST":
        text = request.form["text"]
        mcq_table = generate_mcqs(text)
    return render_template("index.html", tables=[mcq_table.to_html(classes='data')] if mcq_table is not None else [])

if __name__ == "__main__":
    app.run(debug=True)
