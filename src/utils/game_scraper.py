import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import chess.pgn
import io
class GameScraper:
    def __init__(self, username: str, password: str, driver_path: str):
        options = Options()
        options.add_argument("--headless")
        self.driver = webdriver.Chrome(executable_path=driver_path, options=options)
        self.username = username
        self.password = password
    def login(self, url: str = "https://www.chess.com/login"):
        self.driver.get(url)
        time.sleep(2)
        self.driver.find_element(By.ID, "username").send_keys(self.username)
        self.driver.find_element(By.ID, "password").send_keys(self.password)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(3)
    def fetch_pgn(self, game_url: str) -> str:
        self.driver.get(game_url)
        time.sleep(2)
        pgn_button = self.driver.find_element(By.CSS_SELECTOR, ".download-pgn")
        pgn_button.click()
        time.sleep(1)
        pgn_text = self.driver.find_element(By.CSS_SELECTOR, ".pgn-textarea").get_attribute("value")
        return pgn_text
    def parse_pgn(self, pgn_text: str):
        pgn_io = io.StringIO(pgn_text)
        game = chess.pgn.read_game(pgn_io)
        return game
    def close(self):
        self.driver.quit()
