#!/usr/bin/env python
"""测试报告质量评估工具"""

import json
import tempfile
import sys
from pathlib import Path

# 添加父目录到路径，以便导入 scripts 包
sys.path.insert(0, str(Path(__file__).parent.parent))

# 创建一个模拟的测试报告
SAMPLE_REPORT = {
    "company_of_interest": "AAPL",
    "trade_date": "2025-04-27",
    "market_report": """
## AAPL Market Analysis Report

### Technical Analysis Summary

The stock shows strong bullish momentum with the following indicators:

- **SMA (20)**: Current price $178.50 is above the 20-day SMA at $175.30
- **EMA (50)**: Price trading above 50-day EMA ($172.80), indicating uptrend
- **MACD**: Signal line crossover occurred on April 22, bullish signal
- **RSI**: Currently at 62, not yet overbought but showing strength
- **Bollinger Bands**: Price near upper band, indicating momentum

### Price Action Analysis

Recent price movements:
- Open: $176.20
- High: $179.80
- Low: $175.50
- Close: $178.50
- Daily gain: +1.3%

The stock has broken through the resistance level at $177 and is testing the next resistance at $180.

### Volume Analysis

OBV shows increasing trend, confirming the price movement. Daily volume was 52M shares, above average.

### Key Support/Resistance Levels

- Support: $175, $172
- Resistance: $180, $185
""",
    "sentiment_report": """
## Social Media Sentiment Analysis

Based on analysis of Twitter/X, Reddit (r/stocks, r/investing), and financial forums:

### Overall Sentiment: Positive (72% bullish mentions)

- Twitter: 65% positive sentiment in recent tweets about AAPL
- Reddit: Strong bullish discussions in r/stocks
- Forum mentions: Multiple users discussing upcoming earnings

### Key Topics Mentioned

1. iPhone 16 expectations driving excitement
2. AI features in new products
3. Services revenue growth
""",
    "news_report": """
## News Analysis Report - April 27, 2025

### Recent Headlines

1. **April 26**: Apple announces expanded AI partnerships with major tech firms
2. **April 25**: Analyst upgrade from Morgan Stanley - target price raised to $195
3. **April 24**: Q2 earnings preview - expected revenue $94B
4. **本周**: Multiple positive analyst reports released

### Market Impact Analysis

The recent AI announcements have generated significant positive momentum. The Morgan Stanley upgrade provides strong institutional backing.

### Risk Factors

- Regulatory concerns in EU markets
- Supply chain disruptions potential
""",
    "fundamentals_report": """
## Fundamental Analysis Report

### Financial Metrics

| Metric | Value | Industry Avg | Assessment |
|--------|-------|--------------|------------|
| PE Ratio | 28.5 | 25.2 | Above average |
| PB Ratio | 45.2 | 12.5 | High valuation |
| ROE | 147% | 15% | Excellent |
| 净利润率 | 26% | 12% | Outstanding |
| 每股收益 (EPS) | $6.42 | $3.20 | Strong |

### Revenue Analysis

- Q1 Revenue: $119.6B (+2% YoY)
- Services Revenue: $23.1B (+14% YoY)
- Product Revenue: $96.5B

### Profitability

毛利率 maintained at 43.8%, demonstrating strong pricing power and operational efficiency.

### Valuation Assessment

Current valuation is justified by:
- Strong ROE above 140%
- Consistent profit margins
- Growing services segment
""",
    "investment_debate_state": {
        "bull_history": """
Bull Argument 1: AAPL's AI integration strategy is positioning them for significant growth. The recent partnerships demonstrate market leadership in consumer AI.

Bull Argument 2: Financial metrics are exceptional - ROE of 147% is industry-leading. Services revenue growing at 14% YoY provides stable income stream.

Bull Argument 3: Technical indicators show strong momentum - price above key moving averages, MACD bullish crossover, RSI not overbought.

Bull Argument 4: Analyst upgrades from Morgan Stanley and others provide institutional conviction. Target prices averaging $190+.
""",
        "bear_history": """
Bear Argument 1: PE ratio of 28.5 is above industry average, suggesting the stock may be overvalued relative to peers.

Bear Argument 2: Regulatory risks in EU markets could impact revenue. Antitrust concerns remain significant.

Bear Argument 3: Hardware revenue growth only 2% YoY shows potential slowing in core business. iPhone saturation in mature markets.

Bear Argument 4: High PB ratio of 45.2 indicates premium valuation that may not be sustained if growth slows.
""",
        "history": """
Round 1:
Bull: AI strategy is driving growth.
Bear: PE ratio concerns about valuation.

Round 2:
Bull: Services revenue provides stability.
Bear: Hardware growth slowing.

Round 3:
Bull: Technical momentum supports uptrend.
Bear: Regulatory risks in EU.
""",
        "current_response": "Final synthesis needed.",
        "judge_decision": """
**Recommendation**: Overweight

**Rationale**: Based on the debate analysis, the bull arguments carry more weight for the following reasons:
1. AI integration strategy is a genuine growth driver, not just hype
2. Services revenue growth of 14% provides defensive characteristics
3. Exceptional ROE of 147% demonstrates operational excellence
4. Multiple analyst upgrades provide institutional validation

While the bear arguments about valuation and regulatory risks are valid concerns, the growth catalysts and financial strength outweigh these risks at current levels.

**Strategic Actions**:
- Position sizing: 5-7% of portfolio
- Entry strategy: Scale in over 2-3 weeks
- Monitor EU regulatory developments
"""
    },
    "trader_investment_decision": """
**Action**: Buy

**Reasoning**: The Research Manager's Overweight recommendation, combined with bullish technical momentum and strong fundamental metrics, supports a buy position. Entry should be staged to manage volatility risk.

**Entry Price**: $178-180 range

**Stop Loss**: $170 (below key support)

**Position Sizing**: 5% of portfolio

FINAL TRANSACTION PROPOSAL: **BUY**
""",
    "risk_debate_state": {
        "aggressive_history": """
Aggressive View: Full position recommended. AAPL's AI catalyst is real and undervalued by market. Services growth is secular trend. Buy with conviction at current levels.
""",
        "conservative_history": """
Conservative View: Caution advised despite positive signals. PE ratio elevated, regulatory risks material in EU. Recommend smaller position size of 3% max and tighter stop loss at $173.
""",
        "neutral_history": """
Neutral View: Balanced approach recommended. Positive fundamentals but acknowledge valuation concerns. 5% position with stop loss at $172 is appropriate middle ground.
""",
        "history": """
Aggressive: Buy full position.
Conservative: Reduce position size, tighter stops.
Neutral: Balanced approach.
""",
        "judge_decision": """
**Rating**: Overweight

**Executive Summary**: Take a moderate overweight position (5-6%) with staged entry over 2 weeks. Set stop loss at $172 to balance growth potential with downside protection.

**Investment Thesis**: AAPL represents a quality growth opportunity with multiple catalysts:
- AI integration driving new revenue streams
- Services segment providing stable, recurring income
- Strong technical momentum confirming uptrend
- Exceptional financial metrics (ROE 147%, 毛利率 43%)

The primary risks (regulatory, valuation premium) are mitigated by:
- Diversified revenue streams
- Strong operational execution
- Institutional analyst support

**Price Target**: $195 (12-month)
**Time Horizon**: 6-12 months
"""
    },
    "investment_plan": """
**Recommendation**: Overweight

**Rationale**: Strong fundamentals, bullish technicals, AI growth catalyst.

**Strategic Actions**: 5-7% position, staged entry.
""",
    "final_trade_decision": """
**Rating**: Overweight

**Executive Summary**: Apple presents a compelling investment opportunity with strong fundamental metrics (ROE 147%, 毛利率 43%), bullish technical momentum (above key SMAs, MACD crossover), and clear growth catalysts (AI integration). Position at 5-6% with stop loss at $172.

**Investment Thesis**:
The investment thesis rests on three pillars:

1. **Financial Excellence**: AAPL's ROE of 147% far exceeds industry average, demonstrating exceptional capital efficiency. 净利润率 of 26% shows pricing power.

2. **Growth Catalysts**: AI partnerships announced April 26 represent genuine revenue opportunity. Services segment growing 14% YoY provides defensive characteristics.

3. **Technical Confirmation**: Price above SMA(20) and EMA(50), MACD bullish crossover, RSI at 62 not yet overbought - momentum intact.

Risk factors acknowledged:
- PE ratio 28.5 above industry average
- EU regulatory concerns
- Hardware revenue growth modest at 2%

Mitigation through diversified revenue (services) and staged entry strategy.

| Metric | Assessment |
|--------|------------|
| Fundamental | Excellent (ROE 147%) |
| Technical | Bullish (above MAs) |
| Sentiment | Positive (72% bullish) |
| Catalysts | Clear (AI, Services) |

**Price Target**: $195
**Time Horizon**: 6-12 months
"""
}


def create_test_report_file() -> Path:
    """创建临时测试报告文件"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False,
                                     encoding='utf-8') as f:
        json.dump(SAMPLE_REPORT, f, ensure_ascii=False, indent=2)
        return Path(f.name)


def test_evaluator():
    """测试评估器"""
    from scripts.report_quality_evaluator import ReportQualityEvaluator, evaluate_report

    # 创建测试文件
    test_file = create_test_report_file()
    print(f"测试文件: {test_file}")
    print()

    # 测试基本评估
    print("=" * 60)
    print("基本评估测试")
    print("=" * 60)
    evaluate_report(str(test_file))

    print()
    print("=" * 60)
    print("详细评估测试")
    print("=" * 60)
    evaluate_report(str(test_file), verbose=True)

    # 清理
    test_file.unlink()


if __name__ == "__main__":
    test_evaluator()