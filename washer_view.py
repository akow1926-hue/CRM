import streamlit as st
import pandas as pd
import ui_theme
import locales
import pricing_manager
import sms_manager

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

def render_washer_view(df, t, washer_name, update_order_func, send_tg_func):
    """
    Минималистичная панель Мойщика (Цех) без лишнего текста и с быстрым обновлением статуса
    """
    ui_theme.inject_theme()
    lang = st.session_state.get("lang", "ru")

    ui_theme.render_top_header(
        title="Панель Цеха Мойки",
        subtitle=f"Мастер цеха: {washer_name}",
        user_name=washer_name,
        user_role="Washer"
    )

    if df.empty or "Статус" not in df.columns:
        st.info("В цеху пока нет заказов.")
        return

    # Фильтруем заказы со статусом 'В цеху', 'Мойка', 'В обработке' и т.д.
    shop_keywords = ["цех", "цеху", "цехе", "мойк", "стирк", "сушк", "обработк", "принят в цех"]
    
    def is_in_shop_status(val):
        s = str(val).strip().lower()
        if any(w in s for w in ["готов", "выполн", "ожид"]):
            return False
        return any(k in s for k in shop_keywords)

    wash_mask = df["Статус"].apply(is_in_shop_status)
    wash_df = df[wash_mask].copy()

    in_shop_cnt = len(wash_df)
    ready_cnt = len(df[df["Статус"] == "Готов"]) if "Статус" in df.columns else 0

    m1, m2 = st.columns(2)
    m1.metric("🧺 Заказы в цеху", in_shop_cnt)
    m2.metric("✅ Готовы к доставке", ready_cnt)

    st.divider()

    if wash_df.empty:
        st.success("🎉 В цеху чисто! Нет заказов, ожидающих мойку.")
        return

    # Подготавливаем список ID для выпадающего списка
    wash_df["normalized_id"] = wash_df["ID"].apply(normalize_id)
    id_options = wash_df["normalized_id"].tolist()

    # Оформление минималистичного интерфейса
    c_sel, c_info = st.columns([1, 1])
    
    with c_sel:
        selected_id_str = st.selectbox(
            "Выберите № заказа для мойки:",
            id_options,
            format_func=lambda x: f"📦 Заказ №{x}",
            key="washer_order_select"
        )

    # Находим строку выбранного заказа по нормализованному ID
    matching_rows = wash_df[wash_df["normalized_id"] == selected_id_str]
    if matching_rows.empty:
        st.warning("Заказ не найден или уже обновлен.")
        return

    row = matching_rows.iloc[0]
    raw_id = row["ID"]
    client_name = row.get("Клиент", "-")
    client_phone = row.get("Телефон", "-")
    district = row.get("Район", "")
    address = row.get("Адрес", "")
    existing_items = str(row.get("Размеры", "")).strip()
    existing_sum = safe_numeric_val(row.get("Сумма", 0))

    with c_info:
        st.markdown(f"""
        <div style="background:#131d33; border:1.5px solid #1d325c; border-left:4px solid #facc15; padding:14px; border-radius:12px; box-shadow: 0 4px 14px rgba(0,0,0,0.3);">
            <div style="font-size:17px; font-weight:800; color:#facc15;">📦 Заказ №{selected_id_str}</div>
            <div style="font-size:13px; color:#cbd5e1; margin-top:6px;">👤 Клиент: <b>{client_name}</b> ({client_phone})</div>
            <div style="font-size:13px; color:#cbd5e1; margin-top:2px;">🏠 Адрес: <b>{district}, {address}</b></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 🧮 Размеры и калькулятор")

    # Калькулятор расчета стоимости позиций
    calc_note, calc_sum = pricing_manager.render_interactive_calculator(key_prefix=f"w_calc_{selected_id_str}", lang=lang)

    st.markdown("---")

    # Кнопка завершения стирки
    if st.button("🧼 ПОМЫТО И ГОТОВО ✅", type="primary", use_container_width=True, key=f"btn_done_{selected_id_str}"):
        final_items = calc_note.strip() if calc_note.strip() else (existing_items if existing_items != "-" else "Постирано")
        final_sum = int(calc_sum) if calc_sum > 0 else int(existing_sum)

        try:
            # 1. Обновляем статус заказа на 'Готов'
            if update_order_func:
                update_order_func(raw_id, {
                    "Статус": "Готов",
                    "Размеры": final_items,
                    "Сумма": final_sum
                })

            # 2. Безопасная отправка в Telegram
            try:
                if send_tg_func:
                    tg_msg = (
                        f"📦 <b>ЗАКАЗ №{selected_id_str} ПОСТИРАН И ГОТОВ!</b>\n"
                        f"👤 <b>Клиент:</b> {client_name} ({client_phone})\n"
                        f"🧺 <b>Детали:</b> {final_items}\n"
                        f"💰 <b>Сумма к оплате:</b> {final_sum:,} сум"
                    )
                    send_tg_func(tg_msg)
            except Exception:
                pass

            # 3. Безопасная отправка СМС клиенту
            try:
                if client_phone and client_phone != "-":
                    sms_cfg = sms_manager.get_sms_config()
                    if sms_cfg.get("enabled", True) and sms_cfg.get("auto_on_ready", True):
                        sms_body = sms_manager.format_sms_message(
                            sms_cfg.get("template_ready_ru" if lang == "ru" else "template_ready_uz", ""),
                            {"client": client_name, "order_id": selected_id_str, "items": final_items, "sum": f"{final_sum:,}"}
                        )
                        sms_manager.send_sms_notification(client_phone, sms_body, order_id=selected_id_str)
            except Exception:
                pass

            st.success(f"✅ Заказ №{selected_id_str} успешно постиран и переведен в статус 'Готов'!")
            st.rerun()

        except Exception as err:
            st.error(f"Ошибка при обновлении заказа: {err}")
