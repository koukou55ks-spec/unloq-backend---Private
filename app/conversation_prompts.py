"""
対話型学習のためのプロンプト生成システム
ニュース配信ではなく、トレンドトピックをベースにした対話を生成
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

class ConversationPromptGenerator:
    """ユーザー情報とトレンドから対話プロンプトを生成"""

    def __init__(self):
        self.trending_topics = self._get_trending_topics()

    def _get_trending_topics(self) -> List[Dict[str, Any]]:
        """現在のトレンドトピック（手動更新でOK、APIコスト削減）"""
        return [
            {
                "topic": "2024年インボイス制度の影響",
                "keywords": ["インボイス", "消費税", "免税事業者", "2割特例"],
                "target_users": ["フリーランス", "個人事業主", "小規模事業者"],
                "why": "多くのフリーランスが消費税納税を初めて経験している"
            },
            {
                "topic": "新NISA 2024年スタート",
                "keywords": ["新NISA", "つみたて投資枠", "成長投資枠", "年1800万円"],
                "target_users": ["会社員", "20代", "30代", "投資初心者"],
                "why": "非課税枠が大幅拡大、生涯1800万円の資産形成チャンス"
            },
            {
                "topic": "住宅ローン減税の改正",
                "keywords": ["住宅ローン控除", "借入限度額", "認定住宅", "0.7%"],
                "target_users": ["会社員", "30代", "40代", "住宅購入検討者"],
                "why": "控除率引き下げ、環境性能で借入限度額に差"
            },
            {
                "topic": "副業の確定申告",
                "keywords": ["副業", "雑所得", "事業所得", "20万円ルール"],
                "target_users": ["会社員", "副業者"],
                "why": "副業人口増加、事業所得と雑所得の区分が厳格化"
            },
            {
                "topic": "電子帳簿保存法の義務化",
                "keywords": ["電帳法", "電子取引", "検索要件", "タイムスタンプ"],
                "target_users": ["個人事業主", "フリーランス", "経理担当"],
                "why": "2024年1月から完全義務化、対応しないと青色取消リスク"
            },
            {
                "topic": "iDeCo拠出限度額の見直し",
                "keywords": ["iDeCo", "拠出限度額", "企業型DC", "併用"],
                "target_users": ["会社員", "40代", "50代"],
                "why": "企業型DCとの併用条件緩和、老後資金準備の選択肢拡大"
            },
            {
                "topic": "ふるさと納税の経済圏戦略",
                "keywords": ["ふるさと納税", "楽天", "PayPay", "ポイント還元"],
                "target_users": ["会社員", "全年代"],
                "why": "返礼品+ポイント還元で実質負担をマイナスにできる"
            },
            {
                "topic": "個人事業税の対象業種拡大",
                "keywords": ["個人事業税", "法定業種", "290万円控除"],
                "target_users": ["フリーランス", "個人事業主"],
                "why": "気づかず未納になっているケース多数"
            }
        ]

    def generate_conversation_starter(
        self,
        user_profile: Dict[str, Any],
        user_interests: List[str] = None
    ) -> Dict[str, Any]:
        """ユーザーに最適な対話スターターを生成"""

        # ユーザーに関連するトピックをマッチング
        relevant_topics = self._match_topics(user_profile, user_interests)

        if not relevant_topics:
            return self._generate_default_starter(user_profile)

        # 最も関連性の高いトピックを選択
        topic = relevant_topics[0]

        return {
            "topic_name": topic["topic"],
            "conversation_prompt": self._create_socratic_prompt(topic, user_profile),
            "deep_dive_questions": self._create_follow_up_questions(topic, user_profile),
            "user_action": self._suggest_action(topic, user_profile)
        }

    def _match_topics(
        self,
        user_profile: Dict[str, Any],
        user_interests: List[str] = None
    ) -> List[Dict[str, Any]]:
        """ユーザープロフィールとトピックのマッチング"""

        occupation = user_profile.get("occupation", "")
        age_group = user_profile.get("ageGroup", "")
        goals = user_profile.get("financialGoal", "")
        interests = user_interests or user_profile.get("interests", [])

        matched = []

        for topic in self.trending_topics:
            score = 0

            # 職業マッチ
            if occupation in topic["target_users"]:
                score += 3

            # 年代マッチ
            if age_group in topic["target_users"]:
                score += 2

            # キーワードマッチ
            for keyword in topic["keywords"]:
                if keyword in goals or keyword in " ".join(interests):
                    score += 1

            if score > 0:
                matched.append({"topic": topic, "score": score})

        # スコア順にソート
        matched.sort(key=lambda x: x["score"], reverse=True)

        return [m["topic"] for m in matched]

    def _create_socratic_prompt(
        self,
        topic: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> str:
        """ニュース見出し風の短いプロンプトを生成"""

        occupation = user_profile.get("occupation", "あなた")
        income = user_profile.get("incomeLevel", "")

        # ニュース見出し風（短く、クリックを促す）
        prompts = {
            "2024年インボイス制度の影響": f"💼 {occupation}、インボイス登録で本当に損してる？",
            "新NISA 2024年スタート": f"💰 年1800万円の非課税枠、{occupation}はどう使う？",
            "住宅ローン減税の改正": f"🏠 住宅ローン控除、{income}でいくら戻る？",
            "副業の確定申告": f"📊 副業20万円以下でも申告必要？知らないと損",
            "電子帳簿保存法の義務化": f"📱 2024年完全義務化、対応してないと青色取消？",
            "iDeCo拠出限度額の見直し": f"🏦 {occupation}のiDeCo、月いくらまで積める？",
            "ふるさと納税の経済圏戦略": f"🎁 ふるさと納税で実質負担をマイナスにする裏技",
            "個人事業税の対象業種拡大": f"⚠️ {occupation}は個人事業税の対象？290万円控除"
        }

        return prompts.get(
            topic["topic"],
            f"💡 {topic['topic']}について知っておくべきこと"
        )

    def _create_follow_up_questions(
        self,
        topic: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> List[str]:
        """深堀り用の追加質問を生成"""

        questions_map = {
            "2024年インボイス制度の影響": [
                "あなたの取引先は法人が多いですか、それとも個人が多いですか？",
                "年間売上がいくらになったら、課税事業者になるべきだと思いますか？",
                "2割特例は2026年までの期間限定です。その後の戦略は考えていますか？"
            ],
            "新NISA 2024年スタート": [
                "現在の貯蓄のうち、何%を投資に回せますか？",
                "インデックス投資と個別株、それぞれのリスクとリターンを理解していますか？",
                "老後2000万円問題、新NISAだけで解決できると思いますか？"
            ],
            "副業の確定申告": [
                "副業の年間売上と経費、把握していますか？",
                "領収書や請求書、きちんと保存していますか？",
                "青色申告のメリット、3つ挙げられますか？"
            ]
        }

        return questions_map.get(topic["topic"], [
            f"{topic['topic']}について、もっと詳しく知りたいポイントはありますか？"
        ])

    def _suggest_action(
        self,
        topic: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> str:
        """具体的なアクションを提案"""

        actions_map = {
            "2024年インボイス制度の影響": "まず、あなたの取引先に「適格請求書が必要か」確認してみましょう。その結果を教えてください。",
            "新NISA 2024年スタート": "まず、月にいくら積立できるか、家計を見直してみましょう。金額が分かったら教えてください。",
            "副業の確定申告": "まず、今年の副業収入を概算してみましょう。20万円を超えそうですか？"
        }

        return actions_map.get(
            topic["topic"],
            f"{topic['topic']}について、次に知りたいことを教えてください。"
        )

    def _generate_default_starter(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """デフォルトの対話スターター"""

        return {
            "topic_name": "あなたの財務目標",
            "conversation_prompt": """
