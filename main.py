import requests
import gspread
from fake_useragent import UserAgent
from datetime import datetime, timedelta
import time
import mysql.connector
from mysql.connector import Error
import logging

logging.basicConfig(level=logging.INFO, filename='p2p_binance_log.log', filemode='w',
                    format='%(asctime)s %(levelname)s %(message)s')

interval = 0  
  
payment_method = [
    'Monobank',
    'PrivatBank',
    'PUMBbank',
    'ABank',
    'RaiffeisenBankAval',
    'GEOPay'
]

crypto = [
    'USDT',
    'ETH',
    'BTC',
    'BNB',
    'SHIB'
]

google = {} # your google api key, json format

gc = gspread.service_account_from_dict(google)
sh = gc.open_by_key('') # your google sheet ID number
ws = sh.sheet1

def create_connection(host_name, user_name, user_password, db_name):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=db_name
        )
    except Error as e:
        print(e)
    return connection

def execute_query(connection, query):
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()
    except (TypeError, mysql.connector.errors.ProgrammingError, mysql.connector.errors.OperationalError):
        pass

count = 2

def binance(asset, pay_type, trade_type, connection):
    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'content-type': 'application/json',
        'Host': 'p2p.binance.com',
        'Origin': 'https://p2p.binance.com',
        'User-Agent': UserAgent().random
    }

    data = {
        'asset': asset,
        'fiat': 'UAH',
        'merchantCheck': False,
        'page': 1,
        'payTypes': [pay_type],
        'publisherType': None,
        'rows': 10,
        'tradeType': trade_type
    }

    response = requests.post(url='https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search', headers=headers, json=data)

    if response.ok:
        response = response.json()['data']

        for value in response:
            date_now = (datetime.now() + timedelta(hours=2)).strftime('%d.%m.%y %H:%M:%S')
            trader = value["advertiser"]["nickName"]
            price = value["adv"]["price"]
            amount = value["adv"]["tradableQuantity"]
            # min_amount = value["adv"]["minSingleTransAmount"]

            global count, id_table
            if trade_type == 'BUY':
                try:
                    ws.update(f'A{count}', [[date_now, trader, f'{asset}/UAH', price, amount, 'Binance', pay_type]])
                except gspread.exceptions.APIError:
                    pass
                update_info = f"""
                INSERT INTO
                  p2p (`Дата і Час`, `Продавець`, `Пара`, `Курс`, `Ліміти`, `Біржа`, `Метод оплати`)
                VALUES
                  ('{date_now}', '{trader}', '{asset}/UAH', '{price}', '{amount}', 'Binance', '{pay_type}')
                """
                execute_query(connection, update_info)
            else:
                try:
                    ws.update(f'A{count}', [[date_now, trader, f'UAH/{asset}', price, amount, 'Binance', pay_type]])
                except gspread.exceptions.APIError:
                    pass
                update_info = f"""
                INSERT INTO
                    p2p (`Дата і Час`, `Продавець`, `Пара`, `Курс`, `Ліміти`, `Біржа`, `Метод оплати`)
                VALUES
                    ('{date_now}', '{trader}', 'UAH/{asset}', '{price}', '{amount}', 'Binance', '{pay_type}')
                """
                execute_query(connection, update_info)
            count += 1
        time.sleep(8)


def start():
    while True:
        global count
        count = 2
        connection = create_connection('', '', '', '') # your database info(IP, username, password, table name)
        for bank in payment_method:
            for coin in crypto:
                binance(coin, bank, 'BUY', connection)
                binance(coin, bank, 'SELL', connection)
        time.sleep(interval*60)

if __name__ == '__main__':
    start()
