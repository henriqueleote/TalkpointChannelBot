import json
import time
import datetime
#import schedule


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common import TimeoutException
from bs4 import BeautifulSoup

import telegram
from telegram import *
from telegram.ext import *

import config
import asyncio

# URL of the website you want to fetch
most_recent = None
MOST_RECENT_FILE = "most_recent.txt"
watchlist = {}
DATA_FILE = "watchlist.json"
isChecking = False

# Telegram Bot Token
TOKEN = config.TOKEN

# Telegram Channel ID
channel_id = config.channel_id

# Function to get the most recent URL from the file
def get_most_recent(url):
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
            print(f"saved to file at {datetime.datetime.now()}")
        else:
            file.write('')

# Function to run the WebDriver and retrieve the HTML content of the page
def runWebDriver(url, waitSelector):

    options = webdriver.ChromeOptions()
    options.add_argument("--log-level=3")  # removes chrome logs from cmd bash
    options.add_argument("--headless")  # NO GUI browser
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    s = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=s, options=options)

    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )

    # Create the WebDriver instance
    driver.get(url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, waitSelector))
        )
    except TimeoutException:
        return "CRASH"

    # Parse the page source with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    return soup


# Function to fetch data from the website and send updates to the Telegram channel
async def getData(bot, url):
    print('running...')

    # Get page source code
    soup = runWebDriver(url, '.boost-pfs-filter-products')

    if soup == 'CRASH':
        return soup

    ul_element = soup.select_one('ul.boost-pfs-filter-products')

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
            await sendToChannel(productID, product_name, product_price, image, bot, "")
        set_most_recent(recent)
        print("no more products")
    else:
        return

async def sendToChannel(productID, product_name, product_price, image, bot, message):
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
    reply_markup = None # remove once working

    async with bot:
        try:
            await bot.send_photo(chat_id=channel_id, photo=image, caption=message, reply_markup=reply_markup,  disable_notification=True)
        except telegram.error.RetryAfter as e:
            time.sleep(e.retry_after)  # Wait for the specified duration
            # Retry after the waiting period
            await bot.send_photo(chat_id=channel_id, photo=image, caption=message, reply_markup=reply_markup,  disable_notification=True)

def addWatchlist(update, context):
    print('adding')
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
                'productID': product_id,
                'price': float(pre_price.replace("€", "").replace(",", "."))
            }
            button_text = f'\u2705 Added to watchlist!'

        query.edit_message_reply_markup(reply_markup=get_updated_markup(product_id, pre_price + ' €', button_text))
        save_watchlist()
    else:
        print("Can't add to the list because it's checking right now")

# Function to get the updated reply markup with the modified button text
def get_updated_markup(product_id, price, button_text):
    return InlineKeyboardMarkup([[InlineKeyboardButton(button_text, callback_data=f"{product_id}_{price}")]])

async def checkWatchlist(bot):
    global isChecking
    isChecking = True
    toRemove = []
    load_watchlist()
    bot.send_message(chat_id=channel_id, text='Checking watchlist', disable_notification=True)
    for key, value in watchlist.items():
        product_id = value["productID"]
        old_price = value["price"]

        soup = runWebDriver(f'https://talk-point.de/products/{product_id}', '.product--outer')

        if soup == 'CRASH':
            return

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
    #bot.send_message(chat_id=channel_id, text='Checking watchlist finished', disable_notification=True)
    isChecking = False

# Define the main function
async def main():

    application = Application.builder().token(config.TOKEN).build()

    #await application.bot.send_message(chat_id = channel_id, text='Talk point started', disable_notification=True)
    while True:
        #schedule.run_pending()
        result = await getData(application.bot, 'https://talk-point.de/collections/unsere-beste-b-ware?sort=created-descending')
        if result == 'CRASH':
            await application.bot.send_message(chat_id=channel_id, text='TalkPoint crashed due to failed link', disable_notification=True)
            print("Script didn't load correctly the Talkpoint link")
            return
        time.sleep(180)

    await application.shutdown()

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())