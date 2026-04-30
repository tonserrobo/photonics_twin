import pytest

@pytest.fixture
def si_coeffs():
    return (10.6684293, 0.003043475, 1.54133408,
            0.090912191, 1.287460152, 1218816.0)

@pytest.fixture
def sio2_coeffs():
    return (0.6961663, 0.4079426, 0.8974794,
            0.00467914826, 0.01351206307, 97.9340025)
