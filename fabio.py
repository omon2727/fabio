import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import re
import time

"""
Логика обхода сайта по категориям и парсинг данных на целевых страницах (сатраницы-карточки товаров)
"""


def request_get(url, session, params=None):

    """Посылает запрос, получает ответ
    url - строка, ссылка на сайт
    session - объект сессии. должен быть создан заранее и передан в функцию
    params - дополнительная cтрока для url, какие то параметры, например пагинация
    """
    if params:
        url = url + params
    response = session.get(url)

    if response.status_code != 200:
        raise ValueError(f"{url} код упал, стутус код не 200")

    return response.text





def get_categories(url, session):
    """Собирает категории с главной страницы продуктов"""
    html = request_get(url, session)
    soup = BeautifulSoup(html, 'html.parser')
    
    result = []
    
    # Основной контейнер
    product_group = soup.find('div', class_='productListing')
    if not product_group:
        product_group = soup.find('div', class_='productGroup')  # на всякий случай
    
    if product_group:
        items = product_group.find_all('div', class_='item')
        
        for item in items:
            a_tag = item.find('a')
            if not a_tag:
                continue
                
            try:
                href = a_tag.get('href')
                # Приводим к полному URL
                if href.startswith('/'):
                    category_url = 'https://fabioairsprings.com' + href
                else:
                    category_url = href
                    
                # Название категории из <h2>
                h2 = a_tag.find('h2')
                category_name = h2.text.strip() if h2 else ""
                
                result.append({
                    "category_name": category_name,
                    "category_url": category_url
                })
            except Exception as e:
                print(f"Ошибка при парсинге категории: {e}")
                
    return result

def collect_urls_from_catalog_page_selenium(category_url, timeout=60):
    """Супер-агрессивный динамический скроллинг для 200-300+ товаров"""
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1200")
    options.add_argument(f"user-agent={UserAgent().random}")
    
    driver = webdriver.Chrome(options=options)
    
    try:
        print(f"Загружаю большую категорию: {category_url}")
        driver.get(category_url)
        time.sleep(6)   # первая загрузка
        
        print("Запускаем усиленный динамический скроллинг...")
        
        last_count = 0
        no_change_counter = 0
        scroll_count = 0
        
        while no_change_counter < 5:   # 5 раз без роста = остановка
            scroll_count += 1
            
            # Скроллим до самого низа
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3.0)
            
            # Дополнительные манипуляции для триггера подгрузки
            if scroll_count % 2 == 0:
                driver.execute_script("window.scrollBy(0, -1200);")
                time.sleep(1.5)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2.5)
            
            # Ещё один способ — скролл по одному элементу
            try:
                items = driver.find_elements(By.CSS_SELECTOR, "div.item")
                if items:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", items[-1])
                    time.sleep(1.8)
            except:
                pass
            
            current_count = len(driver.find_elements(By.CSS_SELECTOR, "div.item a[href*='/product/']"))
            
            print(f"  Скролл {scroll_count:2d} → товаров: {current_count}")
            
            if current_count > last_count:
                no_change_counter = 0
            else:
                no_change_counter += 1
                
            last_count = current_count
            
            # Защита
            if scroll_count > 50:
                print("   → Достигнут максимум скроллов")
                break
        
        # Финальный сбор
        links = driver.find_elements(By.CSS_SELECTOR, "div.item a[href*='/product/']")
        
        product_urls = []
        seen = set()
        for a in links:
            href = a.get_attribute('href')
            if href:
                if href.startswith('/'):
                    href = 'https://fabioairsprings.com' + href
                if href not in seen:
                    seen.add(href)
                    product_urls.append(href)
        
        print(f"\n✅ ИТОГО собрано товаров: {len(product_urls)}")
        print(f"   Первые 5: {product_urls[:5]}")
        print(f"   Последние 5: {product_urls[-5:]}")
        
        return product_urls
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return []
    finally:
        driver.quit()



def parse_product_page(html):
    """Парсит данные с страницы товара"""
    soup = BeautifulSoup(html, 'html.parser')
    
    product_data = {
        "article": "",
        "category": "",
        "cross": []   # список словарей: [{"brand": "...", "number": "..."}]
    }
    
    # === 1. Артикул (34941-10CPL) ===
    article_tag = soup.find('p', style=re.compile(r'font-size:30px', re.I))
    if article_tag:
        product_data["article"] = article_tag.get_text(strip=True)
    
    # Альтернативный поиск артикула
    if not product_data["article"]:
        h1 = soup.find('h1')
        if h1 and h1.previous_sibling:
            prev = h1.previous_sibling
            if isinstance(prev, str):
                product_data["article"] = prev.strip()
            else:
                product_data["article"] = prev.get_text(strip=True)
    
    # === 2. Категория продукта ===
    h1 = soup.find('h1')
    if h1:
        product_data["category"] = h1.get_text(strip=True)
    
    # === 3. Таблица CROSS ===
    cross_table = None
    tables = soup.find_all('table')
    
    for table in tables:
        thead = table.find('thead')
        if thead and 'CROSS' in thead.get_text():
            cross_table = table
            break
    
    if cross_table:
        rows = cross_table.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            if len(tds) >= 2:
                brand = tds[0].get_text(strip=True)
                number = tds[1].get_text(strip=True)
                
                # Пропускаем заголовок таблицы
                if brand.lower() in ['бренд', 'brand']:
                    continue
                    
                if brand and number:
                    product_data["cross"].append({
                        "brand": brand,
                        "number": number
                    })
    
    return product_data

