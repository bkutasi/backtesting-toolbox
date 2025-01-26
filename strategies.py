import backtrader as bt
import backtrader.analyzers as btanalyzers
import pandas as pd
import datetime as dt
from backtrader.indicators import (
    Indicator,
    MovAv,
    RelativeStrengthIndex,
    Highest,
    Lowest,
)


class SuperTrendBand(bt.Indicator):
    """
    Helper inidcator for Supertrend indicator
    """

    params = (("period", 7), ("multiplier", 3))
    lines = ("basic_ub", "basic_lb", "final_ub", "final_lb")

    def __init__(self):
        self.atr = bt.indicators.AverageTrueRange(period=self.p.period)
        self.l.basic_ub = ((self.data.high + self.data.low) / 2) + (
            self.atr * self.p.multiplier
        )
        self.l.basic_lb = ((self.data.high + self.data.low) / 2) - (
            self.atr * self.p.multiplier
        )

    def next(self):
        if len(self) - 1 == self.p.period:
            self.l.final_ub[0] = self.l.basic_ub[0]
            self.l.final_lb[0] = self.l.basic_lb[0]
        else:
            # =IF(OR(basic_ub<final_ub*,close*>final_ub*),basic_ub,final_ub*)
            if (
                self.l.basic_ub[0] < self.l.final_ub[-1]
                or self.data.close[-1] > self.l.final_ub[-1]
            ):
                self.l.final_ub[0] = self.l.basic_ub[0]
            else:
                self.l.final_ub[0] = self.l.final_ub[-1]

            # =IF(OR(baisc_lb > final_lb *, close * < final_lb *), basic_lb *, final_lb *)
            if (
                self.l.basic_lb[0] > self.l.final_lb[-1]
                or self.data.close[-1] < self.l.final_lb[-1]
            ):
                self.l.final_lb[0] = self.l.basic_lb[0]
            else:
                self.l.final_lb[0] = self.l.final_lb[-1]


class SuperTrend(bt.Indicator):
    """
    Super Trend indicator
    """

    params = (("period", 7), ("multiplier", 3))
    lines = ("super_trend",)
    plotinfo = dict(subplot=False)

    def __init__(self):
        self.stb = SuperTrendBand(period=self.p.period, multiplier=self.p.multiplier)

    def next(self):
        if len(self) - 1 == self.p.period:
            self.l.super_trend[0] = self.stb.final_ub[0]
            return

        if self.l.super_trend[-1] == self.stb.final_ub[-1]:
            if self.data.close[0] <= self.stb.final_ub[0]:
                self.l.super_trend[0] = self.stb.final_ub[0]
            else:
                self.l.super_trend[0] = self.stb.final_lb[0]

        if self.l.super_trend[-1] == self.stb.final_lb[-1]:
            if self.data.close[0] >= self.stb.final_lb[0]:
                self.l.super_trend[0] = self.stb.final_lb[0]
            else:
                self.l.super_trend[0] = self.stb.final_ub[0]


class StochasticRSI(Indicator):
    """
          K - The time period to be used in calculating the %K. 3 is the default.
          D - The time period to be used in calculating the %D. 3 is the default.
          RSI Length - The time period to be used in calculating the RSI
          Stochastic Length - The time period to be used in calculating the Stochastic

          Formula:
    #       %K = SMA(100 * (RSI(n) - RSI Lowest Low(n)) / (RSI HighestHigh(n) - RSI LowestLow(n)), smoothK)
    #       %D = SMA(%K, periodD)

    """

    lines = (
        "fastk",
        "fastd",
    )

    params = (
        ("k_period", 3),
        ("d_period", 3),
        ("rsi_period", 14),
        ("stoch_period", 14),
        ("movav", MovAv.Simple),
        ("rsi", RelativeStrengthIndex),
        ("upperband", 80.0),
        ("lowerband", 20.0),
    )

    plotlines = dict(percD=dict(_name="%D", ls="--"), percK=dict(_name="%K"))

    def _plotlabel(self):
        plabels = [
            self.p.k_period,
            self.p.d_period,
            self.p.rsi_period,
            self.p.stoch_period,
        ]
        plabels += [self.p.movav] * self.p.notdefault("movav")
        return plabels

    def _plotinit(self):
        self.plotinfo.plotyhlines = [self.p.upperband, self.p.lowerband]

    def __init__(self):
        rsi_hh = Highest(
            self.p.rsi(period=self.p.rsi_period), period=self.p.stoch_period
        )
        rsi_ll = Lowest(
            self.p.rsi(period=self.p.rsi_period), period=self.p.stoch_period
        )
        knum = self.p.rsi(period=self.p.rsi_period) - rsi_ll
        kden = rsi_hh - rsi_ll

        self.k = self.p.movav(100.0 * (knum / kden), period=self.p.k_period)
        self.d = self.p.movav(self.k, period=self.p.d_period)

        self.lines.fastk = self.k
        self.lines.fastd = self.d


