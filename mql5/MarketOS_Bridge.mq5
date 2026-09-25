//+------------------------------------------------------------------+
//|                                             MarketOS_Bridge.mq5  |
//|                         Market-OS Native Cloud Execution Bridge  |
//|                                  https://github.com/Abulamido/   |
//+------------------------------------------------------------------+
#property copyright "Market-OS Team"
#property link      "https://primeedge.app"
#property version   "2.00"
#property strict

#include <Trade\Trade.mqh>

//--- Input Parameters
input string InpServerUrl       = "http://127.0.0.1:8000";       // Market-OS API Server URL
input string InpWorkerKey       = "wkey_master_cloud_london";   // Cloud Worker Auth Key
input string InpWorkerId        = "vps-lon-worker-1";           // Cloud Worker Node ID
input int    InpTimerMs         = 1000;                         // Polling Interval (Milliseconds)
input ulong  InpMagic           = 888001;                       // Expert Advisor Magic Number

//--- Global Objects & State
CTrade    m_trade;
long      m_login;
datetime  m_last_heartbeat;
int       m_timer_ms;

//+------------------------------------------------------------------+
//| Simple JSON Parsing Helpers (Zero-dependency, pure MQL5)         |
//+------------------------------------------------------------------+
string ExtractJsonString(const string json, const string key)
{
   string search = "\"" + key + "\":\"";
   int pos = StringFind(json, search);
   if(pos < 0)
   {
      search = "\"" + key + "\": \"";
      pos = StringFind(json, search);
      if(pos < 0) return "";
   }
   pos += StringLen(search);
   int end_pos = StringFind(json, "\"", pos);
   if(end_pos < 0) return "";
   return StringSubstr(json, pos, end_pos - pos);
}

double ExtractJsonDouble(const string json, const string key)
{
   string search = "\"" + key + "\":";
   int pos = StringFind(json, search);
   if(pos < 0) return 0.0;
   pos += StringLen(search);
   while(pos < StringLen(json) && (StringGetCharacter(json, pos) == ' ' || StringGetCharacter(json, pos) == '\"'))
      pos++;
   int end_pos = pos;
   while(end_pos < StringLen(json))
   {
      ushort ch = StringGetCharacter(json, end_pos);
      if((ch >= '0' && ch <= '9') || ch == '.' || ch == '-')
         end_pos++;
      else
         break;
   }
   return StringToDouble(StringSubstr(json, pos, end_pos - pos));
}

long ExtractJsonLong(const string json, const string key)
{
   string search = "\"" + key + "\":";
   int pos = StringFind(json, search);
   if(pos < 0) return 0;
   pos += StringLen(search);
   while(pos < StringLen(json) && (StringGetCharacter(json, pos) == ' ' || StringGetCharacter(json, pos) == '\"'))
      pos++;
   int end_pos = pos;
   while(end_pos < StringLen(json))
   {
      ushort ch = StringGetCharacter(json, end_pos);
      if(ch >= '0' && ch <= '9')
         end_pos++;
      else
         break;
   }
   return StringToInteger(StringSubstr(json, pos, end_pos - pos));
}

int ExtractOrders(const string json, string &order_objects[])
{
   int start = StringFind(json, "\"orders\":");
   if(start < 0) return 0;
   start = StringFind(json, "[", start);
   if(start < 0) return 0;
   int end = StringFind(json, "]", start);
   if(end <= start) return 0;
   
   string array_body = StringSubstr(json, start + 1, end - start - 1);
   StringTrimLeft(array_body);
   StringTrimRight(array_body);
   if(StringLen(array_body) == 0) return 0;

   int count = 0;
   int cur = 0;
   while(cur < StringLen(array_body))
   {
      int o_start = StringFind(array_body, "{", cur);
      if(o_start < 0) break;
      int o_end = StringFind(array_body, "}", o_start);
      if(o_end < 0) break;
      
      ArrayResize(order_objects, count + 1);
      order_objects[count] = StringSubstr(array_body, o_start, o_end - o_start + 1);
      count++;
      cur = o_end + 1;
   }
   return count;
}

