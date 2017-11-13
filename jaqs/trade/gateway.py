# encoding: UTF-8

from abc import abstractmethod
import abc
from six import with_metaclass
import copy
from collections import defaultdict

import numpy as np

from jaqs.data.basic.order import *
from jaqs.data.basic.position import Position
from jaqs.data.basic.trade import Trade
from jaqs.util.sequence import SequenceGenerator
import jaqs.util as jutil
from jaqs.trade.event import EVENT_TYPE, EventEngine, Event
from jaqs.trade.tradeapi import TradeApi
from jaqs.data.basic import OrderRsp, OrderStatusInd, Trade, TaskInd, Task, TaskRsp


'''
class TradeCallback(with_metaclass(abc.ABCMeta)):
    @abstractmethod
    def on_trade(self, ind):
        pass
    
    @abstractmethod
    def on_order_status(self, ind):
        pass
    
    @abstractmethod
    def on_order_rsp(self, rsp):
        pass

'''


class BaseTradeApi(object):
    def __init__(self):
        self._ordstatus_callback = None
        self._taskstatus_callback = None
        self._trade_callback = None
        self._on_connection_callback = None
        
        self.ctx = None
        
    def set_connection_callback(self, callback):
        self._on_connection_callback = callback
    
    def set_ordstatus_callback(self, callback):
        self._ordstatus_callback = callback
    
    def set_trade_callback(self, callback):
        self._trade_callback = callback
    
    def set_task_callback(self, callback):
        self._taskstatus_callback = callback
    
    def place_order(self, symbol, action, price, size, algo="", algo_param={}, userdata=""):
        """
        return (result, message)
        if result is None, message contains error information
        """
        pass
    
    def place_batch_order(self, orders, algo="", algo_param={}, userdata=""):
        """
        orders format:
            [ {"symbol": "000001.SZ", "action": "Buy", "price": 10.0, "size" : 100}, ... ]
        return (result, message)
        if result is None, message contains error information
        """
        pass
    
    def cancel_order(self, task_id):
        """
        return (result, message)
        if result is None, message contains error information
        """
        pass
    
    def query_account(self, format=""):
        """
            return pd.dataframe
        """
        pass
    
    def query_position(self, mode = "all", securities = "", format=""):
        """
            securities: seperate by ","
            return pd.dataframe
        """
        pass
    
    def query_net_position(self, mode = "all", securities = "", format=""):
        """
            securities: seperate by ","
            return pd.dataframe
        """
        pass
    
    def query_task(self, task_id = -1, format=""):
        """
            task_id: -1 -- all
            return pd.dataframe
        """
        pass
    
    def query_order(self, task_id = -1, format=""):
        """
            task_id: -1 -- all
            return pd.dataframe
        """
        pass
    
    def query_trade(self, task_id = -1, format=""):
        """
            task_id: -1 -- all
            return pd.dataframe
        """
        pass
    
    def query_portfolio(self, format=""):
        """
            return pd.dataframe
        """
        pass
    
    def goal_portfolio(self, positions, algo="", algo_param={}, userdata=""):
        """
        positions format:
            [ {"symbol": "000001.SZ", "ref_price": 10.0, "size" : 100}, ...]
        return (result, message)
        if result is None, message contains error information
        """
        pass
    
    def basket_order(self, orders, algo="", algo_param={}, userdata=""):
        """
        orders format:
            [ {"symbol": "000001.SZ", "ref_price": 10.0, "inc_size" : 100}, ...]
        return (result, message)
        if result is None, message contains error information
        """
        pass
    
    def stop_portfolio(self):
        """
        return (result, message)
        if result is None, message contains error information
        """
        pass
    
    def query_universe(self, format=""):
        pass


