import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import styles from './ScheduleLayout.module.css';
import { getSmartStartTime } from '../../utils/timeUtils';

export default function ScheduleLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [notifications, setNotifications] = useState([]);
  const [itinerary, setItinerary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeLocIdx, setActiveLocIdx] = useState(0);

  const fetchSchedule = async (locName) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('accessToken');
      const headers = { 
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      };
      const payload = {
          user_id: localStorage.getItem('currentUser') || "guest",
          start_time: getSmartStartTime(location.state?.timeOffset || 0),
          start_location: "Trung tâm",
          max_distance_km: 30.0,
          travel_style: "Sống ảo nhẹ nhàng",
          preferred_vibe: "Thương mại",
          vehicle_type: "xe máy",
          selected_location: locName || location.state?.selected_location || undefined
      };
      const recommendRes = await fetch('/api/s6/recommend', {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
      });
      if (recommendRes.ok) {
        const recommendData = await recommendRes.json();
        setItinerary(recommendData);
      }
    } catch (e) {
      console.error("Lỗi fetch S6 data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    async function fetchInitialData() {
      try {
        const token = localStorage.getItem('accessToken');
        const headers = { 
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        };
        const notifRes = await fetch('/api/s6/notifications', { headers });
        if (notifRes.ok) {
          const notifData = await notifRes.json();
          setNotifications(notifData);
        }
      } catch (e) {
        console.error("Lỗi fetch Notif data:", e);
      }
      // Khởi tạo lịch trình ban đầu
      await fetchSchedule();
    }
    fetchInitialData();
  }, []);

  const getTrendClass = (trend) => {
    if (!trend) return styles.trendFlat;
    if (trend.includes("Tăng")) return styles.trendUp;
    if (trend.includes("Giảm")) return styles.trendDown;
    return styles.trendFlat;
  };

  const getIndicatorClass = (prob) => {
    if (prob >= 75) return styles.indHigh;
    if (prob >= 50) return styles.indMid;
    return styles.indLow;
  };



  return (
    <div className={styles.pageWrapper}>
      {/* Animated Orbs */}
      <div className={`${styles.orb} ${styles.orb1}`}></div>
      <div className={`${styles.orb} ${styles.orb2}`}></div>
      <div className={`${styles.orb} ${styles.orb3}`}></div>

      <div className={styles.container}>
        {/* Left Panel: Lịch trình đề xuất */}
        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <div className={styles.panelTitle}>
              <button className={styles.backBtnIcon} onClick={() => navigate(-1)}>←</button>
              🗺️ Lịch trình đề xuất
            </div>
          </div>
          
          {loading ? (
            <div className={styles.loadingText}>Đang AI phân tích dữ liệu mây...</div>
          ) : (
            <>
              {itinerary && itinerary.recommended_locations && (
                <div className={styles.locationsWrapper}>
                  {itinerary.recommended_locations.map((loc, idx) => (
                    <div 
                      key={idx} 
                      className={`${styles.locCard} ${idx === activeLocIdx ? styles.locCardActive : ''}`}
                      onClick={() => { setActiveLocIdx(idx); fetchSchedule(loc.location_name); }}
                      style={{cursor: 'pointer'}}
                    >
                      <div className={styles.locName}>{loc.location_name}</div>
                      <div className={styles.locProb}>{(loc.probability || 0).toFixed(1)}%</div>
                      <div className={`${styles.locTrend} ${getTrendClass(loc.trend)}`}>{loc.trend}</div>
                    </div>
                  ))}
                </div>
              )}

              <div className={styles.timelineArea}>
                <div className={styles.timeline}>
                  {itinerary && itinerary.timeline && itinerary.timeline.map((step, idx) => (
                    <div key={idx} className={styles.timelineItem}>
                      <div className={styles.time}>{step.time}</div>
                      <div className={styles.locationTag}>📍 {step.location}</div>
                      <div className={styles.action}>{step.action}</div>
                      <div className={styles.note}>{step.note}</div>
                    </div>
                  ))}
                  {!itinerary && <div className={styles.loadingText}>Không tìm thấy lộ trình phù hợp.</div>}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Right Panel: Cảnh báo Săn Mây */}
        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <div className={styles.panelTitle}>🔔 Cảnh báo Săn Mây</div>
          </div>
          
          <div className={styles.feedArea}>
            {loading ? (
              <div className={styles.loadingText}>Đang tải...</div>
            ) : notifications.length > 0 ? (
              notifications.map((notif, idx) => (
                <div 
                  key={idx} 
                  className={styles.notificationCard}
                  style={{cursor: 'pointer'}}
                  onClick={() => {
                    if (notif.probability >= 50) {
                      setActiveLocIdx(-1); // Deselect cards
                      fetchSchedule(notif.location_name);
                    } else {
                      alert(`⚠️ ${notif.location_name} đang có thời tiết xấu, hãy bấm vào các địa điểm an toàn khác ở cột bên trái nhé!`);
                    }
                  }}
                >
                  <div className={styles.notifHeader}>
                    <div className={styles.notifLoc}>
                      <span className={`${styles.indicator} ${getIndicatorClass(notif.probability)}`}></span>
                      {notif.location_name}
                    </div>
                    <div className={styles.notifTime}>{new Date(notif.timestamp).toLocaleTimeString('vi-VN')}</div>
                  </div>
                  <div className={styles.notifMsg}>{notif.message}</div>
                </div>
              ))
            ) : (
              <div className={styles.loadingText}>Chưa có cảnh báo nào!</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
