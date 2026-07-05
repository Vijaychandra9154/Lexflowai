import os
import openai
from sentence_transformers import SentenceTransformer

openai.api_key = os.getenv("OPENAI_API_KEY")
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
embedder = SentenceTransformer(EMBED_MODEL)


def chunk_text(text: str, chunk_size: int = 2000):
  words = text.split()
  chunks = []
  for i in range(0, len(words), chunk_size):
    chunks.append(" ".join(words[i:i+chunk_size]))
  return chunks


def llm_draft(context_chunks, instruction: str):
  context = "\n\n".join(context_chunks)
  prompt = (
      f"Context: {context}\n\nInstruction: {instruction}\n\n"
      "Please draft a lawyer reply in an Indian legal tone. "
      "Provide references if possible and mark sections that need human verification."
  )
  resp = openai.ChatCompletion.create(
      model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
      messages=[
          {"role": "system", "content": "You are a legal drafting assistant."},
          {"role": "user", "content": prompt},
      ],
      max_tokens=800,
      temperature=0.2,
  )
  return resp["choices"][0]["message"]["content"]


if __name__ == "__main__":
  text = "\n".join([f"This is a sample judgment paragraph number {i}." for i in range(1, 200)])
  chunks = chunk_text(text, chunk_size=100)
  draft = llm_draft(
      chunks[:3],
      instruction="Draft a concise reply for a complainant asserting municipal liability for negligence."
  )
  print("\n\n===== DRAFT =====\n")
  print(draft)
