"""
TradingAgents Web Interface - Streamlit Application

A web-based interface for TradingAgents multi-agent financial trading framework.
Features:
- Single stock analysis (existing)
- Stock screening (Phase 1: Board heat, Phase 2: Quantitative screening)
- Batch analysis with comparison (Phase 3)
- Follow-up questions on results
"""

import streamlit as st
import datetime
import json
import time
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
load_dotenv(".env.enterprise", override=False)

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.interface import route_to_vendor

# 报告质量评估模块
try:
    from scripts.streamlit_quality_integration import render_quality_evaluation
    QUALITY_EVAL_AVAILABLE = True
except ImportError:
    QUALITY_EVAL_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="TradingAgents",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Constants
ANALYST_ORDER = ["market", "social", "news", "fundamentals"]
ANALYST_LABELS = {
    "market": "Market Analyst",
    "social": "Social Analyst",
    "news": "News Analyst",
    "fundamentals": "Fundamentals Analyst",
}

FIXED_AGENTS = {
    "Research Team": ["Bull Researcher", "Bear Researcher", "Research Manager"],
    "Trading Team": ["Trader"],
    "Risk Management": ["Aggressive Analyst", "Neutral Analyst", "Conservative Analyst"],
    "Portfolio Management": ["Portfolio Manager"],
}


def get_default_config():
    """Get default configuration."""
    config = DEFAULT_CONFIG.copy()
    return config


def render_sidebar_single_stock():
    """Render sidebar for single stock analysis mode."""
    st.sidebar.title("Single Stock Analysis")
    st.sidebar.markdown("---")

    # Step 1: Ticker symbol
    ticker = st.sidebar.text_input(
        "Ticker Symbol",
        value="000001.SZ",
        help="Enter the exact ticker symbol (e.g., SPY, CNC.TO, 7203.T, 0700.HK)"
    )

    # Step 2: Analysis date
    today = datetime.datetime.now().date()
    analysis_date = st.sidebar.date_input(
        "Analysis Date",
        value=today,
        max_value=today,
        help="Select the date for analysis"
    )
    analysis_date_str = analysis_date.strftime("%Y-%m-%d")

    # Step 3: Output language
    output_language = st.sidebar.selectbox(
        "Output Language",
        options=["English", "Chinese"],
        index=0,
        help="Language for analyst reports and final decision"
    )

    # Step 4: Select analysts
    st.sidebar.markdown("**Analyst Team Selection**")
    analyst_options = [
        ANALYST_LABELS["market"],
        ANALYST_LABELS["social"],
        ANALYST_LABELS["news"],
        ANALYST_LABELS["fundamentals"],
    ]
    selected_analyst_labels = st.sidebar.multiselect(
        "Select Analysts",
        options=analyst_options,
        default=analyst_options,
        help="Choose which analysts to include in the analysis"
    )

    # Convert labels back to keys
    selected_analysts = []
    for label in selected_analyst_labels:
        for key, value in ANALYST_LABELS.items():
            if value == label:
                selected_analysts.append(key)

    # Normalize to predefined order
    selected_analysts = [a for a in ANALYST_ORDER if a in selected_analysts]

    # Step 5: Research depth
    research_depth = st.sidebar.slider(
        "Research Depth",
        min_value=1,
        max_value=5,
        value=1,
        step=1,
        help="Number of debate rounds for research and risk discussions"
    )

    # Step 6: LLM Provider (simplified for web - uses default kunlun)
    st.sidebar.markdown("**LLM Settings**")
    st.sidebar.info("Using default kunlun provider with qwen3.5-35b-a3b model")

    st.sidebar.markdown("---")

    # Start button
    start_analysis = st.sidebar.button("Start Analysis", type="primary")

    return {
        "ticker": ticker,
        "analysis_date": analysis_date_str,
        "analysts": selected_analysts,
        "research_depth": research_depth,
        "output_language": output_language,
        "start": start_analysis,
    }


