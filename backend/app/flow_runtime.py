import json
import re

from sqlalchemy.orm import Session

from .models import Bot, BotDialogState, FlowDefinition


YES_WORDS = {
    "да",
    "д",
    "yes",
    "y",
    "ok",
    "ага",
    "угу",
    "конечно",
    "верно",
}
NO_WORDS = {
    "нет",
    "н",
    "no",
    "n",
    "неа",
    "не",
    "отмена",
}


def _normalize_text(value: str) -> str:
    return value.strip().lower()


def _is_yes(value: str) -> bool:
    normalized = _normalize_text(value)
    return normalized in YES_WORDS


def _is_no(value: str) -> bool:
    normalized = _normalize_text(value)
    return normalized in NO_WORDS


def _find_dialog_state(db: Session, bot_id: int, chat_id: str) -> BotDialogState | None:
    return (
        db.query(BotDialogState)
        .filter(BotDialogState.bot_id == bot_id, BotDialogState.telegram_chat_id == chat_id)
        .first()
    )


def resolve_action_reply(db: Session, bot: Bot, incoming_text: str, chat_id: str | None = None) -> tuple[str | None, str]:
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

    dialog_state = None
    waiting_trigger_id = None
    if isinstance(chat_id, str) and chat_id.strip():
        dialog_state = _find_dialog_state(db, bot.id, chat_id)
        if dialog_state and isinstance(dialog_state.waiting_trigger_block_id, str):
            waiting_trigger_id = dialog_state.waiting_trigger_block_id
            waiting_trigger = blocks_by_id.get(waiting_trigger_id)
            if isinstance(waiting_trigger, dict) and waiting_trigger.get("type") == "trigger":
                trigger = waiting_trigger
            else:
                dialog_state.waiting_trigger_block_id = None
                db.commit()
                waiting_trigger_id = None

    trigger_paths = trigger.get("trigger_paths")
    branch: str
    if isinstance(trigger_paths, list) and trigger_paths:
        branch = "fallback"
        matched_path_name = None
        matched_path_type = None
        for path in trigger_paths:
            if not isinstance(path, dict):
                continue
            path_id = path.get("id")
            path_name = path.get("name")
            path_regex = path.get("regex")
            path_type = path.get("match_type")
            if not isinstance(path_type, str) or path_type not in ("regex", "yes", "no", "any"):
                path_type = "regex"
            if not isinstance(path_id, str):
                continue
            if path_type == "yes":
                if _is_yes(incoming_text):
                    branch = path_id
                    matched_path_name = path_name if isinstance(path_name, str) else path_id
                    matched_path_type = "yes"
                    break
                continue
            if path_type == "no":
                if _is_no(incoming_text):
                    branch = path_id
                    matched_path_name = path_name if isinstance(path_name, str) else path_id
                    matched_path_type = "no"
                    break
                continue
            if path_type == "any":
                branch = path_id
                matched_path_name = path_name if isinstance(path_name, str) else path_id
                matched_path_type = "any"
                break
            if not isinstance(path_regex, str):
                continue
            try:
                if re.search(path_regex, incoming_text):
                    branch = path_id
                    matched_path_name = path_name if isinstance(path_name, str) else path_id
                    matched_path_type = "regex"
                    break
            except re.error:
                continue
        if matched_path_name:
            debug_match = f"path={matched_path_name}, match_type={matched_path_type}"
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
        if dialog_state and waiting_trigger_id:
            dialog_state.waiting_trigger_block_id = None
            db.commit()
        if isinstance(fallback, str) and fallback.strip():
            return fallback.strip(), f"Flow runtime: {debug_match}, fallback_action_value used"
        return None, f"Flow runtime: {debug_match}, no edge and no fallback"

    target_block = blocks_by_id.get(next_edge.get("to_block_id"))
    if not target_block or target_block.get("type") != "action":
        fallback = trigger.get("fallback_action_value")
        if dialog_state and waiting_trigger_id:
            dialog_state.waiting_trigger_block_id = None
            db.commit()
        if isinstance(fallback, str) and fallback.strip():
            return fallback.strip(), "Flow runtime: target action missing, fallback_action_value used"
        return None, "Flow runtime: target action missing and no fallback"

    action_type = target_block.get("action_type")
    if action_type not in ("return_string", "question"):
        fallback = trigger.get("fallback_action_value")
        if dialog_state and waiting_trigger_id:
            dialog_state.waiting_trigger_block_id = None
            db.commit()
        if isinstance(fallback, str) and fallback.strip():
            return fallback.strip(), "Flow runtime: unsupported action_type, fallback_action_value used"
        return None, "Flow runtime: unsupported action_type and no fallback"
    action_value = target_block.get("action_value")
    if not isinstance(action_value, str) or not action_value.strip():
        fallback = trigger.get("fallback_action_value")
        if dialog_state and waiting_trigger_id:
            dialog_state.waiting_trigger_block_id = None
            db.commit()
        if isinstance(fallback, str) and fallback.strip():
            return fallback.strip(), "Flow runtime: empty action_value, fallback_action_value used"
        return None, "Flow runtime: empty action_value and no fallback"

    if dialog_state and waiting_trigger_id:
        dialog_state.waiting_trigger_block_id = None
        db.commit()

    if action_type == "question" and isinstance(chat_id, str) and chat_id.strip():
        next_trigger_edge = next(
            (
                edge
                for edge in edges
                if isinstance(edge, dict)
                and edge.get("from_block_id") == target_block.get("id")
                and edge.get("when") == "always"
                and isinstance(blocks_by_id.get(edge.get("to_block_id")), dict)
                and blocks_by_id.get(edge.get("to_block_id"), {}).get("type") == "trigger"
            ),
            None,
        )
        if next_trigger_edge:
            next_trigger_id = next_trigger_edge.get("to_block_id")
            if dialog_state:
                dialog_state.waiting_trigger_block_id = str(next_trigger_id)
            else:
                db.add(
                    BotDialogState(
                        bot_id=bot.id,
                        telegram_chat_id=chat_id,
                        waiting_trigger_block_id=str(next_trigger_id),
                    )
                )
            db.commit()

    target_id = target_block.get("id")
    return action_value.strip(), f"Flow runtime: {debug_match}, action={target_id}, action_type={action_type}"
