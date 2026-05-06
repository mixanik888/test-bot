import json
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_org_member, require_manager_or_admin
from ..models import Bot, FlowDefinition, FlowVersion, OrganizationUser
from ..schemas import (
    FlowBlock,
    FlowEdge,
    FlowSchemaResponse,
    FlowSchemaSaveRequest,
    FlowTriggerPath,
    FlowVersionResponse,
)

router = APIRouter(prefix="/api/v1/bots", tags=["flows"])


def _normalize_trigger_paths(blocks: list[FlowBlock], edges: list[FlowEdge]) -> list[FlowBlock]:
    normalized_blocks: list[FlowBlock] = []
    for block in blocks:
        if block.type != "trigger":
            normalized_blocks.append(block)
            continue

        paths = list(block.trigger_paths or [])
        path_ids = {path.id for path in paths}
        candidate_edge_ids = {
            edge.when
            for edge in edges
            if edge.from_block_id == block.id and edge.when not in ("always", "true", "false", "fallback")
        }
        for edge_path_id in sorted(candidate_edge_ids):
            if edge_path_id in path_ids:
                continue
            paths.append(FlowTriggerPath(id=edge_path_id, name=edge_path_id, regex=".*"))
            path_ids.add(edge_path_id)

        normalized_blocks.append(
            FlowBlock(
                id=block.id,
                type=block.type,
                label=block.label,
                x=block.x,
                y=block.y,
                trigger_paths=paths if paths else None,
                condition_regex=block.condition_regex,
                fallback_action_value=block.fallback_action_value,
                action_type=block.action_type,
                action_value=block.action_value,
            )
        )
    return normalized_blocks


