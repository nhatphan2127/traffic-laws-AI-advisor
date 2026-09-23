import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import AuthModal from './components/AuthModal';
import ChatInput from './components/ChatInput';
import ChatMessage from './components/ChatMessage';
import RetrievalPanel from './components/RetrievalPanel';
import { authenticate, getChat, getChats, streamChat } from './api/client';

const welcomeMessage = (
  <div className="welcome-view">
    <h1>Legal Reasoning Engine</h1>
    <p>Truy xuất đa tầng &amp; Phân tích chuyên sâu luật Việt Nam</p>
  </div>
);

export default function App() {
  const [username, setUsername] = useState(() => localStorage.getItem('username') || '');
  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const chatContainerRef = useRef(null);

  useEffect(() => {
    if (username) refreshChats();
  }, [username]);

  useEffect(() => {
    const container = chatContainerRef.current;
    if (container) container.scrollTop = container.scrollHeight;
  }, [messages]);

  async function refreshChats() {
    try {
      setChats(await getChats());
    } catch (error) {
      console.error('Lỗi lấy lịch sử chat:', error);
    }
  }

  async function handleAuth(mode, nextUsername, password) {
    const data = await authenticate(mode, nextUsername, password);
    localStorage.setItem('token', data.token);
    localStorage.setItem('username', data.username);
    setUsername(data.username);
    setAuthOpen(false);
  }

  function startNewConversation() {
    setActiveChatId(null);
    setMessages([]);
    setDocuments([]);
    if (username) refreshChats();
  }

  function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    setUsername('');
    startNewConversation();
    setChats([]);
  }

  async function loadChatDetail(chatId) {
    try {
      const chat = await getChat(chatId);
      setActiveChatId(chatId);
      setDocuments([]);
      setMessages(
        chat.messages.map((message) => ({
          role: message.role === 'user' ? 'user' : 'assistant',
          content: message.content,
          thinking: '',
          loading: false,
        }))
      );
      await refreshChats();
    } catch (error) {
      console.error('Lỗi load chi tiết chat:', error);
    }
  }

  async function handleChat() {
    const query = input.trim();
    if (!query || isProcessing) return;

    const userMessage = { role: 'user', content: query };
    const botMessage = { role: 'assistant', content: '', thinking: '', loading: true };
    const nextMessages = [...messages, userMessage, botMessage];
    setMessages(nextMessages);
    setInput('');
    setIsProcessing(true);
    let finalAnswer = '';
    let accumulatedThinking = '';

    try {
      await streamChat(
        {
          message: query,
          chat_id: activeChatId,
          history: messages.map(({ role, content }) => ({ role, content })),
        },
        (data) => {
          if (data.new_chat_id) {
            setActiveChatId(data.new_chat_id);
            refreshChats();
          }
          if (data.docs?.length) setDocuments(data.docs);
          if (data.thinking) accumulatedThinking += data.thinking;
          if (data.answer) finalAnswer += data.answer;
          setMessages((current) =>
            current.map((msg, index) =>
              index === current.length - 1
                ? { ...msg, content: finalAnswer, thinking: accumulatedThinking }
                : msg
            )
          );
        }
      );
      setMessages((current) =>
        current.map((msg, index) => (index === current.length - 1 ? { ...msg, loading: false } : msg))
      );
    } catch (error) {
      setMessages((current) =>
        current.map((msg, index) =>
          index === current.length - 1 ? { ...msg, content: `Error: ${error.message}`, loading: false } : msg
        )
      );
    } finally {
      setIsProcessing(false);
    }
  }

  return (
    <>
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        username={username}
        onNewChat={startNewConversation}
        onSelectChat={loadChatDetail}
        onLogin={() => setAuthOpen(true)}
        onLogout={logout}
      />
      <main className="main-chat">
        <div className="chat-container" ref={chatContainerRef}>
          {messages.length === 0 ? (
            welcomeMessage
          ) : (
            messages.map((message, index) => <ChatMessage key={`${message.role}-${index}`} message={message} />))}
        </div>
        <ChatInput value={input} disabled={isProcessing} onChange={setInput} onSubmit={handleChat} />
      </main>
      <RetrievalPanel documents={documents} />
      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} onSubmit={handleAuth} />
    </>
  );
}