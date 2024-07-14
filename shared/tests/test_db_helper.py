import unittest
import os
from shared.utils import DBHelper
import psycopg2

class TestDBHelper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure the .env file exists with test database credentials
        if not os.path.exists('.env'):
            raise EnvironmentError("Please create a .env file with test database credentials")
        
        cls.db = DBHelper()
        
        # Create a test table
        cls.db.execute_query("""
            CREATE TABLE IF NOT EXISTS test_users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                email VARCHAR(100) UNIQUE,
                age INTEGER
            )
        """)

    @classmethod
    def tearDownClass(cls):
        # Drop the test table
        cls.db.execute_query("DROP TABLE IF EXISTS test_users")
        cls.db.execute_query("DROP TABLE IF EXISTS test_items")
        if os.path.isfile('shared/tmp/temp_schema.sql'):
            os.remove('shared/tmp/temp_schema.sql')

    def setUp(self):
        # Clear the test table before each test
        self.db.execute_query("DELETE FROM test_users")

    def test_insert_and_select_by_id(self):
        id = self.db.insert('test_users', {'name': 'John Doe', 'email': 'john@example.com', 'age': 30})
        user = self.db.select_by_id('test_users', id)
        self.assertEqual(user['name'], 'John Doe')
        self.assertEqual(user['email'], 'john@example.com')
        self.assertEqual(user['age'], 30)

    def test_select_by_attributes(self):
        self.db.insert('test_users', {'name': 'Jane Doe', 'email': 'jane@example.com', 'age': 25})
        users = self.db.select_by_attributes('test_users', {'name': 'Jane Doe'})
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['email'], 'jane@example.com')
        self.assertEqual(users[0]['age'], 25)

    def test_exists(self):
        self.db.insert('test_users', {'name': 'Bob Smith', 'email': 'bob@example.com', 'age': 40})
        self.assertTrue(self.db.exists('test_users', {'email': 'bob@example.com'}))
        self.assertFalse(self.db.exists('test_users', {'email': 'nonexistent@example.com'}))

    def test_update(self):
        self.db.insert('test_users', {'name': 'Alice Johnson', 'email': 'alice@example.com', 'age': 35})
        user = self.db.select_by_attributes('test_users', {'name': 'Alice Johnson'})[0]
        self.db.update('test_users', user['id'], {'name': 'Alice Smith', 'age': 36})
        updated_user = self.db.select_by_id('test_users', user['id'])
        self.assertEqual(updated_user['name'], 'Alice Smith')
        self.assertEqual(updated_user['age'], 36)

    def test_initialize_database(self):
        # Create a temporary schema file
        schema_content = """
        CREATE TABLE IF NOT EXISTS test_items (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100)
        );
        """
        with open('shared/tmp/temp_schema.sql', 'w') as f:
            f.write(schema_content)

        self.db.initialize_database('shared/tmp/temp_schema.sql')
        
        # Check if the table was created
        result = self.db.execute_query("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'test_items')")
        self.assertTrue(result[0]['exists'])

        # Clean up
        self.db.execute_query("DROP TABLE IF EXISTS test_items")
        os.remove('shared/tmp/temp_schema.sql')

    def test_select_by_id_nonexistent(self):
        result = self.db.select_by_id('test_users', 9999)  # Assuming this ID doesn't exist
        self.assertIsNone(result)

    def test_insert_duplicate_unique_field(self):
        self.db.insert('test_users', {'name': 'Test User', 'email': 'test@example.com', 'age': 25})
        with self.assertRaises(psycopg2.IntegrityError):
            self.db.insert('test_users', {'name': 'Another User', 'email': 'test@example.com', 'age': 30})

    def test_select_by_multiple_attributes(self):
        self.db.insert('test_users', {'name': 'John Doe', 'email': 'john@example.com', 'age': 30})
        self.db.insert('test_users', {'name': 'Jane Doe', 'email': 'jane@example.com', 'age': 30})
        users = self.db.select_by_attributes('test_users', {'age': 30, 'name': 'John Doe'})
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['email'], 'john@example.com')

    def test_execute_query_with_params(self):
        self.db.insert('test_users', {'name': 'Param Test', 'email': 'param@example.com', 'age': 40})
        result = self.db.execute_query("SELECT * FROM test_users WHERE name = %s AND age = %s", ('Param Test', 40))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['email'], 'param@example.com')

    def test_execute_query_no_results(self):
        result = self.db.execute_query("SELECT * FROM test_users WHERE name = 'Nonexistent'")
        self.assertEqual(result, [])

if __name__ == '__main__':
    unittest.main()