class CrossoverStochRSI(bt.Strategy):

    params = (
        ("rsi_period", 14),
        ("stoch_k_period", 3),
        ("stoch_d_period", 3),
        ("stoch_rsi_period", 14),
        ("stoch_period", 14),
        ("stoch_upperband", 80.0),
        ("stoch_lowerband", 20.0),
        ("take_profit", 0.08),
        ("stop_loss", 0.04),
        ("size", 20),
        ("debug", False),
    )

    def __init__(self):
        self.stoch = StochasticRSI(
            k_period=self.p.stoch_k_period,
            d_period=self.p.stoch_d_period,
            rsi_period=self.p.stoch_rsi_period,
            stoch_period=self.p.stoch_period,
            upperband=self.p.stoch_upperband,
            lowerband=self.p.stoch_lowerband,
        )

        self.crossover = bt.ind.CrossOver(self.stoch.l.fastk, self.stoch.l.fastd)

    def next(self):
        if not self.position:
            close = self.data.close[0]
            price1 = close
            price2 = price1 - self.p.stop_loss * close
            price3 = price1 + self.p.take_profit * close

            if self.stoch.l.fastk[0] < 20 and self.crossover > 0:
                self.buy_bracket(
                    price=price1,
                    stopprice=price2,
                    limitprice=price3,
                    exectype=bt.Order.Limit,
                )

            if self.stoch.l.fastk[0] > 80 and self.crossover < 0:
                self.sell_bracket(
                    price=price1,
                    stopprice=price3,
                    limitprice=price2,
                    exectype=bt.Order.Limit,
                )


class TripleSupertrend(bt.Strategy):
    params = (
        ("EMA_length", 200),
        ("ATR_fast_length", 10),
        ("ATR_mid_length", 11),
        ("ATR_slow_length", 12),
        ("take_profit", 0.08),
        ("stop_loss", 0.04),
    )

    def log(self, txt, dt=None):
        """Logging function for this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print("%s, %s" % (dt.isoformat(), txt))

    def __init__(self):
        # Triple supertrend indicator + EMA
        Supertrend_fast = SuperTrend(period=self.params.ATR_fast_length, multiplier=1)
        Supertrend_mid = SuperTrend(period=self.params.ATR_mid_length, multiplier=2)
        self.Supertrend_slow = SuperTrend(
            period=self.params.ATR_slow_length, multiplier=3
        )
        self.EMA = bt.ind.EMA(period=self.params.EMA_length)

        # StochRSI indicator, sRSI is just SMA applied over rsi of length 14 + stoch
        self.stoch = StochasticRSI()

        self.crossover = bt.ind.CrossOver(self.stoch.l.fastk, self.stoch.l.fastd)

        self.dataclose = self.datas[0].close

    def next(self):
        if not self.position:
            close = self.data.close[0]
            price1 = close
            price2 = price1 - self.p.stop_loss * close
            price3 = price1 + self.p.take_profit * close

            if (
                self.stoch.l.fastk[0] < 20
                and self.crossover > 0
                and self.EMA < close
                and close < self.Supertrend_slow
            ):
                self.buy_bracket(
                    price=price1,
                    stopprice=price2,
                    limitprice=price3,
                    exectype=bt.Order.Limit,
                )

            if (
                self.stoch.l.fastk[0] > 80
                and self.crossover < 0
                and self.EMA > close
                and close > self.Supertrend_slow
            ):
                self.sell_bracket(
                    price=price1,
                    stopprice=price3,
                    limitprice=price2,
                    exectype=bt.Order.Limit,
                )


class MaCross(bt.Strategy):
    params = (("fast_length", 50), ("slow_length", 200))

    def log(self, txt, dt=None):
        """Logging function fot this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print("%s, %s" % (dt.isoformat(), txt))

    def __init__(self):

        self.ma_fast = bt.ind.SMA(period=self.params.fast_length)
        self.ma_slow = bt.ind.SMA(period=self.params.slow_length)
        self.EMA_1k = bt.ind.EMA(period=1000)
        self.rsi = bt.ind.RSI(upperband=80.0, lowerband=20.0)
        self.dataclose = self.datas[0].close
        self.crossover = bt.ind.CrossOver(self.ma_fast, self.ma_slow)
        self.crossover_ma_slow_1k = bt.ind.CrossOver(self.ma_slow, self.EMA_1k)
        # self.lastbar = self.dataclose[-20000]

    def next(self):
        if not self.position:
            if self.crossover > 0 and self.dataclose > self.EMA_1k:
                self.buy()
                self.log("BUY CREATE, %.2f" % self.dataclose[0])
            """if self.crossover_ma_slow_1k < 0:
              self.sell()
              self.log('SOLD CREATE, %.2f' % self.dataclose[0])"""
        elif self.crossover < 0:
            self.close()


