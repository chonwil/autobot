import unittest
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == '__main__':
    # Get the directory containing the tests
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests')

    # Discover all tests in the tests directory
    test_suite = unittest.defaultTestLoader.discover(
        start_dir=test_dir,
        pattern='test*.py'
    )

    # Create a test runner
    runner = unittest.TextTestRunner(verbosity=2)

    # Run the tests
    result = runner.run(test_suite)

    # Exit with a non-zero code if there were failures
    sys.exit(not result.wasSuccessful())