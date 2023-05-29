import json
from bs4 import BeautifulSoup
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import Update
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

# Local storage files
INTERVALS_FILE = 'intervals.json'
LINKS_FILE = 'links.json'
STATUS_FILE = 'status.json'
MOST_RECENT_FILE = 'most_recent.txt'

# Website links
URL_GRADE = 'https://talk-point.de/search?type=article%2Cpage%2Cproduct&q=&sort=created-descending&pf_t_produktzustand=Zustand_C&pf_t_produktzustand=Zustand_B&pf_t_produktzustand=Zustand_A'
URL_ALL = 'https://talk-point.de/search?type=article%2Cpage%2Cproduct&q=&sort=created-descending'

# Telegram bot token
TOKEN = '5849084397:AAHOJwEIUNxXml143UY9dHnAd4wdLYPvMUg'

# Global variables
user_intervals = {}
user_links = {}
user_status = {}

# Gets the most recent product from file
def get_most_recent():
    try:
        with open(MOST_RECENT_FILE, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        return None

# Set the most recent product in file
def set_most_recent(value):
    with open(MOST_RECENT_FILE, 'w') as file:
        file.write(value)

# Load user intervals from the JSON file
def load_intervals():
    global user_intervals
    try:
        with open(INTERVALS_FILE, 'r') as file:
            data = file.read()
            if data:
                user_intervals = json.loads(data)
            else:
                user_intervals = {}
    except FileNotFoundError:
        user_intervals = {}

# Load user links from the JSON file
def load_links():
    global user_links
    try:
        with open(LINKS_FILE, 'r') as file:
            data = file.read()
            if data:
                user_links = json.loads(data)
            else:
                user_links = {}
    except FileNotFoundError:
        user_links = {}

# Load user status from the JSON file
def load_status():
    global user_status
    try:
        with open(STATUS_FILE, 'r') as file:
            data = file.read()
            if data:
                user_status = json.loads(data)
            else:
                user_status = {}
    except FileNotFoundError:
        user_status = {}


# Save user intervals to the JSON file
def save_intervals():
    with open(INTERVALS_FILE, 'w') as file:
        if user_intervals:
            json.dump(user_intervals, file)
        else:
            file.write('')

# Save user links to the JSON file
def save_links():
    with open(LINKS_FILE, 'w') as file:
        if user_links:
            json.dump(user_links, file)
        else:
            file.write('')

# Save user status to the JSON file
def save_status():
    with open(STATUS_FILE, 'w') as file:
        if user_status:
            json.dump(user_status, file)
        else:
            file.write('')


# Handle the /help command
def help(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    context.bot.send_message(chat_id=chat_id, text='Welcome!\nUse /interval <seconds> to set the interval.\nUse /run to start afeter setting an interval.\nUser /stop to stop updates.')

# Handle the /stop command
def stop(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    if str(chat_id) in user_status:
        if user_status[str(chat_id)] == "running":
            # Remove the job for the user
            job = context.job_queue.get_jobs_by_name(str(chat_id))
            if job:
                job[0].schedule_removal()
                # user_intervals[str(chat_id)] = -1  # Set interval to -1
                # save_intervals()
                user_status[str(chat_id)] = "stopped"
                save_status()
                context.bot.send_message(chat_id=chat_id,text='Updates have stopped.\nUse /run to start getting updates')
                print(update.effective_chat.username + " stopped the updates")
            else:
                context.bot.send_message(chat_id=chat_id, text='No interval is set.')
        else:
            context.bot.send_message(chat_id=chat_id, text='Updates were already stopped.')
    else:
        context.bot.send_message(chat_id=chat_id, text='No updates were found for this user')



# Handle the /interval command
def set_interval(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    try:
        interval = int(context.args[0])
        if interval <= 0:
            raise ValueError()

        # Check if the user already has an interval set
        if str(chat_id) in user_intervals:
            # Remove the previous job
            job = context.job_queue.get_jobs_by_name(str(chat_id))
            if job:
                job[0].schedule_removal()

        # Store the new interval for the user
        user_intervals[str(chat_id)] = interval
        save_intervals()

        context.bot.send_message(chat_id=chat_id, text=f'Interval set to {interval} seconds.')

    except (IndexError, ValueError):
        context.bot.send_message(chat_id=chat_id, text='Wrong instruction, please write /interval <seconds>')

# Handle the /grade & /allproducts command
def set_link(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message = ''
    try:
        if update.effective_message.text == '/allproducts':
            link = URL_ALL
            message = f"Now getting updates from all products"
        else:
            link = URL_GRADE
            message = f"Now getting updates from Grade A/B/C products"

        # Check if the user already has an interval set
        if str(chat_id) in user_links:
            # Remove the previous job
            job = context.job_queue.get_jobs_by_name(str(chat_id))
            if job:
                job[0].schedule_removal()

        # Store the new interval for the user
        user_links[str(chat_id)] = link
        save_links()

        context.bot.send_message(chat_id=chat_id, text=message)

    except (IndexError, ValueError):
        context.bot.send_message(chat_id=chat_id, text='Please don\'t write anything else')

# Loads the browser and gets the most recent product
def online_search(link):
    most_recent = get_most_recent()  # Read the most_recent value from the file
    new_product_count = -1
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Create the WebDriver instance
    driver = webdriver.Firefox(options=options)
    driver.get(link)
    driver.implicitly_wait(1)  # Wait up to 2 seconds for elements to appear

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
            if product != most_recent:

                # Product data
                most_recent = product
                productID = most_recent.split('/')[4]
                set_most_recent(most_recent)  # Write the updated most_recent value to the file

                # returns a message with the new product
                if new_product_count == 1 or new_product_count == -1:
                    message = 'Novo produto no site!\nhttps://talk-point.de/products/' + productID
                else:
                    message = f'Novo produto no site!\nhttps://talk-point.de/products/{productID}\nNovos produtos: {new_product_count}'
                return message
    else:
        print('Error: ul_element not found')


# Handle the data function to be executed with the specified interval
def run(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    if not str(chat_id) in user_status:
        user_status[str(chat_id)] = "running"
        save_status()

    # if the user doesn't exist in the list, added with default interval
    if not str(chat_id) in user_intervals:
        user_intervals[str(chat_id)] = 1800
        context.bot.send_message(chat_id=chat_id, text='Default interval of 30 minutes was set. /interval <seconds> to change.')
        save_intervals()

    # if the user doesn't exist in the list, added with default URL
    if not str(chat_id) in user_links:
        user_links[str(chat_id)] = URL_ALL
        context.bot.send_message(chat_id=chat_id, text='Now getting updates from all products. \grade to change.')
        save_links()

    if user_status[str(chat_id)] == "stopped":
        # if the user exists in the interval, and the interval > 0, runs the notify that checks the website
        if str(chat_id) in user_intervals:
            interval = user_intervals[str(chat_id)]
            if interval > 0:
                link = user_links.get(str(chat_id))  # Use .get() to handle missing link case
                context.bot.send_message(chat_id=chat_id, text=f'Updates have started every {interval} seconds.')
                print(update.effective_chat.username + " joined the updates")
                user_status[str(chat_id)] = "running"
                save_status()
                context.job_queue.run_repeating(notify, interval, context=(chat_id, link), name=str(chat_id))
            else:
                context.bot.send_message(chat_id=chat_id, text='Please set an interval using /interval <seconds>.')
    else:
        context.bot.send_message(chat_id=chat_id, text='Updates were already running.')

# Notifies the user with data from the function online_search
def notify(context: CallbackContext):
    chat_id, link = context.job.context
    message = online_search(link)
    # if there's a message, sends to the user
    if message:
        context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')


# Main
def main():
    print('running!')

    # Load user intervals from the JSON file on bot startup
    load_intervals()
    load_links()
    load_status()

    for each in user_status:
        user_status[each] = "stopped"

    save_status()

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

    # Start the bot
    updater.start_polling()

    # Send a message to all users
    for chat_id in user_intervals:
        updater.bot.send_message(chat_id=chat_id, text='The bot has restarted.\nPlease /run to continue getting updates')

    updater.idle()

if __name__ == '__main__':
    main()