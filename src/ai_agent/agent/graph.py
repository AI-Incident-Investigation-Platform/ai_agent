import asyncio
import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from time import time
from typing import Annotated

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from ai_agent.agent.decisions import (
    ActionDecision,
    DecisionProvider,
    FinishDecision,
    ToolExecutor,
)
from ai_agent.agent.evidence import (
    collect_evidence,
    link_evidence,
    safe_source_refs,
    update_hypotheses,
)
from ai_agent.agent.execution import ExecutionControl, RunStopped
from ai_agent.agent.state import InvestigationState, LLMProbeState
from ai_agent.domain.models import ExecutionBudget, InvestigationContext
from ai_agent.llm.errors import LLMError, LLMResponseError
from ai_agent.llm.types import ChatMessage, ChatProvider

_DECISION = TypeAdapter(
    Annotated[ActionDecision | FinishDecision, Field(discriminator="kind")]
)


def build_graph(
    decision_provider: DecisionProvider,
    tool_executor: ToolExecutor,
    tool_schemas: Mapping[str, type[BaseModel]],
    *,
    is_cancel_requested: Callable[[str], bool] | None = None,
    clock: Callable[[], float] = time,
    budget_cap: ExecutionBudget | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
):
    control = ExecutionControl(is_cancel_requested, clock)

    async def ingest(state: InvestigationState) -> dict[str, object]:
        context = state.get("context")
        if (
            context is None
            or str(context.investigation_id) != state["investigation_id"]
        ):
            raise ValueError("Graph state has no matching investigation context")
        if state.get("terminal_status"):
            return {}
        limits = context.budget.model_dump()
        if budget_cap is not None:
            limits = {
                key: min(value, getattr(budget_cap, key))
                for key, value in limits.items()
            }
        budget = ExecutionBudget.model_validate(limits)
        deadline = clock() + budget.timeout_seconds
        return {
            "budget": budget,
            "deadline_at": min(deadline, state.get("deadline_at", deadline)),
            "step": state.get("step", 0),
            "tool_calls_count": state.get("tool_calls_count", 0),
            "action_history": state.get("action_history", []),
            "observations": state.get("observations", []),
            "evidence": state.get("evidence", []),
            "hypotheses": state.get("hypotheses", []),
            "hypothesis_relations": state.get("hypothesis_relations", {}),
            "event_summaries": state.get("event_summaries", []),
        }

    async def decide(state: InvestigationState) -> dict[str, object]:
        try:
            control.check(state)
        except RunStopped as exc:
            return exc.state_update()
        if state["step"] >= state["budget"].max_steps:
            return {
                "terminal_status": "inconclusive",
                "terminal_reason": "step_limit",
                "event_summaries": [*state["event_summaries"], "Step limit reached"],
            }
        for attempt in range(2):
            try:
                async with control.bounded(state):
                    if attempt:
                        await asyncio.sleep(0.05)
                        control.check(state)
                    raw = await decision_provider.decide(state)
                control.check(state)
                if not isinstance(raw, (ActionDecision, FinishDecision)):
                    raise ValueError("Decision must be a typed action or finish")
                decision = _DECISION.validate_python(raw)
                break
            except RunStopped as exc:
                return {**exc.state_update(), "step": state["step"] + 1}
            except LLMResponseError, ValueError, TypeError:
                if attempt == 1:
                    return {
                        "step": state["step"] + 1,
                        "terminal_status": "inconclusive",
                        "terminal_reason": "invalid_decision",
                        "event_summaries": [
                            *state["event_summaries"],
                            "Decision validation failed",
                        ],
                    }
            except LLMError, TimeoutError:
                return {
                    "step": state["step"] + 1,
                    "terminal_status": "failed",
                    "terminal_reason": "model_unavailable",
                }
            except Exception:
                return {
                    "step": state["step"] + 1,
                    "terminal_status": "failed",
                    "terminal_reason": "decision_error",
                }
        if isinstance(decision, FinishDecision):
            try:
                hypotheses, relations = update_hypotheses(
                    state["context"],
                    decision.hypotheses,
                    state["evidence"],
                    updated_at=datetime.now(UTC),
                )
            except ValidationError, ValueError, TypeError:
                return {
                    "step": state["step"] + 1,
                    "terminal_status": "inconclusive",
                    "terminal_reason": "invalid_hypothesis",
                    "event_summaries": [
                        *state["event_summaries"],
                        "Hypothesis validation failed",
                    ],
                }
            if not state["evidence"]:
                return {
                    "step": state["step"] + 1,
                    "hypotheses": hypotheses,
                    "hypothesis_relations": relations,
                    "terminal_status": "inconclusive",
                    "terminal_reason": "insufficient_evidence",
                    "event_summaries": [
                        *state["event_summaries"],
                        "No verified evidence was collected",
                    ],
                }
            return {
                "step": state["step"] + 1,
                "evidence": link_evidence(state["evidence"], hypotheses),
                "hypotheses": hypotheses,
                "hypothesis_relations": relations,
                "terminal_status": "ready_for_finalization",
                "terminal_reason": "agent_finished",
                "event_summaries": [
                    *state["event_summaries"],
                    "Agent finished selecting actions",
                ],
            }
        return {
            "step": state["step"] + 1,
            "pending_action": decision.model_dump(),
            "event_summaries": [
                *state["event_summaries"],
                "Agent selected an action",
            ],
        }

    async def validate_action(state: InvestigationState) -> dict[str, object]:
        try:
            control.check(state)
        except RunStopped as exc:
            return exc.state_update()
        action = ActionDecision.model_validate(state["pending_action"])
        schema = tool_schemas.get(action.name)
        if schema is None or schema.model_config.get("extra") != "forbid":
            reason = "unavailable_tool"
        elif state["tool_calls_count"] >= state["budget"].max_tool_calls:
            reason = "tool_call_limit"
        else:
            try:
                args = schema.model_validate_json(
                    json.dumps(action.arguments), strict=True
                ).model_dump(mode="json", by_alias=True)
                context = state["context"]
                if action.name == "get_incident_context":
                    if str(args.get("incident_id")) != str(context.incident_id) or str(
                        args.get("investigation_id")
                    ) != str(context.investigation_id):
                        raise ValueError("Incident outside investigation scope")
                elif "project_id" not in args or str(args["project_id"]) != str(
                    context.project_id
                ):
                    raise ValueError("Project outside investigation scope")
                if "environment_id" in args and str(args["environment_id"]) != str(
                    context.environment_id
                ):
                    raise ValueError("Environment outside investigation scope")
                service_ids = args.get("service_ids", [])
                if "service_id" in args:
                    service_ids = [*service_ids, args["service_id"]]
                allowed_services = {str(item) for item in context.service_ids}
                if any(str(item) not in allowed_services for item in service_ids):
                    raise ValueError("Service outside investigation scope")
                signature = json.dumps([action.name, args], sort_keys=True)
                if signature in state["action_history"]:
                    raise ValueError("Repeated action")
            except ValidationError, ValueError, TypeError:
                reason = "invalid_or_out_of_scope_action"
            else:
                return {
                    "validated_action": {**action.model_dump(), "arguments": args},
                    "action_history": [*state["action_history"], signature],
                }
        return {
            "validated_action": None,
            "pending_action": None,
            "terminal_status": "inconclusive",
            "terminal_reason": reason,
            "event_summaries": [*state["event_summaries"], "Action rejected"],
        }

    async def execute(state: InvestigationState) -> dict[str, object]:
        action = state["validated_action"]
        count = state["tool_calls_count"]
        try:
            async with control.bounded(state):
                count += 1
                result = await tool_executor.execute(
                    action["name"], action["arguments"]
                )
        except RunStopped as exc:
            return {**exc.state_update(), "tool_calls_count": count}
        except Exception:
            result = {
                "status": "error",
                "summary": "Tool execution failed",
                "source_refs": [],
                "items": [],
                "truncated": False,
                "error": {"code": "tool_error", "message": "Tool execution failed"},
            }
        observation = normalize_result(action, result, state["context"])
        try:
            evidence = collect_evidence(
                state["context"],
                action,
                result if isinstance(result, dict) else {},
                state["evidence"],
                collected_at=datetime.now(UTC),
            )
        except ValidationError, ValueError, TypeError:
            evidence = state["evidence"]
        return {
            "tool_calls_count": count,
            "pending_action": {**action, "observation": observation},
            "evidence": evidence,
        }

    def normalize_result(
        action: dict[str, object], result: object, context: InvestigationContext
    ) -> dict[str, object]:
        try:
            if not isinstance(result, dict) or result.get("status") not in {
                "ok",
                "empty",
                "partial",
                "error",
            }:
                raise ValueError("Invalid tool result")
            refs = safe_source_refs(result["source_refs"], context)
            if not isinstance(result.get("items"), list) or not isinstance(
                result.get("truncated"), bool
            ):
                raise ValueError("Invalid tool result")
            status = result["status"]
            truncated = result["truncated"]
            error = result.get("error")
            error_code = error.get("code") if isinstance(error, dict) else None
        except KeyError, TypeError, ValueError, ValidationError:
            status, refs, truncated, error_code = "error", [], False, "invalid_result"
        return {
            "tool_call_id": action["tool_call_id"],
            "tool_name": action["name"],
            "status": status,
            "summary": f"{action['name']}: {status}",
            "source_refs": refs,
            "truncated": truncated,
            "error_code": error_code,
        }

    async def normalize(state: InvestigationState) -> dict[str, object]:
        action = state["pending_action"]
        observation = action["observation"]
        return {
            "observations": [*state["observations"], observation],
            "pending_action": None,
            "validated_action": None,
            "event_summaries": [
                *state["event_summaries"],
                f"{action['name']} returned {observation['status']}",
            ],
        }

    graph = StateGraph(InvestigationState)
    graph.add_node("ingest", ingest)
    graph.add_node("decide", decide)
    graph.add_node("validate_action", validate_action)
    graph.add_node("execute", execute)
    graph.add_node("normalize", normalize)
    graph.add_edge(START, "ingest")
    graph.add_conditional_edges(
        "ingest", lambda state: END if state.get("terminal_status") else "decide"
    )
    graph.add_conditional_edges(
        "decide",
        lambda state: END if state.get("terminal_status") else "validate_action",
    )
    graph.add_conditional_edges(
        "validate_action",
        lambda state: END if state.get("terminal_status") else "execute",
    )
    graph.add_conditional_edges(
        "execute", lambda state: END if state.get("terminal_status") else "normalize"
    )
    graph.add_edge("normalize", "decide")
    return graph.compile(checkpointer=checkpointer).with_config(
        {"recursion_limit": 160}
    )


def build_llm_probe_graph(provider: ChatProvider):

    async def call_model(state: LLMProbeState) -> dict[str, str]:
        completion = await provider.chat([ChatMessage("user", state["prompt"])])
        if completion.tool_calls:
            raise LLMResponseError("Tool calls are not supported by the probe graph")
        if not completion.content:
            raise LLMResponseError("Local inference returned no text")
        return {"response": completion.content}

    graph = StateGraph(LLMProbeState)
    graph.add_node("call_model", call_model)
    graph.add_edge(START, "call_model")
    graph.add_edge("call_model", END)
    return graph.compile()
