import pytest

from aihub.errors import UnsafeSQLError
from aihub.tools.sql_tool import validate_select


def test_accepts_select_and_strips_fences():
    assert validate_select("```sql\nSELECT * FROM orders;\n```") == "SELECT * FROM orders"
    assert validate_select("WITH t AS (SELECT 1) SELECT * FROM t")


@pytest.mark.parametrize("bad", [
    "DROP TABLE orders", "SELECT 1; DROP TABLE orders", "DELETE FROM orders",
    "SELECT * FROM orders -- x", "PRAGMA table_info(orders)", "", "UPDATE orders SET quantity=0",
    "SELECT * FROM orders /* hi */",
])
def test_rejects_unsafe(bad):
    with pytest.raises(UnsafeSQLError):
        validate_select(bad)
