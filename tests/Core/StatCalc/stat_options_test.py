import pytest

from src.swgoh_comlink.StatCalc.stat_values import StatOptions


def test_stat_options_init_default():
    options = StatOptions()
    assert all(getattr(options, flag) is False for flag in options.__slots__ if flag != "LANGUAGE")
    assert getattr(options, "LANGUAGE") == 'eng_us'


def test_stat_options_init_from_list_correct():
    options = StatOptions(["without_mod_calc", "language=eng_us"])
    assert getattr(options, "WITHOUT_MOD_CALC") is True
    assert getattr(options, "LANGUAGE") == 'eng_us'


def test_stat_options_init_from_dict_correct():
    options_dict = {"without_mod_calc": True, "language": "eng_us"}
    options = StatOptions(options_dict)
    assert getattr(options, "WITHOUT_MOD_CALC") is True
    assert getattr(options, "LANGUAGE") == 'eng_us'


@pytest.mark.parametrize("wrong_type", [(True), 123, 456.78, ("tuple"), {"set"}, {1, 2, 3}, None])
def test_stat_options_init_wrong_object(wrong_type):
    with pytest.raises(ValueError):
        StatOptions(wrong_type)


def test_stat_options_init_kwargs():
    options = StatOptions(without_mod_calc=True, language="eng_us")
    assert getattr(options, "WITHOUT_MOD_CALC") is True
    assert getattr(options, "LANGUAGE") == 'eng_us'


def test_stat_options_init_language_error():
    with pytest.raises(ValueError):
        StatOptions(without_mod_calc=True, language="not_a_lang")


def test_stat_options_setters_lang():
    options = StatOptions()
    options.LANGUAGE = "ger_de"
    assert getattr(options, "LANGUAGE") == 'ger_de'


def test_stat_options_setters_non_bool():
    options = StatOptions()
    with pytest.raises(TypeError):
        options.WITHOUT_MOD_CALC = "not a bool"


def test_stat_options_delattr():
    options = StatOptions()
    del options.LANGUAGE
    assert getattr(options, "LANGUAGE") == 'eng_us'


@pytest.mark.parametrize("wrong_type", [(True), 123, 456.78, ("tuple"), {"set"}, {1, 2, 3}, None])
def test_stat_options_from_list(wrong_type):
    options = StatOptions()
    with pytest.raises(TypeError):
        options.from_list(wrong_type)


@pytest.mark.parametrize("wrong_type", [(True), 123, 456.78, ("tuple"), ["list"], {1, 2, 3}, None])
def test_stat_options_from_dict(wrong_type):
    options = StatOptions()
    with pytest.raises(TypeError):
        options.from_dict(wrong_type)


def test_to_list():
    options = StatOptions()
    options_list = options.to_list()
    assert "LANGUAGE=eng_us" in options_list
    assert len(options_list) == 1


def test_to_dict():
    options = StatOptions()
    options_dict = options.to_dict()
    assert options_dict["LANGUAGE"] == 'eng_us'
    assert sum(v is True for v in options_dict.values()) == 0
