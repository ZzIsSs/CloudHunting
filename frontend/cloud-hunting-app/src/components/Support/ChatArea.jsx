import React, { useState, useEffect } from 'react';
import styles from './ChatArea.module.css';

export default function ChatArea({ activeTicketId }) {
  const [ticketData, setTicketData] = useState(null);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!activeTicketId) return;
    async function fetchDetails() {
      setLoading(true);
      try {
        const token = localStorage.getItem('accessToken');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        const res = await fetch(`/content/tickets/${activeTicketId}`, { headers });
        if (res.ok) {
          const data = await res.json();
          setTicketData(data);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    fetchDetails();
  }, [activeTicketId]);

  const handleSend = async () => {
    if (!inputText.trim() || !activeTicketId) return;
    try {
      const token = localStorage.getItem('accessToken');
      const headers = { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      };
      const res = await fetch(`/content/tickets/${activeTicketId}/messages`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ message: inputText })
      });
      if (res.ok) {
        const newMessage = await res.json();
        setTicketData(prev => ({
          ...prev,
          messages: [...prev.messages, newMessage]
        }));
        setInputText('');
      }
    } catch (e) {
      console.error(e);
    }
  };

  if (!activeTicketId) {
    return <div className={styles.chatArea} style={{ alignItems: 'center', justifyContent: 'center' }}>Vui lòng chọn hoặc tạo một ticket.</div>;
  }

  if (loading || !ticketData) {
    return <div className={styles.chatArea} style={{ alignItems: 'center', justifyContent: 'center' }}>Đang tải...</div>;
  }

  const { ticket, messages } = ticketData;

  return (
    <div className={styles.chatArea}>
      <div className={styles.chatHeader}>
        <h2>{ticket.title} (Ticket #{ticket.id})</h2>
        <span className={`${styles.statusBadge} ${ticket.status === 'open' ? styles.statusOpen : styles.statusResolved}`}>
          {ticket.status === 'open' ? 'Đang xử lý' : 'Đã giải quyết'}
        </span>
      </div>
      
      <div className={styles.chatHistory}>
        {messages.map((msg, index) => {
          // sender_id = ticket.user_id means it's the user. otherwise admin.
          const isUser = msg.sender_id === ticket.user_id;
          return (
            <div key={index} className={`${styles.message} ${isUser ? styles.msgUser : styles.msgAdmin}`}>
              <div className={styles.bubble}>{msg.message}</div>
              <div className={styles.msgTime}>{msg.created_at ? new Date(msg.created_at).toLocaleString() : ''}</div>
            </div>
          );
        })}
      </div>

      <div className={styles.chatInputArea}>
        <input 
          type="text" 
          className={styles.chatInput} 
          placeholder="Nhập tin nhắn..." 
          value={inputText}
          onChange={e => setInputText(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()}
        />
        <button className={styles.sendBtn} onClick={handleSend}>➤</button>
      </div>
    </div>
  );
}
