# -*- encoding: utf-8 -*-

import json


from jaqs.util import fileio
from jaqs.trade import model
from jaqs.data.basic.order import Order
from jaqs.trade import common
from jaqs.data.dataservice import RemoteDataService
from jaqs.trade.strategy import EventDrivenStrategy
from jaqs.trade.backtest import EventBacktestInstance
from jaqs.trade.gateway import BacktestTradeApi


class CtaStrategy(EventDrivenStrategy):
    def __init__(self):
        EventDrivenStrategy.__init__(self)
        self.symbol = ''
    
    def init_from_config(self, props):
        self.symbol = props.get('symbol')
        self.init_balance = props.get('init_balance')
    
    def on_cycle(self):
        pass
    
    def on_quote(self, quote):
        # quote.show()
        
        time = quote.time
        if time == 100000:
            order = Order()
            order.entrust_action = common.ORDER_ACTION.BUY
            order.order_type = common.ORDER_TYPE.LIMIT
            order.entrust_date = quote.trade_date
            order.entrust_time = quote.time
            order.symbol = quote.symbol
            order.entrust_size = 10000
            order.entrust_price = quote.close
            self.ctx.gateway.send_order(order, '', '')
            print 'send order %s: %s %s %f' % (order.entrust_no, order.symbol, order.entrust_action, order.entrust_price)
        if time == 140000:
            order = Order()
            order.entrust_action = common.ORDER_ACTION.SELL
            order.order_type = common.ORDER_TYPE.LIMIT
            order.entrust_date = quote.trade_date
            order.entrust_time = quote.time
            order.symbol = quote.symbol
            order.entrust_size = 5000
            order.entrust_price = quote.close
            self.ctx.gateway.send_order(order, '', '')
            print 'send order %s: %s %s %f' % (order.entrust_no, order.symbol, order.entrust_action, order.entrust_price)
    

def test_cta():
    prop_file_path = fileio.join_relative_path("etc/backtest.json")
    print prop_file_path
    prop_file = open(prop_file_path, 'r')
    
    props = json.load(prop_file)
    
    enum_props = {'bar_type': common.QUOTE_TYPE}
    for k, v in enum_props.iteritems():
        props[k] = v.to_enum(props[k])
    
    strategy = CtaStrategy()
    gateway = BacktestTradeApi()
    data_service = RemoteDataService()
    
    context = model.Context()
    
    backtest = EventBacktestInstance()
    backtest.init_from_config(props, strategy, context=context)
    
    backtest.run()
    report = backtest.generate_report(output_format="plot")


if __name__ == "__main__":
    test_cta()
    print "test success."
