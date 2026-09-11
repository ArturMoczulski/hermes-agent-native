"""Offline capability contract, not proof of a live model or desktop session.

Use real config, capture packaging, active-model filtering and Responses encoding.
Only the physical desktop is replaced with a generated screenshot.
"""

import base64
import io
import json
import os
from pathlib import Path

import pytest
from PIL import Image


@pytest.mark.parametrize("provider", ["openai", "openai-codex"])
@pytest.mark.parametrize("mode", ["som", "vision"])
def test_astra_receives_original_screenshot_and_matching_tool_call(provider, mode):
    from agent.auxiliary_client import clear_runtime_main
    from agent.codex_responses_adapter import _chat_messages_to_responses_input
    from agent.vision_message_prep import VisionMessagePrepMixin
    from tools.computer_use import tool
    from tools.computer_use.backend import CaptureResult, UIElement

    clear_runtime_main()
    tool._AUX_VISION_ROUTE_CACHE.clear()
    config = {"model": {"default": "gpt-6-astra", "provider": provider,
                        "supports_vision": True}}
    Path(os.environ["HERMES_HOME"], "config.yaml").write_text(json.dumps(config))
    buffer = io.BytesIO()
    Image.new("RGB", (128, 96), "blue").save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode()
    capture = CaptureResult(
        mode=mode, width=128, height=96, png_b64=encoded,
        png_bytes_len=len(buffer.getvalue()), app="Capability fixture",
        elements=[UIElement(index=1, role="AXButton", label="Save")]
        if mode == "som" else [],
    )
    try:
        result = tool._capture_response(capture)
        agent = VisionMessagePrepMixin()
        agent.model = "gpt-6-astra"
        agent.provider = provider
        content = agent._tool_result_content_for_active_model("computer_use", result)
        messages = [
            {"role": "assistant", "content": None, "tool_calls": [{
                "id": "call_capture", "type": "function", "function": {
                    "name": "computer_use", "arguments": json.dumps({"action": "capture", "mode": mode})}}]},
            {"role": "tool", "tool_call_id": "call_capture", "content": content},
        ]
        items = _chat_messages_to_responses_input(messages)
        call = next(item for item in items if item["type"] == "function_call")
        output = next(item for item in items if item["type"] == "function_call_output")
        assert output["call_id"] == call["call_id"] == "call_capture"
        assert call["name"] == "computer_use"
        image = next(part for part in output["output"] if part["type"] == "input_image")
        assert image["image_url"] == "data:image/png;base64," + encoded
        if mode == "som":
            assert any("Save" in part.get("text", "") for part in output["output"])
    finally:
        tool._AUX_VISION_ROUTE_CACHE.clear()
        clear_runtime_main()
