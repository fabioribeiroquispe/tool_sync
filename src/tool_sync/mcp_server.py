import logging
import asyncio
from mcp.server.fastmcp import FastMCP
from typing import Optional, List

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
def index_documents(paths: List[str]) -> str:
    """
    Builds or updates the knowledge base from a list of local directories.
    Can index work items, source code, and other text files.

    :param paths: A list of local directory or file paths to index. Paths can be absolute or relative.
    """
    logger.info(f"Received request to index documents at paths: {paths}")
    if not paths:
        raise ValueError("'paths' is a required parameter and cannot be empty.")

    try:
        # The build_index function now accepts a list of paths
        build_index(paths)
        return "Successfully indexed all provided paths. The knowledge base is ready."
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
