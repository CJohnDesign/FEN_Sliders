import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def categorize_summaries(summaries: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    categories = {
        "cover": [],
        "benefits": [],
        "limitations": []
    }
    
    # Sort summaries by page number
    summaries.sort(key=lambda x: x["page"])
    
    for summary in summaries:
        if "cover" in summary["feature_category"].lower():
            categories["cover"].append(summary)
        elif "benefit" in summary["feature_category"].lower():
            categories["benefits"].append(summary)
        elif "limitation" in summary["feature_category"].lower() or "exclusion" in summary["feature_category"].lower():
            categories["limitations"].append(summary)
    
    return categories

def format_bullet_points(text: str) -> List[str]:
    # Split text into bullet points based on periods and semicolons
    points = [p.strip() for p in re.split('[.;]', text) if p.strip()]
    # Ensure each point ends with punctuation
    return [f"{p}{'.' if not p.endswith(('.', '!', '?')) else ''}" for p in points]

async def process_slides(deck_id: str, template: str) -> None:
    deck_path = Path("decks") / deck_id
    summaries_path = deck_path / "ai" / "summaries.json"
    
    logging.info(f"Loading summaries from {summaries_path}")
    with open(summaries_path) as f:
        summaries = json.load(f)
    logging.info(f"Loaded {len(summaries)} summaries")
    
    categories = categorize_summaries(summaries)
    
    slides_content = []
    
    # Front matter
    cover = categories["cover"][0] if categories["cover"] else {"title": "Insurance Overview"}
    slides_content.append(f"""---
id: {deck_id}
theme: ../../
title: | 
  {cover["title"]}
info: |
  ## {cover["title"]}
  A comprehensive look at the insurance benefits and details.
verticalCenter: true
layout: intro
themeConfig:
  logoHeader: img/logos/logo.svg
  audioEnabled: true
transition: fade-out
drawings:
  persist: false
---

<SlideAudio deckKey="{deck_id}" />

# {cover["title"]}

{cover["summary"]}
""")

    # Benefits slides
    for benefit in categories["benefits"]:
        points = format_bullet_points(benefit["summary"])
        slides_content.append(f"""---
transition: fade-out
layout: default
---

## {benefit["title"]}

<v-clicks>

{"".join(f'- {point}\n' for point in points)}

</v-clicks>
""")

    # Limitations slides
    for limitation in categories["limitations"]:
        points = format_bullet_points(limitation["summary"])
        slides_content.append(f"""---
transition: fade-out
layout: default
---

## {limitation["title"]}

<v-clicks>

{"".join(f'- {point}\n' for point in points)}

</v-clicks>
""")

    # Closing slide
    slides_content.append("""---
transition: fade-out
layout: center
class: text-center
---

# Thank You!

For questions or support, please contact us.

<div class="absolute bottom-0 left-0 right-0 p-4">
  <img src="./img/logos/logo.svg" class="h-8 mx-auto" alt="Premier Insurance Logo">
</div>
""")

    # Write slides to file
    slides_path = deck_path / "slides.md"
    with open(slides_path, "w") as f:
        f.write("\n".join(slides_content))
    
    logging.info(f"Generated slides saved to {slides_path}")
    return None 