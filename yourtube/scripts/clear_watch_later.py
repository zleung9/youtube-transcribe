from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import time
from yourtube.utils import load_youtube_cookies

def clear_watch_later_with_selenium(cookie_path: str):
    """
    Alternative method to clear Watch Later playlist using browser automation.
    Use this if you don't want to set up the YouTube API.
    
    Requires:
    - selenium: pip install selenium
    - webdriver-manager: pip install webdriver-manager
    """
    # Setup Chrome
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')  # Uncomment to run in background
    
    # Initialize the driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # Load cookies from file
    driver.get("https://www.youtube.com")
    load_youtube_cookies(driver, cookie_path)
    
    # Navigate to Watch Later
    driver.get("https://www.youtube.com/playlist?list=WL")
    time.sleep(3)
    
    videos_removed = 0
    
    while True:
        try:
            # Wait for video elements to load
            video_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "ytd-playlist-video-renderer")
                )
            )
            
            if not video_elements:
                break
            
            # Click the first video's menu button
            menu_button = video_elements[0].find_element(
                By.CSS_SELECTOR, 
                "button.yt-icon-button[aria-label='Action menu']"
            )
            menu_button.click()
            
            # Wait for menu to appear and click "Remove from Watch Later"
            remove_option = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//span[contains(text(), 'Remove from Watch Later')]")
                )
            )
            remove_option.click()
            
            videos_removed += 1
            print(f"Removed video {videos_removed}")
            
            # Wait a bit for removal to complete
            time.sleep(1)
            
            # Refresh page if no more videos are visible
            if len(video_elements) == 1:
                driver.refresh()
                time.sleep(2)
            
        except Exception as e:
            print(f"Error during removal: {str(e)}")
            # Refresh page and try again
            driver.refresh()
            time.sleep(2)
            
            # Break if we've been trying for too long
            if videos_removed == 0:
                break
    
    driver.quit()
    print(f"Successfully removed {videos_removed} videos from Watch Later playlist")
    return True


if __name__ == "__main__":
    clear_watch_later_with_selenium("/Users/zhuliang/Downloads/youtube_cookies.json")