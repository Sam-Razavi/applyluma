import os

import pytest
from airflow.models import DagBag


@pytest.fixture(scope="module")
def dagbag():
    """
    Loads the Airflow DagBag from the dags folder.
    """
    dag_folder = os.path.join(os.path.dirname(__file__), "..", "dags")
    return DagBag(dag_folder=dag_folder, include_examples=False)


def test_dagbag_no_import_errors(dagbag):
    """
    Ensures that there are no import errors in any of the DAG files.
    """
    assert (
        len(dagbag.import_errors) == 0
    ), f"DAG import failures: {dagbag.import_errors}"


def test_expected_dags_exist(dagbag):
    """
    Ensures that the critical pipeline DAGs are actually loaded.
    """
    expected_dags = ["scrape_jobs", "transform_jobs"]
    for dag_id in expected_dags:
        assert dag_id in dagbag.dags, f"Missing expected DAG: {dag_id}"


def test_dag_cycle_check(dagbag):
    """
    Tests that no DAG contains a cycle (which would prevent it from running).
    """
    for dag_id, dag in dagbag.dags.items():
        # dag.validate() replaces the removed test_cycle() from Airflow 1.x
        dag.validate()


def test_dag_parameters(dagbag):
    """
    Check that DAGs have required parameters set correctly.
    """
    for dag_id, dag in dagbag.dags.items():
        assert dag.owner == "applyluma", f"DAG {dag_id} has wrong owner"
        # retries is a task-level attribute set via default_args, not on DAG itself
        retries = dag.default_args.get("retries", 0)
        assert retries >= 1, f"DAG {dag_id} should have at least 1 retry"
        assert len(dag.tags) > 0, f"DAG {dag_id} should have tags"
        assert dag.catchup is False, f"DAG {dag_id} should have catchup=False"
