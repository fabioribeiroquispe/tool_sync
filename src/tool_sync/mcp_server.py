import logging
import asyncio
from mcp.server.fastmcp import FastMCP
from typing import Optional

from .analysis.indexing import build_index
from .analysis.query import query_index

# Set up logging
logging.basicConfig(level=logging.INFO, filename="mcp_server.log", filemode="a")
logger = logging.getLogger(__name__)

# Initialize the MCP server with a friendly name
mcp = FastMCP(
    name="tool_sync_analyzer",
)

@mcp.tool()
def index_documents(work_items_path: str) -> str:
    """
    Builds or updates the knowledge base from local work item files.

    :param work_items_path: The relative path to the directory containing the work item files (e.g., 'work_items/').
    """
    logger.info(f"Received request to index documents at path: {work_items_path}")
    if not work_items_path:
        raise ValueError("'work_items_path' is a required parameter.")

    # Running indexing in a separate thread to not block the server,
    # but FastMCP handles async calls correctly.
    # For simplicity, we'll run it directly. If it's too slow,
    # we can use asyncio.to_thread in the future.
    try:
        build_index(work_items_path)
        return "Successfully indexed documents. The knowledge base is ready."
    except Exception as e:
        logger.error(f"Error during indexing: {e}", exc_info=True)
        raise ValueError(f"An error occurred during indexing: {e}")


@mcp.tool()
def query_documents(question: str, n_results: Optional[int] = 5) -> str:
    """
    Queries the knowledge base to find work items relevant to a question.

    :param question: The question to ask about the work items.
    :param n_results: The maximum number of relevant documents to return.
    """
    logger.info(f"Received query: '{question}' with n_results={n_results}")
    if not question:
        raise ValueError("'question' is a required parameter.")

    try:
        results = query_index(question, n_results)

        documents = results.get('documents', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]

        if not documents:
            return "No relevant documents found."

        context_str = "Here is the context from relevant documents:\n\n"
        for i, doc in enumerate(documents):
            meta = metadatas[i]
            context_str += f"--- Document {i+1} (ID: {meta.get('id')}, Path: {meta.get('file_path')}) ---\n"
            context_str += doc + "\n\n"

        return context_str
    except Exception as e:
        logger.error(f"Error during query: {e}", exc_info=True)
        raise ValueError(f"An error occurred during query: {e}")

def run_server():
    """
    Initializes and runs the MCP server.
    """
    logger.info("Initializing MCP server with FastMCP...")
    # FastMCP runs its own asyncio loop
    mcp.run()
    logger.info("MCP server stopped.")
