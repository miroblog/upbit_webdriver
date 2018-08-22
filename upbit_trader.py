import pandas as pd
from bs4 import BeautifulSoup as BSoup
from selenium import webdriver
import threading, time
import sys
import pickle
import math
import pyperclip
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
# for explicit wait
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

kakao_id_secret = "ur_kakao_id"
kakao_pwd_secret = "ur_pass_wd"


SCROLL_VIEW = "var viewPortHeight = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);"\
              + "var elementTop = arguments[0].getBoundingClientRect().top;"\
              + "window.scrollBy(0, elementTop-(viewPortHeight/2));"


class UpbitOrder:
    def __init__(self, price, quantity, index, timestamp):
        self.price = price
        self.quantity = quantity
        self.index = index
        self.timestamp = timestamp

    def __str__(self):
        return "{0}: price {1} quantity {2} index {3}".format(self.timestamp, self.price, self.quantity, self.index)


class upbitTrader:
    def __init__(self, isAws=False):
        self.handles = []
        self.pending_buy_orders = []
        self.pending_sell_orders = []
        self.available_coin = 0
        self.available_krw = 0
        if (isAws == True):
            from pyvirtualdisplay import Display
            # make virtual display
            self.display = Display(visible=0, size=(800, 600))
            self.display.start()
        self.browser = webdriver.Chrome()
        self.url = "http://upbit.com/exchange?code=CRIX.UPBIT.KRW-"

    def set_value(self, element, value):
        element.click()
        time.sleep(0.5)
        pyperclip.copy(value)
        ActionChains(self.browser).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
        time.sleep(0.5)
        ActionChains(self.browser).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()

    def get_element(self, css_path):
        return WebDriverWait(self.browser, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, css_path)))

    def set_up_trade(self, src):
        # set up trade fee, minimal cur decimal
        self.trade_fee = 0.0005
        self.min_trade_cur_decimal = 1e-9

        self.browser.get("https://upbit.com/home")
        self.browser.maximize_window()
        time.sleep(8)

        original_handle = self.browser.current_window_handle
        login_button = self.get_element(
            "#root > div > div > article:nth-child(3) > header > div > ul > li:nth-child(1) > a")
        self.browser.execute_script("return arguments[0].scrollIntoView();", login_button)
        login_button.click()
        check_btn = self.get_element("#root > div > div > div:nth-child(4) > div > section > article > div > a")
        check_btn.click()
        time.sleep(2)

        kakao_login = self.get_element("#root > div > div > div:nth-child(4) > div > section > article > a")
        kakao_login.click()

        time.sleep(4)
        # email
        kakao_id = self.get_element("#loginEmail")
        self.set_value(kakao_id, kakao_id_secret)
        # kakao_id.send_keys(kakao_id_secret)
        kakao_pwd = self.get_element("#loginPw")
        self.set_value(kakao_pwd, kakao_pwd_secret)

        # login persist
        login_persist = self.get_element("#login-form > fieldset > div.set_login > label > span")
        login_persist.click()
        time.sleep(1)

        # kakao_pwd.send_keys(kakao_pwd_secret)
        kakao_login_confirm = self.get_element("#login-form > fieldset > button")
        kakao_login_confirm.click()
        time.sleep(1)

        self.browser.switch_to.window(original_handle)
        kakao_validation = self.get_element(
            "#root > div > div > div:nth-child(4) > div > section > article > span.btnB.time > input")

        x = input('input kakao validation: ')
        self.set_value(kakao_validation, x)
        kakao_validation_confirm = self.get_element("#root > div > div > div:nth-child(4) > div > section > article > a")
        kakao_validation_confirm.click()

        time.sleep(4)
        self.browser.get(self.url+src)
        time.sleep(4)

    def update_balance_state(self):
        while True:
            try:
                buy_tab = self.get_element(
                    "#root > div > div > div:nth-child(4) > div > section.ty01 > div > div.rightB > article:nth-of-type(1) > span.tabB > ul > li.t2 > a")
                # self.browser.execute_script(SCROLL_VIEW, buy_tab)
                buy_tab.click()
                # self.browser.execute_script("return arguments[0].scrollIntoView();", buy_tab)
                time.sleep(0.8)
                # bs_obj = BSoup(self.browser.page_source, 'html.parser')
                # available_krw = bs_obj.select_one("#root > div > div > div:nth-child(4) > div section.ty01 > div > div.rightB > article:nth-child(1) > span.orderB > div > dl > dd.price > strong").get_text()
                available_krw_field = self.browser.find_elements_by_css_selector(
                    "#root > div > div > div:nth-child(4) > div section.ty01 > div > div.rightB > article:nth-of-type(1) > span.orderB > div > dl > dd.price > strong")[
                    0]
                self.browser.execute_script(SCROLL_VIEW, available_krw_field)
                available_krw = available_krw_field.text
                self.available_krw = float(available_krw.replace(",", ""))
                time.sleep(0.8)
                sell_tab = self.get_element(
                    "#root > div > div > div:nth-child(4) > div section.ty01 > div > div.rightB > article:nth-of-type(1) > span.tabB > ul > li.t3 > a")
                sell_tab.click()
                time.sleep(0.8)
                available_coin_field = self.browser.find_elements_by_css_selector(
                    "#root > div > div > div:nth-child(4) > div section.ty01 > div > div.rightB > article:nth-of-type(1) > span.orderB > div > dl > dd.price > strong")[
                    0]
                available_coin = available_coin_field.text
                self.available_coin = float(available_coin.replace(",", ""))
                break
            except:
                print("error occurred while updating available krw/coin !")
                print("retry ...")
                self.browser.get(self.url+"ADA")
                # self.browser.execute_script('window.scrollTo(0,document.body.scrollHeight)')
                time.sleep(3)
    def show_pending_orders(self):
        self.update_pending_order()
        if (len(self.pending_sell_orders) != 0):
            for order in self.pending_sell_orders:
                print(order)
        if (len(self.pending_buy_orders) != 0):
            for order in self.pending_buy_orders:
                print(order)

    def put_sell_order(self, price, quantity):
        a = 0
        while a < 2:
            try:
                sell_tab = self.get_element(
                    "#root > div > div > div:nth-child(4) > div > section.ty01 > div > div.rightB > article:nth-child(1) > span.tabB > ul > li.t3 > a")
                sell_tab.click()
                # self.browser.execute_script(SCROLL_VIEW, sell_tab)
                time.sleep(1)
                available_coin_field = self.browser.find_elements_by_css_selector(
                    "#root > div > div > div:nth-child(4) > div > section.ty01 > div > div.rightB > article:nth-child(1) > span.orderB > div > dl > dd.price > strong")[
                    0]
                self.browser.execute_script(SCROLL_VIEW, available_coin_field)
                available_coin = available_coin_field.text
                available_coin = float(available_coin.replace(",", ""))
                time.sleep(0.3)
                if quantity == "ALL":
                    quantity = available_coin
                if (available_coin > quantity):
                    print("not enough coin")
                else:
                    # get price and quantity field
                    price_field = self.get_element(
                        "#root > div > div > div:nth-child(4) > div > section.ty01 > div > div.rightB > article:nth-child(1) > span.orderB > div > dl > dd:nth-child(6) > div > input")
                    quantity_field = self.get_element(
                        "#root > div > div > div:nth-child(4) > div > section.ty01 > div > div.rightB > article:nth-child(1) > span.orderB > div > dl > dd:nth-child(4) > input")

                    self.set_value(price_field, str(int(price)))
                    self.set_value(quantity_field, str(quantity))

                    # execute sell
                    sell_btn = self.get_element(
                        "#root > div > div > div:nth-child(4) > div > section.ty01 > div > div.rightB > article:nth-child(1) > span.orderB > div > ul > li.ty02 > a")
                    sell_btn.click()
                    sell_confirm = self.get_element(
                        "#checkVerifMethodModal > div > section > article > span > a:nth-child(2)")
                    sell_confirm.click()
                    final_confirmation = self.get_element("#checkVerifMethodModal > div > section > article > span > a")
                    final_confirmation.click()
                break
            except:
                a += 1
                print("error occured while selling")
                self.browser.get(self.url + "ADA")
                time.sleep(3)

    def put_buy_order(self, price, quantity):
        a = 0
        while a < 2:
            try:
                buy_tab = self.get_element(
                    "#root > div > div > div:nth-child(4) > div > section.ty01 > div > div.rightB > article:nth-child(1) > span.tabB > ul > li.t2 > a")
                buy_tab.click()
                time.sleep(1)
                available_krw_field = self.browser.find_elements_by_css_selector(
                    "#root > div > div > div:nth-child(4) > div > section.ty01 > div > div.rightB > article:nth-child(1) > span.orderB > div > dl > dd.price > strong")[
                    0]
                self.browser.execute_script(SCROLL_VIEW, available_krw_field)
                available_krw = available_krw_field.text
                available_krw = float(available_krw.replace(",", ""))
                if (quantity == "ALL"):
                    before_fee_unit = available_krw / price
                    expected_fee = before_fee_unit * self.trade_fee
                    quantity = math.floor(
                        (before_fee_unit - expected_fee) * (
                        1 / self.min_trade_cur_decimal)) * self.min_trade_cur_decimal
                if (quantity == "HALF"):
                    before_fee_unit = available_krw / price * 0.5
                    expected_fee = before_fee_unit * self.trade_fee
                    quantity = math.floor((before_fee_unit - expected_fee) * (
                        1 / self.min_trade_cur_decimal)) * self.min_trade_cur_decimal
                if (quantity == "TEST"):
                    before_fee_unit = available_krw / price * 0.01
                    expected_fee = before_fee_unit * self.trade_fee
                    quantity = math.floor((before_fee_unit - expected_fee) * (
                        1 / self.min_trade_cur_decimal)) * self.min_trade_cur_decimal
                    print("quantity :", quantity)
                if available_krw < price * quantity:
                    print("not enough money")
                else:
                    # get price and quantity field
                    price_field = self.get_element(
                        "#root > div > div > div:nth-child(4) > div > section.ty01 > div > div.rightB > article:nth-child(1) > span.orderB > div > dl > dd:nth-child(6) > div > input")

                    quantity_field = self.get_element(
                        "#root > div > div > div:nth-child(4) > div > section.ty01 > div > div.rightB > article:nth-child(1) > span.orderB > div > dl > dd:nth-child(4) > input")

                    self.set_value(price_field, str(int(price)))
                    time.sleep(0.1)
                    self.set_value(quantity_field, str(quantity))
                    time.sleep(0.1)

                    # execute buy
                    buy_btn = self.get_element(
                        "#root > div > div > div:nth-child(4) > div > section.ty01 > div > div.rightB > article:nth-child(1) > span.orderB > div > ul > li.ty04 > a")
                    buy_btn.click()
                    time.sleep(0.1)
                    buy_confirm = self.get_element(
                        "#checkVerifMethodModal > div > section > article > span > a.bgRed")
                    buy_confirm.click()
                    final_confirmation = self.get_element(
                        "#checkVerifMethodModal > div > section > article > span > a")
                    final_confirmation.click()
                break
            except:
                a += 1
                print("error occured while buying")
                self.browser.get(self.url + "ADA")
                time.sleep(3)
                self.browser.refresh()
                self.browser.execute_script('window.scrollTo(0,document.body.scrollHeight)')
    def cancel_all_order(self):
        self.update_pending_order()
        num_of_orders = len(self.pending_buy_orders) + len(self.pending_sell_orders)
        while (num_of_orders > 0):
            cancel_btn = self.get_element(
                "#root > div > div > div:nth-child(4) > div section.ty01 > div > div.rightB > article:nth-child(1) > span.orderB > div > div:nth-child(2) > div > div > div:nth-child(1) > table > tbody > tr:nth-child(1) > td:nth-child(6)")
            cancel_btn.click()

            confirm_btn = self.get_element(
                "#checkVerifMethodModal > div > section > article > span > a:nth-child(2)")
            confirm_btn.click()

            final_confirmation = self.get_element(
                "#checkVerifMethodModal > div > section > article > span > a")
            final_confirmation.click()

            num_of_orders -= 1
        self.update_pending_order()
        num_of_orders = len(self.pending_buy_orders) + len(self.pending_sell_orders)
        if (num_of_orders == 0):
            print("all pending orders cancelled")
        else:
            print("something gone wrong :", num_of_orders)

    def cancel_order(self, order):
        index = order.index
        cancel_btn = self.get_element(
            "#root > div > div > div:nth-child(4) > div section.ty01 > div > div.rightB > article:nth-child(1) > span.orderB > div > div:nth-child(2) > div > div > div:nth-child(1) > table > tbody > tr:nth-child(" + str(
                index + 1) + ") > td:nth-child(6) > a")
        cancel_btn.click()

        confirm_btn = self.get_element("#checkVerifMethodModal > div > section > article > span > a:nth-child(2)")
        confirm_btn.click()

        final_confirmation = self.get_element("#checkVerifMethodModal > div > section > article > span > a")
        final_confirmation.click()

        self.update_pending_order()

    def update_pending_order(self):
        history_tab = self.get_element(
            "#root > div > div > div:nth-child(4) > div section.ty01 > div > div.rightB > article:nth-child(1) > span.tabB > ul > li.t4 > a")
        history_tab.click()
        time.sleep(0.5)
        history_tab.click()
        time.sleep(0.5)
        bs_obj = BSoup(self.browser.page_source, 'html.parser')

        pending_order_table = bs_obj.select_one(
            "section.ty01 > div > div.rightB > article:nth-of-type(1) > span.orderB > div > div:nth-of-type(2) > div > div > div:nth-of-type(1) > table > tbody")


        if (pending_order_table is not None):
            print("found table")
            orders_raw = pending_order_table.findAll("tr")
        else:  # empty result
            self.pending_sell_orders, self.pending_buy_orders = [], []
            return
        # return buy and sell orders respectively
        self.pending_sell_orders, self.pending_buy_orders = self.parse_orders(orders_raw)

    def parse_orders(self, orders):
        sell_orders = []
        buy_orders = []
        index = 0
        for order in orders:
            info = [order.get_text().replace(",", "") for order in order.find_all("p")]
            # 3rd and 4th column
            parsed_order = UpbitOrder(price=float(info[1]), quantity=float(info[2]), index=index, timestamp=info[0])
            if (order['class'][0] == 'down'):
                sell_orders.append(parsed_order)
            else:
                buy_orders.append(parsed_order)
            index = index + 1
        return sell_orders, buy_orders

    def collector(self):
        browser = self.browser
        bs_obj = BSoup(browser.page_source, 'html.parser')
        span = bs_obj.findAll("span", {"class": "askpriceB"})
        tables = span[0].find_all('table')
        table_orderbook = tables[0].find("tbody")
        table_contract = tables[1].find("tbody")
        asks = table_orderbook.find_all("tr", {"class": "down"})[:-7 - 1:-1]
        bids = table_orderbook.find_all("tr", {"class": "up"})[:7]
        ask_prices = []
        ask_quantities = []
        bid_prices = []
        bid_quantities = []
        for ask in asks:
            ask_quantities.append(float(ask.find('p').get_text().replace(",", "")))
            ask_prices.append(float(ask.find('strong').get_text().replace(",", "")))
        for bid in bids:
            bid_quantities.append(float(bid.find('p').get_text().replace(",", "")))
            bid_prices.append(float(bid.find('strong').get_text().replace(",", "")))
        return ask_prices, bid_prices, ask_quantities, bid_quantities


def main():
    trader = upbitTrader()
    trader.set_up_trade("BTC")
    cmd = "initial"
    while (cmd != "q"):
        cmd = input("cmd 0:buy at bid, 1:buy at bid, 2:sell at bid 3:sell at ask, c to cancel all order")
        ask_prices, bid_prices, ask_quantities, bid_quantities = trader.collector()
        print(bid_prices)
        print(ask_prices)
        if cmd == "0":
            print(bid_prices[0])
            trader.put_buy_order(bid_prices[0], "HALF")
        elif cmd == "1":
            print(ask_prices[0])
            trader.put_buy_order(bid_prices[0], "HALF")
        elif cmd == "2":
            print(bid_prices[0])
            trader.put_sell_order(bid_prices[0], "ALL")
        elif cmd == "3":
            print(bid_prices[0])
            trader.put_sell_order(ask_prices[0], "ALL")
        elif cmd == "c":
            trader.cancel_all_order()

if __name__ == "__main__":
    main()