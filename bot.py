import time
import pycurl
from io import BytesIO
from bs4 import BeautifulSoup
import telegram
from telegram.error import BadRequest, RetryAfter, TimedOut, NetworkError
import talkpoint_config
import asyncio
import datetime

list = []

# bool to control if messages are sent to telegram or not
sendMessage = True

# Telegram Channel ID
channel_id = talkpoint_config.channel_id

iteration = 0

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
    # Get page source code
    soup = getWebContent(url)

    if soup == 'CRASH':
        return soup

    ul_element = soup.select_one('ul.boost-pfs-filter-products')

    if ul_element:
        for product_li in ul_element.select('.productgrid--item')[::-1]:
            product_item = product_li['data-product-quickshop-url']
            try:
                imagesrc = product_li.select_one('.productitem--image-primary')['src']
            except TypeError:
                print("Image non existing for product")
                imagesrc = 'https://talk-point.de/cdn/shop/t/5/assets/boost-pfs-no-image_512x.gif'

            if imagesrc.startswith("//"):
                productImage = imagesrc[2:]  # Remove the first two characters
            else:
                productImage = imagesrc
            productID = product_item.split('/')[4]
            productPrice = product_li.select_one('span.money').text.strip()
            productName = product_li.select_one('h2.productitem--title').text.strip()

            if (productID not in list):
                list.append(productID)
                print(f'new product -> {productPrice} | {productName}')
                await sendToChannel(productID, productName, productPrice, productImage, "")
    else:
        return


async def sendToChannel(productID, productName, productPrice, productImage, message):
    grade_conditions = {
        "0": "\U0001F7E2 New",
        "223": "\U0001F7E1 Like new",
        "224": "\U0001F7E0 Very good",
        "225": "\U0001F534 Good"
    }

    productImage = 'https://' + productImage.split("?")[0]
    condition = grade_conditions.get(productID.rsplit('-', 1)[-1], "")

    title = f'\U0001F535\u26AA Talkpoint \u26AA\U0001F535{message}\n'
    message = f'{title}{productName}\nPrice: {productPrice}\nCondition: {condition}\nhttps://talk-point.de/products/{productID}'

    if sendMessage and iteration > 0:
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


bot = telegram.Bot(token=talkpoint_config.TOKEN)

# Define the main function
async def main():
    global iteration
    while True:
        print(f'Running talkpoint.de... ({datetime.datetime.now()})')
        result = await getData('https://talk-point.de/collections/unsere-beste-b-ware?sort=created-descending')
        if result == 'CRASH':
            await bot.send_message(chat_id=channel_id, text='TalkPoint crashed due to failed link',
                                   disable_notification=True)
            print("Script didn't load correctly the Talkpoint link")
            return
        print(f'last product -> {list[len(list)-1]}')
        try:
            async with bot:
                await bot.send_message(chat_id=talkpoint_config.status_channel_id,
                                       text=f'Last talk product -> {list[len(list) - 1]}', disable_notification=True)
        except TimedOut as e:
            time.sleep(60)
            async with bot:
                await bot.send_message(chat_id=talkpoint_config.status_channel_id,
                                       text=f'Last talk product -> {list[len(list) - 1]}', disable_notification=True)

        iteration += 1
        time.sleep(180)


# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