def render_sidebar_screening():
    """Render sidebar for stock screening mode."""
    st.sidebar.title("Stock Screening")
    st.sidebar.markdown("---")

    # Analysis date
    today = datetime.datetime.now().date()
    analysis_date = st.sidebar.date_input(
        "Analysis Date",
        value=today,
        max_value=today,
        help="Select the date for screening"
    )
    analysis_date_str = analysis_date.strftime("%Y-%m-%d")

    # Output language
    output_language = st.sidebar.selectbox(
        "Output Language",
        options=["English", "Chinese"],
        index=1,  # Default Chinese for screening
        help="Language for reports"
    )

    st.sidebar.markdown("---")

    # Phase 1: Board Heat Analysis
    st.sidebar.markdown("**Phase 1: Board Heat Analysis**")
    phase1_run = st.sidebar.button("Get Hot Stocks", key="phase1_btn")

    st.sidebar.markdown("---")

    # Phase 2: Stock Screening
    st.sidebar.markdown("**Phase 2: Quantitative Screening**")

    # Screening parameters
    pe_max = st.sidebar.slider("Max PE", 0, 100, 50, help="Maximum PE ratio")
    pb_max = st.sidebar.slider("Max PB", 0, 20, 5, help="Maximum PB ratio")
    min_turnover = st.sidebar.slider("Min Turnover Rate (%)", 0.0, 10.0, 2.0, 0.5, help="Minimum daily turnover rate")

    phase2_run = st.sidebar.button("Screen Stocks", key="phase2_btn")

    st.sidebar.markdown("---")

    # 手动批量输入
    st.sidebar.markdown("**快速股票对比**")
    batch_tickers_input = st.sidebar.text_area(
        "输入股票列表",
        value="",
        height=100,
        help="输入多个股票代码，用逗号、空格或换行分隔\n示例: 000001, 600000, 000002"
    )
    quick_compare_btn = st.sidebar.button("快速对比分析", type="primary", key="quick_compare_btn")

    st.sidebar.markdown("---")

    # Phase 3: Selected Stocks for Batch Analysis
    st.sidebar.markdown("**Phase 3: Batch Analysis**")

    # Manual ticker input
    manual_ticker = st.sidebar.text_input(
        "Add Ticker",
        value="",
        help="Enter ticker (e.g., 000001.SZ)"
    )
    add_ticker_btn = st.sidebar.button("Add", key="add_ticker_btn")

    # Research depth for batch analysis
    batch_depth = st.sidebar.slider(
        "Research Depth",
        min_value=1,
        max_value=3,
        value=1,
        step=1,
        help="Debate rounds (lower for faster batch analysis)"
    )

    batch_run = st.sidebar.button("Run Batch Analysis", type="primary", key="batch_btn")

    st.sidebar.markdown("---")

    # Follow-up question input
    st.sidebar.markdown("**Follow-up Questions**")
    followup_question = st.sidebar.text_input(
        "Ask about results",
        value="",
        help="Ask questions about batch analysis results"
    )
    followup_btn = st.sidebar.button("Ask", key="followup_btn")
    deep_analysis_btn = st.sidebar.button("Deep Analysis (10-30s)", key="deep_btn")

    return {
        "analysis_date": analysis_date_str,
        "output_language": output_language,
        "pe_max": pe_max,
        "pb_max": pb_max,
        "min_turnover": min_turnover,
        "phase1_run": phase1_run,
        "phase2_run": phase2_run,
        "batch_tickers_input": batch_tickers_input,
        "quick_compare_btn": quick_compare_btn,
        "manual_ticker": manual_ticker,
        "add_ticker_btn": add_ticker_btn,
        "batch_depth": batch_depth,
        "batch_run": batch_run,
        "followup_question": followup_question,
        "followup_btn": followup_btn,
        "deep_analysis_btn": deep_analysis_btn,
    }


def render_sidebar():
    """Render sidebar with mode selection."""
    st.sidebar.title("TradingAgents Configuration")
    st.sidebar.markdown("---")

    # Mode selection
    mode = st.sidebar.radio(
        "Analysis Mode",
        options=["Single Stock", "Stock Screening"],
        index=0,
        help="Choose analysis mode"
    )

    st.session_state["analysis_mode"] = mode

    if mode == "Single Stock":
        return render_sidebar_single_stock()
    else:
        return render_sidebar_screening()


def render_agent_status(status_dict: Dict[str, str]):
    """Render agent status indicators."""
    status_colors = {
        "pending": "⚪",
        "in_progress": "🔵",
        "completed": "✅",
        "error": "❌",
    }

    status_html = "<div style='display: flex; flex-wrap: wrap; gap: 10px;'>"

    for agent, status in status_dict.items():
        icon = status_colors.get(status, "⚪")
        status_html += f"<span style='padding: 5px 10px; border-radius: 5px; background: #f0f0f0;'>{icon} {agent}</span>"

    status_html += "</div>"
    st.markdown(status_html, unsafe_allow_html=True)


def render_analyst_reports(final_state: Dict[str, Any], selected_analysts: List[str]):
    """Render analyst team reports in expanders."""
    st.subheader("I. Analyst Team Reports")

    if final_state.get("market_report") and "market" in selected_analysts:
        with st.expander("Market Analyst", expanded=True):
            st.markdown(final_state["market_report"])

    if final_state.get("sentiment_report") and "social" in selected_analysts:
        with st.expander("Social Analyst", expanded=True):
            st.markdown(final_state["sentiment_report"])

    if final_state.get("news_report") and "news" in selected_analysts:
        with st.expander("News Analyst", expanded=True):
            st.markdown(final_state["news_report"])

    if final_state.get("fundamentals_report") and "fundamentals" in selected_analysts:
        with st.expander("Fundamentals Analyst", expanded=True):
            st.markdown(final_state["fundamentals_report"])


def render_research_team(final_state: Dict[str, Any]):
    """Render research team debate results."""
    st.subheader("II. Research Team Decision")

    if final_state.get("investment_debate_state"):
        debate = final_state["investment_debate_state"]

        col1, col2 = st.columns(2)

        with col1:
            if debate.get("bull_history"):
                with st.expander("Bull Researcher", expanded=True):
                    st.markdown(debate["bull_history"])

        with col2:
            if debate.get("bear_history"):
                with st.expander("Bear Researcher", expanded=True):
                    st.markdown(debate["bear_history"])

        if debate.get("judge_decision"):
            st.markdown("---")
            st.markdown("**Research Manager Decision:**")
            st.markdown(debate["judge_decision"])


def render_trading_team(final_state: Dict[str, Any]):
    """Render trading team plan."""
    st.subheader("III. Trading Team Plan")

    if final_state.get("trader_investment_plan"):
        st.markdown(final_state["trader_investment_plan"])


