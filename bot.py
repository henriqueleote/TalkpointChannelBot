import time
import pycurl
from io import BytesIO
from bs4 import BeautifulSoup
import telegram
from telegram.error import BadRequest, RetryAfter, TimedOut, NetworkError
import talkpoint_config
import asyncio

# bool to control if messages are sent to telegram or not
sendMessage = True

# URL of the website you want to fetch
most_recent = None
MOST_RECENT_FILE = "most_recent.txt"
isChecking = False

# Telegram Bot Token
TOKEN = talkpoint_config.TOKEN

# Telegram Channel ID
channel_id = talkpoint_config.channel_id

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
def getWebContent(url):
    curl = pycurl.Curl()
    responseBuffer = BytesIO()

    curl.setopt(curl.URL, url)
    curl.setopt(curl.WRITEDATA, responseBuffer)
    curl.perform()
    response = responseBuffer.getvalue()

    page_source = response.decode('utf-8')
    curl.close()
    responseBuffer.close()

    # Parse the page source with BeautifulSoup
    soup = BeautifulSoup(page_source, "html.parser")

    return soup

# Function to fetch data from the website and send updates to the Telegram channel
async def getData(url):
    print('Running talkpoint.de...')

    # Get page source code
    soup = getWebContent(url)

    if soup == 'CRASH':
        return soup

    ul_element = soup.select_one('ul.boost-pfs-filter-products')

    if ul_element:
        recent = ""

        for i, product_li in enumerate(ul_element.select('.productgrid--item'), start=1):
            product_item = product_li['data-product-quickshop-url']
            if i == 1:
                recent = product_item
            if product_item == get_most_recent() or i == 10:
                break
            imagesrc = product_li.select_one('.productitem--image-primary')['src']
            if imagesrc.startswith("//"):
                image = imagesrc[2:]  # Remove the first two characters
            else: image = imagesrc
            productID = product_item.split('/')[4]
            product_price = product_li.select_one('span.money').text.strip()
            product_name = product_li.select_one('h2.productitem--title').text.strip()
            await sendToChannel(productID, product_name, product_price, image, "")
        set_most_recent(recent)
        print("no more products")
    else:
        return


async def sendToChannel(productID, product_name, product_price, productImage, message):
    grade_conditions = {
        "0": "\U0001F7E2 New",
        "223": "\U0001F7E1 Like new",
        "224": "\U0001F7E0 Very good",
        "225": "\U0001F534 Good"
    }

    condition = grade_conditions.get(productID.rsplit('-', 1)[-1], "")

    title = f'\U0001F535\u26AA Talkpoint \u26AA\U0001F535{message}\n'
    message = f'{title}{product_name}\nPrice: {product_price}\nCondition: {condition}\nhttps://talk-point.de/products/{productID}'

    if(sendMessage):
        try:
            async with bot:
                await bot.send_photo(chat_id=channel_id, photo=productImage, caption=message)
        except BadRequest as e:
            async with bot:
                await bot.send_photo(chat_id=channel_id, photo=productImage, caption=message)
        except RetryAfter as e:
            time.sleep(e.retry_after)
            async with bot:
                await bot.send_photo(chat_id=channel_id, photo=productImage, caption=message)
        except TimedOut as e:
            time.sleep(60)
            async with bot:
                await bot.send_photo(chat_id=channel_id, photo=productImage, caption=message)
        except NetworkError as e:
            time.sleep(30)
            async with bot:
                await bot.send_photo(chat_id=channel_id, photo=productImage, caption=message)
        except Exception as e:
            time.sleep(1)
            async with bot:
                await bot.send_photo(chat_id=channel_id, photo=productImage, caption=message)
    else:
        print(message)


bot = telegram.Bot(token=talkpoint_config.TOKEN)

# Define the main function
async def main():
    while True:
        result = await getData('https://talk-point.de/collections/unsere-beste-b-ware?sort=created-descending')
        if result == 'CRASH':
            await bot.send_message(chat_id=channel_id, text='TalkPoint crashed due to failed link', disable_notification=True)
            print("Script didn't load correctly the Talkpoint link")
            return
        time.sleep(180)


# Run the main function
if __name__ == "__main__":
    asyncio.run(main())