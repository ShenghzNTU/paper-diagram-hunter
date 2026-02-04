import arxiv
import os
import requests

def fetch_papers(query, max_results=5, saved_ids=None):
    """
    Fetches papers from ArXiv based on query.
    Returns list of dicts: {'id': ..., 'title': ..., 'pdf_url': ...}
    Skipping those in saved_ids.
    """
    if saved_ids is None:
        saved_ids = set()

    print(f"[*] Searching ArXiv for: {query}, max: {max_results}")
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=1000, # Large buffer to skip over many existing/duplicate papers
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    results = []
    
    # We might need to handle pagination manually if 'scraper' approach, 
    # but arxiv library handles it nicely.
    count = 0
    for result in client.results(search):
        paper_id = result.entry_id.split('/')[-1]
        
        # Strip version number for cleaner ID logic if desired, 
        # but usually keep it to distinguish v1 vs v2. 
        # Simplicity: use full ID.
        
        if paper_id in saved_ids:
            continue
            
        results.append({
            'id': paper_id,
            'title': result.title,
            'pdf_url': result.pdf_url,
            'published': result.published
        })
        count += 1
        if count >= max_results:
            break
            
    return results

def download_pdf(url, save_path):
    """Downloads PDF to save_path."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"[!] Failed to download {url}: {e}")
        return False