def render_risk_management(final_state: Dict[str, Any]):
    """Render risk management team analysis."""
    st.subheader("IV. Risk Management Team")

    if final_state.get("risk_debate_state"):
        risk = final_state["risk_debate_state"]

        col1, col2, col3 = st.columns(3)

        with col1:
            if risk.get("aggressive_history"):
                with st.expander("Aggressive Analyst"):
                    st.markdown(risk["aggressive_history"])

        with col2:
            if risk.get("conservative_history"):
                with st.expander("Conservative Analyst"):
                    st.markdown(risk["conservative_history"])

        with col3:
            if risk.get("neutral_history"):
                with st.expander("Neutral Analyst"):
                    st.markdown(risk["neutral_history"])


def render_portfolio_decision(final_state: Dict[str, Any]):
    """Render portfolio manager final decision."""
    st.subheader("V. Portfolio Manager Decision")

    if final_state.get("risk_debate_state"):
        risk = final_state["risk_debate_state"]
        if risk.get("judge_decision"):
            # Highlight final decision
            st.markdown(
                f"""
                <div style="padding: 20px; border-radius: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                    <h3 style="color: white; margin-bottom: 10px;">Final Portfolio Decision</h3>
                    {risk["judge_decision"]}
                </div>
                """,
                unsafe_allow_html=True
            )


def render_final_decision(decision: str):
    """Render the extracted final decision rating."""
    st.markdown("---")

    # Decision color mapping
    decision_colors = {
        "BUY": "#28a745",
        "OVERWEIGHT": "#5cb85c",
        "HOLD": "#ffc107",
        "UNDERWEIGHT": "#fd7e14",
        "SELL": "#dc3545",
    }

    color = decision_colors.get(decision.upper(), "#6c757d")

    st.markdown(
        f"""
        <div style="padding: 15px; border-radius: 10px; background: {color}; color: white; text-align: center;">
            <h2 style="color: white; margin: 0;">{decision}</h2>
        </div>
        """,
        unsafe_allow_html=True
    )


def generate_markdown_report(final_state: Dict[str, Any], ticker: str) -> str:
    """Generate complete markdown report for download."""
    report_parts = []

    header = f"# Trading Analysis Report: {ticker}\n\n"
    header += f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    report_parts.append(header)

    # Analyst Team
    analyst_parts = []
    if final_state.get("market_report"):
        analyst_parts.append(f"### Market Analyst\n{final_state['market_report']}")
    if final_state.get("sentiment_report"):
        analyst_parts.append(f"### Social Analyst\n{final_state['sentiment_report']}")
    if final_state.get("news_report"):
        analyst_parts.append(f"### News Analyst\n{final_state['news_report']}")
    if final_state.get("fundamentals_report"):
        analyst_parts.append(f"### Fundamentals Analyst\n{final_state['fundamentals_report']}")

    if analyst_parts:
        report_parts.append(f"## I. Analyst Team Reports\n\n" + "\n\n".join(analyst_parts))

    # Research Team
    if final_state.get("investment_debate_state"):
        debate = final_state["investment_debate_state"]
        research_parts = []
        if debate.get("bull_history"):
            research_parts.append(f"### Bull Researcher\n{debate['bull_history']}")
        if debate.get("bear_history"):
            research_parts.append(f"### Bear Researcher\n{debate['bear_history']}")
        if debate.get("judge_decision"):
            research_parts.append(f"### Research Manager Decision\n{debate['judge_decision']}")

        if research_parts:
            report_parts.append(f"## II. Research Team Decision\n\n" + "\n\n".join(research_parts))

    # Trading Team
    if final_state.get("trader_investment_plan"):
        report_parts.append(f"## III. Trading Team Plan\n\n### Trader\n{final_state['trader_investment_plan']}")

    # Risk Management
    if final_state.get("risk_debate_state"):
        risk = final_state["risk_debate_state"]
        risk_parts = []
        if risk.get("aggressive_history"):
            risk_parts.append(f"### Aggressive Analyst\n{risk['aggressive_history']}")
        if risk.get("conservative_history"):
            risk_parts.append(f"### Conservative Analyst\n{risk['conservative_history']}")
        if risk.get("neutral_history"):
            risk_parts.append(f"### Neutral Analyst\n{risk['neutral_history']}")

        if risk_parts:
            report_parts.append(f"## IV. Risk Management Team\n\n" + "\n\n".join(risk_parts))

        # Portfolio Manager
        if risk.get("judge_decision"):
            report_parts.append(f"## V. Portfolio Manager Decision\n\n{risk['judge_decision']}")

    return "\n\n".join(report_parts)


