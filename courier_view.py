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

def render_gps_button(order_id, lang="ru"):
    """Отображает HTML5 кнопку для захвата реальных GPS координат браузера курьера"""
    btn_text = "📍 Определить GPS координаты" if lang == "ru" else "📍 GPS koordinatalarni aniqlash"
    gps_html = f"""
    <div style="margin: 6px 0 12px 0; font-family: sans-serif;">
        <button onclick="getLocation_{order_id}()" type="button" style="
            background: #2563eb;
            color: white;
            border: none;
            padding: 8px 14px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            font-size: 13px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            {btn_text}
        </button>
        <span id="gps_status_{order_id}" style="margin-left: 10px; font-size: 12px; color: #1e293b; font-weight: 600;"></span>
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
    components.html(gps_html, height=52)

def generate_receipt_html(row, lang="ru"):
    order_id = row.get('ID', '-')
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
    phone_lbl = "Тел" if lang == "ru" else "Tel"
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

def render_courier_view(df, t, courier_name, update_order_func, get_yandex_route_url_func, send_tg_func, active_couriers=None, add_order_func=None, get_next_order_id_func=None):
    """
    Панель Курьера с поддержкой принятия заказов с улицы (Реклама / Соседи) и двух языков
    """
    ui_theme.inject_theme()
    lang = st.session_state.get("lang", "ru")

    if not active_couriers:
        active_couriers = ["Алишер Каримов", "Бобур Ибрагимов", "Сардор Турсунов", "Firuz", "Nazarov01"]

    ui_theme.render_top_header(
        title=locales.get_text("courier_panel", lang),
        subtitle=f"{locales.get_text('Courier', lang)}: {courier_name}",
        user_name=courier_name,
        user_role="Courier"
    )

    my_orders = df[df["Курьер"] == courier_name] if not df.empty and "Курьер" in df.columns else df
    today_cnt = len(my_orders)
    done_cnt = len(my_orders[my_orders["Статус"] == "Выполнен"]) if not my_orders.empty and "Статус" in my_orders.columns else 0
    remain_cnt = max(0, today_cnt - done_cnt)

    m1, m2, m3 = st.columns(3)
    m1.metric("🚚 " + locales.get_text("today_orders", lang), today_cnt)
    m2.metric("✅ " + locales.get_text("completed", lang), done_cnt)
    m3.metric("⏳ " + locales.get_text("remaining", lang), remain_cnt)

    st.divider()

    # 4 ВКЛАДКИ ДЛЯ КУРЬЕРА
    tab_pickup, tab_add_street, tab_all, tab_delivery = st.tabs([
        "📥 " + ("Заявки на забор" if lang == "ru" else "Olib ketish arizalari"),
        "➕ " + ("Принять заказ с улицы (Реклама)" if lang == "ru" else "Ko'chadan buyurtma qabul qilish"),
        "📋 " + locales.get_text("all_orders", lang),
        "📦 " + ("Готовые доставки" if lang == "ru" else "Topshirishga tayyor")
    ])

    # ==================== ВКЛАДКА 1: ЗАЯВКИ (ЗАБОР В ЦЕХ) ====================
    with tab_pickup:

        st.subheader("📥 " + ("Заявки на забор ковров от клиентов" if lang == "ru" else "Mijozlardan gilam olib ketish arizalari"))
        pickup_df = my_orders[my_orders["Статус"] == "Ожидает забора"] if not my_orders.empty and "Статус" in my_orders.columns else pd.DataFrame()

        if not pickup_df.empty:
            for idx, row in pickup_df.iterrows():
                o_id = row["ID"]
                client = row["Клиент"]
                phone = row["Телефон"]
                address = row["Адрес"]
                district = row.get("Район", "")
                details = row.get("Размеры", "")
                existing_loc = str(row.get("Локация", ""))

                with st.expander(f"📦 Заборка №{o_id} — {client} ({district})", expanded=True):
                    st.write(f"👤 **{locales.get_text('client', lang)}:** {client} (`{phone}`)")
                    st.write(f"🗺️ **Район:** {district}")
                    if details and details != "-":
                        st.write(f"📝 **Примечание диспетчера:** {details}")

                    st.markdown("---")
                    st.markdown("##### 🏠 1. Точный адрес дома клиента")
                    cour_exact_address = st.text_input(
                        "Укажите или уточните точный адрес клиента (улица, дом, квартира):" if lang == "ru" else "Mijozning aniq manzilini kiriting:",
                        value=address if address else "",
                        placeholder="Например: ул. Навои 12, дом 4, кв 8",
                        key=f"cour_addr_{o_id}_{idx}"
                    )

                    st.markdown("##### 📍 2. Геолокация дома клиента (GPS)")
                    render_gps_button(o_id, lang=lang)
                    loc_val = st.text_input(
                        "Введите GPS координаты (например 39.6542, 66.9750) или вставьте скопированные:" if lang == "ru" else "GPS koordinatalar kiriting:",
                        value=existing_loc if existing_loc not in ["-", "", "📍 Геолокация не указана"] else "",
                        placeholder="39.6542, 66.9750",
                        key=f"cour_loc_input_{o_id}_{idx}"
                    )

                    st.markdown("##### 🧺 3. Выберите вещи, принимаемые у клиента")
                    st.caption("Укажите количество принимаемых предметов:" if lang == "ru" else "Qabul qilinayotgan buyumlar sonini ko'rsating:")
                    
                    ci1, ci2, ci3 = st.columns(3)
                    cnt_kovr = ci1.number_input("🧼 Ковры (шт):" if lang == "ru" else "🧼 Gilamlar (dona):", min_value=0, value=1, step=1, key=f"cnt_k_{o_id}_{idx}")
                    cnt_kurp = ci2.number_input("🛋️ Курпачи (шт):" if lang == "ru" else "🛋️ Ko'rpa (dona):", min_value=0, value=0, step=1, key=f"cnt_kp_{o_id}_{idx}")
                    cnt_zan = ci3.number_input("🪟 Занавески (шт):" if lang == "ru" else "🪟 Pardalar (dona):", min_value=0, value=0, step=1, key=f"cnt_z_{o_id}_{idx}")

                    ci4, ci5, ci6 = st.columns(3)
                    cnt_od = ci4.number_input("🛏️ Одеяла (шт):" if lang == "ru" else "🛏️ Adyollar (dona):", min_value=0, value=0, step=1, key=f"cnt_o_{o_id}_{idx}")
                    cnt_pokr = ci5.number_input("🛌 Покрывала (шт):" if lang == "ru" else "🛌 Yopinchiq (dona):", min_value=0, value=0, step=1, key=f"cnt_pk_{o_id}_{idx}")
                    cnt_pod = ci6.number_input("🛋️ Подушки (шт):" if lang == "ru" else "🛋️ Yostiqlar (dona):", min_value=0, value=0, step=1, key=f"cnt_pd_{o_id}_{idx}")

                    extra_items_note = st.text_input(
                        "Дополнительные заметки к вещам / редкие изделия:" if lang == "ru" else "Qo'shimcha izoh / boshqa buyumlar:",
                        placeholder="Например: 1 большой плед, пятно на ковре",
                        key=f"extra_note_{o_id}_{idx}"
                    )

                    c1, c2 = st.columns(2)
                    clean_tel = ''.join(filter(str.isdigit, str(phone)))
                    c1.link_button(locales.get_text("call_client", lang), f"tel:+{clean_tel}", use_container_width=True)

                    btn_pickup_label = "🚚 Принять заказ и отправить в цех" if lang == "ru" else "🚚 Buyurtmani qabul qilib sexga yuborish"
                    if c2.button(btn_pickup_label, type="primary", key=f"cour_pickup_{o_id}_{idx}", use_container_width=True):
                        final_addr = cour_exact_address.strip() if cour_exact_address.strip() else address
                        final_loc = loc_val.strip() if loc_val.strip() else f"🗺️ Ориентир: {district}"
                        
                        # Формируем читаемый список принятых вещей
                        items_parts = []
                        if cnt_kovr > 0: items_parts.append(f"Ковёр: {cnt_kovr} шт")
                        if cnt_kurp > 0: items_parts.append(f"Курпача: {cnt_kurp} шт")
                        if cnt_zan > 0: items_parts.append(f"Занавески: {cnt_zan} шт")
                        if cnt_od > 0: items_parts.append(f"Одеяло: {cnt_od} шт")
                        if cnt_pokr > 0: items_parts.append(f"Покрывало: {cnt_pokr} шт")
                        if cnt_pod > 0: items_parts.append(f"Подушка: {cnt_pod} шт")
                        if extra_items_note.strip(): items_parts.append(f"Заметка: {extra_items_note.strip()}")

                        items_summary = ", ".join(items_parts) if items_parts else "Приняты вещи"

                        update_order_func(o_id, {
                            "Статус": "В цеху",
                            "Адрес": final_addr,
                            "Локация": final_loc,
                            "Размеры": items_summary
                        })
                        
                        send_tg_func(
                            f"🚚 <b>Заказ №{o_id} принят курьером {courier_name} и доставлен в цех!</b>\n"
                            f"👤 <b>Клиент:</b> {client} ({phone})\n"
                            f"🏠 <b>Точный адрес:</b> {district}, {final_addr}\n"
                            f"📍 <b>GPS Геолокация:</b> {final_loc}\n"
                            f"🧺 <b>Принятые вещи:</b> {items_summary}"
                        )
                        st.success(f"Заказ №{o_id} принят, адрес и геолокация сохранены, статус переведен в 'В цеху'!")
                        st.rerun()
        else:
            st.info("🎉 " + ("Нет новых заявок на забор ковров." if lang == "ru" else "Yangi olib ketish arizalari yo'q."))

    # ==================== ВКЛАДКА: ПРИЕМ ЗАКАЗА С УЛИЦЫ (РЕКЛАМА / СОСЕДИ) ====================
    with tab_add_street:
        st.subheader("➕ " + ("Оформить новый заказ с улицы (Реклама / Соседи)" if lang == "ru" else "Ko'chadan yangi buyurtma qabul qilish"))
        st.info("ℹ️ " + ("Заполните эту форму, если во время выезда к вам обратился новый клиент с улицы (увидел машину/рекламу)." if lang == "ru" else "Mijoz ko'chadan murojaat qilsa ushbu shaklni to'ldiring."))
        
        with st.form(key=f"courier_add_street_form_{courier_name}"):
            st.write(f"🚗 **Принимает курьер:** `{courier_name}`")
            
            c_cl1, c_cl2 = st.columns(2)
            street_client = c_cl1.text_input("Имя клиента *" if lang == "ru" else "Mijoz ismi *", placeholder="Алишер (сосед)", key=f"st_cl_{courier_name}")
            street_tel = c_cl2.text_input("Телефон (9 цифр) *" if lang == "ru" else "Telefon (9 raqam) *", placeholder="901234567", max_chars=9, key=f"st_phone_{courier_name}")
            
            c_adr1, c_adr2 = st.columns(2)
            street_district = c_adr1.selectbox("Район клиента *" if lang == "ru" else "Tuman *", ["Сиёб (Siyob)", "Багишамальский", "Согдиана", "Микрорайон", "Саттепо", "Железнодорожный", "Самаркандский р-н"], key=f"st_distr_{courier_name}")
            street_address = c_adr2.text_input("Точный адрес *" if lang == "ru" else "Aniq manzil *", placeholder="ул. Навои 14, дом 2, кв 5", key=f"st_addr_{courier_name}")
            
            st.markdown("##### 📍 GPS координаты клиента")
            render_gps_button(f"street_{courier_name}", lang=lang)
            street_loc = st.text_input("GPS Координаты (например 39.6542, 66.9750):" if lang == "ru" else "GPS Koordinatalar:", placeholder="39.6542, 66.9750", key=f"cour_street_gps_{courier_name}")
            
            st.markdown("##### 🧺 Забираемые вещи")
            ci1, ci2, ci3 = st.columns(3)
            cnt_k = ci1.number_input("🧼 Ковры (шт):" if lang == "ru" else "🧼 Gilamlar (dona):", min_value=0, value=1, step=1, key=f"st_cnt_k_{courier_name}")
            cnt_kp = ci2.number_input("🛋️ Курпачи (шт):" if lang == "ru" else "🛋️ Ko'rpa (dona):", min_value=0, value=0, step=1, key=f"st_cnt_kp_{courier_name}")
            cnt_z = ci3.number_input("🪟 Занавески (шт):" if lang == "ru" else "🪟 Pardalar (dona):", min_value=0, value=0, step=1, key=f"st_cnt_z_{courier_name}")

            ci4, ci5, ci6 = st.columns(3)
            cnt_o = ci4.number_input("🛏️ Одеяла (шт):" if lang == "ru" else "🛏️ Adyollar (dona):", min_value=0, value=0, step=1, key=f"st_cnt_o_{courier_name}")
            cnt_pk = ci5.number_input("🛌 Покрывала (шт):" if lang == "ru" else "🛌 Yopinchiq (dona):", min_value=0, value=0, step=1, key=f"st_cnt_pk_{courier_name}")
            cnt_pd = ci6.number_input("🛋️ Подушки (шт):" if lang == "ru" else "🛋️ Yostiqlar (dona):", min_value=0, value=0, step=1, key=f"st_cnt_pd_{courier_name}")

            street_extra = st.text_input("Примечание / Доп. изделия:" if lang == "ru" else "Qo'shimcha izoh:", placeholder="Например: Заказ с рекламы на машине", key=f"st_extra_{courier_name}")

            street_submit = st.form_submit_button("🚚 Принять заказ и отправить в цех", type="primary", use_container_width=True)

            if street_submit:
                clean_tel = ''.join(filter(str.isdigit, street_tel))
                if not street_client or not clean_tel or not street_address:
                    st.error("Заполните имя клиента, телефон и адрес!" if lang == "ru" else "Mijoz ismi, telefon va manzilni kiriting!")
                elif len(clean_tel) != 9:
                    st.error("Номер телефона должен содержать 9 цифр!" if lang == "ru" else "Telefon 9 raqam bo'lishi kerak!")
                else:
                    full_phone = f"+998 {clean_tel[:2]} {clean_tel[2:5]} {clean_tel[5:7]} {clean_tel[7:]}"
                    new_id = get_next_order_id_func(df) if get_next_order_id_func else 5200
                    
                    items_parts = []
                    if cnt_k > 0: items_parts.append(f"Ковёр: {cnt_k} шт")
                    if cnt_kp > 0: items_parts.append(f"Курпача: {cnt_kp} шт")
                    if cnt_z > 0: items_parts.append(f"Занавески: {cnt_z} шт")
                    if cnt_o > 0: items_parts.append(f"Одеяло: {cnt_o} шт")
                    if cnt_pk > 0: items_parts.append(f"Покрывало: {cnt_pk} шт")
                    if cnt_pd > 0: items_parts.append(f"Подушка: {cnt_pd} шт")
                    if street_extra.strip(): items_parts.append(f"Заметка: {street_extra.strip()}")

                    items_summary = ", ".join(items_parts) if items_parts else "Приняты вещи с улицы"
                    final_loc = street_loc.strip() if street_loc.strip() else f"🗺️ Ориентир: {street_district}"

                    order_payload = {
                        "ID": new_id,
                        "Клиент": street_client.strip(),
                        "Телефон": full_phone,
                        "Адрес": street_address.strip(),
                        "Размеры": items_summary,
                        "Статус": "В цеху",
                        "Курьер": courier_name,
                        "Диспетчер": f"Курьер {courier_name} (Реклама)",
                        "Район": street_district,
                        "Язык": "Русский язык" if lang == "ru" else "O'zbek tili",
                        "Локация": final_loc,
                        "Оплачено": 0,
                        "Тип оплаты": "-",
                        "Причина": "-"
                    }

                    if add_order_func:
                        add_order_func(order_payload)

                    tg_msg = (
                        f"🚚 <b>НОВЫЙ ЗАКАЗ С УЛИЦЫ (РЕКЛАМА) №{new_id}!</b>\n"
                        f"🚗 <b>Принял курьер:</b> {courier_name}\n"
                        f"👤 <b>Клиент:</b> {street_client} ({full_phone})\n"
                        f"🏠 <b>Адрес:</b> {street_district}, {street_address}\n"
                        f"📍 <b>GPS:</b> {final_loc}\n"
                        f"🧺 <b>Принятые вещи:</b> {items_summary}"
                    )
                    send_tg_func(tg_msg)

                    sms_cfg = sms_manager.get_sms_config()
                    if sms_cfg.get("enabled", True) and sms_cfg.get("auto_on_create", True):
                        sms_body = sms_manager.format_sms_message(sms_cfg.get("template_create_ru" if lang == "ru" else "template_create_uz", ""), {"client": street_client, "order_id": new_id, "courier": courier_name, "sum": 0, "items": items_summary})
                        sms_manager.send_sms_notification(full_phone, sms_body, order_id=new_id)

                    st.success(f"🎉 Заказ №{new_id} от клиента {street_client} принят с улицы и отправлен в цех!")
                    st.rerun()

    # ==================== ВКЛАДКА 2: ВСЕ ЗАКАЗЫ ====================
    with tab_all:
        st.subheader("📋 " + locales.get_text("all_orders", lang))
        if not my_orders.empty:
            cols = [c for c in ["ID", "Клиент", "Телефон", "Адрес", "Статус", "Сумма", "Локация"] if c in my_orders.columns]
            st.dataframe(my_orders[cols], use_container_width=True, hide_index=True)
        else:
            st.info("У вас нет сохраненных заказов." if lang == "ru" else "Sizda saqlangan buyurtmalar yo'q.")

    # ==================== ВКЛАДКА 3: ГОТОВЫЕ ДОСТАВКИ ====================
    with tab_delivery:
        st.subheader("📦 " + ("Готовые ковры к доставке клиенту" if lang == "ru" else "Topshirishga tayyor gilamlar"))
        delivery_df = my_orders[my_orders["Статус"] == "Готов"] if not my_orders.empty and "Статус" in my_orders.columns else pd.DataFrame()

        if not delivery_df.empty:
            for idx, row in delivery_df.iterrows():
                o_id = row["ID"]
                client = row["Клиент"]
                phone = row["Телефон"]
                address = row["Адрес"]
                district = row.get("Район", "")
                items = row.get("Размеры", "-")
                loc_saved = str(row.get("Локация", ""))
                order_sum = safe_numeric_val(row.get("Сумма", 0))

                with st.expander(f"🚚 Доставка №{o_id} — {client} | {int(order_sum):,} сум", expanded=True):
                    st.write(f"👤 **{locales.get_text('client', lang)}:** {client} (`{phone}`)")
                    st.write(f"🏠 **{locales.get_text('address', lang)}:** {district}, {address}")
                    st.write(f"📍 **Сохраненная локация клиента:** `{loc_saved}`")
                    st.write(f"🧺 **Замеренные ковры:** {items}")
                    st.write(f"💰 **Итоговая сумма к оплате:** **{int(order_sum):,} сум**")

                    c1, c2, c3 = st.columns(3)
                    clean_tel = ''.join(filter(str.isdigit, str(phone)))
                    c1.link_button(locales.get_text("call_client", lang), f"tel:+{clean_tel}", use_container_width=True)

                    # Автоматическое построение маршрута по ранее указанной геолокации
                    r_url, is_exact_gps = get_yandex_route_url_func(district, address, loc_saved)
                    route_btn_label = "🗺️ Построить маршрут (GPS)" if is_exact_gps else "🗺️ Построить маршрут"
                    c2.link_button(route_btn_label, r_url, use_container_width=True)

                    # Передача другому курьеру
                    with c3:
                        popover_label = "⇄ Передать курьеру" if lang == "ru" else "⇄ Kuryerga topshirish"
                        with st.popover(popover_label):
                            other_couriers = [c for c in active_couriers if c != courier_name]
                            if not other_couriers:
                                other_couriers = [c for c in active_couriers]
                            target_courier = st.selectbox("Выберите курьера:" if lang == "ru" else "Kuryerni tanlang:", other_couriers, key=f"tr_cour_{o_id}_{idx}")
                            if st.button("Подтвердить передачу ⇄" if lang == "ru" else "Topshirishni tasdiqlash ⇄", key=f"tr_btn_{o_id}_{idx}"):
                                update_order_func(o_id, {"Курьер": target_courier})
                                send_tg_func(f"⇄ <b>Заказ №{o_id} передан!</b> Курьер {courier_name} передал заказ курьеру {target_courier}.")
                                st.success(f"Заказ передан курьеру {target_courier}!")
                                st.rerun()

                    st.divider()
                    st.markdown("##### 💵 " + ("Завершение доставки и расчет:" if lang == "ru" else "Yetkazishni yakunlash va hisob-kitob:"))
                    p_type = st.radio("Способ оплаты:" if lang == "ru" else "To'lov usuli:", ["Наличные", "Карта (Click/Payme)"] if lang == "ru" else ["Naqd", "Karta"], horizontal=True, key=f"ptype_{o_id}_{idx}")
                    p_paid = st.number_input("Фактически получено (сум):" if lang == "ru" else "Haqiqatda olindi (so'm):", min_value=0, value=int(order_sum), step=1000, key=f"ppaid_{o_id}_{idx}")
                    d_reason = ""
                    if p_paid < order_sum:
                        d_reason = st.text_input("Причина недоплаты / Скидка:" if lang == "ru" else "Kam to'lov sababi / Chegirma:", key=f"dreason_{o_id}_{idx}")

                    # При завершении доставки выдаче клиенту статус автоматически становится 'Выполнен'
                    if st.button("✅ " + ("Завершить доставку (Авто-статус -> Выполнен)" if lang == "ru" else "Tugatish (Bajarildi)"), type="primary", key=f"finish_deliv_{o_id}_{idx}", use_container_width=True):
                        if p_paid < order_sum and not d_reason.strip():
                            st.error("Укажите причину недоплаты!" if lang == "ru" else "Kam to'lov sababini ko'rsating!")
                        else:
                            update_order_func(o_id, {
                                "Статус": "Выполнен",
                                "Оплачено": int(p_paid),
                                "Тип оплаты": p_type,
                                "Причина": d_reason if d_reason.strip() else "Оплачено полностью"
                            })
                            send_tg_func(f"✅ <b>Заказ №{o_id} доставлен клиенту!</b> Курьер: {courier_name}. Оплачено: {p_paid:,} сум. Статус изменился на: Выполнен.")

                            sms_cfg = sms_manager.get_sms_config()
                            if sms_cfg.get("enabled", True) and sms_cfg.get("auto_on_completed", True):
                                sms_body = sms_manager.format_sms_message(sms_cfg.get("template_completed_ru" if lang == "ru" else "template_completed_uz", ""), {"client": client, "order_id": o_id, "sum": f"{p_paid:,}"})
                                sms_manager.send_sms_notification(phone, sms_body, order_id=o_id)

                            r_html = generate_receipt_html(row, lang=lang)
                            st.download_button(
                                label=f"🧾 Скачать Чек №{o_id} (HTML)" if lang == "ru" else f"🧾 Kvitansiyani yuklab olish №{o_id} (HTML)",
                                data=r_html,
                                file_name=f"receipt_{o_id}.html",
                                mime="text/html",
                                key=f"receipt_dl_{o_id}_{idx}",
                                use_container_width=True
                            )
                            st.success("Заказ успешно выдан клиенту! Программа автоматически изменила статус на 'Выполнен'." if lang == "ru" else "Buyurtma yopildi (Bajarildi)!")
                            st.rerun()
        else:
            st.info("🎉 " + ("Нет готовых ковров на доставку." if lang == "ru" else "Topshirishga tayyor gilamlar yo'q."))