class RealTimeTradeApi(BaseTradeApi):
    def __init__(self):
        super(RealTimeTradeApi, self).__init__()
        
        self.seq_gen = SequenceGenerator()

    def _get_next_num(self, key):
        """used to generate id for orders and trades."""
        return str(np.int64(self.ctx.trade_date) * 10000 + self.seq_gen.get_next(key))
    
    def _get_next_task_no(self):
        return self._get_next_num('task_no')
    
    # ----------------------------------------------------------------------------------------
    # place & cancel
    
    def place_order(self, symbol, action, price, size, algo="", algo_param=None, userdata=""):
        if algo_param is None:
            algo_param = dict()
        
        # this order object is not for TradeApi, but for strategy itself to remember the order
        order = Order.new_order(symbol, action, price, size, self.ctx.trade_date, 0)
        order.entrust_no = self._get_next_num('entrust_no')
        
        task = Task(self._get_next_task_no(),
                    algo=algo, algo_param=algo_param,
                    data=order,
                    function_name="place_order")
        self.ctx.pm.add_task(task)
        # self.task_id_map[order.task_id].append(order.entrust_no)
        
        # self.pm.add_order(order)
        
        e = Event(EVENT_TYPE.PLACE_ORDER)
        e.dic['task'] = task
        self.ctx.gateway.put(e)
    
    def cancel_order(self, entrust_no):
        e = Event(EVENT_TYPE.CANCEL_ORDER)
        e.dic['entrust_no'] = entrust_no
        self.ctx.gateway.put(e)
    
    # ----------------------------------------------------------------------------------------
    # PMS
    
    def goal_portfolio(self, positions, algo="", algo_param=None, userdata=""):
        if algo_param is None:
            algo_param = dict()
        
        task = Task(self._get_next_task_no(), data=positions,
                    algo=algo, algo_param=algo_param,
                    function_name="goal_portfolio")
        self.ctx.pm.add_task(task)
        
        e = Event(EVENT_TYPE.GOAL_PORTFOLIO)
        e.dic['task'] = task
        self.ctx.gateway.put(e)
    
    # ----------------------------------------------------------------------------------------
    # query account, universe, position, portfolio
    
    def query_account(self, userdata=""):
        args = locals()
        e = Event(EVENT_TYPE.QUERY_ACCOUNT)
        e.dic['args'] = args
    
    def query_universe(self, userdata=""):
        args = locals()
        e = Event(EVENT_TYPE.QUERY_UNIVERSE)
        e.dic['args'] = args
    
    def query_position(self, mode="all", symbols="", userdata=""):
        args = locals()
        e = Event(EVENT_TYPE.QUERY_POSITION)
        e.dic['args'] = args
    
    def query_portfolio(self, userdata=""):
        args = locals()
        e = Event(EVENT_TYPE.QUERY_PORTFOLIO)
        e.dic['args'] = args
    
    # ----------------------------------------------------------------------------------------
    # query task, order, trade
    
    def query_task(self, task_id=-1, userdata=""):
        args = locals()
        e = Event(EVENT_TYPE.QUERY_TASK)
        e.dic['args'] = args
    
    def query_order(self, task_id=-1, userdata=""):
        args = locals()
        e = Event(EVENT_TYPE.QUERY_ORDER)
        e.dic['args'] = args
    
    def query_trade(self, task_id=-1, userdata=""):
        args = locals()
        e = Event(EVENT_TYPE.QUERY_TRADE)
        e.dic['args'] = args


'''
class BaseGateway(object):
    """
    Strategy communicates with Gateway using APIs defined by ourselves;
    Gateway communicates with brokers using brokers' APIs;
    Gateway can also communicate with simulator.
    
    Attributes
    ----------
    ctx : Context
        Trading context, including data_api, dataview, calendar, etc.

    Notes
    -----
    Gateway knows nothing about task_id but entrust_no, so does Simulator.

    """
    
    def __init__(self):
        super(BaseGateway, self).__init__()
        
        self.ctx = None
    
    @abstractmethod
    def init_from_config(self, props):
        pass
    
    def register_context(self, context=None):
        self.ctx = context
    
    def on_new_day(self, trade_date):
        pass
    
'''


