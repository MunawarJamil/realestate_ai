/**
 * RealEstate AI Embeddable Chat Widget - Complete Client Runtime & SSE Engine
 */

import { WidgetApiClient } from './api';
import { createWidgetContainer, WidgetElements } from './container';
import { renderMarkdown } from './markdown';
import { WidgetStorage } from './storage';
import { ChatMessage, RealEstateAIWindowAPI, WidgetConfig, WidgetState } from './types';
import { WidgetSocketClient } from './socket'; // # 12c HITL

class RealEstateWidgetController {
  private config: WidgetConfig;
  private elements: WidgetElements | null = null;
  private storage: WidgetStorage;
  private api: WidgetApiClient;
  private socketClient: WidgetSocketClient | null = null; // # 12c HITL


  private activeStreamingBubble: HTMLDivElement | null = null; // # 12b HITL
  private accumulatedStreamContent = ''; // # 12b HITL
  private state: WidgetState;
  private currentStreamController: AbortController | null = null;

  constructor(config: WidgetConfig) {
    this.config = config;
    this.storage = new WidgetStorage(config.widgetKey);
    this.api = new WidgetApiClient(config.apiUrl, config.widgetKey);
    this.state = {
      isOpen: false,
      isLoading: false,
      isStreaming: false,
      status: 'ai', // # 12b HITL
      session: null,
      conversationId: null,
      messages: [],
      error: null,
    };
  }

  public mount(): void {
    if (this.elements) {
      return;
    }

    this.elements = createWidgetContainer(this.config);
    this.bindEvents();

    // Check for cached session in localStorage
    const cachedSession = this.storage.getSession();
    const cachedConvId = this.storage.getConversationId();
    if (cachedSession && cachedConvId) {
      this.state.session = cachedSession;
      this.state.conversationId = cachedConvId;
      if (cachedSession.tenant_name && this.elements.headerTitle) {
        this.elements.headerTitle.textContent = cachedSession.tenant_name;
      }
      // # 12b HITL - Eagerly establish WebSocket connection
      this.initWebSocket();
    }
  }

