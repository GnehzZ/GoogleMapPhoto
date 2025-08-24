from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time, os, requests
from urllib.parse import urlparse

# —— 1. 启动 Driver —— #
options = webdriver.ChromeOptions()
# 为了调试，先不要 headless，等能跑通再打开 headless
# options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 15)

# —— 2. 打开页面 —— #
url = "https://www.google.com/maps/contrib/109950398817866786892/photos/"
driver.get(url)

# —— 3. 定位到“照片列表”可滚动容器 —— #
# 下面这个 selector 可能需要根据你浏览器的实际 DOM 调整
container = wait.until(EC.presence_of_element_located((
    By.CSS_SELECTOR,
    'div[role="region"] > div[jsaction][aria-label*="Photos"]'
)))

# —— 4. 在容器里滚动，并收集所有缩略图 —— #
thumbs = set()
last_len = 0
while True:
    # 执行容器滚动到底
    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", container)
    time.sleep(1)  # 等待新缩略图加载

    # 收集当前可见的缩略图
    els = container.find_elements(By.CSS_SELECTOR, 'img[src*="googleusercontent.com"][role="button"]')
    for el in els:
        thumbs.add(el)
    # 如果数量不再增加，则认为滚动结束
    if len(thumbs) == last_len:
        break
    last_len = len(thumbs)

print(f"总共收集到 {len(thumbs)} 个缩略图元素")

# —— 5. 下载目录 —— #
save_dir = "gmaps_large_photos"
os.makedirs(save_dir, exist_ok=True)

# —— 6. 依次打开、下载、关闭 —— #
for idx, thumb in enumerate(thumbs, 1):
    try:
        # 滚入可视区并点击
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", thumb)
        ActionChains(driver).move_to_element(thumb).click().perform()

        # 等待大图预览出现
        big = wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR,
            'img[aria-label="Image"][src*="googleusercontent.com"]'
        )))
        big_url = big.get_attribute("src")

        # 下载
        resp = requests.get(big_url, timeout=15)
        ext = os.path.splitext(urlparse(big_url).path)[1] or ".jpg"
        fname = os.path.join(save_dir, f"photo_{idx:03d}{ext}")
        with open(fname, "wb") as f:
            f.write(resp.content)
        print(f"[{idx}] Saved to {fname}")

        # 关闭预览（优先按钮，失败用 ESC）
        try:
            driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Close"]').click()
        except:
            ActionChains(driver).send_keys(u'\ue00c').perform()
        time.sleep(0.5)

    except Exception as e:
        print(f"[{idx}] Error: {e}")
        # 确保预览被关闭
        ActionChains(driver).send_keys(u'\ue00c').perform()
        time.sleep(0.5)

driver.quit()
print("Finished.")