class RealGateway(EventEngine):
    """
    Attributes
    ----------
    trade_api : TradeApi
    
    """
    def __init__(self):
        super(RealGateway, self).__init__()
        
        self.ctx = None
        
        self.trade_api = None
        self.init_from_config({})

        # event types and trade_api functions are one-to-one corresponded
        self.omni_api_map = {EVENT_TYPE.QUERY_ACCOUNT: self.trade_api.query_account,
                             EVENT_TYPE.QUERY_UNIVERSE: self.trade_api.query_universe,
                             EVENT_TYPE.QUERY_POSITION: self.trade_api.query_position,
                             EVENT_TYPE.QUERY_PORTFOLIO: self.trade_api.query_portfolio,
                             EVENT_TYPE.QUERY_TASK: self.trade_api.query_task,
                             EVENT_TYPE.QUERY_TRADE: self.trade_api.query_trade,
                             EVENT_TYPE.QUERY_ORDER: self.trade_api.query_order,
                             }
        
        self.task_no_id_map = dict()
        
    def init_from_config(self, props):
        """
        Instantiate TradeAPI and login.
        
        Parameters
        ----------
        props : dict

        """
        if self.trade_api is not None:
            self.trade_api.close()
    
        def get_from_list_of_dict(l, key, default=None):
            res = None
            for dic in l:
                res = dic.get(key, None)
                if res is not None:
                    break
            if res is None:
                res = default
            return res
    
        props_default = jutil.read_json(jutil.join_relative_path('etc/trade_config.json'))
        dic_list = [props, props_default]
    
        address = get_from_list_of_dict(dic_list, "remote.address", "")
        username = get_from_list_of_dict(dic_list, "remote.username", "")
        password = get_from_list_of_dict(dic_list, "remote.password", "")
        if address is None or username is None or password is None:
            raise ValueError("no address, username or password available!")
    
        tapi = TradeApi(address)
        self.set_trade_api_callbacks(tapi)

        # 使用用户名、密码登陆， 如果成功，返回用户可用的策略帐号列表
        print("{}@{} login...".format(username, address))
        user_info, msg = tapi.login(username, password)
        print("Login msg: {:s}".format(msg))
        print("Login user info: {:s}".format(user_info))
        print()
        self.trade_api = tapi
    
    # -------------------------------------------------------------------------------------------
    # On TradeAPI Callback: put a corresponding event to RealInstance
    
    def on_connection_callback(self, connected):
        """
        
        Parameters
        ----------
        connected : bool

        """
        if connected:
            print("TradeAPI connected.")
            event_type = EVENT_TYPE.TRADE_API_CONNECTED
        else:
            print("TradeAPI disconnected.")
            event_type = EVENT_TYPE.TRADE_API_DISCONNECTED
        e = Event(event_type)
        self.ctx.instance.put(e)

    def set_trade_api_callbacks(self, trade_api):
        trade_api.set_task_callback(self.on_task_status)
        trade_api.set_ordstatus_callback(self.on_order_status)
        trade_api.set_trade_callback(self.on_trade)
        trade_api.set_connection_callback(self.on_connection_callback)

    def on_trade(self, ind_dic):
        """
        
        Parameters
        ----------
        ind_dic : dict

        """
        # print("\nGateway on trade: ")
        # print(ind_dic)
        if 'security' in ind_dic:
            ind_dic['symbol'] = ind_dic.pop('security')
        
        ind = Trade.create_from_dict(ind_dic)
        ind.task_no = self.task_no_id_map[ind.task_id]
        
        e = Event(EVENT_TYPE.TRADE_IND)
        e.dic['ind'] = ind
        self.ctx.instance.put(e)

    def on_order_status(self, ind_dic):
        """
        
        Parameters
        ----------
        ind_dic : dict

        """
        # print("\nGateway on order status: ")
        # print(ind_dic)
        if 'security' in ind_dic:
            ind_dic['symbol'] = ind_dic.pop('security')
        
        ind = OrderStatusInd.create_from_dict(ind_dic)
        ind.task_no = self.task_no_id_map[ind.task_id]
        
        e = Event(EVENT_TYPE.ORDER_STATUS_IND)
        e.dic['ind'] = ind
        self.ctx.instance.put(e)
        
    def on_task_status(self, ind_dic):
        # print("\nGateway on task ind: ")
        # print(ind_dic)
        ind = TaskInd.create_from_dict(ind_dic)
        ind.task_no = self.task_no_id_map[ind.task_id]

        e = Event(EVENT_TYPE.TASK_STATUS_IND)
        e.dic['ind'] = ind
        self.ctx.instance.put(e)

    # -------------------------------------------------------------------------------------------
    # Run
    def run(self):
        """
        Listen to certain events and run the EventEngine.
        Events include:
            1. placement & cancellation of orders
            2. query of universe, account, position and portfolio
            3. etc.

        """
        for e_type in self.omni_api_map.keys():
            self.register(e_type, self.on_omni_call)
        
        self.register(EVENT_TYPE.PLACE_ORDER, self.on_place_order)
        self.register(EVENT_TYPE.CANCEL_ORDER, self.on_omni_call)
        self.register(EVENT_TYPE.GOAL_PORTFOLIO, self.on_goal_portfolio)
        
        self.start(timer=False)
        
    def on_omni_call(self, event):
        func = self.omni_api_map.get(event.type_, None)
        if func is None:
            print("{} not recgonized. Ignore.".format(event))
            return
        
        args = event.dic.get('args', None)
        func(args)
    
    def _generate_on_task_rsp(self, task_no, task_id, msg):
        # this rsp is generated by gateway itself
        rsp = TaskRsp(task_no=task_no, task_id=task_id, msg=msg)
        if rsp.success:
            self.task_no_id_map[task_id] = task_no
    
        # DEBUG
        print("\nGateway generate task_rsp {}".format(rsp))
        e = Event(EVENT_TYPE.TASK_RSP)
        e.dic['rsp'] = rsp
        self.ctx.instance.put(e)
        
    def on_goal_portfolio(self, event):
        task = event.dic['task']
        positions = task.data
        
        # TODO: compatibility
        for dic in positions:
            dic['symbol'] = dic.pop('security')
        
        task_id, msg = self.trade_api.goal_portfolio(positions, algo=task.algo, algo_param=task.algo_param)
        
        self._generate_on_task_rsp(task.task_no, task_id, msg)
    
    def on_place_order(self, event):
        task = event.dic['task']
        order = task.data
        task_id, msg = self.trade_api.place_order(order.symbol, order.entrust_action,
                                                  order.entrust_price, order.entrust_size,
                                                  task.algo, task.algo_param)
        
        self._generate_on_task_rsp(task.task_no, task_id, msg)


