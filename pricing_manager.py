import streamlit as st
import locales

# Базовый прайс-лист для ориентира
PRICING_CATALOG = {
    "carpet_normal": {"name_ru": "Ковер (Обычный)", "price": 14000, "unit": "кв.м"},
    "carpet_express": {"name_ru": "Ковер (Срочный)", "price": 20000, "unit": "кв.м"},
    "blanket": {"name_ru": "Курпача / Одеяло", "price": 15000, "unit": "шт / кв.м"},
    "curtain": {"name_ru": "Занавески", "price": 15000, "unit": "м"},
    "pillow": {"name_ru": "Подушка", "price": 10000, "unit": "шт"}
}

def render_interactive_calculator(key_prefix="calc", lang="ru"):
    """
    Простой и мгновенный замер ковров (Ширина × Длина = Площадь м² -> Авто-сумма)
    Возвращает (measurements_text: str, total_calculated_sum: int)
    """
    st.markdown("##### 📏 Быстрый замер ковра")

    c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 2])
    
    # 1. Размеры
    width = c1.number_input(
        "Ширина (м):" if lang == "ru" else "Eni (m):",
        min_value=0.0, max_value=20.0, value=2.0, step=0.1,
        key=f"{key_prefix}_w"
    )
    length = c2.number_input(
        "Длина (м):" if lang == "ru" else "Bo'yi (m):",
        min_value=0.0, max_value=30.0, value=3.0, step=0.1,
        key=f"{key_prefix}_l"
    )
    qty = c3.number_input(
        "Кол-во (шт):" if lang == "ru" else "Soni:",
        min_value=1, max_value=50, value=1, step=1,
        key=f"{key_prefix}_q"
    )

    # 2. Тариф за м²
    price_rate = c4.selectbox(
        "Тариф (сум / кв.м):" if lang == "ru" else "Tarif (so'm / kv.m):",
        [14000, 15000, 16000, 18000, 20000, 25000, 30000],
        index=0,
        format_func=lambda x: f"{x:,} сум/м²",
        key=f"{key_prefix}_rate"
    )

    # Расчет площади и стоимости
    area = round(width * length, 2)
    auto_sum = int(area * price_rate * qty)
    auto_text = f"Ковёр: {width}x{length}м ({area} кв.м)" if qty == 1 else f"Ковёр: {width}x{length}м ({area} кв.м) x {qty} шт"

    # Редактируемое итоговое поле
    c_res1, c_res2 = st.columns([2, 1.5])
    
    final_text = c_res1.text_input(
        "Замер / Текст заказа:" if lang == "ru" else "O'lchov matni:",
        value=auto_text,
        key=f"{key_prefix}_txt"
    )
    
    final_sum = c_res2.number_input(
        "Итоговая сумма (сум):" if lang == "ru" else "Yakuniy summa (so'm):",
        min_value=0, value=auto_sum, step=1000,
        key=f"{key_prefix}_sum"
    )

    st.caption(f"💡 Авто-расчет: **{area} кв.м** × **{price_rate:,} сум** = **{auto_sum:,} сум**")

    return final_text, int(final_sum)
