import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './TicketSidebar.module.css';

export default function TicketSidebar({ activeTicketId, onSelectTicket }) {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    async function fetchTickets() {
      try {
        const token = localStorage.getItem('accessToken');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        const res = await fetch('/content/tickets', { headers });
        if (!res.ok) throw new Error('Failed to fetch tickets');
        const data = await res.json();
        if (Array.isArray(data)) {
          setTickets(data);
          if (data.length > 0 && !activeTicketId) {
            onSelectTicket(data[0].id);
          }
        } else {
          setTickets([]);
        }
      } catch (e) {
        console.error(e);
        setTickets([]);
      } finally {
        setLoading(false);
      }
    }
    fetchTickets();
  }, [activeTicketId, onSelectTicket]);

  const handleCreate = async () => {
    const title = prompt('Nhập tiêu đề hỗ trợ:');
    if (!title) return;
    const desc = prompt('Nhập nội dung chi tiết:');
    if (!desc) return;

    try {
      const token = localStorage.getItem('accessToken');
      const headers = { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      };
      const res = await fetch('/content/tickets', {
        method: 'POST',
        headers,
        body: JSON.stringify({ title, description: desc })
      });
      if (res.ok) {
        const newTicket = await res.json();
        setTickets([newTicket, ...tickets]);
        onSelectTicket(newTicket.id);
      }
    } catch (e) {
      console.error('Lỗi khi tạo ticket:', e);
    }
  };

  return (
    <div className={styles.sidebar}>
      <div style={{ padding: '15px 20px 0', fontSize: '0.9rem' }}>
        <a href="#" onClick={(e) => { e.preventDefault(); navigate('/'); }} style={{ color: '#0ea5e9', textDecoration: 'none', fontWeight: '600' }}>← Quay lại Profile</a>
      </div>
      <div className={styles.sidebarHeader}>
        <h2>Hỗ trợ & CSKH</h2>
        <button className={styles.newTicketBtn} onClick={handleCreate}>+ Tạo mới</button>
      </div>
      <div className={styles.ticketList}>
        {loading ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#64748b' }}>Đang tải...</div>
        ) : tickets.length === 0 ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#64748b' }}>Chưa có yêu cầu hỗ trợ nào.</div>
        ) : (
          tickets.map(ticket => (
            <div 
              key={ticket.id} 
              className={`${styles.ticketItem} ${ticket.id === activeTicketId ? styles.active : ''}`}
              onClick={() => onSelectTicket(ticket.id)}
            >
              <div className={styles.ticketTitle}>{ticket.title}</div>
              <div className={styles.ticketMeta}>
                <span>#{ticket.id}</span>
                <span className={`${styles.statusBadge} ${ticket.status === 'open' ? styles.statusOpen : styles.statusResolved}`}>
                  {ticket.status === 'open' ? 'Đang xử lý' : 'Đã giải quyết'}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