# ---------------------------------------------
# For Alpha Strategy

class DailyStockSimGateway(object):
    def __init__(self):
        super(DailyStockSimGateway, self).__init__()
        self.ctx = None
        
        self.simulator = DailyStockSimulator()
    
    def init_from_config(self, props):
        pass
    
    def on_new_day(self, trade_date):
        self.simulator.on_new_day(trade_date)

    def on_after_market_close(self):
        self.simulator.on_after_market_close()
    
    def place_order(self, order):
        err_msg = self.simulator.add_order(order)
        return err_msg
    
    def cancel_order(self, entrust_no):
        order_status_ind, err_msg = self.simulator.cancel_order(entrust_no)
        self.cb_on_order_status(order_status_ind)
        return err_msg
    
    @property
    def match_finished(self):
        return self.simulator.match_finished
    
    @abstractmethod
    def match(self, price_dict, time=0):
        """
        Match un-fill orders in simulator. Return trade indications.

        Parameters
        ----------
        price_dict : dict
        time : int
        # TODO: do we need time parameter?

        Returns
        -------
        list

        """
        return self.simulator.match(price_dict, date=self.ctx.trade_date, time=time)


class DailyStockSimulator(object):
    """This is not event driven!

    Attributes
    ----------
    __orders : list of Order
        Store orders that have not been filled.

    """
    
    def __init__(self):
        # TODO heap is better for insertion and deletion. We only need implement search of heapq module.
        self.__orders = dict()
        self.seq_gen = SequenceGenerator()
        
        self.date = 0
        self.time = 0
    
    def on_new_day(self, trade_date):
        self.date = trade_date
    
    def on_after_market_close(self):
        # self._refresh_orders() #TODO sometimes we do not want to refresh (multi-days match)
        pass
    
    def _refresh_orders(self):
        self.__orders.clear()
    
    def _next_fill_no(self):
        return str(np.int64(self.date) * 10000 + self.seq_gen.get_next('fill_no'))
    
    @property
    def match_finished(self):
        return len(self.__orders) == 0
    
    @staticmethod
    def _validate_order(order):
        # TODO to be enhanced
        assert order is not None
    
    @staticmethod
    def _validate_price(price_dic):
        # TODO to be enhanced
        assert price_dic is not None
    
    def add_order(self, order):
        """
        Add one order to the simulator.

        Parameters
        ----------
        order : Order

        Returns
        -------
        err_msg : str
            default ""

        """
        self._validate_order(order)
        
        if order.entrust_no in self.__orders:
            err_msg = "order with entrust_no {} already exists in simulator".format(order.entrust_no)
        self.__orders[order.entrust_no] = order
        err_msg = ""
        return err_msg
    
    def cancel_order(self, entrust_no):
        """
        Cancel an order.

        Parameters
        ----------
        entrust_no : str

        Returns
        -------
        err_msg : str
            default ""

        """
        popped = self.__orders.pop(entrust_no, None)
        if popped is None:
            err_msg = "No order with entrust_no {} in simulator.".format(entrust_no)
            order_status_ind = None
        else:
            err_msg = ""
            order_status_ind = OrderStatusInd()
            order_status_ind.init_from_order(popped)
            order_status_ind.order_status = common.ORDER_STATUS.CANCELLED
        return order_status_ind, err_msg
    
    def match(self, price_dic, date=19700101, time=150000):
        self._validate_price(price_dic)
        
        results = []
        for order in self.__orders.values():
            symbol = order.symbol
            symbol_dic = price_dic[symbol]
            
            # get fill price
            if isinstance(order, FixedPriceTypeOrder):
                price_target = order.price_target
                fill_price = symbol_dic[price_target]
            elif isinstance(order, VwapOrder):
                if order.start != -1:
                    raise NotImplementedError("Vwap of a certain time range")
                fill_price = symbol_dic['vwap']
            elif isinstance(order, Order):
                # TODO
                fill_price = symbol_dic['close']
            else:
                raise NotImplementedError("order class {} not support!".format(order.__class__))
            
            # get fill size
            fill_size = order.entrust_size - order.fill_size
            
            # create trade indication
            trade_ind = Trade()
            trade_ind.init_from_order(order)
            trade_ind.send_fill_info(fill_price, fill_size,
                                     date, time,
                                     self._next_fill_no())
            results.append(trade_ind)
            
            # update order status
            order.fill_price = (order.fill_price * order.fill_size
                                + fill_price * fill_size) / (order.fill_size + fill_size)
            order.fill_size += fill_size
            if order.fill_size == order.entrust_size:
                order.order_status = common.ORDER_STATUS.FILLED
        
        self.__orders = {k: v for k, v in self.__orders.viewitems() if not v.is_finished}
        # self.cancel_order(order.entrust_no)  # TODO DEBUG
        
        return results


