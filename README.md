# Talk-point Price Updates

This script fetches the latest product updates from Talk-point and sends them to a Telegram channel. It uses web scraping with Selenium and BeautifulSoup to extract data from the Talk-point website and the Telegram API to send notifications.

## Requirements

- Python 3.x
- Selenium
- BeautifulSoup
- Chrome WebDriver
- Telegram Bot API token

## Installation

1. Clone the repository:

```python
git clone https://github.com/henriqueleote/TalkpointChannelBot
cd your-repo
```

2. Install the required dependencies:

```python
pip install selenium beautifulsoup4
```

3. Download the Chrome WebDriver and place it in the project directory. Make sure the WebDriver version matches your Chrome browser version.

4. Obtain a Telegram Bot API token by creating a bot through the BotFather. Copy the token for later use.

5. Update the `TOKEN` variable in the script with your Telegram Bot API token.
```python
py TalkPointChannelBot
```

2. The script will continuously fetch the latest product updates from Talk-point.de and send them to the configured Telegram channel. It will check for new products since the last run.

## Customization

- Modify the `URL_ALL` and `URL_GRADE` variables in the script to fetch data from different URLs on the Talk-point website.
- Adjust the sleep duration in the `time.sleep()` function to control the interval between each data fetch.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.

## License

[MIT License](LICENSE)