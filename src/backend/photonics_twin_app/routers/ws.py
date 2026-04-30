from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from photonics_twin_app.schemas import BraggParams, Sweep
from photonics_twin_app.sim import run_bragg_sweep

router = APIRouter(tags=["ws"])

@router.websocket("/ws/sim")
async def ws_sim(ws: WebSocket, component: str = "bragg_grating"):
    await ws.accept()
    if component != "bragg_grating":
        await ws.send_json({"type": "error", "code": "unknown_component",
                            "message": f"Unknown component: {component}"})
        await ws.close()
        return
    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("type") != "simulate":
                await ws.send_json({"type": "error", "code": "bad_message",
                                    "message": "expected type=simulate"})
                continue
            try:
                params = BraggParams(**msg["params"])
                sweep  = Sweep(**msg["sweep"])
            except ValidationError as e:
                await ws.send_json({"type": "error", "code": "validation_error",
                                    "message": str(e)})
                continue
            result = run_bragg_sweep(params, sweep)
            await ws.send_json({"type": "result", **result})
    except WebSocketDisconnect:
        return
