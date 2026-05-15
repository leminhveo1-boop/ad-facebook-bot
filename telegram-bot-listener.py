import os, sys, requests, time, subprocess, json, threading
from datetime import datetime, timedelta
from flask import Flask

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ===== CAU HINH =====
BOT_TOKEN = "8761610260:AAErFpY0B4LZSdLEPQqI-HCU3QflDxcW8SM"
ALLOWED_CHAT_ID = "1966471122"
SCRIPT_DIR = r"f:\Antigravity\brain2\vault\Projects\ad-facebook"

FB_ACCESS_TOKEN = "EAAWretZAkV04BRQp9Gtoti6ZCHx3nGiB8eN2XKN9oxmpimFNSCvzEKM5p8WP9YZAIQKaRkcxZCG3PyKod9Xh6VhO9EuTRtrnMIcCti9eGLJrDnXC2aSVIXXGpwCaKViL1b0WTIQ3gqcNSCXCsx3uql6VfOVDqVPMFCj3ccSrbPsIXWfYZCWgR6gHukKkA8Abks0ezch9r0k0B7fUrNPWyY9fARLCBRiZB7PUtzKtiQ5iUUIxZAF3y5h5YaH8c8DoYlVsUZC5f6lI0ULnHW41hla1dAZDZD"
FB_AD_ACCOUNT_ID = "act_2087249431632156"
FB_APP_ID = "1595918954813262"

# Thoi gian check ROAS canh bao (giay) — mac dinh 4 tieng
ALERT_INTERVAL = 4 * 60 * 60
last_alert_check = 0

def get_fb_env():
    env = os.environ.copy()
    env["FB_ACCESS_TOKEN"] = FB_ACCESS_TOKEN
    env["FB_AD_ACCOUNT_ID"] = FB_AD_ACCOUNT_ID
    env["FB_APP_ID"] = FB_APP_ID
    env["PYTHONIOENCODING"] = "utf-8"
    return env

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    try:
        r = requests.get(url, params=params, timeout=35)
        return r.json()
    except:
        return None

def send_tg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        try:
            r = requests.post(url, json={"chat_id": ALLOWED_CHAT_ID, "text": chunk, "parse_mode": "HTML"}, timeout=10)
            if not r.ok:
                with open(os.path.join(SCRIPT_DIR, "logs", "tg_error.log"), "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] API Error: {r.status_code} - {r.text}\nText attempted:\n{chunk}\n\n")
                print(f"Loi gui TG: {r.text}")
        except Exception as e:
            with open(os.path.join(SCRIPT_DIR, "logs", "tg_error.log"), "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] Exception: {e}\n\n")
            print(f"Exception gui TG: {e}")

