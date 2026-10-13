from __future__ import annotations

import argparse
import json
import math
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests
import tiktoken

from aulatex.config import load_aulatex_env


@dataclass(frozen=True)
class DeploymentSpec:
    model_id: str
    url: str
    max_input_tokens: int
    max_output_tokens: int
    api_key_env: str
    deployment_env: str
    api_version_env: str = ""
    tokenizer_name: str = "o200k_base"
    tokenizer_approximate: bool = False


SPECS: dict[str, DeploymentSpec] = {
    "gpt-5.4-pro": DeploymentSpec(
        model_id="gpt-5.4-pro",
        url="https://carlosmauriciocarvajalcoronado-4.services.ai.azure.com/openai/v1/responses",
        max_input_tokens=922000,
        max_output_tokens=128000,
        api_key_env="GPT_PRO_API_KEY",
        deployment_env="GPT_PRO_CHAT_DEPLOYMENT",
        api_version_env="GPT_PRO_API_VERSION",
    ),
    "model-router": DeploymentSpec(
        model_id="model-router",
        url="https://carlosmauriciocarvajalcoronado-4.services.ai.azure.com/openai/v1/chat/completions",
        max_input_tokens=1015808,
        max_output_tokens=32768,
        api_key_env="MODEL_ROUTER_API_KEY",
        deployment_env="MODEL_ROUTER_CHAT_DEPLOYMENT",
        api_version_env="MODEL_ROUTER_API_VERSION",
        tokenizer_approximate=True,
    ),
    "Mistral-Large-3": DeploymentSpec(
        model_id="Mistral-Large-3",
        url="https://carlosmauriciocarvajalcoronado-4.services.ai.azure.com/openai/v1/chat/completions",
        max_input_tokens=126976,
        max_output_tokens=4096,
        api_key_env="MISTRAL_LARGE_3_API_KEY",
        deployment_env="MISTRAL_LARGE_3_CHAT_DEPLOYMENT",
        tokenizer_approximate=True,
    ),
    "gpt-chat-latest": DeploymentSpec(
        model_id="gpt-chat-latest",
        url="https://carlosmauriciocarvajalcoronado-4.services.ai.azure.com/openai/v1/responses",
        max_input_tokens=72000,
        max_output_tokens=128000,
        api_key_env="GPT_CHAT_LATEST_API_KEY",
        deployment_env="GPT_CHAT_LATEST_CHAT_DEPLOYMENT",
        api_version_env="GPT_CHAT_LATEST_API_VERSION",
    ),
    "DeepSeek-V4-Pro": DeploymentSpec(
        model_id="DeepSeek-V4-Pro",
        url="https://carlosmauriciocarvajalcoronado-4.services.ai.azure.com/openai/v1/chat/completions",
        max_input_tokens=872000,
        max_output_tokens=128000,
        api_key_env="DEEPSEEK_V4_PRO_API_KEY",
        deployment_env="DEEPSEEK_V4_PRO_CHAT_DEPLOYMENT",
        tokenizer_approximate=True,
    ),
    "gpt-5.3-codex": DeploymentSpec(
        model_id="gpt-5.3-codex",
        url="https://carlosmauriciocarvajalcoronado-4.services.ai.azure.com/openai/v1/responses",
        max_input_tokens=272000,
        max_output_tokens=128000,
        api_key_env="CODEX_API_KEY",
        deployment_env="CODEX_CHAT_DEPLOYMENT",
        api_version_env="CODEX_API_VERSION",
    ),
}


