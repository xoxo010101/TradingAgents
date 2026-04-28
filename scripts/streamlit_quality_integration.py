"""Streamlit 集成模块 - 报告质量评估

将报告质量评估集成到 Streamlit web 应用中。
"""

import streamlit as st
import json
from pathlib import Path
from typing import Dict, Any

from .report_quality_evaluator import ReportQualityEvaluator


def render_quality_evaluation(final_state: Dict[str, Any], ticker: str):
    """在 Streamlit 中渲染质量评估结果

    Args:
        final_state: 分析报告的完整状态
        ticker: 股票代码
    """
    st.subheader("报告质量评估")

    # 创建临时 JSON 文件进行评估
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False,
                                     encoding='utf-8') as f:
        json.dump(final_state, f, ensure_ascii=False, indent=2)
        temp_path = f.name

    try:
        # 执行评估
        evaluator = ReportQualityEvaluator(temp_path)
        result = evaluator.evaluate()

        # 显示总分和等级
        col1, col2 = st.columns(2)

        with col1:
            # 得分显示
            score = result["total_score"]
            grade = result["grade"]

            # 根据等级设置颜色
            grade_colors = {
                "A": "#28a745",  # 绿色
                "B": "#5cb85c",
                "C": "#ffc107",  # 黄色
                "D": "#fd7e14",
                "E": "#dc3545",  # 红色
            }
            grade_letter = grade.split()[0]
            color = grade_colors.get(grade_letter, "#6c757d")

            st.markdown(
                f"""
                <div style="padding: 20px; border-radius: 10px;
                            background: {color}; color: white; text-align: center;">
                    <h1 style="color: white; margin: 0;">{score}</h1>
                    <p style="margin: 5px 0 0 0;">总分 / 100</p>
                    <h3 style="color: white; margin: 10px 0 0 0;">{grade}</h3>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:
            # 各维度得分
            st.markdown("**各维度得分:**")

            dim_names = {
                "completeness": "完整性检查",
                "data_evidence": "数据支撑度",
                "debate_quality": "辩论质量",
                "consistency": "决策一致性",
                "structure": "结构化输出",
            }

            for dim, score_val in result["scores"].items():
                status_icon = "✓" if score_val >= 70 else "⚠" if score_val >= 50 else "✗"
                st.markdown(f"- {dim_names[dim]}: **{score_val}**/100 {status_icon}")

        st.markdown("---")

        # 详细检查结果 (可展开)
        with st.expander("查看详细检查结果", expanded=False):
            for dim, details in result["score_details"].items():
                st.markdown(f"**{dim_names[dim]}:**")
                for line in details["detail"].split("\n"):
                    if line.strip():
                        st.markdown(f"  {line}")
                st.markdown()

        # 问题诊断
        if result["issues"]:
            st.markdown("---")
            st.markdown("**问题诊断:**")

            for i, issue in enumerate(result["issues"], 1):
                # 根据问题严重程度显示
                st.warning(f"{i}. {issue}")

        # 改进建议
        st.markdown("---")
        st.markdown("**改进建议:**")

        suggestions = generate_suggestions(result)
        for suggestion in suggestions:
            st.info(suggestion)

        # 导出评估结果
        st.markdown("---")
        st.download_button(
            label="下载质量评估报告 (JSON)",
            data=json.dumps(result, ensure_ascii=False, indent=2),
            file_name=f"quality_eval_{ticker}_{result['date']}.json",
            mime="application/json"
        )

    finally:
        # 清理临时文件
        Path(temp_path).unlink(missing_ok=True)


def generate_suggestions(result: Dict[str, Any]) -> list:
    """根据评估结果生成改进建议"""
    suggestions = []

    scores = result["scores"]

    if scores["completeness"] < 70:
        suggestions.append("完整性: 建议确保所有分析师报告都生成完整内容，辩论记录完整保存。")

    if scores["data_evidence"] < 70:
        suggestions.append("数据支撑: 建议增加具体技术指标数值 (如 SMA、MACD、RSI) 和基本面财务数据。")

    if scores["debate_quality"] < 70:
        suggestions.append("辩论质量: 建议增加辩论轮数，确保多空观点充分交锋，判决理由清晰。")

    if scores["consistency"] < 70:
        suggestions.append("决策一致性: 建议确保投资计划、Trader提案、最终决策方向一致，明确引用分析依据。")

    if scores["structure"] < 70:
        suggestions.append("结构化输出: 建议使用标准 Markdown 格式，包含 Rating、Executive Summary 等关键字段。")

    if not suggestions:
        suggestions.append("报告质量优秀，建议继续保持当前的分析深度和格式规范。")

    return suggestions


def add_quality_tab_to_display():
    """添加质量评估标签页的辅助函数

    在 web_app.py 的 display results 部分调用此函数，
    可以将质量评估添加为新的标签页。
    """
    st.markdown("""
    ### 使用说明

    要在 web_app.py 中集成质量评估，请在显示结果的标签页部分添加:

    ```python
    from scripts.streamlit_quality_integration import render_quality_evaluation

    # 在 tabs 定义中添加:
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Analyst Team",
        "Research Team",
        "Trading Team",
        "Risk Management",
        "Portfolio Decision",
        "Quality Evaluation",  # 新增
        "Export"
    ])

    # 在 tab6 中:
    with tab6:
        render_quality_evaluation(final_state, selections["ticker"])
    ```
    """)


if __name__ == "__main__":
    # 测试导入
    print("Streamlit integration module loaded successfully.")
    add_quality_tab_to_display()