# Soccer Betting Analyzer

A command-line application to help identify potential value bets in soccer (football) and other sports markets by calculating Expected Value (EV).

## Features

*   Calculates Expected Value (EV) for bets.
*   Fetches live odds data from The Odds API for various sports, regions, and markets.
*   Supports user selection of sport, region, and markets for data fetching.
*   Implements local caching for API responses to minimize redundant calls and stay within API quotas.
*   Identifies value bets based on user-defined probabilities and EV thresholds.
*   Offers multiple methods for determining true probabilities:
    *   User-provided via a JSON file.
    *   Estimated using "vig removal" from bookmaker odds (currently from the first bookmaker in example data).
    *   Default example probabilities.
*   Supports analysis across multiple betting markets for an event (e.g., Head-to-Head (H2H), Totals (Over/Under)).
*   Provides a Command Line Interface (CLI) for interaction, including:
    *   `fetch-data`: Fetches and caches odds.
    *   `analyze-bets`: Analyzes odds using specified probabilities to find value.
    *   `list-sports`: Lists all available sports from The Odds API.
*   Configuration managed via a `config/settings.yaml` file.

## Project Structure

```
soccer_betting_analyzer/
├── config/
│   └── settings.yaml           # Configuration file (API keys, thresholds, cache settings)
├── data/
│   └── api_cache/              # Default directory for cached API responses
├── src/
│   ├── __init__.py
│   ├── main.py                 # Main CLI entry point
│   ├── analysis/               # Modules for betting analysis
│   │   └── value_calculator.py   # Core EV and probability calculations
│   ├── data_acquisition/       # Modules for fetching data
│   │   └── the_odds_api.py       # Interface with The Odds API
│   └── utils/                  # Utility modules
│       ├── config_loader.py      # Loads settings.yaml
│       ├── data_storage.py       # Handles local caching of API data
│       └── probability_loader.py # Loads user-defined probabilities
├── tests/                      # Unit tests
│   ├── test_data_storage.py
│   ├── test_probability_loader.py
│   ├── test_the_odds_api.py
│   └── test_value_calculator.py
├── README.md                   # This file
└── requirements.txt            # Python dependencies
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
    *   The `config/settings.yaml` file is created with default values.
    *   Edit `config/settings.yaml`:
        *   **API Key:** Replace `'YOUR_API_KEY_HERE'` under `the_odds_api.api_key` with your actual API key from [The Odds API](https://the-odds-api.com/). A free plan provides an API key.
        *   **Default EV Threshold:** Adjust `analysis.default_ev_threshold` if desired (default is `0.05`). This is the minimum EV to flag a bet as valuable.
        *   **Data Storage (Caching):**
            *   `data_storage.base_path`: Specifies the directory for cached API responses (default: `'data/api_cache/'`).
            *   `data_storage.freshness_hours`: Defines how long cached data is considered fresh (default: `6` hours).

## Usage

The application is run via `src/main.py`. You can run it from the project root directory (`soccer_betting_analyzer/`).

**General command structure:**
```bash
python src/main.py [command] [options]
```
Or, if your PYTHONPATH includes the `src` directory (or the project is installed as a package):
```bash
python -m src.main [command] [options]
```

**Available Commands:**

1.  **`list-sports`**: Lists all available sports from The Odds API.
    *   This helps you find valid `--sport` keys for the `fetch-data` command.
    *   Requires a valid API key in `config/settings.yaml`.
    ```bash
    python src/main.py list-sports
    ```

2.  **`fetch-data`**: Fetches live odds data from The Odds API for a specified sport and caches the response.
    *   Requires a valid API key.
    *   **Arguments:**
        *   `--sport <sport_key>` (Required): The key for the sport (e.g., `soccer_epl`, `basketball_nba`). Use `list-sports` to find keys.
        *   `--regions <regions>` (Optional): Comma-separated list of regions (e.g., `eu,us,uk,au`). Default: `eu`.
        *   `--markets <markets>` (Optional): Comma-separated list of markets (e.g., `h2h,spreads,totals`). Default: `h2h`.
    *   Example:
        ```bash
        python src/main.py fetch-data --sport soccer_epl --regions uk --markets h2h,totals
        ```
    *   Fetched data is cached locally. If fresh cached data exists for the exact same request, it will be used instead of making a new API call.

3.  **`analyze-bets`**: Analyzes bets from `EXAMPLE_EVENT_DATA` (defined in `src/main.py`) to find value.
    *   This command currently uses hardcoded example event data for analysis.
    *   **Probability Source Priority:**
        1.  `--prob-file <filepath>`: Uses probabilities from your JSON file for the example event.
        2.  `--use-vig-removal`: If `--prob-file` is not used, this flag makes the tool estimate probabilities by removing the vig from the first bookmaker's odds in `EXAMPLE_EVENT_DATA` (for all its markets).
        3.  Default: If neither option is used, it falls back to `USER_ESTIMATED_PROBS_EXAMPLE` defined in `src/main.py`.
    *   **Arguments:**
        *   `--ev-threshold <float>` (Optional): Minimum Expected Value to consider a bet valuable. Defaults to the value in `config/settings.yaml` (e.g., `0.05`).
        *   `--prob-file <filepath>` (Optional): Path to your JSON file containing custom probabilities for the example event. See "User-Defined Probabilities File Format" below.
        *   `--use-vig-removal` (Optional Flag): Estimate probabilities using vig removal.
    *   The analysis considers all available markets in the `EXAMPLE_EVENT_DATA` (e.g., H2H and Totals).
    *   Examples:
        ```bash
        # Use default example probabilities
        python src/main.py analyze-bets --ev-threshold 0.10

        # Use probabilities from a custom file
        python src/main.py analyze-bets --prob-file my_custom_probs.json

        # Use vig removal model
        python src/main.py analyze-bets --use-vig-removal
        ```

## User-Defined Probabilities File Format

When using the `--prob-file` option with `analyze-bets`, your JSON file should follow this structure:
It should be a list of events. For the `analyze-bets` command (which currently analyzes one hardcoded example event), the file should contain an entry for `event_id: "exampleevent001"`.

```json
[
  {
    "event_id": "exampleevent001",
    "home_team": "Team Alpha",
    "away_team": "Team Beta",
    "probabilities": {
      "Team Alpha": 0.48,
      "Draw": 0.24,
      "Team Beta": 0.28,
      "Over 2.5": 0.55,
      "Under 2.5": 0.45
    }
  }
  // You could add other events here for future use if the tool
  // is expanded to analyze multiple events from a data source.
]
```

**Explanation:**

*   **`event_id`**: Must match the ID of the event you want these probabilities to apply to. For the current `analyze-bets` command, this should be `"exampleevent001"`.
*   **`home_team`, `away_team`**: Optional, for readability and your reference. Not used by the loading logic itself.
*   **`probabilities`**: A flat dictionary where:
    *   Keys are the exact outcome names as they appear in the odds data (e.g., "Team Alpha", "Draw", "Over 2.5").
    *   Values are your estimated true probabilities for those outcomes (float between 0.0 and 1.0).
    *   Ensure outcome names are unique if you are providing probabilities for multiple markets within this single `probabilities` object.

The loader will validate this structure and the probability values.

## Running Tests

To run all unit tests, navigate to the project root directory and run:
```bash
python -m unittest discover tests
```
To run a specific test file:
```bash
python tests/test_value_calculator.py # Or any other test file
```

## Disclaimer

This tool is for educational and informational purposes only. Betting involves risk. Always gamble responsibly and within your means. The accuracy of value bet identification depends heavily on the accuracy of the "true probability" estimates. API usage may be subject to quotas and costs from The Odds API.

## Future Development Ideas
*   Analyze live odds data fetched by `fetch-data` instead of just example data.
*   Allow users to specify which event from fetched data to analyze.
*   More sophisticated probability models (e.g., Poisson distribution based on team stats, Elo ratings).
*   Support for a wider range of betting markets and sports.
*   Web interface or a more interactive GUI.
*   Historical odds analysis and backtesting strategies.
*   Integration with multiple odds providers.
```
