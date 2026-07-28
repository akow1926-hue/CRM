import streamlit as st
import locales

PRICING_CATALOG = {
    "carpet_express": {
        "name_ru": "Ковер / Гилам (Срочный 1-2 дня)",
        "name_uz": "Gilam (Tezkor 1-2 kun)",
        "unit": "кв.м",
        "type": "area",
        "price": 20000,
        "min_price": 20000,
        "max_price": 20000,
        "desc_ru": "20 000 сум / кв.м",
        "desc_uz": "20 000 so'm / kv.m"
    },
    "carpet_normal": {
        "name_ru": "Ковер / Гилам (Обычный 3-5 дней)",
        "name_uz": "Gilam (Oddiy 3-5 kun)",
        "unit": "кв.м",
        "type": "area",
        "price": 14000,
        "min_price": 13000,
        "max_price": 16000,
        "desc_ru": "13 000 - 16 000 сум / кв.м",
        "desc_uz": "13 000 - 16 000 so'm / kv.m"
    },
    "blanket": {
        "name_ru": "Одеяло / Курпача",
        "name_uz": "Ko'rpa / Ko'rpa-yostiq",
        "unit": "м / кв.м",
        "type": "area_or_meter",
        "price": 18000,
        "min_price": 15000,
        "max_price": 20000,
        "desc_ru": "15 000 - 20 000 сум / метр",
        "desc_uz": "15 000 - 20 000 so'm / metr"
    },
    "pillow": {
        "name_ru": "Подушка / Йостик",
        "name_uz": "Yostiq",
        "unit": "шт",
        "type": "piece",
        "price": 10000,
        "min_price": 10000,
        "max_price": 10000,
        "desc_ru": "10 000 сум / шт",
        "desc_uz": "10 000 so'm / dona"
    },
    "bedspread_1p": {
        "name_ru": "Покрывало / Yopqich (1-местное)",
        "name_uz": "Yopqich (1 kishilik)",
        "unit": "шт",
        "type": "piece",
        "price": 50000,
        "min_price": 50000,
        "max_price": 50000,
        "desc_ru": "50 000 сум / шт",
        "desc_uz": "50 000 so'm / dona"
    },
    "bedspread_2p": {
        "name_ru": "Покрывало / Yopqich (2-местное)",
        "name_uz": "Yopqich (2 kishilik)",
        "unit": "шт",
        "type": "piece",
        "price": 70000,
        "min_price": 70000,
        "max_price": 70000,
        "desc_ru": "70 000 сум / шт",
        "desc_uz": "70 000 so'm / dona"
    },
    "curtain_normal": {
        "name_ru": "Занавески / Парда (Обычные)",
        "name_uz": "Parda (Oddiy)",
        "unit": "м",
        "type": "meter",
        "price": 15000,
        "min_price": 15000,
        "max_price": 15000,
        "desc_ru": "15 000 сум / метр",
        "desc_uz": "15 000 so'm / metr"
    },
    "curtain_velour": {
        "name_ru": "Занавески / Парда (Вилюр)",
        "name_uz": "Parda (Velyur)",
        "unit": "м",
        "type": "meter",
        "price": 18000,
        "min_price": 18000,
        "max_price": 18000,
        "desc_ru": "18 000 сум / метр",
        "desc_uz": "18 000 so'm / metr"
    }
}