def _validate_schema(blocks: list[FlowBlock], edges: list[FlowEdge]) -> list[str]:
    errors: list[str] = []
    trigger_count = sum(1 for block in blocks if block.type == "trigger")
    action_count = sum(1 for block in blocks if block.type == "action")

    if trigger_count != 1:
        errors.append("Схема должна содержать ровно один блок типа trigger")
    if action_count < 1:
        errors.append("Схема должна содержать хотя бы один блок типа action")

    unsupported = [block.type for block in blocks if block.type not in ("trigger", "action")]
    if unsupported:
        errors.append("Поддерживаются только блоки trigger и action")

    block_ids = {block.id for block in blocks}
    if len(block_ids) != len(blocks):
        errors.append("ID блоков должны быть уникальными")

    if not edges:
        errors.append("Добавьте хотя бы одну связь между блоками")

    blocks_by_id = {block.id: block for block in blocks}

    for edge in edges:
        if edge.from_block_id not in block_ids or edge.to_block_id not in block_ids:
            errors.append("Связи должны указывать на существующие блоки")
            continue
        source_block = blocks_by_id.get(edge.from_block_id)
        if source_block and source_block.type == "trigger":
            path_ids = {path.id for path in (source_block.trigger_paths or [])}
            allowed_when = {"fallback"} | path_ids
            if source_block.condition_regex:
                allowed_when = allowed_when | {"true", "false"}
            if edge.when not in allowed_when:
                errors.append("Для связей trigger используйте when=fallback или when=<path_id>")
        elif edge.when != "always":
            errors.append("Для связей не из trigger используйте when=always")

    outgoing = {edge.from_block_id for edge in edges}
    trigger_ids = {block.id for block in blocks if block.type == "trigger"}
    if trigger_ids and not any(trigger_id in outgoing for trigger_id in trigger_ids):
        errors.append("У блока trigger должна быть исходящая связь")

    trigger_blocks = [block for block in blocks if block.type == "trigger"]
    for trigger_block in trigger_blocks:
        trigger_paths = trigger_block.trigger_paths or []
        if trigger_paths:
            path_ids: set[str] = set()
            for path in trigger_paths:
                if path.id in path_ids:
                    errors.append("ID путей trigger должны быть уникальными")
                path_ids.add(path.id)
                if path.match_type not in ("regex", "yes", "no", "any"):
                    errors.append(f"Тип пути trigger '{path.name}' должен быть regex/yes/no/any")
                    continue
                if path.match_type == "regex":
                    try:
                        re.compile(path.regex)
                    except re.error:
                        errors.append(f"Regex пути trigger '{path.name}' должен быть корректным")
            yes_count = sum(1 for path in trigger_paths if path.match_type == "yes")
            no_count = sum(1 for path in trigger_paths if path.match_type == "no")
            any_count = sum(1 for path in trigger_paths if path.match_type == "any")
            if yes_count > 1:
                errors.append("У trigger может быть только один путь типа yes")
            if no_count > 1:
                errors.append("У trigger может быть только один путь типа no")
            if any_count > 1:
                errors.append("У trigger может быть только один путь типа any")
        elif trigger_block.condition_regex:
            try:
                re.compile(trigger_block.condition_regex)
            except re.error:
                errors.append("condition_regex у trigger должен быть корректным regex")
        else:
            errors.append("Для trigger добавьте хотя бы один путь с regex")

        trigger_edges = [edge for edge in edges if edge.from_block_id == trigger_block.id]
        path_ids = {path.id for path in trigger_paths}
        has_path_target = any(edge.when in path_ids for edge in trigger_edges) if path_ids else False
        has_fallback = bool(trigger_block.fallback_action_value and trigger_block.fallback_action_value.strip())
        has_fallback_edge = any(edge.when == "fallback" for edge in trigger_edges)
        if trigger_paths and not has_path_target and not has_fallback and not has_fallback_edge:
            errors.append("Для trigger свяжите хотя бы один путь с action или заполните fallback")
        if not trigger_paths:
            has_true = any(edge.when == "true" for edge in trigger_edges)
            has_false = any(edge.when == "false" for edge in trigger_edges)
            if not has_true and not has_fallback:
                errors.append("Для trigger нужна ветка when=true или fallback_action_value")
            if not has_false and not has_fallback:
                errors.append("Для trigger нужна ветка when=false или fallback_action_value")

    action_blocks = [block for block in blocks if block.type == "action"]
    for action_block in action_blocks:
        if action_block.action_type not in ("return_string", "question"):
            errors.append("Для action поддерживаются только action_type=return_string или action_type=question")
            continue
        if not action_block.action_value or not action_block.action_value.strip():
            errors.append(f"Для action типа {action_block.action_type} нужно заполнить action_value")
        if action_block.action_type == "question":
            question_edges = [
                edge for edge in edges if edge.from_block_id == action_block.id and edge.when == "always"
            ]
            has_trigger_target = any(
                (blocks_by_id.get(edge.to_block_id) and blocks_by_id[edge.to_block_id].type == "trigger")
                for edge in question_edges
            )
            if not has_trigger_target:
                errors.append("Для action типа question добавьте связь when=always на блок trigger")

    return errors


def _get_bot_in_org(db: Session, bot_id: int, organization_id: int) -> Bot:
    bot = db.query(Bot).filter(Bot.id == bot_id, Bot.organization_id == organization_id).first()
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
    return bot


def _ensure_flow_definition(db: Session, bot_id: int) -> FlowDefinition:
    flow = db.query(FlowDefinition).filter(FlowDefinition.bot_id == bot_id).first()
    if flow:
        return flow
    flow = FlowDefinition(bot_id=bot_id, draft_schema="[]")
    db.add(flow)
    db.commit()
    db.refresh(flow)
    return flow


@router.get("/{bot_id}/flow", response_model=FlowSchemaResponse)
def get_flow(
    bot_id: int,
    member: OrganizationUser = Depends(get_current_org_member),
    db: Session = Depends(get_db),
):
    _get_bot_in_org(db, bot_id, member.organization_id)
    flow = _ensure_flow_definition(db, bot_id)
    data = json.loads(flow.draft_schema or '{"blocks":[],"edges":[]}')
    if isinstance(data, list):
        data = {"blocks": data, "edges": []}
    blocks = [FlowBlock(**item) for item in data.get("blocks", [])]
    edges = [FlowEdge(**item) for item in data.get("edges", [])]
    blocks = _normalize_trigger_paths(blocks, edges)
    errors = _validate_schema(blocks, edges)
    return FlowSchemaResponse(bot_id=bot_id, blocks=blocks, edges=edges, is_valid=not errors, errors=errors)


