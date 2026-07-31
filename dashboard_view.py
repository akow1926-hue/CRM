import pandas as pd
import plotly.express as px
import streamlit as st
import ui_theme
import locales

def safe_numeric_sum(series):
    try:
        clean_s = series.astype(str).str.replace(r"[^\d.]", "", regex=True)
        return float(pd.to_numeric(clean_s, errors="coerce").fillna(0).sum())
    except Exception:
        return 0.0

def render_dashboard_view(df):
    """
    Дашборд статистики CRM в стилистике Blue & Yellow
    """
    ui_theme.inject_theme()
    lang = st.session_state.get("lang", "ru")

    ui_theme.render_top_header(
        title="Главный дашборд",
        subtitle="Сводка по заказам и выручке Cosmo Cleaning Service",
        user_name=st.session_state.get("username", "Администратор"),
        user_role="Admin"
    )

    # 1. Метрики (Просто и понятно)
    total_orders = len(df)
    new_orders = len(df[df["Статус"] == "Ожидает забора"]) if not df.empty and "Статус" in df.columns else 0
    in_work = len(df[df["Статус"] == "В цеху"]) if not df.empty and "Статус" in df.columns else 0
    ready = len(df[df["Статус"] == "Готов"]) if not df.empty and "Статус" in df.columns else 0

    completed = len(df[df["Статус"] == "Выполнен"]) if not df.empty and "Статус" in df.columns else 0
    
    revenue = 0.0
    if not df.empty and "Сумма" in df.columns:
        completed_df = df[df["Статус"] == "Выполнен"]
        revenue = safe_numeric_sum(completed_df["Сумма"]) if not completed_df.empty else safe_numeric_sum(df["Сумма"])

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📦 Всего заказов", total_orders)
    m2.metric("📄 Новые (Забор)", new_orders)
    m3.metric("🧺 В цеху / Стирка", in_work)
    m4.metric("🚚 На доставку (Готов)", ready)
    m5.metric("💰 Выручка", f"{revenue:,.0f} сум")

    st.divider()

    # 2. Графики (Динамика + Статусы)
    col_g1, col_g2 = st.columns([6, 6])

    with col_g1:
        st.subheader("📊 Разделение по статусам")
        if not df.empty and "Статус" in df.columns:
            st_counts = df["Статус"].value_counts().reset_index()
            st_counts.columns = ["Статус", "Количество"]
            fig_pie = px.pie(st_counts, names="Статус", values="Количество", hole=0.4, color_discrete_sequence=["#f59e0b", "#3b82f6", "#60a5fa", "#d97706", "#2563eb"])
            fig_pie.update_layout(
                height=260, 
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#cbd5e1", family="Plus Jakarta Sans")
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Нет данных")

    with col_g2:
        st.subheader("📈 Динамика заказов")
        with st.expander("🔍 Показать график «Заказы по дням»", expanded=False):
            if not df.empty and "Дата" in df.columns:
                df_copy = df.copy()
                df_copy["ShortDate"] = df_copy["Дата"].astype(str).apply(lambda x: x.split(",")[0].strip() if "," in x else x[:10])
                daily_df = df_copy.groupby("ShortDate").size().reset_index(name="Количество")
                fig_line = px.bar(daily_df, x="ShortDate", y="Количество", text_auto=True, color_discrete_sequence=["#f59e0b"])
                fig_line.update_layout(
                    height=240, 
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#cbd5e1", family="Plus Jakarta Sans"),
                    xaxis=dict(gridcolor="#1e2c46"),
                    yaxis=dict(gridcolor="#1e2c46")
                )
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("Нет данных для графика")

    st.divider()

    # 3. Таблица последних заказов и топ клиентов
    col_t1, col_t2 = st.columns([7, 5])

    with col_t1:
        st.subheader("📋 Последние заказы")
        if not df.empty:
            cols = [c for c in ["ID", "Дата", "Клиент", "Телефон", "Сумма", "Статус"] if c in df.columns]
            st.dataframe(df[cols].tail(5).iloc[::-1], use_container_width=True, hide_index=True)
        else:
            st.info("Список заказов пуст")

    with col_t2:
        st.subheader("🏆 Топ клиентов")
        if not df.empty and "Клиент" in df.columns:
            top_df = df.groupby("Клиент").agg(
                Заказов=("ID", "count"),
                Сумма=("Сумма", safe_numeric_sum)
            ).reset_index().sort_values(by="Заказов", ascending=False).head(5)
            st.dataframe(top_df, use_container_width=True, hide_index=True)
        else:
            st.info("Нет данных по клиентам")
