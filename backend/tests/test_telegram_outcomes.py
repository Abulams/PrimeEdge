import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import patch, MagicMock
from app.telegram_service import TelegramService


def test_telegram_outcome_alert_formatting():
    mock_setup = MagicMock()
    mock_setup.instrument = "GBPUSD"
    mock_setup.direction = "LONG"
    mock_setup.setup_ref_price = 1.29450

    mock_trade = MagicMock()
    mock_trade.setup = mock_setup
    mock_trade.instrument = "GBPUSD"
    mock_trade.direction = "LONG"
    mock_trade.actual_entry = 1.29450
    mock_trade.exit_price = 1.29810
    mock_trade.exit_reason = "TAKE_PROFIT"
    mock_trade.outcome = "WIN"
    mock_trade.pnl_pips = 36.0
    mock_trade.pnl_r = 1.80
    mock_trade.max_mae_pips = 4.2
    mock_trade.max_mfe_pips = 39.0

    with patch.object(TelegramService, "send_message_async") as mock_send:
        TelegramService.send_outcome_alert(mock_trade)
        assert mock_send.called
        msg = mock_send.call_args[0][0]
        assert "SETUP RESOLVED: GBPUSD LONG" in msg
        assert "TARGET REACHED" in msg
        assert "+1.80 R" in msg
        assert "36.0 pips" in msg
        assert "1.29450" in msg
        assert "1.29810" in msg


def test_telegram_outcome_alert_early_inval():
    mock_setup = MagicMock()
    mock_setup.instrument = "XAUUSD"
    mock_setup.direction = "SHORT"
    mock_setup.setup_ref_price = 2735.50

    mock_trade = MagicMock()
    mock_trade.setup = mock_setup
    mock_trade.instrument = "XAUUSD"
    mock_trade.direction = "SHORT"
    mock_trade.actual_entry = 2735.50
    mock_trade.exit_price = 2739.00
    mock_trade.exit_reason = "EARLY_INVALIDATION_MAE"
    mock_trade.outcome = "LOSS"
    mock_trade.pnl_pips = -35.0
    mock_trade.pnl_r = -0.35
    mock_trade.max_mae_pips = 35.0
    mock_trade.max_mfe_pips = 5.0

    with patch.object(TelegramService, "send_message_async") as mock_send:
        TelegramService.send_outcome_alert(mock_trade)
        assert mock_send.called
        msg = mock_send.call_args[0][0]
        assert "SETUP RESOLVED: XAUUSD SHORT" in msg
        assert "EARLY INVALIDATION" in msg
        assert "-0.35 R" in msg


def test_telegram_daily_digest_empty():
    mock_db = MagicMock()
    mock_query = mock_db.query.return_value
    mock_options = mock_query.options.return_value
    mock_filter = mock_options.filter.return_value
    mock_filter.order_by.return_value.all.return_value = []

    with patch.object(TelegramService, "send_message_async") as mock_send:
        success = TelegramService.send_daily_digest(mock_db)
        assert success is True
        assert mock_send.called
        msg = mock_send.call_args[0][0]
        assert "PRIMEEDGE DAILY DECISION DIGEST" in msg
        assert "No setups reached resolution in the last 24 hours" in msg


if __name__ == "__main__":
    test_telegram_outcome_alert_formatting()
    test_telegram_outcome_alert_early_inval()
    test_telegram_daily_digest_empty()
    print("All Telegram outcome alert tests passed!")
