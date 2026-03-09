import heapq
import time
from datetime import datetime
from typing import List, Tuple, Optional
from backend.app.models.types import Order, OrderSide, Trade, OrderStatus, MarketDepth

class OrderBook:
    def __init__(self, symbol: str):
        self.symbol = symbol
        # Bids: Max-Heap (stored as negative for Python's min-heap behavior)
        self.bids: List[Tuple[float, float, int, Order]] = [] 
        # Asks: Min-Heap
        self.asks: List[Tuple[float, float, int, Order]] = []
        self.trades: List[Trade] = []
        self.last_price: Optional[float] = None
        self._seq = 0  # Unique sequence counter to break heap ties

    def add_order(self, order: Order) -> List[Trade]:
        if order.side == OrderSide.BUY:
            new_trades = self._match_buy_order(order)
        else:
            new_trades = self._match_sell_order(order)
        
        self.trades.extend(new_trades)
        return new_trades

    def _match_buy_order(self, order: Order) -> List[Trade]:
        trades = []
        skipped = []
        while order.quantity > order.filled_quantity and self.asks:
            best_ask_price, _, _, best_ask = self.asks[0]
            
            if order.price < best_ask_price: # Limit not met
                break

            # Skip self-trades
            if best_ask.agent_id == order.agent_id:
                skipped.append(heapq.heappop(self.asks))
                continue

            # Match
            trade_qty = min(order.quantity - order.filled_quantity, best_ask.quantity - best_ask.filled_quantity)
            self._execute_trade(order, best_ask, trade_qty, best_ask_price, trades)

            if best_ask.status == OrderStatus.FILLED:
                heapq.heappop(self.asks)

        # Re-insert skipped orders
        for entry in skipped:
            heapq.heappush(self.asks, entry)

        if order.quantity > order.filled_quantity:
            # Push with negative price for Max-Heap, seq as tiebreaker
            self._seq += 1
            ts = (order.timestamp or datetime.now()).timestamp()
            heapq.heappush(self.bids, (-order.price, ts, self._seq, order))
        
        return trades

    def _match_sell_order(self, order: Order) -> List[Trade]:
        trades = []
        skipped = []
        while order.quantity > order.filled_quantity and self.bids:
            neg_best_bid_price, _, _, best_bid = self.bids[0]
            best_bid_price = -neg_best_bid_price
            
            if order.price > best_bid_price: # Limit not met
                break

            # Skip self-trades
            if best_bid.agent_id == order.agent_id:
                skipped.append(heapq.heappop(self.bids))
                continue

            # Match
            trade_qty = min(order.quantity - order.filled_quantity, best_bid.quantity - best_bid.filled_quantity)
            self._execute_trade(order, best_bid, trade_qty, best_bid_price, trades)

            if best_bid.status == OrderStatus.FILLED:
                heapq.heappop(self.bids)

        # Re-insert skipped orders
        for entry in skipped:
            heapq.heappush(self.bids, entry)

        if order.quantity > order.filled_quantity:
            self._seq += 1
            ts = (order.timestamp or datetime.now()).timestamp()
            heapq.heappush(self.asks, (order.price, ts, self._seq, order))

        return trades

    def _execute_trade(self, taker: Order, maker: Order, quantity: int, price: float, trade_list: List[Trade]):
        taker.filled_quantity += quantity
        maker.filled_quantity += quantity
        self.last_price = price
        
        taker.status = OrderStatus.FILLED if taker.filled_quantity >= taker.quantity else OrderStatus.PARTIALLY_FILLED
        maker.status = OrderStatus.FILLED if maker.filled_quantity >= maker.quantity else OrderStatus.PARTIALLY_FILLED

        trade = Trade(
            trade_id=f"t_{int(time.time()*1000000)}",
            buy_order_id=taker.id if taker.side == OrderSide.BUY else maker.id,
            sell_order_id=taker.id if taker.side == OrderSide.SELL else maker.id,
            buyer_agent_id=taker.agent_id if taker.side == OrderSide.BUY else maker.agent_id,
            seller_agent_id=taker.agent_id if taker.side == OrderSide.SELL else maker.agent_id,
            stock_symbol=self.symbol,
            price=price,
            quantity=quantity
        )
        trade_list.append(trade)

    def update_price(self, price: float, day: int = 0, session: int = 0):
        """Update price from external random walk (no trade needed)"""
        self.last_price = price

    def get_depth(self, level: int = 10):
        # Snapshot of the book
        # Note: In a real system, we would group by price here.
        # Simple snapshot for now.
        bids_snap = []
        for p, t, s, o in sorted(self.bids):
             qty = o.quantity - o.filled_quantity
             if qty > 0:
                 bids_snap.append(MarketDepth(price=-p, quantity=qty))
        
        asks_snap = []
        for p, t, s, o in sorted(self.asks):
            qty = o.quantity - o.filled_quantity
            if qty > 0:
                asks_snap.append(MarketDepth(price=p, quantity=qty))

        return {"bids": bids_snap[:level], "asks": asks_snap[:level]}
