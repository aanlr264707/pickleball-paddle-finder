import math

import pandas as pd
import pytest

from paddle_finder.core.config import DEFAULT_DATA_FILE
from paddle_finder.data import etl


def test_every_row_becomes_one_paddle_with_a_stable_id(frame):
    assert len(frame) == 494
    assert list(frame["id"]) == list(range(1, 495))
    assert not frame.duplicated(["brand", "name"]).any()
    assert list(frame.columns) == etl.CLEAN_COLUMNS


def test_to_number_handles_dollars_commas_percents_and_junk():
    result = etl.to_number(pd.Series(["$1,169.99", " 59% ", "", "n/a", "7.96"]))
    assert result.iloc[0] == pytest.approx(1169.99)
    assert result.iloc[1] == 59
    assert math.isnan(result.iloc[2]) and math.isnan(result.iloc[3])
    assert result.iloc[4] == pytest.approx(7.96)


def test_brand_spellings_are_merged_most_common_wins():
    brands = pd.Series(["GRUVN", "Gruvn", "Gruvn", "Element 6", "Element6", "JOOLA"])
    assert list(etl.canonical_brands(brands)) == [
        "Gruvn", "Gruvn", "Gruvn", "Element 6", "Element 6", "JOOLA"]


def test_dataset_has_no_duplicate_brand_spellings(frame):
    keys = frame["brand"].str.casefold().str.replace(r"[^0-9a-z]", "", regex=True)
    assert keys.nunique() == frame["brand"].nunique()


def test_text_is_stripped(frame):
    for column in etl.TEXT_KEYS:
        assert (frame[column] == frame[column].str.strip()).all(), column


def test_impossible_grip_size_becomes_missing(frame):
    raw = etl.read_raw(DEFAULT_DATA_FILE)
    assert (etl.to_number(raw["Grip Size (in)"]) > 5).any()   # the bad row exists in the raw file
    assert frame["grip_size"].dropna().between(3.5, 5.0).all()


def test_rows_without_a_name_are_dropped(frame):
    raw = etl.read_raw(DEFAULT_DATA_FILE).head(3).copy()
    raw.loc[1, "Paddle Name"] = "   "
    assert len(etl.clean(raw)) == 2


def test_missing_column_is_a_clear_error():
    raw = etl.read_raw(DEFAULT_DATA_FILE).drop(columns=["Price"])
    with pytest.raises(ValueError, match="Price"):
        etl.clean(raw)


def test_paddles_use_plain_python_types(frame):
    paddles = etl.paddles_from_frame(frame)
    for paddle in paddles:
        assert paddle.year is None or type(paddle.year) is int
        for key in etl.NUMERIC_KEYS:
            value = paddle.value(key)
            assert value is None or (type(value) is float and not math.isnan(value))


def test_no_discount_codes_are_loaded(frame):
    assert not any("discount" in column for column in frame.columns)
    raw_with_codes = etl.read_raw(DEFAULT_DATA_FILE).head(2).copy()
    raw_with_codes["Discount Code"] = "SAVE10"            # an older export that still has the column
    assert "SAVE10" not in etl.clean(raw_with_codes).to_string()


def test_links_are_urls_or_blank(frame):
    assert frame["link"].eq("").any()                      # "Coming Soon" was blanked
    assert frame.loc[frame["link"] != "", "link"].str.match(r"https?://").all()
