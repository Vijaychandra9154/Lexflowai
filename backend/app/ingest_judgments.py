"""Ingest public judgments (demo for IndianKanoon). Use responsibly and respect TOS."""
import argparse
import json
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from .ai_pinecone import add_texts_to_index


def fetch_indiankanoon(url: str):
    r = requests.get(url, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    content = " ".join(
        [p.get_text(separator=" ", strip=True) for p in soup.select("div#bodyContent p")]
    )
    title = soup.select_one("h2")
    title = title.get_text(strip=True) if title else url
    return title, content


def chunk_text_by_chars(text: str, chunk_size: int = 3000):
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + chunk_size])
        i += chunk_size
    return chunks


def ingest(urls, out_dir: str, push_to_pinecone: bool = False, rate_limit: float = 1.0):
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    for url in urls:
        url = url.strip()
        if not url:
            continue
        try:
            title, content = fetch_indiankanoon(url)
            chunks = chunk_text_by_chars(content)
            doc = {"url": url, "title": title, "chunks": chunks}
            fname = out_path / (str(abs(hash(url))) + ".json")
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            print("Saved", fname)
            if push_to_pinecone:
                add_texts_to_index(chunks, metadatas=[{"source": url, "title": title}] * len(chunks))
                print("Pushed to Pinecone", url)
            time.sleep(rate_limit)
        except Exception as e:
            print("Error", url, e)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--urls", required=True, help="file with list of judgment URLs")
    p.add_argument("--out", default="./data", help="output folder")
    p.add_argument("--to-pinecone", action="store_true")
    args = p.parse_args()
    with open(args.urls, "r", encoding="utf-8") as f:
        urls = f.read().splitlines()
    ingest(urls, args.out, push_to_pinecone=args.to_pinecone)