def run_script(script_name, args=None):
    """Chay 1 script va tra ve output"""
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, script_name)]
    if args:
        cmd.extend(args)
    try:
        result = subprocess.run(
            cmd,
            env=get_fb_env(), capture_output=True, text=True, timeout=120,
            encoding='utf-8', errors='replace'
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Loi: {e}"

# =====================================================
# CHUC NANG 1: BAO CAO NGAY (da co)
# =====================================================
def cmd_baocao(date="today"):
    if date == "today":
        send_tg("⏳ Đang lấy dữ liệu hôm nay...")
        run_script("fb-telegram-report.py")
    else:
        send_tg(f"⏳ Đang lấy dữ liệu ngày {date}...")
        run_script("fb-telegram-report.py", ["--date", date])

# =====================================================
# CHUC NANG 2: BAO CAO TUAN (7 ngay)
# =====================================================
def cmd_baocao_tuan():
    send_tg("⏳ Đang tổng hợp dữ liệu 7 ngày qua...")
    try:
        from facebook_business.api import FacebookAdsApi
        from facebook_business.adobjects.adaccount import AdAccount
        
        FacebookAdsApi.init(FB_APP_ID, "", FB_ACCESS_TOKEN)
        account = AdAccount(FB_AD_ACCOUNT_ID)
        
        fields = ['spend', 'actions', 'action_values', 'impressions', 'clicks', 'cpc', 'cpm', 'ctr']
        params = {'date_preset': 'last_7d'}
        insights = account.get_insights(fields=fields, params=params)
        
        if not insights:
            send_tg("📊 Tuần qua chưa có dữ liệu chi tiêu.")
            return
        
        data = insights[0]
        spend = float(data.get('spend', 0))
        impressions = int(data.get('impressions', 0))
        clicks = int(data.get('clicks', 0))
        cpc = float(data.get('cpc', 0))
        cpm = float(data.get('cpm', 0))
        ctr = float(data.get('ctr', 0))
        
        purchases = 0; purchase_value = 0.0; messages = 0
        for act in data.get('actions', []):
            t = act.get('action_type', '')
            if t in ['purchase', 'omni_purchase', 'onsite_conversion.purchase']:
                purchases = max(purchases, int(act.get('value', 0)))
            elif t == 'onsite_conversion.messaging_conversation_started_7d':
                messages = int(act.get('value', 0))
        for act in data.get('action_values', []):
            t = act.get('action_type', '')
            if t in ['purchase', 'omni_purchase', 'onsite_conversion.purchase']:
                purchase_value = max(purchase_value, float(act.get('value', 0)))
        
        roas = (purchase_value / spend) if spend > 0 else 0
        cpa = (spend / purchases) if purchases > 0 else 0
        cpmes = (spend / messages) if messages > 0 else 0
        
        # Danh gia theo SOP
        if roas >= 7: grade = "🟢 XUẤT SẮC"
        elif roas >= 5: grade = "✅ ĐẠT"
        elif roas >= 3: grade = "⚠️ CẢNH BÁO"
        else: grade = "🔴 DƯỚI NGƯỠNG"
        
        # Campaign breakdown
        camp_params = {'date_preset': 'last_7d', 'level': 'campaign'}
        camps = account.get_insights(fields=['campaign_name', 'spend', 'actions', 'action_values'], params=camp_params)
        camps = sorted(camps, key=lambda x: float(x.get('spend', 0)), reverse=True)
        
        msg = f"📊 <b>BÁO CÁO TUẦN — 7 NGÀY QUA</b>\n"
        msg += f"📅 {(datetime.now() - timedelta(days=7)).strftime('%d/%m')} → {datetime.now().strftime('%d/%m/%Y')}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"💸 <b>Tổng chi:</b> {spend:,.0f} đ\n"
        msg += f"👁 <b>Hiển thị:</b> {impressions:,}\n"
        msg += f"👆 <b>Clicks:</b> {clicks:,} (CTR {ctr:.2f}%)\n"
        msg += f"💬 <b>Tin nhắn:</b> {messages} ({cpmes:,.0f} đ/tin)\n"
        msg += f"📦 <b>Số đơn:</b> {purchases} (CPA {cpa:,.0f} đ)\n"
        msg += f"💰 <b>Doanh thu:</b> {purchase_value:,.0f} đ\n"
        msg += f"🚀 <b>ROAS:</b> {roas:.2f}x → {grade}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        
        if camps:
            msg += f"📌 <b>TỪNG CHIẾN DỊCH:</b>\n"
            for c in camps:
                c_spend = float(c.get('spend', 0))
                if c_spend < 5000: continue
                c_purchases = 0; c_pv = 0.0; c_msgs = 0
                for act in c.get('actions', []):
                    t = act.get('action_type', '')
                    if t in ['purchase', 'omni_purchase', 'onsite_conversion.purchase']:
                        c_purchases = max(c_purchases, int(act.get('value', 0)))
                    elif t == 'onsite_conversion.messaging_conversation_started_7d':
                        c_msgs = int(act.get('value', 0))
                for act in c.get('action_values', []):
                    t = act.get('action_type', '')
                    if t in ['purchase', 'omni_purchase', 'onsite_conversion.purchase']:
                        c_pv = max(c_pv, float(act.get('value', 0)))
                c_roas = (c_pv / c_spend) if c_spend > 0 else 0
                c_name = c.get('campaign_name', '')[:22]
                
                if c_roas >= 5: icon = "🟢"
                elif c_roas >= 3: icon = "🟡"
                else: icon = "🔴"
                
                msg += f"{icon} <i>{c_name}</i>\n"
                msg += f"   {c_spend/1000:.0f}k | Đơn:{c_purchases} | TN:{c_msgs} | ROAS:{c_roas:.1f}x\n"
        
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        
        # Goi y hanh dong
        msg += f"💡 <b>GỢI Ý:</b>\n"
        if roas >= 5:
            msg += f"→ Scale +20% cho campaigns ROAS &gt;= 5x\n"
        if roas < 3:
            msg += f"→ Xem xét TẮT campaigns ROAS &lt; 3x\n"
        msg += f"→ Refresh creative cho campaigns &gt; 7 ngày\n"
        msg += f"🤖 <i>Gửi từ Antigravity AI Agent</i>"
        
        send_tg(msg)
        print(f"[{time.strftime('%H:%M:%S')}] Da gui bao cao tuan.")
        
    except Exception as e:
        send_tg(f"❌ Lỗi khi lấy báo cáo tuần: {e}")
        print(f"Loi bao cao tuan: {e}")

# =====================================================
# CHUC NANG 3: CANH BAO ROAS REALTIME
# =====================================================
def check_roas_alert():
    """Kiem tra ROAS hom nay, gui canh bao neu < 3x"""
    try:
        from facebook_business.api import FacebookAdsApi
        from facebook_business.adobjects.adaccount import AdAccount
        
        FacebookAdsApi.init(FB_APP_ID, "", FB_ACCESS_TOKEN)
        account = AdAccount(FB_AD_ACCOUNT_ID)
        
        fields = ['campaign_name', 'spend', 'actions', 'action_values']
        params = {'date_preset': 'today', 'level': 'campaign', 'filtering': [{'field': 'campaign.effective_status', 'operator': 'IN', 'value': ['ACTIVE']}]}
        
        camps = account.get_insights(fields=fields, params=params)
        
        alerts = []
        for c in camps:
            c_spend = float(c.get('spend', 0))
            if c_spend < 50000: continue  # Bo qua campaign chi tieu nho
            
            c_pv = 0.0
            for act in c.get('action_values', []):
                t = act.get('action_type', '')
                if t in ['purchase', 'omni_purchase', 'onsite_conversion.purchase']:
                    c_pv = max(c_pv, float(act.get('value', 0)))
            
            c_roas = (c_pv / c_spend) if c_spend > 0 else 0
            c_name = c.get('campaign_name', '')
            
            if c_roas < 3.0 and c_spend >= 100000:
                alerts.append(f"🔴 <b>{c_name[:25]}</b>\n   Chi: {c_spend/1000:.0f}k | ROAS: {c_roas:.1f}x | DT: {c_pv/1000:.0f}k")
        
        if alerts:
            msg = f"🚨 <b>CẢNH BÁO ROAS — {datetime.now().strftime('%H:%M %d/%m')}</b>\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"Các campaign đang DƯỚI NGƯỠNG 3x:\n\n"
            msg += "\n\n".join(alerts)
            msg += f"\n\n━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"💡 Xem xét: đổi creative / đổi tệp / tắt nếu đã &gt;= 5 ngày\n"
            msg += f"🤖 <i>Cảnh báo tự động từ Antigravity</i>"
            send_tg(msg)
            print(f"[{time.strftime('%H:%M:%S')}] Da gui canh bao ROAS.")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] ROAS check OK — khong co canh bao.")
            
    except Exception as e:
        print(f"Loi check ROAS: {e}")

