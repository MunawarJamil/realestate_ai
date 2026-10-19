import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Search,
  CheckCircle2,
  Send,
  MapPin,
  Phone,
  Sparkles,
  Bot,
  User,
  ChevronLeft,
  RefreshCw,
  Plus,
  AlertCircle,
  MessageSquare,
  UserCheck,
  Radio,
} from 'lucide-react';
import type { Conversation, ConversationStatus, Message, BackendConversationSummary } from '../../types/agency';
import type { BackendConversation, BackendMessage } from '../../api/client';
import { Button } from '../../components/ui/Button';
import { apiClient, ApiError } from '../../api/client';
import { AgentWebSocketClient } from '../../api/agentWs'; // # 12b HITL

function mapBackendConversation(
  conv: BackendConversation,
  messages: BackendMessage[] = []
): Conversation {
  const meta = conv.metadata || {};
  return {
    id: conv.id,
    visitor_name:
      (meta.visitor_name as string) || conv.title || `Visitor ${conv.id.slice(0, 6)}`,
    visitor_location:
      (meta.visitor_location as string) || (meta.location as string) || 'Online Visitor',
    visitor_email: (meta.visitor_email as string) || undefined,
    visitor_phone: (meta.visitor_phone as string) || undefined,
    intent: (meta.intent as string) || 'Property Inquiry',
    budget: (meta.budget as string) || 'AED 2M - 5M',
    property_interest: (meta.property_interest as string) || conv.title || 'Luxury Inquiry',
    status: (conv.status as ConversationStatus) || 'ai', // # 12b HITL
    assigned_agent_id: conv.assigned_agent_id, // # 12b HITL
    started_at: new Date(conv.created_at).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    }),
    last_message_at: new Date(conv.updated_at || conv.created_at).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    }),
    tags: Array.isArray(meta.tags) ? (meta.tags as string[]) : ['Live Web Widget'],
    messages: messages.map(mapBackendMessage),
  };
}

function mapBackendMessage(msg: BackendMessage): Message {
  return {
    id: msg.id,
    role: msg.role === 'user' ? 'user' : msg.role === 'system' ? 'system' : 'assistant',
    sender_type: msg.sender_type, // # 12b HITL
    content: msg.content,
    created_at: new Date(msg.created_at).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    }),
  };
}

