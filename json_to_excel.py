import json
import pandas as pd
from datetime import datetime

def json_to_excel(json_file="all_products_full_data.json", output_excel="Fabio_Airsprings_Products.xlsx"):
    """
    Конвертирует JSON с товарами в удобный Excel файл
    """
    print(f"Загружаем файл: {json_file}")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Найдено товаров: {len(data)}")
    
    # Подготовим данные для Excel
    rows = []
    
    for product in data:
        article = product.get("article", "")
        category = product.get("category", "")
        cat_from_catalog = product.get("category_name_from_catalog", "")
        url = product.get("product_url", "")
        
        cross_list = product.get("cross", [])
        
        if not cross_list:
            # Если CROSS нет — добавляем одну строку
            rows.append({
                "Артикул": article,
                "Категория (на странице)": category,
                "Категория (из каталога)": cat_from_catalog,
                "Бренд Cross": "",
                "Номер Cross": "",
                "Ссылка": url
            })
        else:
            # Если есть CROSS — создаём отдельную строку для каждого
            for cross in cross_list:
                rows.append({
                    "Артикул": article,
                    "Категория (на странице)": category,
                    "Категория (из каталога)": cat_from_catalog,
                    "Бренд Cross": cross.get("brand", ""),
                    "Номер Cross": cross.get("number", ""),
                    "Ссылка": url
                })
    
    # Создаём DataFrame
    df = pd.DataFrame(rows)
    
    # Упорядочиваем колонки
    columns_order = [
        "Артикул",
        "Категория (на странице)",
        "Категория (из каталога)",
        "Бренд Cross",
        "Номер Cross",
        "Ссылка"
    ]
    df = df[columns_order]
    
    # Сохраняем в Excel
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_file = f"Fabio_Airsprings_Products_{timestamp}.xlsx"
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name="Все товары", index=False)
        
        # Добавляем лист со статистикой
        stats = {
            "Всего товаров": len(data),
            "Всего записей Cross": len(df),
            "Дата выгрузки": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        pd.DataFrame([stats]).to_excel(writer, sheet_name="Статистика", index=False)
    
    print(f"\n✅ Успешно сохранено в файл:")
    print(f"   {output_file}")
    print(f"   Строк в таблице: {len(df)}")
    
    # Дополнительно выводим пример
    print("\nПример первых 5 строк:")
    print(df.head().to_string(index=False))
    
    return output_file


# ====================== ЗАПУСК ======================
if __name__ == "__main__":
    json_to_excel(
        json_file="all_products_full_data.json",      # ← поменяй, если файл называется иначе
        output_excel="Fabio_Airsprings_Products.xlsx"
    )