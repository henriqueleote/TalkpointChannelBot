import datetime
import json
import re
import time

import schedule as schedule
from bs4 import BeautifulSoup
from selenium import webdriver
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CallbackQueryHandler

# URL of the website you want to fetch
URL_ALL = 'https://talk-point.de/search?type=article%2Cpage%2Cproduct&q=&sort=created-descending'
URL_GRADE = 'https://talk-point.de/collections/all?sort=created-descending&pf_t_produktzustand=Zustand_A&pf_t_produktzustand=Zustand_B&pf_t_produktzustand=Zustand_C'
most_recent = None
MOST_RECENT_FILE = "most_recent.txt"
history_product_count = 0
TOKEN = '6201495078:AAGmPD9vEI_dIT1D4uAMbF2_9Rx3dOzc1Bg'
channel_id = "-1001921638321"
watchlist = {}
DATA_FILE = "watchlist.json"
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

# Loads watchlist from JSON file
def load_watchlist():
    global watchlist
    try:
        with open(DATA_FILE, 'r') as file:
            data = file.read()
            if data:
                watchlist = json.loads(data)
            else:
                watchlist = {}
    except FileNotFoundError:
        watchlist = {}

# Save watchlist to JSON file
def save_watchlist():
    global watchlist

    with open(DATA_FILE, 'w') as file:
        if watchlist:
            json.dump(watchlist, file)
            print("saved to file")
        else:
            file.write('')

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
    return soup


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
                    product_price = product_li.find("span", {"class", "money"}).text
                    product_name = product_li.find("h2", {"class", "productitem--title"}).text
                    sendToChannel(productID, product_name, product_price, image, bot, "")

                    time.sleep(2)
                set_most_recent(new_products[0]['data-product-quickshop-url'])
                new_products.clear()
                res.clear()
            else:
                print('no product')
    else:
        print('Error: ul_element not found')


def sendToChannel(productID, product_name, product_price, image, bot, message):
    img_src = ''

    grade = productID[-3:]

    pre_img_src = image.get('src')
    if pre_img_src[0] == "/":
        img_src = pre_img_src[2:]
    else:
        img_src = pre_img_src

    if (grade == "223"):
        condition_emoji = "\U0001F7E2"
        condition = "Like new"
    if (grade == "224"):
        condition_emoji = "\U0001F7E1"
        condition = "Very good"
    if (grade == "225"):
        condition_emoji = "\U0001F7E0"
        condition = "Good"

    blue_circle = "\U0001F535"
    white_circle = "\u26AA"
    if(message):
        title = f'{blue_circle}{white_circle} Talkpoint {white_circle}{blue_circle}{message}'
    else:
        title = f'{blue_circle}{white_circle} Talkpoint {white_circle}{blue_circle}\n'
    message = f'{title}{product_name}\nPrice: {product_price}\nCondition: {condition} {condition_emoji}\nhttps://talk-point.de/products/' + productID
    if (img_src != ''):

        # Send the photo with the button to the channel
        plus_emoji = '\u2795'
        button_text = f'{plus_emoji} Add to watchlist!'

        # Create the inline keyboard markup
        keyboard = [[InlineKeyboardButton(button_text, callback_data=f'{productID}_{product_price}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        #ORANGE IPHONE CASE WAS GIVING PROBLEMS
        bot.send_photo(chat_id=channel_id, photo=img_src, caption=message, reply_markup=reply_markup)
    else:
        bot.send_message(chat_id=channel_id, text=message)

def addWatchlist(update, context):
    global watchlist
    query = update.callback_query
    callback_data = query.data

    # Extract the product ID and price from the callback data
    product_id, pre_price = callback_data.split('_')

    cleaned_string = pre_price.replace("€", "").replace(",", ".")
    price = float(cleaned_string)

    # Check if the product is already in the watchlist
    if product_id in watchlist:
        watchlist.pop(product_id)
        emoji = '\u2795'
        button_text = f'{emoji} Add to watchlist!'
    else:
        watchlist[product_id] = {
            'productID' : product_id,
            'price' : price
        }
        emoji = '\u2705'
        button_text = f'{emoji} Added to Watchlist'

    query.edit_message_reply_markup(reply_markup=get_updated_markup(product_id, pre_price, button_text))
    save_watchlist()

# Function to get the updated reply markup with the modified button text
def get_updated_markup(product_id, price, button_text):
    callback_data = f"{product_id}_{price}"
    button = InlineKeyboardButton(button_text, callback_data=callback_data)
    reply_markup = InlineKeyboardMarkup([[button]])
    return reply_markup

def checkWatchlist(bot):
    toRemove = []
    load_watchlist()
    print(watchlist)
    bot.send_message(chat_id=channel_id, text='Checking watchlist')
    for key, value in watchlist.items():
        product_id = value["productID"]
        old_price = value["price"]

        soup = runWebDriver(f'https://talk-point.de/products/{product_id}')
        span_element = soup.select_one('div.price--main')
        price_element = span_element.find("span", {"class":"money"}).contents

        image = soup.find('img', 'product-gallery--loaded-image')
        product_name = soup.select_one('h1.product-title').contents[0].replace("\n","").strip()
        new_price = float(price_element[0].replace("\n","").replace(" ","").replace("€","").replace(",","."))

        if(new_price < old_price):
            toRemove.append(product_id)
            graph_emoji = '\U0001f4c9'
            message = f"\n{graph_emoji} Price drop {graph_emoji}\n"
            sendToChannel(product_id, product_name, new_price, image, bot,message)
            time.sleep(2)

    for val in toRemove:
        watchlist.pop(val)
        save_watchlist()

updater = Updater(token=TOKEN)
dispatcher = updater.dispatcher

load_watchlist()
#updater.bot.send_message(chat_id=channel_id, text='Now getting updates from Talkpoint', disable_notification=True)

# Add a callback query handler for button clicks
dispatcher.add_handler(CallbackQueryHandler(addWatchlist))

updater.start_polling()

schedule.every().day.at("12:30").do(lambda: checkWatchlist(updater.bot))

while True:
    schedule.run_pending()
    getData(updater.bot)
    time.sleep(180)

updater.stop()
