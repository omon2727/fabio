import json
import pandas as pd
from datetime import datetime


def json_to_excel(json_file="all_products_full_data.json", 
                  output_excel="Fabio_Airsprings_Products.xlsx"):
    """
    Конвертирует JSON в Excel + удаляет дубли по артикулу + добавляет OEM
    """
    print(f"Загружаем файл: {json_file}")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Найдено товаров в JSON: {len(data)}")
    
    # === УДАЛЕНИЕ ДУБЛИКАТОВ ПО АРТИКУЛУ ===
    seen = set()
    unique_data = []
    
    for product in data:
        article = product.get("article", "").strip()
        if article and article not in seen:
            seen.add(article)
            unique_data.append(product)
    
    print(f"После удаления дублей осталось: {len(unique_data)} товаров")
    
    # Подготовка строк для Excel
    rows = []
    
    for product in unique_data:
        article = product.get("article", "")
        category = product.get("category", "")
        cat_from_catalog = product.get("category_name_from_catalog", "")
        url = product.get("product_url", "")
        
        oem_list = product.get("oem", [])
        cross_list = product.get("cross", [])
        
        # Если нет ни OEM, ни CROSS — одна пустая строка
        if not oem_list and not cross_list:
            rows.append({
                "Артикул": article,
                "Название": category,
                "Категория каталога": cat_from_catalog,
                "Бренд OEM": "",
                "Номер OEM": "",
                "Бренд Cross": "",
                "Номер Cross": "",
                "Ссылка": url
            })
        else:
            # Создаём строки для всех комбинаций OEM + CROSS
            max_len = max(len(oem_list), len(cross_list))
            for i in range(max_len):
                row = {
                    "Артикул": article,
                    "Название": category,
                    "Категория каталога": cat_from_catalog,
                    "Бренд OEM": "",
                    "Номер OEM": "",
                    "Бренд Cross": "",
                    "Номер Cross": "",
                    "Ссылка": url
                }
                
                if i < len(oem_list):
                    row["Бренд OEM"] = oem_list[i].get("brand", "")
                    row["Номер OEM"] = oem_list[i].get("number", "")
                
                if i < len(cross_list):
                    row["Бренд Cross"] = cross_list[i].get("brand", "")
                    row["Номер Cross"] = cross_list[i].get("number", "")
                
                rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Упорядочиваем колонки
    columns_order = [
        "Артикул",
        "Название",
        "Категория каталога",
        "Бренд OEM",
        "Номер OEM",
        "Бренд Cross",
        "Номер Cross",
        "Ссылка"
    ]
    df = df[columns_order]
    
    # Сохранение в Excel
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_file = f"Fabio_Airsprings_Products_{timestamp}.xlsx"
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name="Товары", index=False)
        
        # Лист со статистикой
        stats = {
            "Всего уникальных артикулов": len(unique_data),
            "Всего строк в таблице": len(df),
            "Дата выгрузки": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        pd.DataFrame([stats]).to_excel(writer, sheet_name="Статистика", index=False)
    
    print(f"\n✅ Файл успешно сохранён:")
    print(f"   {output_file}")
    print(f"   Уникальных артикулов: {len(unique_data)}")
    print(f"   Строк в таблице: {len(df)}")
    
    return output_file


# ====================== ЗАПУСК ======================
if __name__ == "__main__":
    json_to_excel(
        json_file="all_products_full_data.json",   # ← укажи свой файл
    )

