import streamlit as st
import folium
from folium import plugins
from streamlit_folium import st_folium
import plotly.express as px
import pandas as pd
import random
import time
import requests

@st.cache_data(ttl=900) 
def get_live_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        response = requests.get(url, timeout=5)
        data = response.json()
        current = data.get("current_weather", {})
        
        temp = round(current.get("temperature", 0))
        wind_kmh = current.get("windspeed", 0)
        wind_knots = round(wind_kmh * 0.539957)
        code = current.get("weathercode", 0)
        
        if code == 0:
            cond, color = "Clear skies (Safe)", "#006400"
        elif code in [1, 2, 3]:
            cond, color = "Partly Cloudy (Safe)", "#006400"
        elif code in [45, 48]:
            cond, color = "Foggy (Caution)", "#B8860B"
        elif code in [51, 53, 55, 61, 63, 65]:
            cond, color = "Rain (Caution)", "#B8860B"
        elif code > 65:
            cond, color = "Storm Warning (Unsafe)", "#8B0000"
        else:
            cond, color = "Moderate (Safe)", "#006400"
            
        return temp, wind_knots, cond, color
    except Exception:
        return "--", "--", "Offline", "#000000"

# ==========================================
# PAGE CONFIGURATION & CSS
# ==========================================
st.set_page_config(page_title="SeaParcel Unified Platform", layout="wide", page_icon="🚢")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Clean App Background */
    .stApp {
        background-color: #F8FAFC;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    
    /* Advanced Card Design with Hover Effects */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        border: 1px solid #E2E8F0 !important;
        border-radius: 16px !important;
        background-color: #FFFFFF;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02) !important;
        padding: 1.5rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    div[data-testid="stVerticalBlock"] > div[style*="border"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 20px -3px rgba(0, 119, 182, 0.1), 0 4px 6px -2px rgba(0, 119, 182, 0.05) !important;
        border-color: #BAE6FD !important;
    }
    
    /* Premium Buttons */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
        border: none !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
        text-transform: uppercase;
        font-size: 0.85rem !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.1);
    }
    
    button[kind="primary"] {
        background: linear-gradient(135deg, #0077B6 0%, #00B4D8 100%) !important;
        color: white !important;
        box-shadow: 0 4px 14px 0 rgba(0, 119, 182, 0.39) !important;
    }
    
    /* Dashboard Pill Tabs */
    button[data-baseweb="tab"] {
        background-color: transparent !important;
        border-radius: 8px !important;
        margin-right: 8px !important;
        padding: 8px 16px !important;
        font-weight: 600 !important;
    }
    button[aria-selected="true"] {
        background-color: #E0F2FE !important;
        color: #0284C7 !important;
    }
    
    /* Metrics Upgrades */
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        color: #0F172A !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        color: #64748B !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Gradient Headers */
    .gradient-text {
        background: linear-gradient(135deg, #0077B6 0%, #00B4D8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        margin-bottom: 0;
    }

    /* Refined Badges */
    .badge {
        padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.75rem; 
        text-transform: uppercase; letter-spacing: 0.05em; display: inline-block;
    }
    .badge-booked { background: #E0F2FE; color: #0284C7; border: 1px solid #BAE6FD; }
    .badge-transit { background: #DCFCE7; color: #166534; border: 1px solid #BBF7D0; }
    .ship-icon { font-size: 2.5rem; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# SESSION STATE MEMORY
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_name' not in st.session_state:
    st.session_state.user_name = "Customer"
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Dashboard"

if 'show_balloons' not in st.session_state:
    st.session_state.show_balloons = False
if 'show_toast' not in st.session_state:
    st.session_state.show_toast = ""

# Initialize the dynamic user database with a second client for testing
if 'user_db' not in st.session_state:
    st.session_state.user_db = {
        "client@seaparcel.ph": {"password": "password123", "company_name": "Acme Logistics"},
        "client2@seaparcel.ph": {"password": "password123", "company_name": "Global Traders"},
        "admin@seaparcel.ph": {"password": "admin", "company_name": "Port Authority"}
    }

if 'active_shipments' not in st.session_state:
    st.session_state.active_shipments = []
if 'delivered_shipments' not in st.session_state:
    st.session_state.delivered_shipments = []

if st.session_state.show_balloons:
    st.balloons()
    st.session_state.show_balloons = False
if st.session_state.show_toast:
    st.toast(st.session_state.show_toast, icon="✅")
    st.session_state.show_toast = ""

# ==========================================
# VIEW 1: AUTHENTICATION (LOGIN & SIGN UP)
# ==========================================
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("<br><br>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            try:
                st.image("logo.jpg", use_container_width=True)
            except Exception:
                st.markdown("<h1 style='text-align: center; color: #0077B6;'>🚢</h1>", unsafe_allow_html=True)
                
        st.markdown("<h1 style='text-align: center; color: #0077B6;'>SeaParcel</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Unified Maritime Logistics & ESG Platform</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])
            
            with tab_login:
                email = st.text_input("Email Address", placeholder="client@seaparcel.ph")
                password = st.text_input("Password", placeholder="password123", type="password")
                
                if st.button("Log In", type="primary", use_container_width=True):
                    if email in st.session_state.user_db:
                        if st.session_state.user_db[email]["password"] == password:
                            st.session_state.logged_in = True
                            st.session_state.user_name = st.session_state.user_db[email]["company_name"]
                            st.session_state.show_toast = f"Welcome back, {st.session_state.user_name}!"
                            st.rerun()
                        else:
                            st.error("❌ Incorrect password. Please try again.")
                    else:
                        st.error("❌ Email not found. Please check your spelling or Sign Up.")
                        
            with tab_signup:
                new_company = st.text_input("Company Name")
                new_email = st.text_input("Work Email")
                new_password = st.text_input("Create Password", type="password")
                
                if st.button("Create Account", type="primary", use_container_width=True):
                    if new_email in st.session_state.user_db:
                        st.warning("⚠️ An account with this email already exists.")
                    elif new_email and new_password and new_company:
                        st.session_state.user_db[new_email] = {
                            "password": new_password,
                            "company_name": new_company
                        }
                        st.success("✅ Account created successfully! Switch to the 'Log In' tab to access your dashboard.")
                    else:
                        st.error("Please fill out all fields.")

# ==========================================
# VIEW 2: THE UNIFIED PLATFORM
# ==========================================
else:
    # --- DATA ISOLATION FILTER ---
    # Admin sees everything. Customers only see their own cargo.
    if st.session_state.user_name == "Port Authority":
        view_active = st.session_state.active_shipments
        view_delivered = st.session_state.delivered_shipments
    else:
        view_active = [s for s in st.session_state.active_shipments if s.get("Owner") == st.session_state.user_name]
        view_delivered = [s for s in st.session_state.delivered_shipments if s.get("Owner") == st.session_state.user_name]

    # --- AUTO DELIVERY CHECKER ---
    auto_delivered_something = False
    for ship in list(st.session_state.active_shipments):
        if ship['Status'] == "TRANSIT":
            elapsed = time.time() - ship.get('Dispatch_Time', time.time())
            if elapsed >= 1800.0: 
                st.session_state.delivered_shipments.append(ship)
                st.session_state.active_shipments.remove(ship)
                
                if st.session_state.user_name in ["Port Authority", ship.get("Owner")]:
                    st.session_state.show_balloons = True
                    st.session_state.show_toast = f"Shipment {ship['Tracking ID']} Automatically Delivered!"
                auto_delivered_something = True
                
    if auto_delivered_something:
        st.rerun()

    # Header Metrics
    h_col1, h_col2, h_col3, h_col4 = st.columns([3, 1, 1, 1])
    with h_col1:
        st.markdown("### 🚢 SeaParcel Unified Platform")
    with h_col2:
        st.caption("ACTIVE ROLE")
        st.markdown(f"**{st.session_state.user_name}**")
    with h_col3:
        st.caption("VESSELS IN TRANSIT")
        transit_count = sum(1 for s in view_active if s["Status"] == "TRANSIT")
        st.markdown(f"**{max(0, transit_count)}**")
    with h_col4:
        st.caption("TOTAL FUEL SAVED")
        active_weight = sum(ship['Weight'] for ship in view_active)
        delivered_weight = sum(ship['Weight'] for ship in view_delivered)
        total_system_weight = active_weight + delivered_weight
        fuel_saved = total_system_weight * 0.004
        st.markdown(f"**{fuel_saved:.1f} MT**")

    # Sidebar Navigation
    with st.sidebar:
        try:
            st.image("logo.jpg", use_container_width=True)
        except Exception:
            pass
        st.markdown(f"### {st.session_state.user_name}")
        st.write("")
        nav_options = ["Dashboard", "Booking", "Tracking", "ESG Metrics"]
        selected_page = st.radio("Navigation Menu", nav_options, index=nav_options.index(st.session_state.current_page), label_visibility="collapsed")
        
        st.write("<br><br><br><br><br>", unsafe_allow_html=True)
        if st.button("Log Out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_page = "Dashboard"
            st.rerun()
            
    if selected_page != st.session_state.current_page:
        st.session_state.current_page = selected_page
        st.rerun()

    # ==========================================
    # PAGE 1: DASHBOARD
    # ==========================================
    if st.session_state.current_page == "Dashboard":
        st.title("Operations Center")
        st.write("") 
        
        if st.session_state.user_name == "Port Authority":
            tabs = st.tabs(["🌊 Active Fleet Management", "🗄️ Delivery Logs"])
            tab_active = tabs[0]
            tab_delivered_admin = tabs[1]
            tab_delivered_client = None 
        else:
            tabs = st.tabs(["🌊 Active Logistics", "✅ Delivery History & Receipts"])
            tab_active = tabs[0]
            tab_delivered_admin = None
            tab_delivered_client = tabs[1]
            
        with tab_active:
            al_col1, al_col2 = st.columns([3, 1])
            with al_col1:
                st.write("") 
            with al_col2:
                if st.session_state.user_name == "Port Authority" and len(view_active) > 0:
                    df_manifest = pd.DataFrame(view_active)
                    csv_data = df_manifest.to_csv(index=False)
                    st.download_button(
                        label="📊 Download Manifest (CSV)",
                        data=csv_data,
                        file_name=f"SeaParcel_Manifest_{int(time.time())}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    
            if len(view_active) == 0:
                if st.session_state.user_name == "Port Authority":
                    with st.container(border=True):
                        st.markdown("<div style='text-align: center; padding: 3rem 1rem;'>", unsafe_allow_html=True)
                        st.markdown("<h1 style='font-size: 3rem; color: #a0aec0; margin-bottom: 0;'>⚓</h1>", unsafe_allow_html=True)
                        st.markdown("<h4 style='color: #4a5568;'>No Active Vessels</h4>", unsafe_allow_html=True)
                        st.markdown("<p style='color: #718096;'>There are currently no vessels pending dispatch or in transit.</p>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    with st.container(border=True):
                        st.markdown("<div style='text-align: center; padding: 3rem 1rem;'>", unsafe_allow_html=True)
                        st.markdown("<h1 style='font-size: 3rem; color: #a0aec0; margin-bottom: 0;'>🚢</h1>", unsafe_allow_html=True)
                        st.markdown("<h4 style='color: #4a5568;'>No Active Shipments</h4>", unsafe_allow_html=True)
                        st.markdown("<p style='color: #718096;'>Head to the Booking Engine to schedule your first eco-friendly cargo.</p>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                
            for ship in view_active:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([0.5, 4, 1.5])
                    
                    with c1:
                        st.markdown("<div class='ship-icon'>🚢</div>", unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"**{ship['Tracking ID']}**")
                        st.caption(f"Client: {ship.get('Owner')} | Route: {ship['Route']} | Cargo: {ship['Type']} | Weight: {ship['Weight']} kg")
                    with c3:
                        if ship['Status'] == "BOOKED":
                            st.markdown("<div class='badge badge-booked'>BOOKED</div>", unsafe_allow_html=True)
                            
                            if st.session_state.user_name != "Port Authority":
                                if st.button("Cancel Order", key=f"cancel_{ship['Tracking ID']}", type="primary", use_container_width=True):
                                    st.session_state.active_shipments = [s for s in st.session_state.active_shipments if s['Tracking ID'] != ship['Tracking ID']]
                                    st.session_state.show_toast = "Booking Cancelled"
                                    st.rerun()
                                    
                            if st.session_state.user_name == "Port Authority":
                                if st.button("🚀 Dispatch Vessel", key=f"dispatch_{ship['Tracking ID']}", type="primary", use_container_width=True):
                                    for s in st.session_state.active_shipments:
                                        if s['Tracking ID'] == ship['Tracking ID']:
                                            s['Status'] = "TRANSIT"
                                            s['Dispatch_Time'] = time.time()
                                            break
                                    st.session_state.show_toast = "Vessel Dispatched Successfully!"
                                    st.rerun()
                                    
                        elif ship['Status'] == "TRANSIT":
                            st.markdown("<div class='badge badge-transit'>In Transit</div>", unsafe_allow_html=True)
                            
                            if st.session_state.user_name == "Port Authority":
                                if st.button("✅ Marked Delivered", key=f"deliver_{ship['Tracking ID']}", type="primary", use_container_width=True):
                                    st.session_state.delivered_shipments.append(ship)
                                    st.session_state.active_shipments = [s for s in st.session_state.active_shipments if s['Tracking ID'] != ship['Tracking ID']]
                                    st.session_state.show_balloons = True
                                    st.session_state.show_toast = f"Shipment {ship['Tracking ID']} Delivered Early!"
                                    st.rerun()

        if tab_delivered_admin is not None:
            with tab_delivered_admin:
                if len(view_delivered) == 0:
                    with st.container(border=True):
                        st.markdown("<div style='text-align: center; padding: 3rem 1rem;'>", unsafe_allow_html=True)
                        st.markdown("<h1 style='font-size: 3rem; color: #a0aec0; margin-bottom: 0;'>📭</h1>", unsafe_allow_html=True)
                        st.markdown("<h4 style='color: #4a5568;'>No Delivery Logs Found</h4>", unsafe_allow_html=True)
                        st.markdown("<p style='color: #718096;'>Completed fleet deliveries and master data logs will automatically populate here.</p>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    df_delivered = pd.DataFrame(view_delivered)
                    csv_delivered = df_delivered.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Complete Delivery Log (CSV)",
                        data=csv_delivered,
                        file_name=f"SeaParcel_Completed_{int(time.time())}.csv",
                        mime="text/csv",
                        type="primary"
                    )
                    st.divider()
                    for d_ship in reversed(view_delivered):
                        with st.container(border=True):
                            st.markdown(f"**{d_ship['Tracking ID']}**")
                            st.caption(f"Client: {d_ship.get('Owner')} | Route: {d_ship['Route']} | Cargo: {d_ship['Type']} | Weight: {d_ship['Weight']} kg")

        if tab_delivered_client is not None:
            with tab_delivered_client:
                if len(view_delivered) == 0:
                    with st.container(border=True):
                        st.markdown("<div style='text-align: center; padding: 3rem 1rem;'>", unsafe_allow_html=True)
                        st.markdown("<h1 style='font-size: 3rem; color: #a0aec0; margin-bottom: 0;'>📦</h1>", unsafe_allow_html=True)
                        st.markdown("<h4 style='color: #4a5568;'>No Completed Deliveries Yet</h4>", unsafe_allow_html=True)
                        st.markdown("<p style='color: #718096;'>Once your cargo safely reaches its destination, your certified ESG receipts will appear here.</p>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    for d_ship in reversed(view_delivered): 
                        with st.container(border=True):
                            st.success(f"**COMPLETED:** Shipment **{d_ship['Tracking ID']}** has safely arrived. ✅")
                            
                            weight = d_ship['Weight']
                            if "Cebu" in d_ship["Route"]:
                                plastic, woods, paper, oil = weight * 0.062, weight * 0.021, weight * 0.008, weight * 0.005
                            else:
                                plastic, woods, paper, oil = weight * 0.041, weight * 0.048, weight * 0.004, weight * 0.002
                                
                            total_waste = plastic + woods + paper + oil
                            carbon_offset = weight * 0.12
                            
                            receipt_content = f"*** SEAPARCEL OFFICIAL RECEIPT ***\n\nTracking ID: {d_ship['Tracking ID']}\nRoute: {d_ship['Route']}\nCargo Type: {d_ship['Type']}\nWeight: {d_ship['Weight']} kg\nStatus: DELIVERED\n\n*** ENVIRONMENTAL IMPACT REPORT ***\nCarbon Emissions Offset: {carbon_offset:.1f} kg CO2\nTotal Ocean Waste Removed: {total_waste:.1f} kg\n  * Plastic: {plastic:.1f} kg\n  * Woods: {woods:.1f} kg\n  * Paper: {paper:.1f} kg\n  * Oil Spill: {oil:.1f} kg\n\nThank you for choosing eco-friendly maritime logistics."
                            
                            st.download_button(
                                label=f"📄 Download Certified ESG Receipt", 
                                data=receipt_content, 
                                file_name=f"SeaParcel_Receipt_{d_ship['Tracking ID']}.txt",
                                mime="text/plain",
                                key=f"receipt_{d_ship['Tracking ID']}"
                            )
                    
                    if st.button("Clear History", type="secondary"):
                        st.session_state.delivered_shipments = [s for s in st.session_state.delivered_shipments if s.get("Owner") != st.session_state.user_name]
                        st.rerun()

    # ==========================================
    # PAGE 2: BOOKING
    # ==========================================
    elif st.session_state.current_page == "Booking":
        st.title("Intelligent Booking Engine")
        
        if st.session_state.user_name == "Port Authority":
            st.warning("Admins and Port Authorities cannot book freight. Please log in as a corporate client.")
        else:
            with st.container(border=True):
                b_col1, b_col2 = st.columns([2, 1])
                with b_col1:
                    cargo_type = st.selectbox("Select Cargo Type", ["LCL (Less Container Load)", "FCL 20ft Container", "FCL 40ft Container"])
                    route_selection = st.selectbox("Select Shipping Route", ["Manila ➔ Ilocos", "Ilocos ➔ Manila", "Cebu ➔ Manila"])
                    
                    st.write("")
                    st.markdown("**Select Cargo Weight**")
                    weight = st.slider("Total Weight in Kilograms", min_value=100, max_value=10000, step=50, value=500)
                    
                with b_col2:
                    st.markdown("<div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px; height: 100%;'>", unsafe_allow_html=True)
                    st.markdown("#### Instant Quote")
                    base_fee = 25000 if "20ft" in cargo_type else (45000 if "40ft" in cargo_type else 2500)
                    per_kg_fee = 30 if "FCL" in cargo_type else 50
                    total_cost = base_fee + (weight * per_kg_fee)
                    
                    st.markdown(f"<h1 style='color: #00B4D8; margin-top: 0;'>₱{total_cost:,.2f}</h1>", unsafe_allow_html=True)
                    st.caption("Includes fuel surcharge and environmental offset fees.")
                    st.write("")
                    
                    if st.button("Confirm Booking & Dispatch", type="primary", use_container_width=True):
                        new_shipment = {
                            "Tracking ID": f"SP-{random.randint(10, 99)}_{random.choice(['A','B','X','Y'])}",
                            "Owner": st.session_state.user_name,
                            "Route": route_selection,
                            "Status": "BOOKED",
                            "Type": cargo_type,
                            "Weight": weight,
                            "Timestamp": time.time()
                        }
                        st.session_state.active_shipments.append(new_shipment)
                        st.session_state.show_toast = "Cargo booked successfully!"
                        st.session_state.current_page = "Dashboard" 
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================
    # PAGE 3: TRACKING
    # ==========================================
    elif st.session_state.current_page == "Tracking":
        st.title("Live Fleet & Telemetry Tracking")
        
        with st.expander("🌤️ View Live Port Weather Conditions", expanded=True):
            manila_temp, manila_wind, manila_cond, manila_color = get_live_weather(14.59, 120.98)
            cebu_temp, cebu_wind, cebu_cond, cebu_color = get_live_weather(10.31, 123.89)
            ilocos_temp, ilocos_wind, ilocos_cond, ilocos_color = get_live_weather(18.01, 120.48)
            
            w_col1, w_col2, w_col3 = st.columns(3)
            with w_col1:
                st.markdown("**📍 Port of Manila**")
                st.markdown(f"🌡️ {manila_temp}°C | 💨 {manila_wind} knots")
                st.markdown(f"<span style='color:{manila_color}; font-weight:bold;'>✓ {manila_cond}</span>", unsafe_allow_html=True)
            with w_col2:
                st.markdown("**📍 Port of Cebu**")
                st.markdown(f"🌡️ {cebu_temp}°C | 💨 {cebu_wind} knots")
                st.markdown(f"<span style='color:{cebu_color}; font-weight:bold;'>✓ {cebu_cond}</span>", unsafe_allow_html=True)
            with w_col3:
                st.markdown("**📍 Port of Ilocos**")
                st.markdown(f"🌡️ {ilocos_temp}°C | 💨 {ilocos_wind} knots")
                st.markdown(f"<span style='color:{ilocos_color}; font-weight:bold;'>✓ {ilocos_cond}</span>", unsafe_allow_html=True)
        
        st.write("")
        
        if len(view_active) == 0:
            st.info("No active shipments to track on the map.")
        else:
            t_col1, t_col2 = st.columns([2, 1])
            
            with t_col1:
                # Custom Ocean Waypoints (Calibrated to avoid landmasses)
                route_waypoints = {
                    "Manila ➔ Ilocos": [
                        [14.59, 120.98], # Manila Port
                        [14.30, 120.50], # South of Bataan (Exiting Manila Bay)
                        [14.50, 120.20], # West of Bataan Peninsula
                        [15.30, 119.80], # West of Zambales Coast
                        [16.50, 119.70], # Clearing Bolinao Point
                        [17.50, 120.20], # Coast of Vigan
                        [18.01, 120.48]  # Ilocos Port
                    ],
                    "Ilocos ➔ Manila": [
                        [18.01, 120.48], # Ilocos Port
                        [17.50, 120.20], # Coast of Vigan
                        [16.50, 119.70], # Clearing Bolinao Point
                        [15.30, 119.80], # West of Zambales Coast
                        [14.50, 120.20], # West of Bataan Peninsula
                        [14.30, 120.50], # South of Bataan (Entering Manila Bay)
                        [14.59, 120.98]  # Manila Port
                    ],
                    "Cebu ➔ Manila": [
                        [10.31, 123.89], # Cebu Port
                        [11.25, 124.05], # Camotes Sea (Navigating North of Cebu)
                        [11.75, 123.20], # Jintotolo Channel (Between Masbate and Panay)
                        [12.60, 122.20], # Tablas Strait
                        [13.50, 120.90], # Verde Island Passage
                        [14.25, 120.55], # Approaching Corregidor / Manila Bay
                        [14.59, 120.98]  # Manila Port
                    ]
                }

                # Helper function to move the ship smoothly along the waypoints
                def get_point_on_path(path, progress):
                    if progress <= 0: return path[0]
                    if progress >= 1: return path[-1]
                    total_segments = len(path) - 1
                    segment_index = int(progress * total_segments)
                    segment_progress = (progress * total_segments) - segment_index
                    if segment_index >= total_segments: return path[-1]
                    
                    start_pt = path[segment_index]
                    end_pt = path[segment_index + 1]
                    lat = start_pt[0] + (end_pt[0] - start_pt[0]) * segment_progress
                    lon = start_pt[1] + (end_pt[1] - start_pt[1]) * segment_progress
                    return [lat, lon]

                if st.button("📡 Ping Satellites for Live GPS Update", use_container_width=True): 
                    st.rerun()

                m = folium.Map(location=[13.5, 121.5], zoom_start=5.5, tiles="CartoDB positron")
                
                for ship in view_active:
                    try:
                        route_name = ship['Route']
                        path = route_waypoints.get(route_name, [])
                        
                        # Draw the custom dashed path along the ocean
                        if path:
                            plugins.AntPath(path, color="#0077B6", weight=3).add_to(m)
                        
                        if ship['Status'] == "TRANSIT":
                            elapsed = time.time() - ship.get('Dispatch_Time', time.time())
                            # Remember to change 300.0 back to 14400.0 if you want the full 4-hour timer!
                            prog = min(elapsed / 1800.0, 1.0) 
                            
                            # Calculate exactly where the ship is along the ocean waypoints
                            current_pos = get_point_on_path(path, prog)
                            
                            folium.Marker(current_pos, popup=f"<b>{ship['Tracking ID']}</b>", icon=folium.Icon(color="green", icon='ship', prefix='fa')).add_to(m)
                        else:
                            folium.Marker(path[0], popup=f"<b>{ship['Tracking ID']}</b>", icon=folium.Icon(color="blue", icon='ship', prefix='fa')).add_to(m)
                    except Exception as e: 
                        pass
                
                with st.container(border=True):
                    st_folium(m, width=650, height=450, key="fleet_map", returned_objects=[])
                
            with t_col2:
                st.markdown("#### Hardware Telemetry")
                ship_ids = [ship["Tracking ID"] for ship in view_active]
                selected_ship = st.selectbox("Select Vessel Edge Node", ship_ids)
                
                selected_status = next((ship["Status"] for ship in view_active if ship["Tracking ID"] == selected_ship), "Unknown")
                
                with st.container(border=True):
                    if selected_status == "TRANSIT":
                        st.success("🟢 Sensors Online (In Transit)")
                        st.metric("Engine Temp", f"{random.randint(78, 82)}°C", f"{random.choice(['+', '-'])}{random.uniform(0.5, 1.5):.1f}°C")
                        st.metric("Hybrid Battery", f"{random.randint(45, 88)}%", "Discharging")
                        st.metric("Waste Intake Flow", f"{random.uniform(12.5, 14.0):.1f} m³/min", f"{random.choice(['+', '-'])}{random.uniform(0.1, 0.5):.1f} m³/min")
                    else:
                        st.info("🔵 Vessel docked at port. Awaiting departure clearance.")
                        st.metric("Engine Temp", "32°C", "Offline")
                        st.metric("Hybrid Battery", "100%", "Charging (Grid)")
                        st.metric("Waste Intake Flow", "0.0 m³/min", "Offline")

 # ==========================================
    # PAGE 4: ESG METRICS & ROI
    # ==========================================
    elif st.session_state.current_page == "ESG Metrics":
        
        # Add the sync button next to the title
        col_title, col_btn = st.columns([4, 1])
        with col_title:
            st.title("Environmental Impact & ROI")
        with col_btn:
            st.write("<br>", unsafe_allow_html=True)
            if st.button("🔄 Sync Live Data", use_container_width=True):
                st.rerun()
        
        transit_ships = [ship for ship in view_active if ship["Status"] == "TRANSIT"]
        
        # Track physical weight for financials, and effective weight for live ESG
        w_tot_physical = 0 
        w_tot_effective = 0 
        p = wd = pa = o = 0
        
        if len(transit_ships) > 0:
            for ship in transit_ships:
                w_real = ship["Weight"]
                w_tot_physical += w_real
                
                # Calculate progress based on the 4 hour (14400 seconds) timer
                # Note: Keeping your current 300.0 (5 mins) demo timer here based on your code
                elapsed = time.time() - ship.get('Dispatch_Time', time.time())
                prog = min(elapsed / 1800.0, 1.0) 
                
                # Live accumulating weight
                w_eff = w_real * prog
                w_tot_effective += w_eff
                
                # Use random.uniform to make the live AI data fluctuate slightly
                if "Cebu" in ship["Route"]:
                    p += w_eff * random.uniform(0.058, 0.066) 
                    wd += w_eff * random.uniform(0.018, 0.024)
                    pa += w_eff * random.uniform(0.006, 0.010)
                    o += w_eff * random.uniform(0.003, 0.007)
                else:
                    p += w_eff * random.uniform(0.038, 0.044) 
                    wd += w_eff * random.uniform(0.045, 0.051)
                    pa += w_eff * random.uniform(0.002, 0.006)
                    o += w_eff * random.uniform(0.001, 0.003)

        total_waste_removed = p + wd + pa + o
        carbon_offset_so_far = w_tot_effective * 0.12

        e_col1, e_col2 = st.columns([1, 2])
        
        with e_col1:
            with st.container(border=True):
                st.markdown("#### Real-time ESG Impact")
                st.metric("Total Cargo in Transit", f"{w_tot_physical:,.0f} kg")
                st.metric("Ocean Waste Removed", f"{total_waste_removed:,.2f} kg", "Active AI Harvesting" if total_waste_removed > 0 else None)
                st.metric("Carbon Emissions Offset", f"{carbon_offset_so_far:,.2f} kg CO2", "Accumulating" if carbon_offset_so_far > 0 else None)
            
        with e_col2:
            with st.container(border=True):
                st.markdown("#### Validated Waste Composition")
                if w_tot_effective == 0:
                    st.info("Awaiting vessels to enter transit to generate live AI waste composition.")
                    fig = px.pie(values=[1], names=["No Data"], hole=0.4, color_discrete_sequence=["#e0e0e0"])
                    fig.update_traces(textinfo='none', hoverinfo='none')
                else:
                    df_materials = pd.DataFrame({
                        "Waste Type": ["Plastic", "Woods", "Paper", "Oil Spill"],
                        "Amount (kg)": [p, wd, pa, o] 
                    })
                    
                    # Hardcode the exact colors so they never get mixed up by sorting
                    color_mapping = {
                        "Plastic": "#00B4D8",   
                        "Woods": "#8B4513",     
                        "Paper": "#F4A460",     
                        "Oil Spill": "#2F4F4F"  
                    }
                    
                    fig = px.pie(
                        df_materials, 
                        values="Amount (kg)", 
                        names="Waste Type", 
                        hole=0.5, 
                        color="Waste Type",
                        color_discrete_map=color_mapping
                    )
                    
                    # Use 'auto' positioning, 3 decimal places, and force horizontal text
                    fig.update_traces(
                        textposition='auto', 
                        texttemplate='%{label}<br><b>%{value:.3f} kg</b>',
                        sort=False,
                        insidetextorientation='horizontal'
                    )
                    
# Expand the margins slightly so outside labels never get cropped
                fig.update_layout(
                    margin=dict(t=40, b=100, l=40, r=40), 
                    showlegend=False,
                    height=450
                )
                st.plotly_chart(fig, use_container_width=True)
            
        st.divider()
        st.markdown("### 💰 Financial ROI & Business Value")
        
        with st.expander("View Financial Breakdown & Client Savings", expanded=True):
            roi_col1, roi_col2, roi_col3 = st.columns(3)
            traditional_rate = 65.0  
            seaparcel_rate = 45.0    
            
            # Financials are based on physical weight
            traditional_cost = w_tot_physical * traditional_rate
            seaparcel_cost = w_tot_physical * seaparcel_rate
            total_savings = traditional_cost - seaparcel_cost
            
            # Tax savings are based on the live accumulating carbon offset
            carbon_tax_savings = (carbon_offset_so_far / 1000) * 2500 if carbon_offset_so_far > 0 else 0
            
            with roi_col1:
                st.metric("Traditional Freight Cost", f"₱{traditional_cost:,.2f}")
            with roi_col2:
                st.metric("SeaParcel Hybrid Cost", f"₱{seaparcel_cost:,.2f}", delta=f"-₱{total_savings:,.2f}", delta_color="inverse")
            with roi_col3:
                st.metric("Carbon Tax Avoided", f"₱{carbon_tax_savings:,.2f}")
