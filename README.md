# DataCopilot

DataCopilot is an AI-powered data analysis assistant built with Python, LangGraph, LangChain, and Google Gemini. It routes natural-language requests to either a SQL analysis workflow or an ETL workflow, helping users query a MySQL ride-sharing dataset or extract and transform data from external sources.

## Features

- **Intent-based routing** - Automatically directs requests to SQL or ETL processing.
- **Natural-language SQL** - Refines questions, generates MySQL, validates query safety, executes approved read-only queries, and summarizes results.
- **SQL safety guardrail** - Blocks generated queries that are not classified as safe for read-only execution.
- **Database-aware context** - Discovers table and column metadata and includes sample rows during SQL generation.
- **ETL automation** - Downloads JSON API responses and saves them as CSV, JSON, or Parquet.
- **Pandas transformations** - Uses a LLM-generated Pandas workflow to transform extracted datasets.
- **Reproducible sample database** - Creates and seeds a MySQL database from bundled CSV files.

## Technology Stack

| Category | Technology |
| --- | --- |
| Language | Python 3.12+ |
| Agent orchestration | LangGraph |
| AI framework | LangChain |
| LLM provider | Google Gemini |
| Database | MySQL |
| Data processing | Pandas |
| Data validation | Pydantic |
| Package and environment manager | uv |

## System Architecture

```text
User Question
      |
      v
Data Agent Router
      |
      +-----------------------+
      |                       |
      v                       v
SQL Analyst Agent       ETL Analyst Agent
      |                       |
      +-- Curate question     +-- Extract from URL
      +-- Inspect schema      +-- Load dataset
      +-- Generate SQL        +-- Generate Pandas code
      +-- Safety judge        +-- Execute transformation
      +-- Execute query
      +-- Summarize result
```

## Project Structure

```text
data_agent/
├── agents/
│   ├── data_agent.py       # Main router and orchestration graph
│   ├── etl_agent.py        # Extraction and transformation agent
│   └── sql_analyst.py      # SQL generation, validation, and execution
├── data/                   # Bundled ride-sharing CSV datasets
├── models/
│   └── schema.py           # Pydantic and LangGraph state models
├── src/data_agent/
│   └── __init__.py         # Package entry point
├── utils/
│   ├── database.py         # MySQL schema discovery and query execution
│   ├── etl_tool.py         # Data extraction and transformation tools
│   └── llm_picks.py        # Gemini model configuration
├── feed_db.py              # MySQL schema creation and CSV loader
├── main.py                 # Example DataCopilot invocation
└── pyproject.toml          # Project metadata and dependencies
```

## Data Model

The sample database contains five related tables:

| Table | Records |
| --- | ---: |
| `users` | 10,000 |
| `vehicles` | 3,000 |
| `rides` | 20,000 |
| `payments` | 16,073 |
| `ratings` | 12,000 |

Relationships connect vehicles to drivers, rides to riders and drivers, payments to rides and users, and ratings to rides and users.

## Prerequisites

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- A running MySQL server
- A Google Gemini API key

## Installation

Clone the repository:

```bash
git clone https://github.com/Dharanidharan4270/DataCopilot.git
cd DataCopilot
```

Install the dependencies:

```bash
uv sync
```

## Configuration

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Add your credentials:

```dotenv
GEMINI_API_KEY=your_gemini_api_key

host=127.0.0.1
port=3306
database=ola_rides
user=your_mysql_user
password=your_mysql_password
```

The default database name used by the project is `ola_rides`. Create it before seeding:

```sql
CREATE DATABASE ola_rides;
```

Ensure the MySQL account has permission to create tables and indexes. The loader also requires MySQL server and client support for `LOAD DATA LOCAL INFILE`.

## Seed the Database

Run the database setup script:

```bash
uv run python feed_db.py
```

> **Warning:** `feed_db.py` creates the required tables, creates indexes, and truncates the existing `ratings`, `payments`, `rides`, `vehicles`, and `users` tables before loading the bundled CSV files. Use it only on a database that can be safely reset.

## Run the Example

The built-in example sends a SQL question to the agent:

```bash
uv run python main.py
```

Example output is based on natural-language input such as:

```text
Give me the number of vehicles manufactured after 2020
```

To use DataCopilot in another Python program:

```python
from langchain_core.messages import HumanMessage
from agents.data_agent import data_agent

result = data_agent.invoke({
    "message": [
        HumanMessage(content="What are the top 10 drivers by completed rides?")
    ],
    "route_response": "",
})

print(result["message"][-1].content)
```

## Example SQL Questions

- How many rides were completed?
- Show the top 10 cities by rider count.
- What is the average fare for completed rides?
- Which drivers have the highest average rating?
- How many payments failed by payment method?

## Example ETL Requests

- Extract data from a JSON API URL and save it as CSV.
- Transform `data/extracted_data/extracted_data.csv` and save the result as CSV.
- Load an API response into a local Parquet file.

The ETL workflow supports `csv`, `json`, and `parquet` output formats.

## Development

Run the SQL example directly:

```bash
uv run python agents/sql_analyst.py
```

Inspect or generate the ETL agent graph:

```bash
uv run python agents/etl_agent.py
```

Running the ETL script also refreshes `etl_analyst_graph.png`.

## Safety and Limitations

- SQL is generated dynamically and should be reviewed before use in production environments.
- The SQL workflow applies a safety judge intended to allow read-only data retrieval and reject mutations, but AI safeguards are not a substitute for database permissions and network controls.
- Database accounts used with this project should have no write privileges beyond what the selected workflow requires.
- ETL transformation code is generated and executed by the Python runtime; use trusted prompts and inputs only.
- The current package entry point is a placeholder and the primary usage examples execute modules directly.

## Troubleshooting

### `Database connection is not available`

Verify that MySQL is running and that `host`, `port`, `database`, `user`, and `password` are set correctly in `.env`.

### Gemini API authentication errors

Confirm that `GEMINI_API_KEY` is present and valid.

### Local infile is disabled

Enable `local_infile` on the MySQL server and grant the MySQL account permission to use `LOAD DATA LOCAL INFILE`. For example:

```sql
SET GLOBAL local_infile = 1;
```

Client-side support must also be enabled through the connector configuration.

## Contributing

Contributions are welcome. Please open an issue to discuss major changes before submitting a pull request.

1. Fork the repository.
2. Create a feature branch.
3. Keep changes focused and well documented.
4. Verify the relevant workflow before opening a pull request.
