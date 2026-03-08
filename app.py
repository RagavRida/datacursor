"""
Full-Cycle Autonomous Data Analyst - Streamlit Application
Collect → Clean → Analyze → Visualize → Interpret → Recommend

Run with: streamlit run app.py
"""

import os
import json
import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from agent_logic import (
    get_initial_state,
    load_csv,
    load_excel,
    load_sqlite,
    run_profiling,
    run_cleaning,
    run_pattern_hunting,
    run_visualization,
    run_recommendations,
    execute_sql_query,
    generate_sql_query,
)

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="DataLLM - Autonomous Data Analyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern styling
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Card-like sections */
    .stExpander {
        background-color: #f8f9fa;
        border-radius: 10px;
        border: 1px solid #e9ecef;
    }
    
    /* Quality score badge */
    .quality-score {
        font-size: 2rem;
        font-weight: bold;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        color: white;
    }
    
    .quality-high { background: linear-gradient(135deg, #28a745, #20c997); }
    .quality-medium { background: linear-gradient(135deg, #ffc107, #fd7e14); }
    .quality-low { background: linear-gradient(135deg, #dc3545, #e83e8c); }
    
    /* Pattern card */
    .pattern-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
    }
    
    /* Recommendation card */
    .rec-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin-bottom: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Stage indicator */
    .stage-indicator {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    
    .stage-complete { background-color: #d4edda; color: #155724; }
    .stage-active { background-color: #cce5ff; color: #004085; }
    .stage-pending { background-color: #f8f9fa; color: #6c757d; }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

if "analyst_state" not in st.session_state:
    st.session_state.analyst_state = get_initial_state()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def reset_state():
    """Reset the entire workflow state."""
    st.session_state.analyst_state = get_initial_state()
    st.session_state.chat_history = []


# =============================================================================
# SIDEBAR - DATA INPUT
# =============================================================================

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/analytics.png", width=60)
    st.title("DataLLM")
    st.caption("🤖 Autonomous Data Analyst")
    
    st.divider()
    
    # API Key Configuration
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        api_key = st.text_input(
            "🔑 Google API Key",
            type="password",
            help="Required for AI analysis. Get one at https://makersuite.google.com/app/apikey"
        )
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
    else:
        st.success("✅ API Key configured")
    
    st.divider()
    
    # Data Source Selection
    st.subheader("📤 Data Source")
    
    data_source = st.radio(
        "Choose input method:",
        ["Upload File", "Connect to SQLite"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if data_source == "Upload File":
        uploaded_file = st.file_uploader(
            "Upload CSV or Excel",
            type=["csv", "xlsx", "xls"],
            help="Supported formats: CSV, Excel (.xlsx, .xls)"
        )
        
        if uploaded_file is not None:
            if st.button("📥 Load Data", use_container_width=True, type="primary"):
                try:
                    if uploaded_file.name.endswith(".csv"):
                        df = load_csv(uploaded_file)
                        st.session_state.analyst_state["data_source_type"] = "csv"
                    else:
                        df = load_excel(uploaded_file)
                        st.session_state.analyst_state["data_source_type"] = "excel"
                    
                    st.session_state.analyst_state["raw_data"] = df
                    st.session_state.analyst_state["data_source_name"] = uploaded_file.name
                    st.session_state.analyst_state["current_stage"] = "start"
                    
                    # Auto-run profiling
                    st.session_state.analyst_state = run_profiling(st.session_state.analyst_state)
                    st.success(f"✅ Loaded {len(df):,} rows × {len(df.columns)} columns")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error loading file: {str(e)}")
    
    else:  # SQLite Connection
        st.info("💡 Upload a SQLite database file (.db, .sqlite)")
        
        db_file = st.file_uploader(
            "Upload SQLite Database",
            type=["db", "sqlite", "sqlite3"],
            label_visibility="collapsed"
        )
        
        if db_file is not None:
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
                tmp.write(db_file.read())
                tmp_path = tmp.name
            
            try:
                df, engine, tables = load_sqlite(tmp_path)
                
                if tables:
                    st.session_state.analyst_state["sql_engine"] = engine
                    st.session_state.analyst_state["sql_tables"] = tables
                    
                    # Table selection
                    table_names = [t["table"] for t in tables]
                    selected_table = st.selectbox("Select Table", table_names)
                    
                    if st.button("📥 Load Table", use_container_width=True, type="primary"):
                        df, _, _ = load_sqlite(tmp_path, selected_table)
                        st.session_state.analyst_state["raw_data"] = df
                        st.session_state.analyst_state["data_source_type"] = "sqlite"
                        st.session_state.analyst_state["data_source_name"] = f"{db_file.name} → {selected_table}"
                        
                        # Auto-run profiling
                        st.session_state.analyst_state = run_profiling(st.session_state.analyst_state)
                        st.success(f"✅ Loaded {len(df):,} rows")
                        st.rerun()
                else:
                    st.warning("No tables found in database")
                    
            except Exception as e:
                st.error(f"❌ Database error: {str(e)}")
    
    st.divider()
    
    # Workflow Progress
    state = st.session_state.analyst_state
    current_stage = state.get("current_stage", "start")
    
    st.subheader("📈 Workflow Progress")
    
    stages = [
        ("start", "📤 Upload", "Upload data"),
        ("profiled", "🔍 Profile", "Quality report"),
        ("cleaned", "🧹 Clean", "Data cleaning"),
        ("patterns_found", "🔎 Analyze", "Pattern detection"),
        ("visualized", "📊 Visualize", "Charts & insights"),
        ("complete", "✅ Complete", "Recommendations"),
    ]
    
    stage_order = [s[0] for s in stages]
    current_idx = stage_order.index(current_stage) if current_stage in stage_order else 0
    
    for idx, (stage_key, icon, label) in enumerate(stages):
        if idx < current_idx:
            st.markdown(f"<span class='stage-indicator stage-complete'>{icon} {label}</span>", unsafe_allow_html=True)
        elif idx == current_idx:
            st.markdown(f"<span class='stage-indicator stage-active'>{icon} {label}</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"<span class='stage-indicator stage-pending'>{icon} {label}</span>", unsafe_allow_html=True)
    
    st.divider()
    
    if st.button("🔄 Start Over", use_container_width=True):
        reset_state()
        st.rerun()


# =============================================================================
# MAIN CONTENT AREA
# =============================================================================

state = st.session_state.analyst_state
current_stage = state.get("current_stage", "start")

# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.title("📊 Autonomous Data Analyst")
    if state.get("data_source_name"):
        st.caption(f"Analyzing: **{state['data_source_name']}**")

# Error display
if state.get("error_message"):
    st.error(f"⚠️ {state['error_message']}")


# =============================================================================
# STAGE: START (No data loaded)
# =============================================================================

if current_stage == "start" and state.get("raw_data") is None:
    st.info("👈 **Upload a dataset** or connect to a database using the sidebar to get started.")
    
    with st.expander("ℹ️ What can this tool do?", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            ### 🧹 Smart Cleaning
            - Detect missing values
            - Find duplicates
            - Fix data types
            - Human-in-the-loop approval
            """)
        
        with col2:
            st.markdown("""
            ### 🔍 Pattern Discovery
            - Correlation analysis
            - Trend detection
            - Outlier identification
            - Auto-prioritization
            """)
        
        with col3:
            st.markdown("""
            ### 💡 Strategic Insights
            - Interactive visualizations
            - Narrative interpretations
            - Business recommendations
            - Actionable next steps
            """)


# =============================================================================
# STAGE: PROFILED (Show quality report, ask for cleaning input)
# =============================================================================

elif current_stage == "profiled":
    quality_report = state.get("quality_report", {})
    
    st.header("📋 Data Quality Report")
    
    # Quality Score
    score = quality_report.get("quality_score", 0)
    score_class = "quality-high" if score >= 80 else "quality-medium" if score >= 50 else "quality-low"
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        <div class="quality-score {score_class}">
            Data Quality Score: {score}/100
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Shape info
    shape = quality_report.get("shape", {})
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows", f"{shape.get('rows', 0):,}")
    col2.metric("Columns", shape.get("columns", 0))
    col3.metric("Duplicates", quality_report.get("duplicate_rows", 0))
    col4.metric("Missing Cells", sum(v["count"] for v in quality_report.get("missing_values", {}).values()))
    
    # Data Preview
    with st.expander("👀 Data Preview", expanded=True):
        st.dataframe(state["raw_data"].head(10), use_container_width=True)
    
    # Missing Values
    missing = quality_report.get("missing_values", {})
    if missing:
        st.subheader("⚠️ Missing Values - Human Decision Required")
        
        st.info("🧑‍💼 **Your input needed:** Select how to handle missing values for each column.")
        
        cleaning_instructions = {}
        
        cols = st.columns(min(3, len(missing)))
        for idx, (col_name, info) in enumerate(missing.items()):
            with cols[idx % 3]:
                st.markdown(f"**{col_name}**")
                st.caption(f"{info['count']} missing ({info['percentage']}%)")
                
                # Check if numeric
                is_numeric = col_name in quality_report.get("numeric_columns", [])
                
                if is_numeric:
                    options = ["Ignore", "Drop Rows", "Fill with Mean", "Fill with Median", "Fill with 0"]
                else:
                    options = ["Ignore", "Drop Rows", "Fill with Mode", "Fill with 'Unknown'"]
                
                choice = st.selectbox(
                    "Action",
                    options,
                    key=f"clean_{col_name}",
                    label_visibility="collapsed"
                )
                
                if choice != "Ignore":
                    cleaning_instructions[col_name] = choice
        
        # Duplicate handling
        if quality_report.get("duplicate_rows", 0) > 0:
            st.divider()
            st.subheader("📋 Duplicate Rows")
            handle_dupes = st.checkbox(
                f"Remove {quality_report['duplicate_rows']} duplicate rows",
                value=True
            )
            if handle_dupes:
                cleaning_instructions["__duplicates__"] = "drop"
    
    else:
        cleaning_instructions = {}
        st.success("✅ No missing values detected!")
    
    # Proceed button
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 Clean & Continue", type="primary", use_container_width=True):
            state["user_cleaning_instructions"] = cleaning_instructions
            state = run_cleaning(state)
            state = run_pattern_hunting(state)
            st.session_state.analyst_state = state
            st.rerun()
    
    with col2:
        if st.button("⏭️ Skip Cleaning", use_container_width=True):
            state["user_cleaning_instructions"] = {}
            state["cleaned_data"] = state["raw_data"].copy()
            state["current_stage"] = "cleaned"
            state = run_pattern_hunting(state)
            st.session_state.analyst_state = state
            st.rerun()


# =============================================================================
# STAGE: PATTERNS FOUND (Show patterns, ask for approval)
# =============================================================================

elif current_stage == "patterns_found":
    patterns = state.get("patterns", [])
    
    st.header("🔍 Discovered Patterns")
    
    if not patterns:
        st.warning("No significant patterns were detected in the data.")
        if st.button("📊 Skip to Recommendations", type="primary"):
            state["approved_patterns"] = []
            state["current_stage"] = "visualized"
            state = run_recommendations(state)
            st.session_state.analyst_state = state
            st.rerun()
    else:
        st.info("🧑‍💼 **Your input needed:** Select which patterns to visualize and analyze further.")
        
        approved = []
        
        for pattern in patterns:
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    impact = pattern.get("business_impact", "medium")
                    impact_emoji = "🔥" if impact == "high" else "📊" if impact == "medium" else "📉"
                    
                    st.markdown(f"""
                    ### {impact_emoji} {pattern.get('title', 'Pattern')}
                    
                    {pattern.get('description', '')}
                    
                    **Columns:** {', '.join(pattern.get('columns_involved', []))} | 
                    **Chart Type:** {pattern.get('visualization_type', 'auto')} | 
                    **Impact:** {impact.title()}
                    """)
                
                with col2:
                    if st.checkbox("Visualize", value=True, key=f"approve_{pattern.get('id', 0)}"):
                        approved.append(pattern)
                
                st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Generate Visualizations", type="primary", use_container_width=True):
                state["approved_patterns"] = approved
                state = run_visualization(state)
                state = run_recommendations(state)
                st.session_state.analyst_state = state
                st.rerun()
        
        with col2:
            if st.button("⏭️ Skip Visualizations", use_container_width=True):
                state["approved_patterns"] = []
                state["current_stage"] = "visualized"
                state = run_recommendations(state)
                st.session_state.analyst_state = state
                st.rerun()


# =============================================================================
# STAGE: COMPLETE (Show everything)
# =============================================================================

elif current_stage in ["visualized", "complete"]:
    st.header("📊 Analysis Complete")
    
    # Executive Summary
    recommendations = state.get("recommendations", {})
    if recommendations and recommendations.get("executive_summary"):
        st.markdown(f"""
        > ### 💼 Executive Summary
        > {recommendations.get('executive_summary', '')}
        """)
    
    st.divider()
    
    # Tabs for organized content
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Visualizations", "💡 Recommendations", "🔍 SQL Explorer", "📋 Data"])
    
    # Tab 1: Visualizations
    with tab1:
        visualizations = state.get("visualizations", [])
        interpretations = state.get("interpretations", [])
        
        if not visualizations:
            st.info("No visualizations were generated. Select patterns to visualize in the analysis step.")
        else:
            for viz in visualizations:
                with st.container():
                    st.plotly_chart(viz.get("figure"), use_container_width=True)
                    
                    # Find matching interpretation
                    interp = next(
                        (i for i in interpretations if i.get("pattern_id") == viz.get("pattern_id")),
                        None
                    )
                    
                    if interp:
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #667eea22, #764ba222); 
                                    padding: 1rem; border-radius: 10px; border-left: 4px solid #667eea;">
                            <strong>📝 Interpretation:</strong><br>
                            {interp.get('text', '')}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.divider()
    
    # Tab 2: Recommendations
    with tab2:
        recs = recommendations.get("recommendations", [])
        
        if not recs:
            st.info("No recommendations were generated.")
        else:
            for rec in recs:
                priority = rec.get("priority", 99)
                effort = rec.get("effort", "medium")
                timeline = rec.get("timeline", "short-term")
                
                effort_color = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(effort, "⚪")
                
                st.markdown(f"""
                <div class="rec-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong style="font-size: 1.1rem;">#{priority}. {rec.get('title', 'Recommendation')}</strong>
                        <span>{effort_color} {effort.title()} Effort | 🕐 {timeline.title()}</span>
                    </div>
                    <p style="margin: 0.5rem 0;">{rec.get('action', '')}</p>
                    <details>
                        <summary style="cursor: pointer; color: #667eea;">📊 View Evidence</summary>
                        <p style="margin-top: 0.5rem; padding: 0.5rem; background: #f8f9fa; border-radius: 5px;">
                            {rec.get('data_evidence', 'No specific data evidence provided.')}
                        </p>
                    </details>
                    <p style="margin-top: 0.5rem; color: #28a745;">
                        <strong>Expected Impact:</strong> {rec.get('expected_impact', 'Not estimated')}
                    </p>
                </div>
                """, unsafe_allow_html=True)
    
    # Tab 3: SQL Explorer
    with tab3:
        st.subheader("🔍 Query Your Data")
        
        if state.get("sql_engine") is not None:
            st.success("✅ Database connected. Ask questions in natural language!")
            
            # Show available tables
            with st.expander("📋 Available Tables"):
                for table in state.get("sql_tables", []):
                    cols = ", ".join([c["name"] for c in table["columns"]])
                    st.markdown(f"**{table['table']}**: `{cols}`")
            
            # Natural language query
            user_question = st.text_input(
                "Ask a question about your data:",
                placeholder="e.g., What are the top 10 products by revenue?"
            )
            
            if user_question:
                with st.spinner("Generating SQL query..."):
                    query, reasoning = generate_sql_query(state, user_question)
                
                if query:
                    st.code(query, language="sql")
                    st.caption(f"💭 {reasoning}")
                    
                    if st.button("▶️ Execute Query"):
                        result_df, error = execute_sql_query(state, query)
                        
                        if error:
                            st.error(error)
                        else:
                            st.dataframe(result_df, use_container_width=True)
                else:
                    st.error("Could not generate query. Try rephrasing your question.")
        
        else:
            st.info("💡 SQL Explorer is available when you connect to a SQLite database.")
            
            # Still allow querying the DataFrame using natural language
            if state.get("cleaned_data") is not None:
                st.markdown("---")
                st.markdown("**Quick Data Queries** (on loaded DataFrame)")
                
                query_type = st.selectbox(
                    "Select query type:",
                    ["Summary Statistics", "Value Counts", "Filter Data", "Correlation Matrix"]
                )
                
                df = state["cleaned_data"]
                
                if query_type == "Summary Statistics":
                    st.dataframe(df.describe(), use_container_width=True)
                
                elif query_type == "Value Counts":
                    col = st.selectbox("Select column:", df.columns)
                    st.dataframe(df[col].value_counts().head(20), use_container_width=True)
                
                elif query_type == "Filter Data":
                    col = st.selectbox("Filter by column:", df.columns)
                    unique_vals = df[col].dropna().unique()[:50]  # Limit options
                    selected = st.multiselect("Select values:", unique_vals)
                    if selected:
                        st.dataframe(df[df[col].isin(selected)], use_container_width=True)
                
                elif query_type == "Correlation Matrix":
                    numeric_df = df.select_dtypes(include=['number'])
                    if len(numeric_df.columns) >= 2:
                        corr = numeric_df.corr()
                        import plotly.express as px
                        fig = px.imshow(corr, text_auto=True, title="Correlation Matrix")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Not enough numeric columns for correlation matrix.")
    
    # Tab 4: Data Preview
    with tab4:
        st.subheader("📋 Cleaned Data")
        
        if state.get("cleaned_data") is not None:
            df = state["cleaned_data"]
            
            col1, col2 = st.columns(2)
            col1.metric("Rows", f"{len(df):,}")
            col2.metric("Columns", len(df.columns))
            
            st.dataframe(df, use_container_width=True)
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download Cleaned Data (CSV)",
                data=csv,
                file_name="cleaned_data.csv",
                mime="text/csv",
            )


# =============================================================================
# FOOTER
# =============================================================================

st.divider()
st.caption("🤖 DataLLM - Powered by Gemini AI | Built with Streamlit & LangGraph")
