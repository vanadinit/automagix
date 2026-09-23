import pytest

@pytest.fixture(scope="session")
def docker_setup():
    return ["up -d"]
