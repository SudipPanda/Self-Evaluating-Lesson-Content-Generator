"""
This is the main graph structure here
 
    START -> generate -> evaluate --pass/fail?--> END
                ^                        |
                |___________retry________|
"""

import json
import os 
from typing import TypeDict , Optional , Any ,List
from langgraph.graph import StateGraph , End
from prompt import build_initial_prompt , build_regeneration_prompt
from vector_memory import VectorMemory
from evaluator import evaluate , CheckResult

MAX_RETRIES = 2
class AttenptRecord(TypeDict):
    attempt : int
    passed: bool
    failed_checkpoints: List[str]

class LessonState(TypeDict):
    topic: str
    llm_client: Any
    memory:Any
    passed:bool
    prompt:str
    attempt_num:int
    failures:List[CheckResukt]
    text_output:str
    retrieved_notes: List[str]
    attempt_historya: List[AttenptRecord]
    reject_logs = list


def node_generate(state:LessonState)->dict:
    attempt_num = state['attempt_num']+1
    memeory : VectorMemory = state['memory']
    standing = memory.standing_instructions()

    retrieved_notes = memory.retrieve_relevant_notes(state["topic"], k=3)

    if attempt_num == 1:
        prompt = build_initial_prompt(
            state['topic'] ,
            standing , 
            retrieved_notes

        )
    else:

        prompt = build_regeneration_prompt(
            state["topic"], state["text"], state["failures"], standing,)
        
    text = state['llm_client'].generate(prompt)
    return {
        "attempt_num" : attempt_num , 
        "prompt":prompt , 
        "text_output":text,
        "retrieved_notes":retrieved_notes
    }

def node_evaluate(state:LessonState)->dict:
    # we are evaluating the output text here 
    text_to_judge = evaluate(state['text_output'])

    #getting the memory here 
    memory: VectorMemory = state['memory']
    #recording the attempt number here 
    attenmpt_num = state['attempt_num']

    os.makedirs(state["log_dir"], exist_ok=True)
    
    """Saving the text file here"""
    with open(os.path.join(state["log_dir"], f"attempt_{attempt_num}.md"), "w") as f:
        f.write(state["text_output"])
    
    """report dump here"""
    with open(os.path.join(state["log_dir"], f"attempt_{attempt_num}_eval.json"), "w") as f:
        json.dump(text_to_judge.as_dict(), f, indent=2)
    
    """Saving the prompt here"""
    with open(os.path.join(state["log_dir"], f"attempt_{attempt_num}_prompt.txt"), "w") as f:
        f.write(state["prompt"])
    
    #save for the long term memory here
    memory.record_attempt(state["topic"], attempt_num, text_to_judge.failures, text_to_judge.passed)
    
    #here update the short term memory here 
    attempt_history = state["attempt_history"] + [{
        "attempt": attempt_num,
        "passed": report.passed,
        "failed_checkpoints": [f.name for f in report.failures],
    }]

    log_entry = {
        "attempt": attempt_num,
        "result": "PASSED" if report.passed else "FAILED",
        "checks": [r.__dict__ for r in report.results],
    }

    rejection_log = state["rejection_log"] + [log_entry]

    return {
        "passed": report.passed,
        "failures": report.failures,
        "rejection_log": rejection_log,
        "attempt_history": attempt_history,
    }

def route_after_eval(state:LessonState)->str:
    if state["passed"]:
        return "end_passed"
    if state["attempt_num"] >= MAX_RETRIES+1:
        return "end_exhausted"
    return "retry"

def build_graph():
    graph = StateGraph(LessonState)
    graph.add_node("generate" , node_generate)
    graph.add_node("evaluate" , node_evaluate)
    graph.set_entry_point("generate")
    graph.add_edge("generate" , "evaluate")
    graph.add_conditional_edges(
        "evaluate" ,
        route_after_eval , 
        {"end_passed": END, "end_exhausted": END, "retry": "generate"},
    )

    return graph.compile()


 









