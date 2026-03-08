"""
AI Bridge - LLM integration for context-aware code generation.
Uses Google Gemini for generating Python code based on runtime context.
"""

import os
import json
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI


SYSTEM_PROMPT = """You are an expert Python data science assistant embedded in a Jupyter-like IDE called DataCursor.

## Your Role
You help users write Python code by understanding their runtime context - the variables, DataFrames, and imports currently in their session.

## Context Awareness
You will receive:
1. **Current Cell Content**: The code the user is working on
2. **Runtime Context**: Active variables, their types, and DataFrame schemas
3. **User Request**: What the user wants to accomplish

## Rules
1. Generate ONLY Python code - no markdown, no explanations in the response
2. Use existing variables from the context when relevant
3. Prefer pandas/numpy idioms for data manipulation
4. Add brief inline comments for complex operations
5. If the context includes DataFrames, use their actual column names
6. Import statements only if the module isn't already imported

## Output Format
Return ONLY the Python code to be inserted. Do not include ```python markers.
"""

USER_PROMPT_TEMPLATE = """## Current Cell Content
```python
{current_code}
```

## Runtime Context
### Active Variables
{variables}

### DataFrames
{dataframes}

### Imported Modules
{imports}

## User Request
{user_request}

Generate Python code to accomplish this request. Return ONLY the code, no explanations.
"""


class AIBridge:
    """Handles AI code generation with runtime context."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.llm = None
        
        if self.api_key:
            self._init_llm()
    
    def _init_llm(self):
        """Initialize the LLM."""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=self.api_key,
            temperature=0.1,
            convert_system_message_to_human=True,
        )
    
    def set_api_key(self, api_key: str):
        """Set or update the API key."""
        self.api_key = api_key
        os.environ["GOOGLE_API_KEY"] = api_key
        self._init_llm()
    
    def format_context(self, context: dict) -> tuple[str, str, str]:
        """Format runtime context for the prompt."""
        # Format variables
        variables_str = ""
        for var in context.get("variables", []):
            var_line = f"- `{var['name']}` ({var['type']})"
            if 'length' in var:
                var_line += f" - length: {var['length']}"
            if 'shape' in var:
                var_line += f" - shape: {var['shape']}"
            variables_str += var_line + "\n"
        
        if not variables_str:
            variables_str = "No user-defined variables"
        
        # Format DataFrames
        dataframes_str = ""
        for df in context.get("dataframes", []):
            df_str = f"**{df['name']}** {df.get('shape', '')}\n"
            if 'columns' in df:
                df_str += f"  Columns: {', '.join(df['columns'][:10])}"
                if len(df.get('columns', [])) > 10:
                    df_str += f" ... (+{len(df['columns']) - 10} more)"
            if 'dtypes' in df:
                df_str += f"\n  Types: {json.dumps(dict(list(df['dtypes'].items())[:5]))}"
            dataframes_str += df_str + "\n"
        
        if not dataframes_str:
            dataframes_str = "No DataFrames in context"
        
        # Format imports
        imports = context.get("imports", [])
        imports_str = ", ".join(imports[:20]) if imports else "No custom imports"
        
        return variables_str, dataframes_str, imports_str
    
    async def generate_code(
        self,
        user_request: str,
        current_code: str = "",
        context: Optional[dict] = None
    ) -> dict:
        """
        Generate code based on user request and runtime context.
        
        Returns:
            {
                "success": bool,
                "code": str,
                "error": str | None
            }
        """
        if not self.llm:
            return {
                "success": False,
                "code": "",
                "error": "API key not configured"
            }
        
        try:
            # Format context
            context = context or {}
            variables_str, dataframes_str, imports_str = self.format_context(context)
            
            # Build the prompt
            user_prompt = USER_PROMPT_TEMPLATE.format(
                current_code=current_code or "# Empty cell",
                variables=variables_str,
                dataframes=dataframes_str,
                imports=imports_str,
                user_request=user_request,
            )
            
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
            
            # Generate
            response = self.llm.invoke(messages)
            code = response.content.strip()
            
            # Clean up any markdown code blocks if present
            if code.startswith("```python"):
                code = code[9:]
            if code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]
            
            return {
                "success": True,
                "code": code.strip(),
                "error": None
            }
        
        except Exception as e:
            return {
                "success": False,
                "code": "",
                "error": str(e)
            }
    
    def compute_diff(self, original: str, generated: str) -> list[dict]:
        """
        Compute a simple line-by-line diff between original and generated code.
        
        Returns list of:
            {"type": "unchanged" | "added" | "removed", "line": str}
        """
        original_lines = original.split('\n') if original else []
        generated_lines = generated.split('\n')
        
        diff = []
        
        # Simple diff algorithm
        # In production, use difflib for proper Myers diff
        import difflib
        
        matcher = difflib.SequenceMatcher(None, original_lines, generated_lines)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for line in original_lines[i1:i2]:
                    diff.append({"type": "unchanged", "line": line})
            elif tag == 'replace':
                for line in original_lines[i1:i2]:
                    diff.append({"type": "removed", "line": line})
                for line in generated_lines[j1:j2]:
                    diff.append({"type": "added", "line": line})
            elif tag == 'delete':
                for line in original_lines[i1:i2]:
                    diff.append({"type": "removed", "line": line})
            elif tag == 'insert':
                for line in generated_lines[j1:j2]:
                    diff.append({"type": "added", "line": line})
        
        return diff


# Global AI bridge instance
ai_bridge = AIBridge()
