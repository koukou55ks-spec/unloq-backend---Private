"""
TaxHack データベース管理システム
SQLiteベースの永続化機能
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@dataclass
class UserInteraction:
    """ユーザーインタラクション"""
    user_id: str
    query: str
    response: str
    timestamp: str
    response_time: Optional[float] = None
    satisfaction_score: Optional[float] = None
    feedback: Optional[str] = None
    context: Optional[str] = None

@dataclass
class KnowledgeGap:
    """知識ギャップ"""
    query_pattern: str
    frequency: int
    first_occurrence: str
    last_occurrence: str
    suggested_sources: Optional[str] = None
    priority: int = 1

@dataclass
class LearningInsight:
    """学習インサイト"""
    insight_type: str
    description: str
    confidence: float
    actionable: bool
    metadata: Optional[str] = None
    created_at: str = None

class TaxHackDatabase:
    """TaxHackデータベース管理クラス"""
    
    def __init__(self, db_path: str = "./taxhack_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """データベースの初期化"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # ユーザーインタラクションテーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_interactions (
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
                        priority INTEGER NOT NULL DEFAULT 1
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
                
                # ユーザープロフィールテーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        user_id TEXT PRIMARY KEY,
                        age INTEGER,
                        income INTEGER,
                        industry TEXT,
                        location TEXT,
                        marital_status TEXT,
                        dependents INTEGER,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                ''')
                
                # システム統計テーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        stat_name TEXT NOT NULL,
                        stat_value TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                ''')
                
                conn.commit()
                logger.info("データベースが正常に初期化されました")
                
        except Exception as e:
            logger.error(f"データベース初期化エラー: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """データベース接続のコンテキストマネージャー"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"データベース接続エラー: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def save_interaction(self, interaction: UserInteraction) -> int:
        """ユーザーインタラクションを保存"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_interactions 
                    (user_id, query, response, timestamp, response_time, 
                     satisfaction_score, feedback, context)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    interaction.user_id,
                    interaction.query,
                    interaction.response,
                    interaction.timestamp,
                    interaction.response_time,
                    interaction.satisfaction_score,
                    interaction.feedback,
                    interaction.context
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"インタラクション保存エラー: {e}")
            raise
    
    def update_satisfaction(self, interaction_id: int, score: float, feedback: str = None):
        """満足度スコアを更新"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE user_interactions 
                    SET satisfaction_score = ?, feedback = ?
                    WHERE id = ?
                ''', (score, feedback, interaction_id))
                conn.commit()
        except Exception as e:
            logger.error(f"満足度更新エラー: {e}")
            raise
    
    def get_user_interactions(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """ユーザーのインタラクション履歴を取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM user_interactions 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (user_id, limit))
                
                interactions = []
                for row in cursor.fetchall():
                    interactions.append(dict(row))
                return interactions
        except Exception as e:
            logger.error(f"インタラクション取得エラー: {e}")
            return []
    
    def save_knowledge_gap(self, gap: KnowledgeGap):
        """知識ギャップを保存"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO knowledge_gaps 
                    (query_pattern, frequency, first_occurrence, last_occurrence, 
                     suggested_sources, priority)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    gap.query_pattern,
                    gap.frequency,
                    gap.first_occurrence,
                    gap.last_occurrence,
                    gap.suggested_sources,
                    gap.priority
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"知識ギャップ保存エラー: {e}")
            raise
    
    def get_knowledge_gaps(self, min_priority: int = 1) -> List[Dict[str, Any]]:
        """知識ギャップを取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM knowledge_gaps 
                    WHERE priority >= ? 
                    ORDER BY priority DESC, frequency DESC
                ''', (min_priority,))
                
                gaps = []
                for row in cursor.fetchall():
                    gaps.append(dict(row))
                return gaps
        except Exception as e:
            logger.error(f"知識ギャップ取得エラー: {e}")
            return []
    
    def save_learning_insight(self, insight: LearningInsight):
        """学習インサイトを保存"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO learning_insights 
                    (insight_type, description, confidence, actionable, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    insight.insight_type,
                    insight.description,
                    insight.confidence,
                    insight.actionable,
                    insight.metadata,
                    insight.created_at or datetime.now().isoformat()
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"学習インサイト保存エラー: {e}")
            raise
    
    def get_learning_insights(self, limit: int = 20) -> List[Dict[str, Any]]:
        """学習インサイトを取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM learning_insights 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
                
                insights = []
                for row in cursor.fetchall():
                    insights.append(dict(row))
                return insights
        except Exception as e:
            logger.error(f"学習インサイト取得エラー: {e}")
            return []
    
    def save_user_profile(self, user_id: str, profile_data: Dict[str, Any]):
        """ユーザープロフィールを保存"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 既存のプロフィールをチェック
                cursor.execute('SELECT user_id FROM user_profiles WHERE user_id = ?', (user_id,))
                exists = cursor.fetchone()
                
                now = datetime.now().isoformat()
                
                if exists:
                    # 更新
                    cursor.execute('''
                        UPDATE user_profiles 
                        SET age = ?, income = ?, industry = ?, location = ?, 
                            marital_status = ?, dependents = ?, updated_at = ?
                        WHERE user_id = ?
                    ''', (
                        profile_data.get('age'),
                        profile_data.get('income'),
                        profile_data.get('industry'),
                        profile_data.get('location'),
                        profile_data.get('marital_status'),
                        profile_data.get('dependents'),
                        now,
                        user_id
                    ))
                else:
                    # 新規作成
                    cursor.execute('''
                        INSERT INTO user_profiles 
                        (user_id, age, income, industry, location, marital_status, 
                         dependents, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id,
                        profile_data.get('age'),
                        profile_data.get('income'),
                        profile_data.get('industry'),
                        profile_data.get('location'),
                        profile_data.get('marital_status'),
                        profile_data.get('dependents'),
                        now,
                        now
                    ))
                
                conn.commit()
        except Exception as e:
            logger.error(f"ユーザープロフィール保存エラー: {e}")
            raise
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザープロフィールを取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM user_profiles WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"ユーザープロフィール取得エラー: {e}")
            return None
    
    def get_conversation_summary(self, user_id: str = None) -> Dict[str, Any]:
        """会話サマリーを取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if user_id:
                    # 特定ユーザーのサマリー
                    cursor.execute('''
                        SELECT COUNT(*) as total_queries,
                               AVG(response_time) as avg_response_time,
                               AVG(satisfaction_score) as avg_satisfaction
                        FROM user_interactions 
                        WHERE user_id = ?
                    ''', (user_id,))
                else:
                    # 全体のサマリー
                    cursor.execute('''
                        SELECT COUNT(*) as total_queries,
                               COUNT(DISTINCT user_id) as unique_users,
                               AVG(response_time) as avg_response_time,
                               AVG(satisfaction_score) as avg_satisfaction
                        FROM user_interactions
                    ''')
                
                row = cursor.fetchone()
                return dict(row) if row else {}
        except Exception as e:
            logger.error(f"会話サマリー取得エラー: {e}")
            return {}
    
    def get_system_stats(self) -> Dict[str, Any]:
        """システム統計を取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 総インタラクション数
                cursor.execute('SELECT COUNT(*) as total_interactions FROM user_interactions')
                total_interactions = cursor.fetchone()[0]
                
                # 知識ギャップ数
                cursor.execute('SELECT COUNT(*) as knowledge_gaps FROM knowledge_gaps')
                knowledge_gaps = cursor.fetchone()[0]
                
                # 学習インサイト数
                cursor.execute('SELECT COUNT(*) as learning_insights FROM learning_insights')
                learning_insights = cursor.fetchone()[0]
                
                # 登録ユーザー数
                cursor.execute('SELECT COUNT(*) as registered_users FROM user_profiles')
                registered_users = cursor.fetchone()[0]
                
                return {
                    'total_interactions': total_interactions,
                    'knowledge_gaps': knowledge_gaps,
                    'learning_insights': learning_insights,
                    'registered_users': registered_users
                }
        except Exception as e:
            logger.error(f"システム統計取得エラー: {e}")
            return {}

# グローバルデータベースインスタンス
db = TaxHackDatabase()