まず、あなたの財務目標について教えてください。

**問いかけ**:
- 1年後、3年後、10年後、それぞれどんな状態になっていたいですか？
- 「お金の不安」で一番大きいのは何ですか？
- もし今、税金や社会保険料が半分になったら、何をしますか？

一緒に、あなただけの財務戦略を作りましょう。
            """,
            "deep_dive_questions": [
                "現在の年収と、理想の年収を教えてください",
                "貯蓄、投資、保険、それぞれ月にいくら使っていますか？",
                "税金について、一番分からないことは何ですか？"
            ],
            "user_action": "まず、あなたの現状を整理してみましょう。収入と支出を教えてください。"
        }

    def generate_contextual_prompt(
        self,
        user_message: str,
        user_profile: Dict[str, Any],
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """ユーザーメッセージに対する対話型プロンプトを生成"""

        age = user_profile.get("ageGroup", "")
        occupation = user_profile.get("occupation", "")
        income = user_profile.get("incomeLevel", "")
        goal = user_profile.get("financialGoal", "")

        return f"""
あなたは、ユーザーの本質的な理解を深めるパーソナルCFOです。
情報を一方的に提供するのではなく、ソクラテス式対話で思考を促してください。

【ユーザーの背景】
- 年齢: {age}
- 職業: {occupation}
- 収入: {income}
- 財務目標: {goal}

【ユーザーの質問】
{user_message}

【対話の方針】
1. **Why（なぜ）を問う**: 表面的な答えではなく、本質を理解させる
2. **ユーザーの状況で考えさせる**: 「{occupation}のあなたの場合は...」
3. **比較して気づかせる**: 選択肢を提示し、判断させる
4. **具体例で体感させる**: {income}の人のリアルな数字を使う
5. **富裕層の思考を共有**: 「富裕層はこう考える。なぜなら...」
6. **次の一歩を促す**: 「〜についてもっと知りたいですか？」

【回答フォーマット】
## この質問の本質

[Whyから説明]

## {occupation}のあなたの場合...

◆ 現状の推測
[ユーザーの背景から推測]

◆ 選択肢と考察
1. [選択肢A] → [メリット・デメリット]
2. [選択肢B] → [メリット・デメリット]

## 具体例で体感

[{income}レベルでの計算例]

**問いかけ**: どちらを選びますか？なぜですか？

## 富裕層の思考プロセス

[同じ状況で富裕層がどう判断するか、理由を含めて]

## 次の一歩

[具体的なアクション + さらなる問いかけ]

※ 最後は必ず問いかけで終わり、対話を継続させてください
        """


# シングルトンインスタンス
conversation_prompt_generator = ConversationPromptGenerator()