# =====================================================
# CHUC NANG 4: MENU LENH
# =====================================================
def cmd_menu():
    msg = "🤖 <b>MENU LỆNH BOT FB ADS</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    msg += "📊 /baocao — Báo cáo hôm nay\n"
    msg += "📅 /baocao homqua — Báo cáo hôm qua\n"
    msg += "📅 /baocao 14/05 — Báo cáo ngày cụ thể\n"
    msg += "📈 /baocaotuan — Báo cáo 7 ngày\n"
    msg += "🚨 /checkroas — Kiểm tra ROAS ngay\n"
    msg += "📋 /menu — Xem menu này\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    msg += "💡 <i>Cảnh báo ROAS &lt; 3x tự động mỗi 4 tiếng</i>\n"
    msg += "💡 <i>Báo cáo ngày tự động lúc 23:50</i>\n"
    msg += "💡 <i>Báo cáo tuần tự động mỗi CN 20:00</i>"
    send_tg(msg)

# =====================================================
# DUMMY WEB SERVER CHO RENDER
# =====================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot đang chạy ngon lành!"

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# =====================================================
# MAIN LOOP
# =====================================================
def main():
    global last_alert_check
    
    # Khoi dong Web Server tren thread phu
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    print("="*60)
    print(" TELEGRAM BOT LISTENER DANG CHAY...")
    print(" Lenh: /baocao, /baocaotuan, /checkroas, /menu")
    print(" Canh bao ROAS tu dong moi 4 tieng")
    print(" Da tich hop Dummy Web Server cho Render")
    print("="*60)
    
    offset = None
    last_alert_check = time.time()
    last_weekly = time.time()
    last_daily = time.time()
    
    while True:
        # --- XU LY TIN NHAN ---
        updates = get_updates(offset)
        if updates and updates.get("ok"):
            for item in updates.get("result", []):
                offset = item["update_id"] + 1
                msg = item.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text", "").strip().lower()
                
                if chat_id == ALLOWED_CHAT_ID:
                    print(f"[{time.strftime('%H:%M:%S')}] Nhan lenh: {text}")
                    
                    if text.startswith("/baocao") and "/baocaotuan" not in text and "bao cao tuan" not in text and "báo cáo tuần" not in text:
                        parts = text.split()
                        if len(parts) > 1:
                            raw_d = parts[1]
                            if raw_d in ["homqua", "hôm", "yesterday", "qua"]:
                                date_str = "yesterday"
                            else:
                                try:
                                    if "/" in raw_d:
                                        d, m = raw_d.split("/")
                                        date_str = f"{datetime.now().year}-{m.zfill(2)}-{d.zfill(2)}"
                                    else:
                                        date_str = raw_d
                                except:
                                    date_str = raw_d
                            cmd_baocao(date_str)
                        else:
                            cmd_baocao()
                    
                    elif text in ["/baocaotuan", "/weekly", "bao cao tuan", "báo cáo tuần"]:
                        cmd_baocao_tuan()
                    
                    elif text in ["/checkroas", "/check", "check roas", "kiểm tra roas"]:
                        send_tg("⏳ Đang kiểm tra ROAS...")
                        check_roas_alert()
                        send_tg("✅ Đã kiểm tra xong.")
                    
                    elif text in ["/menu", "/help", "menu", "help"]:
                        cmd_menu()
                    
                    elif text in ["/start"]:
                        send_tg("👋 Chào anh! Gõ /menu để xem danh sách lệnh.")
        
        # --- CANH BAO ROAS TU DONG (moi 4 tieng, 8h-22h) ---
        now = time.time()
        current_hour = datetime.now().hour
        if (now - last_alert_check) >= ALERT_INTERVAL and 8 <= current_hour <= 22:
            print(f"[{time.strftime('%H:%M:%S')}] Dang check ROAS tu dong...")
            check_roas_alert()
            last_alert_check = now
        
        # --- BAO CAO TUAN TU DONG (Chu Nhat 20:00) ---
        now_dt = datetime.now()
        if now_dt.weekday() == 6 and now_dt.hour == 20 and (now - last_weekly) > 3600:
            print(f"[{time.strftime('%H:%M:%S')}] Gui bao cao tuan tu dong...")
            cmd_baocao_tuan()
            last_weekly = now
            
        # --- BAO CAO NGAY TU DONG (23:50) ---
        if now_dt.hour == 23 and now_dt.minute >= 50 and (now - last_daily) > 3600:
            print(f"[{time.strftime('%H:%M:%S')}] Gui bao cao ngay tu dong...")
            cmd_baocao()
            last_daily = now
        
        time.sleep(1)

if __name__ == "__main__":
    main()
