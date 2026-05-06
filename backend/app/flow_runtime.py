import json
import re

from sqlalchemy.orm import Session

from .models import Bot, FlowDefinition


def resolve_action_reply(db: Session, bot: Bot, incoming_text: str) -> tuple[str | None, str]:
    flow = db.query(FlowDefinition).filter(FlowDefinition.bot_id == bot.id).first()
    if not flow:
        return None, "Flow runtime: no flow definition"

    try:
        data = json.loads(flow.draft_schema or '{"blocks":[],"edges":[]}')
    except json.JSONDecodeError:
        return None, "Flow runtime: invalid JSON in draft_schema"

    if isinstance(data, list):
        data = {"blocks": data, "edges": []}

    blocks = data.get("blocks") or []
    edges = data.get("edges") or []
    if not blocks or not edges:
        return None, "Flow runtime: blocks/edges are empty"

    blocks_by_id = {block.get("id"): block for block in blocks if isinstance(block, dict)}
    trigger = next((block for block in blocks if block.get("type") == "trigger"), None)
    if not trigger:
        return None, "Flow runtime: trigger block not found"

    trigger_paths = trigger.get("trigger_paths")
    branch: str
    if isinstance(trigger_paths, list) and trigger_paths:
        branch = "fallback"
        matched_path_name = None
        for path in trigger_paths:
            if not isinstance(path, dict):
                continue
            path_id = path.get("id")
            path_name = path.get("name")
            path_regex = path.get("regex")
            if not isinstance(path_id, str) or not isinstance(path_regex, str):
                continue
            try:
                if re.search(path_regex, incoming_text):
                    branch = path_id
                    matched_path_name = path_name if isinstance(path_name, str) else path_id
                    break
            except re.error:
                continue
        if matched_path_name:
            debug_match = f"path={matched_path_name}"
        else:
            debug_match = "path=fallback"
    else:
        pattern = trigger.get("condition_regex")
        if not isinstance(pattern, str) or not pattern:
            return None, "Flow runtime: trigger condition_regex is empty"
        try:
            matched = bool(re.search(pattern, incoming_text))
        except re.error:
            return None, "Flow runtime: invalid trigger regex"
        branch = "true" if matched else "false"
        debug_match = f"branch={branch}"

    trigger_id = trigger.get("id")
    next_edge = next(
        (
            edge
            for edge in edges
            if isinstance(edge, dict)
            and edge.get("from_block_id") == trigger_id
            and edge.get("when") == branch
        ),
        None,
    )
    if not next_edge:
        fallback = trigger.get("fallback_action_value")
        if isinstance(fallback, str) and fallback.strip():
            return fallback.strip(), f"Flow runtime: {debug_match}, fallback_action_value used"
        return None, f"Flow runtime: {debug_match}, no edge and no fallback"

    target_block = blocks_by_id.get(next_edge.get("to_block_id"))
    if not target_block or target_block.get("type") != "action":
        fallback = trigger.get("fallback_action_value")
        if isinstance(fallback, str) and fallback.strip():
            return fallback.strip(), "Flow runtime: target action missing, fallback_action_value used"
        return None, "Flow runtime: target action missing and no fallback"

    action_type = target_block.get("action_type")
    if action_type != "return_string":
        fallback = trigger.get("fallback_action_value")
        if isinstance(fallback, str) and fallback.strip():
            return fallback.strip(), "Flow runtime: unsupported action_type, fallback_action_value used"
        return None, "Flow runtime: unsupported action_type and no fallback"
    action_value = target_block.get("action_value")
    if not isinstance(action_value, str) or not action_value.strip():
        fallback = trigger.get("fallback_action_value")
        if isinstance(fallback, str) and fallback.strip():
            return fallback.strip(), "Flow runtime: empty action_value, fallback_action_value used"
        return None, "Flow runtime: empty action_value and no fallback"

    target_id = target_block.get("id")
    return action_value.strip(), f"Flow runtime: {debug_match}, action={target_id}, action_type=return_string"
