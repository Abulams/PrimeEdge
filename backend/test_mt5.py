import sys
sys.path.insert(0, 'C:\\Market-OS\\backend')
import MetaTrader5 as mt5

result = mt5.initialize(login=5054957055, password='Lamido556@', server='MetaQuotes-Demo')
if result:
    acc = mt5.account_info()
    if acc:
        print('CONNECTED_OK')
        print('Login: ' + str(acc.login))
        print('Balance: ' + str(acc.balance) + ' ' + str(acc.currency))
        print('Equity: ' + str(acc.equity) + ' ' + str(acc.currency))
        print('Leverage: 1:' + str(acc.leverage))
        print('Server: ' + str(acc.server))
    else:
        print('AUTH_FAILED: ' + str(mt5.last_error()))
else:
    print('INIT_FAILED: ' + str(mt5.last_error()))
mt5.shutdown()
