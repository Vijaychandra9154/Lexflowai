import argparse
import json
import os
import requests

BASE = os.getenv("LEXFLOW_BASE", "http://localhost:8000")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--template", required=True)
    p.add_argument("--case-id", type=int, required=True)
    p.add_argument("--instruction", default="")
    args = p.parse_args()

    with open("prompt_templates/prompt_templates.json", encoding="utf-8") as f:
        templates = json.load(f)

    if args.template not in templates:
        print("Template not found")
        raise SystemExit(1)

    prompt = templates[args.template]
    if args.instruction:
        prompt = prompt + "\n\n" + args.instruction

    payload = {
        "case_id": args.case_id,
        "prompt_context": args.instruction or prompt[:200],
        "instruction": prompt,
    }
    resp = requests.post(BASE + "/api/ai/draft", json=payload)
    print(resp.json())