def generate_json_state(final_state: Dict[str, Any]) -> str:
    """Generate JSON state log for download."""
    # Clean state for JSON serialization
    clean_state = {}

    def serialize_value(value):
        """Recursively serialize values, handling langchain message objects."""
        if isinstance(value, (str, int, float, bool, type(None))):
            return value
        elif isinstance(value, dict):
            return {k: serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [serialize_value(item) for item in value]
        elif hasattr(value, 'content'):  # LangChain message objects
            return {"type": value.__class__.__name__, "content": str(value.content)}
        else:
            return str(value)

    for key, value in final_state.items():
        clean_state[key] = serialize_value(value)

    return json.dumps(clean_state, indent=2, ensure_ascii=False)


def run_analysis(user_selections: Dict[str, Any]):
    """Run the trading agents analysis."""
    # Create config
    config = get_default_config()
    config["max_debate_rounds"] = user_selections["research_depth"]
    config["max_risk_discuss_rounds"] = user_selections["research_depth"]
    config["output_language"] = user_selections["output_language"]

    # Initialize graph
    graph = TradingAgentsGraph(
        selected_analysts=user_selections["analysts"],
        config=config,
        debug=True,
    )

    # Initialize agent status tracking
    agent_status = {}

    # Add selected analysts to status
    for analyst_key in user_selections["analysts"]:
        if analyst_key in ANALYST_LABELS:
            agent_status[ANALYST_LABELS[analyst_key]] = "pending"

    # Add fixed teams
    for team_agents in FIXED_AGENTS.values():
        for agent in team_agents:
            agent_status[agent] = "pending"

    # Create initial state
    init_state = graph.propagator.create_initial_state(
        user_selections["ticker"],
        user_selections["analysis_date"]
    )
    args = graph.propagator.get_graph_args()

    # Stream execution with progress
    status_placeholder = st.empty()
    progress_bar = st.progress(0)

    trace = []
    current_agent = None

    # Track analyst completion
    completed_analysts = set()

    with st.status("Running analysis...", expanded=True) as status:
        st.write(f"Analyzing **{user_selections['ticker']}** on **{user_selections['analysis_date']}**...")

        # Update status for first analyst
        if user_selections["analysts"]:
            first_analyst = ANALYST_LABELS[user_selections["analysts"][0]]
            agent_status[first_analyst] = "in_progress"

        for chunk in graph.graph.stream(init_state, **args):
            # Update agent status based on report state
            for analyst_key in user_selections["analysts"]:
                report_key_map = {
                    "market": "market_report",
                    "social": "sentiment_report",
                    "news": "news_report",
                    "fundamentals": "fundamentals_report",
                }

                if analyst_key in report_key_map:
                    report_key = report_key_map[analyst_key]
                    if chunk.get(report_key):
                        agent_status[ANALYST_LABELS[analyst_key]] = "completed"
                        completed_analysts.add(analyst_key)
                        st.write(f"Completed: {ANALYST_LABELS[analyst_key]}")

            # Research Team
            if chunk.get("investment_debate_state"):
                debate = chunk["investment_debate_state"]
                if debate.get("bull_history") or debate.get("bear_history"):
                    agent_status["Bull Researcher"] = "in_progress"
                    agent_status["Bear Researcher"] = "in_progress"
                if debate.get("judge_decision"):
                    agent_status["Bull Researcher"] = "completed"
                    agent_status["Bear Researcher"] = "completed"
                    agent_status["Research Manager"] = "completed"
                    agent_status["Trader"] = "in_progress"
                    st.write("Completed: Research Team")

            # Trading Team
            if chunk.get("trader_investment_plan"):
                agent_status["Trader"] = "completed"
                agent_status["Aggressive Analyst"] = "in_progress"
                st.write("Completed: Trading Team")

            # Risk Management
            if chunk.get("risk_debate_state"):
                risk = chunk["risk_debate_state"]
                if risk.get("aggressive_history"):
                    agent_status["Aggressive Analyst"] = "in_progress"
                if risk.get("conservative_history"):
                    agent_status["Conservative Analyst"] = "in_progress"
                if risk.get("neutral_history"):
                    agent_status["Neutral Analyst"] = "in_progress"
                if risk.get("judge_decision"):
                    agent_status["Aggressive Analyst"] = "completed"
                    agent_status["Conservative Analyst"] = "completed"
                    agent_status["Neutral Analyst"] = "completed"
                    agent_status["Portfolio Manager"] = "completed"
                    st.write("Completed: Risk Management Team")

            # Update progress
            total_agents = len(agent_status)
            completed_count = sum(1 for s in agent_status.values() if s == "completed")
            progress_bar.progress(completed_count / total_agents)

            # Update status display
            status_placeholder.markdown(render_agent_status_html(agent_status), unsafe_allow_html=True)

            trace.append(chunk)

        # Final state
        final_state = trace[-1]
        decision = graph.process_signal(final_state["final_trade_decision"])

        # Mark all as completed
        for agent in agent_status:
            agent_status[agent] = "completed"

        progress_bar.progress(1.0)
        status.update(label="Analysis Complete!", state="complete")

    return final_state, decision, agent_status


def render_agent_status_html(status_dict: Dict[str, str]) -> str:
    """Render agent status as HTML for live updates."""
    status_colors = {
        "pending": "#adb5bd",
        "in_progress": "#0d6efd",
        "completed": "#28a745",
        "error": "#dc3545",
    }

    html = "<div style='padding: 10px;'>"

    # Group by teams
    teams = {
        "Analyst Team": [ANALYST_LABELS[k] for k in ANALYST_ORDER],
        "Research Team": ["Bull Researcher", "Bear Researcher", "Research Manager"],
        "Trading Team": ["Trader"],
        "Risk Management": ["Aggressive Analyst", "Neutral Analyst", "Conservative Analyst"],
        "Portfolio Management": ["Portfolio Manager"],
    }

    for team, agents in teams.items():
        html += f"<div style='margin-bottom: 5px;'><b>{team}:</b> "
        for agent in agents:
            if agent in status_dict:
                status = status_dict[agent]
                color = status_colors.get(status, "#adb5bd")
                icon = "○" if status == "pending" else "◐" if status == "in_progress" else "●"
                html += f"<span style='color: {color};'>{icon} {agent}</span>  "
        html += "</div>"

    html += "</div>"
    return html


# ============================================================================
# Stock Screening Functions
# ============================================================================

def run_phase1_hot_stocks(analysis_date: str) -> str:
    """Run Phase 1: Get hot stocks ranking."""
    try:
        result = route_to_vendor("get_hot_stocks", analysis_date, "ths")
        return result
    except Exception as e:
        return f"Error getting hot stocks: {str(e)}"


def run_phase2_screening(analysis_date: str, pe_max: float, pb_max: float, min_turnover: float) -> str:
    """Run Phase 2: Quantitative stock screening."""
    try:
        result = route_to_vendor(
            "screen_stocks_by_metrics",
            analysis_date,
            pe_max,
            pb_max,
            10.0,  # min_roe default
            min_turnover,
            True   # exclude_alerts
        )
        return result
    except Exception as e:
        return f"Error screening stocks: {str(e)}"


def parse_screening_result(result: str) -> List[str]:
    """Parse screening result to extract ticker list."""
    tickers = []
    for line in result.split('\n'):
        if line.strip() and (line.startswith('1.') or line.startswith('2.') or
                             line.startswith('3.') or line.startswith('4.') or
                             line.startswith('5.') or any(line.startswith(f'{i}.') for i in range(6, 100))):
            # Extract ticker from format like "1. 000001.SZ - PE:..."
            parts = line.split(' ')
            if len(parts) >= 2:
                ticker = parts[1].strip()
                if '.' in ticker:  # Valid ticker format
                    tickers.append(ticker)
    return tickers


def parse_batch_tickers(input_text: str) -> List[str]:
    """解析多股票输入文本，自动格式化"""
    tickers = []

    # 支持逗号、空格、换行分隔
    for part in input_text.replace(',', ' ').replace('\n', ' ').split():
        part = part.strip().upper()
        if not part:
            continue

        # 自动补充交易所后缀
        if '.' not in part:
            if part.startswith('6'):
                part += '.SH'
            elif part.startswith('0') or part.startswith('3'):
                part += '.SZ'
            elif part.startswith('8') or part.startswith('4'):
                part += '.BJ'
            elif part.startswith('0') and len(part) == 5:
                part += '.HK'  # 港股 5位代码

        # 验证格式
        if '.' in part:
            tickers.append(part)

    return tickers


def run_batch_analysis(
    ticker_list: List[str],
    analysis_date: str,
    batch_depth: int = 1,
    output_language: str = "Chinese"
) -> List[Dict[str, Any]]:
    """Run batch TradingAgents analysis for multiple stocks."""
    results = []
    total = len(ticker_list)

    for i, ticker in enumerate(ticker_list):
        try:
            # Create config
            config = get_default_config()
            config["max_debate_rounds"] = batch_depth
            config["max_risk_discuss_rounds"] = batch_depth
            config["output_language"] = output_language

            # Initialize graph
            graph = TradingAgentsGraph(
                selected_analysts=["market", "fundamentals"],  # Simplified for batch
                config=config,
                debug=False,
            )

            # Run analysis
            init_state = graph.propagator.create_initial_state(ticker, analysis_date)
            args = graph.propagator.get_graph_args()

            trace = []
            for chunk in graph.graph.stream(init_state, **args):
                trace.append(chunk)

            final_state = trace[-1]
            decision = graph.process_signal(final_state["final_trade_decision"])

            # Extract key points
            result = {
                "ticker": ticker,
                "decision": decision,
                "market_summary": extract_key_points(final_state.get("market_report", "")),
                "fundamentals_summary": extract_key_points(final_state.get("fundamentals_report", "")),
                "bull_view": extract_debate_view(final_state, "bull"),
                "bear_view": extract_debate_view(final_state, "bear"),
                "risk_level": extract_risk_level(final_state),
                "full_state": final_state,
                "error": None
            }
            results.append(result)

        except Exception as e:
            results.append({
                "ticker": ticker,
                "decision": "ERROR",
                "error": str(e),
                "full_state": None
            })

    return results


def extract_key_points(report: str, max_length: int = 200) -> str:
    """Extract key points from analyst report."""
    if not report:
        return "N/A"
    # Take first meaningful sentences
    lines = report.split('\n')
    key_lines = [l for l in lines if l.strip() and not l.startswith('#')][:5]
    summary = ' '.join(key_lines)
    if len(summary) > max_length:
        summary = summary[:max_length] + "..."
    return summary


def extract_debate_view(final_state: Dict[str, Any], side: str) -> str:
    """Extract bull/bear view from debate."""
    if not final_state.get("investment_debate_state"):
        return "N/A"
    debate = final_state["investment_debate_state"]
    key = f"{side}_history"
    if not debate.get(key):
        return "N/A"
    # Extract last statement
    history = debate[key]
    if isinstance(history, list):
        last = history[-1] if history else ""
    else:
        # Split and get last meaningful part
        parts = history.split('\n\n')
        last = parts[-1] if parts else history
    return last[:150] + "..." if len(last) > 150 else last


def extract_risk_level(final_state: Dict[str, Any]) -> str:
    """Extract risk level from risk debate."""
    if not final_state.get("risk_debate_state"):
        return "N/A"
    risk = final_state["risk_debate_state"]
    if risk.get("judge_decision"):
        decision = risk["judge_decision"]
        # Look for risk keywords
        if "high risk" in decision.lower() or "高风险" in decision:
            return "高"
        elif "low risk" in decision.lower() or "低风险" in decision:
            return "低"
        elif "medium" in decision.lower() or "中等" in decision:
            return "中"
    return "中"


def render_batch_results_table(results: List[Dict[str, Any]]):
    """Render batch analysis results comparison table."""
    if not results:
        st.info("No batch analysis results yet.")
        return

    # Create DataFrame for display
    df_data = []
    for r in results:
        df_data.append({
            "Ticker": r["ticker"],
            "Decision": r["decision"],
            "Risk Level": r.get("risk_level", "N/A"),
            "Market Key Points": r.get("market_summary", "N/A"),
            "Fundamentals Key Points": r.get("fundamentals_summary", "N/A"),
            "Bull View": r.get("bull_view", "N/A"),
            "Bear View": r.get("bear_view", "N/A"),
            "Error": r.get("error", ""),
        })

    df = pd.DataFrame(df_data)

    # Color code decisions
    def color_decision(val):
        colors = {
            "BUY": "background-color: #28a745; color: white",
            "OVERWEIGHT": "background-color: #5cb85c; color: white",
            "HOLD": "background-color: #ffc107; color: black",
            "UNDERWEIGHT": "background-color: #fd7e14; color: white",
            "SELL": "background-color: #dc3545; color: white",
            "ERROR": "background-color: #6c757d; color: white",
        }
        return colors.get(val, "")

    styled_df = df.style.applymap(color_decision, subset=["Decision"])

    st.dataframe(styled_df, use_container_width=True)

    # Export options
    col1, col2 = st.columns(2)
    with col1:
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "Export CSV",
            csv,
            "batch_analysis_results.csv",
            "text/csv"
        )
    with col2:
        json_results = json.dumps(results, ensure_ascii=False, indent=2)
        st.download_button(
            "Export JSON",
            json_results,
            "batch_analysis_results.json",
            "application/json"
        )


