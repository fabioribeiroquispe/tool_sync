import os
import re
import logging
from typing import List, Dict, Any

import yaml
from bs4 import BeautifulSoup
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Constants ---
CODE_FILE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".cs", ".go", ".rs", ".c", ".cpp", ".h", ".hpp",
    ".html", ".css", ".scss", ".sql", ".sh", ".rb", ".php", ".swift", ".kt",
}

# --- ChromaDB Initialization ---
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
db_client = chromadb.PersistentClient(
    path="chroma_db",
    settings=Settings(anonymized_telemetry=False)
)
# Using a more generic collection name
collection = db_client.get_or_create_collection(name="project_knowledge_base")

# --- Parsers ---

def _parse_work_item_file(file_path: str) -> Dict[str, Any] | None:
    """
    Parses a single work item file with YAML front matter.
    Returns a dictionary with parsed data or None if it's not a valid work item file.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        front_matter_match = re.match(r"---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
        if not front_matter_match:
            return None # Not a valid work item file

        front_matter_str, body = front_matter_match.groups()
        metadata = yaml.safe_load(front_matter_str) or {}

        soup = BeautifulSoup(body, 'html.parser')
        cleaned_body = soup.get_text(separator=' ', strip=True)

        return {
            "id": str(metadata.get("id")),
            "text_to_embed": f"Title: {metadata.get('title', '')}\n\n{cleaned_body}",
            "metadata": { "file_type": "work_item", "file_path": file_path, **metadata }
        }
    except Exception:
        logger.warning(f"Could not parse work item {file_path}, treating as plain text.")
        return None

def _parse_plain_text_file(file_path: str) -> Dict[str, Any] | None:
    """
    Parses any file as plain text. Used for source code and other documents.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if not content.strip():
            return None # Skip empty files

        return {
            "id": file_path, # Use file path as the unique ID for code files
            "text_to_embed": content,
            "metadata": { "file_type": "source_code", "file_path": file_path }
        }
    except Exception as e:
        logger.error(f"Error reading file {file_path} as plain text: {e}")
        return None

# --- Main Indexing Logic ---

def build_index(paths_to_index: List[str]):
    """
    Builds or updates the vector index from a list of local directories.
    It can index both structured work items (.md) and source code files.
    """
    logger.info(f"Starting to build vector index from paths: {paths_to_index}")

    documents = []
    metadatas = []
    ids = []

    for path in paths_to_index:
        if not os.path.isdir(path):
            logger.warning(f"Path '{path}' is not a valid directory, skipping.")
            continue

        for root, _, files in os.walk(path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                _, file_extension = os.path.splitext(file_name)

                parsed_data = None
                if file_extension == ".md":
                    # Try to parse as a work item first
                    parsed_data = _parse_work_item_file(file_path)

                if parsed_data is None and (file_extension == ".md" or file_extension in CODE_FILE_EXTENSIONS):
                    # If it's not a work item, or if it's a code file, parse as plain text
                    parsed_data = _parse_plain_text_file(file_path)

                if parsed_data:
                    documents.append(parsed_data["text_to_embed"])
                    metadatas.append(parsed_data["metadata"])
                    ids.append(parsed_data["id"])

    if not documents:
        logger.warning("No valid files found to index in the provided paths.")
        return

    logger.info(f"Found {len(documents)} documents to index. Generating embeddings...")
    embeddings = embedding_model.encode(documents, show_progress_bar=True).tolist()

    logger.info("Embeddings generated. Adding to the vector database...")
    collection.add(
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    logger.info(f"Successfully indexed {len(documents)} documents. Knowledge base is updated.")