def render_interactive_calculator(key_prefix="calc", lang="ru"):
    """
    Интерактивный калькулятор расчета стоимости стирки и замеров вещей.
    Возвращает (measurements_text: str, total_calculated_sum: int)
    """
    title_text = "🧮 Интерактивный калькулятор услуг и прайс-лист" if lang == "ru" else "🧮 Interaktiv xizmatlar kalkulyatori"
    st.markdown(f"#### {title_text}")
    
    state_key = f"items_list_{key_prefix}"
    if state_key not in st.session_state:
        st.session_state[state_key] = []
        
    c1, c2, c3 = st.columns([2, 1, 1])
    
    item_type = c1.selectbox(
        "Выберите услугу / вещь:" if lang == "ru" else "Xizmat turini tanlang:",
        options=list(PRICING_CATALOG.keys()),
        format_func=lambda x: f"{PRICING_CATALOG[x]['name_' + lang]} ({PRICING_CATALOG[x]['desc_' + lang]})",
        key=f"{key_prefix}_item_sel"
    )
    
    info = PRICING_CATALOG[item_type]
    item_kind = info["type"]
    item_name = info["name_" + lang]
    
    w, l, qty = 0.0, 0.0, 1
    price_unit = info["price"]
    
    if item_kind in ["area", "area_or_meter"]:
        col_w, col_l, col_q = st.columns(3)
        w = col_w.number_input("Ширина (м):" if lang == "ru" else "Eni (m):", min_value=0.1, max_value=20.0, value=2.0, step=0.1, key=f"{key_prefix}_w")
        l = col_l.number_input("Длина (м):" if lang == "ru" else "Bo'yi (m):", min_value=0.1, max_value=30.0, value=3.0, step=0.1, key=f"{key_prefix}_l")
        qty = col_q.number_input("Кол-во (шт):" if lang == "ru" else "Soni (dona):", min_value=1, max_value=50, value=1, step=1, key=f"{key_prefix}_qty")
    elif item_kind == "meter":
        col_l, col_q = st.columns(2)
        l = col_l.number_input("Метраж (м):" if lang == "ru" else "Metraj (m):", min_value=0.5, max_value=100.0, value=5.0, step=0.5, key=f"{key_prefix}_m")
        qty = col_q.number_input("Кол-во (шт):" if lang == "ru" else "Soni (dona):", min_value=1, max_value=50, value=1, step=1, key=f"{key_prefix}_qty_m")
    else: # piece
        qty = st.number_input("Кол-во (шт):" if lang == "ru" else "Soni (dona):", min_value=1, max_value=100, value=1, step=1, key=f"{key_prefix}_qty_p")

    if info["min_price"] < info["max_price"]:
        price_unit = st.slider(
            f"Цена за {info['unit']} (сум):" if lang == "ru" else f"Narx ({info['unit']} uchun):",
            min_value=info["min_price"],
            max_value=info["max_price"],
            value=info["price"],
            step=1000,
            key=f"{key_prefix}_slider_price"
        )
    
    if item_kind in ["area", "area_or_meter"]:
        area = round(w * l, 2)
        item_total = int(area * price_unit * qty)
        detail_str = f"{item_name}: {w}x{l}м ({area} кв.м) x {qty} шт @ {price_unit:,} = {item_total:,} сум"
    elif item_kind == "meter":
        item_total = int(l * price_unit * qty)
        detail_str = f"{item_name}: {l}м x {qty} шт @ {price_unit:,} = {item_total:,} сум"
    else:
        item_total = int(price_unit * qty)
        detail_str = f"{item_name}: {qty} шт @ {price_unit:,} = {item_total:,} сум"
        
    st.info(f"💵 Расчет позиции: **{item_total:,} сум** ({detail_str})")
    
    col_add, col_clr = st.columns([2, 1])
    if col_add.button("➕ Добавить позицию в чек" if lang == "ru" else "➕ Chekka qo'shish", key=f"{key_prefix}_add_btn", use_container_width=True):
        st.session_state[state_key].append({
            "name": item_name,
            "detail": detail_str,
            "sum": item_total
        })
        st.success("Позиция добавлена!" if lang == "ru" else "Pozitsiya qo'shildi!")
        st.rerun()
        
    if col_clr.button("🗑️ Очистить калькулятор" if lang == "ru" else "🗑️ Tozalash", key=f"{key_prefix}_clr_btn", use_container_width=True):
        st.session_state[state_key] = []
        st.rerun()
        
    items_list = st.session_state[state_key]
    grand_total = sum(it["sum"] for it in items_list)
    
    if items_list:
        st.markdown("##### 📋 Забранные вещи:" if lang == "ru" else "##### 📋 Olingan narsalar:")
        for idx, it in enumerate(items_list):
            c_txt, c_del = st.columns([5, 1])
            c_txt.write(f"• **{it['detail']}**")
            if c_del.button("❌", key=f"{key_prefix}_del_{idx}"):
                st.session_state[state_key].pop(idx)
                st.rerun()
        st.markdown(f"### 💰 Итоговая авто-сумма: **{grand_total:,} сум**" if lang == "ru" else f"### 💰 Yakuniy summa: **{grand_total:,} so'm**")
    
    summary_text = "\n".join([it["detail"] for it in items_list]) if items_list else detail_str
    final_sum = grand_total if items_list else item_total
    
    return summary_text, final_sum
