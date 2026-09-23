import React, { useState } from 'react';

export default function AuthModal({ open, onClose, onSubmit }) {
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!open) return null;

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await onSubmit(isRegisterMode ? 'register' : 'login', username.trim(), password.trim());
      setUsername('');
      setPassword('');
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  function toggleMode() {
    setIsRegisterMode((current) => !current);
    setError('');
  }

  return (
    <div
      className="modal show"
      role="presentation"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <div className="modal-content" role="dialog" aria-modal="true" aria-labelledby="auth-title">
        <h3 id="auth-title">{isRegisterMode ? 'Đăng ký' : 'Đăng nhập'}</h3>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="auth-username">Tên đăng nhập</label>
            <input
              id="auth-username"
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="auth-password">Mật khẩu</label>
            <input
              id="auth-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>
          {error && <div className="auth-error">{error}</div>}
          <button className="auth-btn" type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Đang xử lý...' : isRegisterMode ? 'Đăng ký' : 'Đăng nhập'}
          </button>
        </form>
        <button className="toggle-auth" type="button" onClick={toggleMode}>
          {isRegisterMode ? 'Đã có tài khoản? Đăng nhập' : 'Chưa có tài khoản? Đăng ký ngay'}
        </button>
        <button className="auth-btn cancel-btn" type="button" onClick={onClose}>
          Hủy
        </button>
      </div>
    </div>
  );
}