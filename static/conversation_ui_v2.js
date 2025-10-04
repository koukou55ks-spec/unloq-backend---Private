/**
 * 対話型学習UI v2 - ニュース見出し風の短いプロンプト
 */

// 対話スターターを読み込む
async function loadConversationStarter() {
    console.log('[Conversation UI] Loading conversation starter...');

    try {
        // userProfileを取得（localStorage or global）
        let profile = {};
        try {
            const stored = localStorage.getItem('userProfile');
            profile = stored ? JSON.parse(stored) : {};
        } catch (e) {
            console.warn('[Conversation UI] Could not load user profile:', e);
        }

        console.log('[Conversation UI] User profile:', profile);

        const response = await fetch('http://127.0.0.1:8003/conversation-starter', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_profile: profile,
                interests: profile?.interests || []
            })
        });

        const data = await response.json();
        console.log('[Conversation UI] API response:', data);

        if (data.success && data.conversation_starter) {
            displayConversationStarter(data.conversation_starter);
        } else {
            console.warn('[Conversation UI] No conversation starter in response');
            displayDefaultStarter();
        }
    } catch (error) {
        console.error('[Conversation UI] Error loading conversation starter:', error);
        displayDefaultStarter();
    }
}

// 対話スターターを表示（ニュース見出し風）
function displayConversationStarter(starter) {
    console.log('[Conversation UI] Displaying conversation starter:', starter);
    const container = document.getElementById('conversationStarterContainer');
    if (!container) {
        console.error('[Conversation UI] Container not found: conversationStarterContainer');
        return;
    }
    console.log('[Conversation UI] Container found, rendering...');

    const html = `
        <div class="conversation-headline" onclick="startConversation('${escapeHtml(starter.topic_name)}')">
            <div class="headline-text">${starter.conversation_prompt}</div>
            <div class="headline-hint">
                <i class="fas fa-arrow-right"></i> クリックして対話を開始
            </div>
        </div>

        <div class="quick-questions">
            <div class="quick-questions-title">💭 気になることから聞いてみる</div>
            ${starter.deep_dive_questions.map(q => `
                <div class="quick-question-item" onclick="askQuestion('${escapeHtml(q)}')">
                    ${q}
                </div>
            `).join('')}
        </div>
    `;

    container.innerHTML = html;
}

// デフォルトスターター表示
function displayDefaultStarter() {
    console.log('[Conversation UI] Displaying default starter');
    const container = document.getElementById('conversationStarterContainer');
    if (!container) {
        console.error('[Conversation UI] Container not found for default starter');
        return;
    }

    container.innerHTML = `
        <div class="conversation-headline" onclick="startConversation('財務目標')">
            <div class="headline-text">🎯 あなたの財務目標を一緒に考えてみませんか？</div>
            <div class="headline-hint">
                <i class="fas fa-arrow-right"></i> クリックして対話を開始
            </div>
        </div>
    `;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/'/g, '&#39;');
}

function askQuestion(question) {
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.value = question;
        chatInput.focus();
    }
}

function startConversation(topic) {
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.value = `${topic}について教えてください`;
        chatInput.focus();
        const sendBtn = document.getElementById('sendBtn');
        if (sendBtn) sendBtn.click();
    }
}

// スタイル追加
const conversationStyles = `
<style>
.conversation-headline {
    background: linear-gradient(135deg, rgba(251, 191, 36, 0.15), rgba(139, 92, 246, 0.15));
    border-left: 4px solid #fbbf24;
    padding: 1.25rem;
    margin-bottom: 1.5rem;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
}

.conversation-headline:hover {
    background: linear-gradient(135deg, rgba(251, 191, 36, 0.25), rgba(139, 92, 246, 0.25));
    transform: translateX(4px);
    border-left-width: 6px;
}

.headline-text {
    font-size: 1.125rem;
    font-weight: 600;
    color: #fbbf24;
    line-height: 1.6;
    margin-bottom: 0.5rem;
}

.headline-hint {
    font-size: 0.75rem;
    color: #9ca3af;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.conversation-headline:hover .headline-hint i {
    transform: translateX(4px);
}

.quick-questions {
    margin-top: 1rem;
}

.quick-questions-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: #d1d5db;
    margin-bottom: 0.75rem;
}

.quick-question-item {
    padding: 0.75rem 1rem;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 6px;
    margin-bottom: 0.5rem;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 0.875rem;
    color: #d1d5db;
    border-left: 2px solid transparent;
}

.quick-question-item:hover {
    background: rgba(251, 191, 36, 0.1);
    border-left-color: #fbbf24;
    transform: translateX(4px);
    color: #fbbf24;
}
</style>
`;

if (!document.getElementById('conversation-styles-v2')) {
    const styleElement = document.createElement('div');
    styleElement.id = 'conversation-styles-v2';
    styleElement.innerHTML = conversationStyles;
    document.head.appendChild(styleElement);
}

// ページロード時（メインスクリプトから呼び出されるため、自動実行は削除）
console.log('[Conversation UI v2] Script loaded and ready');
