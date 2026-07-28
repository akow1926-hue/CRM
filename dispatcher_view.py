import streamlit as st
import pandas as pd
import ui_theme
import locales
from datetime import datetime

def render_dispatcher_view(df, t, courier_list, get_next_order_id_func, sheet_obj, send_tg_func, sms_mgr=None):
    """
    Панель Диспетчера с полной поддержкой двух языков (Русский / Uzbekcha)
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

def render_dispatcher_view(df, t, courier_list, get_next_order_id_func, sheet_obj, send_tg_func, sms_mgr=None):
    """
    Панель Диспетчера с поддержкой двух языков (Русский / Uzbekcha)
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

    # Метрики по 4 основным статусам
    new_cnt = len(df[df["Статус"] == "Ожидает забора"]) if not df.empty and "Статус" in df.columns else 0
    in_shop_cnt = len(df[df["Статус"] == "В цеху"]) if not df.empty and "Статус" in df.columns else 0
    ready_cnt = len(df[df["Статус"] == "Готов"]) if not df.empty and "Статус" in df.columns else 0
    done_cnt = len(df[df["Статус"] == "Выполнен"]) if not df.empty and "Статус" in df.columns else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📄 Ожидают забора", new_cnt)
    m2.metric("🧺 В цеху", in_shop_cnt)
    m3.metric("📦 Готов", ready_cnt)
    m4.metric("✅ Выполнен", done_cnt)

    st.divider()

    col_form, col_history = st.columns([6, 6])

    # Форма приёма нового заказа (Без выпадающего списка деталей вещей, детали вносит курьер/мойщик)
    with col_form:
        form_title = "➕ " + ("Оформить новый заказ" if lang == "ru" else "Yangi buyurtma rasmiylashtirish")
        st.subheader(form_title)
        with st.form("dispatcher_add_form", clear_on_submit=False):
            disp_name = st.text_input(locales.get_text("Dispatcher", lang), value=st.session_state.get("username", "Admin"), disabled=True)
            courier = st.selectbox(locales.get_text("assign_courier", lang), courier_list)

            c1, c2 = st.columns(2)
            mijoz_ismi = c1.text_input(locales.get_text("client_name", lang), placeholder="Алишер Назаров" if lang == "uz" else "Иван Иванов")
            tel = c2.text_input(locales.get_text("phone", lang) + " (9 " + ("raqam" if lang == "uz" else "цифр") + ") *", placeholder="901234567", max_chars=9)

            c3, c4 = st.columns(2)
            manzil = c3.text_input("Точный адрес *" if lang == "ru" else "To'liq manzil *", placeholder="ул. Навои 12, кв 4")
            hudud = c4.selectbox(locales.get_text("district", lang) + " *", ["Сиёб (Siyob)", "Багишамальский", "Согдиана", "Микрорайон", "Саттепо", "Железнодорожный", "Самаркандский р-н"])

            til = st.selectbox("Язык общения *" if lang == "ru" else "Muloqot tili *", ["O'zbek tili", "Русский язык", "Тоҷикӣ"])
            
            time_slots = ["В любое время", "Утро (09:00 - 12:00)", "День (12:00 - 17:00)", "Вечер (17:00 - 21:00)"] if lang == "ru" else ["Istalgan vaqtda", "Ertalab (09:00 - 12:00)", "Kunuduzi (12:00 - 17:00)", "Kechqurun (17:00 - 21:00)"]
            pickup_time_slot = st.selectbox(
                "Удобное время забора:" if lang == "ru" else "Olish uchun qulay vaqt:",
                time_slots
            )

            st.markdown("#### ⚡ " + ("Приоритет выполнения" if lang == "ru" else "Bajarish ustuvorligi"))
            priority_opts = ["Обычный", "🔥 СРОЧНЫЙ"] if lang == "ru" else ["Oddiy", "🔥 TEZKOR"]
            priority = st.radio("Приоритет заказа:" if lang == "ru" else "Buyurtma turi:", priority_opts, horizontal=True, key="disp_order_priority")

            delivery_date_str = ""
            delivery_time_str = ""
            if "СРОЧН" in priority or "TEZKOR" in priority:
                st.warning("⚠️ " + ("Укажите дату и время срочной доставки!" if lang == "ru" else "Tezkor yetkazib berish sana va vaqtini ko'rsating!"))
                cd1, cd2 = st.columns(2)
                d_date = cd1.date_input("Дата доставки *" if lang == "ru" else "Yetkazish sanasi *", value=datetime.today(), key="disp_deliv_date")
                d_time = cd2.time_input("Время доставки *" if lang == "ru" else "Yetkazish vaqti *", key="disp_deliv_time")
                delivery_date_str = d_date.strftime("%d.%m.%Y")
                delivery_time_str = d_time.strftime("%H:%M")

            extra_note = st.text_input("Ориентир по адресу / Примечание:" if lang == "ru" else "Manzil mo'ljali / Izoh:", placeholder="Например: рядом с поликлиникой" if lang == "ru" else "Masalan: kasxona yonida")

            submit_btn = st.form_submit_button("🚀 " + locales.get_text("take_order", lang), type="primary", use_container_width=True)

            if submit_btn:
                clean_tel = ''.join(filter(str.isdigit, tel))
                if not mijoz_ismi or not clean_tel or not manzil:
                    st.error(locales.get_text("required_fields", lang))
                elif len(clean_tel) != 9:
                    st.error(locales.get_text("phone_error", lang))
                else:
                    full_phone = f"+998 {clean_tel[:2]} {clean_tel[2:5]} {clean_tel[5:7]} {clean_tel[7:]}"
                    order_id = get_next_order_id_func(df)
                    date_now = pd.Timestamp.now().strftime("%d.%m.%Y, %H:%M:%S")

                    full_izoh = f"Время забора: {pickup_time_slot}"
                    if extra_note.strip():
                        full_izoh += f" | Примечание: {extra_note.strip()}"

                    if "СРОЧН" in priority or "TEZKOR" in priority:
                        full_izoh = f"🔥 СРОЧНО ({delivery_date_str} {delivery_time_str})! {full_izoh}"

                    try:
                        sheet_obj.append_row([
                            order_id, date_now, mijoz_ismi, full_phone, manzil,
                            full_izoh, 0, 0, "Ожидает забора",
                            courier, disp_name, hudud, til,
                            "-", "-", "-", "-"
                        ])

                        # Отправка Telegram уведомления курьеру
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

                        send_tg_func(tg_msg)

                        # SMS клиенту
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

    # Поиск и история заказов
    with col_history:
        st.subheader("🔍 " + locales.get_text("order_history", lang))
        search_q = st.text_input(locales.get_text("search_by_id", lang), placeholder="5200...")
        
        status_options = ["Все", "🔥 Срочные заказы", "Ожидает забора", "В цеху", "Готов", "Выполнен"] if lang == "ru" else ["Barchasi", "🔥 Tezkor buyurtmalar", "Olib ketish kutilmoqda", "Sexda", "Tayyor", "Bajarilgan"]
        status_f = st.selectbox("Фильтр по статусу:" if lang == "ru" else "Holat bo'yicha saralash:", status_options)

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

        cols = [c for c in ["ID", "Клиент", "Телефон", "Размеры", "Статус", "Курьер"] if c in disp_df.columns]
        st.dataframe(disp_df[cols], use_container_width=True, hide_index=True, height=350)

        if not disp_df.empty and "ID" in disp_df.columns:
            st.divider()
            st.markdown("#### ⚙️ Изменить статус / детали заказа")
            with st.expander("🛠️ Быстрое управление заказом диспетчером", expanded=False):
                sel_id_disp = st.selectbox("Выберите ID заказа для правки:", disp_df["ID"].unique().tolist(), key="disp_manage_sel_id")
                sel_row_disp = disp_df[disp_df["ID"] == sel_id_disp].iloc[0]
                
                curr_st = str(sel_row_disp.get("Статус", "Ожидает забора"))
                all_st_list = ["Ожидает забора", "В цеху", "Готов", "Выполнен"]
                st_idx = all_st_list.index(curr_st) if curr_st in all_st_list else 0
                
                new_st = st.selectbox("Новый статус заказа:", all_st_list, index=st_idx, key=f"disp_new_st_{sel_id_disp}")
                new_cour = st.selectbox("Изменить курьера:", courier_list, index=courier_list.index(sel_row_disp.get("Курьер", courier_list[0])) if sel_row_disp.get("Курьер") in courier_list else 0, key=f"disp_new_cour_{sel_id_disp}")
                
                if st.button("💾 Сохранить изменения заказа", type="primary", key=f"disp_save_btn_{sel_id_disp}", use_container_width=True):
                    try:
                        cell = sheet_obj.find(str(sel_id_disp))
                        row_num = cell.row
                        header_row = [str(h).strip() for h in sheet_obj.row_values(1)]
                        
                        if "Статус" in header_row:
                            sheet_obj.update_cell(row_num, header_row.index("Статус") + 1, new_st)
                        if "Курьер" in header_row:
                            sheet_obj.update_cell(row_num, header_row.index("Курьер") + 1, new_cour)
                            
                        send_tg_func(f"✏️ <b>Диспетчер {st.session_state.get('username','')} обновил заказ №{sel_id_disp}!</b>\nНовый статус: {new_st} | Курьер: {new_cour}")
                        st.success("✅ Заказ успешно обновлен!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка обновления заказа: {e}")



