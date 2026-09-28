import streamlit as st
import sqlite3
from datetime import date, datetime
import pandas as pd

DB_FILE = "hotel.db"

st.set_page_config(
    page_title="Hotel Manager",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# DATABASE
# -----------------------------
def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE NOT NULL,
            room_type TEXT NOT NULL,
            floor INTEGER NOT NULL,
            price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Trống'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS guests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            id_number TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            adults INTEGER DEFAULT 1,
            children INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Đã đặt',
            note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (guest_id) REFERENCES guests(id),
            FOREIGN KEY (room_id) REFERENCES rooms(id)
        )
    """)

    # Tạo dữ liệu phòng mẫu lần đầu chạy
    room_count = cur.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
    if room_count == 0:
        sample_rooms = [
            ("101", "Standard", 1, 900000, "Trống"),
            ("102", "Standard", 1, 900000, "Trống"),
            ("103", "Superior", 1, 1200000, "Trống"),
            ("201", "Superior", 2, 1200000, "Trống"),
            ("202", "Deluxe", 2, 1600000, "Trống"),
            ("203", "Deluxe", 2, 1600000, "Đang ở"),
            ("301", "Suite", 3, 2500000, "Trống"),
            ("302", "Suite", 3, 2500000, "Bảo trì"),
            ("401", "Family", 4, 3000000, "Trống"),
            ("402", "Family", 4, 3000000, "Trống"),
        ]
        cur.executemany("""
            INSERT INTO rooms
            (room_number, room_type, floor, price, status)
            VALUES (?, ?, ?, ?, ?)
        """, sample_rooms)

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# HELPERS
# -----------------------------
ROOM_STATUSES = ["Trống", "Đã đặt", "Đang ở", "Bẩn", "Bảo trì"]
BOOKING_STATUSES = ["Đã đặt", "Đã nhận phòng", "Đã trả phòng", "Đã hủy"]

def query_df(sql, params=()):
    conn = get_conn()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df

def execute(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def money(value):
    return f"{value:,.0f} ₫"

def refresh():
    st.rerun()

# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.title("🏨 HOTEL MANAGER")
st.sidebar.caption("Hệ thống quản lý phòng khách sạn")

menu = st.sidebar.radio(
    "MENU",
    [
        "📊 Dashboard",
        "🛏️ Quản lý phòng",
        "📅 Đặt phòng",
        "👤 Khách hàng",
    ],
)

st.sidebar.divider()
st.sidebar.info(
    "Dữ liệu được lưu tự động trong file hotel.db.\n\n"
    "Bạn có thể chạy app bằng:\n"
    "`streamlit run app.py`"
)

# -----------------------------
# DASHBOARD
# -----------------------------
if menu == "📊 Dashboard":
    st.title("📊 Dashboard")
    st.caption(f"Cập nhật: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    rooms = query_df("SELECT * FROM rooms")
    bookings = query_df("""
        SELECT b.*, g.full_name, r.room_number, r.room_type, r.price
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        JOIN rooms r ON b.room_id = r.id
        ORDER BY b.id DESC
    """)

    total_rooms = len(rooms)
    available = int((rooms["status"] == "Trống").sum()) if total_rooms else 0
    reserved = int((rooms["status"] == "Đã đặt").sum()) if total_rooms else 0
    occupied = int((rooms["status"] == "Đang ở").sum()) if total_rooms else 0
    maintenance = int((rooms["status"] == "Bảo trì").sum()) if total_rooms else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Tổng phòng", total_rooms)
    c2.metric("Phòng trống", available)
    c3.metric("Đã đặt", reserved)
    c4.metric("Đang ở", occupied)
    c5.metric("Bảo trì", maintenance)

    st.divider()

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Tình trạng phòng")
        if total_rooms:
            status_df = rooms["status"].value_counts().rename_axis("Trạng thái").reset_index(name="Số phòng")
            st.bar_chart(status_df.set_index("Trạng thái"))
        else:
            st.info("Chưa có dữ liệu phòng.")

    with col2:
        st.subheader("Đặt phòng gần đây")
        if bookings.empty:
            st.info("Chưa có đơn đặt phòng.")
        else:
            display = bookings[
                ["id", "full_name", "room_number", "room_type", "check_in", "check_out", "status"]
            ].head(10).copy()
            display.columns = [
                "Mã", "Khách hàng", "Phòng", "Loại phòng",
                "Nhận phòng", "Trả phòng", "Trạng thái"
            ]
            st.dataframe(display, use_container_width=True, hide_index=True)

# -----------------------------
# ROOM MANAGEMENT
# -----------------------------
elif menu == "🛏️ Quản lý phòng":
    st.title("🛏️ Quản lý phòng")

    tab1, tab2 = st.tabs(["Danh sách phòng", "Thêm phòng"])

    with tab1:
        rooms = query_df("SELECT * FROM rooms ORDER BY floor, room_number")

        if rooms.empty:
            st.info("Chưa có phòng.")
        else:
            f1, f2 = st.columns(2)
            with f1:
                filter_status = st.selectbox(
                    "Lọc trạng thái",
                    ["Tất cả"] + ROOM_STATUSES
                )
            with f2:
                search_room = st.text_input("Tìm số phòng", placeholder="Ví dụ: 201")

            filtered = rooms.copy()

            if filter_status != "Tất cả":
                filtered = filtered[filtered["status"] == filter_status]

            if search_room.strip():
                filtered = filtered[
                    filtered["room_number"].astype(str).str.contains(
                        search_room.strip(), case=False, na=False
                    )
                ]

            st.dataframe(
                filtered[
                    ["id", "room_number", "room_type", "floor", "price", "status"]
                ].rename(columns={
                    "id": "ID",
                    "room_number": "Số phòng",
                    "room_type": "Loại phòng",
                    "floor": "Tầng",
                    "price": "Giá/đêm",
                    "status": "Trạng thái",
                }),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Giá/đêm": st.column_config.NumberColumn(
                        format="%.0f ₫"
                    )
                },
            )

        st.subheader("Cập nhật trạng thái phòng")

        if not rooms.empty:
            room_options = {
                f"{row['room_number']} - {row['room_type']}": int(row["id"])
                for _, row in rooms.iterrows()
            }

            with st.form("update_room_status"):
                selected_room = st.selectbox("Chọn phòng", list(room_options.keys()))
                new_status = st.selectbox("Trạng thái mới", ROOM_STATUSES)
                submitted = st.form_submit_button("💾 Cập nhật", use_container_width=True)

                if submitted:
                    room_id = room_options[selected_room]
                    execute(
                        "UPDATE rooms SET status = ? WHERE id = ?",
                        (new_status, room_id),
                    )
                    st.success("Đã cập nhật trạng thái phòng.")
                    st.rerun()

    with tab2:
        with st.form("add_room"):
            col1, col2 = st.columns(2)

            with col1:
                room_number = st.text_input("Số phòng *")
                room_type = st.selectbox(
                    "Loại phòng *",
                    ["Standard", "Superior", "Deluxe", "Suite", "Family", "VIP"]
                )
                floor = st.number_input("Tầng *", min_value=1, max_value=100, value=1)

            with col2:
                price = st.number_input(
                    "Giá phòng/đêm (VNĐ) *",
                    min_value=0,
                    value=900000,
                    step=100000
                )
                status = st.selectbox("Trạng thái", ROOM_STATUSES)

            submitted = st.form_submit_button(
                "➕ Thêm phòng",
                use_container_width=True
            )

            if submitted:
                if not room_number.strip():
                    st.error("Vui lòng nhập số phòng.")
                else:
                    try:
                        execute("""
                            INSERT INTO rooms
                            (room_number, room_type, floor, price, status)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            room_number.strip(),
                            room_type,
                            floor,
                            price,
                            status,
                        ))
                        st.success(f"Đã thêm phòng {room_number}.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Số phòng này đã tồn tại.")

