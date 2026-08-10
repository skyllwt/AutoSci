#!/usr/bin/env python3
"""LLM Review MCP Server — OpenAI-compatible API for cross-model review

Provides three tools:
  - chat: single-turn prompt (code review, analysis, general tasks)
  - chat-reply: multi-turn continuation in same thread
  - web_search: web search via LLM (provider-specific, may not work with all APIs)

Works with any OpenAI-compatible API provider:
  - DeepSeek, Qwen (DashScope), OpenRouter, SiliconFlow, OpenAI, OrcaRouter, etc.

Configuration: set LLM_* variables in the project root .env file.
  LLM_API_KEY         - API key (required)
  LLM_BASE_URL        - API base URL, e.g. https://api.deepseek.com/v1
  LLM_MODEL           - Primary model name, e.g. deepseek-chat
  LLM_FALLBACK_MODEL  - Fallback model (optional, defaults to LLM_MODEL)
  LLM_SERVER_NAME     - MCP server name (default: llm-review)
"""

import json
import os
import sys
import tempfile
import httpx
import uuid

sys.stdout = os.fdopen(sys.stdout.fileno(), 'wb', buffering=0)
sys.stdin = os.fdopen(sys.stdin.fileno(), 'rb', buffering=0)

# --- Auto-load .env from project root ---
# Walk up from this script's directory to find the project root .env
_script_dir = os.path.dirname(os.path.abspath(__file__))
for _parent in [_script_dir, os.path.join(_script_dir, '..', '..'), os.getcwd()]:
    _env_path = os.path.join(os.path.realpath(_parent), '.env')
    if os.path.isfile(_env_path):
        with open(_env_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _key, _, _val = _line.partition('=')
                    _key, _val = _key.strip(), _val.strip()
                    if _key and _key not in os.environ:  # env vars take precedence
                        os.environ[_key] = _val
        break

API_KEY = os.environ.get("LLM_API_KEY", "")
BASE_URL = os.environ.get("LLM_BASE_URL", "")
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "")
FALLBACK_MODEL = os.environ.get("LLM_FALLBACK_MODEL", "") or DEFAULT_MODEL
SERVER_NAME = os.environ.get("LLM_SERVER_NAME", "llm-review")

DEBUG_LOG = os.path.join(tempfile.gettempdir(), f"{SERVER_NAME}-mcp-debug.log")

# Thread storage for multi-turn conversations
_threads = {}

def debug_log(msg):
    try:
        with open(DEBUG_LOG, "a") as f:
            import datetime
            f.write(f"{datetime.datetime.now()}: {msg}\n")
            f.flush()
    except:
        pass

def log_error(msg):
    try:
        with open(DEBUG_LOG, "a") as f:
            import datetime
            f.write(f"{datetime.datetime.now()}: ERROR: {msg}\n")
    except:
        pass

debug_log(f"=== {SERVER_NAME} MCP Server Starting (v1.0) ===")
debug_log(f"BASE_URL: {BASE_URL}")
debug_log(f"MODEL: {DEFAULT_MODEL}")
debug_log(f"FALLBACK_MODEL: {FALLBACK_MODEL}")
debug_log(f"API_KEY set: {bool(API_KEY)}")

_use_ndjson = False

def send_response(response):
    global _use_ndjson
    json_str = json.dumps(response, separators=(',', ':'))
    json_bytes = json_str.encode('utf-8')

    if _use_ndjson:
        output = json_bytes + b'\n'
    else:
        header = f"Content-Length: {len(json_bytes)}\r\n\r\n".encode('utf-8')
        output = header + json_bytes

    sys.stdout.write(output)
    sys.stdout.flush()

def call_llm(messages, model=None):
    """Call OpenAI-compatible Chat Completions API with retry and fallback."""
    if not API_KEY:
        return None, "LLM_API_KEY not set. Configure LLM_API_KEY, LLM_BASE_URL, LLM_MODEL in .env"
    if not BASE_URL:
        return None, "LLM_BASE_URL not set. Configure LLM_BASE_URL in .env (e.g. https://api.deepseek.com/v1)"

    use_model = model or DEFAULT_MODEL
    url = f"{BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    for attempt in range(3):
        current_model = use_model if attempt < 2 else FALLBACK_MODEL
        payload = {
            "model": current_model,
            "messages": messages,
            "max_completion_tokens": 16384,
            "temperature": 0.3,
        }

        debug_log(f"Calling LLM API (attempt {attempt + 1}): model={current_model}")

        try:
            with httpx.Client(timeout=300.0) as client:
                response = client.post(url, headers=headers, json=payload)

                if response.status_code in (504, 429):
                    debug_log(f"{response.status_code} on attempt {attempt + 1} with model {current_model}")
                    if attempt < 2:
                        import time
                        time.sleep(2 ** attempt)
                        continue

                if response.status_code != 200:
                    error_msg = f"API error {response.status_code}: {response.text[:500]}"
                    debug_log(f"API error: {error_msg}")
                    return None, error_msg

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                if current_model != use_model:
                    content = f"[Fallback: {current_model}]\n{content}"
                debug_log(f"API success (attempt {attempt + 1}), response length: {len(content)}")
                return content, None
        except Exception as e:
            debug_log(f"API exception on attempt {attempt + 1}: {str(e)}")
            if attempt == 2:
                return None, str(e)

    return None, "All attempts failed"