//+------------------------------------------------------------------+
//| HTTP WebRequest Wrapper                                          |
//+------------------------------------------------------------------+
int HttpSend(const string method, const string path_and_query, const string body, string &response_text)
{
   string url = InpServerUrl + path_and_query;
   string headers = "Content-Type: application/json\r\n" +
                    "X-Worker-Id: " + InpWorkerId + "\r\n" +
                    "X-Worker-Key: " + InpWorkerKey + "\r\n";
   
   char post_data[];
   char result_data[];
   string result_headers;
   int body_len = StringLen(body);
   if(body_len > 0)
      StringToCharArray(body, post_data, 0, body_len);
   else
      ArrayResize(post_data, 0);

   ResetLastError();
   int res = WebRequest(method, url, headers, 5000, post_data, result_data, result_headers);
   if(res == -1)
   {
      int err = GetLastError();
      // 4060 means URL not listed in Tools -> Options -> Expert Advisors -> Allow WebRequest
      if(err == 4060)
         PrintFormat("[MarketOS] ERROR: WebRequest URL '%s' not allowed! Add it to MT5 Options -> Expert Advisors.", url);
      else
         PrintFormat("[MarketOS] WebRequest failed. Error code: %d", err);
      return -1;
   }

   response_text = CharArrayToString(result_data);
   return res;
}

//+------------------------------------------------------------------+
//| Broker Symbol Resolution                                         |
//+------------------------------------------------------------------+
string ResolveBrokerSymbol(const string base_symbol)
{
   if(SymbolInfoInteger(base_symbol, SYMBOL_SELECT) || SymbolSelect(base_symbol, true))
   {
      ENUM_SYMBOL_TRADE_MODE mode = (ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(base_symbol, SYMBOL_TRADE_MODE);
      if(mode != SYMBOL_TRADE_MODE_DISABLED) return base_symbol;
   }

   string candidates[10];
   candidates[0] = base_symbol + "m";
   candidates[1] = base_symbol + ".cash";
   candidates[2] = base_symbol + ".pro";
   candidates[3] = base_symbol + ".raw";
   candidates[4] = base_symbol + "c";
   candidates[5] = "m" + base_symbol;
   candidates[6] = base_symbol;
   candidates[7] = "";
   candidates[8] = "";
   candidates[9] = "";

   if(base_symbol == "US100") { candidates[6] = "USTEC"; candidates[7] = "NAS100"; candidates[8] = "USTEC.cash"; candidates[9] = "NAS100.cash"; }
   else if(base_symbol == "XAUUSD") { candidates[6] = "GOLD"; candidates[7] = "XAUUSDm"; candidates[8] = "GOLD.cash"; }

   for(int i = 0; i < 10; i++)
   {
      if(candidates[i] == "") continue;
      if(SymbolSelect(candidates[i], true))
      {
         ENUM_SYMBOL_TRADE_MODE mode = (ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(candidates[i], SYMBOL_TRADE_MODE);
         if(mode != SYMBOL_TRADE_MODE_DISABLED) return candidates[i];
      }
   }
   return base_symbol;
}

//+------------------------------------------------------------------+
//| Normalize Stops for Broker Compliance                            |
//+------------------------------------------------------------------+
void NormalizeStops(const string symbol, const string direction, double price, double &sl, double &tp)
{
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   long stop_level_points = SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double min_distance = (stop_level_points + 5) * point;

   if(direction == "LONG")
   {
      if(sl > 0 && (price - sl) < min_distance)
         sl = price - min_distance;
      if(tp > 0 && (tp - price) < min_distance)
         tp = price + min_distance;
   }
   else if(direction == "SHORT")
   {
      if(sl > 0 && (sl - price) < min_distance)
         sl = price + min_distance;
      if(tp > 0 && (price - tp) < min_distance)
         tp = price - min_distance;
   }

   if(sl > 0) sl = NormalizeDouble(sl, digits);
   if(tp > 0) tp = NormalizeDouble(tp, digits);
}

//+------------------------------------------------------------------+
//| Heartbeat Reporter                                               |
//+------------------------------------------------------------------+
void SendHeartbeat()
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
   double margin  = AccountInfoDouble(ACCOUNT_MARGIN);
   double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);

   string body = StringFormat("{\"login\":%d,\"balance\":%.2f,\"equity\":%.2f,\"margin\":%.2f,\"free_margin\":%.2f}",
                              m_login, balance, equity, margin, free_margin);
   string response;
   HttpSend("POST", "/api/v1/execution/ea/heartbeat", body, response);
   m_last_heartbeat = TimeCurrent();
}

