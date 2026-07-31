import streamlit as st
import pandas as pd

def render_orders_view(df, update_order_func, generate_receipt_func):
    st.subheader("📋 Список заказов CRM и управление")

    if df.empty:
        st.info("В базе данных пока нет заказов.")
        return

    # Метрики заказов
    total_cnt = len(df)
    pickup_cnt = len(df[df["Статус"].astype(str).str.contains("Ожидает|Забор", case=False, na=False)])
    wash_cnt = len(df[df["Статус"].astype(str).str.contains("цеху|Цех|Стирка", case=False, na=False)])
    ready_cnt = len(df[df["Статус"].astype(str).str.contains("Готов|Доставка", case=False, na=False)])
    done_cnt = len(df[df["Статус"].astype(str).str.contains("Выполнен", case=False, na=False)])

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📊 Всего заказов", total_cnt)
    m2.metric("📦 Ожидают забора", pickup_cnt)
    m3.metric("🧺 В цеху", wash_cnt)
    m4.metric("🚚 Готовы к доставке", ready_cnt)
    m5.metric("✅ Выполнено", done_cnt)

    st.divider()

    # Поиск, Фильтры и Режим отображения
    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    search_q = col_f1.text_input("🔍 Быстрый поиск (по клиенту, телефону или ID):", key="orders_view_search")
    status_filter = col_f2.selectbox("Фильтр по статусу:", ["Все статусы", "Ожидает забора", "В цеху", "Готов", "Выполнен"], key="orders_view_status_filter")
    view_mode = col_f3.radio("Вид:", ["🗂️ Карточки", "📊 Таблица"], horizontal=True, key="orders_view_mode_select")

    filtered = df.copy()
    if status_filter != "Все статусы":
        filtered = filtered[filtered["Статус"].astype(str).str.contains(status_filter, case=False, na=False)]

    if search_q.strip():
        q = search_q.strip()
        filtered = filtered[
            filtered["ID"].astype(str).str.contains(q) |
            filtered["Клиент"].astype(str).str.contains(q, case=False) |
            filtered["Телефон"].astype(str).str.contains(q) |
            filtered["Адрес"].astype(str).str.contains(q, case=False)
        ]

    st.markdown(f"##### 📦 Отображается заказов: `{len(filtered)}`")

    # ---------------- ВАРИАНТ 1: СТИЛЬНЫЕ КАРТОЧКИ ЗАКАЗОВ ----------------
    if "Карточки" in view_mode:
        for idx, row in filtered.iterrows():
            o_id = str(row.get("ID", ""))
            client = str(row.get("Клиент", "-"))
            phone = str(row.get("Телефон", "-"))
            address = str(row.get("Адрес", "-"))
            district = str(row.get("Район", "Siyob"))
            status = str(row.get("Статус", "Ожидает забора"))
            sum_val = str(row.get("Сумма", "0"))
            date_val = str(row.get("Дата", ""))
            courier = str(row.get("Курьер", "-"))
            details = str(row.get("Размеры", "")).strip()

            # Определение цвета статуса
            status_bg = "#f59e0b"
            if "В цеху" in status: status_bg = "#3b82f6"
            elif "Готов" in status: status_bg = "#10b981"
            elif "Выполнен" in status: status_bg = "#8b5cf6"

            clean_tel = ''.join(filter(str.isdigit, phone))

            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #121b2d 0%, #0b1120 100%); border: 1px solid #1e2c46; border-left: 5px solid {status_bg}; border-radius: 12px; padding: 12px 16px; margin-bottom: 8px; box-shadow: 0 4px 14px rgba(0,0,0,0.25);">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 4px;">
                    <span style="background: rgba(245,158,11,0.14); border: 1px solid #f59e0b; color: #fbbf24; padding: 2px 8px; border-radius: 6px; font-weight: 800; font-size: 12px;">📦 № {o_id}</span>
                    <span style="background: {status_bg}; color: #ffffff; padding: 2px 8px; border-radius: 6px; font-weight: 700; font-size: 11.5px;">{status}</span>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 4px;">
                    <span style="font-size: 15px; font-weight: 800; color: #ffffff;">👤 {client}</span>
                    <span style="font-size: 11px; color: #94a3b8;">📅 {date_val}</span>
                </div>
                <div style="font-size: 13px; color: #cbd5e1; margin-bottom: 4px;">
                    📞 <a href="tel:+{clean_tel}" style="color: #fbbf24; text-decoration: none; font-weight: 700;">+{clean_tel}</a> | 🏠 <b>{district}</b> {address}
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; font-size: 12px; color: #94a3b8;">
                    <span>🚚 Курьер: <b>{courier}</b> | 📏 {details if details else 'Детали не указаны'}</span>
                    <span style="font-size: 14px; font-weight: 900; color: #fbbf24;">💰 {sum_val} сум</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Панель быстрых действий по заказу
            c_act1, c_act2 = st.columns([2, 1])
            status_list = ["Ожидает забора", "В цеху", "Готов", "Выполнен"]
            curr_idx = status_list.index(status) if status in status_list else 0
            new_st = c_act1.selectbox("Статус:", status_list, index=curr_idx, key=f"st_sel_ord_{o_id}_{idx}")
            if new_st != status:
                update_order_func(o_id, {"Статус": new_st})
                st.success(f"✅ Статус заказа №{o_id} изменен на «{new_st}»!")
                st.rerun()

            r_data = generate_receipt_func(row)
            c_act2.download_button("🧾 Скачать Чек", data=r_data, file_name=f"receipt_{o_id}.html", mime="text/html", key=f"dl_rec_{o_id}_{idx}", use_container_width=True)

    # ---------------- ВАРИАНТ 2: ИНТЕРАКТИВНАЯ ТАБЛИЦА ----------------
    else:
        st.dataframe(filtered, use_container_width=True, hide_index=True)
        if "ID" in filtered.columns and not filtered.empty:
            st.divider()
            st.markdown("#### 🧾 Чек по номеру заказа")
            col_rec1, col_rec2 = st.columns([2, 1])
            selected_id = col_rec1.selectbox("Выберите ID заказа:", filtered["ID"].unique().tolist(), key="orders_view_rec_select")
            if selected_id:
                sel_row = filtered[filtered["ID"] == selected_id].iloc[0]
                r_data = generate_receipt_func(sel_row)
                col_rec2.download_button(
                    label=f"🧾 Скачать Чек №{selected_id}",
                    data=r_data,
                    file_name=f"receipt_{selected_id}.html",
                    mime="text/html",
                    key=f"orders_view_download_receipt_btn_{selected_id}",
                    use_container_width=True
                )
