# Media Extractor Service

Media Extractor Service is a FastAPI application that extracts text from images, uses a language model to classify movie, tv, or book titles, and fetches metadata about them. It exposes a minimal API to process image uploads and returns enriched media information.

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
3. **Create a `.env` file** in the project root with the following environment variables:
   ```bash
   OPENROUTER_API_KEY=<your-openrouter-api-key>
   TMDB_API_KEY=<your-tmdb-api-key>
   GOOGLE_VISION_API_KEY=<your-google-vision-api-key>
   ```
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

## Roadmap

1. CI/CD (Possibly GH action. Triggered on new release) ✅
2. Fuzzy metadata search ✅
3. Recommendation rate (how much I will enjoy the media)
4. Save to Notion DB
5. LLM confidence level
6. Unit test