class TripleEMaStrategy(bt.Strategy):

    params = (
        ("stop_loss", 0.05),
        ("trail", False),
        ("buy_limit", False),
        ("fast_length", 50),
        ("mid_length", 200),
        ("slow_length", 500),
    )

    buy_order = None  # default value for a potential buy_order

    def log(self, txt, dt=None):
        """Logging function for this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print("%s, %s" % (dt.isoformat(), txt))

    def __init__(self):
        self.ma_fast = bt.ind.SMA(period=self.params.fast_length)
        self.ma_mid = bt.ind.SMA(period=self.params.mid_length)
        self.ma_slow = bt.ind.SMA(period=self.params.slow_length)
        self.HMA1k = bt.ind.HMA(period=1000)
        self.EMA1k = bt.ind.EMA(period=1000)
        self.rsi = bt.ind.RelativeStrengthIndex()
        self.dataclose = self.datas[0].close
        self.crossover = bt.ind.CrossOver(self.ma_fast, self.ma_slow)
        self.crossover_mid = bt.ind.CrossOver(self.ma_fast, self.ma_mid)

    def notify_order(self, order):
        if order.status == order.Cancelled:
            print(
                "CANCEL@price: {:.2f} {}".format(
                    order.executed.price, "buy" if order.isbuy() else "sell"
                )
            )
            return

        if not order.status == order.Completed:
            return  # discard any other notification

        if not self.position:  # we left the market
            print("SELL@price: {:.2f}".format(order.executed.price))
            return

        # We have entered the market
        print("BUY @price: {:.2f}".format(order.executed.price))

    """def next(self):

        if not self.position and self.ma_fast > self.ma_mid and self.ma_mid > self.ma_slow:
            if self.buy_order:  # something was pending
                self.cancel(self.buy_order)

            # not in the market and signal triggered
            if not self.p.buy_limit:
                self.buy_order = self.buy(transmit=False)
            else:
                price = self.data.close[0] * (1.0 - self.p.buy_limit)

                # transmit = False ... await child order before transmission
                self.buy_order = self.buy(price=price, exectype=bt.Order.Limit,
                                          transmit=False)

            # Setting parent=buy_order ... sends both together
            if not self.p.trail:
                stop_price = self.data.close[0] * (1.0 - self.p.stop_loss)
                self.sell(exectype=bt.Order.Stop, price=stop_price,
                          parent=self.buy_order)
            else:
                self.sell(exectype=bt.Order.StopTrail,
                          trailamount=self.p.trail,
                          parent=self.buy_order)"""

    def next(self):
        if not self.position:
            if self.crossover > 0 and self.dataclose > self.EMA1k:
                self.buy()
                # self.log('BUY CREATE, %.2f' % self.dataclose[0])
        elif self.crossover_mid < 0 or self.dataclose < self.HMA1k:
            self.close()


class MaCross(bt.Strategy):
    params = (("fast_length", 50), ("slow_length", 200))

    def log(self, txt, dt=None):
        """Logging function fot this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print("%s, %s" % (dt.isoformat(), txt))

    def __init__(self):

        self.ma_fast = bt.ind.SMA(period=self.params.fast_length)
        self.ma_slow = bt.ind.SMA(period=self.params.slow_length)
        self.EMA_1k = bt.ind.EMA(period=1000)
        self.rsi = bt.ind.RSI(upperband=80.0, lowerband=20.0)
        self.dataclose = self.datas[0].close
        self.crossover = bt.ind.CrossOver(self.ma_fast, self.ma_slow)
        self.crossover_ma_slow_1k = bt.ind.CrossOver(self.ma_slow, self.EMA_1k)
        # self.lastbar = self.dataclose[-20000]

    def next(self):
        if not self.position:
            if self.crossover > 0 and self.dataclose > self.EMA_1k:
                self.buy()
                self.log("BUY CREATE, %.2f" % self.dataclose[0])
            """if self.crossover_ma_slow_1k < 0:
              self.sell()
              self.log('SOLD CREATE, %.2f' % self.dataclose[0])"""
        elif self.crossover < 0:
            self.close()
