"""
エコシステム学習システム
外部データとユーザー行動を通じてチャットボットを継続的に賢くするシステム
"""

import os
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
import sqlite3
from collections import defaultdict, Counter

@dataclass
class UserInteraction:
    """ユーザーインタラクション記録"""
    user_id: str
    query: str
    response: str
    timestamp: datetime
    response_time: float
    satisfaction_score: Optional[float] = None
    feedback: Optional[str] = None
    context: Dict[str, Any] = None

@dataclass
class KnowledgeGap:
    """知識ギャップ記録"""
    query_pattern: str
    frequency: int
    first_occurrence: datetime
    last_occurrence: datetime
    suggested_sources: List[str]
    priority: int  # 1-10 (10が最高優先度)

@dataclass
class LearningInsight:
    """学習インサイト"""
    insight_type: str  # "pattern", "trend", "gap", "optimization"
    description: str
    confidence: float
    actionable: bool
    metadata: Dict[str, Any]

class EcosystemLearningSystem:
    """エコシステム学習システム"""
    
    def __init__(self, db_path: str = "ecosystem_learning.db"):
        self.db_path = db_path
        self.interactions: List[UserInteraction] = []
        self.knowledge_gaps: List[KnowledgeGap] = []
        self.learning_insights: List[LearningInsight] = []
        
        # 学習パラメータ
        self.learning_threshold = 10  # 学習を開始する最小インタラクション数
        self.gap_threshold = 3  # 知識ギャップとして認識する最小頻度
        self.confidence_threshold = 0.7  # インサイトの信頼度閾値
        
        # パターン分析用
        self.query_patterns = defaultdict(int)
        self.response_patterns = defaultdict(int)
        self.user_preferences = defaultdict(dict)
        
        # データベース初期化
        self._init_database()
        
        # 既存データの読み込み
        self._load_existing_data()
    
    def _init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # インタラクションテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                response_time REAL,
                satisfaction_score REAL,
                feedback TEXT,
                context TEXT
            )
        ''')
        
        # 知識ギャップテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_gaps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_pattern TEXT NOT NULL,
                frequency INTEGER NOT NULL,
                first_occurrence TEXT NOT NULL,
                last_occurrence TEXT NOT NULL,
                suggested_sources TEXT,
                priority INTEGER NOT NULL
            )
        ''')
        
        # 学習インサイトテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight_type TEXT NOT NULL,
                description TEXT NOT NULL,
                confidence REAL NOT NULL,
                actionable BOOLEAN NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_existing_data(self):
        """既存データの読み込み"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # インタラクションデータの読み込み
            interactions_df = pd.read_sql_query(
                "SELECT * FROM interactions ORDER BY timestamp DESC LIMIT 1000",
                conn
            )
            
            for _, row in interactions_df.iterrows():
                interaction = UserInteraction(
                    user_id=row['user_id'],
                    query=row['query'],
                    response=row['response'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    response_time=row['response_time'],
                    satisfaction_score=row['satisfaction_score'],
                    feedback=row['feedback'],
                    context=json.loads(row['context']) if row['context'] else {}
                )
                self.interactions.append(interaction)
            
            # 知識ギャップデータの読み込み
            gaps_df = pd.read_sql_query("SELECT * FROM knowledge_gaps", conn)
            
            for _, row in gaps_df.iterrows():
                gap = KnowledgeGap(
                    query_pattern=row['query_pattern'],
                    frequency=row['frequency'],
                    first_occurrence=datetime.fromisoformat(row['first_occurrence']),
                    last_occurrence=datetime.fromisoformat(row['last_occurrence']),
                    suggested_sources=json.loads(row['suggested_sources']),
                    priority=row['priority']
                )
                self.knowledge_gaps.append(gap)
            
            conn.close()
            
        except Exception as e:
            print(f"データ読み込みエラー: {e}")
    
    def record_interaction(self, user_id: str, query: str, response: str, 
                          response_time: float, context: Dict[str, Any] = None) -> str:
        """ユーザーインタラクションを記録"""
        interaction = UserInteraction(
            user_id=user_id,
            query=query,
            response=response,
            timestamp=datetime.now(),
            response_time=response_time,
            context=context or {}
        )
        
        self.interactions.append(interaction)
        
        # データベースに保存
        self._save_interaction(interaction)
        
        # パターン分析を実行
        self._analyze_patterns(interaction)
        
        # 知識ギャップを検出
        self._detect_knowledge_gaps(interaction)
        
        # 学習インサイトを生成
        self._generate_learning_insights()
        
        return interaction.timestamp.isoformat()
    
    def _save_interaction(self, interaction: UserInteraction):
        """インタラクションをデータベースに保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO interactions 
            (user_id, query, response, timestamp, response_time, satisfaction_score, feedback, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            interaction.user_id,
            interaction.query,
            interaction.response,
            interaction.timestamp.isoformat(),
            interaction.response_time,
            interaction.satisfaction_score,
            interaction.feedback,
            json.dumps(interaction.context) if interaction.context else None
        ))
        
        conn.commit()
        conn.close()
    
    def _analyze_patterns(self, interaction: UserInteraction):
        """パターン分析を実行"""
        # クエリパターンの分析
        query_keywords = self._extract_keywords(interaction.query)
        for keyword in query_keywords:
            self.query_patterns[keyword] += 1
        
        # レスポンスパターンの分析
        response_keywords = self._extract_keywords(interaction.response)
        for keyword in response_keywords:
            self.response_patterns[keyword] += 1
        
        # ユーザー好みの分析
        if interaction.satisfaction_score is not None:
            user_prefs = self.user_preferences[interaction.user_id]
            for keyword in query_keywords:
                if keyword not in user_prefs:
                    user_prefs[keyword] = []
                user_prefs[keyword].append(interaction.satisfaction_score)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """テキストからキーワードを抽出"""
        # 簡単なキーワード抽出（実際の実装ではより高度なNLPを使用）
        keywords = []
        
        # 税務関連キーワード
        tax_keywords = [
            "所得税", "消費税", "法人税", "相続税", "贈与税", "住民税",
            "確定申告", "控除", "節税", "税制改正", "インボイス",
            "年収", "所得", "給与", "賞与", "副業", "フリーランス"
        ]
        
        for keyword in tax_keywords:
            if keyword in text:
                keywords.append(keyword)
        
        # 質問パターン
        question_patterns = [
            "いくら", "どのくらい", "計算", "方法", "手続き", "必要",
            "教えて", "説明", "違い", "比較", "おすすめ"
        ]
        
        for pattern in question_patterns:
            if pattern in text:
                keywords.append(f"質問_{pattern}")
        
        return keywords
    
    def _detect_knowledge_gaps(self, interaction: UserInteraction):
        """知識ギャップを検出"""
        # レスポンスの質を評価
        response_quality = self._evaluate_response_quality(interaction)
        
        if response_quality < 0.5:  # 低品質な回答
            query_pattern = self._create_query_pattern(interaction.query)
            
            # 既存のギャップをチェック
            existing_gap = None
            for gap in self.knowledge_gaps:
                if gap.query_pattern == query_pattern:
                    existing_gap = gap
                    break
            
            if existing_gap:
                # 既存ギャップを更新
                existing_gap.frequency += 1
                existing_gap.last_occurrence = interaction.timestamp
                existing_gap.priority = min(10, existing_gap.priority + 1)
            else:
                # 新しいギャップを作成
                gap = KnowledgeGap(
                    query_pattern=query_pattern,
                    frequency=1,
                    first_occurrence=interaction.timestamp,
                    last_occurrence=interaction.timestamp,
                    suggested_sources=self._suggest_sources(query_pattern),
                    priority=5
                )
                self.knowledge_gaps.append(gap)
    
    def _evaluate_response_quality(self, interaction: UserInteraction) -> float:
        """レスポンスの質を評価"""
        score = 0.5  # ベーススコア
        
        response = interaction.response.lower()
        
        # 肯定的な指標
        if "申し訳ありません" not in response:
            score += 0.2
        if len(response) > 100:  # 詳細な回答
            score += 0.2
        if any(keyword in response for keyword in ["計算", "例", "具体的"]):
            score += 0.1
        
        # 否定的な指標
        if "情報は見つかりません" in response:
            score -= 0.3
        if len(response) < 50:  # 短すぎる回答
            score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _create_query_pattern(self, query: str) -> str:
        """クエリからパターンを作成"""
        # クエリを正規化してパターンを作成
        normalized = query.lower()
        
        # 数値を置換
        import re
        normalized = re.sub(r'\d+', 'NUM', normalized)
        
        # 一般的な語句を置換
        replacements = {
            "いくら": "AMOUNT",
            "どのくらい": "AMOUNT",
            "方法": "METHOD",
            "手続き": "PROCEDURE",
            "教えて": "EXPLAIN",
            "計算": "CALCULATE"
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        return normalized
    
    def _suggest_sources(self, query_pattern: str) -> List[str]:
        """クエリパターンに基づいて情報源を提案"""
        suggestions = []
        
        if "所得税" in query_pattern or "所得" in query_pattern:
            suggestions.extend(["e-Gov法令検索", "e-Stat統計データ", "国税庁ホームページ"])
        elif "消費税" in query_pattern:
            suggestions.extend(["e-Gov法令検索", "財務省ホームページ"])
        elif "法人税" in query_pattern:
            suggestions.extend(["e-Gov法令検索", "e-Stat統計データ"])
        elif "計算" in query_pattern or "AMOUNT" in query_pattern:
            suggestions.extend(["e-Stat統計データ", "計算シミュレーター"])
        else:
            suggestions.extend(["e-Gov法令検索", "e-Stat統計データ", "X API"])
        
        return suggestions
    
    def _generate_learning_insights(self):
        """学習インサイトを生成"""
        if len(self.interactions) < self.learning_threshold:
            return
        
        # パターン分析インサイト
        self._generate_pattern_insights()
        
        # トレンド分析インサイト
        self._generate_trend_insights()
        
        # 最適化インサイト
        self._generate_optimization_insights()
    
    def _generate_pattern_insights(self):
        """パターン分析インサイトを生成"""
        # 最も頻繁なクエリパターン
        top_patterns = Counter(self.query_patterns).most_common(5)
        
        for pattern, count in top_patterns:
            if count >= 5:  # 5回以上出現
                insight = LearningInsight(
                    insight_type="pattern",
                    description=f"「{pattern}」に関する質問が{count}回発生しています",
                    confidence=min(1.0, count / 20),
                    actionable=True,
                    metadata={
                        "pattern": pattern,
                        "frequency": count,
                        "action": "このトピックの情報を強化することを推奨"
                    }
                )
                self.learning_insights.append(insight)
    
    def _generate_trend_insights(self):
        """トレンド分析インサイトを生成"""
        # 最近のインタラクションを分析
        recent_interactions = [
            i for i in self.interactions 
            if i.timestamp > datetime.now() - timedelta(days=7)
        ]
        
        if len(recent_interactions) >= 10:
            # 応答時間のトレンド
            avg_response_time = np.mean([i.response_time for i in recent_interactions])
            
            if avg_response_time > 3.0:  # 3秒以上
                insight = LearningInsight(
                    insight_type="trend",
                    description=f"最近の平均応答時間が{avg_response_time:.1f}秒と長くなっています",
                    confidence=0.8,
                    actionable=True,
                    metadata={
                        "metric": "response_time",
                        "value": avg_response_time,
                        "action": "パフォーマンス最適化を検討"
                    }
                )
                self.learning_insights.append(insight)
    
    def _generate_optimization_insights(self):
        """最適化インサイトを生成"""
        # 知識ギャップの優先度分析
        high_priority_gaps = [g for g in self.knowledge_gaps if g.priority >= 8]
        
        if high_priority_gaps:
            insight = LearningInsight(
                insight_type="optimization",
                description=f"高優先度の知識ギャップが{len(high_priority_gaps)}件あります",
                confidence=0.9,
                actionable=True,
                metadata={
                    "gaps": [g.query_pattern for g in high_priority_gaps],
                    "action": "これらのトピックの情報源を強化"
                }
            )
            self.learning_insights.append(insight)
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """学習サマリーを取得"""
        return {
            "total_interactions": len(self.interactions),
            "knowledge_gaps": len(self.knowledge_gaps),
            "learning_insights": len(self.learning_insights),
            "top_query_patterns": dict(Counter(self.query_patterns).most_common(10)),
            "top_response_patterns": dict(Counter(self.response_patterns).most_common(10)),
            "high_priority_gaps": [
                {
                    "pattern": gap.query_pattern,
                    "frequency": gap.frequency,
                    "priority": gap.priority,
                    "suggested_sources": gap.suggested_sources
                }
                for gap in self.knowledge_gaps if gap.priority >= 7
            ],
            "recent_insights": [
                {
                    "type": insight.insight_type,
                    "description": insight.description,
                    "confidence": insight.confidence,
                    "actionable": insight.actionable
                }
                for insight in self.learning_insights[-5:]  # 最新5件
            ]
        }
    
    def get_personalized_recommendations(self, user_id: str) -> Dict[str, Any]:
        """ユーザー個人化された推奨事項を取得"""
        user_interactions = [i for i in self.interactions if i.user_id == user_id]
        
        if not user_interactions:
            return {"recommendations": [], "reason": "データ不足"}
        
        # ユーザーの興味を分析
        user_interests = defaultdict(int)
        for interaction in user_interactions:
            keywords = self._extract_keywords(interaction.query)
            for keyword in keywords:
                user_interests[keyword] += 1
        
        # 推奨事項を生成
        recommendations = []
        
        # 最も興味のあるトピックに関連する情報を推奨
        top_interests = sorted(user_interests.items(), key=lambda x: x[1], reverse=True)[:3]
        
        for interest, count in top_interests:
            recommendations.append({
                "type": "related_topic",
                "title": f"{interest}についてさらに学ぶ",
                "description": f"あなたは{interest}について{count}回質問されています",
                "priority": "high" if count >= 3 else "medium"
            })
        
        # 知識ギャップに基づく推奨
        user_gaps = [g for g in self.knowledge_gaps if g.priority >= 6]
        for gap in user_gaps[:2]:  # 上位2件
            recommendations.append({
                "type": "knowledge_gap",
                "title": f"{gap.query_pattern}について詳しく調べる",
                "description": "このトピックについてより詳しい情報が必要です",
                "priority": "high",
                "suggested_sources": gap.suggested_sources
            })
        
        return {
            "recommendations": recommendations,
            "user_interests": dict(top_interests),
            "total_queries": len(user_interactions)
        }
    
    def update_satisfaction_score(self, interaction_id: str, score: float, feedback: str = None):
        """満足度スコアを更新"""
        # インタラクションIDから対応するインタラクションを検索
        # 実際の実装では、より効率的な方法を使用
        for interaction in self.interactions:
            if interaction.timestamp.isoformat() == interaction_id:
                interaction.satisfaction_score = score
                interaction.feedback = feedback
                
                # データベースを更新
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE interactions 
                    SET satisfaction_score = ?, feedback = ?
                    WHERE timestamp = ?
                ''', (score, feedback, interaction.timestamp.isoformat()))
                conn.commit()
                conn.close()
                
                break

# グローバルインスタンス
ecosystem_learner = EcosystemLearningSystem()
