# Talk-point price Updates

This script fetches the latest product updates from Talk-point and sends them to a Telegram channel. It uses web scraping with Selenium and BeautifulSoup to extract data from the Talk-point website and the Telegram API to send notifications.

## Requirements

- Beautifulsoup4
- Python-telegram-bot
- Selenium
- Selenium stealth
- Webdriver manager

## Features
- Checks website every # minutes for new products
- Has a favorite checklist that can be changed within telegram that is checked everyday at a certain hour to see if a product price has dropped

## Installation

1. Clone the repository:

```python
git clone https://github.com/henriqueleote/TalkpointChannelBot.git
cd TalkpointChannelBot
```

2. Install the required dependencies:

```python
pip install -r requirements.txt
```

3. Download the Chrome WebDriver and place it in the project directory. Make sure the WebDriver version matches your Chrome browser version.

4. Obtain a Telegram Bot API token by creating a bot through the BotFather. Copy the token for later use.

5. Update the `TOKEN` variable in the script with your Telegram Bot API token.
   
## Usage

1. Run the script:

```python
py bot.py
```

2. The script will continuously fetch the latest product updates from Talk-point.de and send them to the configured Telegram channel. It will check for new products since the last run.

## Customization

- Adjust the sleep duration in the `time.sleep()` function to control the interval between each data fetch.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.


## Autors

- [@henriqueleote](https://www.github.com/henriqueleote)

## License

[MIT License](LICENSE)
