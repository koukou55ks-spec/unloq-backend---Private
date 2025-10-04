/**
 * 対話型学習UI - ニュースフィードの代わりに対話スターターを表示
 */

// 対話スターターを読み込む
async function loadConversationStarter() {
    try {
        const response = await fetch('http://127.0.0.1:8003/conversation-starter', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_profile: userProfile || {},
                interests: userProfile?.interests || []
            })
        });

        const data = await response.json();

        if (data.success && data.conversation_starter) {
            displayConversationStarter(data.conversation_starter);
        }
    } catch (error) {
        console.error('対話スターター読み込みエラー:', error);
        displayDefaultStarter();
    }
}

// 対話スターターを表示
function displayConversationStarter(starter) {
    const container = document.getElementById('conversationStarterContainer');
    if (!container) return;

    const html = `
        <div class="conversation-starter-card">
            <div class="card-header">
                <div class="card-icon">💭</div>
                <h3 class="card-title">${starter.topic_name}</h3>
            </div>

            <div class="conversation-prompt">
                ${formatPromptText(starter.conversation_prompt)}
            </div>

            <div class="deep-dive-section" style="margin-top: 1.5rem;">
                <h4 style="font-size: 0.9rem; font-weight: 600; margin-bottom: 0.5rem; color: #fbbf24;">
                    🔍 一緒に考えてみましょう
                </h4>
                <ul class="question-list">
                    ${starter.deep_dive_questions.map(q => `
                        <li class="question-item" onclick="askQuestion('${escapeHtml(q)}')">
                            ${q}
                        </li>
                    `).join('')}
                </ul>
            </div>

            <div class="action-section" style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid rgba(255,255,255,0.1);">
                <p style="font-size: 0.875rem; color: #d1d5db; margin-bottom: 0.75rem;">
                    <strong>次のアクション:</strong>
                </p>
                <p style="font-size: 0.875rem; color: #9ca3af;">
                    ${starter.user_action}
                </p>
                <button
                    class="start-conversation-btn"
                    onclick="startConversation('${escapeHtml(starter.topic_name)}')"
                    style="margin-top: 1rem;">
                    この話題について対話を始める
                </button>
            </div>
        </div>
    `;

    container.innerHTML = html;
}

// デフォルトスターター表示
function displayDefaultStarter() {
    const container = document.getElementById('conversationStarterContainer');
    if (!container) return;

    container.innerHTML = `
        <div class="conversation-starter-card">
            <div class="card-header">
                <div class="card-icon">🎯</div>
                <h3 class="card-title">あなたの財務目標</h3>
            </div>

            <div class="conversation-prompt">
                <p>まず、あなたの財務目標について教えてください。</p>

                <div style="margin-top: 1rem; padding: 1rem; background: rgba(251, 191, 36, 0.1); border-radius: 8px;">
                    <p style="margin-bottom: 0.5rem;"><strong>問いかけ:</strong></p>
                    <ul style="padding-left: 1.5rem; margin-top: 0.5rem;">
                        <li>1年後、3年後、10年後、それぞれどんな状態になっていたいですか？</li>
                        <li>「お金の不安」で一番大きいのは何ですか？</li>
                        <li>もし今、税金や社会保険料が半分になったら、何をしますか？</li>
                    </ul>
                </div>

                <p style="margin-top: 1rem;">一緒に、あなただけの財務戦略を作りましょう。</p>
            </div>

            <button
                class="start-conversation-btn"
                onclick="startConversation('財務目標')"
                style="margin-top: 1.5rem;">
                対話を始める
            </button>
        </div>
    `;
}

// テキストフォーマット
function formatPromptText(text) {
    return text
        .replace(/\*\*問いかけ\*\*:/g, '<div class="question-box"><strong>問いかけ:</strong>')
        .replace(/\n\n/g, '</div><p>')
        .replace(/\n/g, '<br>');
}

// HTMLエスケープ
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/'/g, '&#39;');
}

// 質問をクリックしたときの処理
function askQuestion(question) {
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.value = question;
        chatInput.focus();
    }
}

// 対話を開始
function startConversation(topic) {
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.value = `${topic}について教えてください`;
        chatInput.focus();

        // 自動送信
        const sendBtn = document.getElementById('sendBtn');
        if (sendBtn) {
            sendBtn.click();
        }
    }
}

// 対話型API呼び出し
async function sendConversationMessage(message) {
    try {
        const response = await fetch('http://127.0.0.1:8003/ask-conversation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: message,
                user_id: userId,
                user_profile: userProfile || {},
                conversation_history: conversationHistory.slice(-5) // 直近5件の履歴
            })
        });

        const data = await response.json();

        if (data.success) {
            return {
                answer: data.answer,
                conversation_style: data.conversation_style,
                encourages_thinking: data.encourages_thinking
            };
        }

        throw new Error('対話処理に失敗しました');

    } catch (error) {
        console.error('対話エラー:', error);
        throw error;
    }
}

// スタイルを追加
const conversationStyles = `
<style>
.conversation-starter-card {
    background: linear-gradient(135deg, rgba(251, 191, 36, 0.1), rgba(139, 92, 246, 0.1));
    border: 1px solid rgba(251, 191, 36, 0.3);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}

.card-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.card-icon {
    font-size: 2rem;
}

.card-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: #fbbf24;
}

.conversation-prompt {
    color: #d1d5db;
    line-height: 1.8;
    font-size: 1rem;
}

.conversation-prompt p {
    margin-bottom: 1rem;
}

.question-box {
    background: rgba(251, 191, 36, 0.15);
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
    border-left: 3px solid #fbbf24;
}

.question-list {
    list-style: none;
    padding: 0;
}

.question-item {
    padding: 0.75rem 1rem;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    margin-bottom: 0.5rem;
    cursor: pointer;
    transition: all 0.2s;
    border-left: 3px solid transparent;
}

.question-item:hover {
    background: rgba(251, 191, 36, 0.1);
    border-left-color: #fbbf24;
    transform: translateX(4px);
}

.start-conversation-btn {
    width: 100%;
    padding: 0.875rem 1.5rem;
    background: linear-gradient(135deg, #fbbf24, #f59e0b);
    color: #0a0a0f;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.2s;
}

.start-conversation-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 16px rgba(251, 191, 36, 0.3);
}

.action-section {
    font-size: 0.875rem;
}
</style>
`;

// スタイルを挿入
if (!document.getElementById('conversation-styles')) {
    const styleElement = document.createElement('div');
    styleElement.id = 'conversation-styles';
    styleElement.innerHTML = conversationStyles;
    document.head.appendChild(styleElement);
}

// ページロード時に対話スターターをロード
document.addEventListener('DOMContentLoaded', () => {
    // プロフィール保存後にも再読み込み
    const originalSaveProfile = window.saveProfile;
    window.saveProfile = function(event) {
        if (originalSaveProfile) {
            originalSaveProfile(event);
        }
        // プロフィール保存後に対話スターターを更新
        setTimeout(loadConversationStarter, 500);
    };
});
