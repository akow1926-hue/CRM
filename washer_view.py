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

def render_washer_view(df, t, washer_name, update_order_func, send_tg_func):
    """
    Панель Мойщика (Замер и стирка заказов в цеху -> Кнопка 'ПОМЫТО И ГОТОВО')
    """
    ui_theme.inject_theme()

    ui_theme.render_top_header(
        title="Панель Цеха Мойки",
        subtitle=f"Замер и стирка ковров (Сотрудник: {washer_name})",
        user_name=washer_name,
        user_role="Washer"
    )

    in_shop_cnt = len(df[df["Статус"] == "В цеху"]) if not df.empty and "Статус" in df.columns else 0
    ready_cnt = len(df[df["Статус"] == "Готов"]) if not df.empty and "Статус" in df.columns else 0

    m1, m2 = st.columns(2)
    m1.metric("🧺 Заказы в цеху (На замер и стирку)", in_shop_cnt)
    m2.metric("✅ Готовы к выдаче курьеру", ready_cnt)

    st.divider()

    wash_df = df[df["Статус"] == "В цеху"] if not df.empty and "Статус" in df.columns else pd.DataFrame()

    col_proc, col_list = st.columns([7, 5])

    with col_proc:
        st.subheader("📏 Замер и стирка заказа")
        if not wash_df.empty and "ID" in wash_df.columns:
            sel_id = st.selectbox("Выберите заказ в цеху:", wash_df["ID"].unique().tolist(), key="washer_sel_id")
            row = wash_df[wash_df["ID"] == sel_id].iloc[0]

            st.info(f"**Заказ #{sel_id}** | Клиент: {row.get('Клиент', '-')} (`{row.get('Телефон', '-')}`) | Статус: **{row.get('Статус', '-')}**")

            existing_items = str(row.get("Размеры", ""))
            existing_sum = safe_numeric_val(row.get("Сумма", 0))

            if existing_items and existing_items != "-":
                st.info(f"📋 **Текущие замеры:** {existing_items} | 💰 **Сумма:** {int(existing_sum):,} сум")
            else:
                st.warning("⚠️ **Внимание:** Внесите размеры ковров в калькулятор ниже.")

            st.markdown("#### 🧮 Проведение замера и расчет стоимости")
            m_txt, calc_s = pricing_manager.render_interactive_calculator(key_prefix=f"wash_{sel_id}", lang="ru")

            st.divider()
            
            # ВАЛИДАЦИЯ: Проверяем, внесены ли замер и сумма
            has_valid_measurement = (calc_s > 0 or existing_sum > 0) and bool(m_txt.strip() or (existing_items and existing_items != "-"))
            
            if st.button("🧼 ПОМЫТО И ГОТОВО ✅", type="primary", use_container_width=True, key=f"finish_wash_{sel_id}"):
                if not has_valid_measurement:
                    st.error("❌ ОШИБКА: Запрещено подтверждать стирку без замеров и расчета суммы! Сначала внесите позиции в калькулятор выше.")
                else:
                    new_s = calc_s if calc_s > 0 else existing_sum
                    new_m = m_txt if m_txt.strip() else existing_items

                    update_order_func(sel_id, {"Размеры": new_m, "Сумма": int(new_s), "Статус": "Готов"})
                    
                    tg_msg = (
                        f"📦 <b>ЗАКАЗ №{sel_id} ПОСТИРАН И ГОТОВ К ДОСТАВКЕ!</b>\n"
                        f"🚗 <b>Курьер:</b> {row.get('Курьер', 'Не назначен')}\n"
                        f"👤 <b>Клиент:</b> {row.get('Клиент', '')} ({row.get('Телефон', '')})\n"
                        f"🏠 <b>Адрес:</b> {row.get('Район', '')}, {row.get('Адрес', '')}\n"
                        f"📐 <b>Размеры и детали:</b> <b>{new_m}</b>\n"
                        f"💰 <b>Сумма к оплате:</b> <b>{int(new_s):,} сум</b>\n"
                        f"📍 <b>Локация клиента:</b> {row.get('Локация', 'Не указана')}"
                    )
                    send_tg_func(tg_msg)

                    phone_num = str(row.get("Телефон", ""))
                    if phone_num:
                        sms_cfg = sms_manager.get_sms_config()
                        if sms_cfg.get("enabled", True) and sms_cfg.get("auto_on_ready", True):
                            sms_body = sms_manager.format_sms_message(sms_cfg.get("template_ready_ru", ""), {"client": row.get("Клиент", ""), "order_id": sel_id, "items": new_m, "sum": f"{int(new_s):,}"})
                            sms_manager.send_sms_notification(phone_num, sms_body, order_id=sel_id)

                    st.success("🎉 Заказ постиран, упакован и переведен в статус 'Готов'!")
                    st.rerun()

        else:
            st.success("🎉 В цеху нет заказов на замер и стирку!")

    with col_list:
        st.subheader("📋 Очередь заказов цеха")
        if not wash_df.empty:
            cols = [c for c in ["ID", "Клиент", "Размеры", "Сумма", "Статус"] if c in wash_df.columns]
            st.dataframe(wash_df[cols], use_container_width=True, hide_index=True)
        else:
            st.info("Очередь цеха пуста")



