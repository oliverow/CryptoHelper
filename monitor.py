from coinbase.wallet.client import Client

import os
import math
import time
from multiprocessing import Process, Value, Lock
import csv
from datetime import datetime
from ctypes import c_int
import json


class Monitor(object):
    def __init__(self, apiKey, apiSecret, currency):
        self.client = Client(apiKey, apiSecret)
        self.currency = currency
        self.check_standing_interval = Value(c_int, 3600 * 2)           # shared variable with lock
        self.check_price_interval = Value(c_int, 60 * 5)
        self.check_price_fluctuation = 0.05
        self.price_benchmarks = {}
        self.price_limit = {}
        self.price_benchmark_save_file = ".prices.csv"
        self.price_limit_save_file = ".limits.csv"
        self.price_floor_save_file = ".floors.csv"
        if not os.path.exists(self.price_benchmark_save_file):
            with open(self.price_benchmark_save_file, 'w+') as f:
                headers = ["Time"] + TRACKED_COINS
                writer = csv.writer(f, lineterminator=os.linesep)
                writer.writerow(headers)
            self.recordPrice()
        if not os.path.exists(self.price_limit_save_file):
            with open(self.price_limit_save_file, 'w+') as f:
                headers = ["Time"] + TRACKED_COINS
                writer = csv.writer(f, lineterminator=os.linesep)
                writer.writerow(headers)
                tmp = ["1000000"] * len(headers)
                writer.writerow(tmp)
        if not os.path.exists(self.price_floor_save_file):
            with open(self.price_floor_save_file, 'w+') as f:
                headers = ["Time"] + TRACKED_COINS
                writer = csv.writer(f, lineterminator=os.linesep)
                writer.writerow(headers)
                tmp = ["0"] * len(headers)
                writer.writerow(tmp)
        self.jobs = []
        self.running = True
        self.announce_lock = Lock()

    def __del__(self):
        self.running = False
        print("===============System===============")
        print("Destructing")
        for job in self.jobs:
            job.terminate()
        if len(self.jobs) > 0:
            print("===============System===============")
            print("All processes terminated. Exiting the main program")
            print("===============System===============")

    def say(self, sentence):
        self.announce_lock.acquire()
        print("{} | {}".format(datetime.now().strftime("%b %d %H:%M:%S"), sentence))
        if datetime.now().time() < datetime.strptime("23:00:00", "%H:%M:%S").time() and \
                datetime.now().time() > datetime.strptime("09:00:00", "%H:%M:%S").time():
            os.system("say \"{}\"".format(sentence))
        self.announce_lock.release()

    def announceStanding(self, *args):
        accounts = self.client.get_accounts(limit = 100)['data']
        self.say("Your accounts' standings are")
        for account in accounts:
            currency, amount = account['balance']['currency'], float(account['balance']['amount'])
            if amount == 0.0:
                continue
            price = self.client.get_spot_price(currency_pair = currency + '-' + self.currency)
            worth = round(float(amount) * float(price['amount']), 2)
            if worth < 10:
                continue
            sentence = "{} {} at the value of {} {}".format(amount, currency, worth, price['currency'])
            self.say(sentence)

    def checkPrice(self, *args):
        f_benchmark = open(self.price_benchmark_save_file, 'r+')
        f_limit = open(self.price_limit_save_file, 'r+')
        f_floor = open(self.price_floor_save_file, 'r+')
        reader_limit = csv.reader(f_limit, lineterminator=os.linesep)
        next(reader_limit)
        row_limit = next(reader_limit)
        reader_floor = csv.reader(f_floor, lineterminator=os.linesep)
        next(reader_floor)
        row_floor = next(reader_floor)
        reader_benchmark = csv.reader(f_benchmark, lineterminator=os.linesep)
        header = next(reader_benchmark)
        row_benchmark = next(reader_benchmark)
        for i in range(1, len(header)):
            currency = header[i]
            last_price = float(row_benchmark[i])
            limit = float(row_limit[i])
            floor = float(row_floor[i])
            price = float(self.client.get_spot_price(currency_pair = currency + '-' + self.currency)['amount'])
            if price > limit:
                sentence = "{}'s price of {} has surpassed the set limit of {}".format(currency, price, limit)
                self.say(sentence)
            if price < floor:
                sentence = "{}'s price of {} has broken the set floor of {}".format(currency, price, floor)
                self.say(sentence)
            priceChange = (price - last_price) / last_price
            if priceChange < -self.check_price_fluctuation:
                sentence = "The price of {} has dropped by {}%".format(currency, round(priceChange * -100))
                self.say(sentence)
            elif priceChange > self.check_price_fluctuation:
                sentence = "The price of {} has bumped by {}%".format(currency, round(priceChange * 100))
                self.say(sentence)
        f_benchmark.close()
        f_limit.close()
        f_floor.close()

    def recordPrice(self, *args):
        with open(self.price_benchmark_save_file, 'r+') as f:
            reader = csv.reader(f, lineterminator=os.linesep)
            header = next(reader)
            writer = csv.writer(f, lineterminator=os.linesep)
            entry = [datetime.now().strftime("%a %b %d %H:%M:%S")]          # datetime.strptime(timeStr, "%a %b %d %H:%M:%S")
            entry += [self.client.get_spot_price(currency_pair = currency + '-' + self.currency)['amount'] for currency in header[1:]]
            writer.writerow(entry)
        with open(self.price_benchmark_save_file, 'r') as f:
            data = f.readlines()
            data.insert(1, data[-1])
        with open(self.price_benchmark_save_file, 'w') as f:
            f.writelines(data)

    def timedRun(self, fct, sleepTime, *args):
        while self.running:
            try:
                with sleepTime.get_lock():
                    tmp = sleepTime.value
                time.sleep(tmp)
                fct(args)
            except Exception as err:
                print("===============Error===============")
                print(err)
                with sleepTime.get_lock():
                    tmp = sleepTime.value
                self.say("An error occurred with {}. Trying again in {} minutes".format(fct.__name__, tmp // 60))
                print("===============Error===============")

    def start(self):
        pannounce = Process(target = self.timedRun, args = (self.announceStanding, self.check_standing_interval))
        pannounce.start()
        pcheck = Process(target = self.timedRun, args = (self.checkPrice, self.check_price_interval))
        pcheck.start()
        self.jobs.append(pannounce)
        self.jobs.append(pcheck)
        while self.running:
            cmd = input()
            print("===============Command Line===============")
            args = cmd.split(' ')
            cmd = args[0]
            if cmd == 'python':
                try:
                    command = ' '.join(args[1:])
                    exec(command)
                except Exception as e:
                    print(e)
            elif cmd == 'bash':
                try:
                    command = ' '.join(args[1:])
                    os.system(command)
                except Exception as e:
                    print(e)
            elif cmd == 'record':
                self.recordPrice()
                self.say("Current prices are recorded")
            elif cmd == 'report':
                self.announceStanding()
            elif cmd == 'exit':
                self.say("Quitting the program now...")
                self.running = False
                for job in self.jobs:
                    job.terminate()
            elif cmd == 'updateMonitorFrequency' or cmd == 'umf':
                try:
                    programName = args[1]
                    newFrequency = int(args[2]) * 60
                    if newFrequency <= 0:
                        newFrequency = 365*24*60*60
                    if programName == 'announceStanding':
                        with self.check_standing_interval.get_lock():
                            self.check_standing_interval.value = newFrequency
                    elif programName == 'checkPrice':
                        with self.check_price_interval.get_lock():
                            self.check_price_interval.value = newFrequency
                    else:
                        raise Exception("Incorrect programName")
                    print("Monitor Frequency Updated")
                except Exception:
                    print("usage: updateMonitorFrequency programName newFrequency(in minute)")
                    print("\tprogramName (choose from announceStanding, checkPrice)")
            else:
                print("Instructions:")
                print("\texit - exit and chill")
                print("\trecord - snapshot current prices and reset comparison benchmarks")
                print("\treport - announce current account standing")
                print("\tupdateMonitorFrequency/umf - change the reporting frequency")
                print("More features coming...")
            print("===============Command Line===============")

def main():
    with open('config.json') as config_f:
        config = json.load(config_f)
        APIKEY = config['APIKEY']
        APISECRET = config['APISECRET']
        global BASE_CURRENCY, TRACKED_COINS
        BASE_CURRENCY = config['BASE_CURRENCY']
        TRACKED_COINS = config['TRACKED_COINS']

    monitor = Monitor(APIKEY, APISECRET, BASE_CURRENCY)
    monitor.start()

if __name__ == '__main__':
    main()
