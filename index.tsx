import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

// 초기 테마 설정 (기본값: 라이트 모드)
const savedTheme = localStorage.getItem('theme');
if (savedTheme === 'dark') {
  document.documentElement.classList.add('dark');
} else {
  document.documentElement.classList.remove('dark');
  // 기본값을 라이트 모드로 설정
  if (!savedTheme) {
    localStorage.setItem('theme', 'light');
  }
}

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error("Could not find root element to mount to");
}

const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);