@dataclass(frozen=True)
class ProbeAttempt:
    phase: str
    requested_input_tokens: int
    actual_input_tokens: int
    requested_output_tokens: int
    ok: bool
    status_code: int
    latency_ms: int
    finish_reason: str
    response_output_tokens: int
    response_input_tokens: int
    response_total_tokens: int
    response_chars: int
    error: str
    raw_path: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe Azure/OpenAI deployments near declared token limits.")
    parser.add_argument("--model", action="append", dest="models")
    parser.add_argument("--input-timeout-seconds", type=int, default=120)
    parser.add_argument("--output-timeout-seconds", type=int, default=120)
    parser.add_argument("--max-reductions", type=int, default=8)
    parser.add_argument("--refine-steps", type=int, default=4)
    parser.add_argument("--output-root", default=".aulatex-temp/deployment-limit-probe")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_aulatex_env()
    repo_root = Path(__file__).resolve().parents[1]
    run_dir = repo_root / args.output_root / "runs" / time.strftime("%Y%m%d-%H%M%S")
    prompts_dir = run_dir / "prompts"
    raw_dir = run_dir / "raw"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    model_ids = args.models or list(SPECS.keys())
    payload: dict[str, Any] = {
        "kind": "deployment-limit-probe",
        "version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "run_dir": str(run_dir),
        "models": [],
    }

    for model_id in model_ids:
        spec = SPECS[model_id]
        result = probe_deployment(
            spec,
            prompts_dir=prompts_dir,
            raw_dir=raw_dir,
            input_timeout_seconds=args.input_timeout_seconds,
            output_timeout_seconds=args.output_timeout_seconds,
            max_reductions=args.max_reductions,
            refine_steps=args.refine_steps,
        )
        payload["models"].append(result)

    summary_md = build_summary_markdown(payload)
    (run_dir / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "summary.md").write_text(summary_md, encoding="utf-8")

    print(f"Run dir: {run_dir}")
    print(f"JSON:    {run_dir / 'results.json'}")
    print(f"Summary: {run_dir / 'summary.md'}")
    for model in payload["models"]:
        print(
            json.dumps(
                {
                    "model": model["model_id"],
                    "accepted_input_tokens": model["input_probe"]["best_success"]["actual_input_tokens"] if model["input_probe"]["best_success"] else 0,
                    "accepted_output_request": model["output_probe"]["best_success"]["requested_output_tokens"] if model["output_probe"]["best_success"] else 0,
                    "input_latency_ms": model["input_probe"]["best_success"]["latency_ms"] if model["input_probe"]["best_success"] else 0,
                    "output_latency_ms": model["output_probe"]["best_success"]["latency_ms"] if model["output_probe"]["best_success"] else 0,
                },
                ensure_ascii=False,
            )
        )


def probe_deployment(
    spec: DeploymentSpec,
    *,
    prompts_dir: Path,
    raw_dir: Path,
    input_timeout_seconds: int,
    output_timeout_seconds: int,
    max_reductions: int,
    refine_steps: int,
) -> dict[str, Any]:
    encoding = tiktoken.get_encoding(spec.tokenizer_name)
    deployment = os.getenv(spec.deployment_env, spec.model_id).strip().strip('"')
    api_key = os.getenv(spec.api_key_env, "").strip().strip('"')
    if not api_key:
        raise RuntimeError(f"Falta {spec.api_key_env} para {spec.model_id}")

    input_probe = find_operational_limit(
        spec,
        phase="input",
        claimed_value=spec.max_input_tokens,
        timeout_seconds=input_timeout_seconds,
        max_reductions=max_reductions,
        refine_steps=refine_steps,
        prompts_dir=prompts_dir,
        raw_dir=raw_dir,
        encoding=encoding,
        api_key=api_key,
        deployment=deployment,
    )
    output_probe = find_operational_limit(
        spec,
        phase="output",
        claimed_value=spec.max_output_tokens,
        timeout_seconds=output_timeout_seconds,
        max_reductions=max_reductions,
        refine_steps=refine_steps,
        prompts_dir=prompts_dir,
        raw_dir=raw_dir,
        encoding=encoding,
        api_key=api_key,
        deployment=deployment,
    )

    return {
        "model_id": spec.model_id,
        "url": spec.url,
        "deployment": deployment,
        "claimed_max_input_tokens": spec.max_input_tokens,
        "claimed_max_output_tokens": spec.max_output_tokens,
        "tokenizer": {
            "name": spec.tokenizer_name,
            "approximate": spec.tokenizer_approximate,
        },
        "input_probe": input_probe,
        "output_probe": output_probe,
    }


def descending_targets(claimed_value: int, max_reductions: int) -> list[int]:
    scales = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.15, 0.1, 0.05]
    values: list[int] = []
    for scale in scales[: max_reductions + 1]:
        candidate = max(16, int(math.floor(claimed_value * scale)))
        if candidate not in values:
            values.append(candidate)
    return values


