/**
 * Shadow DOM Container and DOM Element Factory
 */

import { getWidgetStyles } from './styles';
import { WidgetConfig } from './types';

export interface WidgetElements {
  host: HTMLElement;
  shadow: ShadowRoot;
  launcher: HTMLButtonElement;
  window: HTMLDivElement;
  closeBtn: HTMLButtonElement;
  messagesContainer: HTMLDivElement;
  input: HTMLInputElement;
  sendBtn: HTMLButtonElement;
  headerTitle: HTMLHeadingElement;
  headerSubtitle: HTMLParagraphElement;
}

const LAUNCHER_ICON_SVG = `
  <svg viewBox="0 0 24 24">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
  </svg>
`;

const CLOSE_ICON_SVG = `
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
  </svg>
`;

const SEND_ICON_SVG = `
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <line x1="22" y1="2" x2="11" y2="13"></line>
    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
  </svg>
`;

const BOT_AVATAR_SVG = `
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="3" y="11" width="18" height="10" rx="2"></rect>
    <circle cx="12" cy="5" r="2"></circle>
    <path d="M12 7v4"></path>
    <line x1="8" y1="16" x2="8" y2="16"></line>
    <line x1="16" y1="16" x2="16" y2="16"></line>
  </svg>
`;

export function createWidgetContainer(config: WidgetConfig): WidgetElements {
  // 1. Remove any existing host element
  const existing = document.getElementById('realestate-ai-widget-host');
  if (existing) {
    existing.remove();
  }

  // 2. Create the outer host element
  const host = document.createElement('div');
  host.id = 'realestate-ai-widget-host';
  host.style.position = 'fixed';
  host.style.bottom = '20px';
  if (config.position === 'bottom-left') {
    host.style.left = '20px';
    host.style.right = 'auto';
  } else {
    host.style.right = '20px';
    host.style.left = 'auto';
  }
  host.style.zIndex = '2147483647';

  // 3. Attach open Shadow Root for style isolation
  const shadow = host.attachShadow({ mode: 'open' });

  // 4. Inject scoped CSS
  const styleEl = document.createElement('style');
  styleEl.textContent = getWidgetStyles(config);
  shadow.appendChild(styleEl);

  // 5. Build Widget DOM
  const wrapper = document.createElement('div');
  wrapper.className = 're-wrapper';
  wrapper.innerHTML = `
    <!-- Floating Launcher -->
    <button class="re-launcher" id="re-launcher" aria-label="Open Real Estate Chat">
      ${LAUNCHER_ICON_SVG}
    </button>

    <!-- Chat Window -->
    <div class="re-window" id="re-window" role="dialog" aria-modal="true">
      <!-- Header -->
      <div class="re-header">
        <div class="re-header-info">
          <div class="re-avatar">
            ${BOT_AVATAR_SVG}
          </div>
          <div class="re-header-text">
            <h3 id="re-header-title">${config.title || 'Real Estate Assistant'}</h3>
            <p id="re-header-subtitle">
              <span class="re-online-indicator"></span>
              ${config.subtitle || 'Online • Instant Answers'}
            </p>
          </div>
        </div>
        <button class="re-close-btn" id="re-close-btn" aria-label="Close Chat">
          ${CLOSE_ICON_SVG}
        </button>
      </div>

      <!-- Messages Scroll Area -->
      <div class="re-messages" id="re-messages">
        <!-- Messages rendered here dynamically -->
      </div>

      <!-- Input Footer -->
      <div class="re-footer">
        <input 
          type="text" 
          class="re-input" 
          id="re-input" 
          placeholder="${config.placeholder || 'Ask about properties, pricing...'}"
          autocomplete="off"
        />
        <button class="re-send-btn" id="re-send-btn" aria-label="Send Message" disabled>
          ${SEND_ICON_SVG}
        </button>
      </div>
    </div>
  `;

  shadow.appendChild(wrapper);
  document.body.appendChild(host);

  return {
    host,
    shadow,
    launcher: shadow.getElementById('re-launcher') as HTMLButtonElement,
    window: shadow.getElementById('re-window') as HTMLDivElement,
    closeBtn: shadow.getElementById('re-close-btn') as HTMLButtonElement,
    messagesContainer: shadow.getElementById('re-messages') as HTMLDivElement,
    input: shadow.getElementById('re-input') as HTMLInputElement,
    sendBtn: shadow.getElementById('re-send-btn') as HTMLButtonElement,
    headerTitle: shadow.getElementById('re-header-title') as HTMLHeadingElement,
    headerSubtitle: shadow.getElementById('re-header-subtitle') as HTMLParagraphElement,
  };
}
