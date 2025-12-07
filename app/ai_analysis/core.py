import requests
import json
import logging
import time
from .tools import AVAILABLE_TOOLS, execute_tool_call

logger = logging.getLogger(__name__)

class AIAnalysisAgent:
    def __init__(self, engine):
        self.engine = engine
        self.api_url = engine.api_url.strip().rstrip('/')
        if not self.api_url.endswith('/chat/completions'):
            self.api_url += '/chat/completions'
        self.headers = {
            "Authorization": f"Bearer {engine.api_key}",
            "Content-Type": "application/json"
        }
        self.model = engine.model_name
        
    def run(self, user_prompt):
        messages = [
            {"role": "system", "content": """You are an intelligent Data Analysis Expert for a government information system. 
Your goal is to assist administrators in cleaning, analyzing, and managing database content efficiently.

**Database Structure & Analysis Strategy (CRITICAL):**
    1. **`crawl_items` (Master Table)**: Contains **ALL** crawled records.
   - Key columns: `id`, `title`, `url`, `source`, `created_at`, `deep_summary` (Content Summary).
   - **ALWAYS query `title` and `deep_summary` first** when asked for "all data", "titles", "summaries", or generating a report.
   - The `deep_summary` column contains the AI-generated summary of the article. Use this for quick analysis.
2. **`article_details` (Detail Table)**: Contains full text content ONLY for deep-crawled items.
   - Linked via: `article_details.crawl_item_id` = `crawl_items.id`.
   - Use this ONLY when you need to analyze the full body text (`content`).

**Guidelines:**
1. **Language**: ALWAYS use **Simplified Chinese (简体中文)** for your response, reasoning, and summaries.
2. **Tone**: Professional, concise, and helpful. Use a "business intelligence" style.
3. **Format**: ALWAYS output your final answer in **Markdown**.
   - Use **bold** for key insights.
   - Use `Tables` to display data query results (very important).
   - Use `Code Blocks` for SQL or scripts if relevant to explain.
   - Use lists for steps or summaries.
4. **Process**:
   - First, check the table schema if unknown.
   - Use SQL queries to inspect data.
   - Explain your analysis steps clearly before or after execution.
   - If cleaning data, confirm the impact (count of rows) after operation.
5. **Tools**: You have access to `crawl_items` (all data) and `article_details` (content). Use `run_sql_query` to interact.

**CRITICAL INSTRUCTION**:
- **NEVER** write tool calls as text (e.g. `get_table_schema(...)`).
- You **MUST** use the provided tool calling facility to execute functions.
- If you want to check the schema, invoke the `get_table_schema` tool.
- If you want to query data, invoke the `run_sql_query` tool.
- Do not make assumptions about data; verify with tools.

**Output Requirement**:
- When you present data, format it nicely in a Markdown table.
- Provide a brief "Executive Summary" (执行摘要) at the beginning of your final answer.
"""},
            {"role": "user", "content": user_prompt}
        ]
        
        max_turns = 10
        current_turn = 0
        
        yield {"type": "step", "content": "正在初始化分析引擎..."}
        
        while current_turn < max_turns:
            current_turn += 1
            
            payload = {
                "model": self.model,
                "messages": messages,
                "tools": AVAILABLE_TOOLS,
                "tool_choice": "auto",
                "stream": True
            }
            
            try:
                yield {"type": "step", "content": f"第 {current_turn} 轮思考..."}
                
                logger.info(f"AI Analysis Turn {current_turn}: Sending request to {self.model}")
                
                # Retry logic for Rate Limiting
                max_retries = 3
                response = None
                
                for attempt in range(max_retries):
                    try:
                        response = requests.post(self.api_url, json=payload, headers=self.headers, timeout=120, stream=True)
                        
                        # Check for rate limit error (429)
                        if response.status_code == 429:
                            wait_time = (attempt + 1) * 5
                            logger.warning(f"Rate limit hit (429). Retrying in {wait_time}s...")
                            yield {"type": "step", "content": f"API限流，{wait_time}秒后重试..."}
                            time.sleep(wait_time)
                            continue
                            
                        # Check for other transient errors if needed, but for now focusing on rate limit
                        break
                        
                    except requests.exceptions.RequestException as e:
                        logger.error(f"Request failed (attempt {attempt+1}): {e}")
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 3
                            yield {"type": "step", "content": f"网络请求失败，{wait_time}秒后重试..."}
                            time.sleep(wait_time)
                        else:
                            raise e
                
                if not response:
                    raise Exception("Failed to get response after retries")

                logger.info(f"AI Analysis Turn {current_turn}: Received response status {response.status_code}")
                
                if response.status_code != 200:
                    # Consuming the error text
                    error_text = response.text
                    # specific check for the JSON error user reported even if status wasn't 429 (though likely it was caught above if it was 429)
                    if "rate limiting" in error_text or "TPM limit reached" in error_text:
                         yield {"type": "error", "content": "API调用过于频繁(TPM限制)，请稍后再试。"}
                         return

                    error_msg = f"API Error: {error_text}"
                    logger.error(error_msg)
                    yield {"type": "error", "content": error_msg}
                    return
                
                collected_content = ""
                collected_tool_calls = {} # index -> {id, type, function: {name, arguments}}
                
                for line in response.iter_lines():
                    if not line: continue
                    line_text = line.decode('utf-8')
                    if line_text.startswith("data: "):
                        data_str = line_text[6:]
                        if data_str.strip() == "[DONE]": break
                        try:
                            chunk = json.loads(data_str)
                            if not chunk.get('choices'): continue
                            
                            delta = chunk['choices'][0]['delta']
                            
                            # Handle content
                            if 'content' in delta and delta['content']:
                                content_piece = delta['content']
                                collected_content += content_piece
                                # Stream content to frontend as answer updates
                                yield {"type": "answer", "content": collected_content}
                                
                            # Handle tool calls
                            if 'tool_calls' in delta and delta['tool_calls']:
                                for tc in delta['tool_calls']:
                                    idx = tc['index']
                                    if idx not in collected_tool_calls:
                                        collected_tool_calls[idx] = {
                                            "id": tc.get('id'),
                                            "type": tc.get('type'),
                                            "function": {"name": "", "arguments": ""}
                                        }
                                    
                                    # ID is usually only in the first chunk
                                    if tc.get('id'):
                                        collected_tool_calls[idx]["id"] = tc['id']
                                        
                                    if 'function' in tc:
                                        if 'name' in tc['function']:
                                            collected_tool_calls[idx]["function"]["name"] += tc['function']['name']
                                        if 'arguments' in tc['function']:
                                            collected_tool_calls[idx]["function"]["arguments"] += tc['function']['arguments']
                        except Exception as e:
                            logger.error(f"Stream parse error: {e}")
                
                # Reconstruct full message
                message = {
                    "role": "assistant",
                    "content": collected_content
                }
                
                if collected_tool_calls:
                    tool_calls_list = []
                    for idx in sorted(collected_tool_calls.keys()):
                        tc_data = collected_tool_calls[idx]
                        # Ensure we have an ID (fallback if missed in stream)
                        if not tc_data.get("id"):
                             tc_data["id"] = f"call_{idx}_{current_turn}"
                        
                        tool_calls_list.append({
                            "id": tc_data["id"],
                            "type": tc_data["type"] or "function",
                            "function": {
                                "name": tc_data["function"]["name"],
                                "arguments": tc_data["function"]["arguments"]
                            }
                        })
                    message["tool_calls"] = tool_calls_list
                
                # Add assistant message to history
                messages.append(message)
                
                # Check if tool calls
                if message.get('tool_calls'):
                    if message.get('content'):
                         yield {"type": "thought", "content": message['content']}
                         
                    for tool_call in message['tool_calls']:
                        func_name = tool_call['function']['name']
                        try:
                            args = json.loads(tool_call['function']['arguments'])
                            # Handle case where args is not a dict (e.g. string)
                            if not isinstance(args, dict):
                                if func_name == 'run_sql_query' and isinstance(args, str):
                                    args = {"query": args}
                                else:
                                    args = {}
                        except:
                            args = {}
                        
                        yield {"type": "tool_call", "content": func_name, "args": args}
                        
                        # Execute tool
                        result = execute_tool_call(func_name, args)
                        
                        # Yield result (truncated for display if too long)
                        result_str = str(result)
                        display_result = result_str[:500] + "..." if len(result_str) > 500 else result_str
                        yield {"type": "tool_result", "content": display_result}
                        
                        # Add tool result to history
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call['id'],
                            "name": func_name,
                            "content": result_str
                        })
                else:
                    # No tool calls, final response
                    yield {"type": "answer", "content": message.get('content')}
                    return
                    
            except Exception as e:
                yield {"type": "error", "content": f"Error during execution: {str(e)}"}
                return
                
        yield {"type": "error", "content": "Max turns reached without final answer."}