def render_selected_stocks_list():
    """Render the list of selected stocks for batch analysis."""
    if "selected_tickers" not in st.session_state:
        st.session_state["selected_tickers"] = []

    tickers = st.session_state["selected_tickers"]

    st.subheader("Selected Stocks for Batch Analysis")

    if not tickers:
        st.info("No stocks selected. Add stocks from screening results or manually.")
        return tickers

    # Display list with delete option
    for i, ticker in enumerate(tickers):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.text(ticker)
        with col2:
            if st.button("Remove", key=f"remove_{i}_{ticker}"):
                st.session_state["selected_tickers"].remove(ticker)
                st.rerun()

    st.markdown(f"**Total: {len(tickers)} stocks**")

    return tickers


def handle_followup_question(question: str, results: List[Dict[str, Any]], use_deep: bool = False) -> str:
    """Handle follow-up question about batch analysis results."""
    # Build context from results
    context_lines = []
    for r in results:
        if r.get("error"):
            continue
        context_lines.append(f"- {r['ticker']}: Decision={r['decision']}, Risk={r.get('risk_level', 'N/A')}")
        if r.get("market_summary"):
            context_lines.append(f"  Market: {r['market_summary'][:100]}")
        if r.get("fundamentals_summary"):
            context_lines.append(f"  Fundamentals: {r['fundamentals_summary'][:100]}")

    context = "\n".join(context_lines)

    if not use_deep:
        # Quick LLM answer
        # In production, would call actual LLM
        return f"Based on the analysis results:\n{context}\n\nQuick answer to '{question}': This feature requires LLM integration."
    else:
        # Deep analysis - would trigger agent
        return f"Deep analysis for '{question}' would require running specialized agents. This feature is pending implementation."


