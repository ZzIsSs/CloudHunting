from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import math

from .schemas import UserPreferenceRequest, PlanBRequest, LocationData, ItineraryStep, ItineraryResponse
from .database import UserPreferenceLog, NotificationLog
from .integrations import fetch_s1_prediction, fetch_s5_trend

import os
import json

# Đường dẫn tới file JSON lưu cấu hình dùng chung
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOTSPOTS_JSON_PATH = os.path.join(BASE_DIR, "shared", "hotspots.json")

try:
    with open(HOTSPOTS_JSON_PATH, "r", encoding="utf-8") as f:
        LOCATIONS = json.load(f)
except Exception as e:
    print(f"⚠️ [S6] Không thể đọc file hotspots.json: {e}")
    LOCATIONS = []

import requests

def geocode_location(address: str) -> tuple[float, float]:
    """
    Sử dụng OpenStreetMap Nominatim API để chuyển đổi địa chỉ dạng text thành tọa độ GPS thực tế.
    Ví dụ: 'Số 1 Trần Phú, Phường 3, Đà Lạt' -> (11.939, 108.435).
    Nếu không tìm thấy tọa độ hoặc có lỗi xảy ra, hàm sẽ trả về tọa độ mặc định (Chợ Đà Lạt).
    """
    default_coords = (11.940419, 108.458313) # Chợ Đà Lạt
    if not address or not address.strip():
        return default_coords
        
    try:
        print(f"🌍 [Geocoding] Đang phân tích tọa độ cho địa chỉ: '{address}'...")
        url = "https://nominatim.openstreetmap.org/search"
        # Bổ sung chữ Đà Lạt để tối ưu kết quả tìm kiếm nếu người dùng nhập thiếu
        search_query = address if "đà lạt" in address.lower() or "da lat" in address.lower() else f"{address}, Đà Lạt"
        
        params = {
            "q": search_query,
            "format": "json",
            "limit": 1
        }
        headers = {
            "User-Agent": "CloudHuntingApp/1.0"
        }
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                print(f"✅ [Geocoding] Thành công: {lat}, {lon}")
                return lat, lon
                
        print("⚠️ [Geocoding] Không tìm thấy tọa độ. Trả về mặc định (Chợ Đà Lạt).")
    except Exception as e:
        print(f"❌ [Geocoding] Lỗi khi gọi API: {e}. Trả về mặc định.")
        
    return default_coords

def get_real_route(lat1, lon1, lat2, lon2) -> tuple[float, int]:
    """
    Tính khoảng cách ước lượng bằng đường chim bay (x 1.5 hệ số đường đèo).
    Đã tắt gọi OSRM API công cộng vì gọi trong vòng lặp gây nghẽn cổ chai (Chậm & Timeout).
    """
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    dist_km = (R * c) * 1.5
    return dist_km, int(dist_km * 2) # Giả định tốc độ 30km/h

def save_user_preference(db: Session, req: UserPreferenceRequest):
    """
    Lưu lại các thông tin thiết lập/sở thích của người dùng (như phong cách, khoảng cách, loại xe...) vào CSDL.
    """
    log = UserPreferenceLog(
        user_id=req.user_id,
        start_time=req.start_time,
        max_distance_km=req.max_distance_km,
        travel_style=req.travel_style,
        preferred_vibe=req.preferred_vibe,
        vehicle_type=req.vehicle_type
    )
    db.add(log)
    db.commit()
    return log