# -----------------------------
# BOOKING MANAGEMENT
# -----------------------------
elif menu == "📅 Đặt phòng":
    st.title("📅 Quản lý đặt phòng")

    tab1, tab2 = st.tabs(["Danh sách đặt phòng", "Tạo đặt phòng"])

    with tab1:
        bookings = query_df("""
            SELECT
                b.id,
                g.full_name AS guest_name,
                g.phone,
                r.room_number,
                r.room_type,
                b.check_in,
                b.check_out,
                b.adults,
                b.children,
                b.status,
                b.note
            FROM bookings b
            JOIN guests g ON b.guest_id = g.id
            JOIN rooms r ON b.room_id = r.id
            ORDER BY b.id DESC
        """)

        if bookings.empty:
            st.info("Chưa có đơn đặt phòng.")
        else:
            search = st.text_input(
                "🔎 Tìm khách hàng / số phòng",
                placeholder="Nhập tên khách hoặc số phòng"
            )

            filtered = bookings.copy()

            if search.strip():
                mask = (
                    filtered["guest_name"].str.contains(search, case=False, na=False)
                    | filtered["room_number"].astype(str).str.contains(search, case=False, na=False)
                )
                filtered = filtered[mask]

            st.dataframe(
                filtered.rename(columns={
                    "id": "Mã",
                    "guest_name": "Khách hàng",
                    "phone": "SĐT",
                    "room_number": "Phòng",
                    "room_type": "Loại",
                    "check_in": "Nhận phòng",
                    "check_out": "Trả phòng",
                    "adults": "NL",
                    "children": "TE",
                    "status": "Trạng thái",
                    "note": "Ghi chú",
                }),
                use_container_width=True,
                hide_index=True,
            )

            st.subheader("Cập nhật trạng thái đặt phòng")

            booking_options = {
                f"#{row['id']} - {row['guest_name']} - Phòng {row['room_number']}": int(row["id"])
                for _, row in bookings.iterrows()
            }

            with st.form("update_booking"):
                selected_booking = st.selectbox(
                    "Chọn đơn đặt phòng",
                    list(booking_options.keys())
                )
                booking_status = st.selectbox(
                    "Trạng thái",
                    BOOKING_STATUSES
                )
                update_submit = st.form_submit_button(
                    "💾 Cập nhật",
                    use_container_width=True
                )

                if update_submit:
                    booking_id = booking_options[selected_booking]

                    booking_row = query_df(
                        "SELECT room_id FROM bookings WHERE id = ?",
                        (booking_id,)
                    )

                    if not booking_row.empty:
                        room_id = int(booking_row.iloc[0]["room_id"])

                        execute(
                            "UPDATE bookings SET status = ? WHERE id = ?",
                            (booking_status, booking_id)
                        )

                        # Đồng bộ trạng thái phòng
                        if booking_status == "Đã đặt":
                            room_status = "Đã đặt"
                        elif booking_status == "Đã nhận phòng":
                            room_status = "Đang ở"
                        elif booking_status == "Đã trả phòng":
                            room_status = "Bẩn"
                        elif booking_status == "Đã hủy":
                            room_status = "Trống"
                        else:
                            room_status = "Trống"

                        execute(
                            "UPDATE rooms SET status = ? WHERE id = ?",
                            (room_status, room_id)
                        )

                        st.success("Đã cập nhật đơn đặt phòng.")
                        st.rerun()

    with tab2:
        guests = query_df(
            "SELECT * FROM guests ORDER BY full_name"
        )

        rooms = query_df("""
            SELECT * FROM rooms
            WHERE status = 'Trống'
            ORDER BY floor, room_number
        """)

        if rooms.empty:
            st.warning("Hiện không có phòng trống để đặt.")
        else:
            with st.form("new_booking"):
                st.subheader("Thông tin khách")

                col1, col2 = st.columns(2)

                with col1:
                    full_name = st.text_input("Họ và tên khách *")
                    phone = st.text_input("Số điện thoại")
                    email = st.text_input("Email")

                with col2:
                    id_number = st.text_input("CCCD/Hộ chiếu")
                    adults = st.number_input(
                        "Số người lớn",
                        min_value=1,
                        max_value=20,
                        value=1
                    )
                    children = st.number_input(
                        "Số trẻ em",
                        min_value=0,
                        max_value=20,
                        value=0
                    )

                st.subheader("Thông tin phòng")

                room_options = {
                    f"Phòng {row['room_number']} - {row['room_type']} - {money(row['price'])}/đêm":
                    int(row["id"])
                    for _, row in rooms.iterrows()
                }

                selected_room = st.selectbox(
                    "Chọn phòng *",
                    list(room_options.keys())
                )

                col3, col4 = st.columns(2)

                with col3:
                    check_in = st.date_input(
                        "Ngày nhận phòng",
                        value=date.today()
                    )

                with col4:
                    check_out = st.date_input(
                        "Ngày trả phòng",
                        value=date.today()
                    )

                note = st.text_area("Ghi chú")

                submit = st.form_submit_button(
                    "📅 Tạo đặt phòng",
                    use_container_width=True
                )

                if submit:
                    if not full_name.strip():
                        st.error("Vui lòng nhập tên khách.")
                    elif check_out <= check_in:
                        st.error("Ngày trả phòng phải sau ngày nhận phòng.")
                    else:
                        guest_id = execute("""
                            INSERT INTO guests
                            (full_name, phone, email, id_number, created_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            full_name.strip(),
                            phone.strip(),
                            email.strip(),
                            id_number.strip(),
                            datetime.now().isoformat(timespec="seconds")
                        ))

                        room_id = room_options[selected_room]

                        execute("""
                            INSERT INTO bookings
                            (guest_id, room_id, check_in, check_out,
                             adults, children, status, note, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            guest_id,
                            room_id,
                            check_in.isoformat(),
                            check_out.isoformat(),
                            adults,
                            children,
                            "Đã đặt",
                            note.strip(),
                            datetime.now().isoformat(timespec="seconds")
                        ))

                        execute(
                            "UPDATE rooms SET status = 'Đã đặt' WHERE id = ?",
                            (room_id,)
                        )

                        st.success("🎉 Tạo đặt phòng thành công.")
                        st.rerun()

