import React from 'react';
import { Link } from 'react-router-dom';
import logo from '@assets/logo.jpeg';

const Home: React.FC = () => {
  return (
    <div style={{
      position: 'absolute',
      left: '50%',
      top: '50%',
      transform: 'translate(-50%, -50%)',
      width: '100%',
      textAlign: 'center',
    }}>
      <img src={logo} alt="logo" width={128} height={128} style={{ marginBottom: 24 }} />
      <h1 style={{ color: 'var(--text-color)', fontSize: '2.5rem', marginBottom: 48 }}>
        欢迎使用CT肺结节检测系统
      </h1>
      <Link to="/workspace">
        <button className="start-btn" style={{
          padding: '12px 24px',
          fontSize: '1.2rem',
          background: 'var(--accent-color)',
          color: '#0a192f',
          border: 'none',
          borderRadius: 8,
          fontWeight: 600,
          cursor: 'pointer'
        }}>
          开始使用
        </button>
      </Link>
    </div>
  );
};

export default Home;
