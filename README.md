# Paper Diagram Hunter

A specialized tool for researchers to build high-quality datasets of **Methodology Diagrams** and **Model Architectures** from ArXiv papers.

## Motivation & Goals

The primary goal of this project is to collect high-quality paper illustrations to provide **visual inspiration** for researchers and designers. 

Looking ahead, I plan to build a high-quality paper library to further assist AI Agents in generating diagrams, drawing inspiration from projects like [PaperBanana](https://dwzhu-pku.github.io/PaperBanana/).


## Features

- **Smart Crawler**: Automatically fetches the latest papers from top CS fields (CV, NLP, ML, AI).
- **Caption-Aware Extraction**: Uses rigorous "Figure X" caption detection to extract compound figures (sub-figures) as single, complete images.
- **Intelligent Filtering**:
    - **Visual Clustering**: Rejects "complex grids" (e.g., experimental results with >2 sub-images).
    - **AI Analysis**: Uses **Google Gemini 3 Flash** to visually analyze each figure.
    - **Strict Standards**: Only saves figures that explain *HOW* a method works (Architecture, Pipeline, Flowchart), rejecting results, charts, and generic diagrams.
- **Metadata Indexing**: Automatically generates a `dataset_index.md` with visual previews, style tags, and logic summaries.

## Installation

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  Get a [Google Gemini API Key](https://aistudio.google.com/).
2.  Create a file named `.env` in the root directory.
3.  Add your key:
    ```text
    GOOGLE_API_KEY=AIzaSy...YourKeyHere...
    ```

## Usage

Run the main script:

```bash
python src/main.py
```

1.  **Query**: Press Enter to search default top CS categories, or enter a custom ArXiv query (e.g., `cat:cs.RO` for Robotics).
2.  **Quantity**: Enter how many *new* papers you want to process.
3.  **Threads**: Set concurrency (default 4) for faster AI analysis.

The tool will:
- Download PDFs to `data/papers` (temp).
- Extract figures.
- Analyze them with Gemini.
- Save valid methodology diagrams to `data/figures`.
- Update `data/dataset_index.md`.

**Enjoy!**


## License

MIT License.