def run_screening_mode():
    """Run the stock screening mode main logic."""
    st.markdown("### Stock Screening Mode")

    # Initialize session state for selected tickers
    if "selected_tickers" not in st.session_state:
        st.session_state["selected_tickers"] = []

    if "batch_results" not in st.session_state:
        st.session_state["batch_results"] = []

    if "followup_history" not in st.session_state:
        st.session_state["followup_history"] = []

    # Tabs for screening phases
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Phase 1: Hot Stocks",
        "Phase 2: Screening",
        "Phase 3: Batch Analysis",
        "Quick Compare",
        "Follow-up Questions"
    ])

    # Get user selections
    selections = st.session_state.get("screening_selections", {})

    # Tab 1: Phase 1 - Hot Stocks
    with tab1:
        st.subheader("Hot Stocks Ranking")

        if selections.get("phase1_run"):
            st.info(f"Fetching hot stocks for {selections['analysis_date']}...")
            result = run_phase1_hot_stocks(selections["analysis_date"])
            st.markdown(result)

            # Parse and add to selected list
            hot_tickers = parse_screening_result(result)
            if hot_tickers:
                st.markdown(f"**Found {len(hot_tickers)} hot stocks**")
                # Add to selected with user confirmation
                if st.button("Add All Hot Stocks to Batch List"):
                    for t in hot_tickers[:10]:  # Limit to 10
                        if t not in st.session_state["selected_tickers"]:
                            st.session_state["selected_tickers"].append(t)
                    st.success(f"Added {len(hot_tickers[:10])} stocks to batch list")
                    st.rerun()

        st.markdown("---")
        render_selected_stocks_list()

    # Tab 2: Phase 2 - Screening
    with tab2:
        st.subheader("Quantitative Screening")

        if selections.get("phase2_run"):
            st.info(f"Screening stocks for {selections['analysis_date']}...")
            st.markdown(f"Filters: PE≤{selections['pe_max']}, PB≤{selections['pb_max']}, Turnover≥{selections['min_turnover']}%")

            result = run_phase2_screening(
                selections["analysis_date"],
                selections["pe_max"],
                selections["pb_max"],
                selections["min_turnover"]
            )
            st.markdown(result)

            # Parse results
            screened_tickers = parse_screening_result(result)
            if screened_tickers:
                st.markdown(f"**Found {len(screened_tickers)} screened stocks**")
                if st.button("Add All Screened Stocks to Batch List"):
                    for t in screened_tickers[:10]:  # Limit to 10
                        if t not in st.session_state["selected_tickers"]:
                            st.session_state["selected_tickers"].append(t)
                    st.success(f"Added {len(screened_tickers[:10])} stocks to batch list")
                    st.rerun()

        st.markdown("---")
        render_selected_stocks_list()

    # Tab 3: Phase 3 - Batch Analysis
    with tab3:
        st.subheader("Batch TradingAgents Analysis")

        tickers = render_selected_stocks_list()

        # Handle manual ticker addition
        if selections.get("add_ticker_btn") and selections.get("manual_ticker"):
            ticker = selections["manual_ticker"].strip().upper()
            if '.' not in ticker:
                # Auto-add exchange suffix for Chinese stocks
                if ticker.startswith('6'):
                    ticker += '.SH'
                else:
                    ticker += '.SZ'
            if ticker not in st.session_state["selected_tickers"]:
                st.session_state["selected_tickers"].append(ticker)
                st.success(f"Added {ticker}")
                st.rerun()

        if selections.get("batch_run") and tickers:
            st.info(f"Running batch analysis for {len(tickers)} stocks...")

            progress_bar = st.progress(0)
            status_text = st.empty()

            results = []
            for i, ticker in enumerate(tickers):
                status_text.text(f"Analyzing {ticker} ({i+1}/{len(tickers)})...")
                progress_bar.progress((i+1) / len(tickers))

                try:
                    batch_results = run_batch_analysis(
                        [ticker],
                        selections["analysis_date"],
                        selections.get("batch_depth", 1),
                        selections.get("output_language", "Chinese")
                    )
                    results.extend(batch_results)
                except Exception as e:
                    results.append({
                        "ticker": ticker,
                        "decision": "ERROR",
                        "error": str(e)
                    })

            st.session_state["batch_results"] = results
            progress_bar.progress(1.0)
            status_text.text("Analysis complete!")
            st.success(f"Completed analysis for {len(results)} stocks")

        # Display results
        if st.session_state["batch_results"]:
            render_batch_results_table(st.session_state["batch_results"])

            # Detailed view option
            st.markdown("---")
            st.subheader("Detailed View")
            selected_ticker = st.selectbox(
                "View detailed analysis",
                options=[r["ticker"] for r in st.session_state["batch_results"]]
            )

            if selected_ticker:
                result = next((r for r in st.session_state["batch_results"] if r["ticker"] == selected_ticker), None)
                if result and result.get("full_state"):
                    with st.expander("Full Analysis Report", expanded=True):
                        if result["full_state"].get("market_report"):
                            st.markdown("**Market Report:**")
                            st.markdown(result["full_state"]["market_report"])
                        if result["full_state"].get("fundamentals_report"):
                            st.markdown("**Fundamentals Report:**")
                            st.markdown(result["full_state"]["fundamentals_report"])

    # Tab 4: Quick Compare
    with tab4:
        st.subheader("手动输入股票对比")

        batch_input = selections.get("batch_tickers_input", "")
        tickers = []

        if batch_input:
            tickers = parse_batch_tickers(batch_input)
            st.markdown(f"**解析到 {len(tickers)} 只股票:**")
            for t in tickers:
                st.text(t)

        st.markdown("---")

        if selections.get("quick_compare_btn"):
            if not tickers:
                st.warning("请输入股票代码")
            else:
                st.info(f"正在分析 {len(tickers)} 只股票...")

                progress_bar = st.progress(0)
                status_text = st.empty()

                results = []
                for i, ticker in enumerate(tickers):
                    status_text.text(f"分析 {ticker} ({i+1}/{len(tickers)})...")
                    progress_bar.progress((i+1) / len(tickers))

                    try:
                        batch_results = run_batch_analysis(
                            [ticker],
                            selections["analysis_date"],
                            selections.get("batch_depth", 1),
                            selections.get("output_language", "Chinese")
                        )
                        results.extend(batch_results)
                    except Exception as e:
                        results.append({
                            "ticker": ticker,
                            "decision": "ERROR",
                            "error": str(e)
                        })

                st.session_state["batch_results"] = results
                progress_bar.progress(1.0)
                status_text.text("分析完成!")
                st.success(f"完成 {len(results)} 只股票分析")

                # 显示对比表格
                render_batch_results_table(results)

                # 详细查看
                st.markdown("---")
                st.subheader("详细分析")
                valid_tickers = [r["ticker"] for r in results if r.get("full_state")]
                if valid_tickers:
                    selected_ticker = st.selectbox(
                        "查看详细报告",
                        options=valid_tickers
                    )
                    if selected_ticker:
                        result = next((r for r in results if r["ticker"] == selected_ticker), None)
                        if result and result.get("full_state"):
                            with st.expander("完整报告", expanded=True):
                                if result["full_state"].get("market_report"):
                                    st.markdown("**市场分析:**")
                                    st.markdown(result["full_state"]["market_report"])
                                if result["full_state"].get("fundamentals_report"):
                                    st.markdown("**基本面分析:**")
                                    st.markdown(result["full_state"]["fundamentals_report"])

    # Tab 5: Follow-up Questions
    with tab5:
        st.subheader("Ask About Results")

        # Display conversation history
        if st.session_state["followup_history"]:
            st.markdown("**Conversation History:**")
            for qa in st.session_state["followup_history"]:
                st.markdown(f"**Q:** {qa['question']}")
                st.markdown(f"**A:** {qa['answer']}")
                st.markdown("---")

            if st.button("Clear History"):
                st.session_state["followup_history"] = []
                st.rerun()

        # Handle followup
        if selections.get("followup_btn") and selections.get("followup_question"):
            question = selections["followup_question"]
            results = st.session_state.get("batch_results", [])
            answer = handle_followup_question(question, results, use_deep=False)

            st.session_state["followup_history"].append({
                "question": question,
                "answer": answer,
                "timestamp": datetime.datetime.now().isoformat()
            })
            st.markdown(f"**Answer:** {answer}")

        if selections.get("deep_analysis_btn") and selections.get("followup_question"):
            question = selections["followup_question"]
            results = st.session_state.get("batch_results", [])
            st.info("Running deep analysis (10-30 seconds)...")
            answer = handle_followup_question(question, results, use_deep=True)

            st.session_state["followup_history"].append({
                "question": question,
                "answer": answer,
                "timestamp": datetime.datetime.now().isoformat(),
                "deep": True
            })
            st.markdown(f"**Deep Answer:** {answer}")


