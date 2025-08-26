import os
import re
import logging
from typing import List, Dict, Any

import yaml
from bs4 import BeautifulSoup
import chromadb
from sentence_transformers import SentenceTransformer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the embedding model
# This will download the model the first time it's run
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize ChromaDB client
# This will create a local, persistent database in the 'chroma_db' directory
db_client = chromadb.PersistentClient(path="chroma_db")
collection = db_client.get_or_create_collection(name="work_items")

def _parse_work_item_file(file_path: str) -> Dict[str, Any] | None:
    """
    Parses a single work item file and returns its content.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        front_matter_match = re.match(r"---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
        if not front_matter_match:
            logger.warning(f"Could not parse front matter from {file_path}")
            return None

        front_matter_str, body = front_matter_match.groups()
        metadata = yaml.safe_load(front_matter_str) or {}

        # Clean HTML from the body
        soup = BeautifulSoup(body, 'html.parser')
        cleaned_body = soup.get_text(separator=' ', strip=True)

        return {
            "id": metadata.get("id"),
            "title": metadata.get("title"),
            "body": cleaned_body,
            "metadata": metadata,
            "file_path": file_path
        }
    except Exception as e:
        logger.error(f"Error parsing file {file_path}: {e}")
        return None

def build_index(work_items_path: str):
    """
    Builds or updates the vector index for all work items.
    """
    logger.info(f"Starting to build the vector index from path: {work_items_path}")

    documents = []
    metadatas = []
    ids = []

    for root, _, files in os.walk(work_items_path):
        for file_name in files:
            if file_name.endswith(".md"):
                file_path = os.path.join(root, file_name)
                parsed_item = _parse_work_item_file(file_path)

                if parsed_item and parsed_item.get("id"):
                    # Prepare the text to be embedded
                    text_to_embed = f"Title: {parsed_item['title']}\n\n{parsed_item['body']}"

                    documents.append(text_to_embed)

                    # Store useful metadata
                    metadatas.append({
                        "title": parsed_item['title'],
                        "file_path": parsed_item['file_path'],
                        **parsed_item['metadata']
                    })

                    # Use the work item ID as the unique ID in ChromaDB
                    ids.append(str(parsed_item['id']))

    if not documents:
        logger.warning("No valid work item files found to index.")
        return

    logger.info(f"Found {len(documents)} documents to index. Generating embeddings...")

    # Generate embeddings for all documents in a batch
    embeddings = embedding_model.encode(documents).tolist()

    logger.info("Embeddings generated. Adding to the vector database...")

    # Add or update the documents in ChromaDB
    collection.add(
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    logger.info(f"Successfully indexed {len(documents)} documents. Index is ready.")