@router.put("/{bot_id}/flow", response_model=FlowSchemaResponse)
def save_flow(
    bot_id: int,
    payload: FlowSchemaSaveRequest,
    member: OrganizationUser = Depends(require_manager_or_admin),
    db: Session = Depends(get_db),
):
    _get_bot_in_org(db, bot_id, member.organization_id)
    flow = _ensure_flow_definition(db, bot_id)
    normalized_blocks = _normalize_trigger_paths(payload.blocks, payload.edges)
    errors = _validate_schema(normalized_blocks, payload.edges)
    flow.draft_schema = json.dumps(
        {
            "blocks": [block.model_dump() for block in normalized_blocks],
            "edges": [edge.model_dump() for edge in payload.edges],
        },
        ensure_ascii=False,
    )
    db.commit()
    return FlowSchemaResponse(
        bot_id=bot_id,
        blocks=normalized_blocks,
        edges=payload.edges,
        is_valid=not errors,
        errors=errors,
    )


@router.post("/{bot_id}/flow/publish", response_model=FlowVersionResponse)
def publish_flow(
    bot_id: int,
    member: OrganizationUser = Depends(require_manager_or_admin),
    db: Session = Depends(get_db),
):
    _get_bot_in_org(db, bot_id, member.organization_id)
    flow = _ensure_flow_definition(db, bot_id)
    data = json.loads(flow.draft_schema or '{"blocks":[],"edges":[]}')
    if isinstance(data, list):
        data = {"blocks": data, "edges": []}
    blocks = [FlowBlock(**item) for item in data.get("blocks", [])]
    edges = [FlowEdge(**item) for item in data.get("edges", [])]
    blocks = _normalize_trigger_paths(blocks, edges)
    errors = _validate_schema(blocks, edges)
    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=errors)

    latest = (
        db.query(FlowVersion)
        .filter(FlowVersion.flow_definition_id == flow.id)
        .order_by(FlowVersion.version.desc())
        .first()
    )
    next_version = (latest.version + 1) if latest else 1
    version = FlowVersion(
        flow_definition_id=flow.id,
        version=next_version,
        schema=flow.draft_schema,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return FlowVersionResponse(
        id=version.id,
        version=version.version,
        blocks=blocks,
        edges=edges,
        created_at=version.created_at.isoformat() if version.created_at else None,
    )


@router.get("/{bot_id}/flow/versions", response_model=list[FlowVersionResponse])
def list_flow_versions(
    bot_id: int,
    member: OrganizationUser = Depends(get_current_org_member),
    db: Session = Depends(get_db),
):
    _get_bot_in_org(db, bot_id, member.organization_id)
    flow = db.query(FlowDefinition).filter(FlowDefinition.bot_id == bot_id).first()
    if not flow:
        return []
    rows = (
        db.query(FlowVersion)
        .filter(FlowVersion.flow_definition_id == flow.id)
        .order_by(FlowVersion.version.desc())
        .all()
    )
    result: list[FlowVersionResponse] = []
    for row in rows:
        data = json.loads(row.schema or '{"blocks":[],"edges":[]}')
        if isinstance(data, list):
            data = {"blocks": data, "edges": []}
        blocks = [FlowBlock(**item) for item in data.get("blocks", [])]
        edges = [FlowEdge(**item) for item in data.get("edges", [])]
        blocks = _normalize_trigger_paths(blocks, edges)
        result.append(
            FlowVersionResponse(
                id=row.id,
                version=row.version,
                blocks=blocks,
                edges=edges,
                created_at=row.created_at.isoformat() if row.created_at else None,
            )
        )
    return result
