import google.generativeai as genai
import os
import json
import time

# Configurable model name
# Configurable model name
MODEL_NAME = "gemini-3-flash-preview" # Corrected ID from user logs

def init_gemini(api_key):
    genai.configure(api_key=api_key)

def analyze_image(image_path, model_name=MODEL_NAME):
    """
    Uses Gemini to analyze if the image is a high-quality methodology diagram.
    """
    try:
        model = genai.GenerativeModel(model_name)
        
        # Upload the file
        myfile = genai.upload_file(image_path)
        
        prompt = """
        Analyze this image. I am building a dataset of high-quality scientific **Methodology Diagrams** and **Model Architectures**.
        
        STRICT Criteria for "Methodology Diagram":
        1. **YES**: High-level system architectures, neural network diagrams, flowcharts of the proposed method, algorithm pipelines.
        2. **NO**: Experimental results, bar charts, line graphs, confusion matrices, scatters.
        3. **NO**: Qualitative examples (e.g., input images vs output images), grids of photos.
        4. **NO**: Generic icons, logos.
        5. **NO**: **Basic Block Diagrams**: If it's just 3 boxes saying "Encoder -> Latent -> Decoder" with no detail, REJECT IT.
        6. **NO**: **Abstract Illustrations**: If it's a "teaser figure" showing a robot shaking hands with a human, REJECT IT. 
        7. **NO**: **Monochrome/Grayscale**: Reject images that are purely black and white. We prefer colored diagrams that use color to distinguish components. 
        
        The diagram must be **informative** and **technical**. Use a score of 8+ ONLY if it is a detailed, implementation-level diagram.

        If "is_methodology" is true, you MUST provide:
        - "logic_summary": A detailed explanation of the system flow or logic relationships shown (2-3 sentences).
        - "visual_style": The design style (e.g., "flat 2D", "isometric 3D", "minimalist line art", "colorful gradient").
        - "keywords": A list of 5-8 relevant technical tags (e.g., "transformer", "attention mechanism", "encoder-decoder").

        Return a valid JSON object (no markdown formatting) with these fields:
        {
            "is_methodology": boolean,
            "quality_score": number (1-10),
            "description": "short description",
            "reason": "reason for score",
            "logic_summary": "...",
            "visual_style": "...",
            "keywords": ["tag1", "tag2"]
        }
        """
        
        # Wait for file to be ready
        while myfile.state.name == "PROCESSING":
             time.sleep(1)
             myfile = genai.get_file(myfile.name)

        if myfile.state.name == "FAILED":
             raise ValueError("File upload failed.")

        result = model.generate_content([myfile, prompt])
        
        # Clean response to get JSON
        text = result.text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
            
        return json.loads(text)

    except Exception as e:
        print(f"[!] Analysis failed: {e}")
        if "404" in str(e) or "not found" in str(e).lower():
            print(f"    [Hint] Model '{model_name}' might not exist. Available models:")
            try:
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        print(f"      - {m.name}")
            except:
                pass
        return {"is_methodology": False, "quality_score": 0, "reason": "Error"}