export const AgencyConversationsPage: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | ConversationStatus>('all');
  const [replyText, setReplyText] = useState('');
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [showMobileList, setShowMobileList] = useState(false);

  // # 12b HITL - Real-time Agent WebSocket & AI Summary States
  const [activeSummary, setActiveSummary] = useState<BackendConversationSummary | null>(null);
  const [isLoadingSummary, setIsLoadingSummary] = useState(false);
  const [showSummaryDrawer, setShowSummaryDrawer] = useState(false);
  const [agentWsConnected, setAgentWsConnected] = useState(false);
  const [liveHandoffAlert, setLiveHandoffAlert] = useState<{ conversation_id: string; snippet: string } | null>(null);
  const agentWsRef = useRef<AgentWebSocketClient | null>(null);

  // Real-time SSE streaming state
  const [isStreaming, setIsStreaming] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const showNotification = (msg: string) => {
    setActionNotice(msg);
    setTimeout(() => setActionNotice(null), 3500);
  };

  // 1. Fetch Conversations List
  const fetchConversations = useCallback(async () => {
    setIsLoadingList(true);
    setErrorBanner(null);
    try {
      const res = await apiClient.agency.listConversations({ limit: 50 });
      const mapped = res.items.map((c) => mapBackendConversation(c, []));
      setConversations(mapped);

      // Select first conversation if none selected
      if (mapped.length > 0 && !selectedId) {
        setSelectedId(mapped[0].id);
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorBanner(`Failed to load conversations (${err.status}): ${err.message}`);
      } else {
        setErrorBanner('Could not reach backend API server at http://localhost:8000.');
      }
    } finally {
      setIsLoadingList(false);
    }
  }, [selectedId]);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  // # 12b HITL - Connect Agency Agent WebSocket for real-time handoff alerts & live broker messages
  useEffect(() => {
    const ws = new AgentWebSocketClient({
      onConnected: () => {
        setAgentWsConnected(true);
      },
      onDisconnected: () => {
        setAgentWsConnected(false);
      },
      onHandoffAlert: (alert) => {
        setLiveHandoffAlert({
          conversation_id: alert.conversation_id,
          snippet: alert.snippet,
        });
        showNotification(`🚨 Live Visitor Alert: ${alert.snippet}`);
        fetchConversations();
      },
      onStatusChange: (data) => {
        setConversations((prev) =>
          prev.map((c) =>
            c.id === data.conversation_id
              ? {
                  ...c,
                  status: data.status as ConversationStatus,
                  assigned_agent_id: data.assigned_agent_id,
                }
              : c
          )
        );
      },
      onMessage: (msg) => {
        setConversations((prev) =>
          prev.map((c) => {
            if (c.id === msg.conversation_id) {
              const mapped = mapBackendMessage(msg);
              const exists = c.messages.some((m) => m.id === msg.id);
              if (exists) return c;
              return {
                ...c,
                last_message_at: mapped.created_at,
                messages: [...c.messages, mapped],
              };
            }
            return c;
          })
        );
        setTimeout(scrollToBottom, 60);
      },
      onError: (err) => {
        console.warn('[RealEstateAI Agent WS] Notice:', err);
      },
    });

    ws.connect();
    agentWsRef.current = ws;

    return () => {
      ws.disconnect();
    };
  }, [fetchConversations]);

  // 2. Fetch Messages for Selected Conversation
  const loadMessages = useCallback(async (convId: string) => {
    setIsLoadingMessages(true);
    try {
      const msgs = await apiClient.agency.listMessages(convId, { limit: 100 });
      const mappedMsgs = msgs.map(mapBackendMessage);

      setConversations((prev) =>
        prev.map((c) => (c.id === convId ? { ...c, messages: mappedMsgs } : c))
      );
      setTimeout(scrollToBottom, 80);
    } catch (err: unknown) {
      console.error('Failed to load messages for conversation:', err);
    } finally {
      setIsLoadingMessages(false);
    }
  }, []);

  useEffect(() => {
    if (selectedId) {
      loadMessages(selectedId);
      // Reset summary drawer when switching conversations
      setActiveSummary(null);
      setShowSummaryDrawer(false);
    }
  }, [selectedId, loadMessages]);

  const selectedConv = conversations.find((c) => c.id === selectedId) || null;

  const filteredConversations = conversations.filter((c) => {
    const matchesSearch =
      c.visitor_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.intent.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.property_interest.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = statusFilter === 'all' || c.status === statusFilter;
    return matchesSearch && matchesFilter;
  });

  // # 12b HITL - Claim Conversation (Human Takeover)
  const handleClaimConversation = async () => {
    if (!selectedConv) return;
    try {
      await apiClient.agency.claimConversation(selectedConv.id);
      setConversations((prev) =>
        prev.map((c) => (c.id === selectedConv.id ? { ...c, status: 'human_active' } : c))
      );
      showNotification('You have taken live ownership of this conversation.');
      loadMessages(selectedConv.id);
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Claim failed';
      alert(`Error claiming conversation: ${msg}`);
    }
  };

  // # 12b HITL - Release Conversation Back to AI
  const handleReleaseConversation = async () => {
    if (!selectedConv) return;
    try {
      await apiClient.agency.releaseConversation(selectedConv.id);
      setConversations((prev) =>
        prev.map((c) => (c.id === selectedConv.id ? { ...c, status: 'ai', assigned_agent_id: null } : c))
      );
      showNotification('Conversation returned to AI Assistant.');
      loadMessages(selectedConv.id);
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Release failed';
      alert(`Error releasing conversation: ${msg}`);
    }
  };

  // # 12b HITL - Mark Conversation Resolved
  const handleResolveConversation = async () => {
    if (!selectedConv) return;
    try {
      await apiClient.agency.resolveConversation(selectedConv.id);
      setConversations((prev) =>
        prev.map((c) => (c.id === selectedConv.id ? { ...c, status: 'resolved' } : c))
      );
      showNotification('Conversation marked as resolved.');
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Resolve failed';
      alert(`Error resolving conversation: ${msg}`);
    }
  };

  // # 12b HITL - Fetch Real-time AI Context Summary
  const handleFetchSummary = async () => {
    if (!selectedConv) return;
    setIsLoadingSummary(true);
    setShowSummaryDrawer(true);
    try {
      const res = await apiClient.agency.getConversationSummary(selectedConv.id);
      setActiveSummary(res);
    } catch (err: unknown) {
      console.error('Summary fetch error:', err);
      showNotification('AI context summary currently unavailable.');
    } finally {
      setIsLoadingSummary(false);
    }
  };

  // 3. Create a New Conversation Inquiry
  const handleCreateNewConversation = async () => {
    try {
      const newConv = await apiClient.agency.createConversation({
        title: 'Luxury Villa Inquiry',
        metadata: {
          visitor_name: 'VIP Client',
          visitor_location: 'Dubai, UAE',
          intent: 'Investment / Purchase',
          budget: 'AED 8,500,000',
          property_interest: 'Palm Jumeirah Signature Villa',
          status: 'ai',
          tags: ['Dashboard Test'],
        },
      });

      const mapped = mapBackendConversation(newConv, []);
      setConversations((prev) => [mapped, ...prev]);
      setSelectedId(mapped.id);
      showNotification('New inquiry thread created in PostgreSQL!');
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to create conversation';
      alert(`Error creating conversation: ${msg}`);
    }
  };

  // 4. Send Message (Live Human Agent or AI Stream Test)
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyText.trim() || !selectedConv || isStreaming) return;

    const messageContent = replyText.trim();
    setReplyText('');

    const timestampStr = new Date().toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });

    // # 12b HITL - If in Human Active mode, send live broker message
    if (selectedConv.status === 'human_active') {
      const tempAgentMsgId = `agt-${Date.now()}`;
      const agentMsg: Message = {
        id: tempAgentMsgId,
        role: 'user', // UI right alignment
        sender_type: 'agent',
        content: messageContent,
        created_at: timestampStr,
      };

      setConversations((prev) =>
        prev.map((c) =>
          c.id === selectedConv.id
            ? {
                ...c,
                last_message_at: timestampStr,
                messages: [...c.messages, agentMsg],
              }
            : c
        )
      );
      setTimeout(scrollToBottom, 40);

      // Prefer WebSocket dispatch
      if (agentWsRef.current?.isConnected()) {
        const ok = agentWsRef.current.sendMessage(selectedConv.id, messageContent);
        if (ok) return;
      }

      // Fallback to REST
      try {
        await apiClient.agency.sendMessage(selectedConv.id, messageContent);
      } catch (err: unknown) {
        console.error('Failed to send agent message:', err);
        showNotification('Failed to deliver message to visitor.');
      }
      return;
    }

    // Otherwise, simulate/test AI assistant streaming reply
    const tempUserMsgId = `usr-${Date.now()}`;
    const tempAssistantMsgId = `ast-${Date.now()}`;

    const userMessage: Message = {
      id: tempUserMsgId,
      role: 'user',
      content: messageContent,
      created_at: timestampStr,
    };

    const emptyAssistantMessage: Message = {
      id: tempAssistantMsgId,
      role: 'assistant',
      content: '',
      created_at: timestampStr,
      grounded_sources: ['Qdrant Knowledge Chunks'],
    };

    // Optimistically update conversation state
    setConversations((prev) =>
      prev.map((c) =>
        c.id === selectedConv.id
          ? {
              ...c,
              last_message_at: timestampStr,
              messages: [...c.messages, userMessage, emptyAssistantMessage],
            }
          : c
      )
    );

    setTimeout(scrollToBottom, 40);
    setIsStreaming(true);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      let accumulatedText = '';

      await apiClient.agency.streamMessage(selectedConv.id, messageContent, {
        signal: abortController.signal,
        onToken: (token: string) => {
          accumulatedText += token;
          setConversations((prev) =>
            prev.map((c) =>
              c.id === selectedConv.id
                ? {
                    ...c,
                    messages: c.messages.map((m) =>
                      m.id === tempAssistantMsgId
                        ? { ...m, content: accumulatedText }
                        : m
                    ),
                  }
                : c
            )
          );
          scrollToBottom();
        },
        onDone: () => {
          setIsStreaming(false);
          abortControllerRef.current = null;
        },
        onError: (err: Error) => {
          console.error('SSE Stream error:', err);
          setIsStreaming(false);
          setConversations((prev) =>
            prev.map((c) =>
              c.id === selectedConv.id
                ? {
                    ...c,
                    messages: c.messages.map((m) =>
                      m.id === tempAssistantMsgId
                        ? {
                            ...m,
                            content:
                              m.content ||
                              'Sorry, an error occurred while streaming the assistant reply.',
                          }
                        : m
                    ),
                  }
                : c
            )
          );
        },
      });
    } catch {
      setIsStreaming(false);
    }
  };

  return (
    <div className="h-[calc(100dvh-10.5rem)] min-h-[480px] flex flex-col space-y-3 sm:space-y-4 max-w-7xl mx-auto mb-4">
      {/* Toast Alert */}
      {actionNotice && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs flex items-center gap-2 animate-in fade-in shrink-0">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{actionNotice}</span>
        </div>
      )}

      {/* # 12b HITL - Live Handoff Alert Banner */}
      {liveHandoffAlert && (
        <div className="p-3 bg-amber-500/15 border border-amber-500/40 rounded-xl text-amber-300 text-xs flex items-center justify-between gap-3 animate-pulse shrink-0">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Live Visitor Handoff Requested:</strong> "{liveHandoffAlert.snippet}"
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setSelectedId(liveHandoffAlert.conversation_id);
                setLiveHandoffAlert(null);
              }}
              className="px-2.5 py-1 bg-amber-500 text-black font-semibold rounded-lg text-xs hover:bg-amber-400 cursor-pointer"
            >
              Take Over
            </button>
            <button
              onClick={() => setLiveHandoffAlert(null)}
              className="text-zinc-400 hover:text-white px-1 text-xs cursor-pointer"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Backend Error Alert */}
      {errorBanner && (
        <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-300 text-xs flex items-center justify-between gap-2 shrink-0">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>{errorBanner}</span>
          </div>
          <Button variant="ghost" size="sm" onClick={() => fetchConversations()}>
            <span>Retry</span>
          </Button>
        </div>
      )}

      {/* 2-Pane Split Inbox */}
      <div className="flex-1 min-h-0 bg-[#151517] border border-white/8 rounded-2xl overflow-hidden flex relative shadow-lg">
        {/* LEFT PANE: Conversation List */}
        <div
          className={`${
            showMobileList ? 'flex' : 'hidden'
          } md:flex w-full md:w-64 lg:w-72 border-r border-white/8 flex-col bg-[#0F0F12] shrink-0 h-full`}
        >
          {/* Search, Action & Filter Header */}
          <div className="p-3 sm:p-3.5 border-b border-white/8 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-semibold text-white uppercase tracking-wider">
                  Inquiries
                </span>
                <span
                  title={agentWsConnected ? 'Agent Real-time Gateway Connected' : 'Connecting to Real-time Gateway...'}
                  className="text-[10px] text-zinc-500 flex items-center gap-1 font-mono"
                >
                  <Radio className={`w-3 h-3 ${agentWsConnected ? 'text-emerald-400 animate-pulse' : 'text-zinc-600'}`} />
                  {agentWsConnected ? 'Live' : 'Off'}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={fetchConversations}
                  disabled={isLoadingList}
                  title="Refresh conversations"
                  className="p-1 rounded text-zinc-400 hover:text-white cursor-pointer"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isLoadingList ? 'animate-spin' : ''}`} />
                </button>
                <button
                  onClick={handleCreateNewConversation}
                  title="Create new inquiry thread"
                  className="p-1 rounded bg-[#F97316]/10 text-[#F97316] hover:bg-[#F97316]/20 cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search visitor chats..."
                className="w-full pl-8 pr-3 py-1.5 bg-[#0B0B0D] border border-white/10 rounded-lg text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#F97316]"
              />
            </div>

            {/* # 12b HITL - Status Filter Pills */}
            <div className="flex items-center gap-1 overflow-x-auto pb-0.5">
              {[
                { id: 'all', label: 'All' },
                { id: 'handoff_requested', label: '🚨 Handoffs' },
                { id: 'human_active', label: '👤 Live' },
                { id: 'ai', label: '🤖 AI' },
                { id: 'resolved', label: 'Resolved' },
              ].map(({ id, label }) => (
                <button
                  key={id}
                  onClick={() => setStatusFilter(id as any)}
                  className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors cursor-pointer shrink-0 ${
                    statusFilter === id
                      ? 'bg-white/10 text-white font-semibold'
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Conversation Cards */}
          <div className="flex-1 overflow-y-auto divide-y divide-white/5 pb-4 overscroll-contain">
            {isLoadingList ? (
              <div className="py-12 text-center text-zinc-500 text-xs">
                <RefreshCw className="w-4 h-4 animate-spin text-[#F97316] inline-block mr-2" />
                Loading conversations...
              </div>
            ) : filteredConversations.length === 0 ? (
              <div className="py-12 px-4 text-center text-zinc-500 text-xs space-y-3">
                <MessageSquare className="w-6 h-6 text-zinc-600 mx-auto" />
                <p>No active conversations found.</p>
                <Button variant="secondary" size="sm" onClick={handleCreateNewConversation}>
                  <Plus className="w-3 h-3 mr-1" />
                  <span>Start Test Inquiry</span>
                </Button>
              </div>
            ) : (
              filteredConversations.map((conv) => {
                const isSelected = conv.id === selectedConv?.id;
                const lastMsg = conv.messages[conv.messages.length - 1];

                return (
                  <div
                    key={conv.id}
                    onClick={() => {
                      setSelectedId(conv.id);
                      setShowMobileList(false);
                    }}
                    className={`p-3 transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-white/[0.05] border-l-2 border-[#F97316]'
                        : 'hover:bg-white/[0.02]'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-1.5 mb-0.5">
                      <span className="font-semibold text-xs text-white truncate">
                        {conv.visitor_name}
                      </span>
                      <span className="text-[10px] text-zinc-500 shrink-0 font-mono">
                        {conv.last_message_at}
                      </span>
                    </div>

                    <div className="text-[11px] text-[#F97316] font-medium mb-1 truncate">
                      {conv.property_interest}
                    </div>

                    {/* Clean 1-Line Message Preview */}
                    <p className="text-[11px] text-zinc-400 truncate mb-1.5">
                      {lastMsg ? (
                        <>
                          {lastMsg.sender_type === 'agent' ? 'You: ' : lastMsg.role === 'assistant' ? 'AI: ' : ''}
                          {lastMsg.content}
                        </>
                      ) : (
                        <span className="italic text-zinc-600">No messages yet</span>
                      )}
                    </p>

                    <div className="flex items-center justify-between text-[10px]">
                      <span className="font-mono text-zinc-400 bg-[#0B0B0D] px-1.5 py-0.5 rounded border border-white/5 truncate max-w-[110px]">
                        {conv.budget}
                      </span>
                      {conv.status === 'handoff_requested' ? (
                        <span className="text-amber-400 flex items-center gap-1 font-semibold shrink-0 animate-pulse">
                          <AlertCircle className="w-3 h-3" />
                          Handoff
                        </span>
                      ) : conv.status === 'human_active' ? (
                        <span className="text-blue-400 flex items-center gap-1 font-semibold shrink-0">
                          <UserCheck className="w-3 h-3" />
                          Advisor
                        </span>
                      ) : conv.status === 'resolved' ? (
                        <span className="text-zinc-500 flex items-center gap-1 font-medium shrink-0">
                          <CheckCircle2 className="w-3 h-3" />
                          Resolved
                        </span>
                      ) : (
                        <span className="text-emerald-400 flex items-center gap-1 font-medium shrink-0">
                          <Bot className="w-3 h-3" />
                          AI Active
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* RIGHT PANE: Active Chat & RAG Citations */}
        {selectedConv ? (
          <div
            className={`${
              showMobileList ? 'hidden' : 'flex'
            } md:flex flex-1 flex-col min-w-0 bg-[#151517] h-full`}
          >
            {/* Header with Mobile Back Button & # 12b HITL Status Actions */}
            <div className="p-3.5 sm:p-4 border-b border-white/8 bg-[#121215] flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
              <div className="flex items-center gap-3">
                {/* Mobile Back Button */}
                <button
                  onClick={() => setShowMobileList(true)}
                  className="md:hidden p-1.5 rounded-lg bg-zinc-800 text-zinc-300 hover:text-white cursor-pointer"
                  title="Back to conversation list"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>

                <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-gradient-to-br from-[#F97316] to-[#C2410C] flex items-center justify-center font-bold text-white text-xs sm:text-sm shrink-0 shadow-md">
                  {selectedConv.visitor_name.charAt(0)}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-xs sm:text-sm text-white truncate">
                      {selectedConv.visitor_name}
                    </h3>
                    {selectedConv.status === 'handoff_requested' ? (
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center gap-1 animate-pulse">
                        <AlertCircle className="w-3 h-3" /> Handoff Requested
                      </span>
                    ) : selectedConv.status === 'human_active' ? (
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30 flex items-center gap-1">
                        <UserCheck className="w-3 h-3" /> Live Advisor Active
                      </span>
                    ) : selectedConv.status === 'resolved' ? (
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-zinc-700/30 text-zinc-400 border border-zinc-700/40">
                        Resolved
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                        <Bot className="w-3 h-3" /> AI Assistant Active
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-[11px] sm:text-xs text-zinc-400 mt-0.5 flex-wrap">
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3 h-3 text-zinc-500" />
                      {selectedConv.visitor_location}
                    </span>
                    {selectedConv.visitor_phone && (
                      <span className="flex items-center gap-1 font-mono">
                        <Phone className="w-3 h-3 text-zinc-500" />
                        {selectedConv.visitor_phone}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* # 12b HITL - Action Buttons: AI Brief, Claim, Release & Resolve */}
              <div className="flex items-center gap-2 self-end sm:self-auto shrink-0 flex-wrap">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleFetchSummary}
                  title="Generate concise AI Context Brief"
                >
                  <Sparkles className="w-3.5 h-3.5 mr-1 text-amber-400" />
                  <span>{isLoadingSummary ? 'Analyzing...' : 'AI Brief'}</span>
                </Button>

                {selectedConv.status === 'handoff_requested' ? (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleClaimConversation}
                    className="bg-amber-600 hover:bg-amber-500 text-white font-semibold animate-pulse shadow-lg shadow-amber-600/30"
                  >
                    <AlertCircle className="w-3.5 h-3.5 mr-1" />
                    <span>Claim Conversation</span>
                  </Button>
                ) : selectedConv.status === 'human_active' ? (
                  <>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleReleaseConversation}
                      title="Return thread to AI Assistant"
                    >
                      <Bot className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                      <span>Release to AI</span>
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleResolveConversation}
                      title="Mark inquiry as resolved"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-blue-400" />
                      <span>Resolve</span>
                    </Button>
                  </>
                ) : selectedConv.status === 'resolved' ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleClaimConversation}
                    title="Re-open conversation"
                  >
                    <RefreshCw className="w-3.5 h-3.5 mr-1 text-zinc-400" />
                    <span>Re-open</span>
                  </Button>
                ) : (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleClaimConversation}
                    title="Take over conversation live from AI"
                  >
                    <User className="w-3.5 h-3.5 mr-1 text-blue-400" />
                    <span>Take Over</span>
                  </Button>
                )}
              </div>
            </div>

            {/* # 12b HITL - AI Executive Brief Drawer */}
            {showSummaryDrawer && (
              <div className="mx-4 sm:mx-6 mt-4 p-4 rounded-xl bg-gradient-to-r from-amber-500/15 via-amber-500/5 to-transparent border border-amber-500/30 relative animate-in fade-in">
                <div className="flex items-start justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-400">
                    <Sparkles className="w-4 h-4 text-amber-400 shrink-0" />
                    <span>AI Executive Handover Brief</span>
                  </div>
                  <button
                    onClick={() => setShowSummaryDrawer(false)}
                    className="text-zinc-400 hover:text-white text-xs px-1 cursor-pointer"
                  >
                    ✕
                  </button>
                </div>
                <p className="text-xs text-zinc-200 leading-relaxed mb-3">
                  {isLoadingSummary ? 'Analyzing visitor dialogue with LLM...' : activeSummary?.summary || 'Inquiry underway. Ready for advisor.'}
                </p>
                {activeSummary && (
                  <div className="flex items-center gap-3 text-[11px] text-zinc-400 flex-wrap">
                    {activeSummary.key_intent && (
                      <span className="bg-black/40 px-2 py-0.5 rounded border border-white/5">
                        🎯 <strong className="text-zinc-300">Intent:</strong> {activeSummary.key_intent}
                      </span>
                    )}
                    {activeSummary.budget && (
                      <span className="bg-black/40 px-2 py-0.5 rounded border border-white/5">
                        💰 <strong className="text-zinc-300">Budget:</strong> {activeSummary.budget}
                      </span>
                    )}
                    {activeSummary.preferred_location && (
                      <span className="bg-black/40 px-2 py-0.5 rounded border border-white/5">
                        📍 <strong className="text-zinc-300">Location:</strong> {activeSummary.preferred_location}
                      </span>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Message Stream */}
            <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-4 pb-6 overscroll-contain">
              {isLoadingMessages ? (
                <div className="py-12 text-center text-zinc-500 text-xs">
                  <RefreshCw className="w-4 h-4 animate-spin text-[#F97316] inline-block mr-2" />
                  Loading message history...
                </div>
              ) : selectedConv.messages.length === 0 ? (
                <div className="py-16 text-center text-zinc-500 text-xs space-y-2">
                  <Bot className="w-8 h-8 text-zinc-600 mx-auto" />
                  <p>No messages in this inquiry thread yet.</p>
                  <p className="text-[11px] text-zinc-600">
                    Send a message below to interact with this conversation.
                  </p>
                </div>
              ) : (
                selectedConv.messages.map((msg) => {
                  const isAssistant = msg.role === 'assistant';
                  const isAgent = msg.sender_type === 'agent';
                  const isSystem = msg.role === 'system' || msg.sender_type === 'system';

                  // System Event Pill
                  if (isSystem) {
                    return (
                      <div key={msg.id} className="flex justify-center my-2">
                        <span className="text-[11px] text-zinc-400 bg-white/5 border border-white/10 px-3 py-1 rounded-full text-center">
                          ℹ️ {msg.content}
                        </span>
                      </div>
                    );
                  }

                  return (
                    <div
                      key={msg.id}
                      className={`flex flex-col ${
                        isAgent ? 'items-end' : isAssistant ? 'items-start' : 'items-start'
                      }`}
                    >
                      <div className="flex items-center gap-1.5 text-[10px] sm:text-[11px] text-zinc-500 mb-1 px-1">
                        {isAgent ? (
                          <>
                            <span className="font-semibold text-blue-400 flex items-center gap-1">
                              <UserCheck className="w-3 h-3" /> Licensed Advisor (You)
                            </span>
                          </>
                        ) : isAssistant ? (
                          <>
                            <Bot className="w-3 h-3 text-[#F97316]" />
                            <span className="font-semibold text-zinc-300">
                              AI Assistant
                            </span>
                          </>
                        ) : (
                          <>
                            <User className="w-3 h-3 text-amber-400" />
                            <span className="font-semibold text-zinc-300">
                              {selectedConv.visitor_name}
                            </span>
                          </>
                        )}
                        <span>•</span>
                        <span>{msg.created_at}</span>
                      </div>

                      <div
                        className={`max-w-[88%] sm:max-w-2xl p-3.5 sm:p-4 rounded-2xl text-xs sm:text-[13px] leading-relaxed ${
                          isAgent
                            ? 'bg-[#131E30] text-zinc-100 border border-blue-500/40 rounded-tr-sm shadow-md shadow-blue-500/10'
                            : isAssistant
                            ? 'bg-[#1E1E21] text-zinc-100 border border-white/8 rounded-tl-sm'
                            : 'bg-[#2A1D15] text-zinc-100 border border-[#F97316]/30 rounded-tl-sm shadow-sm'
                        }`}
                      >
                        {msg.content ? (
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                        ) : isAssistant && isStreaming ? (
                          <div className="flex items-center gap-1.5 text-zinc-400 italic">
                            <Sparkles className="w-3.5 h-3.5 text-[#F97316] animate-spin" />
                            <span>Streaming assistant response...</span>
                          </div>
                        ) : null}

                        {/* Grounded Citation */}
                        {isAssistant && msg.grounded_sources && msg.grounded_sources.length > 0 && (
                          <div className="mt-3 pt-2 border-t border-white/10 flex items-start gap-1.5 text-[10px] sm:text-[11px] text-zinc-400">
                            <Sparkles className="w-3.5 h-3.5 text-[#F97316] shrink-0 mt-0.5" />
                            <div>
                              <span className="font-semibold text-zinc-300 block">
                                Grounded Citation:
                              </span>
                              {msg.grounded_sources.map((src, idx) => (
                                <span
                                  key={idx}
                                  className="inline-flex items-center gap-1 font-mono text-[10px] text-emerald-400 bg-black/40 px-2 py-0.5 rounded mt-1 mr-1 border border-emerald-500/20"
                                >
                                  {src}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Agent Reply Bar */}
            <form
              onSubmit={handleSendMessage}
              className="p-3 sm:p-3.5 border-t border-white/8 bg-[#121215] flex items-center gap-2 sm:gap-3 shrink-0"
            >
              <input
                type="text"
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                disabled={isStreaming}
                placeholder={
                  selectedConv.status === 'human_active'
                    ? 'Type a message to reply live to the visitor (WebSocket)...'
                    : isStreaming
                    ? 'AI assistant is streaming reply...'
                    : 'Type a prompt to test conversational AI stream...'
                }
                className="flex-1 px-3.5 py-2 sm:py-2.5 bg-[#0B0B0D] border border-white/10 rounded-xl text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#F97316] disabled:opacity-50"
              />
              <Button type="submit" variant="primary" size="md" disabled={isStreaming || !replyText.trim()}>
                {isStreaming ? (
                  <Sparkles className="w-3.5 h-3.5 animate-spin mr-1" />
                ) : (
                  <Send className="w-3.5 h-3.5 mr-1" />
                )}
                <span>
                  {isStreaming
                    ? 'Streaming...'
                    : selectedConv.status === 'human_active'
                    ? 'Reply to Visitor'
                    : 'Send'}
                </span>
              </Button>
            </form>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-6 sm:p-10 text-center max-w-lg mx-auto">
            <div className="w-14 h-14 rounded-2xl bg-[#F97316]/10 border border-[#F97316]/20 flex items-center justify-center text-[#F97316] mb-4 shadow-lg shadow-[#F97316]/10">
              <MessageSquare className="w-7 h-7" />
            </div>
            <h3 className="text-base sm:text-lg font-bold text-white mb-1.5">
              Live Inquiries & Conversation Stream
            </h3>
            <p className="text-xs text-zinc-400 leading-relaxed mb-6">
              This inbox monitors live visitor chats from your website widget. Each visitor inquiry streams in real-time with grounded citations and lead qualification.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full text-left mb-6">
              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5 space-y-1">
                <span className="text-[11px] font-semibold text-white flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-[#F97316]" /> Real-time Streaming
                </span>
                <p className="text-[11px] text-zinc-400">
                  Token-by-token SSE streaming for visitor inquiries and agent replies.
                </p>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5 space-y-1">
                <span className="text-[11px] font-semibold text-white flex items-center gap-1.5">
                  <Bot className="w-3.5 h-3.5 text-blue-400" /> Grounded RAG Answers
                </span>
                <p className="text-[11px] text-zinc-400">
                  AI answers strictly from documents in your agency's Knowledge Base.
                </p>
              </div>
            </div>

            <Button variant="primary" size="md" onClick={handleCreateNewConversation}>
              <Plus className="w-4 h-4 mr-1.5" />
              <span>Launch Test Inquiry</span>
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};
