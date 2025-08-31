import os
import re
import logging
from typing import List, Dict, Any, Generator

import yaml
from bs4 import BeautifulSoup
from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Constants ---
CODE_FILE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".cs", ".go", ".rs", ".c", ".cpp", ".h", ".hpp",
    ".html", ".css", ".scss", ".sql", ".sh", ".rb", ".php", ".swift", ".kt",
}
COLLECTION_NAME = "project_knowledge_base"
BATCH_SIZE = 32  # Process 32 files at a time to keep memory usage low

# --- Qdrant and Embedding Initialization ---
# Use BAAI/bge-small-en-v1.5, a small and efficient model
embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

# Initialize Qdrant client.
# Using in-memory storage for simplicity, but can be configured for on-disk storage
# For on-disk storage: client = QdrantClient(path="qdrant_db")
client = QdrantClient(":memory:")

# Get the dimension of the embeddings
embedding_dim = len(next(embedding_model.embed("test")))

# Create the collection if it doesn't exist
try:
    client.get_collection(collection_name=COLLECTION_NAME)
    logger.info(f"Collection '{COLLECTION_NAME}' already exists.")
except Exception:
    logger.info(f"Creating collection '{COLLECTION_NAME}'...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(size=embedding_dim, distance=models.Distance.COSINE),
    )
    logger.info("Collection created successfully.")

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

        # Ensure metadata values are JSON serializable
        for key, value in metadata.items():
            if isinstance(value, (dict, list, str, int, float, bool, type(None))):
                continue
            metadata[key] = str(value)

        return {
            "id": str(metadata.get("id")),
            "document": f"Title: {metadata.get('title', '')}\n\n{cleaned_body}",
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
            "document": content,
            "metadata": { "file_type": "source_code", "file_path": file_path }
        }
    except Exception as e:
        logger.error(f"Error reading file {file_path} as plain text: {e}")
        return None

# --- Main Indexing Logic ---

def _file_parser_generator(paths_to_index: List[str]) -> Generator[Dict[str, Any], None, None]:
    """
    A generator that walks through directories and yields parsed file data one by one.
    """
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
                    parsed_data = _parse_work_item_file(file_path)

                if parsed_data is None and (file_extension == ".md" or file_extension in CODE_FILE_EXTENSIONS):
                    parsed_data = _parse_plain_text_file(file_path)

                if parsed_data:
                    yield parsed_data

def build_index(paths_to_index: List[str]):
    """
    Builds or updates the vector index from a list of local directories in batches.
    """
    logger.info(f"Starting to build vector index from paths: {paths_to_index}")

    file_generator = _file_parser_generator(paths_to_index)
    total_indexed_count = 0

    while True:
        batch = [next(file_generator, None) for _ in range(BATCH_SIZE)]
        batch = [item for item in batch if item is not None]

        if not batch:
            break # No more files to process

        documents = [item["document"] for item in batch]
        # Store the document content in the payload along with other metadata
        payloads = [{**item["metadata"], "document": item["document"]} for item in batch]
        ids = [item["id"] for item in batch]

        logger.info(f"Processing a batch of {len(documents)} documents...")

        # FastEmbed handles embedding generation and returns a list of numpy arrays
        embeddings = list(embedding_model.embed(documents))

        # Upsert data into Qdrant
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=models.Batch(
                ids=ids,
                vectors=embeddings,
                payloads=payloads,
            ),
            wait=True,
        )
        total_indexed_count += len(batch)
        logger.info(f"Batch indexed. Total documents indexed so far: {total_indexed_count}")

    if total_indexed_count == 0:
        logger.warning("No valid files found to index in the provided paths.")
    else:
        logger.info(f"Successfully indexed a total of {total_indexed_count} documents.")
