import re
from dataclasses import dataclass , field
from typing import Callable , List

@dataclass
class CheckResult:
    name:str
    passed: bool
    reson:bool

@dataclass
class EvalReport:
    result:List[CheckResult] = field(default_dactory=list)
    @property
    def passed(self)->bool:
        return all(r.passed for r in self.result)
    @property
    def failures(self)->List[CheckResult]:
        return [r for r in self.result if not r.passed]

# ---------------------------------------------------------------------------
# Checkpoint 1: accurate & grounded
# ---------------------------------------------------------------------------


def check_accurate_grounded(text:str, llm=None)->CheckResult:
    if llm is not None:
        judge_prompt = f"""Judge whether the lesson below is accurate and grounded.
            Reject claims that are factually unsupported, overconfident, or mechanically misleading.
            Return only valid JSON with exactly two fields: passed (true or false) and reason (a short string).

            Lesson:
            {text}
            """
        try:
            response = llm.invoke(judge_prompt) if hasattr(llm, "invoke") else llm.generate(judge_prompt)
            if hasattr(response, "content"):
                response = response.content
            elif hasattr(response, "generations"):
                response = response.generations[0][0].text
            response = str(response).strip()
            response = re.sub(r"^```(?:json)?\s*|\s*```$", "", response, flags=re.IGNORECASE)
            verdict = __import__("json").loads(response)
            passed = verdict.get("passed")
            reason = verdict.get("reason")
            if isinstance(passed, bool) and isinstance(reason, str) and reason.strip():
                return CheckResult("accurate_grounded", passed, reason.strip())
        except (AttributeError, IndexError, TypeError, ValueError, KeyError):
            pass

    low = text.lower()
    misconception_patterns = [
        r"(?:the )?model\s+(?:is|gets)\s+retrained",
        r"the model\s+learns?\s+(?:permanently|forever|from this conversation)",
        r"(?:guarantees?|always|never)\s+(?:correct|accurate|true)",
    ]
    has_caveat = bool(re.search(
        r"\b(?:may|might|can|not always|depends|limitations?|uncertain)\b",
        low,
    ))
    has_mechanism = bool(re.search(
        r"\b(?:works?|happens?|process|step|input|output|because|means?)\b",
        low,
    ))
    has_misconception = any(re.search(pattern, low) for pattern in misconception_patterns)
    passed = bool(text.strip()) and has_mechanism and not has_misconception
    reason = "The lesson describes a mechanism without a known misconception."
    if not text.strip():
        reason = "The lesson is empty."
    elif has_misconception:
        reason = "The lesson contains an overly strong or mechanically inaccurate claim."
    elif not has_mechanism:
        reason = "The lesson does not explain how the subject works."
        
    return CheckResult("accurate_grounded", passed, reason)

