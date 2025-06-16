# Media Extractor Service

Media Extractor Service is a FastAPI application that extracts text from images, uses a language model to classify movie, tv, or book titles, and fetches metadata about them. It exposes a minimal API to process image uploads and returns enriched media information.

## Running Locally

1. **Clone the repository** and install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. **Create a `.env` file** in the project root with the following environment variables:
   ```bash
   OPENROUTER_API_KEY=<your-openrouter-api-key>
   TMDB_API_KEY=<your-tmdb-api-key>
   GOOGLE_VISION_API_KEY=<your-google-vision-api-key>
   ```
3. **Start the server** using Uvicorn:
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

1. Release branch
2. CI/CD (Possibly GH action. Triggered on new release)
3. Fuzzy metadata search
4. Recommendation rate (how much I will enjoy the media)
5. Save to Notion DB

