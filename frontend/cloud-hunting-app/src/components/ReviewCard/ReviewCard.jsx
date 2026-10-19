import { useState, useCallback, useEffect } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import styles from './ReviewCard.module.css';
import { generateTourId, fetchReviews, postReview, editReview, deleteReview, likeReview, unlikeReview } from '../../bridge/s4_api';
import NearbyUtilitiesPanel from '../NearbyUtilities/NearbyUtilitiesPanel';
import DeleteConfirmModal from '../DeleteConfirmModal/DeleteConfirmModal';
import { getSmartStartTime } from '../../utils/timeUtils';


function getStarsText(rating) {
  let result = '';
  for (let i = 0; i < 5; i++) {
    result += i < rating ? '⭐' : '☆';
  }
  return result;
}

function titleCase(str) {
  return str
    .split(' ')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

// Star Rating sub-component
function StarRating({ rating, onRate }) {
  const [hoverRating, setHoverRating] = useState(0);
  const displayRating = hoverRating || rating;

  return (
    <div
      className={styles.starRating}
      onMouseLeave={() => setHoverRating(0)}
    >
      {[1, 2, 3, 4, 5].map((value) => (
        <span
          key={value}
          className={`${styles.star} ${value <= displayRating ? styles.starActive : ''}`}
          onMouseOver={() => setHoverRating(value)}
          onClick={() => onRate(value)}
        >
          ★
        </span>
      ))}
    </div>
  );
}

export default function ReviewCard() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const locName = searchParams.get('name');
  const displayName = locName ? titleCase(locName) : 'Đồi Chè Cầu Đất';
  const tourId = generateTourId(displayName.toLowerCase());

  const [reviews, setReviews] = useState([]);
  const [currentRating, setCurrentRating] = useState(5);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);

  // States for right panel
  const [activeTab, setActiveTab] = useState('reviews'); // 'reviews' | 'utilities'
  
  // Modal states
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [suggestedTime, setSuggestedTime] = useState(null);
  const [loadingSuggestion, setLoadingSuggestion] = useState(false);

  // Edit states
  const [editingReviewId, setEditingReviewId] = useState(null);

  // Delete states
  const [deletingReviewId, setDeletingReviewId] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Like states
  const [likedReviews, setLikedReviews] = useState(() => {
    const stored = localStorage.getItem('likedReviews');
    return stored ? JSON.parse(stored) : {};
  });

  const toggleLikedReviewLocally = (reviewId, isLiked) => {
    setLikedReviews(prev => {
      const newState = { ...prev };
      if (isLiked) newState[reviewId] = true;
      else delete newState[reviewId];
      localStorage.setItem('likedReviews', JSON.stringify(newState));
      return newState;
    });
  };
  const [editRating, setEditRating] = useState(5);
  const [editComment, setEditComment] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);

  // Parse JWT to get current user ID
  const token = localStorage.getItem('accessToken');
  let currentUserId = null;
  if (token) {
    try {
      let base64Url = token.split('.')[1];
      let base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const padLength = (4 - (base64.length % 4)) % 4;
      base64 += '='.repeat(padLength);
      
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      
      const payload = JSON.parse(jsonPayload);
      currentUserId = parseInt(payload.sub, 10);
    } catch (e) {
      console.error('Invalid token', e);
    }
  }

  // Load reviews on mount
  const loadReviews = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchReviews(tourId);
      // Backend trả về mảng reviews, sắp xếp mới nhất lên đầu
      if (Array.isArray(data)) {
        const sortedData = data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        setReviews(sortedData);
      } else {
        setReviews([]);
      }
    } catch (err) {
      console.error('Failed to load reviews:', err);
      setReviews([]);
    } finally {
      setLoading(false);
    }
  }, [tourId]);

  useEffect(() => {
    loadReviews();
  }, [loadReviews]);

  // Calculate average rating
  const avgRating = reviews.length > 0
    ? (reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length).toFixed(1)
    : '0';

  const handleSubmit = useCallback(async () => {
    if (!comment.trim()) {
      alert('Vui lòng nhập nội dung!');
      return;
    }
    if (!currentUserId) {
      alert('Vui lòng đăng nhập để đánh giá!');
      return;
    }

    setSubmitting(true);
    try {
      await postReview(tourId, currentRating, comment, displayName);
      setComment('');
      setCurrentRating(5);
      // Reload reviews sau khi post thành công
      await loadReviews();
    } catch (err) {
      alert(err.message || 'Lỗi gửi đánh giá');
    } finally {
      setSubmitting(false);
    }
  }, [comment, currentRating, tourId, loadReviews, currentUserId, displayName]);

  const handleEditClick = (rv) => {
    setEditingReviewId(rv.id);
    setEditRating(rv.rating);
    setEditComment(rv.comment);
  };

  const handleCancelEdit = () => {
    setEditingReviewId(null);
  };

  const handleSaveEdit = async (review_id) => {
    if (!editComment.trim()) {
      alert('Nội dung không được để trống!');
      return;
    }
    
    setSavingEdit(true);
    try {
      await editReview(review_id, editRating, editComment);
      setEditingReviewId(null);
      await loadReviews();
    } catch (err) {
      alert(err.message || 'Lỗi cập nhật đánh giá');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDeleteClick = (review_id) => {
    setDeletingReviewId(review_id);
  };

  const confirmDeleteReview = async () => {
    if (deletingReviewId === null) return;
    setIsDeleting(true);
    try {
      await deleteReview(deletingReviewId);
      setDeletingReviewId(null);
      await loadReviews();
    } catch (err) {
      alert(err.message || 'Lỗi xóa đánh giá');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleLikeClick = async (review_id) => {
    const isCurrentlyLiked = likedReviews[review_id];
    try {
      if (isCurrentlyLiked) {
        await unlikeReview(review_id);
        toggleLikedReviewLocally(review_id, false);
      } else {
        await likeReview(review_id);
        toggleLikedReviewLocally(review_id, true);
      }
      await loadReviews();
    } catch (err) {
      alert(err.message || 'Lỗi khi thả/huỷ tim');
    }
  };

  const handleSuggestStartTime = async () => {
    setLoadingSuggestion(true);
    try {
      const token = localStorage.getItem('accessToken');
      const headers = { 
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      };
      const payload = {
          user_id: currentUserId ? String(currentUserId) : "guest",
          start_time: getSmartStartTime(location.state?.timeOffset || 0),
          start_location: "Trung tâm",
          max_distance_km: 30.0,
          travel_style: "Sống ảo nhẹ nhàng",
          preferred_vibe: "Thương mại",
          vehicle_type: "xe máy",
          selected_location: displayName
      };
      const res = await fetch('/api/s6/recommend', {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        const primaryLoc = data.recommended_locations?.[0];
        const departureStep = data.timeline?.find(s => s.action.toLowerCase().includes("xuất phát"));
        
        if (primaryLoc && departureStep) {
          setSuggestedTime({
            bestTime: primaryLoc.best_time,
            departTime: departureStep.time,
            prob: primaryLoc.probability
          });
        } else {
          alert("Không thể tính toán được thời gian phù hợp lúc này.");
        }
      } else {
        alert("Có lỗi xảy ra khi kết nối máy chủ AI.");
      }
    } catch (e) {
      console.error(e);
      alert("Lỗi khi lấy gợi ý thời gian.");
    } finally {
      setLoadingSuggestion(false);
    }
  };

  return (
    <div className={styles.reviewCard}>
      {/* Left Panel: Header + Image */}
      <div className={styles.leftPanel}>
        <div className={styles.cardHeader}>
          <button className={styles.backBtn} onClick={() => navigate('/results', { state: location.state })}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            Quay lại Danh sách
          </button>
          <h2>Đánh giá {displayName}</h2>
          <p>Rating trung bình: {avgRating} ⭐ ({reviews.length} lượt)</p>
        </div>
        <div className={styles.locationImage}>
          <img
            src={location.state?.image_url || "https://images.unsplash.com/photo-1596704144574-e8620ba0606f?auto=format&fit=crop&w=800&q=80"}
            alt={displayName}
          />
          <div className={styles.actionButtons}>
            <button className={styles.utilityBtn} onClick={() => navigate('/booking', { state: { ...location.state, name: displayName } })}>
              ☕ Khám phá Tiện ích
            </button>
          </div>
        </div>
      </div>



      {/* Right Area: Viewport for Sliding Panels */}
      <div className={styles.rightAreaViewport}>
        <div className={`${styles.slidingContainer} ${activeTab === 'utilities' ? styles.slideLeft : ''}`}>
          
          {/* Panel 1: Reviews */}
          <div className={styles.reviewsPanel}>
            {/* Review List */}
            <div className={styles.reviewList}>
          {loading ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#64748b' }}>Đang tải đánh giá...</div>
          ) : reviews.length === 0 ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#64748b' }}>Chưa có đánh giá nào. Hãy là người đầu tiên!</div>
          ) : reviews.map((rv, index) => (
            <div key={index} className={styles.reviewItem}>
              {editingReviewId === rv.id ? (
                <div className={styles.editMode}>
                  <div style={{ marginBottom: '10px' }}>
                    <StarRating rating={editRating} onRate={setEditRating} />
                  </div>
                  <textarea
                    className={styles.commentText}
                    style={{ minHeight: '60px', marginBottom: '10px' }}
                    value={editComment}
                    onChange={(e) => setEditComment(e.target.value)}
                  />
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button 
                      className={styles.submitBtn} 
                      style={{ padding: '8px 16px', flex: 1 }}
                      onClick={() => handleSaveEdit(rv.id)}
                      disabled={savingEdit}
                    >
                      {savingEdit ? 'Đang lưu...' : 'Lưu lại'}
                    </button>
                    <button 
                      className={styles.backBtn} 
                      style={{ position: 'relative', top: 0, left: 0, flex: 1, textAlign: 'center' }}
                      onClick={handleCancelEdit}
                      disabled={savingEdit}
                    >
                      Hủy
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className={styles.reviewMeta}>
                    <span className={styles.userId}>
                      {rv.display_name || rv.username || `User #${rv.user_id}`}
                      {rv.user_id === currentUserId && (
                        <>
                          <span 
                            style={{ marginLeft: '10px', fontSize: '12px', color: '#0284c7', cursor: 'pointer', fontWeight: 'normal' }}
                            onClick={() => handleEditClick(rv)}
                          >
                            [Sửa]
                          </span>
                          <span 
                            style={{ marginLeft: '8px', fontSize: '12px', color: '#ef4444', cursor: 'pointer', fontWeight: 'normal' }}
                            onClick={() => handleDeleteClick(rv.id)}
                          >
                            [Xóa]
                          </span>
                        </>
                      )}
                    </span>
                    <span className={styles.rating}>
                      {getStarsText(rv.rating)}
                    </span>
                  </div>
                  <div className={styles.reviewText}>{rv.comment}</div>
                  <div className={styles.reviewTime} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>
                      {rv.created_at 
                        ? new Date(rv.created_at.endsWith('Z') ? rv.created_at : rv.created_at + 'Z').toLocaleString('vi-VN') 
                        : 'Vừa xong'}
                    </span>
                    <button 
                      onClick={() => handleLikeClick(rv.id)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px', color: likedReviews[rv.id] ? '#ef4444' : '#6b7280', fontSize: '14px', fontWeight: likedReviews[rv.id] ? 'bold' : 'normal' }}
                      title={likedReviews[rv.id] ? "Bỏ thích" : "Thích bình luận này"}
                    >
                      {likedReviews[rv.id] ? '❤️' : '♡'} {rv.helpful_count || 0}
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>

        {/* Floating Action Buttons */}
        <div style={{
          position: 'sticky',
          bottom: '15px',
          display: 'flex',
          gap: '10px',
          justifyContent: 'flex-end',
          marginRight: '15px',
          marginTop: '15px',
          zIndex: 10
        }}>
          <button 
            onClick={handleSuggestStartTime}
            disabled={loadingSuggestion}
            style={{
              padding: '12px 24px',
              background: 'linear-gradient(135deg, #0ea5e9, #0284c7)',
              color: 'white',
              border: 'none',
              borderRadius: '25px',
              fontWeight: 'bold',
              fontSize: '1rem',
              cursor: loadingSuggestion ? 'wait' : 'pointer',
              boxShadow: '0 4px 15px rgba(14, 165, 233, 0.4)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              opacity: loadingSuggestion ? 0.7 : 1
            }}
          >
            {loadingSuggestion ? '⏳ Đang tính toán...' : '🤖 Gợi ý thời điểm bắt đầu'}
          </button>
          <button 
            className={styles.writeReviewFloatBtn}
            onClick={() => setShowReviewModal(true)}
            style={{
              padding: '12px 24px',
              background: 'linear-gradient(135deg, #10b981, #059669)',
              color: 'white',
              border: 'none',
              borderRadius: '25px',
              fontWeight: 'bold',
              fontSize: '1rem',
              cursor: 'pointer',
              boxShadow: '0 4px 15px rgba(16, 185, 129, 0.4)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            ✍️ Viết đánh giá
          </button>
        </div>

        {/* Review Form Modal */}
        {showReviewModal && (
          <div onClick={() => setShowReviewModal(false)} style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)', zIndex: 9999, display: 'flex', justifyContent: 'center', alignItems: 'center'
          }}>
            <div onClick={e => e.stopPropagation()} style={{
              background: 'white', padding: '25px', borderRadius: '15px', width: '90%', maxWidth: '500px',
              boxShadow: '0 10px 30px rgba(0,0,0,0.2)'
            }}>
              <h3 style={{ margin: '0 0 15px 0', color: '#1e293b' }}>Đánh giá trải nghiệm của bạn</h3>
              <StarRating rating={currentRating} onRate={setCurrentRating} />
              <textarea
                className={styles.commentText}
                placeholder="Chia sẻ trải nghiệm săn mây của bạn..."
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                style={{ width: '100%', minHeight: '100px', marginTop: '15px', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', boxSizing: 'border-box' }}
              />
              <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
                <button
                  className={styles.submitBtn}
                  onClick={() => {
                    handleSubmit();
                    if (comment.trim() && currentUserId) setShowReviewModal(false);
                  }}
                  disabled={submitting}
                  style={{ flex: 1, padding: '12px', background: '#0ea5e9', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}
                >
                  {submitting ? 'Đang gửi...' : 'Gửi đánh giá'}
                </button>
                <button
                  onClick={() => setShowReviewModal(false)}
                  style={{ flex: 1, padding: '12px', background: '#f1f5f9', color: '#475569', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}
                >
                  Hủy
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Suggestion Time Modal */}
        {suggestedTime && (
          <div onClick={() => setSuggestedTime(null)} style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)', zIndex: 9999, display: 'flex', justifyContent: 'center', alignItems: 'center'
          }}>
            <div onClick={e => e.stopPropagation()} style={{
              background: 'white', padding: '30px', borderRadius: '20px', width: '90%', maxWidth: '400px',
              boxShadow: '0 10px 40px rgba(0,0,0,0.3)', textAlign: 'center'
            }}>
              <div style={{ fontSize: '3rem', marginBottom: '10px' }}>⏰</div>
              <h3 style={{ margin: '0 0 10px 0', color: '#0f172a', fontSize: '1.4rem' }}>Gợi ý Lịch Trình Săn Mây</h3>
              <p style={{ color: '#475569', fontSize: '1rem', lineHeight: '1.6', marginBottom: '20px' }}>
                AI dự báo thời điểm <strong>{displayName}</strong> có mây đẹp nhất là vào lúc <strong style={{ color: '#0ea5e9', fontSize: '1.2rem' }}>{suggestedTime.bestTime}</strong> (Tỷ lệ: {(suggestedTime.prob || 0).toFixed(0)}%).
                <br /><br />
                Đã trừ hao thời gian di chuyển và leo núi, bạn nên xuất phát vào lúc:
              </p>
              <div style={{
                background: 'linear-gradient(135deg, #f0f9ff, #e0f2fe)',
                padding: '20px',
                borderRadius: '15px',
                border: '2px dashed #38bdf8',
                marginBottom: '25px'
              }}>
                <span style={{ fontSize: '2.5rem', fontWeight: 'bold', color: '#0284c7' }}>{suggestedTime.departTime}</span>
              </div>
              
              <button
                onClick={() => setSuggestedTime(null)}
                style={{ width: '100%', padding: '12px', background: '#0ea5e9', color: 'white', border: 'none', borderRadius: '10px', fontWeight: 'bold', cursor: 'pointer', fontSize: '1.1rem' }}
              >
                Đã hiểu!
              </button>
            </div>
          </div>
        )}
          </div>

          {/* Panel 2: Utilities */}
          <div className={styles.utilitiesPanel}>
            <NearbyUtilitiesPanel 
              onBack={() => setActiveTab('reviews')} 
              locName={displayName} 
              lat={location.state?.lat} 
              lon={location.state?.lon} 
            />
          </div>

        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmModal
        isOpen={deletingReviewId !== null}
        onClose={() => setDeletingReviewId(null)}
        onConfirm={confirmDeleteReview}
        isDeleting={isDeleting}
      />
    </div>
  );
}
