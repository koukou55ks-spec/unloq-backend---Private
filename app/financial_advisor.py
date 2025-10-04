"""
TaxHack 金融アドバイザーシステム
お金に関心のあるすべての人向けの包括的な機能
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class FinancialProfile:
    """金融プロフィール"""
    user_id: str
    age: Optional[int] = None
    income: Optional[int] = None
    savings: Optional[int] = None
    investments: Optional[int] = None
    debt: Optional[int] = None
    family_size: Optional[int] = None
    risk_tolerance: Optional[str] = None  # conservative, moderate, aggressive
    financial_goals: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.financial_goals is None:
            self.financial_goals = []

@dataclass
class FinancialAdvice:
    """金融アドバイス"""
    category: str
    title: str
    description: str
    priority: str  # high, medium, low
    action_items: List[str]
    estimated_benefit: Optional[str] = None
    timeline: Optional[str] = None

class FinancialAdvisor:
    """金融アドバイザークラス"""
    
    def __init__(self):
        self.tax_brackets_2024 = [
            (1950000, 0.05),
            (3300000, 0.10),
            (6950000, 0.20),
            (9000000, 0.23),
            (18000000, 0.33),
            (40000000, 0.40),
            (float('inf'), 0.45)
        ]
        
        self.deductions = {
            'basic': 480000,  # 基礎控除
            'employment': self._calculate_employment_deduction,
            'spouse': 380000,  # 配偶者控除
            'dependent': 380000  # 扶養控除（一人当たり）
        }
    
    def _calculate_employment_deduction(self, income: int) -> int:
        """給与所得控除を計算"""
        if income <= 1625000:
            return max(550000, income * 0.4)
        elif income <= 1800000:
            return income * 0.4 + 100000
        elif income <= 3600000:
            return income * 0.3 + 280000
        elif income <= 6600000:
            return income * 0.2 + 640000
        elif income <= 8500000:
            return income * 0.1 + 1300000
        else:
            return 1950000
    
    def calculate_income_tax(self, profile: FinancialProfile) -> Dict[str, Any]:
        """所得税を計算"""
        if not profile.income:
            return {"error": "年収情報が必要です"}
        
        # 給与所得控除
        employment_deduction = self._calculate_employment_deduction(profile.income * 10000)
        
        # 基礎控除
        basic_deduction = self.deductions['basic']
        
        # 扶養控除
        dependent_deduction = 0
        if profile.family_size and profile.family_size > 1:
            dependent_deduction = (profile.family_size - 1) * self.deductions['dependent']
        
        # 課税所得
        total_deductions = employment_deduction + basic_deduction + dependent_deduction
        taxable_income = max(0, (profile.income * 10000) - total_deductions)
        
        # 所得税計算
        tax = 0
        remaining_income = taxable_income
        
        for bracket_limit, rate in self.tax_brackets_2024:
            if remaining_income <= 0:
                break
            
            taxable_in_bracket = min(remaining_income, bracket_limit - (taxable_income - remaining_income))
            tax += taxable_in_bracket * rate
            remaining_income -= taxable_in_bracket
        
        # 住民税（概算）
        resident_tax = taxable_income * 0.1
        
        return {
            "gross_income": profile.income * 10000,
            "employment_deduction": employment_deduction,
            "basic_deduction": basic_deduction,
            "dependent_deduction": dependent_deduction,
            "total_deductions": total_deductions,
            "taxable_income": taxable_income,
            "income_tax": int(tax),
            "resident_tax": int(resident_tax),
            "total_tax": int(tax + resident_tax),
            "net_income": int((profile.income * 10000) - tax - resident_tax),
            "effective_tax_rate": round((tax + resident_tax) / (profile.income * 10000) * 100, 2)
        }
    
    def generate_tax_saving_advice(self, profile: FinancialProfile) -> List[FinancialAdvice]:
        """節税アドバイスを生成"""
        advice_list = []
        
        if not profile.income:
            return advice_list
        
        # iDeCo推奨
        if profile.age and profile.age < 60:
            max_ideco = 276000 if profile.income > 500 else 144000
            advice_list.append(FinancialAdvice(
                category="節税",
                title="iDeCo（個人型確定拠出年金）の活用",
                description=f"年間最大{max_ideco:,}円まで拠出可能。全額所得控除で大きな節税効果があります。",
                priority="high",
                action_items=[
                    "金融機関でiDeCo口座を開設",
                    "月額拠出額を設定（年収の10-15%程度推奨）",
                    "運用商品を選択（インデックスファンド推奨）"
                ],
                estimated_benefit=f"年間約{int(max_ideco * 0.2):,}円の節税効果",
                timeline="1ヶ月以内"
            ))
        
        # つみたてNISA推奨
        advice_list.append(FinancialAdvice(
            category="投資",
            title="つみたてNISAの活用",
            description="年間40万円まで非課税で投資可能。20年間運用益が非課税になります。",
            priority="high",
            action_items=[
                "証券会社でつみたてNISA口座を開設",
                "月額33,333円の積立設定",
                "全世界株式インデックスファンドを選択"
            ],
            estimated_benefit="20年で約200万円の運用益非課税効果",
            timeline="1ヶ月以内"
        ))
        
        # ふるさと納税
        if profile.income and profile.income >= 300:
            limit = int(profile.income * 10000 * 0.02)  # 概算
            advice_list.append(FinancialAdvice(
                category="節税",
                title="ふるさと納税の活用",
                description=f"年間約{limit:,}円まで実質2,000円の負担で返礼品を受け取れます。",
                priority="medium",
                action_items=[
                    "ふるさと納税サイトで寄付先を選択",
                    "ワンストップ特例制度を利用",
                    "年末までに寄付を完了"
                ],
                estimated_benefit=f"約{limit-2000:,}円相当の返礼品",
                timeline="年内"
            ))
        
        # 生命保険料控除
        advice_list.append(FinancialAdvice(
            category="節税",
            title="生命保険料控除の最適化",
            description="生命保険、介護医療保険、個人年金保険でそれぞれ最大4万円の控除が可能。",
            priority="medium",
            action_items=[
                "現在の保険契約を見直し",
                "不足している保険種類を検討",
                "控除額を最大化する保険料設定"
            ],
            estimated_benefit="年間最大12万円の所得控除",
            timeline="3ヶ月以内"
        ))
        
        return advice_list
    
    def generate_investment_advice(self, profile: FinancialProfile) -> List[FinancialAdvice]:
        """投資アドバイスを生成"""
        advice_list = []
        
        if not profile.age or not profile.income:
            return advice_list
        
        # リスク許容度に基づく資産配分
        if profile.risk_tolerance == "conservative":
            stock_ratio = 30
            bond_ratio = 70
        elif profile.risk_tolerance == "aggressive":
            stock_ratio = 80
            bond_ratio = 20
        else:  # moderate
            stock_ratio = min(100 - profile.age, 70)
            bond_ratio = 100 - stock_ratio
        
        advice_list.append(FinancialAdvice(
            category="投資",
            title="資産配分の最適化",
            description=f"あなたの年齢とリスク許容度に基づき、株式{stock_ratio}%、債券{bond_ratio}%の配分を推奨します。",
            priority="high",
            action_items=[
                f"株式インデックスファンド: {stock_ratio}%",
                f"債券インデックスファンド: {bond_ratio}%",
                "月1回のリバランス実施"
            ],
            estimated_benefit="年間5-7%のリターン期待",
            timeline="即座に実行可能"
        ))
        
        # 緊急資金の確保
        emergency_fund = profile.income * 10000 * 0.5 if profile.income else 1000000
        advice_list.append(FinancialAdvice(
            category="貯蓄",
            title="緊急資金の確保",
            description=f"生活費の6ヶ月分（約{emergency_fund:,}円）を普通預金で確保することを推奨します。",
            priority="high",
            action_items=[
                "高金利ネット銀行口座を開設",
                "毎月一定額を自動積立",
                "目標額達成まで投資は控えめに"
            ],
            estimated_benefit="金融的安定性の確保",
            timeline="1年以内"
        ))
        
        return advice_list
    
    def generate_retirement_planning(self, profile: FinancialProfile) -> Dict[str, Any]:
        """退職金計画を生成"""
        if not profile.age or not profile.income:
            return {"error": "年齢と年収情報が必要です"}
        
        years_to_retirement = 65 - profile.age
        if years_to_retirement <= 0:
            return {"message": "既に退職年齢に達しています"}
        
        # 必要退職資金の計算（現在の生活費の70%×25年）
        annual_expenses = profile.income * 10000 * 0.7
        required_retirement_fund = annual_expenses * 25
        
        # 現在の資産
        current_assets = (profile.savings or 0) * 10000 + (profile.investments or 0) * 10000
        
        # 必要な月額積立額
        required_monthly_saving = (required_retirement_fund - current_assets) / (years_to_retirement * 12)
        
        return {
            "years_to_retirement": years_to_retirement,
            "required_retirement_fund": int(required_retirement_fund),
            "current_assets": int(current_assets),
            "shortfall": int(required_retirement_fund - current_assets),
            "required_monthly_saving": int(required_monthly_saving),
            "recommended_actions": [
                f"毎月{int(required_monthly_saving):,}円の積立投資",
                "iDeCoの満額拠出",
                "つみたてNISAの活用",
                "企業型確定拠出年金の最適化"
            ]
        }
    
    def analyze_debt_management(self, profile: FinancialProfile) -> List[FinancialAdvice]:
        """債務管理アドバイス"""
        advice_list = []
        
        if not profile.debt or profile.debt <= 0:
            return advice_list
        
        debt_amount = profile.debt * 10000
        monthly_income = (profile.income * 10000) / 12 if profile.income else 0
        
        if monthly_income > 0:
            debt_ratio = (debt_amount / 12) / monthly_income
            
            if debt_ratio > 0.3:
                advice_list.append(FinancialAdvice(
                    category="債務管理",
                    title="債務比率の改善が必要",
                    description=f"債務比率が{debt_ratio*100:.1f}%と高めです。30%以下に抑えることを推奨します。",
                    priority="high",
                    action_items=[
                        "高金利債務から優先的に返済",
                        "債務整理の検討",
                        "副収入の確保",
                        "支出の見直し"
                    ],
                    estimated_benefit="金融的安定性の向上",
                    timeline="6ヶ月以内"
                ))
            
            # 繰上返済のアドバイス
            if profile.savings and profile.savings > 100:
                advice_list.append(FinancialAdvice(
                    category="債務管理",
                    title="繰上返済の検討",
                    description="貯蓄の一部を使って高金利債務の繰上返済を検討しましょう。",
                    priority="medium",
                    action_items=[
                        "債務の金利と投資リターンを比較",
                        "緊急資金を残して繰上返済",
                        "返済計画の見直し"
                    ],
                    estimated_benefit="利息負担の軽減",
                    timeline="3ヶ月以内"
                ))
        
        return advice_list
    
    def generate_comprehensive_advice(self, profile: FinancialProfile) -> Dict[str, Any]:
        """包括的な金融アドバイスを生成"""
        advice = {
            "tax_calculation": self.calculate_income_tax(profile),
            "tax_saving_advice": self.generate_tax_saving_advice(profile),
            "investment_advice": self.generate_investment_advice(profile),
            "retirement_planning": self.generate_retirement_planning(profile),
            "debt_management": self.analyze_debt_management(profile),
            "financial_health_score": self._calculate_financial_health_score(profile)
        }
        
        return advice
    
    def _calculate_financial_health_score(self, profile: FinancialProfile) -> Dict[str, Any]:
        """金融健全性スコアを計算"""
        score = 0
        max_score = 100
        factors = []
        
        # 収入の安定性 (20点)
        if profile.income and profile.income > 300:
            score += 20
            factors.append("安定した収入")
        elif profile.income and profile.income > 200:
            score += 15
            factors.append("中程度の収入")
        else:
            factors.append("収入の改善が必要")
        
        # 貯蓄率 (25点)
        if profile.income and profile.savings:
            savings_rate = (profile.savings * 10000) / (profile.income * 10000)
            if savings_rate >= 0.2:
                score += 25
                factors.append("優秀な貯蓄率")
            elif savings_rate >= 0.1:
                score += 20
                factors.append("良好な貯蓄率")
            elif savings_rate >= 0.05:
                score += 15
                factors.append("平均的な貯蓄率")
            else:
                factors.append("貯蓄率の改善が必要")
        
        # 投資状況 (20点)
        if profile.investments and profile.investments > 0:
            score += 20
            factors.append("投資を実践")
        else:
            factors.append("投資の開始を推奨")
        
        # 債務状況 (20点)
        if not profile.debt or profile.debt <= 0:
            score += 20
            factors.append("債務なし")
        elif profile.income and profile.debt:
            debt_ratio = (profile.debt * 10000) / (profile.income * 10000)
            if debt_ratio <= 0.3:
                score += 15
                factors.append("管理可能な債務レベル")
            else:
                factors.append("債務の削減が必要")
        
        # 年齢に応じた準備 (15点)
        if profile.age:
            if profile.age < 30:
                score += 15
                factors.append("若年期の良いスタート")
            elif profile.age < 50:
                if profile.investments or (profile.savings and profile.savings > 500):
                    score += 15
                    factors.append("中年期の適切な準備")
                else:
                    factors.append("退職準備の加速が必要")
            else:
                if profile.investments and profile.investments > 1000:
                    score += 15
                    factors.append("退職準備が順調")
                else:
                    factors.append("退職準備の強化が必要")
        
        # スコアの評価
        if score >= 80:
            grade = "優秀"
            message = "金融状況は非常に良好です"
        elif score >= 60:
            grade = "良好"
            message = "金融状況は安定しています"
        elif score >= 40:
            grade = "普通"
            message = "改善の余地があります"
        else:
            grade = "要改善"
            message = "金融計画の見直しが必要です"
        
        return {
            "score": score,
            "max_score": max_score,
            "grade": grade,
            "message": message,
            "factors": factors
        }

# グローバルインスタンス
financial_advisor = FinancialAdvisor()
