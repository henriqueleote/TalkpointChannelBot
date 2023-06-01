import time
from bs4 import BeautifulSoup
from selenium import webdriver
import telegram

# URL of the website you want to fetch
URL_ALL = 'https://talk-point.de/search?type=article%2Cpage%2Cproduct&q=&sort=created-descending'
URL_GRADE = 'https://talk-point.de/collections/all?sort=created-descending&pf_t_produktzustand=Zustand_A&pf_t_produktzustand=Zustand_B&pf_t_produktzustand=Zustand_C'
most_recent = None
MOST_RECENT_FILE = "most_recent.txt"
history_product_count = 0
TOKEN = '6201495078:AAGmPD9vEI_dIT1D4uAMbF2_9Rx3dOzc1Bg'
channel_id = "-1001921638321"

"10089055-225"

# Function to get the most recent URL from the file
def get_most_recent():
    try:
        with open(MOST_RECENT_FILE, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        return None

# Function to set the most recent URL in the file
def set_most_recent(value):
    with open(MOST_RECENT_FILE, 'w') as file:
        file.write(value)

# Function to run the WebDriver and retrieve the HTML content of the page
def runWebDriver(url):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=chrome_options)
    # Create the WebDriver instance
    driver.get(url)
    html_content = driver.page_source
    driver.quit()
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup;

# Function to fetch data from the website and send updates to the Telegram channel
def getData(bot):
    print('running...')
    most_recent = get_most_recent()

    # Get internet code
    soup = runWebDriver(URL_GRADE)
    ul_element = soup.select_one('.boost-pfs-filter-products')

    new_products = []

    # Check how many products were added since the last "most_recent" until the newest

    # TODO: If it doesn't exist, just show the newest
    for index, element in enumerate(ul_element):
        if element['data-product-quickshop-url'] == most_recent:
            # new_product_count = index
            break
        new_products.append(element)

    # Find the most recent through the HTML <li> inside the <ul>
    if ul_element:
        li_element = ul_element.find('li')
        if li_element:
            if new_products:
                res = new_products[::-1]  # reversing using list slicing
                for product_li in res:

                    product_item = product_li['data-product-quickshop-url']
                    image = product_li.find('img', 'productitem--image-primary')
                    productID = product_item.split('/')[4]

                    img_src = ''

                    grade = productID[-3:]

                    pre_img_src = image.get('src')
                    if pre_img_src[0] == "/":
                        img_src = pre_img_src[2:]
                    else:
                        img_src = pre_img_src

                    if (grade == "223"):
                        emoji = "\U0001F7E2"
                        condition = "Like new"
                    if (grade == "224"):
                        emoji = "\U0001F7E1"
                        condition = "Very good"
                    if (grade == "225"):
                        emoji = "\U0001F7E0"
                        condition = "Good"

                    blue_circle = "\U0001F535"
                    white_circle = "\u26AA"
                    product_price = product_li.find("span", {"class", "money"}).text
                    product_name = product_li.find("h2", {"class", "productitem--title"}).text
                    title = f'{blue_circle}{white_circle} Talkpoint {white_circle}{blue_circle}\n'
                    message = f'{title}{product_name}\nPrice: {product_price}\nCondition: {condition} {emoji}\nhttps://talk-point.de/products/' + productID
                    if (img_src != ''):
                        bot.send_photo(chat_id=channel_id, photo=img_src, caption=message)
                    else:
                        bot.send_message(chat_id=channel_id, text=message)
                    time.sleep(2)
                set_most_recent(new_products[0]['data-product-quickshop-url'])
                new_products.clear()
                res.clear()
            else:
                print('no product')
    else:
        print('Error: ul_element not found')

bot = telegram.Bot(token=TOKEN)
bot.send_message(chat_id=channel_id, text='Now getting updates from Talkpoint')

while (True):
    getData(bot)
    time.sleep(180)
