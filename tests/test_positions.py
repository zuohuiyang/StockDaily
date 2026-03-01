import unittest

from stock.calc.positions import compute_positions_fifo


class TestFifo(unittest.TestCase):
    def test_fifo_realized_and_remaining(self):
        txs = [
            {"trade_time": "2026-01-01T10:00:00", "code": "AAA", "side": "BUY", "quantity": 10, "price": 10, "currency": "USD", "fee": 1, "fx_rate": None},
            {"trade_time": "2026-01-02T10:00:00", "code": "AAA", "side": "BUY", "quantity": 10, "price": 12, "currency": "USD", "fee": 0, "fx_rate": None},
            {"trade_time": "2026-01-03T10:00:00", "code": "AAA", "side": "SELL", "quantity": 12, "price": 11, "currency": "USD", "fee": 2, "fx_rate": None},
        ]
        pos = compute_positions_fifo(txs)["AAA"]
        self.assertAlmostEqual(pos.quantity, 8.0)
        self.assertAlmostEqual(pos.lots[0].quantity, 8.0)
        self.assertAlmostEqual(pos.lots[0].unit_cost, 12.0)
        realized = (12 * 11 - 2) - (10 * 10.1 + 2 * 12)
        self.assertAlmostEqual(pos.realized_pnl, realized)


if __name__ == "__main__":
    unittest.main()