# ---------------------------------------------
# For Event-driven Strategy

class OrderBook(object):
    def __init__(self):
        self.orders = []
        self.trade_id = 0
        self.order_id = 0
        
        self.seq_gen = SequenceGenerator()
    
    def next_trade_id(self):
        return self.seq_gen.get_next('trade_id')
    
    def next_order_id(self):
        return self.seq_gen.get_next('order_id')
    
    def add_order(self, order):
        neworder = Order()
        # to do
        order.entrust_no = self.next_order_id()
        neworder = copy.copy(order)
        self.orders.append(neworder)
    
    def make_tick_trade(self, quote):
        raise NotImplementedError()
    
    def make_trade(self, quote, freq):
        
        if freq == common.QUOTE_TYPE.TICK:
            # TODO
            return self.make_tick_trade(quote)
        
        elif (freq == common.QUOTE_TYPE.MIN
              or freq == common.QUOTE_TYPE.FIVEMIN
              or freq == common.QUOTE_TYPE.QUARTERMIN
              or freq == common.QUOTE_TYPE.SPECIALBAR):
            return self._make_trade_bar(quote)
        
        elif freq == common.QUOTE_TYPE.DAILY:
            return self._make_trade_bar(quote)
    
    def _make_trade_bar(self, quote_dic):
        
        result = []
        # to be optimized
        for order in self.orders:
            if order.is_finished:
                continue
    
            quote = quote_dic[order.symbol]
            low = quote.low
            high = quote.high
            quote_date = quote.trade_date
            quote_time = quote.time
            quote_symbol = quote.symbol
        
            if order.order_type == common.ORDER_TYPE.LIMIT:
                if order.entrust_action == common.ORDER_ACTION.BUY and order.entrust_price >= low:
                    trade = Trade()
                    trade.init_from_order(order)
                    trade.send_fill_info(order.entrust_price, order.entrust_size,
                                         quote_date, quote_time,
                                         self.next_trade_id())
                    
                    order.order_status = common.ORDER_STATUS.FILLED
                    order.fill_size = trade.fill_size
                    order.fill_price = trade.fill_price
                    
                    orderstatus_ind = OrderStatusInd()
                    orderstatus_ind.init_from_order(order)
                    
                    trade.task_no = order.task_no
                    orderstatus_ind.task_no = order.task_no
                    result.append((trade, orderstatus_ind))
                    
                elif order.entrust_action == common.ORDER_ACTION.SELL and order.entrust_price <= high:
                    trade = Trade()
                    trade.init_from_order(order)
                    trade.send_fill_info(order.entrust_price, order.entrust_size,
                                         quote_date, quote_time,
                                         self.next_trade_id())
                    
                    order.order_status = common.ORDER_STATUS.FILLED
                    order.fill_size = trade.fill_size
                    order.fill_price = trade.fill_price
                    
                    orderstatus_ind = OrderStatusInd()
                    orderstatus_ind.init_from_order(order)

                    trade.task_no = order.task_no
                    orderstatus_ind.task_no = order.task_no

                    trade.task_no = order.task_no
                    orderstatus_ind.task_no = order.task_no
                    result.append((trade, orderstatus_ind))
            
            elif order.order_type == common.ORDER_TYPE.STOP:
                if order.entrust_action == common.ORDER_ACTION.BUY and order.entrust_price <= high:
                    trade = Trade()
                    trade.init_from_order(order)
                    trade.send_fill_info(order.entrust_price, order.entrust_size,
                                         quote_date, quote_time,
                                         self.next_trade_id())
                    
                    order.order_status = common.ORDER_STATUS.FILLED
                    order.fill_size = trade.fill_size
                    order.fill_price = trade.fill_price
                    orderstatus_ind = OrderStatusInd()
                    orderstatus_ind.init_from_order(order)
                    result.append((trade, orderstatus_ind))
                
                if order.entrust_action == common.ORDER_ACTION.SELL and order.entrust_price >= low:
                    trade = Trade()
                    trade.init_from_order(order)
                    trade.send_fill_info(order.entrust_price, order.entrust_size,
                                         quote_date, quote_time,
                                         self.next_trade_id())
                    
                    order.order_status = common.ORDER_STATUS.FILLED
                    order.fill_size = trade.fill_size
                    order.fill_price = trade.fill_price
                    orderstatus_ind = OrderStatusInd()
                    orderstatus_ind.init_from_order(order)
                    result.append((trade, orderstatus_ind))
        
        return result
    
    def cancel_order(self, entrust_no):
        for i in xrange(len(self.orders)):
            order = self.orders[i]
            
            if (order.is_finished):
                continue
            
            if (order.entrust_no == entrust_no):
                order.cancel_size = order.entrust_size - order.fill_size
                order.order_status = common.ORDER_STATUS.CANCELLED
            
            # todo
            orderstatus = OrderStatusInd()
            orderstatus.init_from_order(order)
            
            return orderstatus
    
    def cancel_all(self):
        result = []
        for order in self.orders:
            if order.is_finished:
                continue
            order.cancel_size = order.entrust_size - order.fill_size
            order.order_status = common.ORDER_STATUS.CANCELLED
            
            # todo
            orderstatus = OrderStatusInd()
            orderstatus.init_from_order(order)
            result.append(orderstatus)
        
        return result


