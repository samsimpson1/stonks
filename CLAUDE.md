# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python application that scrapes and stores Final Fantasy XIV market data from Universalis API. The application connects to a WebSocket stream to receive real-time market sale events and stores them in a local SQLite database.

## Development Commands

- **Run the application**: `uv run scrape.py`
- **Install dependencies**: `uv sync --locked`
- **Format code**: `uv tool run ruff format` (configured with 2-space indentation in pyproject.toml)
- **Lint code**: `uv tool run ruff check`
- **Run tests**: `uv run pytest` (runs all tests including integration tests)
- **Run fast tests only**: `uv run pytest -m "not slow"` (skips 30-second integration test)
- **Run specific test**: `uv run pytest test_integration.py::TestScraperIntegration::test_scraper_initialization`
- **Run in Docker**: `docker build -t stonks . && docker run stonks`

## Architecture

### Core Components

- **scrape.py**: Main application entry point containing WebSocket handling and business logic
- **database.py**: Database abstraction layer with `StonksDatabase` class for all SQLite operations
- **test_integration.py**: Pytest-based integration tests that verify live API connectivity and data collection
- **SQLite Database**: Stores three main tables:
  - `items`: Item ID to name mapping (item_id, item_name)
  - `worlds`: World ID to name mapping (world_id, world_name) 
  - `sales`: Market transaction records (timestamp, world_id, item_id, price, quantity, buyer)

### Data Flow

1. **Initialization**: Sets up SQLite tables and fetches world list from Universalis API for the configured data center (hardcoded to "Light")
2. **WebSocket Connection**: Connects to `wss://universalis.app/api/ws` and subscribes to sales events for all worlds in the data center
3. **Event Processing**: Receives BSON-encoded market sale events, processes each sale, and stores in database
4. **Item Name Resolution**: Looks up item names from XIVAPI v2 when encountering new items, with caching to avoid repeated API calls

### External APIs

- **Universalis API**: Provides FFXIV market data
  - Data centers: `https://universalis.app/api/v2/data-centers`
  - Worlds: `https://universalis.app/api/v2/worlds`
  - WebSocket: `wss://universalis.app/api/ws`
- **XIVAPI v2**: Provides item name lookups
  - Item lookup: `https://v2.xivapi.com/api/sheet/Item/{item_id}?fields=Name&language=en`

### Key Implementation Details

- Uses BSON encoding for WebSocket communication
- Implements graceful shutdown handling for SIGINT/SIGTERM
- Filters out sales older than 7 days to keep data relevant
- Database path configurable via `DB_PATH` environment variable (defaults to `/data/stonks.db`)
- Separation of concerns: database operations in `StonksDatabase` class, business logic in `scrape.py`
- Item name caching to avoid repeated XIVAPI calls for the same item
- Runs as non-root user (UID 568) in Docker container

## Database Schema

- Primary keys and indexes are set up for efficient querying
- Sales table uses compound primary key (timestamp, item_id, price) to handle duplicates
- Timestamp index on sales table for time-based queries

## Testing

The project uses pytest for testing with integration tests that verify live API connectivity:

- **test_integration.py**: Contains `TestScraperIntegration` class with three test methods:
  - `test_scraper_initialization()`: Verifies scraper can connect and populate worlds table (10 seconds)
  - `test_live_data_collection()`: Full 30-second test collecting live market data (marked as `@pytest.mark.slow`)
  - `test_database_schema()`: Validates database table structure and indexes
- **Fixtures**: Automatic setup/teardown of temporary databases and scraper processes
- **Environment variables**: Tests use `DB_PATH` to run with temporary SQLite files
- **Subprocess execution**: Tests run scraper as separate process to avoid threading issues

Tests are marked with `slow` marker for the 30-second integration test. Use `-m "not slow"` to skip during development.