//+------------------------------------------------------------------+
//| Report Fill back to Cloud Router                                 |
//+------------------------------------------------------------------+
void ReportFill(long order_id, const string signal_id, const string symbol, const string direction,
                double volume, double fill_price, double sl, double tp, ulong ticket_id,
                const string status, const string error_comment, int retcode, double latency_ms)
{
   string body = StringFormat(
      "{\"login\":%d,\"order_id\":%d,\"signal_id\":\"%s\",\"instrument\":\"%s\",\"direction\":\"%s\"," +
      "\"volume\":%.2f,\"fill_price\":%.5f,\"sl\":%.5f,\"tp\":%.5f,\"ticket_id\":\"%d\"," +
      "\"status\":\"%s\",\"error_comment\":\"%s\",\"retcode\":%d,\"latency_ms\":%.1f}",
      m_login, order_id, signal_id, symbol, direction, volume, fill_price, sl, tp, ticket_id,
      status, error_comment, retcode, latency_ms
   );
   string response;
   HttpSend("POST", "/api/v1/execution/ea/report-fill", body, response);
}

//+------------------------------------------------------------------+
//| Report Position Close back to Cloud Router                       |
//+------------------------------------------------------------------+
void ReportClose(ulong ticket_id, const string symbol, double exit_price, double profit, const string reason)
{
   string body = StringFormat(
      "{\"login\":%d,\"ticket_id\":\"%d\",\"instrument\":\"%s\",\"exit_price\":%.5f,\"profit\":%.2f,\"exit_reason\":\"%s\"}",
      m_login, ticket_id, symbol, exit_price, profit, reason
   );
   string response;
   HttpSend("POST", "/api/v1/execution/ea/report-close", body, response);
}

