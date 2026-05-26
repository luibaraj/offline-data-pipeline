import pytest
from storage.preprocess import clean_description


@pytest.mark.parametrize("inp, expected", [
    ("hello\xa0world", "hello world"),
    (r"React \- TypeScript", "React - TypeScript"),
    (r"Smith \& Jones", "Smith & Jones"),
    ("**Required:** Python", "Required: Python"),
    ("*preferred*", "preferred"),
    ("a\n\n\n\nb", "a\n\nb"),
    ("a\n\nb", "a\n\nb"),
    ("a   b", "a b"),
    ("a\t\tb", "a b"),
    ("", ""),
    (None, None),
    ("  leading and trailing  ", "leading and trailing"),
])
def test_clean_description(inp, expected):
    assert clean_description(inp) == expected
