#!/usr/bin/env python
"""Streamlit Web Application for TradingAgents Multi-Agent Trading Analysis."""

import streamlit as st
from datetime import datetime, date
import json
import os
import sys

# Add project root to path if needed
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.interface import init_tushare_api

# Page configuration
st.set_page_config(
    page_title="TradingAgents - 多智能体交易分析",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #FF4B4B;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #262730;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1rem;
    }
    .analysis-complete {
        background-color: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def get_llm_presets():
    """Return LLM preset configurations - NO hardcoded keys."""
    return {
        "昆仑 Qwen2.5-14B (大模型)": {
            "api_key": "",  # 用户必须输入自己的 API Key
            "base_url": "https://platform.ai.cnpc/kunlun/ingress/api/h3t-qqwwee/6ede2fb11ceb481e8c51cffcc40d2517/ai-8ae6408193ce464dbed0d877dea4362b/service-3a1f891055d546e999f49db9bfecd541/v1",
            "model": "Qwen2.5-14B-Instruct",
        },
        "昆仑 Qwen2.5-7B (小模型)": {
            "api_key": "",  # 用户必须输入自己的 API Key
            "base_url": "https://platform.ai.cnpc/kunlun/ingress/api/h3t-qqwwee/6ede2fb11ceb481e8c51cffcc40d2517/ai-758eadfb3e4f41b3800a2da724196c25/service-170f88cc65004889bcf2582571c3e476/v1",
            "model": "Qwen2.5-7B-Instruct",
        },
        "自定义配置": {
            "api_key": "",
            "base_url": "",
            "model": "",
        },
    }


def main():
    """Main Streamlit application."""

    # Title
    st.markdown('<p class="main-header">TradingAgents 多智能体交易分析系统</p>', unsafe_allow_html=True)
    st.markdown("---")

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ 配置参数")

        # LLM Configuration
        st.subheader("LLM 配置")
        llm_presets = get_llm_presets()
        llm_choice = st.selectbox("选择模型配置", list(llm_presets.keys()), index=0)

        preset = llm_presets[llm_choice]

        if llm_choice == "自定义配置":
            # 完全自定义配置
            api_key = st.text_input("API Key", type="password",
                                    placeholder="输入您的 API Key")
            base_url = st.text_input("API 端点",
                                     placeholder="如: https://api.openai.com/v1")
            model_name = st.text_input("模型名称",
                                       placeholder="如: gpt-4, deepseek-chat, qwen-plus")
        else:
            # 预设模型配置 - 必须输入 Key
            api_key = st.text_input("API Key", type="password",
                                    placeholder="请输入您的 API Key")

            # 可选：编辑预设参数
            edit_preset = st.checkbox("编辑预设参数", value=False,
                                      help="勾选后可修改 API 端点和模型名称")

            if edit_preset:
                # 用户可修改预设的端点和模型
                base_url = st.text_input("API 端点", value=preset["base_url"])
                model_name = st.text_input("模型名称", value=preset["model"])
            else:
                # 使用预设默认值
                base_url = preset["base_url"]
                model_name = preset["model"]
                st.info(f"已选择: {preset['model']}")

        # Proxy configuration (optional)
        st.subheader("网络配置")
        use_proxy = st.checkbox("使用代理", value=False)
        proxy_url = st.text_input("代理地址", value="http://10.22.98.21:8080", disabled=not use_proxy)
        verify_ssl = st.checkbox("验证 SSL", value=True)

        # Data Source Configuration
        st.subheader("数据源配置")
        data_source = st.radio("数据源", ["yfinance (免费)", "Tushare (需Token)"], index=0)

        if "Tushare" in data_source:
            tushare_token = st.text_input("Tushare Token", type="password",
                                          placeholder="输入您的 Tushare Token")
        else:
            tushare_token = None

        # Analysis Parameters
        st.subheader("分析参数")
        max_debate = st.slider("最大辩论轮数", 1, 5, 1,
                              help="辩论轮数越多，分析越深入，但耗时更长")
        max_risk_discuss = st.slider("风险评估轮数", 1, 3, 1,
                                    help="风险团队讨论轮数")

        # Analyst selection
        st.subheader("分析师选择")
        available_analysts = ["market", "social", "news", "fundamentals"]
        selected_analysts = st.multiselect(
            "选择分析师类型",
            available_analysts,
            default=available_analysts,
            help="选择参与分析的分析师类型"
        )

        # Output language
        output_language = st.selectbox("输出语言", ["中文", "English"], index=0)

        # Debug mode
        st.subheader("调试选项")
        debug_mode = st.checkbox("调试模式", value=False,
                                help="开启后可查看完整的 Agent 交互过程")

    # Main interface
    st.subheader("股票信息")

    col1, col2 = st.columns(2)
    with col1:
        ticker = st.text_input("股票代码", placeholder="如: 600519, 00700.HK, AAPL, NVDA",
                              help="支持 A 股、港股、美股代码")
    with col2:
        default_date = date.today()
        trade_date = st.date_input("交易日期", value=default_date)

    # Stock code examples
    st.markdown("""
    **支持的股票代码格式:**
    - A 股上海: `600519` (贵州茅台) → 自动转换为 `600519.SS`
    - A 股深圳: `000001` (平安银行) → 自动转换为 `000001.SZ`
    - 港股: `00700` (腾讯控股) → 自动转换为 `00700.HK`
    - 美股: `AAPL`, `NVDA`, `MSFT` 等
    """)

    # Run button
    st.markdown("---")

    if st.button("🚀 开始分析", type="primary", use_container_width=True):
        if not ticker:
            st.error("请输入股票代码!")
        elif not selected_analysts:
            st.error("请至少选择一个分析师类型!")
        elif not api_key:
            st.error("请输入 API Key!")
        elif "Tushare" in data_source and not tushare_token:
            st.error("请输入 Tushare Token!")
        else:
            run_analysis(
                ticker=ticker,
                trade_date=str(trade_date),
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                data_source=data_source,
                tushare_token=tushare_token,
                max_debate=max_debate,
                max_risk_discuss=max_risk_discuss,
                selected_analysts=selected_analysts,
                output_language=output_language,
                debug_mode=debug_mode,
                use_proxy=use_proxy,
                proxy_url=proxy_url,
                verify_ssl=verify_ssl,
            )


def run_analysis(
    ticker: str,
    trade_date: str,
    api_key: str,
    base_url: str,
    model_name: str,
    data_source: str,
    tushare_token: str,
    max_debate: int,
    max_risk_discuss: int,
    selected_analysts: list,
    output_language: str,
    debug_mode: bool,
    use_proxy: bool,
    proxy_url: str,
    verify_ssl: bool,
):
    """Run the TradingAgents analysis with the given configuration."""

    # Create progress display
    progress_bar = st.progress(0, text="正在初始化...")
    status_text = st.empty()

    try:
        # Step 1: Initialize data source
        status_text.text("初始化数据源...")
        progress_bar.progress(10, text="初始化数据源...")

        if "Tushare" in data_source and tushare_token:
            init_tushare_api(tushare_token)
            data_vendor = "tushare"
        else:
            data_vendor = "yfinance"

        # Step 2: Configure TradingAgents
        status_text.text("配置 TradingAgents...")
        progress_bar.progress(20, text="配置 TradingAgents...")

        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = "openai"
        config["deep_think_llm"] = model_name
        config["quick_think_llm"] = model_name
        config["backend_url"] = base_url
        config["llm_api_key"] = api_key
        config["max_debate_rounds"] = max_debate
        config["max_risk_discuss_rounds"] = max_risk_discuss
        config["output_language"] = output_language

        # Network configuration
        if use_proxy:
            config["llm_proxy"] = proxy_url
        config["llm_verify"] = verify_ssl

        # Data vendor configuration
        config["data_vendors"] = {
            "core_stock_apis": data_vendor,
            "technical_indicators": data_vendor,
            "fundamental_data": data_vendor,
            "news_data": data_vendor,
        }

        # Step 3: Initialize graph
        status_text.text("初始化多智能体图...")
        progress_bar.progress(30, text="初始化多智能体图...")

        ta = TradingAgentsGraph(
            selected_analysts=selected_analysts,
            debug=debug_mode,
            config=config,
        )

        # Step 4: Run analysis
        status_text.text(f"正在分析股票 {ticker}...")
        progress_bar.progress(50, text="正在进行多智能体分析...")

        final_state, decision = ta.propagate(ticker, trade_date)

        progress_bar.progress(100, text="分析完成!")
        status_text.empty()

        # Display results
        display_results(final_state, decision, ticker, trade_date)

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"分析过程中出现错误: {str(e)}")
        st.exception(e)


