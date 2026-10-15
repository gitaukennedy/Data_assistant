from decimal import Decimal

from sqlalchemy.exc import OperationalError

from backend.agent.data_assistant import DataAssistant
from backend.database.db_manager import DatabaseManager
from backend.utils.sql_validator import SQLValidator


class FakeDatabase:
    def __init__(self):
        self.queries = []

    def execute_safe_select(self, query):
        self.queries.append(query)
        if "total_revenue" in query:
            return [{"total_revenue": Decimal("4200.50")}]
        return [{"product": "Pro Plan", "revenue": Decimal("1200.00")}]

    def get_table_schemas(self):
        return {
            "orders": {"columns": [{"order_id": "INTEGER"}, {"amount": "NUMERIC"}]},
        }


def test_common_question_uses_direct_database_path_without_model():
    database = FakeDatabase()
    assistant = DataAssistant(db_manager=database)

    result = assistant.answer_question("What is the total revenue?")

    assert result["fast_path"] is True
    assert result["answer"] == "Total revenue is $4,200.50."
    assert len(database.queries) == 1


def test_custom_question_executes_only_validated_generated_select(monkeypatch):
    database = FakeDatabase()
    assistant = DataAssistant(db_manager=database)
    monkeypatch.setattr(assistant, "_generate_sql", lambda _: "SELECT product, SUM(amount) AS revenue FROM orders GROUP BY product")

    result = assistant.answer_question("Which product earns the most?")

    assert result["fast_path"] is False
    assert "Pro Plan" in result["answer"]


def test_validator_rejects_multiple_or_modifying_statements():
    for query in (
        "DELETE FROM orders",
        "SELECT * FROM orders; DROP TABLE orders",
        "SELECT * FROM orders -- comment",
        "SELECT * INTO archive FROM orders",
    ):
        assert SQLValidator.is_safe_query(query)[0] is False


def test_database_manager_caps_unbounded_select_results():
    database = DatabaseManager("sqlite://")
    with database.engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE products (name TEXT)")
        connection.exec_driver_sql("INSERT INTO products (name) VALUES ('A'), ('B')")

    rows = database.execute_safe_select("SELECT name FROM products ORDER BY name")

    assert rows == [{"name": "A"}, {"name": "B"}]


def test_database_connection_failure_has_a_clear_non_model_response():
    class OfflineDatabase:
        def execute_safe_select(self, query):
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    result = DataAssistant(db_manager=OfflineDatabase()).answer_question("total revenue")

    assert result["status"] == "success"
    assert result["database_unavailable"] is True
    assert "PostgreSQL connection settings" in result["answer"]


def test_general_question_does_not_require_the_database_or_sql_generation():
    class FakeResponse:
        text = "Yes. I can help explain the data and answer general questions."

    class FakeModels:
        def generate_content(self, **kwargs):
            assert kwargs["config"]["max_output_tokens"] == 160
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    assistant = DataAssistant(db_manager=object())
    assistant._client = FakeClient()

    result = assistant.answer_question("Is this a data assistant?")

    assert result["general_chat"] is True
    assert result["answer"] == FakeResponse.text


def test_local_nlp_handles_open_ended_data_wording_without_a_model_call():
    database = FakeDatabase()
    assistant = DataAssistant(db_manager=database)

    result = assistant.answer_question("Which product has the highest sales?")

    assert result["local_nlp"] is True
    assert "Pro Plan" in result["answer"]
    assert "LIMIT 1" in database.queries[0]


def test_local_nlp_replaces_general_model_failure_with_a_helpful_response(monkeypatch):
    assistant = DataAssistant(db_manager=object())
    monkeypatch.setattr(assistant, "_general_response", lambda _: (_ for _ in ()).throw(RuntimeError("offline")))

    result = assistant.answer_question("okay")

    assert result["local_nlp"] is True
    assert result["answer"].startswith("Great.")
