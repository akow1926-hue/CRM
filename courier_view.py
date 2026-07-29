import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import ui_theme
import locales
import sms_manager
import pricing_manager

def safe_numeric_val(val):
    try:
        clean_v = str(val).replace(" ", "").replace(",", ".").replace("сум", "").replace("so'm", "").strip()
        return float(clean_v)
    except Exception:
        return 0.0

def normalize_id(val):
    try:
        if pd.isna(val) or val is None:
            return ""
        s = str(val).strip()
        if s.endswith(".0"):
            s = s[:-2]
        return str(int(float(s)))
    except Exception:
        return str(val).strip()

def render_gps_button(order_id, lang="ru"):
    """Отображает HTML5 кнопку для захвата реальных GPS координат браузера курьера"""
    btn_text = "📍 Определить GPS координаты" if lang == "ru" else "📍 GPS koordinatalarni aniqlash"
    gps_html = f"""
    <div style="margin: 4px 0 8px 0; font-family: sans-serif;">
        <button onclick="getLocation_{order_id}()" type="button" style="
            background: #2563eb;
            color: white;
            border: none;
            padding: 8px 14px;
            border-radius: 8px;
            font-weight: 700;
            cursor: pointer;
            font-size: 13px;
            width: 100%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            box-shadow: 0 3px 6px rgba(37,99,235,0.3);
        ">
            {btn_text}
        </button>
        <span id="gps_status_{order_id}" style="display:block; margin-top: 4px; font-size: 11px; color: #60a5fa; font-weight: 600; text-align:center;"></span>
    </div>
    <script>
    function getLocation_{order_id}() {{
        var status = document.getElementById('gps_status_{order_id}');
        if (navigator.geolocation) {{
            status.innerText = "⏳ Определение координат...";
            navigator.geolocation.getCurrentPosition(function(position) {{
                var lat = position.coords.latitude.toFixed(6);
                var lng = position.coords.longitude.toFixed(6);
                var coordsStr = lat + ", " + lng;
                status.innerText = "✅ GPS: " + coordsStr + " (скопировано!)";
                if (navigator.clipboard) {{
                    navigator.clipboard.writeText(coordsStr);
                }}
            }}, function(error) {{
                status.innerText = "❌ Ошибка GPS: " + error.message;
            }}, {{ enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }});
        }} else {{
            status.innerText = "❌ Геолокация не поддерживается браузером.";
        }}
    }}
    </script>
    """
    components.html(gps_html, height=58)

