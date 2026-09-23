const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

function authHeaders() {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...options.headers,
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'Lỗi hệ thống');
  return data;
}

export function authenticate(mode, username, password) {
  return request(mode === 'register' ? '/api/register' : '/api/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export function getChats() {
  return request('/api/chats');
}

export function getChat(chatId) {
  return request(`/api/chats/${chatId}`);
}

export async function streamChat(payload, onEvent) {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(payload),
  });

  if (!response.ok || !response.body) {
    throw new Error('Network connection failed. Please check backend server.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmedLine = line.trim();
      if (!trimmedLine.startsWith('data: ')) continue;
      try {
        onEvent(JSON.parse(trimmedLine.slice(6)));
      } catch {
        // Ignore incomplete or malformed SSE records.
      }
    }
  }
}
