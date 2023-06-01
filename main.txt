import json
from bs4 import BeautifulSoup
from talkpoint_channel_bot.ext import Updater, CommandHandler, CallbackContext
from talkpoint_channel_bot import Update, Chat, Message
from selenium import webdriver
from datetime import datetime
import os, psutil


# Local storage files
SETTINGS_FILE = 'user_settings.json'

# Website links
URL_GRADE = 'https://talk-point.de/search?type=article%2Cpage%2Cproduct&q=&sort=created-descending&pf_t_produktzustand=Zustand_C&pf_t_produktzustand=Zustand_B&pf_t_produktzustand=Zustand_A'
URL_ALL = 'https://talk-point.de/search?type=article%2Cpage%2Cproduct&q=&sort=created-descending'
DEFAULT_INTERVAL = 1800

# Telegram bot token
TOKEN = '5849084397:AAGWlLjZIdO3Ize5Myl_gG5k7N3FV0PURmM'

# Global variables
user_settings = {}

# Load user status from the JSON file
def load_settings():
    global user_settings
    try:
        with open(SETTINGS_FILE, 'r') as file:
            data = file.read()
            if data:
                user_settings = json.loads(data)
            else:
                user_settings = {}
    except FileNotFoundError:
        user_settings = {}


# Save user status to the JSON file
def save_settings():
    with open(SETTINGS_FILE, 'w') as file:
        if user_settings:
            json.dump(user_settings, file)
        else:
            file.write('')


