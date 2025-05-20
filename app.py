import datetime
import logging
import os
import time
import argparse
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
)
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC


BASE_URL = "https://seller.wildberries.ru"
SUPPLIES_URL = "/supplies-management/all-supplies"

USER_WAREHOUSES_DATA = [
    {"name": "Электросталь", "order": "38521712"},
    # {"name": "Коледино", "order": "29875722"},
    {"name": "Тула", "order": "38443505"},
    # {"name": "Казань_тест", "order": "38519855"},
    # {"name": "Тест_астана2", "order": "38475160"},
    # {"name": "Краснодар", "order": "30454707"},
]

USER_WAREHOUSES_LIST = [warehouse["name"] for warehouse in USER_WAREHOUSES_DATA]

# USER_BOX_TYPE = ['Короба',] не нужен, тк при создании черновика выбирается тип упаковки

USER_COEFFICIENT = [
    0,
    1,
    2,
    # 3,
    # 4,
    # 5,
    # 20,
]

USER_DATE = "2025-05-26"


def createParserCMD():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--single", action="store_true", default=False)
    return parser


def transform_date(date: str):
    months = [
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ]

    if "-" in date:
        year, month, day = date.split("-")
        return {"day": int(day), "month": int(month), "year": int(year)}
    else:
        date_process = date.split(",")[0]
        day, month_str = date_process.split(" ")
        month_int = int(months.index(month_str) + 1)
        current_month = int(datetime.datetime.now().month)
        current_year = int(datetime.datetime.now().year)
        year = current_year if month_int >= current_month else current_year + 1
        return {"day": int(day), "month": int(month_int), "year": int(year)}


def CMD_validate_single_date(flag: bool, day_date_dict: dict, user_date_dict: dict, day_coefficient: int):
    if flag is False:
        return (
            (day_date_dict["day"] >= user_date_dict["day"] and day_date_dict["month"] == user_date_dict["month"])
            or day_date_dict["month"] > user_date_dict["month"]
            or day_date_dict["year"] > user_date_dict["year"]
        ) and int(day_coefficient) in USER_COEFFICIENT
    elif flag is True:
        return day_date_dict["day"] == user_date_dict["day"] and int(day_coefficient) in USER_COEFFICIENT