def find_operational_limit(
    spec: DeploymentSpec,
    *,
    phase: str,
    claimed_value: int,
    timeout_seconds: int,
    max_reductions: int,
    refine_steps: int,
    prompts_dir: Path,
    raw_dir: Path,
    encoding: tiktoken.Encoding,
    api_key: str,
    deployment: str,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    first_success: ProbeAttempt | None = None
    last_failure: ProbeAttempt | None = None
    for candidate in descending_targets(claimed_value, max_reductions):
        attempt = run_attempt(
            spec,
            phase=phase,
            input_target_tokens=(candidate if phase == "input" else min(256, max(32, spec.max_input_tokens // 1024))),
            output_target_tokens=(candidate if phase == "output" else 16),
            timeout_seconds=timeout_seconds,
            prompts_dir=prompts_dir,
            raw_dir=raw_dir,
            encoding=encoding,
            api_key=api_key,
            deployment=deployment,
        )
        attempts.append(asdict(attempt))
        if attempt.ok:
            first_success = attempt
            break
        last_failure = attempt

    best_success = first_success
    if first_success and last_failure:
        low = first_success.requested_input_tokens if phase == "input" else first_success.requested_output_tokens
        high = (last_failure.requested_input_tokens if phase == "input" else last_failure.requested_output_tokens) - 1
        for _ in range(refine_steps):
            if low >= high:
                break
            mid = (low + high + 1) // 2
            attempt = run_attempt(
                spec,
                phase=phase,
                input_target_tokens=(mid if phase == "input" else min(256, max(32, spec.max_input_tokens // 1024))),
                output_target_tokens=(mid if phase == "output" else 16),
                timeout_seconds=timeout_seconds,
                prompts_dir=prompts_dir,
                raw_dir=raw_dir,
                encoding=encoding,
                api_key=api_key,
                deployment=deployment,
            )
            attempts.append(asdict(attempt))
            if attempt.ok:
                best_success = attempt
                low = mid
            else:
                high = mid - 1

    return {
        "claimed_value": claimed_value,
        "best_success": asdict(best_success) if best_success else None,
        "attempts": attempts,
    }


def run_attempt(
    spec: DeploymentSpec,
    *,
    phase: str,
    input_target_tokens: int,
    output_target_tokens: int,
    timeout_seconds: int,
    prompts_dir: Path,
    raw_dir: Path,
    encoding: tiktoken.Encoding,
    api_key: str,
    deployment: str,
) -> ProbeAttempt:
    slug = spec.model_id.replace("/", "-")
    prompt = (
        build_input_prompt(encoding, input_target_tokens)
        if phase == "input"
        else build_output_prompt()
    )
    actual_input_tokens = len(encoding.encode(prompt, disallowed_special=()))
    prompt_path = prompts_dir / f"{slug}-{phase}-{output_target_tokens if phase == 'output' else input_target_tokens}.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    raw_path = raw_dir / f"{slug}-{phase}-{output_target_tokens if phase == 'output' else input_target_tokens}.json"

    started = time.perf_counter()
    try:
        response = requests.post(
            spec.url,
            headers=build_headers(spec.url, api_key),
            json=build_payload(spec, deployment, prompt, output_target_tokens),
            timeout=timeout_seconds,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        payload = response.json() if response.content else {}
        raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if response.status_code >= 400:
            return ProbeAttempt(
                phase=phase,
                requested_input_tokens=input_target_tokens,
                actual_input_tokens=actual_input_tokens,
                requested_output_tokens=output_target_tokens,
                ok=False,
                status_code=response.status_code,
                latency_ms=latency_ms,
                finish_reason="",
                response_output_tokens=0,
                response_input_tokens=0,
                response_total_tokens=0,
                response_chars=0,
                error=extract_error(payload) or f"HTTP {response.status_code}",
                raw_path=str(raw_path),
            )
        usage = extract_usage(payload)
        text = extract_text(payload)
        finish_reason = extract_finish_reason(payload)
        ok = True if phase == "input" else (usage["output_tokens"] > 0 or len(text) > 0)
        return ProbeAttempt(
            phase=phase,
            requested_input_tokens=input_target_tokens,
            actual_input_tokens=actual_input_tokens,
            requested_output_tokens=output_target_tokens,
            ok=ok,
            status_code=response.status_code,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            response_output_tokens=usage["output_tokens"],
            response_input_tokens=usage["input_tokens"],
            response_total_tokens=usage["total_tokens"],
            response_chars=len(text),
            error="" if ok else "Respuesta vacia o sin uso reportado.",
            raw_path=str(raw_path),
        )
    except requests.Timeout:
        latency_ms = int((time.perf_counter() - started) * 1000)
        raw_path.write_text(json.dumps({"error": "timeout"}, ensure_ascii=False, indent=2), encoding="utf-8")
        return ProbeAttempt(
            phase=phase,
            requested_input_tokens=input_target_tokens,
            actual_input_tokens=actual_input_tokens,
            requested_output_tokens=output_target_tokens,
            ok=False,
            status_code=0,
            latency_ms=latency_ms,
            finish_reason="timeout",
            response_output_tokens=0,
            response_input_tokens=0,
            response_total_tokens=0,
            response_chars=0,
            error="Tiempo de espera agotado.",
            raw_path=str(raw_path),
        )
    except requests.RequestException as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        raw_path.write_text(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2), encoding="utf-8")
        return ProbeAttempt(
            phase=phase,
            requested_input_tokens=input_target_tokens,
            actual_input_tokens=actual_input_tokens,
            requested_output_tokens=output_target_tokens,
            ok=False,
            status_code=0,
            latency_ms=latency_ms,
            finish_reason="network-error",
            response_output_tokens=0,
            response_input_tokens=0,
            response_total_tokens=0,
            response_chars=0,
            error=str(exc),
            raw_path=str(raw_path),
        )


def build_headers(url: str, api_key: str) -> dict[str, str]:
    netloc = urlsplit(url).netloc.lower()
    headers = {"Content-Type": "application/json"}
    if "azure.com" in netloc:
        headers["api-key"] = api_key
    else:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def build_payload(spec: DeploymentSpec, deployment: str, prompt: str, output_tokens: int) -> dict[str, Any]:
    if "/responses" in urlsplit(spec.url).path:
        return {
            "model": deployment,
            "input": prompt,
            "max_output_tokens": max(16, int(output_tokens)),
        }
    return {
        "model": deployment,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max(16, int(output_tokens)),
        "temperature": 0,
    }


def build_input_prompt(encoding: tiktoken.Encoding, target_tokens: int) -> str:
    prefix = "Prueba directa de limite de contexto. Responde solo con OK.\n\n"
    prefix_tokens = len(encoding.encode(prefix, disallowed_special=()))
    filler_needed = max(0, target_tokens - prefix_tokens)
    filler_token = choose_single_token_id(encoding)
    filler = encoding.decode([filler_token] * filler_needed)
    prompt = prefix + filler
    current = len(encoding.encode(prompt, disallowed_special=()))
    if current > target_tokens:
        delta = current - target_tokens
        filler = encoding.decode([filler_token] * max(0, filler_needed - delta))
        prompt = prefix + filler
    return prompt


def build_output_prompt() -> str:
    return (
        "Prueba directa de limite de salida. "
        "Produce lineas numeradas consecutivas con texto muy corto y sigue hasta que el sistema te corte por longitud."
    )


def choose_single_token_id(encoding: tiktoken.Encoding) -> int:
    for candidate in (" a", " hola", " dato", " texto"):
        token_ids = encoding.encode(candidate, disallowed_special=())
        if len(token_ids) == 1:
            return token_ids[0]
    return encoding.encode(" a", disallowed_special=())[0]


def extract_error(payload: dict[str, Any]) -> str:
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str):
            return message
    if isinstance(error, str):
        return error
    return ""


def extract_usage(payload: dict[str, Any]) -> dict[str, int]:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))
    total_tokens = usage.get("total_tokens", 0)
    return {
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "total_tokens": int(total_tokens or 0),
    }


def extract_finish_reason(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0]
        if isinstance(choice, dict):
            value = choice.get("finish_reason")
            if isinstance(value, str):
                return value
    incomplete = payload.get("incomplete_details")
    if isinstance(incomplete, dict):
        reason = incomplete.get("reason")
        if isinstance(reason, str):
            return reason
    status = payload.get("status")
    return status if isinstance(status, str) else ""


def extract_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        return output_text
    choices = payload.get("choices")
    if isinstance(choices, list):
        parts: list[str] = []
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    parts.append(content)
        if parts:
            return "".join(parts)
    output = payload.get("output")
    if isinstance(output, list):
        parts = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, list):
                for content_item in content:
                    if isinstance(content_item, dict) and isinstance(content_item.get("text"), str):
                        parts.append(content_item["text"])
        if parts:
            return "".join(parts)
    return ""


def build_summary_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Validacion Directa De Deployments",
        "",
        f"Run dir: {payload['run_dir']}",
        "",
        "## Resumen",
        "",
        "| Modelo | Entrada reclamada | Entrada operativa | Latencia entrada (ms) | Salida reclamada | Salida operativa | Latencia salida (ms) | Primer rechazo salida |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model in payload["models"]:
        input_success = model["input_probe"]["best_success"] or {}
        output_success = model["output_probe"]["best_success"] or {}
        rejected_output = 0
        for attempt in model["output_probe"]["attempts"]:
            if not attempt["ok"]:
                rejected_output = attempt["requested_output_tokens"]
                break
        lines.append(
            "| {0} | {1} | {2} | {3} | {4} | {5} | {6} | {7} |".format(
                model["model_id"],
                model["claimed_max_input_tokens"],
                input_success.get("actual_input_tokens", 0),
                input_success.get("latency_ms", 0),
                model["claimed_max_output_tokens"],
                output_success.get("requested_output_tokens", 0),
                output_success.get("latency_ms", 0),
                rejected_output,
            )
        )
    lines.extend(
        [
            "",
            "## Notas",
            "",
            "- La entrada se construye para acercarse al limite reclamado usando tokenizacion local con `o200k_base`.",
            "- Si la solicitud falla, el probador reduce gradualmente el valor y luego refina por busqueda binaria para encontrar un techo operativo.",
            "- La salida operativa se interpreta como el mayor `max_output_tokens` aceptado por la API dentro del timeout configurado.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()