"""
会話履歴管理システム
ChatGPT風の会話管理機能
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import uuid

@dataclass
class Conversation:
    """会話セッション"""
    id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0
    is_archived: bool = False

@dataclass
class Message:
    """メッセージ"""
    id: str
    conversation_id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None

class ConversationManager:
    """会話履歴管理"""
    
    def __init__(self, db_path: str = "conversations.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """データベース初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    is_archived BOOLEAN DEFAULT FALSE
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
                ON conversations (user_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
                ON messages (conversation_id)
            """)
    
    def create_conversation(self, user_id: str, title: str = None) -> Conversation:
        """新しい会話を作成"""
        conversation_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        if not title:
            title = f"新しい会話 {datetime.now().strftime('%m/%d %H:%M')}"
        
        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            title=title,
            created_at=now,
            updated_at=now
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO conversations 
                (id, user_id, title, created_at, updated_at, message_count, is_archived)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation.id,
                conversation.user_id,
                conversation.title,
                conversation.created_at,
                conversation.updated_at,
                conversation.message_count,
                conversation.is_archived
            ))
        
        return conversation
    
    def add_message(self, conversation_id: str, role: str, content: str, metadata: Dict[str, Any] = None) -> Message:
        """メッセージを追加"""
        message_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        message = Message(
            id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            timestamp=now,
            metadata=metadata
        )
        
        with sqlite3.connect(self.db_path) as conn:
            # メッセージを追加
            conn.execute("""
                INSERT INTO messages 
                (id, conversation_id, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                message.id,
                message.conversation_id,
                message.role,
                message.content,
                message.timestamp,
                json.dumps(metadata) if metadata else None
            ))
            
            # 会話の更新日時とメッセージ数を更新
            conn.execute("""
                UPDATE conversations 
                SET updated_at = ?, message_count = message_count + 1
                WHERE id = ?
            """, (now, conversation_id))
            
            # 最初のユーザーメッセージの場合、タイトルを更新
            if role == 'user':
                message_count = conn.execute("""
                    SELECT COUNT(*) FROM messages 
                    WHERE conversation_id = ? AND role = 'user'
                """, (conversation_id,)).fetchone()[0]
                
                if message_count == 1:
                    # 最初のメッセージからタイトルを生成
                    title = self._generate_title(content)
                    conn.execute("""
                        UPDATE conversations SET title = ? WHERE id = ?
                    """, (title, conversation_id))
        
        return message
    
    def get_conversations(self, user_id: str, limit: int = 50, archived: bool = False) -> List[Conversation]:
        """ユーザーの会話一覧を取得"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM conversations 
                WHERE user_id = ? AND is_archived = ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (user_id, archived, limit))
            
            conversations = []
            for row in cursor.fetchall():
                conversations.append(Conversation(
                    id=row['id'],
                    user_id=row['user_id'],
                    title=row['title'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    message_count=row['message_count'],
                    is_archived=bool(row['is_archived'])
                ))
            
            return conversations
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """特定の会話を取得"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM conversations WHERE id = ?
            """, (conversation_id,))
            
            row = cursor.fetchone()
            if row:
                return Conversation(
                    id=row['id'],
                    user_id=row['user_id'],
                    title=row['title'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    message_count=row['message_count'],
                    is_archived=bool(row['is_archived'])
                )
            return None
    
    def get_messages(self, conversation_id: str) -> List[Message]:
        """会話のメッセージ一覧を取得"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM messages 
                WHERE conversation_id = ?
                ORDER BY timestamp ASC
            """, (conversation_id,))
            
            messages = []
            for row in cursor.fetchall():
                metadata = None
                if row['metadata']:
                    try:
                        metadata = json.loads(row['metadata'])
                    except json.JSONDecodeError:
                        pass
                
                messages.append(Message(
                    id=row['id'],
                    conversation_id=row['conversation_id'],
                    role=row['role'],
                    content=row['content'],
                    timestamp=row['timestamp'],
                    metadata=metadata
                ))
            
            return messages
    
    def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """会話タイトルを更新"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE conversations 
                SET title = ?, updated_at = ?
                WHERE id = ?
            """, (title, datetime.now().isoformat(), conversation_id))
            
            return cursor.rowcount > 0
    
    def archive_conversation(self, conversation_id: str) -> bool:
        """会話をアーカイブ"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE conversations 
                SET is_archived = TRUE, updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), conversation_id))
            
            return cursor.rowcount > 0
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """会話を削除"""
        with sqlite3.connect(self.db_path) as conn:
            # メッセージを削除
            conn.execute("""
                DELETE FROM messages WHERE conversation_id = ?
            """, (conversation_id,))
            
            # 会話を削除
            cursor = conn.execute("""
                DELETE FROM conversations WHERE id = ?
            """, (conversation_id,))
            
            return cursor.rowcount > 0
    
    def search_conversations(self, user_id: str, query: str, limit: int = 20) -> List[Conversation]:
        """会話を検索"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT DISTINCT c.* FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_id = ? AND (
                    c.title LIKE ? OR m.content LIKE ?
                )
                ORDER BY c.updated_at DESC
                LIMIT ?
            """, (user_id, f'%{query}%', f'%{query}%', limit))
            
            conversations = []
            for row in cursor.fetchall():
                conversations.append(Conversation(
                    id=row['id'],
                    user_id=row['user_id'],
                    title=row['title'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    message_count=row['message_count'],
                    is_archived=bool(row['is_archived'])
                ))
            
            return conversations
    
    def get_conversation_stats(self, user_id: str) -> Dict[str, Any]:
        """会話統計を取得"""
        with sqlite3.connect(self.db_path) as conn:
            # 総会話数
            total_conversations = conn.execute("""
                SELECT COUNT(*) FROM conversations WHERE user_id = ?
            """, (user_id,)).fetchone()[0]
            
            # 総メッセージ数
            total_messages = conn.execute("""
                SELECT COUNT(*) FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.user_id = ?
            """, (user_id,)).fetchone()[0]
            
            # 今日の会話数
            today = datetime.now().date().isoformat()
            today_conversations = conn.execute("""
                SELECT COUNT(*) FROM conversations 
                WHERE user_id = ? AND DATE(created_at) = ?
            """, (user_id, today)).fetchone()[0]
            
            # 平均メッセージ数
            avg_messages = total_messages / total_conversations if total_conversations > 0 else 0
            
            return {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "today_conversations": today_conversations,
                "avg_messages_per_conversation": round(avg_messages, 1)
            }
    
    def _generate_title(self, content: str) -> str:
        """メッセージ内容からタイトルを生成"""
        # 簡単なタイトル生成ロジック
        content = content.strip()
        if len(content) <= 30:
            return content
        
        # 最初の30文字 + "..."
        return content[:30] + "..."
    
    def cleanup_old_conversations(self, days: int = 90):
        """古い会話をクリーンアップ"""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # 古いメッセージを削除
            conn.execute("""
                DELETE FROM messages 
                WHERE conversation_id IN (
                    SELECT id FROM conversations 
                    WHERE updated_at < ? AND is_archived = TRUE
                )
            """, (cutoff_date,))
            
            # 古い会話を削除
            cursor = conn.execute("""
                DELETE FROM conversations 
                WHERE updated_at < ? AND is_archived = TRUE
            """, (cutoff_date,))
            
            return cursor.rowcount

# グローバルインスタンス
conversation_manager = ConversationManager()
