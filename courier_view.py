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
    btn_text = "📍 Определить GPS" if lang == "ru" else "📍 GPS аniqlash"
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
    Панель Курьера: Структура карточки по образцу 12.png (KV badge, № ID, 4 нижние цветные кнопки ⇄, ✓, ✏️, ❌)
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
        my_orders = df.copy()
    else:
        if not df.empty and "Курьер" in df.columns:
            c_str = df["Курьер"].astype(str).str.lower().str.strip()
            cn_lower = str(courier_name).lower().strip()
            mask_assigned = c_str.str.contains(cn_lower, regex=False, na=False)
            mask_unassigned = c_str.isin(["", "-", "не назначен", "nan", "none"])
            my_orders = df[mask_assigned | mask_unassigned].copy()
        else:
            my_orders = df.copy()

    # Разделение по статусам
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

    tab_pickup, tab_delivery, tab_add_street, tab_all = st.tabs([
        f"📥 Забор ({pickup_cnt})",
        f"📦 Доставка ({ready_cnt})",
        "➕ Принять новый заказ",
        "📋 Все заказы"
    ])

    def render_order_card(row, is_delivery=False):
        o_id = row["ID"]
        norm_id = normalize_id(o_id)
        client = str(row.get("Клиент", "-"))
        phone = str(row.get("Телефон", "-"))
        address = str(row.get("Адрес", "-"))
        district = str(row.get("Район", "Siyob"))
        details = str(row.get("Размеры", "")).strip()
        existing_loc = str(row.get("Локация", ""))
        curr_courier = str(row.get("Курьер", courier_name))
        dispatcher_name = str(row.get("Диспетчер", "Bobur"))
        date_str = str(row.get("Дата", "21.7.2026, 22:06:12"))
        lang_str = str(row.get("Язык", "tojik")).replace("Русский язык", "ru").replace("O'zbek tili", "uz")
        order_sum = int(safe_numeric_val(row.get("Сумма", 0)))
        clean_tel = ''.join(filter(str.isdigit, phone))

        # Извлечение числа ковров (KV)
        kv_count = "5"
        if "Ковёр:" in details or "Ковер:" in details:
            try:
                kv_count = details.split("шт")[0].split(":")[-1].strip()
            except Exception:
                kv_count = "1"

        res_tuple = get_yandex_route_url_func(district, address, existing_loc)
        r_url = res_tuple[0] if isinstance(res_tuple, (tuple, list)) else res_tuple

        # Карточка точь-в-точь по макету 12.png
        st.markdown(f"""
        <div style="background: #182030; border: 1px solid #2a3447; border-radius: 12px; padding: 12px; margin-bottom: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); font-family: sans-serif;">
            <!-- ВЕРХНЯЯ СТРОКА: KV Badge & № ID -->
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;">
                <span style="background: #059669; color: #ffffff; padding: 3px 8px; border-radius: 6px; font-weight: 800; font-size: 13px;">KV: {kv_count}</span>
                <span style="color: #9ca3af; font-size: 14px; font-weight: 700;">№ {norm_id}</span>
            </div>
            
            <!-- СТРОКА КУРЬЕРА И ДАТЫ -->
            <div style="display:flex; justify-content:space-between; align-items:center; font-size: 12px; color: #9ca3af; margin-bottom: 6px;">
                <span>🚚 {curr_courier}</span>
                <span>{date_str}</span>
            </div>
            
            <!-- ИМЯ КЛИЕНТА -->
            <div style="font-size: 15px; font-weight: 700; color: #ffffff; margin-bottom: 4px;">👤 {client}</div>
            
            <!-- ТЕЛЕФОН И ЗНАЧОК КРАСНОЙ ЛОКАЦИИ 📍 -->
            <div style="display:flex; justify-content:space-between; align-items:center; font-size: 14px; margin-bottom: 4px;">
                <span>📞 <a href="tel:+{clean_tel}" style="color: #3b82f6; text-decoration: none; font-weight: 700;">+{clean_tel}</a></span>
                <a href="{r_url}" target="_blank" title="Яндекс Навигатор" style="color: #ef4444; font-size: 18px; text-decoration: none; font-weight: bold;">📍</a>
            </div>
            
            <!-- РАЙОН И АДРЕС -->
            <div style="font-size: 13px; color: #e2e8f0; margin-bottom: 4px;">🏠 <b>{district}</b> {address}</div>
            
            <!-- ИНФО ЗНАЧКИ: ЯЗЫК, ДИСПЕТЧЕР, СКИДКА -->
            <div style="display:flex; gap: 8px; align-items:center; font-size: 12px; color: #9ca3af; margin-bottom: 4px;">
                <span style="background: #374151; color: #d1d5db; padding: 2px 6px; border-radius: 4px;">🗣️ {lang_str}</span>
                <span>👤 {dispatcher_name}</span>
                <span style="background: #059669; color: white; padding: 1px 5px; border-radius: 4px; font-weight:700;">%</span>
            </div>
            {f'<div style="font-size:13px; color:#34d399; font-weight:800; text-align:right; margin-top:4px;">💰 К оплате: {order_sum:,} сум</div>' if is_delivery else ''}
        </div>
        """, unsafe_allow_html=True)

        # 4 ЦВЕТНЫЕ КНОПКИ ДЕЙСТВИЯ В ОДИН РЯД (12.png)
        # 1: ⇄ (Темно-синяя - Смена курьера)
        # 2: ✓ (Зеленая - Одобрить / Принять в цех / Доставлено)
        # 3: ✏️ (Желтая - Редактировать №, Адрес, GPS)
        # 4: ❌ (Красная - Отмена / Удаление заказа)
        
        c_tr, c_ok, c_ed, c_del = st.columns(4)

        b_tr = c_tr.button("⇄", key=f"btn_tr_act_{norm_id}_{idx}", use_container_width=True, help="Смена курьера")
        b_ok = c_ok.button("✓", type="primary" if is_delivery else "secondary", key=f"btn_ok_act_{norm_id}_{idx}", use_container_width=True, help="Одобрить / Принять")
        b_ed = c_ed.button("✏️", key=f"btn_ed_act_{norm_id}_{idx}", use_container_width=True, help="Изменить №, адрес, GPS")
        b_del = c_del.button("❌", key=f"btn_del_act_{norm_id}_{idx}", use_container_width=True, help="Отменить заказ")

        state_key = f"active_action_{norm_id}"
        if b_tr:
            st.session_state[state_key] = "transfer" if st.session_state.get(state_key) != "transfer" else None
        elif b_ok:
            st.session_state[state_key] = "approve" if st.session_state.get(state_key) != "approve" else None
        elif b_ed:
            st.session_state[state_key] = "edit" if st.session_state.get(state_key) != "edit" else None
        elif b_del:
            st.session_state[state_key] = "cancel" if st.session_state.get(state_key) != "cancel" else None

        active_action = st.session_state.get(state_key)

        # ---------------- 1. ПАНЕЛЬ СМЕНЫ КУРЬЕРА (⇄) ----------------
        if active_action == "transfer":
            with st.container():
                st.markdown("##### ⇄ Смена курьера")
                other_couriers = [c for c in active_couriers if c != curr_courier]
                if not other_couriers: other_couriers = active_couriers
                target_courier = st.selectbox("Выберите нового курьера:", other_couriers, key=f"sel_tr_{norm_id}_{idx}")
                
                if st.button("🚀 Передать заказ курьеру & Отправить в Telegram", key=f"exec_tr_{norm_id}_{idx}", use_container_width=True):
                    update_order_func(o_id, {"Курьер": target_courier})
                    try:
                        send_tg_func(
                            f"⇄ <b>ЗАКАЗ №{norm_id} ПЕРЕДАН ВАМ!</b>\n"
                            f"Курьер {courier_name} передал вам заказ.\n"
                            f"👤 <b>Клиент:</b> {client} ({phone})\n"
                            f"🏠 <b>Адрес:</b> {district}, {address}\n\n"
                            f"<i>Нажмите в боте /accept_{norm_id} чтобы подтвердить прием!</i>",
                            target_couriers=target_courier
                        )
                    except Exception:
                        pass
                    st.success(f"Заказ №{norm_id} передан курьеру {target_courier}!")
                    st.session_state[state_key] = None
                    st.rerun()

        # ---------------- 2. ПАНЕЛЬ ОДОБРЕНИЯ / ПРИЕМА (✓) ----------------
        elif active_action == "approve":
            with st.container():
                if not is_delivery:
                    st.markdown("##### ✓ Принять заказ и отправить в цех")
                    ci1, ci2, ci3 = st.columns(3)
                    cnt_kovr = ci1.number_input("🧼 Ковры:", min_value=0, value=1, step=1, key=f"k_approve_{norm_id}_{idx}")
                    cnt_kurp = ci2.number_input("🛋️ Курпачи:", min_value=0, value=0, step=1, key=f"kp_approve_{norm_id}_{idx}")
                    cnt_zan = ci3.number_input("🪟 Занавески:", min_value=0, value=0, step=1, key=f"z_approve_{norm_id}_{idx}")
                    extra_note = st.text_input("Заметка к вещам:", key=f"ex_approve_{norm_id}_{idx}")

                    if st.button("🚚 ПОДТВЕРДИТЬ ПРИЕМ И ОТПРАВИТЬ В ЦЕХ", type="primary", use_container_width=True, key=f"exec_appr_{norm_id}_{idx}"):
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
                            send_tg_func(f"🚚 <b>Заказ №{norm_id} принят курьером {courier_name} и доставлен в цех!</b>\n👤 Клиент: {client} ({phone})\n🧺 Вещи: {items_summary}")
                        except Exception:
                            pass

                        st.success(f"✅ Заказ №{norm_id} принят и отправлен в цех!")
                        st.session_state[state_key] = None
                        st.rerun()
                else:
                    st.markdown("##### ✅ Завершить доставку и выдать заказ")
                    p_type = st.radio("Способ оплаты:", ["Наличные", "Карта (Click/Payme)"], horizontal=True, key=f"pt_appr_{norm_id}_{idx}")
                    p_paid = st.number_input("Оплачено (сум):", min_value=0, value=order_sum, step=1000, key=f"pp_appr_{norm_id}_{idx}")
                    d_reason = ""
                    if p_paid < order_sum:
                        d_reason = st.text_input("Причина недоплаты:", key=f"dr_appr_{norm_id}_{idx}")

                    if st.button("✅ ВЫДАТЬ ЗАКАЗ КЛИЕНТУ", type="primary", use_container_width=True, key=f"exec_deliv_{norm_id}_{idx}"):
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

                            r_html = generate_receipt_html(row, lang=lang)
                            st.download_button(
                                label=f"🧾 Скачать Чек №{norm_id} (HTML)",
                                data=r_html,
                                file_name=f"receipt_{norm_id}.html",
                                mime="text/html",
                                key=f"dl_rec_appr_{norm_id}_{idx}",
                                use_container_width=True
                            )
                            st.success(f"✅ Заказ №{norm_id} успешно выдан!")
                            st.session_state[state_key] = None
                            st.rerun()

        # ---------------- 3. ПАНЕЛЬ РЕДАКТИРОВАНИЯ (✏️) ----------------
        elif active_action == "edit":
            with st.container():
                st.markdown("##### ✏️ Редактирование номерации, адреса & GPS")
                new_id_val = st.text_input("Номерация / ID заказа (№):", value=norm_id, key=f"edit_id_{norm_id}_{idx}")
                new_addr_val = st.text_input("Точный адрес:", value=address, key=f"edit_addr_{norm_id}_{idx}")
                new_dist_val = st.selectbox("Район:", ["Сиёб (Siyob)", "Багишамальский", "Согдиана", "Микрорайон", "Саттепо", "Железнодорожный", "Самаркандский р-н"], index=0, key=f"edit_dist_{norm_id}_{idx}")
                
                render_gps_button(f"edit_gps_{norm_id}", lang=lang)
                new_loc_val = st.text_input("GPS координаты:", value=existing_loc if existing_loc not in ["-", ""] else "", key=f"edit_loc_{norm_id}_{idx}")

                if st.button("💾 Сохранить изменения", key=f"exec_edit_{norm_id}_{idx}", use_container_width=True):
                    updates_dict = {
                        "ID": new_id_val.strip() if new_id_val.strip() else norm_id,
                        "Адрес": new_addr_val.strip(),
                        "Район": new_dist_val,
                        "Локация": new_loc_val.strip() if new_loc_val.strip() else existing_loc
                    }
                    update_order_func(o_id, updates_dict)
                    st.success("✅ Данные заказа обновлены!")
                    st.session_state[state_key] = None
                    st.rerun()

        # ---------------- 4. ПАНЕЛЬ ОТМЕНЫ / УДАЛЕНИЯ (❌) ----------------
        elif active_action == "cancel":
            with st.container():
                st.warning(f"⚠️ Вы уверены, что хотите отменить/удалить заказ №{norm_id}?")
                c_cancel_confirm, c_cancel_abort = st.columns(2)
                
                if c_cancel_confirm.button("❌ Да, отменить заказ", key=f"exec_del_yes_{norm_id}_{idx}", use_container_width=True):
                    if delete_order_func:
                        delete_order_func(o_id)
                        try:
                            send_tg_func(f"❌ <b>Заказ №{norm_id} отменен/удален курьером {courier_name}!</b>")
                        except Exception:
                            pass
                        st.warning(f"Заказ №{norm_id} отменен.")
                        st.session_state[state_key] = None
                        st.rerun()

                if c_cancel_abort.button("↩️ Назад", key=f"exec_del_no_{norm_id}_{idx}", use_container_width=True):
                    st.session_state[state_key] = None
                    st.rerun()

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    # ==================== ВКЛАДКА 1: ЗАЯВКИ НА ЗАБОР ====================
    with tab_pickup:
        if not pickup_df.empty:
            for idx, row in pickup_df.iterrows():
                render_order_card(row, is_delivery=False)
        else:
            st.info("🎉 Нет заказов, ожидающих забора.")

    # ==================== ВКЛАДКА 2: ГОТОВЫЕ ДОСТАВКИ ====================
    with tab_delivery:
        if not delivery_df.empty:
            for idx, row in delivery_df.iterrows():
                render_order_card(row, is_delivery=True)
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