def generate_receipt_html(row, lang="ru"):
    order_id = normalize_id(row.get('ID', '-'))
    client = row.get('Клиент', '-')
    phone = row.get('Телефон', '-')
    address = f"{row.get('Район', '')}, {row.get('Адрес', '')}".strip(', ')
    items = row.get('Размеры', '-')
    sum_val = int(safe_numeric_val(row.get('Сумма', 0)))
    paid_val = int(safe_numeric_val(row.get('Оплачено', 0))) or sum_val
    ptype = row.get('Тип оплаты', 'Наличные')
    date_val = row.get('Дата', '-')

    receipt_title = "Чек №" if lang == "ru" else "Kvitansiya №"
    client_lbl = "Клиент" if lang == "ru" else "Mijoz"
    addr_lbl = "Адрес" if lang == "ru" else "Manzil"
    item_lbl = "Заказ" if lang == "ru" else "Buyurtma"
    ptype_lbl = "Способ оплаты" if lang == "ru" else "To'lov usuli"
    paid_lbl = "Оплачено" if lang == "ru" else "To'landi"

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8">
        <style>
            body {{ font-family: sans-serif; padding: 20px; background: #ffffff; color: #0f172a; }}
            .box {{ max-width: 400px; margin: auto; border: 2px solid #2563eb; border-radius: 8px; padding: 16px; }}
            .hdr {{ text-align: center; border-bottom: 1px dashed #ccc; padding-bottom: 10px; margin-bottom: 10px; }}
            .total {{ font-weight: bold; font-size: 16px; border-top: 2px solid #2563eb; padding-top: 8px; margin-top: 10px; text-align: right; }}
        </style>
    </head>
    <body>
        <div class="box">
            <div class="hdr"><h2>✨ Cosmo Cleaning ✨</h2><div>{receipt_title} {order_id} | {date_val}</div></div>
            <div><b>{client_lbl}:</b> {client} ({phone})</div>
            <div><b>{addr_lbl}:</b> {address}</div>
            <div style="background:#f1f5f9; color:#0f172a; padding:8px; margin:8px 0;"><b>{item_lbl}:</b> {items}</div>
            <div><b>{ptype_lbl}:</b> {ptype}</div>
            <div class="total">{paid_lbl}: {paid_val:,} сум</div>
        </div>
    </body>
    </html>
    """

def render_courier_view(df, t, courier_name, update_order_func, get_yandex_route_url_func, send_tg_func, active_couriers=None, add_order_func=None, get_next_order_id_func=None, delete_order_func=None):
    """
    Панель Курьера: Заказы на забор и доставку, свободный выбор статуса при создании и умный поиск
    """
    ui_theme.inject_theme()
    lang = st.session_state.get("lang", "ru")

    if not active_couriers:
        active_couriers = ["Алишер Каримов", "Бобур Ибрагимов", "Сардор Турсунов", "Firuz", "Nazarov01"]

    ui_theme.render_top_header(
        title="Панель Курьера",
        subtitle=f"Курьер: {courier_name}",
        user_name=courier_name,
        user_role="Courier"
    )

    filter_options = ["📌 Назначенные мне & Свободные", "🌐 Все заказы CRM"] if lang == "ru" else ["📌 Menga tayinlanganlar", "🌐 Barcha buyurtmalar"]
    view_mode = st.radio(
        "Фильтр отображения:" if lang == "ru" else "Filtr:",
        filter_options,
        horizontal=True,
        key=f"cour_mode_{courier_name}"
    )

    if "Все" in view_mode or "Barcha" in view_mode:
        my_orders = df
    else:
        if not df.empty and "Курьер" in df.columns:
            c_str = df["Курьер"].astype(str).str.lower().str.strip()
            cn_lower = str(courier_name).lower().strip()
            mask_assigned = c_str.str.contains(cn_lower, regex=False, na=False)
            mask_unassigned = c_str.isin(["", "-", "не назначен", "nan", "none"])
            my_orders = df[mask_assigned | mask_unassigned].copy()
        else:
            my_orders = df.copy()

    # Фильтрация по статусам
    if not my_orders.empty and "Статус" in my_orders.columns:
        st_clean = my_orders["Статус"].astype(str).str.strip().str.lower()
        pickup_df = my_orders[st_clean.str.contains("забор|ожид|новы|yangi", regex=True, na=False)].copy()
        delivery_df = my_orders[st_clean.str.contains("готов|доставка|tayyor", regex=True, na=False)].copy()
        done_df = my_orders[st_clean.str.contains("выполн|заверш|bajaril", regex=True, na=False)].copy()
    else:
        pickup_df, delivery_df, done_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    pickup_cnt = len(pickup_df)
    ready_cnt = len(delivery_df)
    done_cnt = len(done_df)

    m1, m2, m3 = st.columns(3)
    m1.metric("📥 Забор", pickup_cnt)
    m2.metric("📦 Доставка", ready_cnt)
    m3.metric("✅ Выполнено", done_cnt)

    st.divider()

    tab_pickup, tab_delivery, tab_add_street, tab_all = st.tabs([
        f"📥 Забор ({pickup_cnt})",
        f"📦 Доставка ({ready_cnt})",
        "➕ Принять новый заказ",
        "📋 Все заказы"
    ])

    # ==================== ВКЛАДКА 1: ЗАЯВКИ НА ЗАБОР ====================
    with tab_pickup:
        if not pickup_df.empty:
            for idx, row in pickup_df.iterrows():
                o_id = row["ID"]
                norm_id = normalize_id(o_id)
                client = row.get("Клиент", "-")
                phone = row.get("Телефон", "-")
                address = row.get("Адрес", "-")
                district = row.get("Район", "")
                details = str(row.get("Размеры", "")).strip()
                existing_loc = str(row.get("Локация", ""))
                curr_courier = str(row.get("Курьер", courier_name))
                clean_tel = ''.join(filter(str.isdigit, str(phone)))

                # Мобильная карточка заказа
                st.markdown(f"""
                <div style="background: #111827; border: 1px solid #1f2937; border-radius: 14px; padding: 14px; margin-bottom: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
                    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 1px dashed #374151; padding-bottom: 8px; margin-bottom: 8px;">
                        <span style="font-size:17px; font-weight:800; color:#60a5fa;">📦 Заказ #{norm_id}</span>
                        <span style="background:rgba(245,158,11,0.2); color:#fbbf24; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:700;">🟡 Ожидает забора</span>
                    </div>
                    <div style="font-size:15px; font-weight:700; color:#ffffff; margin-bottom:4px;">👤 {client}</div>
                    <div style="font-size:14px; color:#9ca3af; margin-bottom:4px;">📞 <a href="tel:+{clean_tel}" style="color:#60a5fa; text-decoration:none; font-weight:700;">{phone}</a></div>
                    <div style="font-size:14px; color:#e2e8f0; margin-bottom:6px;">🏠 <b>{district}</b>, {address}</div>
                    {f'<div style="font-size:13px; color:#fbbf24; background:#1e1e38; padding:6px 10px; border-radius:8px; margin-bottom:6px;">📝 {details}</div>' if details and details != '-' else ''}
                </div>
                """, unsafe_allow_html=True)

                c_call, c_nav = st.columns(2)
                c_call.link_button("📞 Позвонить", f"tel:+{clean_tel}", use_container_width=True)

                res_tuple = get_yandex_route_url_func(district, address, existing_loc)
                r_url_pk = res_tuple[0] if isinstance(res_tuple, (tuple, list)) else res_tuple
                c_nav.link_button("🧭 Навигатор", r_url_pk, use_container_width=True)

                with st.expander(f"⚙️ Забрать ковры & Управление №{norm_id}", expanded=False):
                    
                    # 1. Принять заказ в цех
                    st.markdown("##### 🚚 1. Забор вещи и отправка в цех")
                    ci1, ci2, ci3 = st.columns(3)
                    cnt_kovr = ci1.number_input("🧼 Ковры:", min_value=0, value=1, step=1, key=f"k_pk_{norm_id}_{idx}")
                    cnt_kurp = ci2.number_input("🛋️ Курпачи:", min_value=0, value=0, step=1, key=f"kp_pk_{norm_id}_{idx}")
                    cnt_zan = ci3.number_input("🪟 Занавески:", min_value=0, value=0, step=1, key=f"z_pk_{norm_id}_{idx}")

                    extra_note = st.text_input("Заметка к вещам:", key=f"ex_pk_{norm_id}_{idx}")

                    if st.button("🚚 ПРИНЯТЬ И ОТПРАВИТЬ В ЦЕХ", type="primary", use_container_width=True, key=f"pickup_btn_{norm_id}_{idx}"):
                        items_parts = []
                        if cnt_kovr > 0: items_parts.append(f"Ковёр: {cnt_kovr} шт")
                        if cnt_kurp > 0: items_parts.append(f"Курпача: {cnt_kurp} шт")
                        if cnt_zan > 0: items_parts.append(f"Занавески: {cnt_zan} шт")
                        if extra_note.strip(): items_parts.append(f"Заметка: {extra_note.strip()}")
                        items_summary = ", ".join(items_parts) if items_parts else "Приняты вещи"

                        update_order_func(o_id, {
                            "Статус": "В цеху",
                            "Курьер": courier_name,
                            "Размеры": items_summary
                        })

                        try:
                            send_tg_func(
                                f"🚚 <b>Заказ №{norm_id} принят курьером {courier_name} и отправлен в цех!</b>\n"
                                f"👤 <b>Клиент:</b> {client} ({phone})\n"
                                f"🧺 <b>Принято:</b> {items_summary}"
                            )
                        except Exception:
                            pass

                        st.success(f"✅ Заказ №{norm_id} отправлен в цех!")
                        st.rerun()

                    st.markdown("---")
                    
                    # 2. Смена курьера
                    st.markdown("##### ⇄ 2. Смена курьера / передать другому")
                    other_couriers = [c for c in active_couriers if c != curr_courier]
                    if not other_couriers: other_couriers = active_couriers
                    target_courier_pk = st.selectbox("Передать курьеру:", other_couriers, key=f"tr_pk_{norm_id}_{idx}")
                    if st.button("⇄ Передать заказ", key=f"btn_tr_pk_{norm_id}_{idx}", use_container_width=True):
                        update_order_func(o_id, {"Курьер": target_courier_pk})
                        try:
                            send_tg_func(f"⇄ <b>Заказ №{norm_id} передан!</b> Курьер {courier_name} передал заказ курьеру {target_courier_pk}.", target_couriers=target_courier_pk)
                        except Exception:
                            pass
                        st.success(f"Заказ №{norm_id} передан курьеру {target_courier_pk}!")
                        st.rerun()

                    st.markdown("---")

                    # 3. Изменение точного адреса, заметки и GPS
                    st.markdown("##### ✏️ 3. Изменить точный адрес & GPS геолокацию")
                    edit_addr_val = st.text_input("Точный адрес:", value=address if address else "", key=f"edit_addr_pk_{norm_id}_{idx}")
                    
                    render_gps_button(f"edit_gps_pk_{norm_id}", lang=lang)
                    edit_loc_val = st.text_input("GPS координаты:", value=existing_loc if existing_loc not in ["-", ""] else "", key=f"edit_loc_pk_{norm_id}_{idx}")
                    edit_notes_val = st.text_input("Детали заказа / Заметка:", value=details if details else "", key=f"edit_notes_pk_{norm_id}_{idx}")

                    if st.button("💾 Сохранить изменения заказа", key=f"btn_save_edit_pk_{norm_id}_{idx}", use_container_width=True):
                        update_order_func(o_id, {
                            "Адрес": edit_addr_val.strip(),
                            "Локация": edit_loc_val.strip() if edit_loc_val.strip() else existing_loc,
                            "Размеры": edit_notes_val.strip()
                        })
                        st.success("✅ Изменения заказа сохранены!")
                        st.rerun()

                    st.markdown("---")

                    # 4. Удалить заказ
                    st.markdown("##### 🗑️ 4. Удалить заказ")
                    if st.button(f"🗑️ Удалить заказ №{norm_id}", type="secondary", key=f"btn_del_pk_{norm_id}_{idx}", use_container_width=True):
                        if delete_order_func:
                            delete_order_func(o_id)
                            try:
                                send_tg_func(f"🗑️ <b>Заказ №{norm_id} удален курьером {courier_name}!</b>")
                            except Exception:
                                pass
                            st.warning(f"Заказ №{norm_id} удален.")
                            st.rerun()
        else:
            st.info("🎉 Нет заказов, ожидающих забора.")

    # ==================== ВКЛАДКА 2: ГОТОВЫЕ ДОСТАВКИ ====================
    with tab_delivery:
        if not delivery_df.empty:
            for idx, row in delivery_df.iterrows():
                o_id = row["ID"]
                norm_id = normalize_id(o_id)
                client = row.get("Клиент", "-")
                phone = row.get("Телефон", "-")
                address = row.get("Адрес", "-")
                district = row.get("Район", "")
                items = str(row.get("Размеры", "-"))
                loc_saved = str(row.get("Локация", ""))
                curr_courier = str(row.get("Курьер", courier_name))
                order_sum = int(safe_numeric_val(row.get("Сумма", 0)))
                clean_tel = ''.join(filter(str.isdigit, str(phone)))

                # Мобильная карточка доставки
                st.markdown(f"""
                <div style="background: #111827; border: 1.5px solid #10b981; border-radius: 14px; padding: 14px; margin-bottom: 10px; box-shadow: 0 4px 12px rgba(16,185,129,0.15);">
                    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 1px dashed #374151; padding-bottom: 8px; margin-bottom: 8px;">
                        <span style="font-size:17px; font-weight:800; color:#34d399;">🚚 Доставка #{norm_id}</span>
                        <span style="background:rgba(16,185,129,0.2); color:#34d399; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:700;">🟢 Готов к выдаче</span>
                    </div>
                    <div style="font-size:15px; font-weight:700; color:#ffffff; margin-bottom:4px;">👤 {client}</div>
                    <div style="font-size:14px; color:#9ca3af; margin-bottom:4px;">📞 <a href="tel:+{clean_tel}" style="color:#60a5fa; text-decoration:none; font-weight:700;">{phone}</a></div>
                    <div style="font-size:14px; color:#e2e8f0; margin-bottom:6px;">🏠 <b>{district}</b>, {address}</div>
                    <div style="font-size:13px; color:#cbd5e1; background:#1e1e38; padding:6px 10px; border-radius:8px; margin-bottom:8px;">🧺 {items}</div>
                    <div style="font-size:16px; font-weight:800; color:#34d399; text-align:right;">💰 К оплате: {order_sum:,} сум</div>
                </div>
                """, unsafe_allow_html=True)

                res_tuple = get_yandex_route_url_func(district, address, loc_saved)
                r_url_deliv = res_tuple[0] if isinstance(res_tuple, (tuple, list)) else res_tuple

                c_call, c_nav = st.columns(2)
                c_call.link_button("📞 Позвонить", f"tel:+{clean_tel}", use_container_width=True)
                c_nav.link_button("🧭 Навигатор", r_url_deliv, use_container_width=True)

                with st.expander(f"✅ 1. ДОСТАВЛЕНО (Выдать и оплатить №{norm_id})", expanded=False):
                    p_type = st.radio("Способ оплаты:", ["Наличные", "Карта (Click/Payme)"], horizontal=True, key=f"pt_{norm_id}_{idx}")
                    p_paid = st.number_input("Оплачено (сум):", min_value=0, value=order_sum, step=1000, key=f"pp_{norm_id}_{idx}")
                    d_reason = ""
                    if p_paid < order_sum:
                        d_reason = st.text_input("Причина недоплаты / Скидка:", key=f"dr_{norm_id}_{idx}")

                    if st.button("✅ ВЫДАТЬ И ЗАКРЫТЬ ЗАКАЗ", type="primary", use_container_width=True, key=f"fin_deliv_{norm_id}_{idx}"):
                        if p_paid < order_sum and not d_reason.strip():
                            st.error("Укажите причину недоплаты!")
                        else:
                            update_order_func(o_id, {
                                "Статус": "Выполнен",
                                "Оплачено": int(p_paid),
                                "Тип оплаты": p_type,
                                "Причина": d_reason if d_reason.strip() else "Оплачено полностью"
                            })

                            try:
                                send_tg_func(f"✅ <b>Заказ №{norm_id} выдан клиенту!</b> Курьер: {courier_name}. Оплачено: {p_paid:,} сум.")
                            except Exception:
                                pass

                            try:
                                sms_cfg = sms_manager.get_sms_config()
                                if sms_cfg.get("enabled", True) and sms_cfg.get("auto_on_completed", True):
                                    sms_body = sms_manager.format_sms_message(sms_cfg.get("template_completed_ru", ""), {"client": client, "order_id": norm_id, "sum": f"{p_paid:,}"})
                                    sms_manager.send_sms_notification(phone, sms_body, order_id=norm_id)
                            except Exception:
                                pass

                            r_html = generate_receipt_html(row, lang=lang)
                            st.download_button(
                                label=f"🧾 Скачать Чек №{norm_id} (HTML)",
                                data=r_html,
                                file_name=f"receipt_{norm_id}.html",
                                mime="text/html",
                                key=f"dl_rec_{norm_id}_{idx}",
                                use_container_width=True
                            )
                            st.success(f"✅ Заказ №{norm_id} успешно выдан!")
                            st.rerun()

                with st.expander(f"⚙️ Смена курьера / Править адрес / Удалить №{norm_id}", expanded=False):
                    st.markdown("##### ⇄ Смена курьера / передать другому")
                    other_couriers = [c for c in active_couriers if c != curr_courier]
                    if not other_couriers: other_couriers = active_couriers
                    target_courier_deliv = st.selectbox("Передать курьеру:", other_couriers, key=f"tr_deliv_{norm_id}_{idx}")
                    if st.button("⇄ Передать заказ", key=f"btn_tr_deliv_{norm_id}_{idx}", use_container_width=True):
                        update_order_func(o_id, {"Курьер": target_courier_deliv})
                        try:
                            send_tg_func(f"⇄ <b>Заказ №{norm_id} передан!</b> Курьер {courier_name} передал заказ курьеру {target_courier_deliv}.", target_couriers=target_courier_deliv)
                        except Exception:
                            pass
                        st.success(f"Заказ №{norm_id} передан курьеру {target_courier_deliv}!")
                        st.rerun()

                    st.markdown("---")
                    st.markdown("##### ✏️ Изменить точный адрес & GPS геолокацию")
                    edit_addr_deliv = st.text_input("Точный адрес:", value=address if address else "", key=f"edit_addr_dl_{norm_id}_{idx}")
                    render_gps_button(f"edit_gps_dl_{norm_id}", lang=lang)
                    edit_loc_deliv = st.text_input("GPS координаты:", value=loc_saved if loc_saved not in ["-", ""] else "", key=f"edit_loc_dl_{norm_id}_{idx}")
                    edit_notes_deliv = st.text_input("Детали заказа / Заметка:", value=items if items else "", key=f"edit_notes_dl_{norm_id}_{idx}")

                    if st.button("💾 Сохранить изменения заказа", key=f"btn_save_edit_dl_{norm_id}_{idx}", use_container_width=True):
                        update_order_func(o_id, {
                            "Адрес": edit_addr_deliv.strip(),
                            "Локация": edit_loc_deliv.strip() if edit_loc_deliv.strip() else loc_saved,
                            "Размеры": edit_notes_deliv.strip()
                        })
                        st.success("✅ Изменения заказа сохранены!")
                        st.rerun()

                    st.markdown("---")
                    st.markdown("##### 🗑️ Удалить заказ")
                    if st.button(f"🗑️ Удалить заказ №{norm_id}", type="secondary", key=f"btn_del_dl_{norm_id}_{idx}", use_container_width=True):
                        if delete_order_func:
                            delete_order_func(o_id)
                            try:
                                send_tg_func(f"🗑️ <b>Заказ №{norm_id} удален курьером {courier_name}!</b>")
                            except Exception:
                                pass
                            st.warning(f"Заказ №{norm_id} удален.")
                            st.rerun()
        else:
            st.info("🎉 Нет готовых заказов на доставку.")

    # ==================== ВКЛАДКА 3: ПРИНЯТЬ НОВЫЙ ЗАКАЗ ====================
    with tab_add_street:
        st.subheader("➕ Оформить новый заказ (Реклама / С улицы)")
        
        street_status_choice = st.radio(
            "Статус создаваемого заказа:" if lang == "ru" else "Buyurtma holati:",
            ["🟡 Ожидает забора (Нужно забрать у клиента)", "🧺 В цеху (Уже привез в цех)"],
            horizontal=True,
            key=f"cour_st_choice_{courier_name}"
        )
        new_order_status = "Ожидает забора" if "забора" in street_status_choice else "В цеху"

        with st.form(key=f"cour_street_form_{courier_name}"):
            c1, c2 = st.columns(2)
            street_client = c1.text_input("Имя клиента *", placeholder="Иван")
            street_tel = c2.text_input("Телефон (9 цифр) *", placeholder="901234567", max_chars=9)

            c3, c4 = st.columns(2)
            street_district = c3.selectbox("Район *", ["Сиёб (Siyob)", "Багишамальский", "Согдиана", "Микрорайон", "Саттепо", "Железнодорожный", "Самаркандский р-н"])
            street_address = c4.text_input("Точный адрес *", placeholder="ул. Навои 14")

            render_gps_button(f"street_{courier_name}", lang=lang)
            street_loc = st.text_input("GPS Координаты:", placeholder="39.6542, 66.9750")

            ci1, ci2, ci3 = st.columns(3)
            cnt_k = ci1.number_input("🧼 Ковры:", min_value=0, value=1, step=1)
            cnt_kp = ci2.number_input("🛋️ Курпачи:", min_value=0, value=0, step=1)
            cnt_z = ci3.number_input("🪟 Занавески:", min_value=0, value=0, step=1)

            street_extra = st.text_input("Примечание / Заметка:")

            if st.form_submit_button("🚀 Сохранить и создать заказ", type="primary", use_container_width=True):
                clean_tel = ''.join(filter(str.isdigit, street_tel))
                if not street_client or not clean_tel or not street_address:
                    st.error("Заполните все обязательные поля!")
                elif len(clean_tel) != 9:
                    st.error("Номер телефона должен состоять из 9 цифр!")
                else:
                    full_phone = f"+998 {clean_tel[:2]} {clean_tel[2:5]} {clean_tel[5:7]} {clean_tel[7:]}"
                    new_id = get_next_order_id_func(df) if get_next_order_id_func else 5218
                    
                    items_parts = []
                    if cnt_k > 0: items_parts.append(f"Ковёр: {cnt_k} шт")
                    if cnt_kp > 0: items_parts.append(f"Курпача: {cnt_kp} шт")
                    if cnt_z > 0: items_parts.append(f"Занавески: {cnt_z} шт")
                    if street_extra.strip(): items_parts.append(f"Заметка: {street_extra.strip()}")
                    items_summary = ", ".join(items_parts) if items_parts else "Новый заказ"

                    order_payload = {
                        "ID": new_id,
                        "Клиент": street_client.strip(),
                        "Телефон": full_phone,
                        "Адрес": street_address.strip(),
                        "Размеры": items_summary,
                        "Статус": new_order_status,
                        "Курьер": courier_name,
                        "Диспетчер": f"Курьер {courier_name}",
                        "Район": street_district,
                        "Язык": "Русский язык",
                        "Локация": street_loc.strip() if street_loc.strip() else f"🗺️ {street_district}",
                        "Оплачено": 0,
                        "Тип оплаты": "-",
                        "Причина": "-"
                    }

                    if add_order_func:
                        add_order_func(order_payload)

                    try:
                        send_tg_func(f"🚚 <b>НОВЫЙ ЗАКАЗ №{new_id} ({new_order_status})!</b>\nКурьер: {courier_name}\nКлиент: {street_client} ({full_phone})\nАдрес: {street_district}, {street_address}")
                    except Exception:
                        pass

                    st.success(f"🎉 Заказ №{new_id} сохранен со статусом «{new_order_status}»!")
                    st.rerun()

    # ==================== ВКЛАДКА 4: ВСЕ ЗАКАЗЫ ====================
    with tab_all:
        if not my_orders.empty:
            cols = [c for c in ["ID", "Клиент", "Телефон", "Адрес", "Статус", "Курьер", "Сумма"] if c in my_orders.columns]
            st.dataframe(my_orders[cols], use_container_width=True, hide_index=True)
        else:
            st.info("Нет заказов.")
