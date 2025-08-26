import logging
from typing import List, Dict, Any

# Import the shared model and collection from the indexing module
from .indexing import embedding_model, collection

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def query_index(question: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """
    Queries the vector index to find documents relevant to a question.

    Args:
        question (str): The user's question.
        n_results (int): The number of results to return.

    Returns:
        List[Dict[str, Any]]: A list of relevant documents, including their
                              content and metadata.
    """
    logger.info(f"Received query: '{question}'")

    if not question:
        return []

    # Generate an embedding for the user's question
    query_embedding = embedding_model.encode(question).tolist()

    # Query the collection
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            # We only need the documents and metadata for the context
            include=['metadatas', 'documents']
        )
        logger.info(f"Found {len(results.get('documents', [[]])[0])} relevant documents.")
        return results
    except Exception as e:
        logger.error(f"Error querying the index: {e}")
        return []
