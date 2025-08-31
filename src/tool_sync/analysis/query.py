import logging
from typing import List, Dict, Any, Union

# Import the shared client and embedding_model from the indexing module
from .indexing import client, embedding_model, COLLECTION_NAME

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def query_index(question: str, n_results: int = 5) -> Dict[str, Union[List[List[Any]], str]]:
    """
    Queries the vector index to find documents relevant to a question.

    Args:
        question (str): The user's question.
        n_results (int): The number of results to return.

    Returns:
        A dictionary containing the query results, compatible with the MCP server's expected format.
    """
    logger.info(f"Received query: '{question}'")

    if not question:
        return {"documents": [[]], "metadatas": [[]]}

    # Generate an embedding for the user's question.
    # FastEmbed returns a list with one embedding, so we get the first element.
    query_embedding = next(embedding_model.embed(question))

    # Query the collection using Qdrant's search method
    try:
        # The search method returns a list of ScoredPoint objects
        search_results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=n_results,
            with_payload=True,  # Include the payload (metadata)
        )
        logger.info(f"Found {len(search_results)} relevant documents.")

        # Reformat the results to match the structure expected by the MCP server
        documents = []
        metadatas = []
        for result in search_results:
            # The payload now contains both the original metadata and the document content
            payload = result.payload
            if payload:
                # The 'document' field was stored in the payload
                doc_content = payload.pop("document", "")
                documents.append(doc_content)
                # The rest of the payload is the metadata
                metadatas.append(payload)

        return {
            "documents": [documents],
            "metadatas": [metadatas]
        }

    except Exception as e:
        logger.error(f"Error querying the index: {e}", exc_info=True)
        return {"documents": [[]], "metadatas": [[]]}
