# Media Extractor Service

Media Extractor Service is an AI-powered FastAPI application that extracts text from images, uses a language model to classify movie, tv, or book titles, and fetches metadata about them. It exposes a minimal API to process image uploads and returns enriched media information.

Metadata lookups first query the Wikipedia search API to fix misspellings. The result is cleaned of any trailing parentheses before querying Google Books or TMDB.

## Running Locally

1. **Clone the repository** and install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. **Install pre-commit hooks** so `pylint` runs on every commit:
   ```bash
   pre-commit install
   ```
3. **Create a `.env` file** based on `.env.example` and set the following variables:
   ```bash
   cp .env.example .env
   OPENROUTER_API_KEY=<your-openrouter-api-key>
   TMDB_API_KEY=<your-tmdb-api-key>
   GOOGLE_VISION_API_KEY=<your-google-vision-api-key>
   MEDIA_EXTRACTOR_API_KEY=<generated-api-key>
   MEDIA_EXTRACTOR_PUBLIC_API_KEY=<optional-public-api-key>
   ```
   The two `MEDIA_EXTRACTOR_*` keys can be any random strings generated with your
   preferred key generator.
4. **Start the server** using Uvicorn:
   ```bash
   uvicorn app.main:app --reload --port 3005
   ```
   The API will be available at `http://localhost:3005`.

## API Usage

### `POST /extract`

Send a multipart request containing a file, a query string, or both. At least one of them must be provided.

Form fields:

| Field | Type | Description |
|-------|------|-------------|
| `file` | File | Image file containing text (optional) |
| `query` | string | Additional text query (optional) |

If both fields are supplied, the text extracted from the file is concatenated with the query before being processed.

Requests authenticated with the optional public API key are limited to **2** requests every **15 minutes**. Exceeding this limit will return a `429 Too Many Requests` error.

## Roadmap

1. Recommendation rate
1. LLM confidence level
1. Unit test
1. Improve rate limit
