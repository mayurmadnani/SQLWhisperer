from agentic_sql.questions import get_questions, QUESTIONS


def test_questions_non_empty():
    assert len(QUESTIONS) >= 5


def test_get_questions_limit():
    subset = get_questions(3)
    assert len(subset) == 3
    assert subset == QUESTIONS[:3]


def test_get_questions_full():
    assert get_questions() is QUESTIONS
