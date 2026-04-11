# Tool for reading a local PDF paper.
#
# The @function_tool wrapper gets the paper path from the SDK context,
# so the LLM never sees the actual file path — it just calls "read_paper".

from agents import RunContextWrapper, function_tool
from pypdf import PdfReader

from research_agents.project import ResearchContext


def read_paper_text(paper_path: str) -> str:
    """Extract all text from a PDF, page by page."""
    reader = PdfReader(paper_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)

    full_text = "\n\n".join(pages)
    if not full_text.strip():
        raise ValueError("PDF contained no extractable text")

    return full_text


@function_tool
def read_paper(context: RunContextWrapper[ResearchContext]) -> str:
    """Read the local project paper and return its text.

    Note: only text is extracted — images, figures, and scanned
    pages won't be captured.
    """
    paper_path = context.context.paper_path
    return f"Contents of {paper_path}:\n{read_paper_text(str(paper_path))}"