def main():
    """Main application entry point."""
    # Header
    st.title("TradingAgents")
    st.markdown("**Multi-Agents LLM Financial Trading Framework**")
    st.markdown("[GitHub](https://github.com/TauricResearch/TradingAgents)")

    st.markdown("---")

    # Get user selections from sidebar
    user_selections = render_sidebar()

    # Handle different modes
    mode = st.session_state.get("analysis_mode", "Single Stock")

    if mode == "Single Stock":
        # Validate selections for single stock mode
        if not user_selections.get("analysts"):
            st.warning("Please select at least one analyst.")
            return

        if not user_selections.get("ticker"):
            st.warning("Please enter a ticker symbol.")
            return

        # Run analysis when button clicked
        if user_selections.get("start"):
            st.session_state["run_analysis"] = True
            st.session_state["user_selections"] = user_selections

        # Check if analysis should run
        if st.session_state.get("run_analysis", False):
            selections = st.session_state["user_selections"]

            try:
                # Run analysis
                final_state, decision, agent_status = run_analysis(selections)

                # Store results in session state
                st.session_state["final_state"] = final_state
                st.session_state["decision"] = decision
                st.session_state["analysis_complete"] = True

            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")
                st.exception(e)
                st.session_state["run_analysis"] = False
                return

            # Reset run flag
            st.session_state["run_analysis"] = False

        # Display results if analysis complete
        if st.session_state.get("analysis_complete", False):
            final_state = st.session_state["final_state"]
            decision = st.session_state["decision"]
            selections = st.session_state["user_selections"]

            st.markdown("---")

            # Tabbed layout for reports
            if QUALITY_EVAL_AVAILABLE:
                tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
                    "Analyst Team",
                    "Research Team",
                    "Trading Team",
                    "Risk Management",
                    "Portfolio Decision",
                    "Quality Evaluation",
                    "Export"
                ])
            else:
                tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                    "Analyst Team",
                    "Research Team",
                    "Trading Team",
                    "Risk Management",
                    "Portfolio Decision",
                    "Export"
                ])

            with tab1:
                render_analyst_reports(final_state, selections["analysts"])

            with tab2:
                render_research_team(final_state)

            with tab3:
                render_trading_team(final_state)

            with tab4:
                render_risk_management(final_state)

            with tab5:
                render_portfolio_decision(final_state)
                render_final_decision(decision)

            if QUALITY_EVAL_AVAILABLE:
                with tab6:
                    render_quality_evaluation(final_state, selections["ticker"])

                with tab7:
                    st.subheader("Export Reports")

                    col1, col2 = st.columns(2)

                    with col1:
                        # Markdown download
                        md_report = generate_markdown_report(final_state, selections["ticker"])
                        st.download_button(
                            label="Download Markdown Report",
                            data=md_report,
                            file_name=f"trading_report_{selections['ticker']}_{selections['analysis_date']}.md",
                            mime="text/markdown",
                        )

                    with col2:
                        # JSON download
                        json_state = generate_json_state(final_state)
                        st.download_button(
                            label="Download JSON State",
                            data=json_state,
                            file_name=f"trading_state_{selections['ticker']}_{selections['analysis_date']}.json",
                            mime="application/json",
                        )

                    st.markdown("---")

                    # Option to start new analysis
                    if st.button("Start New Analysis"):
                        st.session_state["analysis_complete"] = False
                        st.session_state["final_state"] = None
                        st.session_state["decision"] = None
                        st.rerun()
            else:
                with tab6:
                    st.subheader("Export Reports")

                    col1, col2 = st.columns(2)

                    with col1:
                        # Markdown download
                        md_report = generate_markdown_report(final_state, selections["ticker"])
                        st.download_button(
                            label="Download Markdown Report",
                            data=md_report,
                            file_name=f"trading_report_{selections['ticker']}_{selections['analysis_date']}.md",
                            mime="text/markdown",
                        )

                    with col2:
                        # JSON download
                        json_state = generate_json_state(final_state)
                        st.download_button(
                            label="Download JSON State",
                            data=json_state,
                            file_name=f"trading_state_{selections['ticker']}_{selections['analysis_date']}.json",
                            mime="application/json",
                        )

                    st.markdown("---")

                    # Option to start new analysis
                    if st.button("Start New Analysis"):
                        st.session_state["analysis_complete"] = False
                        st.session_state["final_state"] = None
                        st.session_state["decision"] = None
                        st.rerun()

    else:  # Stock Screening Mode
        # Store selections in session state
        st.session_state["screening_selections"] = user_selections

        # Run screening mode
        run_screening_mode()


if __name__ == "__main__":
    main()