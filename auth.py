from selenium import webdriver

import time
import pickle
import os


url = "https://seller.wildberries.ru/about-portal/ru/"

#скроем ошибку, связанную с SSL
options = webdriver.ChromeOptions()
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
options.add_argument("--ignore-certificate-errors-spki-list")
options.add_argument("--ignore-ssl-errors")

options.add_argument('--allow-profiles-outside-user-dir')
options.add_argument('--enable-profile-shortcut-manager')
options.add_argument(f'user-data-dir={os.getcwd()}\\User')
options.add_argument('--profile-directory=Vlad')


driver = webdriver.Chrome(options=options)

try:
    driver.get(url)
    print(driver.get_cookies())
    time.sleep(90)
    print(driver.get_cookies())

    pickle.dump(driver.get_cookies(), open("cookies_wb.pkl", "wb"))


except Exception as e:
    print(e)
finally:
    driver.close()
    # driver.quit()