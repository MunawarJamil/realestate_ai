/**
 * RealEstate AI Embeddable Chat Widget - Complete Client Runtime & SSE Engine
 */

import { WidgetApiClient } from './api';
import { createWidgetContainer, WidgetElements } from './container';
import { renderMarkdown } from './markdown';
import { WidgetStorage } from './storage';
import { ChatMessage, RealEstateAIWindowAPI, WidgetConfig, WidgetState } from './types';

class RealEstateWidgetController {
  private config: WidgetConfig;
  private elements: WidgetElements | null = null;
  private storage: WidgetStorage;
  private api: WidgetApiClient;
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
    if (cachedSession) {
      this.state.session = cachedSession;
      this.state.conversationId = cachedConvId;
      if (cachedSession.tenant_name && this.elements.headerTitle) {
        this.elements.headerTitle.textContent = cachedSession.tenant_name;
      }
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

    // If chat is empty, initialize session and load/greeting
    if (this.state.messages.length === 0) {
      await this.ensureSession();
    }
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
    if (this.state.session && this.state.conversationId) {
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
      const history = await this.api.listMessages(session.visitor_token, convId);
      this.hideTypingIndicator();

      if (history.length > 0) {
        for (const msg of history) {
          this.appendMessage(msg, false);
        }
      } else {
        const greeting =
          this.config.greeting ||
          `Hello! Welcome to ${session.tenant_name || 'our real estate agency'}. How can I assist you with properties or pricing today?`;
        this.appendMessage(
          {
            id: 'greeting',
            role: 'assistant',
            content: greeting,
          },
          false
        );
      }

      return true;
    } catch (err: unknown) {
      this.hideTypingIndicator();
      console.error('[RealEstateAI Widget] Session initialization error', err);
      const errMsg = err instanceof Error ? err.message : 'Unable to connect to assistant';
      this.appendErrorMessage(errMsg);
      return false;
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
      content: text,
    };
    this.appendMessage(userMsg, true);

    // Prepare assistant message bubble
    this.state.isStreaming = true;
    this.showTypingIndicator();

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
    const bubble = this.createMessageBubble(msg.role);
    bubble.innerHTML =
      msg.role === 'assistant' ? renderMarkdown(msg.content) : this.escapeText(msg.content);
    this.scrollToBottom();
  }

  private createMessageBubble(role: 'user' | 'assistant' | 'system'): HTMLDivElement {
    const bubble = document.createElement('div');
    bubble.className = `re-msg re-msg-${role}`;
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
