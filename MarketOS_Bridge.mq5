//+------------------------------------------------------------------+
//| Market OS Execution Bridge EA                                     |
//| Listens on TCP port 9999 for trade commands from Market OS       |
//+------------------------------------------------------------------+
#property copyright "Market OS"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

CTrade trade;
int server_socket = INVALID_HANDLE;
int port = 9999;

int OnInit()
{
    server_socket = SocketCreate();
    if(server_socket == INVALID_HANDLE) {
        Print("Market OS Bridge: Failed to create socket");
        return INIT_FAILED;
    }
    
    if(!SocketListen(server_socket, "0.0.0.0", port, 10)) {
        Print("Market OS Bridge: Failed to listen on port ", port);
        SocketClose(server_socket);
        return INIT_FAILED;
    }
    
    Print("✅ Market OS Bridge: Listening on port ", port);
    EventSetMillisecondTimer(100);
    return INIT_SUCCEEDED;
}

void OnTimer()
{
    int client = SocketAccept(server_socket);
    if(client == INVALID_HANDLE) return;
    
    string request = "";
    char buf[];
    ArrayResize(buf, 4096);
    int len = SocketRead(client, buf, 4096, 100);
    if(len > 0) {
        request = CharArrayToString(buf, 0, len);
        Print("Market OS Bridge: Received: ", request);
        
        string response = ProcessCommand(request);
        
        char resp[];
        StringToCharArray(response, resp, 0, StringLen(response));
        SocketSend(client, resp, ArraySize(resp) - 1);
    }
    
    SocketClose(client);
}

string ProcessCommand(string json)
{
    // Parse: {"action":"buy","symbol":"EURUSD","volume":0.1,"sl":1.0800,"tp":1.0950}
    string action = JsonGetString(json, "action");
    string symbol = JsonGetString(json, "symbol");
    double volume = JsonGetDouble(json, "volume");
    double sl     = JsonGetDouble(json, "sl");
    double tp     = JsonGetDouble(json, "tp");
    
    if(symbol == "") symbol = Symbol();
    if(volume <= 0) volume = 0.01;
    
    bool result = false;
    string ticket = "";
    
    if(action == "buy") {
        result = trade.Buy(volume, symbol, 0, sl, tp, "MarketOS");
        ticket = IntegerToString(trade.ResultOrder());
    } else if(action == "sell") {
        result = trade.Sell(volume, symbol, 0, sl, tp, "MarketOS");
        ticket = IntegerToString(trade.ResultOrder());
    } else if(action == "close") {
        ulong t = (ulong)JsonGetDouble(json, "ticket");
        result = trade.PositionClose(t);
        ticket = IntegerToString(t);
    } else if(action == "ping") {
        double bal = AccountInfoDouble(ACCOUNT_BALANCE);
        double eq  = AccountInfoDouble(ACCOUNT_EQUITY);
        long   login = AccountInfoInteger(ACCOUNT_LOGIN);
        string server = AccountInfoString(ACCOUNT_SERVER);
        return "{\"status\":\"ok\",\"login\":" + IntegerToString(login) + 
               ",\"balance\":" + DoubleToString(bal, 2) + 
               ",\"equity\":" + DoubleToString(eq, 2) + 
               ",\"server\":\"" + server + "\"}";
    }
    
    if(result)
        return "{\"status\":\"ok\",\"ticket\":\"" + ticket + "\"}";
    else
        return "{\"status\":\"error\",\"code\":" + IntegerToString(GetLastError()) + "}";
}

string JsonGetString(string json, string key)
{
    string pattern = "\"" + key + "\":\"";
    int start = StringFind(json, pattern);
    if(start < 0) return "";
    start += StringLen(pattern);
    int end = StringFind(json, "\"", start);
    if(end < 0) return "";
    return StringSubstr(json, start, end - start);
}

double JsonGetDouble(string json, string key)
{
    string pattern = "\"" + key + "\":";
    int start = StringFind(json, pattern);
    if(start < 0) return 0;
    start += StringLen(pattern);
    int end = start;
    while(end < StringLen(json) && (StringGetCharacter(json,end) == '.' || 
          (StringGetCharacter(json,end) >= '0' && StringGetCharacter(json,end) <= '9'))) end++;
    return StringToDouble(StringSubstr(json, start, end - start));
}

void OnDeinit(const int reason)
{
    if(server_socket != INVALID_HANDLE) {
        SocketClose(server_socket);
        Print("Market OS Bridge: Stopped");
    }
}

void OnTick() {}
//+------------------------------------------------------------------+
