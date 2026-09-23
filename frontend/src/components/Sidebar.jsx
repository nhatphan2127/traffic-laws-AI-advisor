import React from 'react';

export default function Sidebar({ chats, activeChatId, username, onNewChat, onSelectChat, onLogin, onLogout }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <div className="sidebar-header">⚖ AI Legal Advisor</div>
        <button className="new-chat" type="button" onClick={onNewChat}>
          + New Conversation
        </button>
        <div className="history">
          {chats.map((chat) => (
            <button
              className={`history-item ${activeChatId === chat.id ? 'active' : ''}`}
              key={chat.id}
              type="button"
              onClick={() => onSelectChat(chat.id)}
            >
              {chat.title}
            </button>
          ))}
        </div>
      </div>
      <div className="user-auth-section">
        {username ? (
          <>
            <div className="user-name">👤 <b>{username}</b></div>
            <button className="auth-btn logout-btn" type="button" onClick={onLogout}>
              Đăng xuất
            </button>
          </>
        ) : (
          <button className="auth-btn" type="button" onClick={onLogin}>
            Đăng nhập / Đăng ký
          </button>
        )}
      </div>
    </aside>
  );
}