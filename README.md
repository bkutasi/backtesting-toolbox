# Backtesting Toolbox

This project focuses on backtesting various trading strategies using historical price data from Binance. It leverages the `backtrader` library for backtesting and provides options for visualizing and saving the results.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Strategies](#strategies)
- [Data](#data)
- [Backtesting](#backtesting)
- [Analysis](#analysis)
- [Contributing](#contributing)
- [License](#license)

## Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/yourusername/backtesting-toolbox.git
    cd backtesting-toolbox
    ```

2. **Install the required packages:**

    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the project from the command line using:

```bash
python main.py [options]
```

### Options

*   `--no-plot`: Disable plotting the chart.
*   `--save-plot`: Save the plot to a file (`btc_strategy_plot.png`).
*   `--strategy`: Select the strategy to use (default: `MaCross`). Available strategies:
    *   `MaCross`
    *   `TripleSupertrend`
    *   `CrossoverStochRSI`
    *   `TripleEMaStrategy`

## Strategies

The project implements the following trading strategies, defined in `strategies.py`:

*   **MaCross:** A moving average crossover strategy.
*   **TripleSupertrend:** A strategy based on three Supertrend indicators with different periods and multipliers.
*   **CrossoverStochRSI:** A strategy that combines Stochastic Oscillator and RSI.
*   **TripleEMaStrategy:** A strategy based on three Exponential Moving Averages.

## Data

The project fetches historical Bitcoin price data from the Binance API using the `DataHandler` class in `main.py`. It caches the data in a pickle file (`btc_price_data.pkl`) to avoid redundant API calls.

## Backtesting

The `BacktestRunner` class in `main.py` handles the backtesting process using the `backtrader` library. It performs the following steps:

1. Sets up the `backtrader` Cerebro engine.
2. Adds the historical price data.
3. Adds the selected trading strategy.
4. Sets the initial cash and commission.
5. Adds analyzers for Sharpe Ratio, Drawdown, Returns, and Trade Analysis.
6. Runs the backtest.

## Analysis

After running the backtest, the project calculates and prints the following performance metrics:

*   **Winrate:** The percentage of profitable trades.
*   **Sharpe Ratio:** A measure of risk-adjusted return.
*   **Max Drawdown:** The maximum peak-to-trough decline during the backtesting period.
*   **Total Return:** The overall return of the strategy.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues to improve the project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.