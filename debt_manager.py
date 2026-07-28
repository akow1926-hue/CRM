import pandas as pd
import streamlit as st
import sms_manager
import locales

def safe_float(val):
    if pd.isna(val) or val is None:
        return 0.0
    val_str = str(val).replace(" ", "").replace(",", ".").replace("₽", "").replace("сум", "").strip()
    try:
        return float(val_str)
    except Exception:
        return 0.0

def get_debts_df(df):
    """Фильтрует заказы с имеющейся задолженностью клиентов"""
    if df.empty:
        return pd.DataFrame()

    df_copy = df.copy()

    def calc_debt(row):
        total_sum = safe_float(row.get("Сумма", 0))
        paid_sum = safe_float(row.get("Оплачено", 0))
        if total_sum > paid_sum:
            return total_sum - paid_sum
        return 0.0

    df_copy["Долг"] = df_copy.apply(calc_debt, axis=1)
    debts_df = df_copy[df_copy["Долг"] > 0]
    return debts_df

def render_debts_ui(df, update_order_fn=None):
    """Отображает аналитику по долгам и список должников с действиями"""
    lang = st.session_state.get("lang", "ru")
    st.markdown(f"### {locales.get_text('debts', lang)}")

    debts_df = get_debts_df(df)

    if debts_df.empty:
        st.success("🎉 Отлично! Ни у одного клиента нет задолженности по оплате." if lang == "ru" else "🎉 Ajoyib! Hech bir mijozda qarzdorlik yo'q.")
        return

    total_debt = debts_df["Долг"].sum()
    debtors_count = len(debts_df)
    avg_debt = total_debt / debtors_count if debtors_count > 0 else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("🔴 Общий долг клиентов" if lang == "ru" else "🔴 Umumiy qarzdorlik", f"{int(total_debt):,} сум")
    m2.metric("👥 Количество должников" if lang == "ru" else "👥 Qarzdorlar soni", f"{debtors_count} чел" if lang == "ru" else f"{debtors_count} kishi")
    m3.metric("📊 Средний долг на клиента" if lang == "ru" else "📊 O'rtacha qarzdorlik", f"{int(avg_debt):,} сум")

    st.divider()
    st.markdown("#### 📋 Список клиентов с задолженностью:" if lang == "ru" else "#### 📋 Qarzdor mijozlar ro'yxati:")

    for idx, row in debts_df.iterrows():
        order_id = str(row.get("ID", f"idx_{idx}"))
        client_name = row.get("Клиент", "Клиент")
        phone = row.get("Телефон", "")
        debt_val = int(row.get("Долг", 0))
        total_val = int(safe_float(row.get("Сумма", 0)))
        paid_val = int(safe_float(row.get("Оплачено", 0)))
        reason = row.get("Причина", "-")

        with st.container():
            col_info, col_act = st.columns([3, 2])

            with col_info:
                st.markdown(
                    f"🔻 **Заказ №{order_id}** | **{client_name}** (`{phone}`)\n"
                    f"• Всего к оплате: **{total_val:,} сум** | Оплачено: **{paid_val:,} сум**\n"
                    f"• 🚨 **Остаток долга: {debt_val:,} сум**\n"
                    f"• Причина/Скидка: *{reason}*"
                )

            with col_act:
                c_sms, c_pay = st.columns(2)

                if c_sms.button("📱 Напомнить СМС", key=f"debt_sms_{order_id}_{idx}"):
                    debt_msg = f"Уважаемый(ая) {client_name}, напоминаем о задолженности по заказу №{order_id} в размере {debt_val:,} сум. Cosmo Cleaning Service."
                    ok, res = sms_manager.send_sms_notification(phone, debt_msg, order_id=order_id)
                    if ok:
                        st.success(f"✅ СМС отправлено: {res}")
                    else:
                        st.error(f"❌ {res}")

                if c_pay.button("✅ Погасить долг", type="primary", key=f"debt_pay_{order_id}_{idx}"):
                    if update_order_fn:
                        success = update_order_fn(order_id, {"Оплачено": total_val, "Причина": "Долг полностью погашен"})
                        if success:
                            st.success(f"🎉 Долг по заказу №{order_id} полностью погашен!")
                            st.rerun()
                        else:
                            st.error("Ошибка при обновлении статуса в таблице.")
                    else:
                        st.warning("Функция обновления не привязана.")

            st.divider()
