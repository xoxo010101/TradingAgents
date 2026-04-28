#!/usr/bin/env python
"""报告质量评估工具

评估 TradingAgents 生成的单只股票分析报告质量。
评估维度包括：完整性、逻辑性、数据支撑、辩论质量、决策一致性等。

用法:
    python scripts/report_quality_evaluator.py <report_json_path>
    python scripts/report_quality_evaluator.py <report_json_path> --verbose
"""

import json
import re
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field


@dataclass
class CheckResult:
    """单个检查项的结果"""
    passed: bool
    score: int  # 0-100
    detail: str
    issues: List[str] = field(default_factory=list)


class ReportQualityEvaluator:
    """评估单只股票分析报告的质量"""

    # 评估维度权重
    WEIGHTS = {
        "completeness": 0.30,
        "data_evidence": 0.25,
        "debate_quality": 0.20,
        "consistency": 0.15,
        "structure": 0.10,
    }

    # 技术指标关键词
    TECH_INDICATORS = [
        "SMA", "EMA", "MACD", "RSI", "BOLL", "ATR", "VWMA", "MA",
        "KDJ", "OBV", "WR", "CCI", "移动平均", "均线", "布林带",
        "相对强弱", "成交量", "振幅", "波动率"
    ]

    # 基本面指标关键词
    FUNDAMENTAL_TERMS = [
        "PE", "市盈率", "PB", "市净率", "ROE", "净资产收益率",
        "营收", "收入", "利润", "净利润", "EPS", "每股收益",
        "毛利率", "净利率", "ROA", "总资产收益率", "现金流",
        "负债", "资产", "市值", "估值", "分红", "股息"
    ]

    # 5-tier 评级
    RATINGS = ["Buy", "Overweight", "Hold", "Underweight", "Sell",
               "买入", "增持", "持有", "减持", "卖出"]

    # 时间关键词
    TIME_KEYWORDS = [
        "近期", "最近", "本周", "本月", "昨日", "今日", "今天",
        "昨天", "上周", "上月", "年初", "年末", "季度",
        "2024", "2025", "2026",  # 年份
    ]

    # 价格相关关键词
    PRICE_KEYWORDS = [
        "价格", "价位", "成本", "支撑", "阻力", "突破",
        "回调", "反弹", "涨", "跌", "涨幅", "跌幅",
        "高点", "低点", "新高", "新低", "开盘", "收盘",
    ]

    def __init__(self, report_path: str):
        """初始化评估器

        Args:
            report_path: 报告 JSON 文件路径
        """
        self.report_path = Path(report_path)
        self.report = self._load_report()
        self.scores: Dict[str, CheckResult] = {}
        self.all_issues: List[str] = []

    def _load_report(self) -> Dict[str, Any]:
        """加载报告 JSON 文件"""
        try:
            with open(self.report_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"无法解析 JSON 文件: {e}")
        except FileNotFoundError:
            raise FileNotFoundError(f"报告文件不存在: {self.report_path}")

    def evaluate(self) -> Dict[str, Any]:
        """执行完整评估"""
        self.scores["completeness"] = self._check_completeness()
        self.scores["data_evidence"] = self._check_data_evidence()
        self.scores["debate_quality"] = self._check_debate_quality()
        self.scores["consistency"] = self._check_consistency()
        self.scores["structure"] = self._check_structure()

        # 计算总分
        total = sum(v.score * self.WEIGHTS[k] for k, v in self.scores.items())
        grade = self._get_grade(total)

        # 收集所有问题
        for result in self.scores.values():
            self.all_issues.extend(result.issues)

        return {
            "ticker": self.report.get("company_of_interest", "N/A"),
            "date": self.report.get("trade_date", "N/A"),
            "scores": {k: v.score for k, v in self.scores.items()},
            "score_details": {k: {"passed": v.passed, "detail": v.detail, "issues": v.issues}
                             for k, v in self.scores.items()},
            "total_score": round(total, 1),
            "grade": grade,
            "issues": self.all_issues,
        }

    def _check_completeness(self) -> CheckResult:
        """检查报告完整性"""
        issues = []
        passed_count = 0
        total_checks = 7

        # 检查各报告是否存在且长度足够
        min_length = 200

        checks = [
            ("market_report", "市场分析报告"),
            ("news_report", "新闻分析报告"),
            ("fundamentals_report", "基本面分析报告"),
            ("sentiment_report", "情绪分析报告"),
        ]

        for key, name in checks:
            content = self.report.get(key, "")
            if content and len(content) > min_length:
                passed_count += 1
            elif content and len(content) < min_length:
                issues.append(f"{name}内容过短 (仅 {len(content)} 字符)")
            else:
                issues.append(f"{name}缺失")

        # 检查辩论记录
        debate = self.report.get("investment_debate_state", {})
        if debate.get("bull_history"):
            passed_count += 1
        else:
            issues.append("多头辩论记录缺失")

        if debate.get("bear_history"):
            passed_count += 1
        else:
            issues.append("空头辩论记录缺失")

        # 检查最终决策
        decision = self.report.get("final_trade_decision", "")
        if decision and any(r.lower() in decision.lower() for r in self.RATINGS):
            passed_count += 1
        else:
            issues.append("最终决策缺失或不包含有效评级")

        score = int(passed_count / total_checks * 100)
        passed = score >= 70

        detail = f"完整性检查: {passed_count}/{total_checks} 项通过"
        if issues:
            detail += f"\n  - 未通过项: {len(issues)}"

        return CheckResult(passed=passed, score=score, detail=detail, issues=issues)

    def _check_data_evidence(self) -> CheckResult:
        """检查数据支撑度"""
        issues = []
        passed_checks = []
        total_checks = 5
        passed_count = 0

        # 1. 技术指标引用
        market = self.report.get("market_report", "")
        tech_found = [ind for ind in self.TECH_INDICATORS
                     if ind.lower() in market.lower()]
        if len(tech_found) >= 2:
            passed_count += 1
            passed_checks.append(f"技术指标: {', '.join(tech_found[:3])}")
        elif len(tech_found) == 1:
            passed_count += 0.5
            issues.append(f"技术指标引用较少，仅找到: {tech_found[0]}")
        else:
            issues.append("技术分析报告缺少技术指标引用")

        # 2. 价格数据引用
        price_found = any(kw in market for kw in self.PRICE_KEYWORDS)
        # 检查是否有具体数字
        numbers = re.findall(r'\d+\.?\d*', market)
        if price_found and len(numbers) >= 3:
            passed_count += 1
            passed_checks.append("包含价格数据和具体数值")
        elif price_found:
            passed_count += 0.5
            issues.append("价格数据引用缺少具体数值")
        else:
            issues.append("缺少价格数据引用")

        # 3. 基本面数据
        fundamentals = self.report.get("fundamentals_report", "")
        fund_found = [term for term in self.FUNDAMENTAL_TERMS
                     if term in fundamentals]
        if len(fund_found) >= 3:
            passed_count += 1
            passed_checks.append(f"基本面数据: {', '.join(fund_found[:4])}")
        elif len(fund_found) >= 1:
            passed_count += 0.5
            issues.append(f"基本面数据引用不足，建议补充 ROE、PE 等关键指标")
        else:
            issues.append("基本面报告缺少关键财务指标引用")

        # 4. 新闻时效性
        news = self.report.get("news_report", "")
        time_found = [kw for kw in self.TIME_KEYWORDS if kw in news]
        if time_found:
            passed_count += 1
            passed_checks.append(f"新闻时效性关键词: {', '.join(time_found[:3])}")
        else:
            issues.append("新闻报告缺少时效性标识")

        # 5. 数据来源多样性
        debate = self.report.get("investment_debate_state", {})
        bull = debate.get("bull_history", "")
        bear = debate.get("bear_history", "")
        # 检查辩论中是否引用了数据
        debate_has_data = (len(re.findall(r'\d+\.?\d*', bull)) >= 2 or
                          len(re.findall(r'\d+\.?\d%', bear)) >= 2)
        if debate_has_data:
            passed_count += 1
            passed_checks.append("辩论中引用了具体数据")
        else:
            issues.append("辩论论点缺少数据支撑")

        score = int(passed_count / total_checks * 100)
        passed = score >= 60

        detail = f"数据支撑度: {passed_count}/{total_checks} 项通过"
        if passed_checks:
            detail += "\n  ✓ " + "\n  ✓ ".join(passed_checks)
        if issues:
            detail += "\n  ⚠ " + "\n  ⚠ ".join(issues)

        return CheckResult(passed=passed, score=score, detail=detail, issues=issues)

    def _check_debate_quality(self) -> CheckResult:
        """检查辩论质量"""
        issues = []
        passed_checks = []
        total_checks = 5
        passed_count = 0

        debate = self.report.get("investment_debate_state", {})
        risk_debate = self.report.get("risk_debate_state", {})

        # 1. 辩论轮数 (history 字段包含完整辩论记录)
        history = debate.get("history", "")
        # 计算对话轮数（通过分隔符或特定标记）
        rounds = len(history.split("\n\n")) if history else 0
        if rounds >= 3:
            passed_count += 1
            passed_checks.append(f"辩论轮数: {rounds} 轮 (≥3)")
        elif rounds >= 1:
            passed_count += 0.5
            issues.append(f"辩论轮数较少 ({rounds} 轮)，建议增加观点交锋")
        else:
            issues.append("缺少辩论记录")

        # 2. 多空观点都有实质内容
        bull = debate.get("bull_history", "")
        bear = debate.get("bear_history", "")
        bull_len = len(bull) if bull else 0
        bear_len = len(bear) if bear else 0

        if bull_len > 300 and bear_len > 300:
            passed_count += 1
            passed_checks.append(f"多头观点: {bull_len} 字符, 空头观点: {bear_len} 字符")
        elif bull_len > 100 or bear_len > 100:
            passed_count += 0.5
            issues.append("多空辩论内容不够充实")
        else:
            issues.append("多空观点缺失或内容过短")

        # 3. 判决明确性
        judge = debate.get("judge_decision", "")
        if judge and len(judge) > 100:
            # 检查是否有明确的推荐理由
            has_reasoning = any(kw in judge for kw in
                               ["理由", "基于", "考虑", "综合", "建议", "推荐",
                                "recommend", "rationale", "reason"])
            if has_reasoning:
                passed_count += 1
                passed_checks.append("Research Manager 决策包含明确理由")
            else:
                passed_count += 0.5
                issues.append("判决缺少明确的推荐理由说明")
        else:
            issues.append("Research Manager 决策缺失或过短")

        # 4. 风险辩论三方观点
        aggressive = risk_debate.get("aggressive_history", "")
        conservative = risk_debate.get("conservative_history", "")
        neutral = risk_debate.get("neutral_history", "")

        risk_views_count = sum([
            len(aggressive) > 50,
            len(conservative) > 50,
            len(neutral) > 50,
        ])

        if risk_views_count == 3:
            passed_count += 1
            passed_checks.append("风险辩论三方观点完整")
        elif risk_views_count >= 1:
            passed_count += 0.5 * risk_views_count / 3
            missing = []
            if not aggressive: missing.append("激进")
            if not conservative: missing.append("保守")
            if not neutral: missing.append("中性")
            issues.append(f"风险辩论缺少: {', '.join(missing)} 视角")
        else:
            issues.append("风险辩论记录缺失")

        # 5. Portfolio Manager 决策
        pm_decision = risk_debate.get("judge_decision", "")
        if pm_decision and len(pm_decision) > 150:
            passed_count += 1
            passed_checks.append("Portfolio Manager 决策详细")
        elif pm_decision:
            passed_count += 0.5
            issues.append("Portfolio Manager 决策内容较简略")
        else:
            issues.append("Portfolio Manager 决策缺失")

        score = int(passed_count / total_checks * 100)
        passed = score >= 60

        detail = f"辩论质量: {passed_count}/{total_checks} 项通过"
        if passed_checks:
            detail += "\n  ✓ " + "\n  ✓ ".join(passed_checks)
        if issues:
            detail += "\n  ⚠ " + "\n  ⚠ ".join(issues)

        return CheckResult(passed=passed, score=score, detail=detail, issues=issues)

    def _check_consistency(self) -> CheckResult:
        """检查决策一致性"""
        issues = []
        passed_checks = []
        total_checks = 4
        passed_count = 0

        # 1. Rating 合规性
        decision = self.report.get("final_trade_decision", "")
        rating_found = None
        for rating in self.RATINGS:
            if rating.lower() in decision.lower():
                rating_found = rating
                break

        if rating_found:
            passed_count += 1
            passed_checks.append(f"Rating 合规: {rating_found}")
        else:
            issues.append("最终决策缺少有效的 5-tier 评级关键词")

        # 2. 投资计划 → Trader提案 → 最终决策 方向一致性
        investment_plan = self.report.get("investment_plan", "")
        trader_plan = self.report.get("trader_investment_decision",
                                       self.report.get("trader_investment_plan", ""))
        risk_judge = self.report.get("risk_debate_state", {}).get("judge_decision", "")

        # 提取各阶段的倾向
        def extract_bias(text: str) -> str:
            if not text:
                return "unknown"
            text_lower = text.lower()
            if any(kw in text_lower for kw in ["buy", "买入", "overweight", "增持", "看多", "bullish"]):
                return "bullish"
            elif any(kw in text_lower for kw in ["sell", "卖出", "underweight", "减持", "看空", "bearish"]):
                return "bearish"
            elif any(kw in text_lower for kw in ["hold", "持有", "中性", "neutral"]):
                return "neutral"
            return "unknown"

        plan_bias = extract_bias(investment_plan)
        trader_bias = extract_bias(trader_plan)
        final_bias = extract_bias(decision)

        biases = [plan_bias, trader_bias, final_bias]
        valid_biases = [b for b in biases if b != "unknown"]

        if len(set(valid_biases)) <= 1 and len(valid_biases) >= 2:
            passed_count += 1
            passed_checks.append(f"决策方向一致: {plan_bias} → {trader_bias} → {final_bias}")
        elif len(set(valid_biases)) == 2:
            passed_count += 0.5
            issues.append(f"决策方向存在轻微偏差: {plan_bias} → {trader_bias} → {final_bias}")
        else:
            issues.append(f"决策链方向不一致，请检查逻辑连贯性")

        # 3. 风险考量
        risk_keywords = ["止损", "stop", "仓位", "position", "风险", "risk",
                        "波动", "volatility", "警告", "warning", "警惕"]
        has_risk = any(kw in decision.lower() for kw in risk_keywords)
        if has_risk:
            passed_count += 1
            passed_checks.append("包含风险考量关键词")
        else:
            issues.append("最终决策缺少风险考量或止损建议")

        # 4. 投资论据支撑决策
        # 检查最终决策是否引用了分析师的观点
        debate = self.report.get("investment_debate_state", {})
        bull_points = debate.get("bull_history", "")
        bear_points = debate.get("bear_history", "")

        # 检查决策是否提及了关键论据
        decision_mentions_evidence = (
            any(word in decision for word in ["技术", "基本面", "新闻", "分析", "指标"]) or
            any(word in decision for word in ["technical", "fundamental", "analysis", "indicator"])
        )

        if decision_mentions_evidence:
            passed_count += 1
            passed_checks.append("决策引用了分析依据")
        else:
            issues.append("决策缺少对分析师观点的具体引用")

        score = int(passed_count / total_checks * 100)
        passed = score >= 60

        detail = f"决策一致性: {passed_count}/{total_checks} 项通过"
        if passed_checks:
            detail += "\n  ✓ " + "\n  ✓ ".join(passed_checks)
        if issues:
            detail += "\n  ⚠ " + "\n  ⚠ ".join(issues)

        return CheckResult(passed=passed, score=score, detail=detail, issues=issues)

    def _check_structure(self) -> CheckResult:
        """检查结构化输出"""
        issues = []
        passed_checks = []
        total_checks = 4
        passed_count = 0

        decision = self.report.get("final_trade_decision", "")

        # 1. Markdown 表格结构
        has_table = "|" in decision and "---" in decision
        if has_table:
            passed_count += 1
            passed_checks.append("包含 Markdown 表格结构")
        else:
            # 不强制要求表格，但建议有
            passed_count += 0.5

        # 2. 关键字段格式
        key_fields = ["Rating", "Executive Summary", "Investment Thesis",
                      "评级", "摘要", "投资逻辑", "建议"]
        fields_found = [f for f in key_fields if f.lower() in decision.lower()]
        if len(fields_found) >= 3:
            passed_count += 1
            passed_checks.append(f"关键字段: {', '.join(fields_found[:3])}")
        elif len(fields_found) >= 1:
            passed_count += 0.5
            issues.append("建议增加更多关键字段格式")
        else:
            issues.append("缺少标准化的关键字段格式")

        # 3. JSON 可解析性 (已在加载时验证)
        passed_count += 1
        passed_checks.append("JSON 文件可正常解析")

        # 4. 格式一致性 (检查是否使用了 markdown 加粗)
        has_bold = "**" in decision
        if has_bold:
            passed_count += 1
            passed_checks.append("使用了 Markdown 格式化")
        else:
            issues.append("建议使用 Markdown 格式化增强可读性")

        score = int(passed_count / total_checks * 100)
        passed = score >= 75

        detail = f"结构化输出: {passed_count}/{total_checks} 项通过"
        if passed_checks:
            detail += "\n  ✓ " + "\n  ✓ ".join(passed_checks)
        if issues:
            detail += "\n  ⚠ " + "\n  ⚠ ".join(issues)

        return CheckResult(passed=passed, score=score, detail=detail, issues=issues)

    def _get_grade(self, score: float) -> str:
        """根据得分返回等级"""
        if score >= 90:
            return "A (优秀)"
        elif score >= 75:
            return "B (良好)"
        elif score >= 60:
            return "C (合格)"
        elif score >= 40:
            return "D (需改进)"
        else:
            return "E (不合格)"

    def print_report(self, verbose: bool = False):
        """打印评估报告"""
        result = self.evaluate()

        print("=" * 50)
        print(f"报告质量评估 - {result['ticker']} ({result['date']})")
        print("=" * 50)
        print()

        print("【各维度得分】")
        for dim, score in result["scores"].items():
            dim_names = {
                "completeness": "完整性检查",
                "data_evidence": "数据支撑度",
                "debate_quality": "辩论质量",
                "consistency": "决策一致性",
                "structure": "结构化输出",
            }
            status = "✓" if score >= 70 else "⚠" if score >= 50 else "✗"
            print(f"{dim_names[dim]}: {score}/100 {status}")

            if verbose:
                detail = result["score_details"][dim]["detail"]
                for line in detail.split("\n"):
                    print(f"  {line}")

        print()
        print(f"【总分】 {result['total_score']}/100 → {result['grade']}")

        if result["issues"]:
            print()
            print("【问题诊断】")
            for i, issue in enumerate(result["issues"], 1):
                print(f"{i}. {issue}")

        print()
        print("=" * 50)


