# Tool Sync - Analysis Server

This server provides an API for analyzing the work items synchronized by `tool_sync`. It uses a Retrieval-Augmented Generation (RAG) pipeline to allow a Large Language Model (LLM) to answer questions based on the content of your local work item files.

It is designed to be used as a custom tool with AI assistants like the [Cline VS Code extension](https://marketplace.visualstudio.com/items?itemName=cline.bot), allowing you to have rich, context-aware conversations about your project's data.

## How it Works

The server has two main functions:

1.  **Indexing:** It first needs to build a "knowledge base" from your work item files. It does this by reading all your `.md` files, cleaning the content, and converting them into numerical representations (embeddings). These embeddings are stored in a local vector database (ChromaDB). This process only needs to be run when you have new or updated work items.

2.  **Querying:** Once the index is built, the server can answer questions. It takes your question, finds the most relevant documents from its knowledge base, and returns their content. This relevant context can then be passed to an LLM to generate a precise answer.

## Setup

1.  **Navigate to the server directory:**
    ```bash
    cd analysis_server
    ```

2.  **Install the required Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    This will install `fastapi`, `uvicorn`, `chromadb`, `sentence-transformers`, and `beautifulsoup4`. The first time you run the server, `sentence-transformers` will download the embedding model (approx. 120MB).

## Usage

### 1. Run the Server

From within the `analysis_server` directory, run the following command in your terminal:

```bash
uvicorn main:app --reload
```

The server will start and be available at `http://localhost:8000`.

### 2. Build the Index

Before you can query, you need to build the index from your synchronized work item files. You do this by sending a `POST` request to the `/index` endpoint.

You only need to do this once, or whenever you run `tool_sync` to get new updates.

Using `curl`:
```bash
curl -X POST http://localhost:8000/index -H "Content-Type: application/json" -d '{"work_items_path": "../work_items"}'
```

-   Replace `../work_items` with the actual path to the directory where your `tool_sync` files are stored.
-   This process will run in the background. You will see log messages in the terminal where the server is running.

### 3. Query the Index

Once the index is built, you can ask questions by sending a `GET` request to the `/query` endpoint.

Using `curl`:
```bash
curl -G http://localhost:8000/query --data-urlencode "pergunta=What is the most common cause of login errors?"
```

The server will return a JSON object containing the content of the most relevant documents found in your work items.

## Integration with Cline

The primary goal of this server is to be used as a custom tool with the Cline VS Code extension.

1.  Make sure the analysis server is running locally.
2.  In the Cline chat window, tell it how to use your new tool. Here is an example prompt:

    > add a tool that analyzes my local Azure DevOps work items. It is a local API running at http://localhost:8000.
    > It has a `/query` endpoint that takes a single query parameter named `pergunta`.
    > This tool will return the content of the most relevant work items for a given question.
    > When I ask you to analyze my work items, I want you to use this tool to get context before answering.

3.  Once Cline has learned the tool, you can ask it questions like:
    -   "Cline, using the work item analysis tool, find the root cause for login errors reported by third-party users."
    -   "Cline, please summarize the defects related to the 'Roteirizador Product' using the analysis tool."
    -   "Cline, what are the most common patterns you see in our bug reports? Use the work item tool."