class BacktestTradeApi(BaseTradeApi):
    def __init__(self):
        super(BacktestTradeApi, self).__init__()
        
        self.ctx = None
        
        self._orderbook = OrderBook()
        self.seq_gen = SequenceGenerator()

    def _get_next_num(self, key):
        """used to generate id for orders and trades."""
        return str(np.int64(self.ctx.trade_date) * 10000 + self.seq_gen.get_next(key))

    def _get_next_task_no(self):
        return self._get_next_num('task_no')
    
    def init_from_config(self, props):
        pass

    def on_new_day(self, trade_date):
        self._orderbook = OrderBook()
    
    def place_order(self, security, action, price, size, algo="", algo_param={}, userdata=""):
        order = Order.new_order(security, action, price, size, self.ctx.trade_date, self.ctx.time,
                                order_type=common.ORDER_TYPE.LIMIT)
        order.entrust_no = self._get_next_num('entrust_no')
        
        task_no = self._get_next_task_no()
        order.task_no = task_no
        
        task = Task(task_no,
                    algo=algo, algo_param=algo_param, data=order,
                    function_name='place_order')

        self.ctx.pm.add_task(task)
        
        self._orderbook.add_order(order)
        
        rsp = OrderRsp(order.entrust_no, task_id=1, msg="")
        self.ctx.instance.strategy.on_order_rsp(rsp)

    def _process_quote(self, df_quote, freq):
        return self._orderbook.make_trade(df_quote, freq)
    
    '''
    def send_order(self, order, algo, param):
        self.orderbook.add_order(order)
        # TODO: no consistence between backtest and real time trading
        rsp = OrderRsp(order.entrust_no, task_id=1, msg="")
        if rsp.task_id:
            self.ctx.instance.strategy.pm.add_order(order)
        self.ctx.instance.strategy.on_order_rsp(rsp)
    
    '''
