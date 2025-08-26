import logging
import asyncio
from mcp import (
    Server,
    StdioServerTransport,
    ListToolsRequestSchema,
    ExecuteToolRequestSchema,
    McpError,
    ErrorCode,
)

from .analysis.indexing import build_index
from .analysis.query import query_index

# Set up logging
logging.basicConfig(level=logging.INFO, filename="mcp_server.log", filemode="a")
logger = logging.getLogger(__name__)

# Define the tools that this server provides
TOOLS = [
    {
        "name": "index_documents",
        "description": "Builds or updates the knowledge base from local work item files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "work_items_path": {
                    "type": "string",
                    "description": "The relative path to the directory containing the work item files (e.g., 'work_items/')."
                }
            },
            "required": ["work_items_path"],
        },
    },
    {
        "name": "query_documents",
        "description": "Queries the knowledge base to find work items relevant to a question.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask about the work items."
                },
                "n_results": {
                    "type": "integer",
                    "description": "The maximum number of relevant documents to return.",
                    "default": 5,
                }
            },
            "required": ["question"],
        },
    },
]

async def handle_list_tools(request):
    """
    Handles the request to list the tools available on this server.
    """
    logger.info("Received ListToolsRequest")
    return {"tools": TOOLS}

async def handle_execute_tool(request):
    """
    Handles the request to execute a specific tool.
    """
    tool_name = request.params.name
    tool_input = request.params.input
    logger.info(f"Received ExecuteToolRequest for tool: {tool_name} with input: {tool_input}")

    try:
        if tool_name == "index_documents":
            path = tool_input.get("work_items_path")
            if not path:
                raise McpError(ErrorCode.InvalidParams, "'work_items_path' is a required parameter.")

            # Running indexing in a separate thread to not block the server
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, build_index, path)

            return {
                "content": [{"type": "text", "text": "Successfully started indexing process. Check server logs for progress."}]
            }

        elif tool_name == "query_documents":
            question = tool_input.get("question")
            n_results = tool_input.get("n_results", 5)
            if not question:
                raise McpError(ErrorCode.InvalidParams, "'question' is a required parameter.")

            results = query_index(question, n_results)

            # Format the results into a readable string for the LLM
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]

            if not documents:
                return {"content": [{"type": "text", "text": "No relevant documents found."}]}

            context_str = "Here is the context from relevant documents:\n\n"
            for i, doc in enumerate(documents):
                meta = metadatas[i]
                context_str += f"--- Document {i+1} (ID: {meta.get('id')}, Path: {meta.get('file_path')}) ---\n"
                context_str += doc + "\n\n"

            return {"content": [{"type": "text", "text": context_str}]}

        else:
            raise McpError(ErrorCode.MethodNotFound, f"Unknown tool: {tool_name}")

    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
        # Re-raise as McpError so Cline can handle it gracefully
        if isinstance(e, McpError):
            raise e
        else:
            raise McpError(ErrorCode.InternalError, str(e))

def run_server():
    """
    Initializes and runs the MCP server.
    """
    logger.info("Initializing MCP server...")
    server = Server(
        name="tool_sync_analyzer",
        version="0.1.0",
        transport=StdioServerTransport(),
    )
    server.add_request_handler(ListToolsRequestSchema, handle_list_tools)
    server.add_request_handler(ExecuteToolRequestSchema, handle_execute_tool)

    logger.info("MCP server running and listening for requests from Cline...")
    asyncio.run(server.listen())
    logger.info("MCP server stopped.")
