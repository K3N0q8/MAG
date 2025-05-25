# Soccer Betting Analyzer

A command-line application to help identify potential value bets in soccer (football) markets by calculating Expected Value (EV).

## Features (Current & Planned)

*   Calculates Expected Value (EV) for bets.
*   Fetches odds from The Odds API (requires API key). (Currently simulated in `fetch-data`)
*   Identifies value bets based on user-defined probabilities and EV thresholds.
*   Basic Command Line Interface (CLI) for interaction.
*   Configuration via `config/settings.yaml`.

## Project Structure

```
soccer_betting_analyzer/
├── config/
│   └── settings.yaml       # Configuration file (API keys, thresholds)
├── data/                   # For storing local data (e.g., downloaded odds, not yet implemented)
├── src/
│   ├── __init__.py
│   ├── main.py             # Main CLI entry point
│   ├── analysis/           # Modules for betting analysis (value calculation)
│   │   └── value_calculator.py
│   ├── data_acquisition/   # Modules for fetching data (e.g., from APIs)
│   │   └── the_odds_api.py
│   └── utils/              # Utility modules (config loading)
│       └── config_loader.py
├── tests/                  # Unit tests
│   └── test_value_calculator.py
├── README.md               # This file
└── requirements.txt        # Python dependencies
```

## Setup

1.  **Clone the repository (if applicable):**
    ```bash
    # git clone <repository_url>
    # cd soccer_betting_analyzer
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the application:**
    *   Copy or rename `config/settings.yaml` if needed (though it's created by default).
    *   Edit `config/settings.yaml`:
        *   Replace `'YOUR_API_KEY_HERE'` under `the_odds_api.api_key` with your actual API key from [The Odds API](https://the-odds-api.com/). You can sign up for a free plan to get an API key.
        *   Adjust `analysis.default_ev_threshold` if desired (default is 0.05).

## Usage

The application is run via `src/main.py`. You can run it from the project root directory (`soccer_betting_analyzer/`).

**General command structure:**
```bash
python src/main.py [command] [options]
```
Or, if you set your PYTHONPATH to include the `src` directory or install the project as a package (more advanced):
```bash
python -m src.main [command] [options]
```

**Available Commands:**

1.  **`fetch-data`**: Simulates fetching sports odds data.
    *   This command currently prints a message and shows an example of the data structure. It does not make live API calls unless you have modified `the_odds_api.py` and correctly set your API key.
    ```bash
    python src/main.py fetch-data
    ```

2.  **`analyze-bets`**: Analyzes a predefined set of example match data to find value bets.
    *   This command uses hardcoded example event data and example user-estimated probabilities defined in `src/main.py`. It's useful for seeing the value calculation logic in action.
    *   You can set a custom EV threshold using the `--ev-threshold` option.
    ```bash
    python src/main.py analyze-bets
    ```
    ```bash
    python src/main.py analyze-bets --ev-threshold 0.10
    ```
    The default EV threshold is taken from `config/settings.yaml` (initially 0.05).

## Running Tests

To run the unit tests:
```bash
python -m unittest discover tests
```
Or, to run a specific test file (from the project root):
```bash
python tests/test_value_calculator.py
```

## Disclaimer

This tool is for educational and informational purposes only. Betting involves risk. Always gamble responsibly and within your means. The accuracy of value bet identification depends heavily on the accuracy of the "true probability" estimates.

## Future Development Ideas
*   Implement actual data fetching and storage from The Odds API.
*   Allow users to input or load their own probability models/estimates.
*   Support for more sports and betting markets.
*   More sophisticated probability models (e.g., Poisson, Elo ratings).
*   Web interface instead of/in addition to CLI.
*   Historical odds analysis.
```
