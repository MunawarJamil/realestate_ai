/**
 * Scoped Shadow DOM CSS Styles and Unified Design System Tokens
 */

import { WidgetConfig } from './types';

export function getWidgetStyles(config?: Partial<WidgetConfig>): string {
  const isLeft = config?.position === 'bottom-left';
  const posStyle = isLeft
    ? 'left: 20px; right: auto;'
    : 'right: 20px; left: auto;';

  return `
    :host {
      --bg: #0B0B0D;
      --surface: #151517;
      --surface-2: #1E1E21;
      --surface-hover: #27272A;
      --brown-glow: linear-gradient(135deg, #3A1F10 0%, #0B0B0D 100%);
      --accent: ${config?.primaryColor || '#F97316'};
      --accent-hover: #EA580C;
      --accent-glow: rgba(249, 115, 22, 0.25);
      --text: #FFFFFF;
      --text-muted: #A1A1AA;
      --border: rgba(255, 255, 255, 0.08);
      --border-focus: rgba(249, 115, 22, 0.5);
      --shadow-lg: 0 18px 48px rgba(0, 0, 0, 0.55), 0 0 0 1px rgba(255, 255, 255, 0.08);
      --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Inter', system-ui, sans-serif;
      --radius-sm: 8px;
      --radius-md: 14px;
      --radius-lg: 20px;
      --radius-full: 9999px;
      --transition-smooth: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);

      display: block !important;
      position: fixed !important;
      bottom: 20px !important;
      ${posStyle}
      z-index: 2147483647 !important;
      font-family: var(--font-family);
      color: var(--text);
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      box-sizing: border-box;
    }

    .re-wrapper {
      position: relative;
      display: block;
    }

    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    /* Floating Launcher Button */
    .re-launcher {
      position: relative;
      width: 60px;
      height: 60px;
      border-radius: var(--radius-full);
      background: var(--accent);
      color: #FFFFFF;
      border: 1px solid rgba(255, 255, 255, 0.15);
      box-shadow: 0 8px 24px var(--accent-glow), 0 4px 12px rgba(0, 0, 0, 0.4);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: var(--transition-smooth);
      outline: none;
      user-select: none;
      -webkit-tap-highlight-color: transparent;
    }

    .re-launcher:hover {
      background: var(--accent-hover);
      transform: translateY(-2px) scale(1.05);
      box-shadow: 0 12px 30px var(--accent-glow), 0 6px 16px rgba(0, 0, 0, 0.5);
    }

    .re-launcher:active {
      transform: translateY(0) scale(0.96);
    }

    .re-launcher svg {
      width: 28px;
      height: 28px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
      transition: var(--transition-smooth);
    }

    /* Chat Window Container */
    .re-window {
      position: absolute;
      bottom: 74px;
      ${isLeft ? 'left: 0;' : 'right: 0;'}
      width: 380px;
      max-width: calc(100vw - 32px);
      height: 580px;
      max-height: calc(100vh - 100px);
      background: var(--bg);
      border-radius: var(--radius-lg);
      border: 1px solid var(--border);
      box-shadow: var(--shadow-lg);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      opacity: 0;
      pointer-events: none;
      transform: translateY(16px) scale(0.96);
      transform-origin: ${isLeft ? 'bottom left' : 'bottom right'};
      transition: opacity 0.22s ease, transform 0.26s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .re-window.re-open {
      opacity: 1;
      pointer-events: auto;
      transform: translateY(0) scale(1);
    }

    /* Window Header */
    .re-header {
      background: var(--brown-glow);
      padding: 16px 18px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: relative;
    }

    .re-header-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .re-avatar {
      width: 36px;
      height: 36px;
      border-radius: var(--radius-full);
      background: var(--surface-2);
      border: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--accent);
      flex-shrink: 0;
    }

    .re-avatar svg {
      width: 20px;
      height: 20px;
    }

    .re-header-text h3 {
      font-size: 14px;
      font-weight: 600;
      color: var(--text);
      line-height: 1.2;
    }

    .re-header-text p {
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 2px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .re-online-indicator {
      width: 7px;
      height: 7px;
      border-radius: var(--radius-full);
      background: #22C55E;
      box-shadow: 0 0 8px rgba(34, 197, 94, 0.6);
      display: inline-block;
    }

    .re-close-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      width: 30px;
      height: 30px;
      border-radius: var(--radius-sm);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: var(--transition-smooth);
    }

    .re-close-btn:hover {
      color: var(--text);
      background: rgba(255, 255, 255, 0.08);
    }

    /* Messages Area */
    .re-messages {
      flex: 1;
      padding: 18px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: var(--bg);
      scroll-behavior: smooth;
    }

    .re-messages::-webkit-scrollbar {
      width: 5px;
    }

    .re-messages::-webkit-scrollbar-thumb {
      background: var(--surface-2);
      border-radius: var(--radius-full);
    }

    /* Message Bubbles */
    .re-msg {
      max-width: 82%;
      padding: 11px 14px;
      font-size: 13.5px;
      line-height: 1.45;
      border-radius: var(--radius-md);
      animation: reFadeInUp 0.25s ease-out;
      word-break: break-word;
    }

    .re-msg-user {
      align-self: flex-end;
      background: var(--accent);
      color: #FFFFFF;
      border-bottom-right-radius: 4px;
    }

    .re-msg-assistant {
      align-self: flex-start;
      background: var(--surface);
      color: var(--text);
      border: 1px solid var(--border);
      border-bottom-left-radius: 4px;
    }

    /* # 12b HITL - Human Broker & System Event Bubbles */
    .re-msg-agent {
      align-self: flex-start;
      background: #131E30;
      color: #F1F5F9;
      border: 1px solid rgba(59, 130, 246, 0.35);
      border-bottom-left-radius: 4px;
      box-shadow: 0 2px 10px rgba(59, 130, 246, 0.08);
    }

    .re-msg-system {
      align-self: center;
      background: rgba(255, 255, 255, 0.05);
      color: #CBD5E1;
      font-size: 11px;
      font-weight: 500;
      padding: 5px 14px;
      border-radius: var(--radius-full);
      border: 1px solid rgba(255, 255, 255, 0.1);
      max-width: 90%;
      text-align: center;
      margin: 6px 0;
      letter-spacing: 0.1px;
      line-height: 1.4;
    }

    /* Typing Indicator */
    .re-typing {
      display: flex;
      align-items: center;
      gap: 5px;
      padding: 12px 16px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      border-bottom-left-radius: 4px;
      align-self: flex-start;
      width: fit-content;
    }

    .re-typing-dot {
      width: 6px;
      height: 6px;
      background: var(--text-muted);
      border-radius: var(--radius-full);
      animation: rePulse 1.2s infinite;
    }

    .re-typing-dot:nth-child(2) { animation-delay: 0.2s; }
    .re-typing-dot:nth-child(3) { animation-delay: 0.4s; }

    /* Input Footer */
    .re-footer {
      padding: 12px 16px;
      background: var(--surface);
      border-top: 1px solid var(--border);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .re-input {
      flex: 1;
      background: var(--surface-2);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 10px 14px;
      color: var(--text);
      font-family: inherit;
      font-size: 13.5px;
      outline: none;
      transition: var(--transition-smooth);
    }

    .re-input:focus {
      border-color: var(--border-focus);
      box-shadow: 0 0 0 2px var(--accent-glow);
    }

    .re-input::placeholder {
      color: var(--text-muted);
    }

    .re-send-btn {
      width: 38px;
      height: 38px;
      border-radius: var(--radius-md);
      background: var(--accent);
      color: #FFFFFF;
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: var(--transition-smooth);
      flex-shrink: 0;
    }

    .re-send-btn:hover {
      background: var(--accent-hover);
    }

    .re-send-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    /* Keyframe Animations */
    @keyframes reFadeInUp {
      from {
        opacity: 0;
        transform: translateY(6px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @keyframes rePulse {
      0%, 80%, 100% { transform: scale(0.8); opacity: 0.4; }
      40% { transform: scale(1.15); opacity: 1; }
    }
  `;
}