  private bindEvents(): void {
    if (!this.elements) return;

    // Toggle on launcher click
    this.elements.launcher.addEventListener('click', () => {
      this.toggle();
    });

    // Close on close button click
    this.elements.closeBtn.addEventListener('click', () => {
      this.close();
    });

    // Input text validation
    this.elements.input.addEventListener('input', () => {
      if (!this.elements) return;
      const hasText = this.elements.input.value.trim().length > 0;
      this.elements.sendBtn.disabled = !hasText || this.state.isStreaming;
    });

    // Enter key to send
    this.elements.input.addEventListener('keydown', (e: KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!this.elements?.sendBtn.disabled) {
          this.handleSendMessage();
        }
      }
    });

    // Send button click
    this.elements.sendBtn.addEventListener('click', () => {
      this.handleSendMessage();
    });

    // Escape key to close
    window.addEventListener('keydown', (e: KeyboardEvent) => {
      if (e.key === 'Escape' && this.state.isOpen) {
        this.close();
      }
    });
  }

  public async open(): Promise<void> {
    if (!this.elements) return;
    this.state.isOpen = true;
    this.elements.window.classList.add('re-open');
    this.elements.input.focus();

    // Ensure session is active, WS is connected, and past messages are rendered
    await this.ensureSession();
  }

  public close(): void {
    if (!this.elements) return;
    this.state.isOpen = false;
    this.elements.window.classList.remove('re-open');
  }

  public toggle(): void {
    if (this.state.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  public getState(): Readonly<WidgetState> {
    return { ...this.state };
  }

  /**
   * Ensures a valid visitor session and conversation are ready
   */
  private async ensureSession(): Promise<boolean> {
    // # 12b HITL - If session and conversationId are already in memory, ensure WS is connected and messages loaded
    if (this.state.session && this.state.conversationId) {
      this.initWebSocket();
      if (this.state.messages.length === 0) {
        await this.loadMessagesHistory(this.state.session.visitor_token, this.state.conversationId);
      }
      return true;
    }

    this.showTypingIndicator();

    try {
      // 1. Init or resume visitor session
      const existingSession = this.storage.getSession();
      const requestedId = existingSession?.visitor_id || undefined;
      const session = await this.api.initSession(requestedId);

      this.state.session = session;
      if (this.elements?.headerTitle && session.tenant_name) {
        this.elements.headerTitle.textContent = session.tenant_name;
      }

      // 2. Check for existing conversation or create a new one
      let convId = this.storage.getConversationId();
      if (!convId) {
        const conv = await this.api.createConversation(
          session.visitor_token,
          'Website Visitor Inquiry'
        );
        convId = conv.id;
        this.storage.saveSession(session, convId);
      }

      this.state.conversationId = convId;

      // 3. Load past messages if any, or render initial greeting
      await this.loadMessagesHistory(session.visitor_token, convId);

      // # 12b HITL - Establish Real-time WebSocket Connection
      this.initWebSocket();

      return true;
    } catch (err: unknown) {
      this.hideTypingIndicator();
      console.error('[RealEstateAI Widget] Session initialization error', err);
      const errMsg = err instanceof Error ? err.message : 'Unable to connect to assistant';
      this.appendErrorMessage(errMsg);
      return false;
    }
  }

  // # 12b HITL - Load past messages history into widget
  private async loadMessagesHistory(visitorToken: string, convId: string): Promise<void> {
    this.hideTypingIndicator();
    try {
      const history = await this.api.listMessages(visitorToken, convId);
      if (history.length > 0) {
        for (const msg of history) {
          if (!this.state.messages.some((m) => m.id === msg.id)) {
            this.appendMessage(msg, true);
          }
        }
      } else {
        const greeting =
          this.config.greeting ||
          `Hello! Welcome to ${this.state.session?.tenant_name || 'our real estate agency'}. How can I assist you with properties or pricing today?`;
        this.appendMessage(
          {
            id: 'greeting',
            role: 'assistant',
            sender_type: 'ai',
            content: greeting,
          },
          true
        );
      }
    } catch (err) {
      console.warn('[RealEstateAI Widget] Failed to load messages history:', err);
    }
  }

  // # 12c HITL - Socket.IO Real-Time Gateway
  private initWebSocket(): void {
    if (!this.state.session || !this.state.conversationId) return;
    if (this.socketClient && this.socketClient.isConnected()) return;

    if (this.socketClient) {
      this.socketClient.disconnect();
    }

    this.socketClient = new WidgetSocketClient(
      this.config.apiUrl,
      this.state.session.visitor_token,
      this.state.conversationId,
      {
        onMessage: (msg: ChatMessage) => {
          this.hideTypingIndicator();
          this.state.isStreaming = false;
          if (this.elements) {
            this.elements.sendBtn.disabled = this.elements.input.value.trim().length === 0;
            this.elements.input.focus();
          }

          // Avoid duplicate rendering of visitor's own messages
          if (msg.role === 'user' && msg.sender_type === 'visitor') {
            return;
          }

          // Avoid duplicate message if already in state
          if (this.state.messages.some((m) => m.id === msg.id)) {
            return;
          }

          this.appendMessage(msg, true);
        },
        onError: (err: Error) => {
          console.warn('[RealEstateAI Widget] Socket.IO notice:', err);
        },
      }
    );

    this.socketClient.connect();
  }


  // # 12b HITL - Header Live Status Badge
  private updateStatusBadge(status: 'ai' | 'handoff_requested' | 'human_active' | 'resolved'): void {
    if (!this.elements) return;
    this.state.status = status;

    if (status === 'human_active') {
      this.elements.headerSubtitle.innerHTML = `
        <span class="re-online-indicator" style="background:#3B82F6;box-shadow:0 0 8px rgba(59,130,246,0.6);"></span>
        Live Property Advisor • Connected
      `;
    } else if (status === 'handoff_requested') {
      this.elements.headerSubtitle.innerHTML = `
        <span class="re-online-indicator" style="background:#EAB308;box-shadow:0 0 8px rgba(234,179,8,0.6);"></span>
        Connecting to Advisor...
      `;
    } else if (status === 'resolved') {
      this.elements.headerSubtitle.innerHTML = `
        <span class="re-online-indicator" style="background:#6B7280;"></span>
        Inquiry Resolved
      `;
    } else {
      this.elements.headerSubtitle.innerHTML = `
        <span class="re-online-indicator"></span>
        ${this.config.subtitle || 'Online • Instant Answers'}
      `;
    }
  }

  /**
   * Handles user sending a chat message
   */
  private async handleSendMessage(): Promise<void> {
    if (!this.elements || this.state.isStreaming) return;

    const text = this.elements.input.value.trim();
    if (!text) return;

    // Clear input and disable button
    this.elements.input.value = '';
    this.elements.sendBtn.disabled = true;

    // Ensure session is active
    const ready = await this.ensureSession();
    if (!ready || !this.state.session || !this.state.conversationId) {
      this.appendErrorMessage('Session expired or unavailable. Please reload the page.');
      return;
    }

    // Append user message bubble
    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      role: 'user',
      sender_type: 'visitor',
      content: text,
    };
    this.appendMessage(userMsg, true);

    // Prepare assistant message bubble
    this.state.isStreaming = true;
    this.showTypingIndicator();
    this.activeStreamingBubble = null;
    this.accumulatedStreamContent = '';

    // # 12c HITL - Real-Time Socket.IO Dispatch
    if (this.socketClient && this.socketClient.isConnected()) {
      const dispatched = this.socketClient.sendMessage(text);
      if (dispatched) {
        this.hideTypingIndicator();
        this.state.isStreaming = false;
        if (this.elements) {
          this.elements.sendBtn.disabled = this.elements.input.value.trim().length === 0;
          this.elements.input.focus();
        }
        return;
      }
    }



    // Fallback to HTTP SSE Stream
    let assistantBubble: HTMLDivElement | null = null;
    let accumulatedContent = '';

    const token = this.state.session.visitor_token;
    const convId = this.state.conversationId;

    this.currentStreamController = this.api.streamChat(
      token,
      convId,
      text,
      // onToken
      (chunk: string) => {
        if (!assistantBubble) {
          this.hideTypingIndicator();
          assistantBubble = this.createMessageBubble('assistant');
        }
        accumulatedContent += chunk;
        assistantBubble.innerHTML = renderMarkdown(accumulatedContent);
        this.scrollToBottom();
      },
      // onDone
      () => {
        this.hideTypingIndicator();
        this.state.isStreaming = false;
        if (this.elements) {
          this.elements.sendBtn.disabled = this.elements.input.value.trim().length === 0;
          this.elements.input.focus();
        }
        if (accumulatedContent) {
          this.state.messages.push({
            id: `ast_${Date.now()}`,
            role: 'assistant',
            sender_type: 'ai',
            content: accumulatedContent,
          });
        }
      },
      // onError
      (err: Error) => {
        this.hideTypingIndicator();
        this.state.isStreaming = false;
        if (this.elements) {
          this.elements.sendBtn.disabled = this.elements.input.value.trim().length === 0;
        }
        console.error('[RealEstateAI Widget] Stream error', err);
        if (!assistantBubble) {
          this.appendErrorMessage(err.message || 'Stream interrupted. Please try again.');
        }
      }
    );
  }

  private appendMessage(msg: ChatMessage, pushToState = true): void {
    if (pushToState) {
      this.state.messages.push(msg);
    }
    const bubble = this.createMessageBubble(msg.role, msg.sender_type);
    if (msg.sender_type === 'agent') {
      bubble.innerHTML = `
        <div style="font-size:11px;font-weight:600;color:#60A5FA;margin-bottom:4px;display:flex;align-items:center;gap:4px;">
          <span>👤</span> Licensed Property Advisor
        </div>
        <div>${renderMarkdown(msg.content)}</div>
      `;
    } else if (msg.sender_type === 'system' || msg.role === 'system') {
      bubble.textContent = msg.content;
    } else {
      bubble.innerHTML =
        msg.role === 'assistant' ? renderMarkdown(msg.content) : this.escapeText(msg.content);
    }
    this.scrollToBottom();
  }

  private createMessageBubble(role: 'user' | 'assistant' | 'system', senderType?: string): HTMLDivElement {
    const bubble = document.createElement('div');
    if (senderType === 'agent') {
      bubble.className = 're-msg re-msg-agent';
    } else if (senderType === 'system' || role === 'system') {
      bubble.className = 're-msg re-msg-system';
    } else {
      bubble.className = `re-msg re-msg-${role}`;
    }
    this.elements?.messagesContainer.appendChild(bubble);
    return bubble;
  }

  private appendErrorMessage(text: string): void {
    const bubble = document.createElement('div');
    bubble.className = 're-msg re-msg-assistant';
    bubble.style.borderColor = 'rgba(239, 68, 68, 0.4)';
    bubble.style.color = '#FCA5A5';
    bubble.textContent = `⚠️ ${text}`;
    this.elements?.messagesContainer.appendChild(bubble);
    this.scrollToBottom();
  }

  private showTypingIndicator(): void {
    this.hideTypingIndicator();
    const typing = document.createElement('div');
    typing.id = 're-active-typing';
    typing.className = 're-typing';
    typing.innerHTML = `
      <span class="re-typing-dot"></span>
      <span class="re-typing-dot"></span>
      <span class="re-typing-dot"></span>
    `;
    this.elements?.messagesContainer.appendChild(typing);
    this.scrollToBottom();
  }

  private hideTypingIndicator(): void {
    const existing = this.elements?.shadow.getElementById('re-active-typing');
    if (existing) {
      existing.remove();
    }
  }

  private scrollToBottom(): void {
    if (!this.elements) return;
    this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
  }

  private escapeText(raw: string): string {
    const p = document.createElement('p');
    p.textContent = raw;
    return p.innerHTML;
  }
}

