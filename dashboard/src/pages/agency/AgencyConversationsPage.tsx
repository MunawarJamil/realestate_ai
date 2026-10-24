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
  MoreVertical,
  Trash2,
  AlertCircle,
  MessageSquare,
  UserCheck,
  Radio,
} from 'lucide-react';
import type { Conversation, ConversationStatus, Message, BackendConversationSummary } from '../../types/agency';
import type { BackendConversation, BackendMessage } from '../../api/client';
import { Button } from '../../components/ui/Button';
import { apiClient, ApiError } from '../../api/client';
import { AgentSocketClient } from '../../api/agentSocket';


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

    const selectedIdRef = useRef<string | null>(selectedId);
  useEffect(() => {
    selectedIdRef.current = selectedId;
  }, [selectedId]);


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


  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [isDeletingId, setIsDeletingId] = useState<string | null>(null);

  // Close three-dots dropdown menu when clicking anywhere outside
  useEffect(() => {
    const handleOutsideClick = () => setOpenMenuId(null);
    window.addEventListener('click', handleOutsideClick);
    return () => window.removeEventListener('click', handleOutsideClick);
  }, []);




  const [liveHandoffAlert, setLiveHandoffAlert] = useState<{ conversation_id: string; snippet: string } | null>(null);
  const [typingMap, setTypingMap] = useState<Record<string, { isTyping: boolean; sender: string }>>({});
  const agentWsRef = useRef<AgentSocketClient | null>(null);
  const agentTypingTimerRef = useRef<any>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const showNotification = (msg: string) => {
    setActionNotice(msg);
    setTimeout(() => setActionNotice(null), 3500);
  };

  // 1. Fetch Conversations List (Runs only on mount, merges safely with live state)
  const fetchConversations = useCallback(async () => {
    setIsLoadingList(true);
    setErrorBanner(null);
    try {
      const res = await apiClient.agency.listConversations({ limit: 50 });
      const mapped = res.items.map((c) => mapBackendConversation(c, []));

      setConversations((prev) => {
        // Create lookup to preserve loaded messages & unread counts
        const prevMap = new Map(prev.map((c) => [c.id, c]));
        return mapped.map((c) => {
          const existing = prevMap.get(c.id);
          if (existing) {
            return {
              ...c,
              messages: existing.messages.length > 0 ? existing.messages : c.messages,
              last_message_preview: existing.last_message_preview,
              last_message_sender: existing.last_message_sender,
              unread_count: existing.unread_count ?? 0,
            };
          }
          return c;
        });
      });

      // Select first conversation only if nothing is currently selected
      setSelectedId((curr) => curr || (mapped.length > 0 ? mapped[0].id : null));
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorBanner(`Failed to load conversations (${err.status}): ${err.message}`);
      } else {
        setErrorBanner('Could not reach backend API server at http://localhost:8000.');
      }
    } finally {
      setIsLoadingList(false);
    }
  }, []); // <-- Empty array: Never re-fetch just because selectedId changed

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);




    const handleIncomingMessage = useCallback((msg: BackendMessage) => {
    setConversations((prev) => {
      const mappedMsg = mapBackendMessage(msg);
      const targetIndex = prev.findIndex((c) => c.id === msg.conversation_id);
      const isCurrentActive = selectedIdRef.current === msg.conversation_id;

      if (targetIndex === -1) {
        // Prepend brand new conversation from incoming visitor
        const newConv: Conversation = {
          id: msg.conversation_id,
          visitor_name: `Visitor ${msg.conversation_id.slice(0, 6)}`,
          visitor_location: 'Online Visitor',
          intent: 'Property Inquiry',
          budget: 'Pending Inquiry',
          property_interest: 'General Inquiry',
          status: 'ai',
          started_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          last_message_at: mappedMsg.created_at,
          last_message_preview: mappedMsg.content,
          last_message_sender: msg.sender_type || (msg.role === 'user' ? 'visitor' : 'ai'),
          tags: ['Live Web Widget'],
          messages: [mappedMsg],
          unread_count: isCurrentActive ? 0 : 1,
        };
        return [newConv, ...prev];
      }

          const targetConv = prev[targetIndex];

      // Check if message already exists by ID, OR matches an optimistic agent message
      const existingIndex = targetConv.messages.findIndex(
        (m) =>
          m.id === msg.id ||
          (msg.sender_type === 'agent' &&
            m.sender_type === 'agent' &&
            m.id.startsWith('agt-') &&
            m.content === msg.content)
      );

      let updatedMessages: Message[];
      if (existingIndex !== -1) {
        // Replace optimistic placeholder with confirmed server message (adopting real UUID)
        updatedMessages = targetConv.messages.map((m, idx) =>
          idx === existingIndex ? mappedMsg : m
        );
      } else {
        updatedMessages = [...targetConv.messages, mappedMsg];
      }


      const updatedConv: Conversation = {
        ...targetConv,
        last_message_at: mappedMsg.created_at,
        last_message_preview: mappedMsg.content,
        last_message_sender: msg.sender_type || (msg.role === 'user' ? 'visitor' : 'ai'),
        messages: updatedMessages,
        unread_count: isCurrentActive
          ? 0
          : (targetConv.unread_count || 0) + (msg.sender_type === 'agent' ? 0 : 1),
      };

      // WhatsApp Reorder: prepend to index 0 (top)
      const remaining = prev.filter((_, idx) => idx !== targetIndex);
      return [updatedConv, ...remaining];
    });

    if (selectedIdRef.current === msg.conversation_id) {
      setTimeout(scrollToBottom, 60);
    }
  }, []);


    // # 12c HITL - Connect Agency Agent Socket.IO for real-time live two-way messaging
  useEffect(() => {
    const socket = new AgentSocketClient({
      onConnected: () => {
        setAgentWsConnected(true);
      },
      onDisconnected: () => {
        setAgentWsConnected(false);
      },
      onMessage: (msg) => {
        handleIncomingMessage(msg);
      },
      onVisitorActivity: (msg) => {
        handleIncomingMessage(msg);
      },
      onTyping: (data: { conversation_id: string; is_typing: boolean; sender: string }) => {
        setTypingMap((prev) => ({
          ...prev,
          [data.conversation_id]: { isTyping: data.is_typing, sender: data.sender },
        }));
      },

      onError: (err) => {
        console.warn('[RealEstateAI Agent Socket.IO] Notice:', err);
      },
    });

    socket.connect();
    agentWsRef.current = socket;

    return () => {
      socket.disconnect();
    };
  }, []);


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

  // useEffect(() => {
  //   if (selectedId) {
  //     loadMessages(selectedId);
  //     // Reset summary drawer when switching conversations
  //     setActiveSummary(null);
  //     setShowSummaryDrawer(false);
  //   }
  // }, [selectedId, loadMessages]);


    useEffect(() => {
    if (selectedId) {
      loadMessages(selectedId);
      // # 12c HITL - Join active conversation room on Socket.IO
      agentWsRef.current?.joinConversation(selectedId);
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
    const handleDeleteConversation = async (convId: string) => {
    if (!window.confirm('Are you sure you want to delete this conversation? This will permanently delete all messages.')) {
      return;
    }

    setIsDeletingId(convId);
    try {
      await apiClient.agency.deleteConversation(convId);
      setConversations((prev) => {
        const next = prev.filter((c) => c.id !== convId);
        if (selectedId === convId) {
          setSelectedId(next.length > 0 ? next[0].id : null);
        }
        return next;
      });
      showNotification('Conversation deleted successfully.');
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to delete conversation';
      alert(`Could not delete conversation: ${msg}`);
    } finally {
      setIsDeletingId(null);
    }
  };
  const handleReplyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setReplyText(val);

    if (selectedId && agentWsRef.current?.isConnected()) {
      if (val.trim().length > 0) {
        agentWsRef.current.sendTyping(selectedId, true);
        if (agentTypingTimerRef.current) clearTimeout(agentTypingTimerRef.current);
        agentTypingTimerRef.current = setTimeout(() => {
          if (selectedId) agentWsRef.current?.sendTyping(selectedId, false);
        }, 2000);
      } else {
        if (agentTypingTimerRef.current) clearTimeout(agentTypingTimerRef.current);
        agentWsRef.current.sendTyping(selectedId, false);
      }
    }
  };

  // 4. Send Message (Strictly Human Agent Reply)
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyText.trim() || !selectedConv) return;
    // Guard: Resolved conversations cannot receive replies without explicit re-opening
    if (selectedConv.status === 'resolved') return;

    const messageContent = replyText.trim();
    setReplyText('');
    if (agentTypingTimerRef.current) clearTimeout(agentTypingTimerRef.current);
    if (selectedConv) agentWsRef.current?.sendTyping(selectedConv.id, false);

    const timestampStr = new Date().toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });

    // If currently 'ai' or 'handoff_requested', claim conversation to transition to human_active
    if (selectedConv.status !== 'human_active') {
      try {
        await apiClient.agency.claimConversation(selectedConv.id);
        setConversations((prev) =>
          prev.map((c) => (c.id === selectedConv.id ? { ...c, status: 'human_active' } : c))
        );
      } catch (err) {
        console.warn('Auto-claim on send failed, attempting direct send:', err);
      }
    }

    // Optimistic UI update for immediate feedback
    const tempAgentMsgId = `agt-${Date.now()}`;
    const agentMsg: Message = {
      id: tempAgentMsgId,
      role: 'user', // UI right-alignment
      sender_type: 'agent',
      content: messageContent,
      created_at: timestampStr,
    };

    setConversations((prev) =>
      prev.map((c) =>
        c.id === selectedConv.id
          ? {
              ...c,
              status: 'human_active',
              last_message_at: timestampStr,
              messages: [...c.messages, agentMsg],
            }
          : c
      )
    );

    setTimeout(scrollToBottom, 40);

    // Prefer Real-time Socket.IO dispatch
    if (agentWsRef.current?.isConnected()) {
      const ok = agentWsRef.current.sendMessage(selectedConv.id, messageContent);
      if (ok) return;
    }

    // Fallback to REST endpoint
    try {
      await apiClient.agency.sendMessage(selectedConv.id, messageContent);
    } catch (err: unknown) {
      console.error('Failed to deliver agent message:', err);
      showNotification('Failed to deliver message to visitor.');
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
                      // Clear unread badge on open
                      setConversations((prev) =>
                        prev.map((c) => (c.id === conv.id ? { ...c, unread_count: 0 } : c))
                      );
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
                      <div className="flex items-center gap-1.5 shrink-0">
                        <span className="text-[10px] text-zinc-500 font-mono">
                          {conv.last_message_at}
                        </span>
                        {Boolean(conv.unread_count && conv.unread_count > 0) && (
                          <span className="inline-flex items-center justify-center bg-[#F97316] text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] h-[18px] shadow-sm animate-pulse">
                            {conv.unread_count}
                          </span>
                        )}

                        {/* Three Vertical Dots Dropdown */}
                        <div className="relative">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setOpenMenuId((curr) => (curr === conv.id ? null : conv.id));
                            }}
                            className="p-1 rounded hover:bg-white/10 text-zinc-400 hover:text-white transition-colors cursor-pointer"
                            title="Chat options"
                          >
                            <MoreVertical className="w-3.5 h-3.5" />
                          </button>

                          {openMenuId === conv.id && (
                            <div
                              onClick={(e) => e.stopPropagation()}
                              className="absolute right-0 top-6 z-30 w-36 bg-[#1A1A1E] border border-white/10 rounded-lg shadow-xl py-1 animate-in fade-in zoom-in-95"
                            >
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setOpenMenuId(null);
                                  handleDeleteConversation(conv.id);
                                }}
                                disabled={isDeletingId === conv.id}
                                className="w-full text-left px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/10 hover:text-red-300 flex items-center gap-2 cursor-pointer transition-colors"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                                <span>{isDeletingId === conv.id ? 'Deleting...' : 'Delete Chat'}</span>
                              </button>
                            </div>
                          )}
                        </div>
                      </div>

                    </div>


                    <div className="text-[11px] text-[#F97316] font-medium mb-1 truncate">
                      {conv.property_interest}
                    </div>

                    {/* Clean 1-Line Message Preview */}
                    <p className="text-[11px] text-zinc-400 truncate mb-1.5">
                      {typingMap[conv.id]?.isTyping && typingMap[conv.id]?.sender === 'visitor' ? (
                        <span className="text-amber-400 font-medium italic animate-pulse flex items-center gap-1">
                          <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping mr-0.5" />
                          Typing...
                        </span>
                      ) : lastMsg ? (
                        <>
                          {lastMsg.sender_type === 'agent' ? 'You: ' : lastMsg.role === 'assistant' ? 'AI: ' : ''}
                          {lastMsg.content}
                        </>
                      ) : conv.last_message_preview ? (
                        <>
                          {conv.last_message_sender === 'agent' ? 'You: ' : conv.last_message_sender === 'ai' ? 'AI: ' : ''}
                          {conv.last_message_preview}
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

            {/* Agent Reply Bar or Resolved Read-Only Banner */}
            {selectedConv.status === 'resolved' ? (
              <div className="p-3 sm:p-3.5 border-t border-white/8 bg-[#101013] flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
                <div className="flex items-center gap-2 text-xs text-zinc-400">
                  <CheckCircle2 className="w-4 h-4 text-zinc-500 shrink-0" />
                  <span>
                    This inquiry is <strong>Resolved</strong> (read-only mode). Re-open to message the visitor.
                  </span>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleClaimConversation}
                  className="bg-white/5 hover:bg-white/10 text-white shrink-0 self-end sm:self-auto cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5 mr-1.5 text-amber-400" />
                  <span>Re-open Conversation</span>
                </Button>
              </div>
            ) : (
              <div className="border-t border-white/8 bg-[#121215] shrink-0">
                {typingMap[selectedConv.id]?.isTyping && typingMap[selectedConv.id]?.sender === 'visitor' && (
                  <div className="px-4 py-1.5 border-b border-white/5 flex items-center gap-2 text-[11px] text-amber-400 animate-pulse bg-amber-500/5">
                    <span className="flex gap-1 items-center">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-bounce" />
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-bounce [animation-delay:0.2s]" />
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-bounce [animation-delay:0.4s]" />
                    </span>
                    <span><strong>{selectedConv.visitor_name}</strong> is typing...</span>
                  </div>
                )}
                <form
                  onSubmit={handleSendMessage}
                  className="p-3 sm:p-3.5 flex items-center gap-2 sm:gap-3"
                >
                  <input
                    type="text"
                    value={replyText}
                    onChange={handleReplyChange}
                    placeholder={
                      selectedConv.status === 'human_active'
                        ? 'Type a message to reply live to the visitor...'
                        : selectedConv.status === 'handoff_requested'
                        ? 'Reply to claim and join live conversation with visitor...'
                        : 'Reply to take over conversation from AI...'
                    }
                    className="flex-1 px-3.5 py-2 sm:py-2.5 bg-[#0B0B0D] border border-white/10 rounded-xl text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-[#F97316]"
                  />
                  <Button
                    type="submit"
                    variant="primary"
                    size="md"
                    disabled={!replyText.trim()}
                    className="shrink-0 cursor-pointer"
                  >
                    <Send className="w-3.5 h-3.5 mr-1" />
                    <span>
                      {selectedConv.status === 'human_active' ? 'Reply' : 'Claim & Reply'}
                    </span>
                  </Button>
                </form>
              </div>
            )}
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
