"""Isolated Claude CLI call used by the LLM experiment.

Isolation: an empty sandbox working directory, the given file as the *replacement* system prompt, no tools,
no user/project settings, no MCP servers, no session persistence, JSON envelope output.
"""
import hashlib, json, os, subprocess, tempfile, time

SANDBOX = os.path.join(tempfile.gettempdir(), "t2a-ess-sandbox")


def sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha_file(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def run_claude(model, system_prompt_path, user_text, timeout=2400):
    """Returns (envelope, elapsed_s, returncode). The envelope is the CLI's JSON output."""
    os.makedirs(SANDBOX, exist_ok=True)
    cmd = ["claude", "-p", "--model", model, "--system-prompt-file", system_prompt_path, "--tools", "",
           "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence", "--output-format", "json"]
    env = dict(os.environ, CLAUDE_CODE_MAX_OUTPUT_TOKENS="128000")
    t0 = time.time()
    proc = subprocess.run(cmd, input=user_text, capture_output=True, text=True, encoding="utf-8",
                          cwd=SANDBOX, env=env, timeout=timeout, shell=(os.name == "nt"))
    elapsed = time.time() - t0
    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError:
        envelope = {"is_error": True, "result": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}
    return envelope, elapsed, proc.returncode


def parse_json(text):
    """The first JSON object in a model answer (tolerates a ```json fence)."""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(s[s.find("{"):s.rfind("}") + 1])
