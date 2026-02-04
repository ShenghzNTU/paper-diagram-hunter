import fitz  # PyMuPDF
import os
import re

def get_page_elements(page):
    """
    Scans page and categorizes elements into Captions, Body Text, and Visuals.
    """
    captions = []
    body_text = []
    
    # 1. Text Analysis
    text_blocks = page.get_text("blocks")
    caption_pattern = re.compile(r'^(Fig\.?|Figure)\s*\d+', re.IGNORECASE)
    
    for block in text_blocks:
        # block: (x0, y0, x1, y1, text, block_no, type)
        if block[6] == 0: # Text
            text = block[4].strip()
            r = fitz.Rect(block[:4])
            
            # Simple heuristic: Captions usually start with "Figure X"
            # Note: Sometimes caption text is split across blocks. 
            # We assume the block *starting* with "Figure" is the anchor.
            if caption_pattern.match(text):
                captions.append((r, text))
            else:
                # Treat everything else as body text potential barrier
                # Filter out headers/footers if possible (y < 50 or y > h-50?)
                # For now, trust raw blocks.
                body_text.append(r)

    # 2. Visuals (Images + Drawings)
    visuals = []
    
    # Images
    for info in page.get_image_info(xrefs=True):
        visuals.append(fitz.Rect(info['bbox']))
        
    # Vector Drawings (Rects, lines for diagrams)
    # drawings = page.get_drawings()
    # for d in drawings:
    #     visuals.append(d["rect"])
    # Note: Drawings often include borders/underlines which mess up bounding boxes.
    # For now, relying on images is safer for "methodology" diagrams which are usually bitmaps.
    # If the user's diagram is pure vector (PDF stream), we might miss it without get_drawings.
    # Let's enable drawings but be careful filtering small ones.
    for p in page.get_drawings():
        r = p["rect"]
        # Filter tiny specs or full page borders
        if r.width > 20 and r.height > 20 and r.width < page.rect.width - 20:
             visuals.append(r)

    return captions, body_text, visuals

def extract_images_from_pdf(pdf_path, output_dir, min_size=50000, min_dim=400):
    """
    Extracts figures by finding the 'gap' between the Caption and the Body Text above it.
    """
    doc = fitz.open(pdf_path)
    extracted_images = []
    paper_basename = os.path.splitext(os.path.basename(pdf_path))[0]

    for page_index, page in enumerate(doc):
        # 1. Analyze page structure
        captions, body_text, visuals = get_page_elements(page)
        
        if not captions:
            continue
            
        # Sort captions top-to-bottom
        captions.sort(key=lambda x: x[0].y0)
        
        for i, (cap_rect, cap_text) in enumerate(captions):
            # Target Region Finding:
            # We want to find the whitespace *above* this caption.
            # It stops at the nearest Body Text or Page Top.
            
            # Define horizontal/column bounds based on caption width
            # If caption is wide (> 70% page width), search full width.
            # If caption is narrow, search roughly that column (+ buffer).
            is_wide = cap_rect.width > (page.rect.width * 0.6)
            
            if is_wide:
                x_min, x_max = 0, page.rect.width
            else:
                x_min = cap_rect.x0 - 20
                x_max = cap_rect.x1 + 20

            # Find Y-Limit (The ceiling)
            # Default ceiling is top of page
            y_ceiling = 0
            
            # Check against Body Text to pull ceiling down
            # valid text blocks are those strictly ABOVE caption and INTERSECTING horizontal range
            for txt_rect in body_text:
                if txt_rect.y1 < cap_rect.y0: # Text is above caption
                    # Check horizontal overlap
                    if max(x_min, txt_rect.x0) < min(x_max, txt_rect.x1):
                        # This text block is in the same column/region above us.
                        # Push ceiling down to the bottom of this text
                        if txt_rect.y1 > y_ceiling:
                            y_ceiling = txt_rect.y1
            
            # Also check against PREVIOUS caption (don't gobble previous figure)
            if i > 0:
                prev_cap = captions[i-1][0]
                if prev_cap.y1 < cap_rect.y0: # pure vertical order
                     # If previous caption is in same column?
                     if max(x_min, prev_cap.x0) < min(x_max, prev_cap.x1):
                         if prev_cap.y1 > y_ceiling:
                             y_ceiling = prev_cap.y1

            # Sanity buffer
            y_ceiling += 5 
            
            # Now we have a "Candidate Box" = [x_min, y_ceiling, x_max, cap_rect.y0]
            # Identify all visuals strictly inside or significantly overlapping this box
            candidate_visuals = []
            
            # We search slightly above the caption to valid ceiling
            search_rect = fitz.Rect(x_min, y_ceiling, x_max, cap_rect.y0)
            
            for v_rect in visuals:
                # We want visuals that are mostly inside the vertical region
                # Intersection area check?
                
                # Check 1: Must be largely above caption
                if v_rect.y0 >= cap_rect.y0: 
                    continue # This visual is below the caption logic line
                
                # Check 2: Must be largely below ceiling
                if v_rect.y1 <= y_ceiling:
                    continue
                
                # Check 3: Horizontal overlap
                if not (v_rect.x1 > x_min and v_rect.x0 < x_max):
                    continue
                    
                candidate_visuals.append(v_rect)
            
            if not candidate_visuals:
                continue

            # --- NEW LOGIC: Complexity Check ---
            # If a Figure is made of too many separate image objects (e.g. a 4x4 grid), 
            # it's likely a "Results" figure which user dislikes.
            # User wants to "Give up extracting this sequence number".
            if len(candidate_visuals) > 2:
                # print(f"    [Skip] {cap_text} has {len(candidate_visuals)} sub-images (Too complex).")
                continue
            # -----------------------------------
                
            # Union the candidates
            final_bbox = fitz.Rect(candidate_visuals[0])
            for v in candidate_visuals[1:]:
                final_bbox.include_rect(v)
            
            # Final Safety Crop: constrain to page and ceiling
            if final_bbox.y0 < y_ceiling:
                final_bbox.y0 = y_ceiling

            if final_bbox.width < 50 or final_bbox.height < 50:
                continue

            try:
                # Render (Fixes black background vs raw extraction)
                pix = page.get_pixmap(clip=final_bbox, alpha=False, dpi=150)
                
                if pix.size < min_size:
                    continue
                
                safe_cap = re.sub(r'[^\w\-]', '_', cap_text.split('\n')[0][:25])
                img_filename = f"{paper_basename}_p{page_index}_{safe_cap}.png"
                img_path = os.path.join(output_dir, img_filename)
                
                pix.save(img_path)
                pix = None
                
                extracted_images.append(img_path)
            except Exception as e:
                print(f"[!] Error on {cap_text}: {e}")

    return extracted_images