def score_locations(req: UserPreferenceRequest) -> list[LocationData]:
    """
    Module 2: Đánh giá mức độ phù hợp của các địa điểm săn mây.
    Lọc các điểm vượt khoảng cách hoặc ô tô không vào được. 
    Chấm điểm dựa trên S1 (Tỷ lệ mây), S5 (Xu hướng) và Sở thích (Style, Vibe).
    """
    scored_list = []
    start_lat, start_lon = geocode_location(req.start_location)
    
    # Parse start_time to check against opening_time
    try:
        start_dt = datetime.strptime(req.start_time, "%H:%M")
        start_hour = start_dt.hour + start_dt.minute / 60.0
    except:
        start_hour = 4.0 # Default fallback
    
    for loc in LOCATIONS:
        # Tính khoảng cách và thời gian chạy xe từ điểm xuất phát tới điểm săn mây bằng OSRM
        distance_km, est_drive_mins = get_real_route(start_lat, start_lon, loc["lat"], loc["lon"])
        trekking_mins = loc.get("trekking_mins", 0)
        total_travel_mins = est_drive_mins + trekking_mins
        
        # Hard Filter 1: Vượt quá khoảng cách -> Loại khỏi danh sách
        if distance_km > req.max_distance_km:
            continue
            
        # Hard Filter 2: Đi ô tô nhưng điểm đến không hỗ trợ -> Loại
        if req.vehicle_type.lower() == "ô tô" and not loc["car_accessible"]:
            continue
            
        # Hard Filter 3: Check opening time
        arrive_hour = start_hour + (total_travel_mins / 60.0)
        # If arrive time > 24, wrap around
        if arrive_hour >= 24:
            arrive_hour -= 24
            
        if loc.get("opening_time", 0) > 0 and arrive_hour < loc.get("opening_time", 0):
            continue
            
        # Gọi qua S1 và S5
        s1_data = fetch_s1_prediction(loc["name"], loc["lat"], loc["lon"])
        prob = s1_data.get("probability", 0.0)
        best_time = s1_data.get("best_time", None)
        trend = fetch_s5_trend(loc["name"])
        
        # Hard Filter 4: Tỷ lệ mây quá thấp hoặc thời tiết xấu (< 30%) -> Loại
        if prob < 30.0:
            continue
            
        # 1. Điểm mây: (từ 0-100)
        score = prob
        
        # 2. Điểm Trend (S5)
        if trend == "Tăng":
            score += 10
        elif trend == "Giảm":
            score -= 10
            
        # 3. Soft Score: Chấm điểm Sở thích
        if loc["style"] == req.travel_style:
            score += 20
        else:
            score -= 20
            
        if loc["vibe"] == req.preferred_vibe:
            score += 20
        else:
            score -= 20
            
        # Cập nhật vào đối tượng trả về
        scored_list.append(LocationData(
            location_name=loc["name"],
            lat=loc["lat"],
            lon=loc["lon"],
            probability=prob,
            best_time=best_time,
            trend=trend,
            score=max(0.0, score) # Không cho điểm âm
        ))
        
    # Sắp xếp từ cao xuống thấp
    scored_list.sort(key=lambda x: x.score, reverse=True)
    return scored_list

