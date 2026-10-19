import React, { useState } from 'react';
import {
  Code2,
  Copy,
  Check,
  Globe,
  Sparkles,
  Bot,
  Send,
  Save,
  CheckCircle2,
  ShieldCheck,
  Palette,
} from 'lucide-react';
import { Button } from '../../components/ui/Button';

export const AgencySettingsPage: React.FC = () => {
  // Widget Customization States
  const [assistantName, setAssistantName] = useState('Apex Luxury Concierge');
  const [welcomeGreeting, setWelcomeGreeting] = useState(
    'Welcome to Apex Luxury Properties. How may I assist you with our luxury waterfront villas or Downtown penthouses today?'
  );
  const [accentColor, setAccentColor] = useState('#F97316'); // Default luxury orange
  const [quickPrompts, setQuickPrompts] = useState([
    'Palm Jumeirah Signature Villas',
    'Downtown Sky Residences ROI',
    'Book Private VIP Viewing',
  ]);
  const [newPromptInput, setNewPromptInput] = useState('');
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Agency Whitelist credentials
  const widgetKey = 'wk_live_b21e89f03c4a71d2';
  const allowedDomains = ['apexproperties.ae', 'localhost:5173'];

  const colorOptions = [
    { label: 'Apex Amber (Default)', hex: '#F97316' },
    { label: 'Emerald Mint', hex: '#10B981' },
    { label: 'Royal Gold', hex: '#EAB308' },
    { label: 'Azure Blue', hex: '#3B82F6' },
  ];

  const embedScript = `<script
  src="https://cdn.realestate-ai.com/widget.js"
  data-widget-key="${widgetKey}"
  data-tenant-slug="apex-luxury"
  async>
</script>`;

  const copyToClipboard = (text: string, identifier: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(identifier);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setToastMessage('Widget customization saved & live configuration updated!');
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleAddPrompt = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPromptInput.trim()) return;
    if (quickPrompts.length >= 4) return;
    setQuickPrompts([...quickPrompts, newPromptInput.trim()]);
    setNewPromptInput('');
  };

  const handleRemovePrompt = (indexToRemove: number) => {
    setQuickPrompts(quickPrompts.filter((_, i) => i !== indexToRemove));
  };

  return (
    <div className="space-y-6 sm:space-y-8 max-w-7xl mx-auto">
      {/* Toast Alert */}
      {toastMessage && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/8">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Widget Settings
            </h2>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Persona, greeting, brand accent, and website embed snippet.
          </p>
        </div>

        <Button variant="primary" size="md" onClick={handleSave}>
          <Save className="w-4 h-4 mr-1.5" />
          <span>Save Changes</span>
        </Button>
      </div>

      {/* 2-Column Layout: Controls Form (Left) & Live Widget Preview (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8">
        {/* LEFT COLUMN: Customization Controls (7 Cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Persona & Brand Styling */}
          <div className="p-5 sm:p-6 rounded-xl bg-[#151517] border border-white/8 space-y-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#F97316]" />
              <h3 className="text-sm font-semibold text-white">Assistant Persona & Styling</h3>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                  Assistant Display Name
                </label>
                <input
                  type="text"
                  value={assistantName}
                  onChange={(e) => setAssistantName(e.target.value)}
                  className="w-full px-3.5 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#F97316]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1">
                  Initial Welcome Message
                </label>
                <textarea
                  rows={3}
                  value={welcomeGreeting}
                  onChange={(e) => setWelcomeGreeting(e.target.value)}
                  className="w-full px-3.5 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#F97316]"
                />
                <p className="text-[11px] text-zinc-500 mt-1">
                  Shown automatically to website visitors when opening the chat window.
                </p>
              </div>

              {/* Accent Color Picker */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2 flex items-center gap-1.5">
                  <Palette className="w-3.5 h-3.5 text-zinc-400" />
                  <span>Theme Accent Color</span>
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {colorOptions.map((opt) => (
                    <button
                      key={opt.hex}
                      type="button"
                      onClick={() => setAccentColor(opt.hex)}
                      className={`p-2 rounded-lg border text-xs flex items-center gap-2 transition-all cursor-pointer ${
                        accentColor === opt.hex
                          ? 'bg-white/10 border-white/40 text-white font-semibold'
                          : 'bg-[#0B0B0D] border-white/5 text-zinc-400 hover:text-white'
                      }`}
                    >
                      <span
                        className="w-3.5 h-3.5 rounded-full shrink-0 shadow-sm"
                        style={{ backgroundColor: opt.hex }}
                      />
                      <span className="truncate">{opt.label.split(' ')[0]}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Suggested Quick Prompts */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
                  Suggested Visitor Quick Prompts (Max 4)
                </label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {quickPrompts.map((prompt, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1.5 text-xs text-zinc-300 bg-[#0B0B0D] border border-white/10 px-2.5 py-1 rounded-full"
                    >
                      <span>{prompt}</span>
                      <button
                        type="button"
                        onClick={() => handleRemovePrompt(idx)}
                        className="text-zinc-500 hover:text-rose-400 ml-1 text-xs"
                      >
                        &times;
                      </button>
                    </span>
                  ))}
                </div>

                {quickPrompts.length < 4 && (
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={newPromptInput}
                      onChange={(e) => setNewPromptInput(e.target.value)}
                      placeholder="Add quick question chip..."
                      className="flex-1 px-3 py-1.5 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#F97316]"
                    />
                    <Button variant="secondary" size="sm" onClick={handleAddPrompt}>
                      Add
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Embed Tag & Domain Whitelist */}
          <div className="p-6 rounded-xl bg-[#151517] border border-white/8 space-y-4">
            <div className="flex items-center gap-2">
              <Code2 className="w-4 h-4 text-[#F97316]" />
              <h3 className="text-sm font-semibold text-white">Embed Script & Domain Whitelist</h3>
            </div>

            {/* Allowed Domains */}
            <div className="p-3 bg-[#0B0B0D] border border-white/5 rounded-lg space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-zinc-400 flex items-center gap-1.5">
                  <Globe className="w-3.5 h-3.5 text-emerald-400" /> Whitelisted Origins:
                </span>
                <span className="text-emerald-400 text-[11px] font-medium flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" /> Origin Checked
                </span>
              </div>
              <div className="flex items-center gap-1.5 font-mono text-[11px] text-zinc-300 flex-wrap">
                {allowedDomains.map((dom) => (
                  <span key={dom} className="bg-white/5 px-2 py-0.5 rounded border border-white/5">
                    {dom}
                  </span>
                ))}
              </div>
            </div>

            {/* Script Tag */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                HTML Embed Code
              </label>
              <div className="relative">
                <pre className="p-3 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs font-mono text-zinc-300 overflow-x-auto whitespace-pre-wrap break-all">
                  {embedScript}
                </pre>
                <div className="absolute top-2 right-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => copyToClipboard(embedScript, 'script')}
                  >
                    {copiedKey === 'script' ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400 mr-1" />
                    ) : (
                      <Copy className="w-3.5 h-3.5 text-zinc-400 mr-1" />
                    )}
                    <span>{copiedKey === 'script' ? 'Copied' : 'Copy'}</span>
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Live Interactive Widget Preview (5 Cols) */}
        <div className="lg:col-span-5 space-y-3.5 max-w-md mx-auto lg:max-w-none w-full">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[#F97316]" />
              Live Widget Interactive Preview
            </span>
            <span className="text-[11px] text-zinc-500 font-mono">1:1 Scale</span>
          </div>

          {/* Mock Floating Chat Window Container */}
          <div className="w-full bg-[#151517] border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col h-[520px]">
            {/* Widget Header with Luxury Brown Glow & Custom Accent */}
            <div
              className="p-4 border-b border-white/10 flex items-center justify-between"
              style={{
                background: `linear-gradient(135deg, ${accentColor}22 0%, #151517 80%)`,
              }}
            >
              <div className="flex items-center gap-2.5">
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-white text-xs shadow-md"
                  style={{ backgroundColor: accentColor }}
                >
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-white tracking-tight leading-none">
                    {assistantName}
                  </h4>
                  <span className="text-[10px] text-emerald-400 flex items-center gap-1 mt-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Online • Grounded RAG
                  </span>
                </div>
              </div>
              <div className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
            </div>

            {/* Widget Messages Stream */}
            <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-[#0B0B0D]/50 text-xs">
              {/* Assistant Welcome Message */}
              <div className="flex flex-col items-start space-y-1">
                <span className="text-[10px] text-zinc-500 ml-1">{assistantName}</span>
                <div className="p-3 rounded-2xl rounded-tl-sm bg-[#1E1E21] border border-white/8 text-zinc-200 leading-relaxed max-w-[90%]">
                  {welcomeGreeting}
                </div>
              </div>

              {/* Sample Visitor Inquiry */}
              <div className="flex flex-col items-end space-y-1">
                <span className="text-[10px] text-zinc-500 mr-1">Visitor</span>
                <div
                  className="p-3 rounded-2xl rounded-tr-sm text-white leading-relaxed max-w-[85%] shadow-sm"
                  style={{ backgroundColor: accentColor }}
                >
                  Do you have any 4-bedroom beachfront villas available on Palm Jumeirah?
                </div>
              </div>

              {/* Sample Grounded Reply */}
              <div className="flex flex-col items-start space-y-1">
                <span className="text-[10px] text-zinc-500 ml-1">{assistantName}</span>
                <div className="p-3 rounded-2xl rounded-tl-sm bg-[#1E1E21] border border-white/8 text-zinc-200 leading-relaxed max-w-[90%]">
                  Yes, we have Signature Villas on Frond N featuring 4 & 5-bedroom layouts with private beach access and infinity pools.
                </div>
              </div>

              {/* Quick Prompts Chips */}
              <div className="pt-2 flex flex-wrap gap-1.5">
                {quickPrompts.map((prompt, i) => (
                  <span
                    key={i}
                    className="text-[10px] px-2 py-1 rounded-full border border-white/10 bg-[#151517] text-zinc-300 font-medium hover:border-white/30 cursor-pointer"
                  >
                    {prompt}
                  </span>
                ))}
              </div>
            </div>

            {/* Widget Mock Input Bar */}
            <div className="p-3 border-t border-white/8 bg-[#151517] flex items-center gap-2">
              <input
                readOnly
                type="text"
                placeholder="Ask about properties, pricing, layouts..."
                className="flex-1 px-3 py-2 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-zinc-400 focus:outline-none"
              />
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center text-white shrink-0 shadow-sm cursor-pointer"
                style={{ backgroundColor: accentColor }}
              >
                <Send className="w-3.5 h-3.5" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
