import React, { useRef } from 'react';

export default function ChatInput({ value, disabled, onChange, onSubmit }) {
  const textareaRef = useRef(null);

  function handleChange(event) {
    onChange(event.target.value);
    event.target.style.height = 'auto';
    event.target.style.height = `${Math.min(event.target.scrollHeight, 200)}px`;
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      onSubmit();
    }
  }

  return (
    <div className="input-area">
      <div className="input-wrapper">
        <textarea
          ref={textareaRef}
          className="chat-input"
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Hỏi về quy định, mức phạt, thủ tục..."
          rows="1"
          disabled={disabled}
        />
        <button className="send-btn" type="button" onClick={onSubmit} disabled={disabled} aria-label="Gửi câu hỏi">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M15 8L1 15L3 8L1 1L15 8Z" fill="currentColor" />
          </svg>
        </button>
      </div>
    </div>
  );
}