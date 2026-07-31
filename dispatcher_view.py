import streamlit as st
import pandas as pd
import ui_theme
import locales
from datetime import datetime

def render_dispatcher_view(df, t, courier_list, get_next_order_id_func, add_order_func, update_order_func, send_tg_func, sms_mgr=None):
    """
    Панель Диспетчера: Адаптированная под мобильные устройства и ПК в стилистике Blue & Yellow
    """
    ui_theme.inject_theme()
    lang = st.session_state.get("lang", "ru")

    title_txt = locales.get_text("dispatcher_panel", lang)
    subtitle_txt = "Прием заказов и назначение курьеров" if lang == "ru" else "Buyurtmalarni qabul qilish va kuryerlarni tayinlash"

    ui_theme.render_top_header(
        title=title_txt,
        subtitle=subtitle_txt,
        user_name=st.session_state.get("username", "Диспетчер"),
        user_role="Dispatcher"
    )

    # Метрики по основным статусам
    new_cnt = len(df[df["Статус"] == "Ожидает забора"]) if not df.empty and "Статус" in df.columns else 0
    in_shop_cnt = len(df[df["Статус"] == "В цеху"]) if not df.empty and "Статус" in df.columns else 0
    ready_cnt = len(df[df["Статус"] == "Готов"]) if not df.empty and "Статус" in df.columns else 0
    done_cnt = len(df[df["Статус"] == "Выполнен"]) if not df.empty and "Статус" in df.columns else 0

    # Быстрые метрики для мобильных устройств
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📄 Забор", new_cnt)
    m2.metric("🧺 В цеху", in_shop_cnt)
    m3.metric("📦 Готовы", ready_cnt)
    m4.metric("✅ Выполнено", done_cnt)

    st.divider()

    # Табы для удобной навигации на телефонах
    tab_new, tab_list, tab_msg = st.tabs([
        "➕ Новый заказ",
        "📋 Поиск и редактирование",
        "💬 Сообщение курьерам"
    ])

    # ==================== ВКЛАДКА 1: ОФОРМЛЕНИЕ ЗАКАЗА ====================
    with tab_new:
        st.subheader("➕ " + ("Оформить новый заказ" if lang == "ru" else "Yangi buyurtma rasmiylashtirish"))

        with st.form("dispatcher_add_form", clear_on_submit=False):
            disp_name = st.session_state.get("username", "Admin")
            
            selected_couriers = st.multiselect(
                locales.get_text("assign_courier", lang) + " *",
                courier_list,
                default=[courier_list[0]] if courier_list else []
            )
            courier = ", ".join(selected_couriers) if selected_couriers else (courier_list[0] if courier_list else "Не назначен")

            c1, c2 = st.columns(2)
            mijoz_ismi = c1.text_input(locales.get_text("client_name", lang), placeholder="Алишер Назаров" if lang == "uz" else "Иван Иванов")
            tel = c2.text_input(locales.get_text("phone", lang) + " (9 цифр) *", placeholder="901234567", max_chars=9)

            c3, c4 = st.columns(2)
            manzil = c3.text_input("Точный адрес *", placeholder="ул. Навои 12, кв 4")
            hudud = c4.selectbox(locales.get_text("district", lang) + " *", ["Сиёб (Siyob)", "Багишамальский", "Согдиана", "Микрорайон", "Саттепо", "Железнодорожный", "Самаркандский р-н"])

            c5, c6 = st.columns(2)
            til = c5.selectbox("Язык общения *", ["O'zbek tili", "Русский язык", "Тоҷикӣ"])
            
            time_slots = ["В любое время", "Утро (09:00 - 12:00)", "День (12:00 - 17:00)", "Вечер (17:00 - 21:00)"]
            pickup_time_slot = c6.selectbox("Удобное время забора:", time_slots)

            st.markdown("##### ⚡ Приоритет заказа")
            priority_opts = ["Обычный", "🔥 СРОЧНЫЙ"]
            priority = st.radio("Приоритет:", priority_opts, horizontal=True, key="disp_order_priority")

            delivery_date_str = ""
            delivery_time_str = ""
            if "СРОЧН" in priority or "TEZKOR" in priority:
                st.warning("⚠️ Укажите дату и время срочной доставки!")
                cd1, cd2 = st.columns(2)
                d_date = cd1.date_input("Дата доставки *", value=datetime.today(), key="disp_deliv_date")
                d_time = cd2.time_input("Время доставки *", key="disp_deliv_time")
                delivery_date_str = d_date.strftime("%d.%m.%Y")
                delivery_time_str = d_time.strftime("%H:%M")

            extra_note = st.text_input("Ориентир по адресу / Примечание:", placeholder="Например: рядом с поликлиникой")

            submit_btn = st.form_submit_button("🚀 Оформить заказ и передать курьеру", type="primary", use_container_width=True)

            if submit_btn:
                clean_tel = ''.join(filter(str.isdigit, tel))
                if not mijoz_ismi or not clean_tel or not manzil:
                    st.error(locales.get_text("required_fields", lang))
                elif len(clean_tel) != 9:
                    st.error(locales.get_text("phone_error", lang))
                else:
                    full_phone = f"+998 {clean_tel[:2]} {clean_tel[2:5]} {clean_tel[5:7]} {clean_tel[7:]}"
                    order_id = get_next_order_id_func(df)

                    full_izoh = f"Время забора: {pickup_time_slot}"
                    if extra_note.strip():
                        full_izoh += f" | Примечание: {extra_note.strip()}"

                    if "СРОЧН" in priority or "TEZKOR" in priority:
                        full_izoh = f"🔥 СРОЧНО ({delivery_date_str} {delivery_time_str})! {full_izoh}"

                    try:
                        order_payload = {
                            "ID": order_id,
                            "Клиент": mijoz_ismi,
                            "Телефон": full_phone,
                            "Адрес": manzil,
                            "Размеры": full_izoh,
                            "Статус": "Ожидает забора",
                            "Курьер": courier,
                            "Диспетчер": disp_name,
                            "Район": hudud,
                            "Язык": til,
                            "Локация": "-",
                            "Оплачено": 0,
                            "Тип оплаты": "-",
                            "Причина": "-"
                        }
                        if add_order_func:
                            add_order_func(order_payload)

                        tg_msg = (
                            f"{'🚨 <b>СРОЧНЫЙ ЗАКАЗ №' + str(order_id) + '!</b>' if ('СРОЧН' in priority or 'TEZKOR' in priority) else '🆕 <b>Новый заказ №' + str(order_id) + '</b>'}\n"
                            f"👤 <b>Клиент:</b> {mijoz_ismi} ({full_phone})\n"
                            f"🏠 <b>Адрес:</b> {hudud}, {manzil}\n"
                            f"⏰ <b>Время забора:</b> {pickup_time_slot}\n"
                            f"🚗 <b>Курьер:</b> {courier}\n"
                        )
                        if "СРОЧН" in priority or "TEZKOR" in priority:
                            tg_msg += f"🔥 <b>Срок доставки:</b> {delivery_date_str} в {delivery_time_str}\n"
                        if extra_note.strip():
                            tg_msg += f"📍 <b>Ориентир:</b> {extra_note.strip()}\n"

                        send_tg_func(tg_msg, target_couriers=courier)

                        if sms_mgr:
                            sms_cfg = sms_mgr.get_sms_config()
                            if sms_cfg.get("enabled", True) and sms_cfg.get("auto_on_create", True):
                                order_data = {"client": mijoz_ismi, "order_id": order_id, "courier": courier, "sum": 0, "items": "Ковры"}
                                sms_body = sms_mgr.format_sms_message(sms_cfg.get("template_create_ru" if lang == "ru" else "template_create_uz", ""), order_data)
                                sms_mgr.send_sms_notification(full_phone, sms_body, order_id=order_id)

                        st.success(locales.get_text("order_created", lang).format(order_id=order_id, courier=courier))
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка сохранения: {e}")

    # ==================== ВКЛАДКА 2: ИСТОРИЯ И ПОИСК ЗАКАЗОВ ====================
    with tab_list:
        st.subheader("🔍 История и поиск заказов")
        c_search, c_filter = st.columns([1, 1])
        search_q = c_search.text_input(locales.get_text("search_by_id", lang), placeholder="5200 или Имя...", key="main_search_q")
        
        status_options = ["Все", "🔥 Срочные заказы", "Ожидает забора", "В цеху", "Готов", "Выполнен"] if lang == "ru" else ["Barchasi", "🔥 Tezkor buyurtmalar", "Olib ketish kutilmoqda", "Sexda", "Tayyor", "Bajarilgan"]
        status_f = c_filter.selectbox("Фильтр по статусу:" if lang == "ru" else "Holat bo'yicha:", status_options, key="main_status_f")

        disp_df = df.copy()
        if "Срочн" in status_f or "Tezkor" in status_f:
            disp_df = disp_df[disp_df["Размеры"].astype(str).str.contains("СРОЧНО|TEZKOR", case=False, na=False)]
        elif status_f not in ["Все", "Barchasi"]:
            if status_f in ["Готов", "Tayyor"]:
                disp_df = disp_df[disp_df["Статус"] == "Готов"]
            else:
                disp_df = disp_df[disp_df["Статус"] == status_f]
            
        if search_q.strip():
            disp_df = disp_df[disp_df["ID"].astype(str).str.contains(search_q) | disp_df["Клиент"].astype(str).str.contains(search_q, case=False)]

        cols = [c for c in ["ID", "Клиент", "Телефон", "Адрес", "Статус", "Курьер"] if c in disp_df.columns]
        st.dataframe(disp_df[cols], use_container_width=True, hide_index=True)

        if not disp_df.empty and "ID" in disp_df.columns:
            st.markdown("---")
            with st.expander("🛠️ Быстрое редактирование статуса / курьера", expanded=True):
                sel_id_disp = st.selectbox("Выберите ID заказа:", disp_df["ID"].unique().tolist(), key="disp_main_sel_id")
                sel_row_disp = disp_df[disp_df["ID"] == sel_id_disp].iloc[0]
                
                curr_st = str(sel_row_disp.get("Статус", "Ожидает забора"))
                all_st_list = ["Ожидает забора", "В цеху", "Готов", "Выполнен"]
                st_idx = all_st_list.index(curr_st) if curr_st in all_st_list else 0
                
                c_st, c_cr = st.columns(2)
                new_st = c_st.selectbox("Новый статус:", all_st_list, index=st_idx, key=f"disp_mn_st_{sel_id_disp}")
                
                curr_c_str = str(sel_row_disp.get("Курьер", ""))
                default_cour_sel = [c for c in courier_list if c in curr_c_str]
                if not default_cour_sel and courier_list:
                    default_cour_sel = [courier_list[0]]

                new_cour_list = c_cr.multiselect("Изменить курьеров:", courier_list, default=default_cour_sel, key=f"disp_mn_cour_{sel_id_disp}")
                new_cour = ", ".join(new_cour_list) if new_cour_list else curr_c_str

                if st.button("💾 Сохранить изменения", type="primary", key=f"disp_mn_save_{sel_id_disp}", use_container_width=True):
                    try:
                        if update_order_func:
                            update_order_func(sel_id_disp, {"Статус": new_st, "Курьер": new_cour})
                            
                        send_tg_func(f"✏️ <b>Диспетчер {st.session_state.get('username','')} обновил заказ №{sel_id_disp}!</b>\nНовый статус: {new_st} | Курьеры: {new_cour}", target_couriers=new_cour)
                        st.success("✅ Заказ сохранен!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка: {e}")

    # ==================== ВКЛАДКА 3: СООБЩЕНИЯ КУРЬЕРАМ ====================
    with tab_msg:
        st.subheader("💬 Отправить сообщение курьерам в Telegram")
        msg_couriers = st.multiselect("Выберите курьеров:", courier_list, default=courier_list, key="tab_msg_couriers_sel")
        custom_msg = st.text_area("Текст сообщения:", placeholder="Например: В районе Сиёб появился срочный забор ковров!", key="tab_custom_msg_text")
        if st.button("🚀 Отправить рассылку в Telegram", type="primary", key="tab_send_couriers_broadcast", use_container_width=True):
            if not msg_couriers:
                st.error("Выберите хотя бы одного курьера!")
            elif not custom_msg.strip():
                st.error("Введите текст сообщения!")
            else:
                c_str = ", ".join(msg_couriers)
                send_tg_func(f"📢 <b>Уведомление для курьеров ({c_str}):</b>\n\n{custom_msg.strip()}\n\n<i>Отправитель: Диспетчер {st.session_state.get('username','')}</i>", target_couriers=msg_couriers)
                st.success(f"Сообщение успешно отправлено курьерам: {c_str}!")
