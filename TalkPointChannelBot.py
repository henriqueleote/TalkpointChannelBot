import datetime
import json
import re
import time
import datetime
import schedule as schedule
from bs4 import BeautifulSoup
from selenium import webdriver
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CallbackQueryHandler
import config

# URL of the website you want to fetch
URL_ALL = 'https://talk-point.de/search?type=article%2Cpage%2Cproduct&q=&sort=created-descending'
URL_GRADE = 'https://talk-point.de/collections/all?sort=created-descending&pf_t_produktzustand=Zustand_A&pf_t_produktzustand=Zustand_B&pf_t_produktzustand=Zustand_C'
URL_LAST = 'https://talk-point.de/collections/letzte-chance?sort=created-descending&page=1'
most_recent = None
MOST_RECENT_FILE_GRADE = "most_recent_grade.txt"
MOST_RECENT_FILE_LAST = "most_recent_last.txt"
history_product_count = 0
TOKEN = config.TOKEN
channel_id = config.channel_id
watchlist = {}
DATA_FILE = "watchlist.json"
interval = 180
isChecking = False

# Function to get the most recent URL from the file
def get_most_recent(url):
    if url is URL_GRADE:
        FILE = MOST_RECENT_FILE_GRADE
    else:
        FILE = MOST_RECENT_FILE_LAST
    try:
        with open(FILE, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        return None

# Function to set the most recent URL in the file
def set_most_recent(value, url):
    if url is URL_GRADE:
        FILE = MOST_RECENT_FILE_GRADE
    else:
        FILE = MOST_RECENT_FILE_LAST
    with open(FILE, 'w') as file:
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
            print(f"saved to file at {datetime.datetime.now()}")
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
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()
    return soup


# Function to fetch data from the website and send updates to the Telegram channel
def getData(bot, url):
    print('running...')

    # Get page source code
    soup = runWebDriver(url)
    ul_element = soup.select_one('.boost-pfs-filter-products')

    if ul_element:
        recent = ""
        for i, product_li in enumerate(ul_element, start=1):
            product_item = product_li['data-product-quickshop-url']
            if i == 1:
                recent = product_item
            if product_item == get_most_recent(url) or i == 10:
                break
            imagesrc = product_li.select_one('.productitem--image-primary')['src']
            if imagesrc.startswith("//"):
                image = imagesrc[2:]  # Remove the first two characters
            else: image = imagesrc
            productID = product_item.split('/')[4]
            product_price = product_li.select_one('span.money').text
            product_name = product_li.select_one('h2.productitem--title').text
            sendToChannel(productID, product_name, product_price, image, bot, "")
        set_most_recent(recent, url)
        print("no more products")
    else:
        print('Error: ul_element not found')


def sendToChannel(productID, product_name, product_price, image, bot, message):
    grade_conditions = {
        "0": "\U0001F7E2 New",
        "223": "\U0001F7E1 Like new",
        "224": "\U0001F7E0 Very good",
        "225": "\U0001F534 Good"
    }

    condition = grade_conditions.get(productID.rsplit('-', 1)[-1], "")

    title = f'\U0001F535\u26AA Talkpoint \u26AA\U0001F535{message}\n'
    message = f'{title}{product_name}\nPrice: {product_price}\nCondition: {condition}\nhttps://talk-point.de/products/{productID}'

    # Add the watchlist button to the chat message
    markup = [[InlineKeyboardButton('\u2795 Add to watchlist!', callback_data=f'{productID}_{product_price}')]]
    reply_markup = InlineKeyboardMarkup(markup)

    try:
        bot.send_photo(chat_id=channel_id, photo=image, caption=message, reply_markup=reply_markup)
    except telegram.error.RetryAfter as e:
        time.sleep(e.retry_after)  # Wait for the specified duration
        # Retry after the waiting period
        bot.send_photo(chat_id=channel_id, photo=image, caption=message, reply_markup=reply_markup)


def addWatchlist(update, context):
    global watchlist
    global isChecking
    query = update.callback_query
    callback_data = query.data

    if isChecking is False:
        # Extract the product ID and price from the callback data
        product_id, pre_price = callback_data.split('_')

        # Check if the product is already in the watchlist
        if product_id in watchlist:
            watchlist.pop(product_id)
            button_text = f'\u2795 Add to watchlist!'
        else:
            watchlist[product_id] = {
                'productID' : product_id,
                'price' : float(pre_price.replace("€", "").replace(",", "."))
            }
            button_text = f'\u2705 Added to watchlist!'

        query.edit_message_reply_markup(reply_markup=get_updated_markup(product_id, pre_price + ' €', button_text))
        save_watchlist()
    else:
        print("Can't add to the list because it's checking right now")

# Function to get the updated reply markup with the modified button text
def get_updated_markup(product_id, price, button_text):
    return InlineKeyboardMarkup([[InlineKeyboardButton(button_text, callback_data=f"{product_id}_{price}")]])

def checkWatchlist(bot):
    global isChecking
    isChecking = True
    toRemove = []
    load_watchlist()
    bot.send_message(chat_id=channel_id, text='Checking watchlist', disable_notification=True)
    for key, value in watchlist.items():
        product_id = value["productID"]
        old_price = value["price"]

        soup = runWebDriver(f'https://talk-point.de/products/{product_id}')
        span_element = soup.select_one('div.price--main')
        if span_element:
            price_element = span_element.find("span", {"class":"money"}).contents
            imagesrc = soup.find('img', 'product-gallery--loaded-image').get('src')
            if imagesrc.startswith("//"):
                image = imagesrc[2:]  # Remove the first two characters
            else: image = imagesrc
            product_name = soup.select_one('h1.product-title').contents[0].replace("\n","").strip()
            new_price = float(price_element[0].replace("\n","").replace(" ","").replace("€","").replace(",","."))

            if(new_price < old_price):
                toRemove.append(product_id)
                graph_emoji = '\U0001f4c9'
                dropValue = ((old_price - new_price) / old_price) * 100
                message = f"\n{graph_emoji} Price drop of {dropValue:.1f}% {graph_emoji}"
                sendToChannel(product_id, product_name, new_price, image, bot, message)
        else:
            # Product doesnt exist anymore
            toRemove.append(product_id)
            print("Product removed from watchlist because it was remove from website")

    for val in toRemove:
        watchlist.pop(val)
        save_watchlist()
    bot.send_message(chat_id=channel_id, text='Checking watchlist finished', disable_notification=True)
    isChecking = False


updater = Updater(token=TOKEN)
dispatcher = updater.dispatcher

load_watchlist()

# Add a callback query handler for button clicks
dispatcher.add_handler(CallbackQueryHandler(addWatchlist))

updater.start_polling()

schedule.every().day.at("13:00").do(lambda: checkWatchlist(updater.bot))

while True:
    schedule.run_pending()
    getData(updater.bot, URL_GRADE)
    getData(updater.bot, URL_LAST)
    time.sleep(interval)

updater.stop()