def handle_request(request):
    method = request.get("method", "")
    params = request.get("params", {})
    request_id = request.get("id")

    debug_log(f"Handling method: {method}, id: {request_id}")

    if request_id is None:
        if method == "notifications/initialized":
            debug_log("Client initialized successfully")
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": "1.0.0"}
            }
        }

    elif method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "chat",
                        "description": f"Send a prompt to {DEFAULT_MODEL} for code review, analysis, or research tasks. Returns a threadId for follow-up via chat-reply.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "prompt": {"type": "string", "description": "The prompt to send"},
                                "model": {"type": "string", "description": f"Model to use (default: {DEFAULT_MODEL or 'configured in .env'})"},
                                "system": {"type": "string", "description": "Optional system prompt"}
                            },
                            "required": ["prompt"]
                        }
                    },
                    {
                        "name": "chat-reply",
                        "description": "Continue a multi-turn conversation with the Review LLM using an existing threadId.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "threadId": {"type": "string", "description": "Thread ID from a previous chat call"},
                                "prompt": {"type": "string", "description": "Follow-up message"}
                            },
                            "required": ["threadId", "prompt"]
                        }
                    },
                    {
                        "name": "web_search",
                        "description": f"Search the web via {DEFAULT_MODEL} with built-in web search capability.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query"},
                                "system": {"type": "string", "description": "Optional system prompt for interpreting results"}
                            },
                            "required": ["query"]
                        }
                    }
                ]
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name == "chat":
            prompt = arguments.get("prompt", "")
            model = arguments.get("model", DEFAULT_MODEL)
            system = arguments.get("system", "")

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            debug_log(f"Tool call: chat, prompt length: {len(prompt)}")
            content, error = call_llm(messages, model)

            if error:
                return {"jsonrpc": "2.0", "id": request_id, "result": {
                    "content": [{"type": "text", "text": f"Error: {error}"}], "isError": True
                }}

            # Store thread for multi-turn
            thread_id = str(uuid.uuid4())[:8]
            messages.append({"role": "assistant", "content": content})
            _threads[thread_id] = {"messages": messages, "model": model}

            return {"jsonrpc": "2.0", "id": request_id, "result": {
                "content": [{"type": "text", "text": f"[threadId: {thread_id}]\n\n{content}"}]
            }}

        elif tool_name == "chat-reply":
            thread_id = arguments.get("threadId", "")
            prompt = arguments.get("prompt", "")

            if thread_id not in _threads:
                return {"jsonrpc": "2.0", "id": request_id, "result": {
                    "content": [{"type": "text", "text": f"Error: thread {thread_id} not found"}], "isError": True
                }}

            thread = _threads[thread_id]
            thread["messages"].append({"role": "user", "content": prompt})

            content, error = call_llm(thread["messages"], thread["model"])

            if error:
                thread["messages"].pop()  # rollback
                return {"jsonrpc": "2.0", "id": request_id, "result": {
                    "content": [{"type": "text", "text": f"Error: {error}"}], "isError": True
                }}

            thread["messages"].append({"role": "assistant", "content": content})
            return {"jsonrpc": "2.0", "id": request_id, "result": {
                "content": [{"type": "text", "text": f"[threadId: {thread_id}]\n\n{content}"}]
            }}

        elif tool_name == "web_search":
            query = arguments.get("query", "")
            system = arguments.get("system", "")

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": query})

            # NOTE: web_search uses a provider-specific tools parameter.
            # This works with APIs that support {"type": "web_search"} (provider-specific).
            # For providers without built-in web search, this tool will return an error.
            if not API_KEY or not BASE_URL:
                return {"jsonrpc": "2.0", "id": request_id, "result": {
                    "content": [{"type": "text", "text": "Error: LLM_API_KEY or LLM_BASE_URL not set. Configure in .env"}], "isError": True
                }}

            url = f"{BASE_URL.rstrip('/')}/chat/completions"
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
            payload = {
                "model": DEFAULT_MODEL,
                "messages": messages,
                "max_completion_tokens": 8192,
                "temperature": 0.3,
                "tools": [{"type": "web_search", "max_keyword": 3, "force_search": True, "limit": 5}]
            }

            try:
                with httpx.Client(timeout=300.0) as client:
                    response = client.post(url, headers=headers, json=payload)
                    if response.status_code != 200:
                        return {"jsonrpc": "2.0", "id": request_id, "result": {
                            "content": [{"type": "text", "text": f"Error: {response.status_code}: {response.text[:500]}"}], "isError": True
                        }}
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    return {"jsonrpc": "2.0", "id": request_id, "result": {
                        "content": [{"type": "text", "text": content}]
                    }}
            except Exception as e:
                return {"jsonrpc": "2.0", "id": request_id, "result": {
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}], "isError": True
                }}

        return {"jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}

    else:
        return {"jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32601, "message": f"Unknown method: {method}"}}

def read_message():
    global _use_ndjson

    line = sys.stdin.readline()
    if not line:
        return None

    line = line.decode('utf-8').rstrip('\r\n')

    if line.lower().startswith("content-length:"):
        try:
            content_length = int(line.split(":", 1)[1].strip())
        except ValueError:
            return None

        while True:
            hdr = sys.stdin.readline()
            if not hdr:
                return None
            hdr = hdr.decode('utf-8').rstrip('\r\n')
            if hdr == "":
                break

        body = sys.stdin.read(content_length)
        try:
            return json.loads(body.decode('utf-8'))
        except:
            return None

    elif line.startswith("{") or line.startswith("["):
        _use_ndjson = True
        try:
            return json.loads(line)
        except:
            return None

    return None

def main():
    debug_log("Entering main loop")
    while True:
        try:
            request = read_message()
            if request is None:
                debug_log("EOF, exiting")
                break
            response = handle_request(request)
            if response:
                send_response(response)
        except Exception as e:
            log_error(f"Exception: {e}")
    debug_log("=== Server Exiting ===")

if __name__ == "__main__":
    main()