# ---------------------------------------------------------------------------
# Checkpoint 2: beginner-friendly language
# --------------------------------------------------------------------------
def check_beginner_friendly(text:str)->CheckResult:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    words = re.findall(r"\b[\w'-]+\b", text)
    average_length = len(words) / len(sentences) if sentences else 0
    long_sentences = sum(
        len(re.findall(r"\b[\w'-]+\b", sentence)) > 30
        for sentence in sentences
    )
    has_definition = bool(re.search(
        r"\b(?:means|is|are|refers to|defined as)\b", text, re.IGNORECASE
    ))
    passed = bool(words) and average_length <= 24 and long_sentences <= max(1, len(sentences) // 5) and has_definition
    reason = "The lesson uses short sentences and defines its subject."
    if not words:
        reason = "The lesson is empty."
    elif average_length > 24 or long_sentences > max(1, len(sentences) // 5):
        reason = "The lesson uses too many long sentences for a beginner audience."
    elif not has_definition:
        reason = "The lesson does not clearly define the subject."
    return CheckResult("beginner_friendly", passed, reason)

# ---------------------------------------------------------------------------
# Checkpoint 3: check any exemple were given or not in text
# ---------------------------------------------------------------------------
EXAMPLE_MARKERS = [r"for example", r"let.?s say", r"imagine", r"picture this",
                    r"for instance", r"here.?s an example", r"walk(ing)? through an example"]

def check_teaches_by_example(text:str)->CheckResult:
    low = text.lower()
    has_marker = any(re.search(marker, low) for marker in EXAMPLE_MARKERS)
    has_example_header = bool(re.search(r"^\s*#+\s*example\b", text, re.IGNORECASE | re.MULTILINE))
    has_steps = bool(re.search(r"\b(?:first|then|next|finally|step\s*\d+)\b", low))
    passed = (has_marker or has_example_header) and has_steps
    reason = "The lesson includes a concrete example with a sequence of steps."
    if not (has_marker or has_example_header):
        reason = "The lesson does not include an example."
    elif not has_steps:
        reason = "The example is not worked through step by step."
    return CheckResult("teaches_by_example", passed, reason)


# ---------------------------------------------------------------------------
# Checkpoint 4: no unexplained jargon
# ---------------------------------------------------------------------------
def check_no_unexplained_jargon(text:str)->CheckResult:
    acronym_pattern = r"\b[A-Z]{2,}\b"
    acronyms = set(re.findall(acronym_pattern, text))
    explained_acronyms = {
        acronym for acronym in acronyms
        if re.search(rf"\b[A-Za-z][^.!?\n]*\b{re.escape(acronym)}\b", text)
        and re.search(rf"\b{re.escape(acronym)}\s*\([^)]*\)", text)
    }
    unexplained_acronyms = acronyms - explained_acronyms
    technical_terms = re.findall(
        r"\b(?:algorithm|API|embedding|inference|latency|token|vector|parameter)\b",
        text,
        re.IGNORECASE,
    )
    terms_with_definitions = sum(
        bool(re.search(rf"\b{re.escape(term)}\b[^.!?\n]{{0,80}}\b(?:means|is|are|refers to)\b", text, re.IGNORECASE))
        for term in set(technical_terms)
    )
    passed = not unexplained_acronyms and terms_with_definitions == len(set(technical_terms))
    reason = "Technical terms and acronyms are explained."
    if unexplained_acronyms:
        reason = "The lesson contains unexplained acronyms: " + ", ".join(sorted(unexplained_acronyms)) + "."
    elif terms_with_definitions != len(set(technical_terms)):
        reason = "The lesson uses technical terms without defining all of them."
    return CheckResult("no_unexplained_jargon", passed, reason)



 
# ---------------------------------------------------------------------------
# Checkpoint 5: check whether the explanation has check point or not 
# ---------------------------------------------------------------------------

def check_covers_key_points(text:str)->CheckResult:
    low = text.lower()
    required_topics = {
        "what_it_is": r"\b(?:what is|is a|refers to|means)\b",
        "why_it_matters": r"\b(?:why it matters|useful|problem|benefit|helps)\b",
        "how_it_works": r"\b(?:how it works|works|process|step|input|output)\b",
        "summary": r"\b(?:summary|in short|to recap|remember)\b",
    }
    missing = [name for name, pattern in required_topics.items() if not re.search(pattern, low)]
    passed = not missing
    reason = "The lesson covers what it is, why it matters, how it works, and a summary."
    if missing:
        reason = "The lesson is missing: " + ", ".join(missing) + "."
    return CheckResult("covers_key_points", passed, reason)


# ---------------------------------------------------------------------------
# Checkpoint 6: coherent teaching flow
# ---------------------------------------------------------------------------
def check_coherent_flow(text:str)->CheckResult:
    required_headers = [
        r"what is\b",
        r"why it matters\b",
        r"how it works\b",
        r"example\b",
        r"summary\b",
    ]
    positions = []
    for header in required_headers:
        match = re.search(r"^\s*#+\s*" + header, text, re.IGNORECASE | re.MULTILINE)
        if not match:
            return CheckResult("coherent_flow", False, "The lesson is missing a required section header.")
        positions.append(match.start())
    passed = positions == sorted(positions)
    reason = "The lesson follows the expected teaching order."
    if not passed:
        reason = "The lesson sections are not in the expected teaching order."
    return CheckResult("coherent_flow", passed, reason)




CHECKS = [
    check_accurate_grounded,
    check_beginner_friendly,
    check_teaches_by_example,
    check_no_unexplained_jargon,
    check_covers_key_points,
    check_coherent_flow,
]

def evaluate(text:str, llm=None)->EvalReport:
    report = EvalReport()
    for check in CHECKS:
        if check is check_accurate_grounded:
            report.result.append(check(text, llm))
        else:
            report.result.append(check(text))

    return report 