# Handle the /help command
def help(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    context.bot.send_message(chat_id=chat_id, text='Welcome!\nUse /interval <seconds> to set the interval.\nUse /run to start afeter setting an interval.\nUser /stop to stop updates.')


# Handle the /status command
def check_status(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    if str(chat_id) in user_settings:
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

        # check if user has username
        if update.effective_chat.username is not None:
            print(update.effective_chat.username + ' checked status at ' + dt_string)
        else:
            print(str(chat_id) + '  checked status at  ' + dt_string)

        string = ""

        if (user_settings[str(chat_id)].get('status') == "running"):
            if user_settings[str(chat_id)].get("link") == URL_ALL:
                string = "for all products."
            if user_settings[str(chat_id)].get("link") == URL_GRADE:
                string = "for all Grade A/B/C products."
            interval = user_settings[str(chat_id)].get("interval")
            if interval % 60 == 0:
                message = f'Updates are currently running every {interval // 60} minute(s) {string}'
            else:
                message = f'Updates are currently running every {interval} seconds {string}'
        else:
            message = "Updates are currently stopped."

        context.bot.send_message(chat_id=chat_id, text=message)

# Handle the /interval command
def set_interval(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    try:
        interval = int(context.args[0])
        if interval <= 0:
            raise ValueError()

        # Check if the user already has an interval set
        if str(chat_id) in user_settings:
            # Remove the previous job
            job = context.job_queue.get_jobs_by_name(str(chat_id))
            if job:
                job[0].schedule_removal()
                user_settings[str(chat_id)]["status"] = "stopped"


        # Check if a key exists in the dictionary
        if not str(chat_id) in user_settings:
            user_settings[str(chat_id)] = {
                "interval": interval,
                "link": URL_ALL,
                "most_recent": "",
                "status": "stopped"
            }

        user_settings[str(chat_id)]["interval"] = interval
        save_settings()

        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

        # check if user has username
        if update.effective_chat.username is not None:
            print(update.effective_chat.username + ' set a new interval at ' + dt_string)
        else:
            print(str(chat_id) + '  set a new interval at ' + dt_string)

        run(update, context)

    except (IndexError, ValueError):
        context.bot.send_message(chat_id=chat_id, text='Wrong instruction, please write /interval <seconds>')

# Handle the /grade & /allproducts command
#link is not changing
def set_link(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message = ''
    if update.effective_message.text == '/allproducts' or update.effective_message.text == '/grade':
        if update.effective_message.text == '/allproducts':
            link = URL_ALL
            message = f"Now getting updates from all products"
        else:
            link = URL_GRADE
            message = f"Now getting updates from Grade A/B/C products"

        # Check if a key exists in the dictionary
        if not str(chat_id) in user_settings:
            user_settings[str(chat_id)] = {
               "interval": DEFAULT_INTERVAL,
               "link": URL_ALL,
               "most_recent": "",
               "status": "stopped"
            }

        user_settings[str(chat_id)]["link"] = link
        save_settings()
        context.bot.send_message(chat_id=chat_id, text=message)

        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

        # check if user has username
        if update.effective_chat.username is not None:
            print(update.effective_chat.username + ' set a new link at ' + dt_string)
        else:
            print(str(chat_id) + '  set a new link at ' + dt_string)
    else:
        context.bot.send_message(chat_id=chat_id, text='Wrong instruction')


# Loads the browser and gets the most recent product
def online_search(chat_id):
    link = user_settings[str(chat_id)].get("link")
    most_recent = user_settings[str(chat_id)].get("most_recent")
    new_product_count = -1
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=chrome_options)

    # Create the WebDriver instance
    driver.get(link)
    #driver.implicitly_wait(1)  # Wait up to 2 seconds for elements to appear

    html_content = driver.page_source
    driver.quit()

    soup = BeautifulSoup(html_content, 'html.parser')
    ul_element = soup.select_one('.boost-pfs-filter-products')

    # checks how many products were added since the last "most_recent" until the newest
    for index, element in enumerate(ul_element):
        if element['data-product-quickshop-url'] == most_recent:
            new_product_count = index
            break

    # find the most_recent through the HTML <li> inside the <ul>
    if ul_element:
        li_element = ul_element.find('li')
        if li_element:
            product = li_element['data-product-quickshop-url']
            product_price = li_element.find("span", {"class", "money"}).text
            product_name = li_element.find("h2", {"class", "productitem--title"}).text
            now = datetime.now()
            dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
            if product != most_recent:

                # Product data
                most_recent = product
                productID = most_recent.split('/')[4]
                user_settings[str(chat_id)]["most_recent"] = most_recent
                save_settings()

                # returns a message with the new product
                if new_product_count == 1 or new_product_count == -1:
                    message = f'{product_name} -> {product_price}\nhttps://talk-point.de/products/' + productID
                else:
                    message = f'{product_name} -> {product_price}\nhttps://talk-point.de/products/{productID}\nNovos produtos: {new_product_count}'
                return message
            else:
                print(f"{chat_id} -> no product | {dt_string}")
    else:
        print('Error: ul_element not found')

# Handle the /stop command
def stop(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    if str(chat_id) in user_settings:
        if user_settings[str(chat_id)].get("status") == "running":

            # Remove job
            job = context.job_queue.get_jobs_by_name(str(chat_id))
            if job:
                job[0].schedule_removal()

            user_settings[str(chat_id)]["status"] = "stopped"
            save_settings()
            context.bot.send_message(chat_id=chat_id,text='Updates have stopped.\nUse /run to start getting updates')
            now = datetime.now()
            dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

            # check if user has username
            if update.effective_chat.username is not None:
                print(update.effective_chat.username + ' stopped the updates at ' + dt_string)
            else:
                print(str(chat_id) + ' stopped the updates at ' + dt_string)
        else:
            context.bot.send_message(chat_id=chat_id, text='Updates were already stopped.')
    else:
        context.bot.send_message(chat_id=chat_id, text='No updates were found for this user')




# Handle the data function to be executed with the specified interval
def run(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    # Check if a key exists in the dictionary
    if not str(chat_id) in user_settings:
        user_settings[str(chat_id)] = {
            "interval": DEFAULT_INTERVAL,
            "link": URL_ALL,
            "most_recent": "",
            "status" : "stopped"
        }

    if user_settings[str(chat_id)].get("interval") is None or user_settings[str(chat_id)].get("interval") == "" or user_settings[str(chat_id)].get("interval") == "0"  or user_settings[str(chat_id)].get("interval") == 0:
        user_settings[str(chat_id)]["interval"] = DEFAULT_INTERVAL
        context.bot.send_message(chat_id=chat_id, text='Default interval of 30 minutes was set. /interval <seconds> to change.')

    if user_settings[str(chat_id)].get("link") is None or user_settings[str(chat_id)].get("link") == "":
        user_settings[str(chat_id)]["link"] = URL_ALL
        context.bot.send_message(chat_id=chat_id, text='Now getting updates from all products. \grade to change.')

    if user_settings[str(chat_id)].get("status") is None or user_settings[str(chat_id)].get("status") == "":
        user_settings[str(chat_id)]["status"] = "running"

    save_settings()

    if user_settings[str(chat_id)].get("status") == "stopped":
        interval = user_settings[str(chat_id)].get("interval")
        if interval % 60 == 0:
            context.bot.send_message(chat_id=chat_id, text=f'Updates have started every {interval // 60} minute(s).')
        else:
            context.bot.send_message(chat_id=chat_id, text=f'Updates have started every {interval} seconds.')

        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

        #check if user has username
        if update.effective_chat.username is not None:
            print(update.effective_chat.username + ' joined the updates at ' + dt_string)
        else:
            print(str(chat_id) + ' joined the updates at ' + dt_string)
        user_settings[str(chat_id)]["status"] = "running"
        save_settings()
        context.job_queue.run_repeating(notify, interval, context=(chat_id), name=str(chat_id))
    else:
        context.bot.send_message(chat_id=chat_id, text='Updates were already running.')

# Notifies the user with data from the function online_search
def notify(context: CallbackContext):
    chat_id = context.job.context
    message = online_search(chat_id)
    # if there's a message, sends to the user
    if message:
        context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')


# Main
def main():
    print('running!')

    # Load user intervals from the JSON file on bot startup
    load_settings()

    for user_id, settings in user_settings.items():
        settings["status"] = "stopped"

    save_settings()

    # Initialize the bot
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Register bot command handlers
    dispatcher.add_handler(CommandHandler('help', help))
    dispatcher.add_handler(CommandHandler('stop', stop))
    dispatcher.add_handler(CommandHandler('interval', set_interval))
    dispatcher.add_handler(CommandHandler('grade', set_link))
    dispatcher.add_handler(CommandHandler('allproducts', set_link))
    dispatcher.add_handler(CommandHandler('run', run))
    dispatcher.add_handler(CommandHandler('status', check_status))

    # Start the bot
    updater.start_polling()

    # Send a message to all users
    for chat_id in user_settings.keys():
        updater.bot.send_message(chat_id=chat_id, text='The bot has restarted.\nPlease /run to continue getting updates')

    print(psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2)

    updater.idle()

if __name__ == '__main__':
    main()