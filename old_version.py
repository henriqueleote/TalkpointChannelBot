from requests_html import HTMLSession
import time
import requests
import urllib.parse

# URL of the website you want to fetch
url_grade = 'https://talk-point.de/search?type=article%2Cpage%2Cproduct&q=&sort=created-descending&pf_t_produktzustand=Zustand_C&pf_t_produktzustand=Zustand_B&pf_t_produktzustand=Zustand_A'
url_novo= 'https://talk-point.de/search?type=article%2Cpage%2Cproduct&q=&sort=created-descending'
most_recent = None
history_product_count = 0
TOKEN = '5849084397:AAHOJwEIUNxXml143UY9dHnAd4wdLYPvMUg'
chat_id_henrique = "962245992"
chat_id_fred = "760157734"

MOST_RECENT_FILE = 'most_recent.txt'

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
    most_recent = get_most_recent()  # Read the most_recent value from the file
    session = HTMLSession()
    response = session.get(url_novo)
    encoded_url = urllib.parse.quote(url_novo, safe='')
    new_product_count = -1
    response.html.render(wait=0)
    ul_element = response.html.find('.boost-pfs-filter-products', first=True)
    li_elements = ul_element.find('li')  # Find all the <li> elements inside the <ul>

    # Gets position of the last knowned product to know how many new products are there
    for index, element in enumerate(li_elements):
        if element.attrs.get('data-product-quickshop-url') == most_recent:
            new_product_count = index
            break

    if ul_element:
        first_child = ul_element.find('li', first=True)
        if first_child:
            product = first_child.attrs.get('data-product-quickshop-url')
            if product != most_recent:

                # Product data
                most_recent = product
                productID = most_recent.split('/')[4]

                # Send data to user
                if new_product_count == 1:
                    message = 'Novo produto no site!\nhttps://talk-point.de/products/' + productID
                else:
                    message = 'Novo produto no site!\nhttps://talk-point.de/products/' + productID + '\nNovos produtos: ' + str(new_product_count) + f'\nVerifica todos os novos produtos [aqui]({encoded_url})'

                send_msg_henrique = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id_henrique}&text={message}&parse_mode=Markdown"
                send_msg_fred = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id_fred}&text={message}&parse_mode=Markdown"
                print(requests.get(send_msg_henrique).json())  # This sends the message
                print(requests.get(send_msg_fred).json())  # This sends the message

                set_most_recent(most_recent)  # Write the updated most_recent value to the file
            else:
                print('no new product')

    session.close()

while (True):
    getData()
    time.sleep(180)