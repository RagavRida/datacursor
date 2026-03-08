"""
LangGraph State Machine for the Full-Cycle Autonomous Data Analyst.
Implements 5 nodes: Ingestion, Cleaning, Pattern Hunting, Visualization, Recommendations.
"""

import json
import re
from typing import TypedDict, Literal, Optional, Any
from io import StringIO

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, inspect, text

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI

from prompts import (
    DATA_JANITOR_SYSTEM_PROMPT,
    DATA_JANITOR_CLEANING_PROMPT,
    PATTERN_HUNTER_SYSTEM_PROMPT,
    PATTERN_HUNTER_ANALYSIS_PROMPT,
    INTERPRETER_SYSTEM_PROMPT,
    INTERPRETER_PROMPT,
    STRATEGIST_SYSTEM_PROMPT,
    STRATEGIST_PROMPT,
    SQL_ANALYST_SYSTEM_PROMPT,
    SQL_ANALYST_PROMPT,
    DATA_PROFILER_PROMPT,
)


# =============================================================================
# STATE DEFINITION
# =============================================================================

class AnalystState(TypedDict):
    """State schema for the Data Analyst agent."""
    
    # Data Source
    raw_data: Optional[pd.DataFrame]
    data_source_type: Literal["csv", "excel", "sqlite", None]
    data_source_name: str
    
    # SQL Connection (for database sources)
    sql_engine: Optional[Any]
    sql_tables: list[dict]
    
    # Quality Report
    quality_report: Optional[dict]
    
    # Cleaning
    user_cleaning_instructions: dict
    cleaning_code: str
    cleaned_data: Optional[pd.DataFrame]
    
    # Analysis
    patterns: list[dict]
    approved_patterns: list[dict]
    
    # Visualization & Interpretation
    visualizations: list[dict]  # {"figure": plotly_fig, "pattern_id": int}
    interpretations: list[dict]  # {"pattern_id": int, "text": str}
    
    # Recommendations
    recommendations: Optional[dict]
    
    # Workflow Control
    current_stage: Literal[
        "start",
        "profiled",
        "awaiting_cleaning_input",
        "cleaned",
        "patterns_found",
        "awaiting_pattern_approval",
        "visualized",
        "complete",
        "error"
    ]
    error_message: Optional[str]
    messages: list[str]  # Log of agent messages


# =============================================================================
# LLM INITIALIZATION
# =============================================================================

def get_llm(temperature: float = 0.1) -> ChatGoogleGenerativeAI:
    """Get a configured Gemini LLM instance."""
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=temperature,
        convert_system_message_to_human=True,
    )


def parse_json_response(response_text: str) -> dict:
    """Extract and parse JSON from LLM response."""
    # Try to find JSON in code blocks first
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find raw JSON
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            json_str = json_match.group(0)
        else:
            raise ValueError("No JSON found in response")
    
    return json.loads(json_str)


# =============================================================================
# NODE 1: INGESTION & PROFILING
# =============================================================================

def ingest_and_profile(state: AnalystState) -> AnalystState:
    """
    Load data and generate a comprehensive quality report.
    This node is called after data is uploaded to create the profile.
    """
    df = state["raw_data"]
    
    if df is None:
        return {
            **state,
            "current_stage": "error",
            "error_message": "No data provided for profiling.",
        }
    
    try:
        # Calculate missing values
        missing = df.isnull().sum()
        missing_pct = (missing / len(df) * 100).round(2)
        missing_summary = {
            col: {"count": int(missing[col]), "percentage": float(missing_pct[col])}
            for col in df.columns if missing[col] > 0
        }
        
        # Detect duplicates
        duplicate_count = df.duplicated().sum()
        
        # Numeric column statistics
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        numeric_stats = {}
        if numeric_cols:
            stats_df = df[numeric_cols].describe()
            numeric_stats = stats_df.to_dict()
        
        # Categorical column info
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        categorical_info = {}
        for col in cat_cols:
            unique_count = df[col].nunique()
            top_values = df[col].value_counts().head(5).to_dict()
            categorical_info[col] = {
                "unique_values": unique_count,
                "top_values": top_values,
            }
        
        # Data type issues
        dtype_info = {col: str(dtype) for col, dtype in df.dtypes.items()}
        
        # Build quality report
        quality_report = {
            "shape": {"rows": len(df), "columns": len(df.columns)},
            "columns": list(df.columns),
            "dtypes": dtype_info,
            "missing_values": missing_summary,
            "duplicate_rows": int(duplicate_count),
            "numeric_columns": numeric_cols,
            "categorical_columns": cat_cols,
            "numeric_stats": numeric_stats,
            "categorical_info": categorical_info,
        }
        
        # Calculate overall quality score
        total_cells = len(df) * len(df.columns)
        missing_cells = df.isnull().sum().sum()
        quality_score = int(100 - (missing_cells / total_cells * 100) - (duplicate_count / len(df) * 10))
        quality_report["quality_score"] = max(0, min(100, quality_score))
        
        return {
            **state,
            "quality_report": quality_report,
            "current_stage": "profiled",
            "messages": state.get("messages", []) + [
                f"✅ Data profiled successfully. Shape: {quality_report['shape']}"
            ],
        }
        
    except Exception as e:
        return {
            **state,
            "current_stage": "error",
            "error_message": f"Error during profiling: {str(e)}",
        }


