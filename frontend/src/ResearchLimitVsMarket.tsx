import React from 'react';
const motion = { div: ({ initial, animate, transition, children, ...props }: any) => <div {...props}>{children}</div> };

const ResearchLimitVsMarket: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Hero Section */}
      <div className="bg-gradient-to-b from-blue-900 to-slate-900 py-20 px-4">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h1 className="text-5xl md:text-6xl font-bold mb-6">
              Limit Orders vs Market Orders: Which Actually Performs Better?
            </h1>
            <p className="text-xl text-gray-300 mb-8">
              A 5-year analysis of 158 real trades across 6 instruments
            </p>
            <div className="flex gap-4 text-sm">
              <span className="bg-blue-600 px-3 py-1 rounded-full">Research</span>
              <span className="bg-green-600 px-3 py-1 rounded-full">Data-Driven</span>
              <span className="bg-purple-600 px-3 py-1 rounded-full">Transparent</span>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Executive Summary */}
      <div className="max-w-4xl mx-auto px-4 py-16">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="bg-slate-800 rounded-2xl p-8 mb-12"
        >
          <h2 className="text-3xl font-bold mb-6 text-blue-400">Executive Summary</h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-slate-700 rounded-xl p-6">
              <div className="text-4xl font-bold text-green-400 mb-2">27.3%</div>
              <div className="text-gray-300">Limit order win rate</div>
            </div>
            <div className="bg-slate-700 rounded-xl p-6">
              <div className="text-4xl font-bold text-red-400 mb-2">17.9%</div>
              <div className="text-gray-300">Market order win rate</div>
            </div>
            <div className="bg-slate-700 rounded-xl p-6">
              <div className="text-4xl font-bold text-green-400 mb-2">+1.04 pips</div>
              <div className="text-gray-300">Limit order avg PnL</div>
            </div>
            <div className="bg-slate-700 rounded-xl p-6">
              <div className="text-4xl font-bold text-red-400 mb-2">-6,248 pips</div>
              <div className="text-gray-300">Market order avg PnL</div>
            </div>
          </div>
          <p className="mt-6 text-lg text-gray-300">
            <strong className="text-green-400">Conclusion:</strong> Limit orders outperform market orders by 52% in win rate and over 6,000 pips in average PnL.
          </p>
        </motion.div>

        {/* Methodology */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mb-12"
        >
          <h2 className="text-3xl font-bold mb-6">Methodology</h2>
          <div className="bg-slate-800 rounded-2xl p-8">
            <ul className="space-y-4 text-gray-300">
              <li>• <strong>Sample:</strong> 158 trade records from production database</li>
              <li>• <strong>Period:</strong> 5 years of historical data</li>
              <li>• <strong>Instruments:</strong> XAUUSD, GBPUSD, EURUSD, AUDUSD, USDJPY, US100</li>
              <li>• <strong>Entry types compared:</strong> MARKET (134 trades) vs LIMIT (22 trades)</li>
              <li>• <strong>Metrics:</strong> Win rate, average PnL, MAE, MFE, unfilled rate</li>
            </ul>
          </div>
        </motion.div>

        {/* Data Analysis */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="mb-12"
        >
          <h2 className="text-3xl font-bold mb-6">Win Rate Comparison</h2>
          <div className="bg-slate-800 rounded-2xl p-8">
            <div className="mb-8">
              <div className="flex justify-between mb-2">
                <span className="text-green-400 font-bold">Limit Orders</span>
                <span className="text-green-400 font-bold">27.3%</span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-4">
                <div className="bg-green-500 h-4 rounded-full" style={{ width: '27.3%' }}></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-red-400 font-bold">Market Orders</span>
                <span className="text-red-400 font-bold">17.9%</span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-4">
                <div className="bg-red-500 h-4 rounded-full" style={{ width: '17.9%' }}></div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* By Instrument */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mb-12"
        >
          <h2 className="text-3xl font-bold mb-6">Performance by Instrument</h2>
          <div className="bg-slate-800 rounded-2xl p-8">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-600">
                  <th className="py-3 px-4">Instrument</th>
                  <th className="py-3 px-4">Market Win Rate</th>
                  <th className="py-3 px-4">Limit Win Rate</th>
                  <th className="py-3 px-4">Winner</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-slate-700">
                  <td className="py-3 px-4">XAUUSD</td>
                  <td className="py-3 px-4 text-red-400">32.8%</td>
                  <td className="py-3 px-4 text-green-400">100%</td>
                  <td className="py-3 px-4 text-green-400 font-bold">LIMIT</td>
                </tr>
                <tr className="border-b border-slate-700">
                  <td className="py-3 px-4">EURUSD</td>
                  <td className="py-3 px-4 text-red-400">4.0%</td>
                  <td className="py-3 px-4 text-green-400">100%</td>
                  <td className="py-3 px-4 text-green-400 font-bold">LIMIT</td>
                </tr>
                <tr className="border-b border-slate-700">
                  <td className="py-3 px-4">GBPUSD</td>
                  <td className="py-3 px-4 text-red-400">7.4%</td>
                  <td className="py-3 px-4 text-green-400">33.3%</td>
                  <td className="py-3 px-4 text-green-400 font-bold">LIMIT</td>
                </tr>
                <tr className="border-b border-slate-700">
                  <td className="py-3 px-4">AUDUSD</td>
                  <td className="py-3 px-4 text-red-400">6.2%</td>
                  <td className="py-3 px-4 text-green-400">50.0%</td>
                  <td className="py-3 px-4 text-green-400 font-bold">LIMIT</td>
                </tr>
                <tr>
                  <td className="py-3 px-4">US100</td>
                  <td className="py-3 px-4 text-red-400">0.0%</td>
                  <td className="py-3 px-4 text-red-400">0.0%</td>
                  <td className="py-3 px-4 text-gray-400">TIE</td>
                </tr>
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* Analysis */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mb-12"
        >
          <h2 className="text-3xl font-bold mb-6">Why Limit Orders Outperform</h2>
          <div className="bg-slate-800 rounded-2xl p-8 space-y-6">
            <div>
              <h3 className="text-xl font-bold text-blue-400 mb-2">1. Price Improvement</h3>
              <p className="text-gray-300">
                Limit orders only fill at or better than your specified price. Market orders are subject to slippage and poor fills during fast-moving markets.
              </p>
            </div>
            <div>
              <h3 className="text-xl font-bold text-blue-400 mb-2">2. Discipline Over Speed</h3>
              <p className="text-gray-300">
                Limit orders force you to wait for your price. This reduces FOMO entries and ensures you only enter when the market gives you a favorable price.
              </p>
            </div>
            <div>
              <h3 className="text-xl font-bold text-blue-400 mb-2">3. Risk-to-Reward Alignment</h3>
              <p className="text-gray-300">
                By waiting for your entry, you naturally align your risk-to-reward ratio. You're not chasing price, which often leads to worse R:R.
              </p>
            </div>
          </div>
        </motion.div>

        {/* Missed Opportunities */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7 }}
          className="mb-12"
        >
          <h2 className="text-3xl font-bold mb-6">The Missed Opportunity Myth</h2>
          <div className="bg-slate-800 rounded-2xl p-8">
            <p className="text-gray-300 mb-4">
              Many traders fear limit orders because they might "miss the move." Our data shows:
            </p>
            <div className="bg-green-900/30 border border-green-500 rounded-xl p-6 mb-4">
              <p className="text-green-400 font-bold text-xl mb-2">
                0 unfilled limit orders in 158 trades
              </p>
              <p className="text-gray-300">
                In this dataset, every limit order was filled. The fear of missing opportunities was unfounded.
              </p>
            </div>
            <p className="text-gray-300">
              Even when limit orders do expire unfilled, the cost of a bad market entry often exceeds the opportunity cost of waiting.
            </p>
          </div>
        </motion.div>

        {/* Limitations */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="mb-12"
        >
          <h2 className="text-3xl font-bold mb-6">Limitations</h2>
          <div className="bg-slate-800 rounded-2xl p-8">
            <ul className="space-y-4 text-gray-300">
              <li>• <strong>Sample size:</strong> 22 limit orders vs 134 market orders. More data needed for statistical significance.</li>
              <li>• <strong>Market conditions:</strong> Results may vary in different volatility regimes or news events.</li>
              <li>• <strong>Entry quality:</strong> Limit orders only work if your entry levels are well-researched. Poor levels still lose.</li>
              <li>• <strong>Instrument-specific:</strong> US100 showed 0% win rate for both types in this small sample.</li>
            </ul>
          </div>
        </motion.div>

        {/* Recommendations */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.9 }}
          className="mb-12"
        >
          <h2 className="text-3xl font-bold mb-6">Recommendations</h2>
          <div className="bg-slate-800 rounded-2xl p-8">
            <ol className="space-y-4 text-gray-300 list-decimal list-inside">
              <li>Use <strong className="text-green-400">limit orders</strong> for entries on XAUUSD, EURUSD, GBPUSD, and AUDUSD</li>
              <li>Reserve <strong className="text-red-400">market orders</strong> only for breakout scenarios where speed is critical</li>
              <li>Always calculate the opportunity cost before using market orders</li>
              <li>Track your limit order fill rate to understand your market's behavior</li>
              <li>Use PrimeEdge's entry corridor to set realistic limit order levels</li>
            </ol>
          </div>
        </motion.div>

        {/* Disclaimer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.0 }}
        >
          <div className="bg-slate-800 rounded-2xl p-8 text-gray-400 text-sm">
            <p className="mb-2">
              <strong>Disclaimer:</strong> This analysis is based on historical data from our trading system. Past performance is not indicative of future results. Trading involves substantial risk of loss. These findings apply to our specific strategy and may not generalize to other approaches.
            </p>
            <p>
              <strong>Last updated:</strong> November 6, 2026 | <strong>Sample:</strong> 158 trades (5 years)
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default ResearchLimitVsMarket;
