# qkd_bb84.py - BB84 Quantum Key Distribution simulated generation

from qiskit import QuantumCircuit
import numpy as np
import hashlib

def bb84_shared_key_ibm(key_length=64, debug=False):
    max_attempts = 5
    attempt = 0
    while attempt < max_attempts:
        n = key_length * 2
        alice_bits = np.random.randint(2, size=n)
        alice_bases = np.random.randint(2, size=n)
        bob_bases = np.random.randint(2, size=n)
        qc = QuantumCircuit(n, n)
        for i in range(n):
            if alice_bits[i] == 1:
                qc.x(i)
            if alice_bases[i] == 1:
                qc.h(i)
        for i in range(n):
            if bob_bases[i] == 1:
                qc.h(i)
        qc.measure(range(n), range(n))
        matches = (alice_bases == bob_bases)
        shared_alice = alice_bits[matches]
        agreed = shared_alice
        if len(agreed) >= key_length:
            break
        attempt += 1
    if len(agreed) < key_length:
        raise RuntimeError(f"Failed to generate enough matched bits after {max_attempts} attempts.")
    if debug:
        print(qc.draw(output="text"))
    final_bits = agreed[:key_length]
    bit_string = ''.join(str(int(b)) for b in final_bits)
    key_bytes = hashlib.sha256(bit_string.encode()).digest()
    return key_bytes
