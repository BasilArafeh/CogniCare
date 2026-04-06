# step1: extract text from pdf using unstrcutured to get headers and titles and keep their meaning

from unstructured.partition.pdf import partition_pdf


def extract_pdf_elements(file_path: str):
    elements = partition_pdf(
        filename=file_path,
        strategy="fast"
    )
    return elements


def preview_elements(elements, n=20):
    for i, el in enumerate(elements[:n]):
        text_preview = el.text[:100].replace("\n", " ") if el.text else ""
        print(f"{i+1}. [{el.category}] → {text_preview}")