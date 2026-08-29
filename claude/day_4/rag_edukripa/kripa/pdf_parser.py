"""
Extracts text from a PDF, page by page.
We keep page numbers attached to each chunk of text so that later,
when we retrieve a chunk, we can tell the user roughly where it came from.
"""

import fitz  # this is PyMuPDF's import name, not a typo


def extract_pages(pdf_path: str) -> list[dict]:
    """
    Returns a list of {"page": int, "text": str} dicts, one per page.
    Skips pages that are empty (e.g. blank pages, pure-image pages with no text layer).
    """
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    pages = []

    for page_num in range(total_pages):
        page = doc[page_num]
        text = page.get_text().strip()
        if text:  # skip empty pages
            pages.append({"page": page_num + 1, "text": text})

    doc.close()
    print(f"Extracted text from {len(pages)} non-empty pages (out of {total_pages} total).")
    return pages


if __name__ == "__main__":
    # quick manual test: python pdf_parser.py path/to/file.pdf
    import sys

    if len(sys.argv) != 2:
        print("Usage: python pdf_parser.py <path_to_pdf>")
        sys.exit(1)

    result = extract_pages(sys.argv[1])
    print(f"\nFirst page preview:\n{result[0]['text'][:500]}")