def get_product_data_selenium(driver, product_url):
    """Получает данные товара через Selenium"""
    try:
        driver.get(product_url)
        time.sleep(3.5)  # даём время на загрузку
        
        html = driver.page_source
        data = parse_product_page(html)
        
        print(f"✓ {data['article']} | {data['category']} | {len(data['cross'])} cross")
        return data
        
    except Exception as e:
        print(f"Ошибка при парсинге {product_url}: {e}")
        return None



def parse_product_page(html, product_url=""):
    """Парсит страницу товара: article, category, OEM, CROSS и доп. данные"""
    soup = BeautifulSoup(html, 'html.parser')
    
    data = {
        "article": "",
        "category": "",
        "oem": [],           # Новый список для OEM
        "cross": [],         # CROSS (как было)
        "product_url": product_url,
        "category_name_from_catalog": "",
        "weight": "",
        "pallet_size": "",
        "pallet_qty": "",
        "title": ""          # Полное название из h1
    }
    
    # === 1. Артикул ===
    article_tag = soup.find('p', style=re.compile(r'font-size:30px', re.I))
    if article_tag:
        data["article"] = article_tag.get_text(strip=True)
    
    # Запасной вариант поиска артикула
    if not data["article"]:
        article_tag = soup.find('p', string=re.compile(r'\d{4,5}-\d{2,}', re.I))
        if article_tag:
            data["article"] = article_tag.get_text(strip=True)

    # === 2. Название товара (h1) ===
    h1 = soup.find('h1')
    if h1:
        data["category"] = h1.get_text(strip=True)   # или title
        data["title"] = h1.get_text(strip=True)

    # === 3. Парсинг таблиц OEM и CROSS ===
    tables = soup.find_all('table')
    
    for table in tables:
        thead = table.find('thead')
        if not thead:
            continue
            
        header_text = thead.get_text(strip=True).upper()
        
        # Определяем тип таблицы
        if 'OEM' in header_text:
            target_list = data["oem"]
        elif 'CROSS' in header_text:
            target_list = data["cross"]
        else:
            continue
        
        rows = table.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            if len(tds) >= 2:
                brand = tds[0].get_text(strip=True)
                number = tds[1].get_text(strip=True)
                
                # Пропускаем заголовки строк
                if brand.lower() in ['бренд', 'brand', 'нет.', 'no.']:
                    continue
                    
                if brand and number:
                    target_list.append({
                        "brand": brand,
                        "number": number
                    })
    
    
    return data



def main():
    """Полная обработка ВСЕХ категорий"""
    
    ua = UserAgent()
    headers = {
        'User-Agent': ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    session = requests.Session()
    session.headers.update(headers)

    # Получаем список категорий
    root_catalog_url = "https://fabioairsprings.com/ru/produkty"
    categories_list = get_categories(root_catalog_url, session)

    print(f"Найдено категорий: {len(categories_list)}\n")
    for cat in categories_list:
        print(cat['category_name'], "->", cat['category_url'])
    
    print(f"\n{'='*90}")
    print("НАЧИНАЕМ ПОЛНЫЙ ПАРСИНГ ВСЕГО САЙТА")
    print(f"{'='*90}\n")

    all_products_data = []
    total_products = 0

    # Настраиваем один Selenium driver на всю работу
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"user-agent={UserAgent().random}")
    
    driver = webdriver.Chrome(options=options)

    try:
        for cat_idx, cat in enumerate(categories_list, 1):
            print(f"\n[{cat_idx}/{len(categories_list)}] Обрабатываю категорию: {cat['category_name']}")
            
            # 1. Собираем ссылки на товары
            product_urls = collect_urls_from_catalog_page_selenium(cat['category_url'])
            
            print(f"   → Найдено товаров: {len(product_urls)}")
            
            if not product_urls:
                continue

            # 2. Парсим каждый товар
            category_products = 0
            for i, url in enumerate(product_urls, 1):
                print(f"   [{i:3d}/{len(product_urls)}] Парсим → {url.split('/')[-1]}", end=" ")
                
                try:
                    driver.get(url)
                    time.sleep(3.2)  # оптимальная пауза
                    
                    html = driver.page_source
                    product_data = parse_product_page(html)
                    
                    if product_data and product_data["article"]:
                        product_data["product_url"] = url
                        product_data["category_name_from_catalog"] = cat['category_name']
                        all_products_data.append(product_data)
                        
                        cross_count = len(product_data['cross'])
                        print(f"✓ {product_data['article']} | CROSS: {cross_count}")
                        category_products += 1
                        total_products += 1
                    else:
                        print("— не удалось распарсить")
                        
                except Exception as e:
                    print(f"✗ Ошибка: {e}")
                
                time.sleep(1.1)  # пауза между товарами

            print(f"   Готово по категории! Собрано: {category_products} товаров")

            # Промежуточное сохранение после каждой категории
            with open('products_backup.json', 'w', encoding='utf-8') as f:
                json.dump(all_products_data, f, ensure_ascii=False, indent=2)

    finally:
        driver.quit()

    # Финальное сохранение
    final_file = "all_products_full_data.json"
    with open(final_file, 'w', encoding='utf-8') as f:
        json.dump(all_products_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*90}")
    print("ПАРСИНГ УСПЕШНО ЗАВЕРШЁН!")
    print(f"Всего собрано товаров: {total_products}")
    print(f"Данные сохранены в: {final_file}")
    print(f"Также есть промежуточный бэкап: products_backup.json")
    print(f"{'='*90}")


if __name__ == "__main__":
      main()



      