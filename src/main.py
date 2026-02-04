import os
import json
import crawler
import extractor
import analyzer
import shutil
from dotenv import load_dotenv

# Resolve paths relative to this script file to be robust
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) # Go up from src/ to figure_extractor/
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PAPERS_DIR = os.path.join(DATA_DIR, "papers")
FIGURES_DIR = os.path.join(DATA_DIR, "figures")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {"processed_ids": []}

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

import concurrent.futures

def process_one_image(img_path, paper_id):
    """
    Helper to process a single image: Analyze -> Save/Delete.
    Returns 1 if saved, 0 if skipped/deleted.
    """
    try:
        filename = os.path.basename(img_path)
        print(f"    [Thread] Analyzing {filename}...", flush=True)
        result = analyzer.analyze_image(img_path)
        
        if result.get("is_methodology") and result.get("quality_score", 0) >= 8:
            # Move to figures dir
            dest_name = f"{paper_id}_{filename}"
            dest_path = os.path.join(FIGURES_DIR, dest_name)
            shutil.move(img_path, dest_path)
            
            # Save metadata
            with open(dest_path + ".json", 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"    [+] KEEP: {filename} (Score: {result.get('quality_score')})")
            return 1
        else:
            # Cleanup rejected
            os.remove(img_path)
            print(f"    [-] SKIP: {filename} ({result.get('reason', 'low quality')})")
            return 0
    except Exception as e:
        print(f"    [!] Error analyzing {img_path}: {e}")
        return 0

def main():
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Please set GOOGLE_API_KEY in .env or environment.")
        return

    # Init
    analyzer.init_gemini(api_key)
    history = load_history()
    processed_ids = set(history["processed_ids"])

    # User Input
    print("--- Scientific Methodology Figure Extractor ---")
    
    # Default to top Computer Science categories: CV, CL (NLP), LG (Machine Learning), AI
    default_query = "cat:cs.CV OR cat:cs.CL OR cat:cs.LG OR cat:cs.AI"
    print(f"Default Query: Top CS Categories (CV, NLP, ML, AI)")
    
    user_query = input(f"Enter ArXiv query (Press Enter for default): ").strip()
    query = user_query if user_query else default_query
    
    try:
        count = int(input("How many NEW papers to process? ").strip())
    except:
        count = 1
    
    try:
        max_workers = int(input("Max concurrent threads (default 4): ").strip())
    except:
        max_workers = 4

    # 1. Fetch
    papers = crawler.fetch_papers(query, max_results=count, saved_ids=processed_ids)
    print(f"[*] Found {len(papers)} new papers to process.")

    for paper in papers:
        print(f"\n[=] Processing: {paper['title']} ({paper['id']})")
        
        # Download
        pdf_name = f"{paper['id']}.pdf"
        pdf_path = os.path.join(PAPERS_DIR, pdf_name)
        
        if not crawler.download_pdf(paper['pdf_url'], pdf_path):
            continue

        # Extract
        print("    Extracting images...")
        raw_images = extractor.extract_images_from_pdf(pdf_path, PAPERS_DIR) 
        print(f"    Found {len(raw_images)} candidate images. Analyzing with {max_workers} threads...")

        # Analyze (Multi-threaded)
        saved_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create a future for each image
            futures = {executor.submit(process_one_image, img, paper['id']): img for img in raw_images}
            
            for future in concurrent.futures.as_completed(futures):
                saved_count += future.result()

        # Cleanup PDF to save space
        try:
            os.remove(pdf_path)
            print(f"    [Cleanup] Deleted temporary PDF: {pdf_name}")
        except OSError as e:
            print(f"    [Warning] Could not delete PDF: {e}")
        
        # Update History (JSON for code, MD for human)
        processed_ids.add(paper['id'])
        history["processed_ids"] = list(processed_ids)
        save_history(history)
        
        # Append to human-readable log (Legacy, we now use sync_dataset_index)
        # log_file = os.path.join(DATA_DIR, "history.md")
        # with open(log_file, "a", encoding="utf-8") as f:
        #     f.write(f"- **{paper['id']}**: {paper['title']} ({saved_count} figures saved)\n")

        print(f"    Saved {saved_count} figures from this paper.")
    
    # Final Step: Sync the detailed index
    print("\n[Index] Syncing dataset index and checking for deleted files...")
    sync_dataset_index()
    print("[Done] Dataset updated.")

def sync_dataset_index():
    """
    Rebuilds dataset_index.md based on actual files in figures/.
    Removes sidecar .json if the image was manually deleted.
    """
    index_file = os.path.join(DATA_DIR, "dataset_index.md")
    
    # 1. Scan for consistency
    all_files = os.listdir(FIGURES_DIR)
    json_files = [f for f in all_files if f.endswith('.json')]
    
    valid_entries = []
    
    for jf in json_files:
        json_path = os.path.join(FIGURES_DIR, jf)
        img_filename = jf[:-5] # remove .json
        img_path = os.path.join(FIGURES_DIR, img_filename)
        
        # Check if image still exists
        if not os.path.exists(img_path):
            print(f"    [Sync] Orphaned metadata found, removing: {jf}")
            try:
                os.remove(json_path)
            except:
                pass
            continue
            
        # Read metadata
        try:
            with open(json_path, 'r') as f:
                meta = json.load(f)
                meta['filename'] = img_filename
                valid_entries.append(meta)
        except Exception as e:
            print(f"    [Sync] Corrupt metadata {jf}: {e}")

    # 2. Sort entries (by filename or score?) - let's do filename (date implicit)
    valid_entries.sort(key=lambda x: x['filename'], reverse=True)
    
    # 3. Write Markdown
    with open(index_file, 'w', encoding="utf-8") as f:
        f.write("# Dataset Index\n\n")
        f.write(f"Total Figures: {len(valid_entries)}\n\n")
        f.write("---\n\n")
        
        for entry in valid_entries:
            f.write(f"### {entry['filename']}\n")
            f.write(f"![{entry['filename']}](figures/{entry['filename']})\n\n")
            f.write(f"- **Score**: {entry.get('quality_score')} / 10\n")
            f.write(f"- **Style**: {entry.get('visual_style', 'N/A')}\n")
            f.write(f"- **Logic**: {entry.get('logic_summary', 'N/A')}\n")
            
            tags = entry.get('keywords', [])
            if tags:
                f.write(f"- **Tags**: `{'`, `'.join(tags)}`\n")
            
            f.write("\n---\n\n")

if __name__ == "__main__":
    main()
