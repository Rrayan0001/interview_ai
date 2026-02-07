#!/usr/bin/env python3
import argparse
import os
import sys
from typing import List, Optional

try:
    from pypdf import PdfReader
except ImportError:
    print("Missing dependency 'pypdf'. Install with: pip install pypdf", file=sys.stderr)
    raise


def read_pdf_text(file_path: str) -> str:
    reader = PdfReader(file_path)
    pages_text: List[str] = []
    for page_index, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
        except Exception as extract_err:
            page_text = ""
            print(f"Warning: failed to extract text from page {page_index + 1}: {extract_err}", file=sys.stderr)
        pages_text.append(page_text)
    return "\n".join(pages_text).strip()


def chunk_text(text: str, max_chars: int) -> List[str]:
    if len(text) <= max_chars:
        return [text]
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        # try to break on a paragraph boundary
        split_at = text.rfind("\n\n", start, end)
        if split_at == -1:
            split_at = text.rfind("\n", start, end)
        if split_at == -1:
            split_at = end
        chunks.append(text[start:split_at])
        start = split_at
        # skip any extra newlines at the start of next chunk
        while start < len(text) and text[start] == "\n":
            start += 1
    return [c for c in (c.strip() for c in chunks) if c]


def clean_with_groq_llm(text: str, model: str, api_key: Optional[str], verbose: bool = False) -> str:
    """
    Sends the extracted text to a Groq LLM for light cleanup/normalization.
    This does not perform OCR; it only cleans already-extracted text.
    """
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Please set the environment variable or pass --groq-api-key.")
    try:
        from groq import Groq
    except ImportError:
        print("Missing dependency 'groq'. Install with: pip install groq", file=sys.stderr)
        raise

    client = Groq(api_key=api_key)

    # Keep chunks conservative to stay within model context limits.
    # Adjust if you use a larger-context model.
    chunks = chunk_text(text, max_chars=12000)
    cleaned_chunks: List[str] = []
    system_prompt = (
        "You receive raw text extracted from a PDF. "
        "Return the same content with line-wrapped paragraphs merged, hyphenation at line breaks fixed, "
        "and spurious whitespace removed. Preserve headings and lists when obvious. Do not summarize."
    )

    for idx, chunk in enumerate(chunks, start=1):
        if verbose:
            print(f"[groq] calling model='{model}' for chunk {idx}/{len(chunks)} (chars={len(chunk)})", file=sys.stderr)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": chunk},
        ]
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0,
        )
        if verbose:
            try:
                usage = getattr(response, "usage", None)
                if usage:
                    prompt_t = getattr(usage, "prompt_tokens", None)
                    comp_t = getattr(usage, "completion_tokens", None)
                    total_t = getattr(usage, "total_tokens", None)
                    print(f"[groq] received response: prompt_tokens={prompt_t}, completion_tokens={comp_t}, total_tokens={total_t}", file=sys.stderr)
                else:
                    print("[groq] received response (usage not provided)", file=sys.stderr)
            except Exception as _:
                print("[groq] received response (unable to read usage)", file=sys.stderr)
        cleaned = response.choices[0].message.content or ""
        cleaned_chunks.append(cleaned.strip())
        # Stream-friendly behavior could be added, but we keep it simple/non-interactive here.
    return "\n\n".join(cleaned_chunks).strip()


