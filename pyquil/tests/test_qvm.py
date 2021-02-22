import numpy as np
import pytest
from httpx import Client

from rpcq.messages import PyQuilExecutableResponse

from pyquil import Program
from pyquil.api import QVM
from pyquil.api._compiler import _extract_program_from_pyquil_executable_response
from pyquil.api._errors import QVMError
from pyquil.gates import MEASURE, X, CNOT, H
from pyquil.quilbase import Declare, MemoryReference


def test_qvm_run_pqer(qcs_client: Client):
    qvm = QVM(client=qcs_client, gate_noise=[0.01] * 3)
    p = Program(Declare("ro", "BIT"), X(0), MEASURE(0, MemoryReference("ro")))
    p.wrap_in_numshots_loop(1000)
    nq = PyQuilExecutableResponse(program=p.out(), attributes={"num_shots": 1000})
    qvm.load(nq)
    qvm.run()
    qvm.wait()
    bitstrings = qvm.read_memory(region_name="ro")
    assert bitstrings.shape == (1000, 1)
    assert np.mean(bitstrings) > 0.8


def test_qvm_run_just_program(qcs_client: Client):
    qvm = QVM(client=qcs_client, gate_noise=[0.01] * 3)
    p = Program(Declare("ro", "BIT"), X(0), MEASURE(0, MemoryReference("ro")))
    p.wrap_in_numshots_loop(1000)
    qvm.load(p)
    qvm.run()
    qvm.wait()
    bitstrings = qvm.read_memory(region_name="ro")
    assert bitstrings.shape == (1000, 1)
    assert np.mean(bitstrings) > 0.8


def test_qvm_run_only_pqer(qcs_client: Client):
    qvm = QVM(client=qcs_client, gate_noise=[0.01] * 3, requires_executable=True)
    p = Program(Declare("ro", "BIT"), X(0), MEASURE(0, MemoryReference("ro")))
    p.wrap_in_numshots_loop(1000)

    with pytest.raises(TypeError) as e:
        qvm.load(p)
        qvm.run()
        qvm.wait()
    assert e.match(r".*Make sure you have explicitly compiled your program.*")

    nq = PyQuilExecutableResponse(program=p.out(), attributes={"num_shots": 1000})
    qvm.load(nq)
    qvm.run()
    qvm.wait()
    bitstrings = qvm.read_memory(region_name="ro")
    assert bitstrings.shape == (1000, 1)
    assert np.mean(bitstrings) > 0.8


def test_qvm_run_region_declared_and_measured(qcs_client: Client):
    qvm = QVM(client=qcs_client)
    p = Program(Declare("reg", "BIT"), X(0), MEASURE(0, MemoryReference("reg")))
    nq = PyQuilExecutableResponse(program=p.out(), attributes={"num_shots": 100})
    qvm.load(nq).run().wait()
    bitstrings = qvm.read_memory(region_name="reg")
    assert bitstrings.shape == (100, 1)


def test_qvm_run_region_declared_not_measured(qcs_client: Client):
    qvm = QVM(client=qcs_client)
    p = Program(Declare("reg", "BIT"), X(0))
    nq = PyQuilExecutableResponse(program=p.out(), attributes={"num_shots": 100})
    qvm.load(nq).run().wait()
    bitstrings = qvm.read_memory(region_name="reg")
    assert bitstrings.shape == (100, 0)


# For backwards compatibility, we support omitting the declaration for "ro" specifically
def test_qvm_run_region_not_declared_is_measured_ro(qcs_client: Client):
    qvm = QVM(client=qcs_client)
    p = Program(X(0), MEASURE(0, MemoryReference("ro")))
    nq = PyQuilExecutableResponse(program=p.out(), attributes={"num_shots": 100})
    qvm.load(nq).run().wait()
    bitstrings = qvm.read_memory(region_name="ro")
    assert bitstrings.shape == (100, 1)


def test_qvm_run_region_not_declared_is_measured_non_ro(qcs_client: Client):
    qvm = QVM(client=qcs_client)
    p = Program(X(0), MEASURE(0, MemoryReference("reg")))
    nq = PyQuilExecutableResponse(program=p.out(), attributes={"num_shots": 100})

    with pytest.raises(QVMError, match='Bad memory region name "reg" in MEASURE'):
        qvm.load(nq).run().wait()


def test_qvm_run_region_not_declared_not_measured_ro(qcs_client: Client):
    qvm = QVM(client=qcs_client)
    p = Program(X(0))
    nq = PyQuilExecutableResponse(program=p.out(), attributes={"num_shots": 100})
    qvm.load(nq).run().wait()
    bitstrings = qvm.read_memory(region_name="ro")
    assert bitstrings.shape == (100, 0)


def test_qvm_run_region_not_declared_not_measured_non_ro(qcs_client: Client):
    qvm = QVM(client=qcs_client)
    p = Program(X(0))
    nq = PyQuilExecutableResponse(program=p.out(), attributes={"num_shots": 100})
    qvm.load(nq).run().wait()
    assert qvm.read_memory(region_name="reg") is None


def test_roundtrip_pyquilexecutableresponse(compiler):
    p = Program(H(10), CNOT(10, 11))
    pqer = compiler.native_quil_to_executable(p)
    p2 = _extract_program_from_pyquil_executable_response(pqer)
    for i1, i2 in zip(p, p2):
        assert i1 == i2


def test_qvm_version(qcs_client: Client):
    qvm = QVM(client=qcs_client)
    version = qvm.get_version_info()

    def is_a_version_string(version_string: str):
        parts = version_string.split(".")
        try:
            map(int, parts)
        except ValueError:
            return False
        return True

    assert is_a_version_string(version)