//+------------------------------------------------------------------+
//| Poll Orders & Execute                                            |
//+------------------------------------------------------------------+
void PollAndExecuteOrders()
{
   string query = StringFormat("/api/v1/execution/ea/poll-orders?login=%d", m_login);
   string response;
   int status_code = HttpSend("GET", query, "", response);
   if(status_code != 200 || StringLen(response) < 10) return;

   string orders[];
   int count = ExtractOrders(response, orders);
   if(count == 0) return;

   for(int i = 0; i < count; i++)
   {
      string o = orders[i];
      string action = ExtractJsonString(o, "action_type");
      long order_id = ExtractJsonLong(o, "order_id");
      string signal_id = ExtractJsonString(o, "signal_id");
      string raw_symbol = ExtractJsonString(o, "instrument");
      string direction = ExtractJsonString(o, "direction");
      double volume = ExtractJsonDouble(o, "position_size_lots");
      double sl = ExtractJsonDouble(o, "stop_loss");
      double tp = ExtractJsonDouble(o, "take_profit");
      long ticket = ExtractJsonLong(o, "ticket_id");

      string symbol = ResolveBrokerSymbol(raw_symbol);
      SymbolSelect(symbol, true);

      // ── CLOSE ACTION ───────────────────────────────────────────────
      if(action == "CLOSE")
      {
         PrintFormat("[MarketOS] Executing CLOSE for Ticket #%d on %s", ticket, symbol);
         bool closed = m_trade.PositionClose(ticket, 30);
         if(closed)
         {
            PrintFormat("[MarketOS] Ticket #%d CLOSED successfully.", ticket);
            ReportClose(ticket, symbol, m_trade.ResultPrice(), 0.0, "SIGNAL_CLOSE");
         }
         else
         {
            int err = (int)m_trade.ResultRetcode();
            // If already closed or not found, report as already closed
            PrintFormat("[MarketOS] Ticket #%d Close returned retcode %d. Reporting closed.", ticket, err);
            ReportClose(ticket, symbol, 0.0, 0.0, "ALREADY_CLOSED");
         }
         continue;
      }

      // ── OPEN ACTION ────────────────────────────────────────────────
      PrintFormat("[MarketOS] Executing OPEN %s %.2f lots on %s (Signal: %s)", direction, volume, symbol, signal_id);

      MqlTick tick;
      if(!SymbolInfoTick(symbol, tick))
      {
         PrintFormat("[MarketOS] ERROR: No tick available for %s", symbol);
         ReportFill(order_id, signal_id, symbol, direction, volume, 0.0, sl, tp, 0, "REJECTED", "No tick data", 10006, 0.0);
         continue;
      }

      double price = (direction == "LONG") ? tick.ask : tick.bid;
      NormalizeStops(symbol, direction, price, sl, tp);

      uint start_tick = GetTickCount();
      bool ok = false;
      if(direction == "LONG")
         ok = m_trade.Buy(volume, symbol, price, sl, tp, "PE-" + StringSubstr(signal_id, 0, 10));
      else
         ok = m_trade.Sell(volume, symbol, price, sl, tp, "PE-" + StringSubstr(signal_id, 0, 10));

      double latency_ms = (double)(GetTickCount() - start_tick);

      if(ok && m_trade.ResultRetcode() == TRADE_RETCODE_DONE)
      {
         ulong executed_ticket = m_trade.ResultOrder();
         double fill_price = m_trade.ResultPrice();
         PrintFormat("[MarketOS] Trade EXECUTED! Ticket: #%d @ %.5f (Latency: %.1f ms)", executed_ticket, fill_price, latency_ms);
         ReportFill(order_id, signal_id, symbol, direction, volume, fill_price, sl, tp, executed_ticket, "FILLED", "", 10009, latency_ms);
      }
      else
      {
         string err_comment = m_trade.ResultComment();
         int retcode = (int)m_trade.ResultRetcode();
         PrintFormat("[MarketOS] Trade REJECTED by broker: %s (code: %d)", err_comment, retcode);
         ReportFill(order_id, signal_id, symbol, direction, volume, price, sl, tp, 0, "REJECTED", err_comment, retcode, latency_ms);
      }
   }
}

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   m_login = AccountInfoInteger(ACCOUNT_LOGIN);
   m_timer_ms = (InpTimerMs < 200) ? 200 : InpTimerMs;

   m_trade.SetExpertMagicNumber(InpMagic);
   m_trade.SetDeviationInPoints(30);

   PrintFormat("==========================================================");
   PrintFormat("  Market-OS Native Cloud Execution Bridge ACTIVE          ");
   PrintFormat("  Account Login: #%d | Server: %s", m_login, AccountInfoString(ACCOUNT_SERVER));
   PrintFormat("  Cloud API: %s | Poll Interval: %d ms", InpServerUrl, m_timer_ms);
   PrintFormat("==========================================================");

   EventSetMillisecondTimer(m_timer_ms);
   SendHeartbeat();
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   PrintFormat("[MarketOS] Bridge deinitialized (Reason: %d)", reason);
}

//+------------------------------------------------------------------+
//| Expert timer function                                            |
//+------------------------------------------------------------------+
void OnTimer()
{
   PollAndExecuteOrders();

   if(TimeCurrent() - m_last_heartbeat >= 30)
      SendHeartbeat();
}

//+------------------------------------------------------------------+
//| Trade transaction listener (Instant SL/TP/Closure Capture)       |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   // Capture closed deals (DEAL_ENTRY_OUT)
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD)
   {
      ulong deal_ticket = trans.deal;
      if(deal_ticket > 0 && HistoryDealSelect(deal_ticket))
      {
         ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal_ticket, DEAL_ENTRY);
         if(entry == DEAL_ENTRY_OUT)
         {
            ulong pos_id = HistoryDealGetInteger(deal_ticket, DEAL_POSITION_ID);
            double profit = HistoryDealGetDouble(deal_ticket, DEAL_PROFIT);
            double price  = HistoryDealGetDouble(deal_ticket, DEAL_PRICE);
            string symbol = HistoryDealGetString(deal_ticket, DEAL_SYMBOL);
            string comment = HistoryDealGetString(deal_ticket, DEAL_COMMENT);

            string reason = "MANUAL";
            if(StringFind(comment, "sl") >= 0 || StringFind(comment, "so") >= 0) reason = "STOP_LOSS";
            else if(StringFind(comment, "tp") >= 0) reason = "TAKE_PROFIT";

            PrintFormat("[MarketOS] Position #%d CLOSED via %s! Realized PnL: $%.2f", pos_id, reason, profit);
            ReportClose(pos_id, symbol, price, profit, reason);
         }
      }
   }
}
//+------------------------------------------------------------------+
