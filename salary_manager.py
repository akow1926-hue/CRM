import os
import json
from datetime import datetime
import pandas as pd
import streamlit as st

SALARY_DATA_FILE = "salary_data.json"

DEFAULT_SALARY_CONFIG = {
    "courier_fee_per_order": 10000,    # Фиксированная ставка курьеру за заказ (сум)
    "courier_percent": 10,              # Или % от суммы заказа курьеру
    "courier_calc_mode": "fixed",       # 'fixed' или 'percent'
    
    "washer_fee_per_sqm": 2000,        # Ставка мойщику за 1 кв.м (сум)
    "washer_percent": 15,               # Или % от суммы стирки мойщику
    "washer_calc_mode": "fixed"         # 'fixed' или 'percent'
}

def load_salary_data():
    if os.path.exists(SALARY_DATA_FILE):
        try:
            with open(SALARY_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "config" not in data:
                    data["config"] = DEFAULT_SALARY_CONFIG
                if "payouts" not in data:
                    data["payouts"] = []
                return data
        except Exception:
            pass
    return {"config": DEFAULT_SALARY_CONFIG, "payouts": []}

def save_salary_data(data):
    try:
        with open(SALARY_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def safe_numeric_val(val):
    try:
        clean_v = str(val).replace(" ", "").replace(",", ".").replace("сум", "").replace("so'm", "").strip()
        return float(clean_v)
    except Exception:
        return 0.0

def calculate_employee_earnings(df, users_df):
    """
    Расчет начисленной зарплаты и комиссии для каждого курьера и мойщика
    """
    sal_data = load_salary_data()
    cfg = sal_data.get("config", DEFAULT_SALARY_CONFIG)
    payouts = sal_data.get("payouts", [])

    c_mode = cfg.get("courier_calc_mode", "fixed")
    c_fixed = cfg.get("courier_fee_per_order", 10000)
    c_pct = cfg.get("courier_percent", 10)

    w_mode = cfg.get("washer_calc_mode", "fixed")
    w_fixed = cfg.get("washer_fee_per_sqm", 2000)
    w_pct = cfg.get("washer_percent", 15)

    stats = {}

    # Получаем список сотрудников
    if not users_df.empty and "Username" in users_df.columns:
        for idx, row in users_df.iterrows():
            uname = str(row.get("Username", "")).strip()
            urole = str(row.get("Role", "")).strip()
            if uname:
                stats[uname] = {
                    "Username": uname,
                    "Role": urole,
                    "CompletedOrders": 0,
                    "TotalRevenue": 0.0,
                    "Earned": 0.0,
                    "Paid": 0.0,
                    "Balance": 0.0
                }

    # Считаем выполненные заказы из CRM
    if not df.empty and "Статус" in df.columns:
        completed_df = df[df["Статус"].astype(str).str.strip().isin(["Выполнен", "Готов", "В цеху"])]

        for idx, row in completed_df.iterrows():
            courier_name = str(row.get("Курьер", "")).strip()
            order_sum = safe_numeric_val(row.get("Сумма", 0))
            st_val = str(row.get("Статус", ""))

            # 1. Начисление Курьеру (за выполненные / доставленные заказы)
            if courier_name and st_val == "Выполнен":
                if courier_name not in stats:
                    stats[courier_name] = {
                        "Username": courier_name,
                        "Role": "Доставщик (Курьер)",
                        "CompletedOrders": 0,
                        "TotalRevenue": 0.0,
                        "Earned": 0.0,
                        "Paid": 0.0,
                        "Balance": 0.0
                    }

                stats[courier_name]["CompletedOrders"] += 1
                stats[courier_name]["TotalRevenue"] += order_sum

                if c_mode == "percent":
                    earned = order_sum * (c_pct / 100.0)
                else:
                    earned = float(c_fixed)

                stats[courier_name]["Earned"] += earned

            # 2. Начисление Мойщикам (за заказы в цехе/готовые)
            dispatcher_or_washer = str(row.get("Диспетчер", ""))
            if "Мойщик" in dispatcher_or_washer or "Washer" in dispatcher_or_washer:
                washer_name = dispatcher_or_washer
                if washer_name not in stats:
                    stats[washer_name] = {
                        "Username": washer_name,
                        "Role": "Мойщик",
                        "CompletedOrders": 0,
                        "TotalRevenue": 0.0,
                        "Earned": 0.0,
                        "Paid": 0.0,
                        "Balance": 0.0
                    }
                stats[washer_name]["CompletedOrders"] += 1
                stats[washer_name]["TotalRevenue"] += order_sum
                if w_mode == "percent":
                    stats[washer_name]["Earned"] += order_sum * (w_pct / 100.0)
                else:
                    stats[washer_name]["Earned"] += float(w_fixed) * 10  # Средняя площадь или ставка

    # Учитываем произведенные выплаты из истории payouts
    for p in payouts:
        uname = p.get("employee")
        amt = float(p.get("amount", 0))
        if uname in stats:
            stats[uname]["Paid"] += amt

    # Расчет остатка баланса (К выплате = Начислено - Выплачено)
    for uname, s in stats.items():
        s["Balance"] = s["Earned"] - s["Paid"]

    return pd.DataFrame(list(stats.values())), sal_data

def render_salary_ui(df, users_df):
    """
    Интерфейс управления зарплатами и комиссией сотрудников
    """
    st.subheader("💰 Расчет зарплат и комиссии сотрудников")

    emp_df, sal_data = calculate_employee_earnings(df, users_df)
    cfg = sal_data.get("config", DEFAULT_SALARY_CONFIG)

    # Общие сводные метрики
    total_earned = emp_df["Earned"].sum() if not emp_df.empty else 0.0
    total_paid = emp_df["Paid"].sum() if not emp_df.empty else 0.0
    total_balance = emp_df["Balance"].sum() if not emp_df.empty else 0.0

    m1, m2, m3 = st.columns(3)
    m1.metric("📊 Всего начислено (сум)", f"{total_earned:,.0f} сум")
    m2.metric("💳 Всего выплачено (сум)", f"{total_paid:,.0f} сум")
    m3.metric("⚠️ Долг по зарплате (сум)", f"{total_balance:,.0f} сум")

    st.divider()

    tab_payroll, tab_payout, tab_cfg = st.tabs([
        "📋 Ведомость начислений", "💳 Выплатить зарплату / аванс", "⚙️ Настройки ставок"
    ])

    # ==================== ВКЛАДКА 1: ВЕДОМОСТЬ НАЧИСЛЕНИЙ ====================
    with tab_payroll:
        st.markdown("#### 📋 Сводная ведомость доходов сотрудников")
        if not emp_df.empty:
            disp_df = emp_df.copy()
            disp_df.columns = ["Сотрудник", "Должность", "Выполнено заказов", "Оборот (сум)", "Начислено (сум)", "Выплачено (сум)", "Остаток к выплате (сум)"]
            
            # Форматирование сумм
            disp_df["Оборот (сум)"] = disp_df["Оборот (сум)"].apply(lambda x: f"{x:,.0f} сум")
            disp_df["Начислено (сум)"] = disp_df["Начислено (сум)"].apply(lambda x: f"{x:,.0f} сум")
            disp_df["Выплачено (сум)"] = disp_df["Выплачено (сум)"].apply(lambda x: f"{x:,.0f} сум")
            disp_df["Остаток к выплате (сум)"] = disp_df["Остаток к выплате (сум)"].apply(lambda x: f"{x:,.0f} сум")

            st.dataframe(disp_df, use_container_width=True, hide_index=True)
        else:
            st.info("Нет данных по сотрудникам.")

    # ==================== ВКЛАДКА 2: ВЫПЛАТА ЗАРПЛАТЫ ====================
    with tab_payout:
        st.markdown("#### 💳 Оформить выплату зарплаты или аванса")

        emp_list = emp_df["Username"].tolist() if not emp_df.empty else []
        if not emp_list:
            st.warning("Нет доступных сотрудников для выплаты.")
        else:
            with st.form("salary_payout_form", clear_on_submit=True):
                sel_emp = st.selectbox("Выберите сотрудника:", emp_list)
                
                # Показываем текущий баланс сотрудника
                emp_info = emp_df[emp_df["Username"] == sel_emp].iloc[0] if not emp_df.empty else {}
                curr_bal = emp_info.get("Balance", 0.0) if isinstance(emp_info, pd.Series) else 0.0
                st.info(f"💡 Текущий остаток к выплате для **{sel_emp}**: **{curr_bal:,.0f} сум**")

                c1, c2 = st.columns(2)
                payout_amt = c1.number_input("Сумма выплаты (сум):", min_value=1000, value=max(1000, int(curr_bal)) if curr_bal > 0 else 50000, step=5000)
                payout_mode = c2.selectbox("Способ выплаты:", ["Наличные", "Карта (Перевод / Click)", "Банковский перевод"])

                payout_note = st.text_input("Примечание / Заметка:", placeholder="Например: Зарплата за июль")

                if st.form_submit_button("🚀 Подтвердить выплату", type="primary", use_container_width=True):
                    new_payout = {
                        "id": len(sal_data.get("payouts", [])) + 1,
                        "date": datetime.now().strftime("%d.%m.%Y, %H:%M:%S"),
                        "employee": sel_emp,
                        "amount": int(payout_amt),
                        "mode": payout_mode,
                        "note": payout_note.strip() if payout_note.strip() else "Выплата зарплаты",
                        "admin": st.session_state.get("username", "Admin")
                    }
                    sal_data["payouts"].append(new_payout)
                    if save_salary_data(sal_data):
                        st.success(f"✅ Выплата в размере {payout_amt:,.0f} сум для сотрудника {sel_emp} успешно проведена!")
                        st.rerun()

            # История последних выплат
            st.markdown("---")
            st.markdown("##### 📜 История последних выплат зарплаты:")
            payouts_list = sal_data.get("payouts", [])
            if payouts_list:
                p_df = pd.DataFrame(payouts_list[::-1])
                cols = [c for c in ["date", "employee", "amount", "mode", "note", "admin"] if c in p_df.columns]
                st.dataframe(p_df[cols], use_container_width=True, hide_index=True)
            else:
                st.caption("История выплат пока пуста.")

    # ==================== ВКЛАДКА 3: НАСТРОЙКИ СТАВОК ====================
    with tab_cfg:
        st.markdown("#### ⚙️ Настройка правил комиссии и ставок")

        with st.form("salary_config_form"):
            st.markdown("##### 🚗 Ставки для курьеров:")
            c_calc_mode = st.radio("Принцип расчета курьерам:", ["Фиксированная плата за каждый заказ", "Процент % от суммы заказа"], index=0 if cfg.get("courier_calc_mode") == "fixed" else 1)
            c_fixed_val = st.number_input("Фиксированная ставка за 1 заказ (сум):", min_value=0, value=int(cfg.get("courier_fee_per_order", 10000)), step=1000)
            c_pct_val = st.number_input("Процент курьеру от заказа (%):", min_value=0, max_value=100, value=int(cfg.get("courier_percent", 10)), step=1)

            st.markdown("---")
            st.markdown("##### 🧺 Ставки для мойщиков:")
            w_calc_mode = st.radio("Принцип расчета мойщикам:", ["Фиксированная плата за каждый заказ", "Процент % от суммы стирки"], index=0 if cfg.get("washer_calc_mode") == "fixed" else 1)
            w_fixed_val = st.number_input("Ставка мойщику за 1 заказ (сум):", min_value=0, value=int(cfg.get("washer_fee_per_sqm", 2000)), step=500)
            w_pct_val = st.number_input("Процент мойщику от заказа (%):", min_value=0, max_value=100, value=int(cfg.get("washer_percent", 15)), step=1)

            if st.form_submit_button("💾 Сохранить правила зарплаты", type="primary", use_container_width=True):
                new_cfg = {
                    "courier_fee_per_order": int(c_fixed_val),
                    "courier_percent": int(c_pct_val),
                    "courier_calc_mode": "fixed" if "Фиксированная" in c_calc_mode else "percent",
                    "washer_fee_per_sqm": int(w_fixed_val),
                    "washer_percent": int(w_pct_val),
                    "washer_calc_mode": "fixed" if "Фиксированная" in w_calc_mode else "percent"
                }
                sal_data["config"] = new_cfg
                if save_salary_data(sal_data):
                    st.success("✅ Настройки ставок зарплаты и комиссии успешно обновлены!")
                    st.rerun()
