from typing import Annotated, Any, Dict, List, TypedDict
from langgraph.graph import Graph, StateGraph
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage

# Define the state structure
class ResearchState(TypedDict):
    question: str
    research_plan: List[str]
    findings: List[str]
    current_task: str
    final_answer: str
    messages: List[Any]
    should_continue: bool
    error: str | None
    iteration_count: int
    steps_taken: int  # Add step counter


# Initialize Claude
model = ChatAnthropic(
  model="claude-3-sonnet-20240229"
)

# Create the research planner agent
def create_research_plan(state: ResearchState) -> ResearchState:
    try:
        planner_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a research planning assistant. Break down complex questions into smaller research tasks."),
            ("human", "Create a research plan for the following question: {question}")
        ])
        
        response = model.invoke(planner_prompt.format_messages(question=state["question"]))
        research_plan = [task.strip() for task in response.content.split('\n') if task.strip()]
        
        if not research_plan:
            raise ValueError("No valid research tasks generated")
            
        return {
            **state,
            "research_plan": research_plan,
            "current_task": research_plan[0] if research_plan else "",
            "findings": [],
            "should_continue": bool(research_plan),
            "steps_taken": 0
        }
    except Exception as e:
        print(f"Error in create_research_plan: {str(e)}")
        return {
            **state,
            "error": f"Failed to create research plan: {str(e)}",
            "should_continue": False
        }

# Create the researcher agent
def conduct_research(state: ResearchState) -> ResearchState:
    try:
        # Increment step counter
        steps_taken = state["steps_taken"] + 1
        
        researcher_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a thorough researcher. Provide concise but comprehensive findings for the current task.
            Focus on key information and avoid redundancy."""),
            ("human", """Research task: {current_task}
            
            Context:
            Main Question: {question}
            Previous Findings: {findings}
            
            Provide a focused response addressing this specific task.""")
        ])
        
        response = model.invoke(researcher_prompt.format_messages(
            current_task=state["current_task"],
            question=state["question"],
            findings="\n".join(state["findings"])
        ))
        
        findings = state["findings"] + [response.content]
        remaining_tasks = state["research_plan"][1:] if len(state["research_plan"]) > 1 else []
        
        return {
            **state,
            "findings": findings,
            "research_plan": remaining_tasks,
            "current_task": remaining_tasks[0] if remaining_tasks else "",
            "should_continue": bool(remaining_tasks) and steps_taken < 5,
            "steps_taken": steps_taken,
            "messages": state["messages"] + [HumanMessage(content=state["current_task"]), AIMessage(content=response.content)],
            "error": None  # Clear any previous errors
        }
    except Exception as e:
        print(f"Error in conduct_research: {str(e)}")
        return {
            **state,
            "error": f"Research failed: {str(e)}",
            "should_continue": False
        }

def synthesize_findings(state: ResearchState) -> ResearchState:
    try:
        synthesizer_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a synthesis expert. Create a concise but comprehensive summary of the research findings."),
            ("human", """Synthesize these findings to answer the original question:
            
            Question: {question}
            Findings:
            {findings}
            
            Provide a clear, well-structured answer.""")
        ])
        
        response = model.invoke(synthesizer_prompt.format_messages(
            question=state["question"],
            findings="\n\n".join(state["findings"])
        ))
        
        return {
            **state,
            "final_answer": response.content,
            "messages": state["messages"] + [AIMessage(content=response.content)],
            "error": None
        }
    except Exception as e:
        print(f"Error in synthesize_findings: {str(e)}")
        return {
            **state,
            "error": f"Synthesis failed: {str(e)}",
            "final_answer": "Failed to synthesize findings due to an error."
        }

def should_continue(state: ResearchState) -> str:
    # Add error check
    if state.get("error"):
        return "synthesize"
    if state["should_continue"] and state["steps_taken"] < 5:
        return "continue_research"
    return "synthesize"


# Create the workflow graph
workflow = StateGraph(ResearchState)

# Add nodes
workflow.add_node("create_plan", create_research_plan)
workflow.add_node("research", conduct_research)
workflow.add_node("synthesize", synthesize_findings)

# Add edges
workflow.add_edge("create_plan", "research")
workflow.add_conditional_edges(
    "research",
    should_continue,
    {
        "continue_research": "research",
        "synthesize": "synthesize"
    }
)
workflow.set_entry_point("create_plan")
workflow.set_finish_point("synthesize")

# Compile the graph
graph = workflow.compile()

# Function to run the research workflow
def run_research(question: str) -> Dict:
    print(question)
    initial_state = {
        "question": question,
        "research_plan": [],
        "findings": [],
        "current_task": "",
        "final_answer": "",
        "messages": [],
        "should_continue": True,
        "error": None,
        "iteration_count": 0
    }
    print(initial_state)
    result = graph.invoke(initial_state, config={"recursion_limit": 15})
    return result