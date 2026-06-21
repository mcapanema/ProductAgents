"""Guard that .env.example documents every supported variable."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_EXAMPLE = REPO_ROOT / ".env.example"

EXPECTED_KEYS = (
    "PRODUCTAGENTS_MODEL",
    "PRODUCTAGENTS_MODEL_PROVIDER",
    "PRODUCTAGENTS_DEBATE_ROUNDS",
    "ANTHROPIC_API_KEY",
)


def test_env_example_exists():
    assert ENV_EXAMPLE.is_file()


def test_env_example_documents_all_keys():
    text = ENV_EXAMPLE.read_text()
    for key in EXPECTED_KEYS:
        assert key in text, f"{key} missing from .env.example"


def test_env_example_has_no_real_anthropic_key():
    text = ENV_EXAMPLE.read_text()
    # A real Anthropic key starts with "sk-ant-"; the template must not embed one.
    assert "sk-ant-" not in text
