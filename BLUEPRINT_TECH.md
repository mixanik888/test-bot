# Технический blueprint (Этап 1)

## Стек

- Frontend: React + TypeScript (план)
- Backend: FastAPI + SQLAlchemy
- DB: SQLite (локально для MVP)
- Queue: отложено до Этапа 2 (планируется Redis + worker)

## API-контракт (минимум)

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/oauth/google`
- `POST /api/v1/auth/oauth/telegram`
- `GET /api/v1/me`
- `GET /api/v1/org`
- `POST /api/v1/org/users/invite`
- `PATCH /api/v1/org/users/{user_id}/role`
- `GET /api/v1/billing/plan`
- `GET /api/v1/billing/limits`

## BPMN JSON (черновая модель для следующих этапов)

```json
{
  "processId": "flow_001",
  "name": "Welcome flow",
  "version": 1,
  "nodes": [
    { "id": "start_1", "type": "start", "position": { "x": 80, "y": 120 } },
    { "id": "msg_1", "type": "message", "text": "Привет!", "position": { "x": 240, "y": 120 } },
    { "id": "end_1", "type": "end", "position": { "x": 400, "y": 120 } }
  ],
  "edges": [
    { "id": "e1", "from": "start_1", "to": "msg_1" },
    { "id": "e2", "from": "msg_1", "to": "end_1" }
  ]
}
```