def display_results(final_state: dict, decision: str, ticker: str, trade_date: str):
    """Display the analysis results in a structured format."""

    # Success message with decision
    st.markdown(f"""
    <div class="analysis-complete">
        <h3>分析完成!</h3>
        <p><strong>股票:</strong> {ticker}</p>
        <p><strong>日期:</strong> {trade_date}</p>
        <p><strong>最终决策:</strong> {decision}</p>
    </div>
    """, unsafe_allow_html=True)

    # Tabs for detailed reports
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "市场分析", "新闻分析", "基本面分析", "多空辩论", "风险评估", "完整报告"
    ])

    with tab1:
        st.subheader("市场分析师报告")
        if final_state.get("market_report"):
            st.markdown(final_state["market_report"])
        else:
            st.info("市场分析报告未生成")

    with tab2:
        st.subheader("新闻分析师报告")
        if final_state.get("news_report"):
            st.markdown(final_state["news_report"])
        else:
            st.info("新闻分析报告未生成")

    with tab3:
        st.subheader("基本面分析师报告")
        if final_state.get("fundamentals_report"):
            st.markdown(final_state["fundamentals_report"])
        else:
            st.info("基本面分析报告未生成")

    with tab4:
        st.subheader("多空辩论历史")
        debate_state = final_state.get("investment_debate_state", {})

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 看多观点")
            if debate_state.get("bull_history"):
                st.markdown(debate_state["bull_history"])
            else:
                st.info("无看多辩论记录")

        with col2:
            st.markdown("### 看空观点")
            if debate_state.get("bear_history"):
                st.markdown(debate_state["bear_history"])
            else:
                st.info("无看空辩论记录")

        st.markdown("---")
        st.subheader("辩论完整记录")
        if debate_state.get("history"):
            st.markdown(debate_state["history"])

        st.subheader("投资法官决策")
        if debate_state.get("judge_decision"):
            st.markdown(debate_state["judge_decision"])

    with tab5:
        st.subheader("风险评估讨论")
        risk_state = final_state.get("risk_debate_state", {})

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("### 激进观点")
            if risk_state.get("aggressive_history"):
                st.markdown(risk_state["aggressive_history"])

        with col2:
            st.markdown("### 保守观点")
            if risk_state.get("conservative_history"):
                st.markdown(risk_state["conservative_history"])

        with col3:
            st.markdown("### 中性观点")
            if risk_state.get("neutral_history"):
                st.markdown(risk_state["neutral_history"])

        st.markdown("---")
        st.subheader("风险法官决策")
        if risk_state.get("judge_decision"):
            st.markdown(risk_state["judge_decision"])

    with tab6:
        st.subheader("完整分析报告 (JSON)")

        # Prepare clean state for display
        display_state = {
            "company_of_interest": final_state.get("company_of_interest"),
            "trade_date": final_state.get("trade_date"),
            "market_report": final_state.get("market_report"),
            "sentiment_report": final_state.get("sentiment_report"),
            "news_report": final_state.get("news_report"),
            "fundamentals_report": final_state.get("fundamentals_report"),
            "investment_debate_state": final_state.get("investment_debate_state", {}),
            "trader_investment_decision": final_state.get("trader_investment_plan"),
            "risk_debate_state": final_state.get("risk_debate_state", {}),
            "investment_plan": final_state.get("investment_plan"),
            "final_trade_decision": final_state.get("final_trade_decision"),
        }

        st.json(display_state)

        # Download button
        st.download_button(
            label="下载完整报告 (JSON)",
            data=json.dumps(display_state, indent=2, ensure_ascii=False),
            file_name=f"trading_report_{ticker}_{trade_date}.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()