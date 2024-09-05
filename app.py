import datetime
import logging
import os
import time
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
    {
        "name": "Электросталь", 
        "order": "27859852"
    },
    # {
    #     "name": "Коледино", 
    #     "order": "27742994"
    # },
    {
        "name": "Тула", 
        "order": "27944626"
    },
]

USER_WAREHOUSES_LIST = [warehouse["name"] for warehouse in USER_WAREHOUSES_DATA]

# USER_BOX_TYPE = ['Короба',] не нужен, тк при создании черновика выбирается тип упаковки

USER_COEFFICIENT = [
    0,
    1,
]

USER_DATE = "2024-09-11"


def start_app():
    options = webdriver.ChromeOptions()
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )
    # скроем ошибку, связанную с SSL
    options.add_argument("--ignore-certificate-errors-spki-list")
    options.add_argument("--ignore-ssl-errors")
    # сессию будем хранить в отдельном профиле
    options.add_argument("--allow-profiles-outside-user-dir")
    options.add_argument("--enable-profile-shortcut-manager")
    options.add_argument(f"user-data-dir={os.getcwd()}\\User")
    options.add_argument("--profile-directory=Vlad")
    # безголовый режим
    options.add_argument("--headless")

    driver = webdriver.Chrome(options=options)
    actions = ActionChains(driver)

    driver.get(BASE_URL + SUPPLIES_URL)

    for warehouse in USER_WAREHOUSES_DATA:
        driver.switch_to.new_window("tab")
        url = f'{BASE_URL}{SUPPLIES_URL}/supply-detail/uploaded-goods?preorderId={warehouse["order"]}&supplyId'
        driver.get(url)
        descriptor = driver.current_window_handle
        warehouse.update({"descriptor": descriptor})
        time.sleep(2)

    def transform_user_date(date: str):
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

        year, month, day = date.split("-")

        if " ".join(list(day)).startswith("0"):
            day = list(day)[-1]

        return f"{day} {months[int(month) - 1]}"

    success = False
    counter = 0

    while not success:
        print(f"{datetime.datetime.now()} Запускаем цикл {counter}")
        counter += 1
        for warehouse in USER_WAREHOUSES_DATA:
            # переключаемся на соответствующую вкладку
            driver.switch_to.window(warehouse["descriptor"])
            if counter == 100:
                driver.refresh()
                print(
                    f'{datetime.datetime.now()} Перезагружаем вкладку {warehouse["name"]}'
                )
                counter = 0 
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
                continue
            except ElementClickInterceptedException:
                logging.error(
                    f'{datetime.datetime.now()} Всплыло окошко "ошибка сети" - schedule_delivery_button на цикле {warehouse["name"]}'
                )
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
                        "xpath", "./div[2]/div[1]/div[1]/div[1]/span/div[1]/span[2]"
                    ).text
                    logging.info(f"{datetime.datetime.now()} {day_date} - {day_coefficient}")
                except NoSuchElementException:
                    logging.info(f"{datetime.datetime.now()} поставка на {day_date} не активна")
                    continue

                day_date_format = day_date.split(",")[0]
                user_date_format = transform_user_date(USER_DATE)

                if (
                    int(day_date_format.split(" ")[0]) >= int(user_date_format.split(" ")[0])
                    and int(day_coefficient) in USER_COEFFICIENT
                ):
                    # если условие выполняется наводим курсор и нажимаем выбрать
                    actions.move_to_element(day)
                    actions.perform()

                    # Нажимаем кнопку выбрать
                    day.parent.find_element(
                        "xpath",
                        './/div[@class="Custom-popup"]//span[contains(text(), "Выбрать")]',
                    ).click()

                    driver.get_screenshot_as_file(
                        f"{datetime.datetime.now()}_{warehouse['name']}_{day_coefficient}.png"
                    )
                    # нажимаем на кнопку "Запланировать"
                    # driver.find_element('xpath', f'//div[@class="Modal__content__tdLj90YfdL"]//button[contains(@class, "button__I8dwnFm136")]//span[text()="Запланировать"]').click()
                    schedule_enter = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (
                                "xpath",
                                f'//div[@class="Modal__content__tdLj90YfdL"]//button[contains(@class, "button__I8dwnFm136")]//span[text()="Запланировать"]',
                            )
                        )
                    )
                    schedule_enter.click()
                    success = True
                    print(
                        f'{datetime.datetime.now()}: поставка на {warehouse["name"]} с {day_coefficient} запланирована!'
                    )
                    time.sleep(20)

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

    driver.close()


if __name__ == "__main__":
    logging.basicConfig(level=30)
    start_app()
