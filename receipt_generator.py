import os
from datetime import datetime

def generate_receipt_html(row: dict) -> str:
    """Генерация печатного HTML-чека для клиента"""
    order_id = str(row.get('ID', '-'))
    client = str(row.get('Клиент', '-'))
    phone = str(row.get('Телефон', '-'))
    address = f"{row.get('Район', '')}, {row.get('Адрес', '')}".strip(', ')
    items = str(row.get('Размеры', '-'))
    area = str(row.get('Площадь', '-'))
    
    try:
        sum_val = int(float(row.get('Сумма', 0)))
    except Exception:
        sum_val = 0
        
    try:
        paid_val = int(float(row.get('Оплачено', 0)))
    except Exception:
        paid_val = sum_val
        
    ptype = str(row.get('Тип оплаты', 'Наличные'))
    date_val = str(row.get('Дата', datetime.now().strftime("%d.%m.%Y, %H:%M")))
    reason = str(row.get('Причина', '-'))

    debt_info_html = ""
    if sum_val > paid_val:
        debt_val = sum_val - paid_val
        debt_info_html = f"""
        <div class="row" style="color: #dc2626; font-weight: bold;"><b>🔻 Остаток долга:</b> <span>{debt_val:,} сум</span></div>
        <div class="row" style="color: #dc2626;"><b>📝 Причина долга:</b> <span>{reason}</span></div>
        """

    receipt_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Чек №{order_id}</title>
    <style>
        body {{ font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #f8fafc; color: #0f172a; padding: 20px; margin: 0; }}
        .receipt-box {{ max-width: 420px; margin: 0 auto; background: #ffffff; border: 2px solid #2563eb; border-radius: 16px; padding: 24px; box-shadow: 0 10px 25px rgba(37,99,235,0.15); }}
        .header {{ text-align: center; border-bottom: 2px dashed #cbd5e1; padding-bottom: 16px; margin-bottom: 16px; }}
        .logo {{ font-size: 22px; font-weight: 800; color: #2563eb; letter-spacing: 0.5px; }}
        .subtitle {{ font-size: 13px; color: #64748b; margin-top: 4px; }}
        .row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }}
        .row b {{ color: #334155; }}
        .items {{ background: #f1f5f9; padding: 12px 14px; border-radius: 10px; margin: 14px 0; border-left: 4px solid #2563eb; font-size: 13px; line-height: 1.5; }}
        .total {{ font-size: 18px; font-weight: 800; text-align: right; border-top: 2px solid #2563eb; padding-top: 12px; margin-top: 14px; color: #1e3a8a; }}
        .footer {{ text-align: center; font-size: 12px; color: #64748b; margin-top: 20px; border-top: 1px solid #e2e8f0; padding-top: 12px; }}
    </style>
</head>
<body>
    <div class="receipt-box">
        <div class="header">
            <div class="logo">✨ Cosmo Cleaning Service ✨</div>
            <div class="subtitle">Электронный кассовый чек №{order_id}</div>
            <div class="subtitle">Дата: {date_val}</div>
        </div>
        <div class="row"><b>Клиент:</b> <span>{client}</span></div>
        <div class="row"><b>Телефон:</b> <span>{phone}</span></div>
        <div class="row"><b>Адрес доставки:</b> <span>{address}</span></div>
        
        <div class="items">
            <b>🧺 Размеры и детали:</b><br>{items}<br>
            <b>📐 Площадь:</b> {area} м²
        </div>

        <div class="row"><b>Итоговая сумма:</b> <span>{sum_val:,} сум</span></div>
        <div class="row"><b>Способ оплаты:</b> <span>{ptype}</span></div>
        {debt_info_html}
        <div class="total">
            Оплачено: {paid_val:,} сум
        </div>
        <div class="footer">
            Спасибо за заказ! 🧼<br>Cosmo Cleaning Service
        </div>
    </div>
</body>
</html>"""
    return receipt_html

def generate_receipt_text(row: dict) -> str:
    """Текстовая версия чека для сообщений в Telegram"""
    order_id = str(row.get('ID', '-'))
    client = str(row.get('Клиент', '-'))
    phone = str(row.get('Телефон', '-'))
    address = f"{row.get('Район', '')}, {row.get('Адрес', '')}".strip(', ')
    items = str(row.get('Размеры', '-'))
    area = str(row.get('Площадь', '-'))
    
    try:
        sum_val = int(float(row.get('Сумма', 0)))
    except Exception:
        sum_val = 0
        
    try:
        paid_val = int(float(row.get('Оплачено', 0)))
    except Exception:
        paid_val = sum_val
        
    ptype = str(row.get('Тип оплаты', 'Наличные'))
    date_val = str(row.get('Дата', datetime.now().strftime("%d.%m.%Y, %H:%M")))
    reason = str(row.get('Причина', '-'))

    msg = (
        f"🧾 **ЧЕК ОБ ОПЛАТЕ — ЗАКАЗ №{order_id}**\n\n"
        f"✨ **Cosmo Cleaning Service** ✨\n"
        f"📅 **Дата:** {date_val}\n"
        f"👤 **Клиент:** {client}\n"
        f"📞 **Тел:** `{phone}`\n"
        f"🏠 **Адрес:** {address}\n\n"
        f"🧺 **Размеры / Детали:** {items}\n"
        f"📐 **Площадь:** {area} м²\n"
        f"💰 **Итоговая сумма:** `{sum_val:,} сум`\n"
        f"💳 **Способ оплаты:** {ptype}\n"
        f"✅ **Оплачено:** `{paid_val:,} сум`\n"
    )
    if sum_val > paid_val > 0 or "Долг" in reason:
        debt_val = max(0, sum_val - paid_val)
        msg += f"🔻 **Остаток долга:** `{debt_val:,} сум`\n"
        msg += f"📝 **Причина долга:** {reason}\n"
    msg += "\n🧼 *Спасибо за заказ! Cosmo Cleaning Service*"
    return msg