def generate_itinerary(req: UserPreferenceRequest, best_locations: list[LocationData], is_stop_scenario: bool = False, is_safe_fallback: bool = False) -> ItineraryResponse:
    """
    Module 3 & 4: Sắp xếp phân chia và đóng gói lịch trình (Timeline).
    Cung cấp các mốc thời gian xuất phát, ghé quán cafe, giờ bình minh, giờ chụp ảnh đẹp nhất.
    Hỗ trợ sinh lộ trình dừng chân khẩn cấp nếu thời tiết xấu (is_stop_scenario).
    """
    if is_safe_fallback:
        message = f"🚨 Cảnh báo: Không có địa điểm săn mây nào phù hợp. S6 đề xuất bạn khám phá các tiện ích gần khu vực {req.start_location} thay vì leo đèo."
        try:
            start_dt = datetime.strptime(req.start_time, "%H:%M")
        except:
            start_dt = datetime.now().replace(second=0, microsecond=0)
        
        coffee_dt = start_dt + timedelta(hours=3)
        
        # Tạo danh sách tiện ích ảo gần nơi nhập
        nearby_amenities = [
            LocationData(
                location_name=f"Quán Cafe view đẹp quanh {req.start_location}",
                lat=0.0, lon=0.0, probability=0.0, trend="Đi ngang", score=0.0
            ),
            LocationData(
                location_name=f"Quán ăn sáng đặc sản quanh {req.start_location}",
                lat=0.0, lon=0.0, probability=0.0, trend="Đi ngang", score=0.0
            ),
            LocationData(
                location_name=f"Khu vui chơi / Check-in an toàn quanh {req.start_location}",
                lat=0.0, lon=0.0, probability=0.0, trend="Đi ngang", score=0.0
            )
        ]
        
        timeline = [
            ItineraryStep(
                time=start_dt.strftime("%H:%M"),
                action="Nghỉ ngơi tại chỗ",
                location=req.start_location,
                note="Thời tiết đi đường đèo quá nguy hiểm. Hãy nghỉ ngơi thêm một chút để đảm bảo sức khỏe."
            ),
            ItineraryStep(
                time=coffee_dt.strftime("%H:%M"),
                action="Khám phá tiện ích gần bạn",
                location=f"Khu vực {req.start_location}",
                note="Dạo quanh khu vực bạn đang ở để thưởng thức bữa sáng nóng hổi, nhâm nhi ly cafe và tận hưởng không khí lạnh an toàn."
            )
        ]
        return ItineraryResponse(
            user_id=req.user_id,
            recommended_locations=nearby_amenities,
            timeline=timeline,
            message=message
        )

    # Mặc định lấy top 1 điểm săn mây tốt nhất làm đích đến chính
    primary_dest = best_locations[0] if best_locations else None
    
    # Nếu người dùng có chỉ định rõ muốn xem lịch trình của 1 điểm cụ thể
    if getattr(req, "selected_location", None):
        found = False
        # Tìm trong danh sách best_locations trước
        for loc in best_locations:
            if loc.location_name.lower() == req.selected_location.lower():
                primary_dest = loc
                found = True
                break
        
        # Nếu điểm bị loại khỏi best_locations (do thời tiết xấu, ở xa...), vẫn cho phép lên lịch trình cho điểm đó
        if not found:
            for loc in LOCATIONS:
                if loc["name"].lower() == req.selected_location.lower():
                    # Gọi lại API lấy tỉ lệ mây mới nhất
                    s1_data = fetch_s1_prediction(loc["name"], loc["lat"], loc["lon"])
                    prob = s1_data.get("probability", 0.0)
                    best_time = s1_data.get("best_time", None)
                    trend = fetch_s5_trend(loc["name"])
                    primary_dest = LocationData(
                        location_name=loc["name"],
                        lat=loc["lat"],
                        lon=loc["lon"],
                        probability=prob,
                        best_time=best_time,
                        trend=trend,
                        score=0.0 # Score thấp do bị loại
                    )
                    break
    
    # Nếu vẫn không có primary_dest (VD: best_locations rỗng và không tìm thấy location), trả về mảng rỗng
    if not primary_dest:
        return ItineraryResponse(
            user_id=req.user_id,
            recommended_locations=[],
            timeline=[],
            message="Không tìm thấy điểm đến nào phù hợp."
        )
    
    # Tính toán thời gian di chuyển thực tế (Module 3) bằng OSRM
    start_lat, start_lon = geocode_location(req.start_location)
    distance_km, travel_time_mins = get_real_route(start_lat, start_lon, primary_dest.lat, primary_dest.lon)
    
    # Lấy thêm thời gian trekking từ dữ liệu gốc
    trekking_mins = 0
    for loc in LOCATIONS:
        if loc["name"] == primary_dest.location_name:
            trekking_mins = loc.get("trekking_mins", 0)
            break
            
    total_travel_mins = travel_time_mins + trekking_mins
    
    if is_stop_scenario:
        message = "Đã tìm thấy nơi an toàn để dừng chân!"
    elif primary_dest.score < 50:
        message = "Thời tiết không lý tưởng, bạn có thể cân nhắc lại việc đi săn mây hôm nay."
    else:
        message = "Đã tìm thấy lộ trình tuyệt vời nhất cho bạn!"

    # Reverse Scheduling từ best_time
    peak_dt = None
    if getattr(primary_dest, "best_time", None):
        best_str = primary_dest.best_time
        try:
            if "T" in best_str:
                peak_dt = datetime.fromisoformat(best_str.replace('Z', ''))
            else:
                # Format từ Open-Meteo (S1) thường là "%H:%M %d/%m"
                # Thêm năm hiện tại để datetime hiểu trọn vẹn
                peak_dt = datetime.strptime(best_str + f"/{datetime.now().year}", "%H:%M %d/%m/%Y")
        except Exception:
            peak_dt = None

    if peak_dt:
        arrive_peak_dt = peak_dt
        arrive_parking_dt = arrive_peak_dt - timedelta(minutes=trekking_mins)
        start_dt = arrive_parking_dt - timedelta(minutes=travel_time_mins)
        sunrise_dt = arrive_peak_dt + timedelta(minutes=30)
        breakfast_dt = sunrise_dt + timedelta(hours=1, minutes=30)
    else:
        # Fallback (Forward Scheduling)
        try:
            start_dt = datetime.strptime(req.start_time, "%H:%M")
        except:
            start_dt = datetime.now().replace(second=0, microsecond=0)
        arrive_parking_dt = start_dt + timedelta(minutes=travel_time_mins)
        arrive_peak_dt = arrive_parking_dt + timedelta(minutes=trekking_mins)
        sunrise_dt = arrive_peak_dt + timedelta(minutes=30)
        breakfast_dt = sunrise_dt + timedelta(hours=1, minutes=30)
    
    if is_stop_scenario:
        timeline = [
            ItineraryStep(
                time=start_dt.strftime("%H:%M"),
                action="Quay xe / Thay đổi lộ trình",
                location=req.start_location,
                note="Bật đèn sương mù, di chuyển chậm lại."
            ),
            ItineraryStep(
                time=arrive_parking_dt.strftime("%H:%M"),
                action="Dừng chân an toàn",
                location=primary_dest.location_name,
                lat=primary_dest.lat,
                lon=primary_dest.lon,
                note="Tìm chỗ trú ấm áp, tránh gió lạnh và sương mù."
            ),
            ItineraryStep(
                time=sunrise_dt.strftime("%H:%M"),
                action="Nghỉ ngơi & Chill",
                location=primary_dest.location_name,
                note="Nhâm nhi đồ uống nóng, giữ ấm cơ thể thay vì cố chạy đua với mặt trời."
            )
        ]
    else:
        # Thời gian bình minh và chụp ảnh
        sunrise_dt = arrive_peak_dt + timedelta(minutes=15)
        golden_hour_dt = sunrise_dt + timedelta(minutes=30)
        
        timeline = [
            ItineraryStep(
                time=start_dt.strftime("%H:%M"),
                action="Xuất phát",
                location=req.start_location,
                note=f"Khoảng cách: {distance_km:.1f} km. Lái xe dự kiến {travel_time_mins} phút. Tỷ lệ mây: {primary_dest.probability}%."
            ),
            ItineraryStep(
                time=arrive_parking_dt.strftime("%H:%M"),
                action="Đến nơi / Gửi xe",
                location=primary_dest.location_name,
                lat=primary_dest.lat,
                lon=primary_dest.lon,
                note="Nghỉ ngơi 5 phút, chuẩn bị đèn pin và đồ đạc."
            )
        ]
        
        if trekking_mins > 0:
            timeline.append(ItineraryStep(
                time=arrive_peak_dt.strftime("%H:%M"),
                action="Lên tới đỉnh",
                location=primary_dest.location_name,
                note=f"Đã hoàn tất {trekking_mins} phút leo núi/đi bộ."
            ))
            
        timeline.extend([
            ItineraryStep(
                time=(arrive_parking_dt + timedelta(minutes=10)).strftime("%H:%M"),
                action="Gợi ý điểm dừng chân / Cafe săn mây",
                location=f"Khu vực quanh {primary_dest.location_name}",
                lat=primary_dest.lat,
                lon=primary_dest.lon,
                note="Trên đường tới nơi, hãy ghé vào những tiệm cafe có view đồi cao hoặc các bãi đá nổi tiếng tại khu vực này - đây là những tọa độ săn mây đẹp và lý tưởng nhất để bạn vừa nhâm nhi nước ấm vừa ngắm cảnh."
            ),
            ItineraryStep(
                time=sunrise_dt.strftime("%H:%M"),
                action="Thời gian bình minh lên",
                location=primary_dest.location_name,
                note="Mặt trời bắt đầu ló rạng, sương tan dần và biển mây xuất hiện."
            ),
            ItineraryStep(
                time=golden_hour_dt.strftime("%H:%M"),
                action="Thời gian chụp hình đẹp nhất",
                location=primary_dest.location_name,
                note="Ánh sáng rực rỡ nhất (Golden Hour) - Thời điểm hoàn hảo để bắt trọn những bức ảnh để đời."
            )
        ])
    
    return ItineraryResponse(
        user_id=req.user_id,
        recommended_locations=best_locations[:3], # Trả về top 3 để tham khảo
        timeline=timeline,
        message=message
    )