let activeController: RealEstateWidgetController | null = null;

function detectScriptConfig(): WidgetConfig | null {
  // 1. Global config object
  if (window.RealEstateAIConfig?.widgetKey) {
    return {
      widgetKey: window.RealEstateAIConfig.widgetKey,
      apiUrl: window.RealEstateAIConfig.apiUrl || window.location.origin,
      ...window.RealEstateAIConfig,
    } as WidgetConfig;
  }

  // 2. Embedded <script data-widget-key="..."> (supports both classic and module scripts)
  const currentScript =
    (document.currentScript as HTMLScriptElement | null) ||
    (document.querySelector('script[data-widget-key]') as HTMLScriptElement | null);

  if (currentScript) {
    const key = currentScript.getAttribute('data-widget-key');
    if (key) {
      return {
        widgetKey: key,
        apiUrl: currentScript.getAttribute('data-api-url') || window.location.origin,
        title: currentScript.getAttribute('data-title') || undefined,
        subtitle: currentScript.getAttribute('data-subtitle') || undefined,
        greeting: currentScript.getAttribute('data-greeting') || undefined,
        placeholder: currentScript.getAttribute('data-placeholder') || undefined,
        position:
          (currentScript.getAttribute('data-position') as 'bottom-right' | 'bottom-left') ||
          'bottom-right',
      };
    }
  }

  return null;
}