# -----------------------------
# GUEST MANAGEMENT
# -----------------------------
elif menu == "👤 Khách hàng":
    st.title("👤 Quản lý khách hàng")

    guests = query_df("""
        SELECT
            g.id,
            g.full_name,
            g.phone,
            g.email,
            g.id_number,
            g.created_at,
            COUNT(b.id) AS booking_count
        FROM guests g
        LEFT JOIN bookings b ON g.id = b.guest_id
        GROUP BY g.id
        ORDER BY g.id DESC
    """)

    if guests.empty:
        st.info("Chưa có khách hàng.")
    else:
        search = st.text_input(
            "🔎 Tìm khách hàng",
            placeholder="Tên, số điện thoại hoặc CCCD"
        )

        filtered = guests.copy()

        if search.strip():
            term = search.strip()
            mask = (
                filtered["full_name"].str.contains(term, case=False, na=False)
                | filtered["phone"].fillna("").str.contains(term, case=False, na=False)
                | filtered["id_number"].fillna("").str.contains(term, case=False, na=False)
            )
            filtered = filtered[mask]

        st.dataframe(
            filtered.rename(columns={
                "id": "ID",
                "full_name": "Họ tên",
                "phone": "Số điện thoại",
                "email": "Email",
                "id_number": "CCCD/Hộ chiếu",
                "created_at": "Ngày tạo",
                "booking_count": "Số lần đặt",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        st.subheader("Chi tiết lịch sử đặt phòng")

        guest_options = {
            f"{row['full_name']} - {row['phone'] or 'Không có SĐT'}": int(row["id"])
            for _, row in guests.iterrows()
        }

        selected_guest = st.selectbox(
            "Chọn khách hàng",
            list(guest_options.keys())
        )

        guest_id = guest_options[selected_guest]

        history = query_df("""
            SELECT
                b.id,
                r.room_number,
                r.room_type,
                b.check_in,
                b.check_out,
                b.status,
                b.note
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            WHERE b.guest_id = ?
            ORDER BY b.id DESC
        """, (guest_id,))

        if history.empty:
            st.info("Khách này chưa có lịch sử đặt phòng.")
        else:
            st.dataframe(
                history.rename(columns={
                    "id": "Mã đặt",
                    "room_number": "Phòng",
                    "room_type": "Loại phòng",
                    "check_in": "Nhận phòng",
                    "check_out": "Trả phòng",
                    "status": "Trạng thái",
                    "note": "Ghi chú",
                }),
                use_container_width=True,
                hide_index=True,
            )

# Footer
st.divider()
st.caption("🏨 Hotel Manager • Streamlit + SQLite")
