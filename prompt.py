BASE_SYSTEM_PROMPT = """You are writing a single, standalone beginner lesson for someone with
ZERO prior background in the topic. Assume they have never heard the term before.
 
Requirements:
- Cover: what it is, why it matters (what problem it solves), and how it works.
- Use short, plain sentences (aim for under ~20 words on average).
- Define every technical term in plain language the moment you first use it.
- Include a concrete worked example under a '## Example' header (a sample
  question, what happens step by step, and the final answer).
- Structure the lesson with these headers, in this order:
  '## What is {topic}', '## Why it matters', '## How it works', '## Example', '## Summary'.
- Do not include any factual misconceptions. In particular, be explicit about
  what does and does not happen mechanically (e.g. whether a model is retrained).
- No filler, no marketing language, no unexplained acronyms.
"""
 
def build_initial_prompt(topic:str , standing_instruction:list , topic_notes:list)->str:
    extra = ""
    if standing_instructions:
        extra += "\n\nAdditional standing requirements learned from past runs (do not skip these):\n"
        extra += "\n".join(f"- {s}" for s in standing_instructions)

    if topic_notes:
        extra += "\n\nNotes from previous attempts at this exact topic:\n"
        extra += "\n".join(f"- {n}" for n in topic_notes)

    return BASE_SYSTEM_PROMPT.format(topic=topic) + extra + f"\n\nTopic: {topic}\n\nWrite the lesson now."


def build_regeneration_prompt(topic:str , previous_text:str , failures:list , standing_instruction:list)->str:
    reasons = "\n".join(f"- [{f.name}] FAILED: {f.reason}" for f in failures)
    extra = ""
    if standing_instructions:
        extra += "\n\nAlso keep respecting these standing requirements:\n"
        extra += "\n".join(f"- {s}" for s in standing_instructions)
    return f"""{BASE_SYSTEM_PROMPT.format(topic=topic)}
 