def scan_and_notify_opportunities(db: Session):
    """
    Background Job: Quét tự động toàn bộ địa điểm, lấy tỷ lệ mây từ S1. 
    Nếu >= 85% và chưa cảnh báo trong 12 tiếng qua, tạo Notification mới để chống spam.
    """
    print("\n🔍 [Auto-Scan] Đang quét tìm cơ hội săn mây...")
    now = datetime.now()
    # Cooldown 12 tiếng để chống Spam
    cutoff_time = (now - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")
    
    for loc in LOCATIONS:
        prob = fetch_s1_prediction(loc["name"], loc["lat"], loc["lon"]).get("probability", 0.0)

        if prob >= 85.0:
            # Kiểm tra xem trong 12 tiếng qua đã báo chỗ này chưa
            recent_log = db.query(NotificationLog).filter(
                NotificationLog.location_name == loc["name"],
                NotificationLog.timestamp >= cutoff_time
            ).first()
            
            if not recent_log:
                # Nếu chưa báo, tạo cảnh báo mới
                msg = f"Cơ hội vàng! {loc['name']} đang có tỷ lệ mây {int(prob)}%. Xuất phát ngay!"
                print(f"🔔 TING TING: {msg}")
                
                new_noti = NotificationLog(
                    location_name=loc["name"],
                    message=msg,
                    probability=int(prob),
                    timestamp=now.strftime("%Y-%m-%d %H:%M:%S")
                )
                db.add(new_noti)
                db.commit()
    print("✅ [Auto-Scan] Hoàn tất quét.")


def switch_to_plan_b(req: PlanBRequest) -> ItineraryResponse:
    """
    Tính năng Cứu nét (Plan B): Kiểm tra thời tiết điểm đến hiện tại.
    Nếu xấu (< 60%), tìm điểm thay thế tốt nhất có áp dụng phạt khoảng cách (Distance Penalty).
    Nếu điểm thay thế quá xa (> 15km), khuyên tìm nơi dừng chân thay vì đi tiếp.
    """
    target_loc = next((l for l in LOCATIONS if l["name"] == req.current_target_location), None)
    
    # 1. Kiểm tra lại điểm đến hiện tại
    if target_loc:
        current_prob = fetch_s1_prediction(target_loc["name"], target_loc["lat"], target_loc["lon"]).get("probability", 0.0)
        if current_prob >= 60.0:
            # Thời tiết vẫn ổn, khuyên đi tiếp
            loc_data = LocationData(
                location_name=target_loc["name"], lat=target_loc["lat"], lon=target_loc["lon"], 
                probability=current_prob, trend="Đi ngang", score=100.0
            )
            itinerary = generate_itinerary(req, [loc_data])
            itinerary.message = f"Thời tiết tại {req.current_target_location} vẫn đang khá ổn ({current_prob}%). Hãy giữ vững lộ trình!"
            return itinerary

    # 2. Thời tiết thực sự xấu -> Tìm Plan B
    scored_list = []
    for loc in LOCATIONS:
        # Bỏ qua điểm đến đang bị xấu
        if loc["name"] == req.current_target_location:
            continue
            
        # Khoảng cách từ điểm săn mây "cũ" tới điểm "mới"
        distance_km, est_travel_mins = get_real_route(target_loc["lat"], target_loc["lon"], loc["lat"], loc["lon"])
        
        # Hard filter: Không đi được ô tô thì loại
        if req.vehicle_type.lower() == "ô tô" and not loc["car_accessible"]:
            continue
            
        prob = fetch_s1_prediction(loc["name"], loc["lat"], loc["lon"]).get("probability", 0.0)
        trend = fetch_s5_trend(loc["name"])
        score = prob
        if trend == "Tăng": score += 10
        elif trend == "Giảm": score -= 10
        
        if loc["style"] == req.travel_style: score += 20
        else: score -= 20
        if loc["vibe"] == req.preferred_vibe: score += 20
        else: score -= 20
        
        # 🚨 ĐIỂM NHẤN: Trừ điểm dựa trên khoảng cách (Distance Penalty)
        # Cứ mỗi 1km cách xa điểm đến cũ, trừ 3 điểm.
        # Ví dụ cách 10km sẽ bị trừ 30 điểm.
        score -= (distance_km * 3)
        
        scored_list.append(LocationData(
            location_name=loc["name"], lat=loc["lat"], lon=loc["lon"],
            probability=prob, trend=trend, score=max(0.0, score)
        ))
        
    scored_list.sort(key=lambda x: x.score, reverse=True)
    best_alt = scored_list[0]
    distance_to_alt, time_to_alt = get_real_route(target_loc["lat"], target_loc["lon"], best_alt.lat, best_alt.lon)
    
    # Nếu điểm thay thế quá xa (VD: > 15km), việc chạy đua với thời gian là không khả thi
    if distance_to_alt > 15.0:
        # Tạo một điểm giả định là nơi dừng chân
        cafe_loc = LocationData(
            location_name="Nơi dừng chân an toàn gần nhất", lat=target_loc["lat"], lon=target_loc["lon"],
            probability=0.0, trend="Đi ngang", score=0.0
        )
        itinerary = generate_itinerary(req, [cafe_loc], is_stop_scenario=True)
        itinerary.message = f"🚨 Mây đang tan nhanh nhưng điểm khả thi gần nhất cách tới {distance_to_alt:.1f}km! Việc di chuyển lúc này không an toàn. Đề xuất bạn tìm nơi dừng chân an toàn/quán cà phê gần nhất để nghỉ ngơi nhé!"
        return itinerary
        
    # Sinh lịch trình mới và ghi đè câu thông báo bẻ lái
    itinerary = generate_itinerary(req, scored_list)
    itinerary.message = f"🚨 Mây tại {req.current_target_location} đang tan nhanh. Đề xuất rẽ sang {best_alt.location_name} (Cách bạn khoảng {distance_to_alt:.1f}km)!"
    return itinerary
