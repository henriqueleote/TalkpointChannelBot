import time
from bs4 import BeautifulSoup
from selenium import webdriver
import telegram
import re

# URL of the website you want to fetch
URL_ALL = 'https://talk-point.de/search?type=article%2Cpage%2Cproduct&q=&sort=created-descending'
URL_GRADE = 'https://talk-point.de/collections/all?sort=created-descending&pf_t_produktzustand=Zustand_A&pf_t_produktzustand=Zustand_B&pf_t_produktzustand=Zustand_C'
most_recent = None
MOST_RECENT_FILE = "most_recent.txt"
history_product_count = 0
TOKEN = '6201495078:AAGmPD9vEI_dIT1D4uAMbF2_9Rx3dOzc1Bg'
channel_id = "-1001921638321"

"10089055-225"

def get_most_recent():
    try:
        with open(MOST_RECENT_FILE, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        return None

def set_most_recent(value):
    with open(MOST_RECENT_FILE, 'w') as file:
        file.write(value)

def getData():
    most_recent = get_most_recent()
    new_product_count = -1
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=chrome_options)
    # Create the WebDriver instance
    driver.get(URL_GRADE)
    html_content = driver.page_source
    driver.quit()

    soup = BeautifulSoup(html_content, 'html.parser')
    ul_element = soup.select_one('.boost-pfs-filter-products')

    new_products = []

    # checks how many products were added since the last "most_recent" until the newest
    for index, element in enumerate(ul_element):
        if element['data-product-quickshop-url'] == most_recent:
            #new_product_count = index
            break
        new_products.append(element)

    # find the most_recent through the HTML <li> inside the <ul>
    if ul_element:
        li_element = ul_element.find('li')
        if li_element:
            bot = telegram.Bot(token=TOKEN)
            if new_products:
                res = new_products[::-1]  # reversing using list slicing
                for li_element in res:

                    #Gets product grade state
                    #element_html = str(li_element)
                    script = '''
                    var style = getComputedStyle(document.querySelector('.product-condition-scale-overlay > div:nth-child(3)'), '::before');
                    return style.getPropertyValue('content') + "hello";
                    '''

                    #pre_grade_state = driver.execute_script(script, element_html)
                    grade_state = ''#pre_grade_state.strip('"')
                    emoji = ''
                    condition = ''

                    #print(grade_state)

                    if(grade_state == "sehr gut"):
                        emoji = '\U0001F7E0'
                        condition = 'Very good'
                    if (grade_state == "gut"):
                        emoji = '\U0001F7E1'
                        condition = 'Good'
                    if (grade_state == "wie neu"):
                        emoji = '\U0001F7E2'
                        condition = 'Like new'

                    product = li_element['data-product-quickshop-url']
                    product_price = li_element.find("span", {"class", "money"}).text
                    product_name = li_element.find("h2", {"class", "productitem--title"}).text
                    productID = product.split('/')[4]
                    message = f'{product_name} -> {product_price}\nhttps://talk-point.de/products/' + productID
                    print(message)
                    print(product)
                    bot.send_message(chat_id=channel_id, text=message)
                    time.sleep(3)
                set_most_recent(new_products[0]['data-product-quickshop-url'])
                new_products.clear()
                res.clear()
            else:
                print('no product')
    else:
        print('Error: ul_element not found')

    #driver.quit()

while (True):
    getData()
    time.sleep(180)