import React, { useState, useEffect } from 'react';
import styles from './ScheduleTimeline.module.css';
import { getSmartStartTime } from '../../utils/timeUtils';

export default function ScheduleTimeline() {
  const [scheduleData, setScheduleData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchSchedule() {
      try {
        const token = localStorage.getItem('accessToken');
        const headers = {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        };
        const body = JSON.stringify({
          start_time: getSmartStartTime(),
          start_location: "Chợ Đà Lạt",
          max_distance_km: 30.0,
          travel_style: "Sống ảo nhẹ nhàng",
          preferred_vibe: "Thương mại",
          vehicle_type: "xe máy"
        });
        const res = await fetch('/api/s6/recommend', {
          method: 'POST',
          headers,
          body
        });
        if (!res.ok) throw new Error('Lỗi fetch lịch trình');
        const data = await res.json();
        setScheduleData(data.timeline || []);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    fetchSchedule();
  }, []);

  if (loading) {
    return <div className={styles.timelineContainer} style={{ padding: '20px', color: '#64748b' }}>Đang tự động lập lịch trình...</div>;
  }

  if (scheduleData.length === 0) {
    return <div className={styles.timelineContainer} style={{ padding: '20px', color: '#64748b' }}>Chưa có lịch trình nào được gợi ý.</div>;
  }

  return (
    <div className={styles.timelineContainer}>
      {scheduleData.map((item, index) => (
        <div key={index} className={styles.timelineItem}>
          <div className={styles.timeBox}>{item.time}</div>
          <div className={styles.timelineContent}>
            <div className={styles.timelineTitle}>{item.action} {item.location ? `- ${item.location}` : ''}</div>
            <div className={styles.timelineDesc}>{item.note}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