# =============================================================================
# NODE 2: DATA JANITOR (CLEANING)
# =============================================================================

def clean_data(state: AnalystState) -> AnalystState:
    """
    Generate and execute cleaning code based on user instructions.
    """
    df = state["raw_data"].copy()
    user_instructions = state.get("user_cleaning_instructions", {})
    quality_report = state["quality_report"]
    
    if not user_instructions:
        # No cleaning requested, pass through
        return {
            **state,
            "cleaned_data": df,
            "current_stage": "cleaned",
            "messages": state.get("messages", []) + ["ℹ️ No cleaning required, using original data."],
        }
    
    try:
        llm = get_llm(temperature=0.0)
        
        # Format the prompt
        prompt = DATA_JANITOR_CLEANING_PROMPT.format(
            quality_report=json.dumps(quality_report, indent=2),
            user_instructions=json.dumps(user_instructions, indent=2),
            columns=list(df.columns),
            shape=df.shape,
            sample_data=df.head(3).to_string(),
        )
        
        messages = [
            {"role": "system", "content": DATA_JANITOR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        
        response = llm.invoke(messages)
        result = parse_json_response(response.content)
        
        cleaning_code = result.get("code", "")
        
        # Execute the cleaning code safely
        if cleaning_code:
            # Create a restricted namespace
            namespace = {"df": df, "pd": pd, "np": np}
            exec(cleaning_code, namespace)
            df = namespace.get("df", df)
        
        return {
            **state,
            "cleaning_code": cleaning_code,
            "cleaned_data": df,
            "current_stage": "cleaned",
            "messages": state.get("messages", []) + [
                f"✅ Data cleaned. New shape: {df.shape}",
                f"Code executed:\n```python\n{cleaning_code}\n```" if cleaning_code else "",
            ],
        }
        
    except Exception as e:
        return {
            **state,
            "cleaned_data": state["raw_data"].copy(),  # Fallback to original
            "current_stage": "cleaned",
            "error_message": f"Cleaning error (using original data): {str(e)}",
            "messages": state.get("messages", []) + [f"⚠️ Cleaning failed: {str(e)}"],
        }


# =============================================================================
# NODE 3: PATTERN HUNTER (ANALYSIS)
# =============================================================================

def hunt_patterns(state: AnalystState) -> AnalystState:
    """
    Analyze the cleaned data to find the top 3 most interesting patterns.
    """
    df = state["cleaned_data"]
    
    if df is None:
        return {
            **state,
            "current_stage": "error",
            "error_message": "No cleaned data available for analysis.",
        }
    
    try:
        llm = get_llm(temperature=0.2)
        
        # Calculate correlations for numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        correlations = ""
        if len(numeric_cols) >= 2:
            corr_matrix = df[numeric_cols].corr().round(3)
            correlations = corr_matrix.to_string()
        
        # Get statistics
        statistics = df.describe().to_string()
        
        prompt = PATTERN_HUNTER_ANALYSIS_PROMPT.format(
            columns=list(df.columns),
            shape=df.shape,
            dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
            statistics=statistics,
            correlations=correlations if correlations else "No numeric correlations available",
            sample_data=df.head(5).to_string(),
        )
        
        messages = [
            {"role": "system", "content": PATTERN_HUNTER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        
        response = llm.invoke(messages)
        result = parse_json_response(response.content)
        
        patterns = result.get("patterns", [])
        
        return {
            **state,
            "patterns": patterns,
            "current_stage": "patterns_found",
            "messages": state.get("messages", []) + [
                f"🔍 Found {len(patterns)} patterns to explore."
            ],
        }
        
    except Exception as e:
        return {
            **state,
            "patterns": [],
            "current_stage": "patterns_found",
            "error_message": f"Pattern analysis error: {str(e)}",
            "messages": state.get("messages", []) + [f"⚠️ Pattern hunting failed: {str(e)}"],
        }


# =============================================================================
# NODE 4: VISUALIZATION & INTERPRETATION
# =============================================================================

def create_visualization(df: pd.DataFrame, pattern: dict) -> go.Figure:
    """Create a Plotly visualization based on the pattern type."""
    viz_type = pattern.get("visualization_type", "scatter")
    columns = pattern.get("columns_involved", [])
    title = pattern.get("title", "Pattern Visualization")
    
    fig = None
    
    try:
        if viz_type == "scatter" and len(columns) >= 2:
            fig = px.scatter(df, x=columns[0], y=columns[1], title=title)
            fig.update_traces(marker=dict(size=8, opacity=0.7))
            
        elif viz_type == "bar" and len(columns) >= 1:
            if len(columns) >= 2:
                fig = px.bar(df, x=columns[0], y=columns[1], title=title)
            else:
                value_counts = df[columns[0]].value_counts().head(10)
                fig = px.bar(x=value_counts.index, y=value_counts.values, title=title)
                
        elif viz_type == "line" and len(columns) >= 2:
            fig = px.line(df, x=columns[0], y=columns[1], title=title)
            
        elif viz_type == "histogram" and len(columns) >= 1:
            fig = px.histogram(df, x=columns[0], title=title)
            
        elif viz_type == "box" and len(columns) >= 1:
            if len(columns) >= 2:
                fig = px.box(df, x=columns[0], y=columns[1], title=title)
            else:
                fig = px.box(df, y=columns[0], title=title)
                
        elif viz_type == "heatmap" and len(columns) >= 2:
            # Create correlation heatmap
            numeric_df = df[columns].select_dtypes(include=[np.number])
            if len(numeric_df.columns) >= 2:
                corr = numeric_df.corr()
                fig = px.imshow(corr, title=title, text_auto=True)
        
        # Default to scatter if nothing else works
        if fig is None and len(columns) >= 2:
            fig = px.scatter(df, x=columns[0], y=columns[1], title=title)
        elif fig is None and len(columns) == 1:
            fig = px.histogram(df, x=columns[0], title=title)
        elif fig is None:
            fig = go.Figure()
            fig.add_annotation(text="Unable to create visualization", 
                             xref="paper", yref="paper", x=0.5, y=0.5)
        
        # Apply consistent styling
        fig.update_layout(
            template="plotly_white",
            title_font_size=16,
            margin=dict(l=50, r=50, t=60, b=50),
        )
        
        return fig
        
    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Visualization error: {str(e)}", 
                         xref="paper", yref="paper", x=0.5, y=0.5)
        return fig


def visualize_and_interpret(state: AnalystState) -> AnalystState:
    """
    Generate visualizations and narrative interpretations for approved patterns.
    """
    df = state["cleaned_data"]
    approved_patterns = state.get("approved_patterns", [])
    
    if not approved_patterns:
        return {
            **state,
            "visualizations": [],
            "interpretations": [],
            "current_stage": "visualized",
            "messages": state.get("messages", []) + ["ℹ No patterns approved for visualization."],
        }
    
    try:
        llm = get_llm(temperature=0.3)
        visualizations = []
        interpretations = []
        
        for pattern in approved_patterns:
            # Create visualization
            fig = create_visualization(df, pattern)
            visualizations.append({
                "pattern_id": pattern.get("id", 0),
                "figure": fig,
                "title": pattern.get("title", ""),
            })
            
            # Generate interpretation
            columns = pattern.get("columns_involved", [])
            relevant_stats = ""
            if columns:
                for col in columns:
                    if col in df.columns:
                        if df[col].dtype in ['int64', 'float64']:
                            stats = df[col].describe()
                            relevant_stats += f"\n{col}: mean={stats['mean']:.2f}, std={stats['std']:.2f}"
            
            prompt = INTERPRETER_PROMPT.format(
                pattern_title=pattern.get("title", ""),
                pattern_description=pattern.get("description", ""),
                columns=columns,
                relevant_stats=relevant_stats if relevant_stats else "Statistics not available",
            )
            
            messages = [
                {"role": "system", "content": INTERPRETER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            
            response = llm.invoke(messages)
            
            interpretations.append({
                "pattern_id": pattern.get("id", 0),
                "title": pattern.get("title", ""),
                "text": response.content,
            })
        
        return {
            **state,
            "visualizations": visualizations,
            "interpretations": interpretations,
            "current_stage": "visualized",
            "messages": state.get("messages", []) + [
                f"📊 Created {len(visualizations)} visualizations with interpretations."
            ],
        }
        
    except Exception as e:
        return {
            **state,
            "visualizations": [],
            "interpretations": [],
            "current_stage": "visualized",
            "error_message": f"Visualization error: {str(e)}",
            "messages": state.get("messages", []) + [f"⚠️ Visualization failed: {str(e)}"],
        }


# =============================================================================
# NODE 5: STRATEGIC RECOMMENDATIONS
# =============================================================================

def generate_recommendations(state: AnalystState) -> AnalystState:
    """
    Generate actionable business recommendations based on all findings.
    """
    patterns = state.get("approved_patterns", [])
    interpretations = state.get("interpretations", [])
    df = state["cleaned_data"]
    quality_report = state["quality_report"]
    
    try:
        llm = get_llm(temperature=0.4)
        
        # Format patterns for prompt
        patterns_text = "\n".join([
            f"- {p.get('title', 'Pattern')}: {p.get('description', '')}"
            for p in patterns
        ])
        
        # Format interpretations
        interpretations_text = "\n".join([
            f"- {i.get('title', 'Finding')}: {i.get('text', '')}"
            for i in interpretations
        ])
        
        # Key statistics
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        key_stats = ""
        if numeric_cols:
            key_stats = df[numeric_cols].describe().to_string()
        
        prompt = STRATEGIST_PROMPT.format(
            patterns=patterns_text if patterns_text else "No patterns analyzed",
            interpretations=interpretations_text if interpretations_text else "No interpretations generated",
            dataset_info=f"Rows: {len(df)}, Columns: {len(df.columns)}",
            key_stats=key_stats if key_stats else "No numeric statistics available",
        )
        
        messages = [
            {"role": "system", "content": STRATEGIST_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        
        response = llm.invoke(messages)
        result = parse_json_response(response.content)
        
        return {
            **state,
            "recommendations": result,
            "current_stage": "complete",
            "messages": state.get("messages", []) + [
                f" Analysis complete! Generated {len(result.get('recommendations', []))} recommendations."
            ],
        }
        
    except Exception as e:
        return {
            **state,
            "recommendations": {
                "executive_summary": "Unable to generate recommendations due to an error.",
                "recommendations": [],
            },
            "current_stage": "complete",
            "error_message": f"Recommendations error: {str(e)}",
            "messages": state.get("messages", []) + [f"Recommendations failed: {str(e)}"],
        }


# =============================================================================
# SQL QUERY HELPER
# =============================================================================

def execute_sql_query(state: AnalystState, query: str) -> tuple[pd.DataFrame, str]:
    """Execute a safe SELECT query on the connected database."""
    engine = state.get("sql_engine")
    
    if engine is None:
        return pd.DataFrame(), "No database connection available."
    
    # Safety check - only allow SELECT queries
    query_upper = query.strip().upper()
    if not query_upper.startswith("SELECT"):
        return pd.DataFrame(), "Only SELECT queries are allowed for safety."
    
    dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "EXEC", "EXECUTE"]
    for keyword in dangerous_keywords:
        if keyword in query_upper:
            return pd.DataFrame(), f"Query contains forbidden keyword: {keyword}"
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
        return df, ""
    except Exception as e:
        return pd.DataFrame(), f"Query error: {str(e)}"


def get_sql_tables_info(engine) -> list[dict]:
    """Get information about tables in the connected database."""
    inspector = inspect(engine)
    tables_info = []
    
    for table_name in inspector.get_table_names():
        columns = []
        for column in inspector.get_columns(table_name):
            columns.append({
                "name": column["name"],
                "type": str(column["type"]),
            })
        tables_info.append({
            "table": table_name,
            "columns": columns,
        })
    
    return tables_info


def generate_sql_query(state: AnalystState, question: str) -> tuple[str, str]:
    """Generate a SQL query to answer the user's question."""
    tables_info = state.get("sql_tables", [])
    
    if not tables_info:
        return "", "No tables available in the database."
    
    try:
        llm = get_llm(temperature=0.0)
        
        tables_str = json.dumps(tables_info, indent=2)
        
        prompt = SQL_ANALYST_PROMPT.format(
            tables_info=tables_str,
            question=question,
        )
        
        messages = [
            {"role": "system", "content": SQL_ANALYST_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        
        response = llm.invoke(messages)
        result = parse_json_response(response.content)
        
        return result.get("query", ""), result.get("reasoning", "")
        
    except Exception as e:
        return "", f"Query generation error: {str(e)}"


# =============================================================================
# GRAPH BUILDER
# =============================================================================

def create_analyst_graph() -> StateGraph:
    """Create the LangGraph state machine for the data analyst workflow."""
    
    # Define the graph
    workflow = StateGraph(AnalystState)
    
    # Add nodes
    workflow.add_node("ingest_and_profile", ingest_and_profile)
    workflow.add_node("clean_data", clean_data)
    workflow.add_node("hunt_patterns", hunt_patterns)
    workflow.add_node("visualize_and_interpret", visualize_and_interpret)
    workflow.add_node("generate_recommendations", generate_recommendations)
    
    # Set entry point
    workflow.set_entry_point("ingest_and_profile")
    
    # Add edges (linear flow with HITL pauses handled by Streamlit)
    workflow.add_edge("ingest_and_profile", END)  # Pause for user input
    workflow.add_edge("clean_data", "hunt_patterns")
    workflow.add_edge("hunt_patterns", END)  # Pause for user approval
    workflow.add_edge("visualize_and_interpret", "generate_recommendations")
    workflow.add_edge("generate_recommendations", END)
    
    return workflow


def get_initial_state() -> AnalystState:
    """Get a fresh initial state for the workflow."""
    return {
        "raw_data": None,
        "data_source_type": None,
        "data_source_name": "",
        "sql_engine": None,
        "sql_tables": [],
        "quality_report": None,
        "user_cleaning_instructions": {},
        "cleaning_code": "",
        "cleaned_data": None,
        "patterns": [],
        "approved_patterns": [],
        "visualizations": [],
        "interpretations": [],
        "recommendations": None,
        "current_stage": "start",
        "error_message": None,
        "messages": [],
    }


# =============================================================================
# CONVENIENCE FUNCTIONS FOR STREAMLIT
# =============================================================================

def load_csv(file) -> pd.DataFrame:
    """Load a CSV file into a DataFrame."""
    return pd.read_csv(file)


def load_excel(file) -> pd.DataFrame:
    """Load an Excel file into a DataFrame."""
    return pd.read_excel(file, engine='openpyxl')


def load_sqlite(db_path: str, table_name: str = None) -> tuple[pd.DataFrame, Any, list]:
    """Load data from a SQLite database."""
    engine = create_engine(f"sqlite:///{db_path}")
    tables_info = get_sql_tables_info(engine)
    
    if not tables_info:
        return pd.DataFrame(), engine, tables_info
    
    # If no table specified, use the first one
    if table_name is None:
        table_name = tables_info[0]["table"]
    
    with engine.connect() as conn:
        df = pd.read_sql(text(f"SELECT * FROM {table_name} LIMIT 10000"), conn)
    
    return df, engine, tables_info


def run_profiling(state: AnalystState) -> AnalystState:
    """Run just the profiling node."""
    return ingest_and_profile(state)


def run_cleaning(state: AnalystState) -> AnalystState:
    """Run just the cleaning node."""
    return clean_data(state)


def run_pattern_hunting(state: AnalystState) -> AnalystState:
    """Run just the pattern hunting node."""
    return hunt_patterns(state)


def run_visualization(state: AnalystState) -> AnalystState:
    """Run just the visualization and interpretation node."""
    return visualize_and_interpret(state)


def run_recommendations(state: AnalystState) -> AnalystState:
    """Run just the recommendations node."""
    return generate_recommendations(state)
