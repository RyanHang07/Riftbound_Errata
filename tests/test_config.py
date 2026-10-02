import pytest

from rb_errata import config


def test_defaults_match_the_brief() -> None:
    s = config.load({})
    assert s.database_url.endswith(":5433/rb_errata")
    assert (s.embed_model, s.embed_dims, s.gen_model) == (
        "nomic-embed-text",
        768,
        "qwen3:4b-instruct-2507-q4_K_M",
    )
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
    assert record["gen_model"] == "qwen3:4b-instruct-2507-q4_K_M"


def test_default_settings_are_the_nomic_profile() -> None:
    # Two sources of truth for the default embedder would drift apart.
    s = config.Settings()
    for field, value in config.EMBED_PROFILES["nomic"].items():
        assert getattr(s, field) == value, field
    assert s.db_schema == "public"  # the corpus ingested before profiles existed


def test_profile_ignores_env_written_for_another_embedder() -> None:
    # A .env pinning nomic's digest must not leak into the qwen3 profile.
    s = config.load({"RB_EMBED_PROFILE": "qwen3", "RB_EMBED_DIGEST": "nomic-digest",
                     "RB_EMBED_DIMS": "768", "RB_CPU_ONLY": "true"})  # fmt: skip
    assert s.embed_model == "qwen3-embedding:0.6b"
    assert (s.embed_dims, s.embed_digest) == (1024, config.EMBED_PROFILES["qwen3"]["embed_digest"])
    assert s.cpu_only is True  # non-embedding settings still apply
    assert s.db_schema == "emb_qwen3"


def test_unknown_profile_is_refused() -> None:
    import pytest

    with pytest.raises(ValueError):
        config.load({"RB_EMBED_PROFILE": "nomic2"})
