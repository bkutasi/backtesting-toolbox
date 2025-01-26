# -*- coding: utf-8 -*-
"""BTCUSD - MovingAverage strategy"""

import os
import requests
import backtrader as bt
from strategies import MaCross, TripleSupertrend, CrossoverStochRSI, TripleEMaStrategy
import backtrader.analyzers as btanalyzers
import json
import pandas as pd
import datetime as dt
import argparse
import matplotlib.pyplot as plt
import pickle


class DataHandler:
    def __init__(
        self,
        data_file="btc_price_data.pkl",
        symbol="BTCUSDT",
        interval="1h",
        start_date=dt.datetime(2019, 1, 1),
        end_date=dt.datetime(2022, 5, 1),
    ):
        self.data_file = data_file
        self.symbol = symbol
        self.interval = interval
        self.start_date = start_date
        self.end_date = end_date

    def load_or_fetch_data(self):
        """Load cached data or fetch new data from Binance"""
        if os.path.exists(self.data_file):
            print("Loading cached price data...")
            with open(self.data_file, "rb") as f:
                return pickle.load(f)

        print("Fetching new price data...")
        df_list = []
        last_datetime = self.start_date

        while True:
            new_df = self.get_binance_bars(
                self.symbol, self.interval, last_datetime, self.end_date
            )
            if new_df is None:
                break
            df_list.append(new_df)
            last_datetime = max(new_df.index) + dt.timedelta(hours=1)

        df = pd.concat(df_list)

        # Save data for future runs
        with open(self.data_file, "wb") as f:
            pickle.dump(df, f)

        return df

    @staticmethod
    def get_binance_bars(symbol, interval, startTime, endTime):
        """Fetch historical price data from Binance API"""
        url = "https://api.binance.com/api/v3/klines"

        startTime = str(int(startTime.timestamp() * 1000))
        endTime = str(int(endTime.timestamp() * 1000))
        limit = "1000"

        req_params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": startTime,
            "endTime": endTime,
            "limit": limit,
        }
        a = json.loads(requests.get(url, params=req_params).text)
        df = pd.DataFrame(a)

        if len(df.index) == 0:
            return None

        df = df.iloc[:, 0:6]
        df.columns = ["datetime", "open", "high", "low", "close", "volume"]

        df.open = df.open.astype("float")
        df.high = df.high.astype("float")
        df.low = df.low.astype("float")
        df.close = df.close.astype("float")
        df.volume = df.volume.astype("float")

        df["adj_close"] = df["close"]
        df.index = [dt.datetime.fromtimestamp(x / 1000.0) for x in df.datetime]

        return df


class BacktestRunner:
    def __init__(self, args, strategy_name):
        self.args = args
        self.strategy_name = strategy_name
        self.cerebro = bt.Cerebro()
        self.data_handler = DataHandler()

    def setup_cerebro(self, df):
        data = bt.feeds.PandasData(dataname=df)
        self.cerebro.adddata(data)
        if self.strategy_name == "MaCross":
            self.cerebro.addstrategy(MaCross)
        elif self.strategy_name == "TripleSupertrend":
            self.cerebro.addstrategy(TripleSupertrend)
        elif self.strategy_name == "CrossoverStochRSI":
            self.cerebro.addstrategy(CrossoverStochRSI)
        elif self.strategy_name == "TripleEMaStrategy":
            self.cerebro.addstrategy(TripleEMaStrategy)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy_name}")
        self.cerebro.broker.setcash(1000)
        self.cerebro.addsizer(bt.sizers.PercentSizer, percents=100)
        self.cerebro.addanalyzer(btanalyzers.SharpeRatio, _name="sharpe")
        self.cerebro.addanalyzer(btanalyzers.DrawDown, _name="drawdown")
        self.cerebro.addanalyzer(btanalyzers.Returns, _name="returns")
        self.cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name="trade_analyzer")

    def run_backtest(self):
        return self.cerebro.run()

    def analyze_results(self, results):
        strat = results[0]
        print("Final Portfolio Value: %.2f" % self.cerebro.broker.getvalue())
        print("\n--- Strategy Analysis ---")

        # Calculate winrate
        trade_analysis = strat.analyzers.trade_analyzer.get_analysis()
        if "won" in trade_analysis and "total" in trade_analysis.won:
            won_trades = trade_analysis.won.total
        else:
            won_trades = 0
        if "lost" in trade_analysis and "total" in trade_analysis.lost:
            lost_trades = trade_analysis.lost.total
        else:
            lost_trades = 0

        if won_trades + lost_trades > 0:
            winrate = won_trades / (won_trades + lost_trades)
        else:
            winrate = 0

        print("Winrate: %.2f%%" % (winrate * 100))
        print("Sharpe Ratio:", strat.analyzers.sharpe.get_analysis()["sharperatio"])
        print(
            "Max Drawdown: %.2f%%"
            % strat.analyzers.drawdown.get_analysis()["max"]["drawdown"]
        )
        print(
            "Total Return: %.2f%%"
            % (strat.analyzers.returns.get_analysis()["rtot"] * 100)
        )

    def plot_results(self):
        if self.args.plot:
            plt.rcParams["figure.figsize"] = [40, 20]
            plt.rcParams["savefig.dpi"] = 300
            figure = self.cerebro.plot(style="candlebars", iplot=False)[0][0]
            if self.args.save_plot:
                figure.savefig("btc_strategy_plot.png", bbox_inches="tight")
                print("Plot saved to btc_strategy_plot.png")
        elif self.args.save_plot:
            print("Cannot save plot when --no-plot is specified.")

    def run(self):
        df = self.data_handler.load_or_fetch_data()
        self.setup_cerebro(df)
        results = self.run_backtest()
        self.analyze_results(results)
        self.plot_results()


def main():
    parser = argparse.ArgumentParser(
        description="Backtesting script with plot options."
    )
    parser.add_argument(
        "--no-plot",
        dest="plot",
        action="store_false",
        help="Disable plotting the chart.",
    )
    parser.add_argument(
        "--save-plot",
        dest="save_plot",
        action="store_true",
        help="Save the plot to a file (btc_strategy_plot.png).",
    )
    parser.add_argument(
        "--strategy",
        dest="strategy_name",
        default="MaCross",
        choices=[
            "MaCross",
            "TripleSupertrend",
            "CrossoverStochRSI",
            "TripleEMaStrategy",
        ],
        help="Name of the strategy to use.",
    )
    parser.set_defaults(plot=True)
    args = parser.parse_args()

    if args.plot and args.save_plot:
        args.save_plot = True
    else:
        args.save_plot = False

    runner = BacktestRunner(args, args.strategy_name)
    runner.run()


if __name__ == "__main__":
    main()
