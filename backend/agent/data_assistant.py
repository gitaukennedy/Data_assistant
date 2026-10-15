"""Cost-conscious, safe Text-to-SQL assistant powered by Gemini."""
import json
import logging
import os
import re
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.exc import OperationalError

from backend.database.db_manager import DatabaseManager
from backend.utils.sql_validator import SQLValidator

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash-lite"
SQL_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {"sql": {"type": "string"}},
    "required": ["sql"],
    "additionalProperties": False,
}
DATA_QUERY_KEYWORDS = {
    "amount", "customer", "customers", "database", "order", "orders", "product",
    "products", "region", "regions", "revenue", "sale", "sales", "subscription",
}


class DataAssistant:
    """Uses direct SQL for common questions and one low-cost model call otherwise."""

    def __init__(self, db_manager=None):
        self.db_manager = db_manager or DatabaseManager()
        self.model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self._client = None
        logger.info("DataAssistant initialized; model=%s", self.model_name)

    def _get_client(self):
        """Initialize the SDK only when a custom question requires it."""
        if self._client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY is not configured")
            from google import genai
            self._client = genai.Client(api_key=api_key)
        return self._client

    def _schema_context(self):
        schemas = self.db_manager.get_table_schemas()
        return "\n".join(
            f"{table}: " + ", ".join(next(iter(column)) for column in details["columns"])
            for table, details in schemas.items()
        )

    def _generate_sql(self, question):
        """Generate structured SELECT SQL with a deliberately small output budget."""
        prompt = f"""Generate exactly one PostgreSQL SELECT query for this business question.

Allowed schema:
{self._schema_context()}

Rules:
- Query only the tables and columns listed above.
- Return the data needed to answer the question; use aggregation when appropriate.
- Never use comments, semicolons, CTEs, system tables, data-modification statements, or SELECT INTO.
- Prefer an explicit LIMIT for detail rows.

Question: {question}"""
        response = self._get_client().models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                "temperature": 0,
                "max_output_tokens": 250,
                "response_mime_type": "application/json",
                "response_json_schema": SQL_RESPONSE_SCHEMA,
            },
        )
        try:
            sql = json.loads(response.text)["sql"].strip()
        except (AttributeError, TypeError, ValueError, KeyError) as error:
            raise ValueError("The model did not return valid SQL") from error

        is_safe, reason = SQLValidator.is_safe_query(sql)
        if not is_safe:
            raise ValueError(reason)
        return sql

    def _general_response(self, question):
        """Answer ordinary conversation without requiring a database connection."""
        response = self._get_client().models.generate_content(
            model=self.model_name,
            contents=(
                "You are a concise, friendly data-assistant chat companion. "
                "Answer the user's general question directly. Do not claim to have "
                "looked up database records unless results were supplied to you.\n\n"
                f"User question: {question}"
            ),
            config={"temperature": 0.3, "max_output_tokens": 160},
        )
        answer = (getattr(response, "text", None) or "").strip()
        if not answer:
            raise ValueError("The model returned an empty response")
        return answer

    @staticmethod
    def _local_nlp_sql(question):
        """Interpret common business language locally when an LLM is unavailable.

        This deliberately covers the project's known customer-and-order schema,
        keeps all generated SQL read-only, and costs no model credits.
        """
        normalized = " ".join(re.findall(r"[a-z0-9]+", question.lower()))
        wants_count = any(term in normalized for term in ("how many", "count", "number of", "total customers", "total orders"))
        wants_average = any(term in normalized for term in ("average", "mean"))
        wants_top = any(term in normalized for term in ("highest", "top", "most", "best"))
        mentions_order = any(term in normalized for term in ("order", "sale", "revenue", "amount", "product"))
        mentions_customer = any(term in normalized for term in ("customer", "client", "buyer", "region"))

        if mentions_order:
            if wants_top:
                return "SELECT product, SUM(amount) AS revenue FROM orders GROUP BY product ORDER BY revenue DESC LIMIT 1"
            if wants_average:
                return "SELECT product, AVG(amount) AS average_amount FROM orders GROUP BY product ORDER BY average_amount DESC"
            if wants_count:
                return "SELECT COUNT(*) AS order_count FROM orders"
            if "customer" in normalized or "client" in normalized or "buyer" in normalized:
                return (
                    "SELECT customers.name, customers.region, orders.product, orders.amount, orders.order_date "
                    "FROM orders JOIN customers ON orders.customer_id = customers.customer_id "
                    "ORDER BY orders.order_date DESC"
                )
            if "product" in normalized or "sales" in normalized or "revenue" in normalized:
                return "SELECT product, SUM(amount) AS revenue FROM orders GROUP BY product ORDER BY revenue DESC"
            return "SELECT order_id, customer_id, product, amount, order_date FROM orders ORDER BY order_date DESC"

        if mentions_customer:
            if wants_count and "region" not in normalized:
                return "SELECT COUNT(*) AS customer_count FROM customers"
            if "region" in normalized:
                return "SELECT region, COUNT(*) AS customer_count FROM customers GROUP BY region ORDER BY customer_count DESC"
            if "name" in normalized or "email" in normalized or "list" in normalized or "show" in normalized:
                return "SELECT customer_id, name, email, region, signup_date FROM customers ORDER BY customer_id"
            return "SELECT customer_id, name, region, signup_date FROM customers ORDER BY customer_id"
        return None

    @staticmethod
    def _local_nlp_response(question):
        """Keep offline conversation useful rather than returning a generic error."""
        normalized = " ".join(re.findall(r"[a-z]+", question.lower()))
        if normalized in {"ok", "okay", "cool", "great", "good"}:
            return "Great. Ask naturally about customers, orders, sales, products, or regions."
        if "data assistant" in normalized or "what can you do" in normalized:
            return "Yes. I can understand natural-language questions about customers and orders, then return the matching data."
        return (
            "I understood your question. This installation is currently operating in local data mode, "
            "so I can directly analyze customers, orders, products, revenue, and regions."
        )

    @staticmethod
    def _is_data_question(question):
        words = set(re.findall(r"[a-z]+", question.lower()))
        return bool(words & DATA_QUERY_KEYWORDS)

    @staticmethod
    def _display_value(value):
        if isinstance(value, Decimal):
            return f"{value:.2f}"
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return str(value)

    @classmethod
    def _format_rows(cls, rows):
        """Create a Markdown table locally, avoiding a second paid model call."""
        if not rows:
            return "No matching records were found."
        headers = list(rows[0])
        output = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        for row in rows:
            values = [cls._display_value(row.get(column, "")).replace("|", "\\|") for column in headers]
            output.append("| " + " | ".join(values) + " |")
        return "\n".join(output)

    def answer_question(self, question):
        """Answer a user question, keeping common paths entirely free of LLM usage."""
        if not question or not question.strip():
            return {"status": "error", "question": question, "answer": "Please provide a valid question.", "context_used": False}
        try:
            fast_result = self._fast_path_answer(question)
            if fast_result is not None:
                return fast_result

            if not self._is_data_question(question):
                try:
                    answer = self._general_response(question)
                    return {
                        "status": "success", "question": question, "answer": answer,
                        "context_used": False, "general_chat": True,
                    }
                except Exception as error:
                    logger.info("Remote general chat unavailable; using local NLP: %s", error)
                    return {
                        "status": "success", "question": question,
                        "answer": self._local_nlp_response(question),
                        "context_used": False, "local_nlp": True,
                    }

            sql = self._local_nlp_sql(question)
            if sql is None:
                sql = self._generate_sql(question)
            rows = self.db_manager.execute_safe_select(sql)
            return {
                "status": "success", "question": question, "answer": self._format_rows(rows),
                "context_used": sql is not None, "fast_path": False,
                "local_nlp": self._local_nlp_sql(question) is not None,
            }
        except OperationalError:
            # Do not make the UI look like the model failed when the database is
            # unavailable. Connection credentials are deployment configuration,
            # not a user-question error.
            logger.warning("Database unavailable while answering a question")
            return {
                "status": "success", "question": question,
                "answer": "I cannot reach the data source right now. Please check the PostgreSQL connection settings, then try again.",
                "context_used": False, "fallback": True, "database_unavailable": True,
            }
        except Exception as error:
            logger.warning("Question could not be completed: %s", error)
            return {
                "status": "success", "question": question,
                "answer": self._local_nlp_response(question),
                "context_used": False, "fallback": True, "local_nlp": True,
            }

    def _fast_path_answer(self, question):
        """Serve frequent dashboard questions directly from the database."""
        normalized = " ".join(re.sub(r"[^a-z0-9 ]", " ", question.lower()).split())
        if normalized in {"hello", "hi", "hey", "good morning", "good afternoon"}:
            return self._instant_response(question, "Hello. Ask me about sales, revenue, or customers.")
        if normalized in {"thanks", "thank you", "thx"}:
            return self._instant_response(question, "You are welcome!")
        if normalized in {"help", "what can you do"}:
            return self._instant_response(question, "I can analyze sales, products, customers, regions, and order metrics.")

        query, answer_template = None, None
        if "sales order" in normalized or "show orders" in normalized:
            query = "SELECT order_id, customer_id, product, amount, order_date FROM orders ORDER BY order_date DESC"
        elif "total revenue" in normalized or "total sales" in normalized or normalized == "revenue":
            query, answer_template = "SELECT COALESCE(SUM(amount), 0) AS total_revenue FROM orders", "Total revenue is ${:,.2f}."
        elif "sales by product" in normalized or "revenue by product" in normalized or normalized in {"sales", "sales report"}:
            query = "SELECT product, SUM(amount) AS revenue FROM orders GROUP BY product ORDER BY revenue DESC"
        elif ("region" in normalized and "customer" in normalized) or normalized in {"customers", "regions"}:
            query = "SELECT region, COUNT(*) AS customer_count FROM customers GROUP BY region ORDER BY customer_count DESC"
        elif "average" in normalized and "order" in normalized and "amount" in normalized:
            query = "SELECT product, AVG(amount) AS average_amount FROM orders GROUP BY product ORDER BY average_amount DESC"
        elif "how many" in normalized and "order" in normalized:
            query, answer_template = "SELECT COUNT(*) AS order_count FROM orders", "There are {} orders in total."
        if query is None:
            return None

        rows = self.db_manager.execute_safe_select(query)
        if answer_template:
            key = "total_revenue" if "total_revenue" in rows[0] else "order_count"
            value = float(rows[0][key]) if key == "total_revenue" else rows[0][key]
            answer = answer_template.format(value)
        else:
            answer = self._format_rows(rows)
        return {"status": "success", "question": question, "answer": answer, "context_used": False, "fast_path": True}

    @staticmethod
    def _instant_response(question, answer):
        return {"status": "success", "question": question, "answer": answer, "context_used": False, "fast_path": True}

    def get_database_info(self):
        try:
            schemas = self.db_manager.get_table_schemas()
            return {"status": "success", "tables": list(schemas), "schemas": schemas}
        except Exception as error:
            logger.exception("Failed to retrieve database schema info")
            return {"status": "error", "error": str(error)}