export function init(config?: Partial<WidgetConfig>): RealEstateAIWindowAPI {
  const detected = detectScriptConfig();
  const effectiveConfig: WidgetConfig = {
    widgetKey: config?.widgetKey || detected?.widgetKey || '',
    apiUrl: config?.apiUrl || detected?.apiUrl || window.location.origin,
    ...detected,
    ...config,
  };

  if (!effectiveConfig.widgetKey) {
    console.warn('[RealEstateAI Widget] Missing required widgetKey configuration.');
  }

  activeController = new RealEstateWidgetController(effectiveConfig);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => activeController?.mount());
  } else {
    activeController.mount();
  }

  const api: RealEstateAIWindowAPI = {
    init,
    open: () => activeController?.open(),
    close: () => activeController?.close(),
    toggle: () => activeController?.toggle(),
    getState: () => activeController?.getState() ?? ({} as Readonly<WidgetState>),
  };

  window.RealEstateAI = api;
  return api;
}

// Auto-run if script attributes or global config are present
const autoConfig = detectScriptConfig();
if (autoConfig) {
  init(autoConfig);
} else {
  window.RealEstateAI = {
    init,
    open: () => activeController?.open(),
    close: () => activeController?.close(),
    toggle: () => activeController?.toggle(),
    getState: () => activeController?.getState() ?? ({} as Readonly<WidgetState>),
  };
}

export default init;