def evaluate_report(report_path: str, verbose: bool = False) -> Dict[str, Any]:
    """评估单个报告并返回结果字典

    Args:
        report_path: 报告 JSON 文件路径
        verbose: 是否输出详细信息

    Returns:
        评估结果字典
    """
    evaluator = ReportQualityEvaluator(report_path)
    if verbose:
        evaluator.print_report(verbose=True)
    else:
        evaluator.print_report()
    return evaluator.evaluate()


def batch_evaluate(directory: str, verbose: bool = False) -> List[Dict[str, Any]]:
    """批量评估目录下的所有报告

    Args:
        directory: 包含报告 JSON 文件的目录
        verbose: 是否输出详细信息

    Returns:
        所有报告的评估结果列表
    """
    results = []
    dir_path = Path(directory)

    # 递归查找所有 JSON 文件
    json_files = list(dir_path.glob("**/*_logs/*.json"))

    if not json_files:
        print(f"目录 {directory} 下未找到报告文件")
        return results

    print(f"找到 {len(json_files)} 个报告文件")
    print("=" * 50)

    for json_file in json_files:
        try:
            evaluator = ReportQualityEvaluator(str(json_file))
            result = evaluator.evaluate()
            results.append(result)

            status = "✓" if result["total_score"] >= 70 else "⚠"
            print(f"{json_file.name}: {result['total_score']}/100 {status} → {result['grade']}")

            if verbose and result["issues"]:
                for issue in result["issues"]:
                    print(f"  - {issue}")

        except Exception as e:
            print(f"{json_file.name}: 评估失败 - {str(e)}")

    print("=" * 50)

    # 统计总体情况
    if results:
        avg_score = sum(r["total_score"] for r in results) / len(results)
        grade_dist = {}
        for r in results:
            grade = r["grade"].split()[0]
            grade_dist[grade] = grade_dist.get(grade, 0) + 1

        print(f"\n【批量评估统计】")
        print(f"平均得分: {avg_score:.1f}/100")
        print(f"等级分布: {grade_dist}")

    return results


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="评估 TradingAgents 生成的股票分析报告质量"
    )
    parser.add_argument(
        "path",
        help="报告 JSON 文件路径，或包含报告的目录路径"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="输出详细的检查细节"
    )
    parser.add_argument(
        "-b", "--batch",
        action="store_true",
        help="批量评估目录下的所有报告"
    )

    args = parser.parse_args()

    path = Path(args.path)

    if args.batch or path.is_dir():
        batch_evaluate(args.path, args.verbose)
    else:
        evaluate_report(args.path, args.verbose)


if __name__ == "__main__":
    main()