def parse_resume_with_groq(
    text: str,
    model: str,
    api_key: Optional[str],
    verbose: bool = False,
    output_format: str = "json",
    output_preset: str = "full",
) -> str:
    """
    Parse resume/CV content into structured fields using Groq.
    By default returns strict JSON. Optionally returns a concise markdown summary.
    """
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Please set the environment variable or pass --groq-api-key.")
    try:
        from groq import Groq
    except ImportError:
        print("Missing dependency 'groq'. Install with: pip install groq", file=sys.stderr)
        raise

    client = Groq(api_key=api_key)

    # Resumes are typically short; still guard with chunking to be safe.
    chunks = chunk_text(text, max_chars=12000)
    if len(chunks) > 1:
        # Merge chunks before sending to ensure single holistic parse
        merged_text = "\n\n".join(chunks)
    else:
        merged_text = text

    if output_format.lower() == "json" and output_preset == "full":
        system_prompt = (
            "You MUST return only valid JSON. No markdown. No prose. No explanations.\n"
            "Escape all quotes inside strings using backslash.\n"
            "Do NOT include trailing commas.\n"
            "Structure exactly like this:\n"
            "\n"
            "{\n"
            "  \"name\": \"\",\n"
            "  \"email\": \"\",\n"
            "  \"phone\": \"\",\n"
            "  \"links\": {\n"
            "    \"linkedin\": \"\",\n"
            "    \"github\": \"\",\n"
            "    \"portfolio\": \"\",\n"
            "    \"other\": []\n"
            "  },\n"
            "  \"summary\": \"\",\n"
            "  \"education\": [\n"
            "    {\n"
            "      \"institution\": \"\",\n"
            "      \"degree\": \"\",\n"
            "      \"field\": \"\",\n"
            "      \"start\": \"\",\n"
            "      \"end\": \"\",\n"
            "      \"grade_type\": \"CGPA\" | \"Percentage\" | null,\n"
            "      \"grade_value\": \"\"\n"
            "    }\n"
            "  ],\n"
            "  \"experience\": [\n"
            "    {\n"
            "      \"title\": \"\",\n"
            "      \"company\": \"\",\n"
            "      \"location\": \"\",\n"
            "      \"start\": \"\",\n"
            "      \"end\": \"\",\n"
            "      \"bullets\": []\n"
            "    }\n"
            "  ],\n"
            "  \"projects\": [\n"
            "    {\n"
            "      \"name\": \"\",\n"
            "      \"description\": \"\",\n"
            "      \"tech_stack\": []\n"
            "    }\n"
            "  ],\n"
            "  \"skills\": {\n"
            "    \"programming_languages\": [],\n"
            "    \"frameworks_libraries\": [],\n"
            "    \"tools\": [],\n"
            "    \"other\": []\n"
            "  }\n"
            "}\n"
            "\n"
            "CRITICAL RULES:\n"
            "- Populate fields from the resume text.\n"
            "- Use null for missing values, empty strings \"\" for empty text, empty arrays [] for empty lists.\n"
            "- Escape quotes inside strings: \"He said \\\"hello\\\"\"\n"
            "- NO trailing commas after last item in objects/arrays.\n"
            "- Your output must be parseable by json.loads() - test it mentally before responding."
        )
    elif output_format.lower() == "json" and output_preset == "minimal":
        # Minimal schema with strict empty defaults when missing
        system_prompt = (
            "You are a resume parser. Extract only the specified fields from the resume text. "
            "Return STRICT JSON ONLY, with no code fences, no extra text. Use this schema:\n"
            "{\n"
            "  \"name\": string,\n"
            "  \"email\": string,\n"
            "  \"phone\": string,\n"
            "  \"experience\": string[],\n"
            "  \"tenth_percentage\": string,\n"
            "  \"twelfth_percentage\": string,\n"
            "  \"degree_percentage_or_cgpa\": string\n"
            "}\n"
            "Rules:\n"
            "- Fill missing or unavailable scalar fields with an empty string \"\".\n"
            "- Fill missing lists with an empty array [].\n"
            "- For experience, provide a short list of key experience lines (role @ company or top bullets).\n"
            "- For percentages/CGPA, extract numeric value with unit if present (e.g., \"91%\", \"8.40/10\"); if absent, use \"\".\n"
            "- Output strictly valid JSON with double quotes and no trailing commas."
        )
    elif output_format.lower() == "markdown":
        # Concise markdown summary
        system_prompt = (
            "You are a resume parser. Produce a concise markdown summary highlighting key details:\n"
            "- Name, Email, Phone, Links\n"
            "- Education (institution, degree/field, years, CGPA/Percentage)\n"
            "- Experience (company, title, dates, top highlights)\n"
            "- Projects (name, 1-line description, tech stack)\n"
            "- Skills (categorized)\n"
            "Be accurate and avoid inventing facts."
        )
    else:
        raise ValueError("Unsupported combination of output_format and output_preset")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": merged_text},
    ]
    if verbose:
        print(f"[groq] resume-parse calling model='{model}' (chars={len(merged_text)})", file=sys.stderr)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.0,
    )
    if verbose:
        try:
            usage = getattr(response, "usage", None)
            if usage:
                prompt_t = getattr(usage, "prompt_tokens", None)
                comp_t = getattr(usage, "completion_tokens", None)
                total_t = getattr(usage, "total_tokens", None)
                print(f"[groq] resume-parse response: prompt_tokens={prompt_t}, completion_tokens={comp_t}, total_tokens={total_t}", file=sys.stderr)
            else:
                print("[groq] resume-parse response (usage not provided)", file=sys.stderr)
        except Exception:
            print("[groq] resume-parse response (unable to read usage)", file=sys.stderr)
    content = response.choices[0].message.content or ""
    return content.strip()

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract text from a PDF; optionally clean it with a Groq LLM."
    )
    parser.add_argument("pdf_path", help="Path to the input PDF file")
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="If set, send extracted text to a Groq LLM for cleanup",
    )
    parser.add_argument(
        "--model",
        default="llama-3.1-8b-instant",
        help="Groq model to use when --use-llm is set (default: llama-3.1-8b-instant)",
    )
    parser.add_argument(
        "--groq-api-key",
        default=os.environ.get("GROQ_API_KEY"),
        help="Groq API key. If omitted, reads GROQ_API_KEY from environment.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logs (e.g., Groq API call traces) to stderr.",
    )
    parser.add_argument(
        "--resume-parse",
        action="store_true",
        help="If set, parse resume/CV content into structured fields using Groq.",
    )
    parser.add_argument(
        "--resume-output-preset",
        choices=["full", "minimal"],
        default="full",
        help="Preset for resume parsing fields (default: full; use 'minimal' for limited fields).",
    )
    parser.add_argument(
        "--resume-output-format",
        choices=["json", "markdown"],
        default="json",
        help="Output format when using --resume-parse (default: json).",
    )
    args = parser.parse_args()

    pdf_path = args.pdf_path
    if not os.path.isfile(pdf_path):
        print(f"File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    extracted_text = read_pdf_text(pdf_path)

    if not extracted_text:
        print(
            "No text could be extracted. The PDF may be scanned (image-only). "
            "Consider OCR (e.g., pytesseract) if you need text from scanned PDFs.",
            file=sys.stderr,
        )
        print("")  # Print empty output to STDOUT for clarity
        sys.exit(0)

    if args.resume_parse:
        try:
            parsed = parse_resume_with_groq(
                text=extracted_text,
                model=args.model,
                api_key=args.groq_api_key,
                verbose=args.verbose,
                output_format=args.resume_output_format,
                output_preset=args.resume_output_preset,
            )
            print(parsed)
        except Exception as err:
            print(f"Resume parsing failed. Error: {err}", file=sys.stderr)
            print(extracted_text)
    elif args.use_llm:
        try:
            cleaned = clean_with_groq_llm(
                text=extracted_text, model=args.model, api_key=args.groq_api_key, verbose=args.verbose
            )
            print(cleaned)
        except Exception as err:
            print(f"LLM cleanup failed, returning raw extracted text. Error: {err}", file=sys.stderr)
            print(extracted_text)
    else:
        print(extracted_text)


if __name__ == "__main__":
    main()


