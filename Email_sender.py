import requests
import pandas as pd
from bs4 import BeautifulSoup
from transformers import pipeline
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
import transformers

# --------------------------
# Step 1: Scrape Hacker News
# --------------------------
def search_hackernews_saas(keywords, max_pages=2):
    base_url = "https://hn.algolia.com/api/v1/search"
    results = []

    for keyword in keywords:
        for page in range(max_pages):
            params = {
                "query": keyword,
                "tags": "story",
                "page": page
            }

            r = requests.get(base_url, params=params)
            if r.status_code != 200:
                continue

            data = r.json()
            for hit in data["hits"]:
                results.append({
                    "date": datetime.fromtimestamp(hit["created_at_i"]).strftime("%Y-%m-%d"),
                    "saas_tool": keyword,
                    "title": hit.get("title", ""),
                    "link": hit.get("url") or f'https://news.ycombinator.com/item?id={hit["objectID"]}',
                    "points": hit.get("points", 0),
                    "comments": hit.get("num_comments", 0)
                })

    return pd.DataFrame(results)

# --------------------------
# Step 2: Summarize per tool
# --------------------------
def summarize_titles_grouped(df, summarizer):
    if df.empty:
        return "No relevant Hacker News posts found today."

    grouped = df.groupby("saas_tool")["title"].apply(list)
    summaries = []

    for tool, titles in grouped.items():
        input_text = f"The following Hacker News posts today mention {tool}:\n"
        input_text += "\n".join(f"- {t}" for t in titles[:5])
        input_text += "\nWrite a paragraph summarizing the above."

        if len(input_text) > 2048:
            input_text = input_text[:2048]

        try:
            result = summarizer(input_text, max_length=200, min_length=60, do_sample=False)
            summary_text = result[0]['summary_text']
        except Exception as e:
            summary_text = f"[Error summarizing {tool}: {e}]"

        summaries.append(f"🔹 {tool}:\n{summary_text}\n")

    return "\n".join(summaries)

# --------------------------
# Step 3: Email function
# --------------------------
def send_email(summary_text, recipients):
    sender_email = "aautom621@gmail.com"
    subject = f"SaaS Trend Summary - {datetime.today().strftime('%Y-%m-%d')}"

    for receiver_email in recipients:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject

        body = MIMEText(summary_text, 'plain')
        msg.attach(body)

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login("aautom621@gmail.com", "nznfykwlccbhbrzf")
            server.send_message(msg)

# --------------------------
# Step 4: Main execution
# --------------------------
def main():
    saas_tools = [
        "Notion", "Zapier", "Airtable", "Figma", "Slack", "Linear", "n8n",
        "ClickUp", "Asana", "Trello", "Webflow", "Calendly", "Superhuman",
        "Loom", "Softr", "Retool", "Framer", "Bubble", "Ghost", "Obsidian",
        "Basecamp", "Pitch", "Coda", "Jira", "Monday.com", "Freshdesk"
    ]
    df = search_hackernews_saas(saas_tools, max_pages=2)
    os.environ["TRANSFORMERS_BACKEND"] = "pt"  # pt = PyTorch
    summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6", device=-1)
    summary = summarize_titles_grouped(df, summarizer)

    recipients = ["amavrits@gmail.com", "credekker@gmail.com", "panagiotismavritsakis@gmail.com", "imavrit@yahoo.gr"]  # ← Add as many as you want
    send_email(summary, recipients)

if __name__ == "__main__":
    main()
