import pytest
from storage.extract import JDExtraction, QualMeta, extract_jd_fields, extract_qual_meta, is_internship_title


def test_extract_jd_fields_returns_result(mocker):
    expected = JDExtraction(qualifications=["Python"], responsibilities=["Build models"])
    mock_chain = mocker.MagicMock()
    mock_chain.invoke.return_value = expected
    mocker.patch("storage.extract._chain", mock_chain)

    result = extract_jd_fields("some job description")

    assert result == expected
    mock_chain.invoke.assert_called_once()


def test_extract_jd_fields_retries_on_empty_result(mocker):
    empty = JDExtraction(qualifications=[], responsibilities=[])
    valid = JDExtraction(qualifications=["Python"], responsibilities=["Build models"])
    mock_chain = mocker.MagicMock()
    mock_chain.invoke.side_effect = [empty, valid]
    mocker.patch("storage.extract._chain", mock_chain)

    result = extract_jd_fields("some job description")

    assert result == valid
    assert mock_chain.invoke.call_count == 2


def test_extract_jd_fields_returns_second_even_if_still_empty(mocker):
    empty = JDExtraction(qualifications=[], responsibilities=[])
    mock_chain = mocker.MagicMock()
    mock_chain.invoke.return_value = empty
    mocker.patch("storage.extract._chain", mock_chain)

    result = extract_jd_fields("some job description")

    assert result.qualifications == []
    assert result.responsibilities == []
    assert mock_chain.invoke.call_count == 2


def test_extract_qual_meta_formats_bullet_list(mocker):
    mock_qual_chain = mocker.MagicMock()
    mock_qual_chain.invoke.return_value = QualMeta(max_yoe=5, min_education="BS")
    mocker.patch("storage.extract._qual_meta_chain", mock_qual_chain)

    extract_qual_meta(["5+ years Python", "BS in CS"])

    call_arg = mock_qual_chain.invoke.call_args[0][0]
    assert call_arg["qualifications"] == "- 5+ years Python\n- BS in CS"


def test_extract_qual_meta_returns_result(mocker):
    expected = QualMeta(max_yoe=3, min_education="MS")
    mock_qual_chain = mocker.MagicMock()
    mock_qual_chain.invoke.return_value = expected
    mocker.patch("storage.extract._qual_meta_chain", mock_qual_chain)

    result = extract_qual_meta(["3+ years experience"])

    assert result == expected


def test_extract_qual_meta_senior_title_sets_yoe_fallback(mocker):
    mock_qual_chain = mocker.MagicMock()
    mock_qual_chain.invoke.return_value = QualMeta(max_yoe=None, min_education="BS")
    mocker.patch("storage.extract._qual_meta_chain", mock_qual_chain)

    result = extract_qual_meta(["Strong Python skills"], title="Senior ML Engineer")

    assert result.max_yoe == 5
    assert result.min_education == "BS"


def test_extract_qual_meta_no_fallback_when_yoe_already_set(mocker):
    mock_qual_chain = mocker.MagicMock()
    mock_qual_chain.invoke.return_value = QualMeta(max_yoe=3, min_education=None)
    mocker.patch("storage.extract._qual_meta_chain", mock_qual_chain)

    result = extract_qual_meta(["3+ years experience"], title="Senior ML Engineer")

    assert result.max_yoe == 3


def test_extract_qual_meta_no_fallback_when_title_not_senior(mocker):
    mock_qual_chain = mocker.MagicMock()
    mock_qual_chain.invoke.return_value = QualMeta(max_yoe=None, min_education=None)
    mocker.patch("storage.extract._qual_meta_chain", mock_qual_chain)

    result = extract_qual_meta(["Strong Python skills"], title="ML Engineer")

    assert result.max_yoe is None


# Roman numeral / number → YOE fallback tests

@pytest.mark.parametrize("title,expected_yoe", [
    ("Software Engineer II", 3),   # roman numeral II maps to mid-level (3 yoe)
    ("Data Scientist IV", 8),      # roman numeral IV maps to staff-level (8 yoe)
    ("ML Engineer I", 0),          # roman numeral I maps to entry-level (0 yoe)
    ("Data Scientist 3", 5),       # arabic numeral 3 maps to senior-level (5 yoe)
    ("ML Engineer 1", 0),          # arabic numeral 1 maps to entry-level (0 yoe)
])
def test_extract_qual_meta_level_numeral_sets_yoe(title, expected_yoe, mocker):
    mock_qual_chain = mocker.MagicMock()
    mock_qual_chain.invoke.return_value = QualMeta(max_yoe=None, min_education=None)
    mocker.patch("storage.extract._qual_meta_chain", mock_qual_chain)

    result = extract_qual_meta([], title=title)

    assert result.max_yoe == expected_yoe


def test_extract_qual_meta_level_numeral_preserves_education(mocker):
    # level numeral fallback keeps the LLM-extracted education degree
    mock_qual_chain = mocker.MagicMock()
    mock_qual_chain.invoke.return_value = QualMeta(max_yoe=None, min_education="MS")
    mocker.patch("storage.extract._qual_meta_chain", mock_qual_chain)

    result = extract_qual_meta([], title="Software Engineer III")

    assert result.max_yoe == 5
    assert result.min_education == "MS"


def test_extract_qual_meta_level_numeral_skipped_when_yoe_already_set(mocker):
    # LLM result is not overridden when it already returned a yoe
    mock_qual_chain = mocker.MagicMock()
    mock_qual_chain.invoke.return_value = QualMeta(max_yoe=7, min_education=None)
    mocker.patch("storage.extract._qual_meta_chain", mock_qual_chain)

    result = extract_qual_meta([], title="Software Engineer II")

    assert result.max_yoe == 7


def test_extract_qual_meta_level_numeral_beats_senior_keyword(mocker):
    # when title has both a level numeral and a senior keyword, the numeral wins
    mock_qual_chain = mocker.MagicMock()
    mock_qual_chain.invoke.return_value = QualMeta(max_yoe=None, min_education=None)
    mocker.patch("storage.extract._qual_meta_chain", mock_qual_chain)

    result = extract_qual_meta([], title="Senior Software Engineer II")

    assert result.max_yoe == 3


@pytest.mark.parametrize("title,expected", [
    ("Software Intern", True),
    ("Software Engineering Internship", True),
    ("Data Science Co-op", True),
    ("Co Op Engineer", True),
    ("Coop Position", True),
    ("ML Intern 2025", True),
    ("Senior ML Engineer", False),
    ("Internal Tools Engineer", False),
    ("Program Coordinator", False),
])
def test_is_internship_title(title, expected):
    assert is_internship_title(title) == expected
