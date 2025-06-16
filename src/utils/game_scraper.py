# src/utils/game_scraper.py

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import chess.pgn
import io

class GameScraper:
    """
    Uses Selenium WebDriver to fetch game PGN from Chess.com or similar platforms.
    """

    def __init__(self, username: str, password: str, driver_path: str):
        """
        Initialize the scraper with login credentials and WebDriver path.
        """
        options = Options()
        options.add_argument("--headless")  # Run in headless mode for CI/CD environments[1]
        self.driver = webdriver.Chrome(executable_path=driver_path, options=options)
        self.username = username
        self.password = password

    def login(self, url: str = "https://www.chess.com/login"):
        """
        Log into the chess platform using provided credentials.
        """
        self.driver.get(url)
        time.sleep(2)  # Wait for page load
        self.driver.find_element(By.ID, "username").send_keys(self.username)
        self.driver.find_element(By.ID, "password").send_keys(self.password)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(3)  # Allow login to complete[2]

    def fetch_pgn(self, game_url: str) -> str:
        """
        Navigate to a game page and return the PGN text.
        """
        self.driver.get(game_url)
        time.sleep(2)  # Wait for game page to load
        # Click on the "Download" or "PGN" button
        pgn_button = self.driver.find_element(By.CSS_SELECTOR, ".download-pgn")
        pgn_button.click()
        time.sleep(1)  # Wait for PGN modal
        pgn_text = self.driver.find_element(By.CSS_SELECTOR, ".pgn-textarea").get_attribute("value")
        return pgn_text

    def parse_pgn(self, pgn_text: str):
        """
        Convert PGN string to a chess.pgn.Game object for further processing.
        """
        pgn_io = io.StringIO(pgn_text)
        game = chess.pgn.read_game(pgn_io)
        return game

    def close(self):
        """
        Close the browser session.
        """
        self.driver.quit()
