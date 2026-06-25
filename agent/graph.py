import os

from dotenv import load_dotenv
from langchain_core.globals import set_verbose, set_debug
from langchain_openai import AzureChatOpenAI
from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent

from agent.prompts import *
from agent.states import *
from agent.tools import write_file, read_file, get_current_directory, list_files

_ = load_dotenv()

set_debug(True)
set_verbose(True)

# Shared LLM client used by every agent node in the graph.
# Backed by Azure AI Foundry (Azure OpenAI). Only the *base* resource endpoint is
# needed (e.g. https://<resource>.services.ai.azure.com); the client builds the
# full request URL from the deployment name and API version. All values come from
# environment variables (see .sample_env).
llm = AzureChatOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    model=os.environ.get("AZURE_OPENAI_MODEL"),
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
)


def planner_agent(state: dict) -> dict:
    """Planner node: turn the raw user prompt into a structured ``Plan``.

    Reads ``user_prompt`` from the graph state and asks the LLM to emit a
    high-level project plan (name, tech stack, features, files).
    """
    user_prompt = state["user_prompt"]
    project_plan = llm.with_structured_output(Plan, method="function_calling").invoke(
        planner_prompt(user_prompt)
    )
    if project_plan is None:
        raise ValueError("Planner did not return a valid response.")
    return {"plan": project_plan}


def architect_agent(state: dict) -> dict:
    """Architect node: expand a ``Plan`` into an ordered ``TaskPlan``.

    Breaks the project plan into explicit, dependency-ordered implementation
    tasks and carries the original plan forward on the returned task plan.
    """
    project_plan: Plan = state["plan"]
    task_plan = llm.with_structured_output(TaskPlan, method="function_calling").invoke(
        architect_prompt(plan=project_plan.model_dump_json())
    )
    if task_plan is None:
        raise ValueError("Architect did not return a valid response.")

    task_plan.plan = project_plan
    print(task_plan.model_dump_json())
    return {"task_plan": task_plan}


def coder_agent(state: dict) -> dict:
    """Coder node: implement the current task using a tool-using ReAct agent.

    Advances through the implementation steps one at a time. Each invocation
    loads the file's existing content, lets the ReAct agent edit it via the
    file tools, then increments the step index. Signals ``DONE`` once every
    step has been processed.
    """
    coder_state: CoderState = state.get("coder_state")
    if coder_state is None:
        coder_state = CoderState(task_plan=state["task_plan"], current_step_idx=0)

    implementation_steps = coder_state.task_plan.implementation_steps
    if coder_state.current_step_idx >= len(implementation_steps):
        return {"coder_state": coder_state, "status": "DONE"}

    current_task = implementation_steps[coder_state.current_step_idx]
    existing_content = read_file.run(current_task.filepath)

    system_prompt = coder_system_prompt()
    user_prompt = (
        f"Task: {current_task.task_description}\n"
        f"File: {current_task.filepath}\n"
        f"Existing content:\n{existing_content}\n"
        "Use write_file(path, content) to save your changes."
    )

    coder_tools = [read_file, write_file, list_files, get_current_directory]
    react_agent = create_react_agent(llm, coder_tools)

    react_agent.invoke({"messages": [{"role": "system", "content": system_prompt},
                                     {"role": "user", "content": user_prompt}]})

    coder_state.current_step_idx += 1
    return {"coder_state": coder_state}


# Wire the three agent nodes into a LangGraph state machine:
#   planner -> architect -> coder -> (loop until DONE) -> END
graph = StateGraph(dict)

graph.add_node("planner", planner_agent)
graph.add_node("architect", architect_agent)
graph.add_node("coder", coder_agent)

graph.add_edge("planner", "architect")
graph.add_edge("architect", "coder")
# Loop back into the coder node until it reports DONE, then terminate.
graph.add_conditional_edges(
    "coder",
    lambda state: "END" if state.get("status") == "DONE" else "coder",
    {"END": END, "coder": "coder"}
)

graph.set_entry_point("planner")
agent = graph.compile()
if __name__ == "__main__":
    result = agent.invoke({"user_prompt": "Build a colourful modern todo app in html css and js"},
                          {"recursion_limit": 100})
    print("Final State:", result)
