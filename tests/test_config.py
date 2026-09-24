import pytest

from rb_errata import config


def test_defaults_match_the_brief() -> None:
    s = config.load({})
    assert s.database_url.endswith(":5433/rb_errata")
    assert (s.embed_model, s.embed_dims, s.gen_model) == ("nomic-embed-text", 768, "qwen3:4b")
    assert s.gen_think is False


def test_env_overrides_are_typed() -> None:
    s = config.load({"RB_EMBED_DIMS": "1024", "RB_GEN_THINK": "true", "RB_GEN_TEMPERATURE": "0.5"})
    assert (s.embed_dims, s.gen_think, s.gen_temperature) == (1024, True, 0.5)


def test_bad_boolean_is_refused_not_guessed() -> None:
    with pytest.raises(ValueError):
        config.load({"RB_GEN_THINK": "ture"})


def test_run_record_omits_credentials() -> None:
    record = config.load({}).as_record()
    assert "database_url" not in record
    assert record["gen_model"] == "qwen3:4b"