def start_app(single_date: bool):
    if single_date:
        print(f'Запускаем поиск поставки на конкретный день {USER_DATE}')
    else:
        print(f'Запускаем поиск поставки после указанной даты {USER_DATE}')

    options = webdriver.ChromeOptions()
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    )
    # скроем ошибку, связанную с SSL
    options.add_argument("--ignore-certificate-errors-spki-list")
    options.add_argument("--ignore-ssl-errors")
    # сессию будем хранить в отдельном профиле
    options.add_argument("--allow-profiles-outside-user-dir")
    options.add_argument("--enable-profile-shortcut-manager")
    options.add_argument(f"user-data-dir={os.getcwd()}\\User")
    options.add_argument("--profile-directory=Vlad")
    # отключения механизма, который позволяет веб-сайтам обнаруживать автоматизацию
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])  # Скрывает баннер 
    options.add_argument("--disable-infobars")  # Отключает инфо-ленту
    # options.binary_location = "C:\Program Files\Google\Chrome\Application\chrome.exe"

    # безголовый режим
    options.add_argument("--headless")

    driver = webdriver.Chrome(options=options)
    actions = ActionChains(driver)

    driver.get(BASE_URL + SUPPLIES_URL)

    for warehouse in USER_WAREHOUSES_DATA:
        driver.switch_to.new_window("tab")
        url = f'{BASE_URL}{SUPPLIES_URL}/supply-detail?preorderId={warehouse["order"]}&supplyId'

        try:
            driver.get(url)
        except Exception as e:
            logging.error(f'-- Неверно указан order -- Error: {e}')

        descriptor = driver.current_window_handle
        warehouse.update({"descriptor": descriptor, "life_time": 100})
        time.sleep(2)

    while USER_WAREHOUSES_DATA:
        print(
            f"{datetime.datetime.now()} Запускаем цикл {100 - warehouse['life_time']}"
        )

        for warehouse in USER_WAREHOUSES_DATA:
            # переключаемся на соответствующую вкладку
            driver.switch_to.window(warehouse["descriptor"])
            warehouse["life_time"] -= 1

            # нажмем на кнопку "Запланировать поставку"
            try:
                schedule_delivery_button = (
                    "xpath",
                    '//button[contains(@class, "button__ymbakhzRxO")]/span[contains(text(), "Запланировать поставку")]',
                )
                schedule_delivery = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located(schedule_delivery_button)
                )
                schedule_delivery.click()

            except TimeoutException:
                logging.error(
                    f'{datetime.datetime.now()} Превышен таймаут schedule_delivery_button на цикле {warehouse["name"]}'
                )
                driver.refresh()
                continue
            except ElementClickInterceptedException:
                logging.error(
                    f'{datetime.datetime.now()} Всплыло окошко "ошибка сети" - schedule_delivery_button на цикле {warehouse["name"]}'
                )
                driver.refresh()
                continue
            except Exception as e:
                logging.error(f'{datetime.datetime.now()} - schedule_delivery_button на цикле {warehouse["name"]} - ошибка {e}')
                driver.refresh()
                continue

            # получаем дни из календаря
            try:
                days_list_xpath = (
                    "xpath",
                    '//div[@class="Calendar-cell__cell-content__EoHgwsbqB0"]',
                )
                days_list = WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located(days_list_xpath)
                )
            except TimeoutException:
                logging.error(
                    f'{datetime.datetime.now()} Превышен таймаут days_list на цикле {warehouse["name"]}'
                )
                continue
            # каждый день на соответствие исходным данным
            for day in days_list:
                try:
                    day_date = day.find_element(
                        "xpath",
                        './div[@class="Calendar-cell__date-container__2TUSaIwaeG"]/span',
                    ).text
                    day_coefficient = day.find_element(
                        "xpath", "./div[2]/div[1]/div[1]/div[1]/span[1]/div[1]/span[2]", 
                    ).text

                    if day_coefficient.isnumeric():
                        day_coefficient = int(day_coefficient)
                    elif day_coefficient == "Бесплатно":
                        day_coefficient = 0
                    elif day_coefficient == "Пока недоступно":
                        day_coefficient = 21

                    # elif isinstance(day_coefficient, str):
                    #     day_coefficient = 21

                    logging.info(f"{datetime.datetime.now()} {day_date} - {day_coefficient}")

                except Exception as e:
                    logging.info(f"{datetime.datetime.now()} поставка на {day_date} ошибка {e}")
                    continue

                user_date_dict = transform_date(USER_DATE)
                day_date_dict = transform_date(day_date)
                # print("This is return from validator")
                # print(CMD_validate_single_date(single_date, day_date_dict, user_date_dict, day_coefficient))

                if CMD_validate_single_date(single_date, day_date_dict, user_date_dict, day_coefficient):
                    # если условие выполняется наводим курсор и нажимаем выбрать
                    actions.move_to_element(day)
                    actions.perform()
                    # driver.get_screenshot_as_file(
                    #     f"{datetime.datetime.now().day}_test.png"
                    # )

                    # Нажимаем кнопку выбрать
                    day.parent.find_element(
                        "xpath",
                        './/div[@class="Custom-popup"]//span[contains(text(), "Выбрать")]',
                    ).click()

                    # нажимаем на кнопку "Запланировать"
                    # driver.find_element('xpath', f'//div[@class="Modal__content__tdLj90YfdL"]//button[contains(@class, "button__I8dwnFm136")]//span[text()="Запланировать"]').click()
                    schedule_enter = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (
                                "xpath",
                                f'//div[@class="Modal__content__tdLj90YfdL"]//button[contains(@class, "button__I8dwnFm136")]//span[contains(text(), "Запланировать")]',
                            )
                        )
                    )
                    schedule_enter.click()
                    # try:
                    #     WebDriverWait(driver, 60).until(EC.url_to_be(f'{BASE_URL}{SUPPLIES_URL}'))
                    # except Exception as e:
                    #     logging.info(f'Произошла ошибка создания поставки на {warehouse["name"]} с {day_coefficient} запланирована на {day_date} или переход не состоялся: {e}')
                    #     continue

                    driver.get_screenshot_as_file(
                        f"{datetime.datetime.now().day}_{warehouse['name']}_{day_coefficient}.png"
                    )
                    time.sleep(10)

                    print(
                        f'{datetime.datetime.now()}: поставка на {warehouse["name"]} с {day_coefficient} запланирована на {day_date}!'
                    )
                    # time.sleep(10)

                    USER_WAREHOUSES_DATA.remove(warehouse)
                    break

            # будем нажимать крестик для закрытия модального окна button__ynLa9D20nV m__Mbjscl64eV onlyIcon__IUCeD-rFzH
            # exit_button_xpath = ('xpath', '//button[@class="button__ynLa9D20nV m__Mbjscl64eV onlyIcon__IUCeD-rFzH"]')
            # exit_button = WebDriverWait(driver, 20).until(EC.presence_of_element_located(exit_button_xpath))
            # exit_button.click()
            # !!!!!Не получилось нажимать, периодически выпадает профиль и перекрывает кнопку х

            # нажатие клавиши esc
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(("xpath", "//body[1]"))
            ).send_keys(Keys.ESCAPE)

            if warehouse["life_time"] <= 0:
                driver.refresh()
                print(
                    f'{datetime.datetime.now()} Перезагружаем вкладку {warehouse["name"]}'
                )
                warehouse["life_time"] = 100
    driver.close()


if __name__ == "__main__":
    logging.basicConfig(level=30)

    parser = createParserCMD()
    namespace = parser.parse_args()

    start_app(namespace.single)
