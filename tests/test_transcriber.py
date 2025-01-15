import pytest
from youtube.transcriber import srt_to_continuous_text

def test_srt_to_continuous_text(tmp_path):
    # Create a temporary SRT file
    srt_content = """1
    00:00:00,000 --> 00:00:08,199
    我们不是没有需求,我们动过念头,我们在这需要一个什么东西。

    2
    00:00:08,199 --> 00:00:13,040
    就只能找别人去问问,也有一个沟通成本。

    3
    00:00:13,040 --> 00:00:18,440
    坦特最近大家聊得比较多的,有一个叫做AI福祝编程。
    """

    srt_path = tmp_path / "test.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    # Expected continuous text
    expected_text = (
        "我们不是没有需求,我们动过念头,我们在这需要一个什么东西。\n"
        "就只能找别人去问问,也有一个沟通成本。\n"
        "坦特最近大家聊得比较多的,有一个叫做AI福祝编程。"
    )

    # Call the function
    result = srt_to_continuous_text(srt_path)

    # Assert the result matches the expected text
    assert result == expected_text