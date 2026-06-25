import os
import sys
import subprocess
import random
from pathlib import Path
from itertools import combinations
from pysat.formula import CNF
from pysat.solvers import Solver, Cadical195
from aag_to_cnf_v2 import Aiger, main as aag_to_cnf_main
from duplicate.duplicate_aag_v3 import make_duplicate
from define.define_ivs_gates_v2 import define_gates

transalg = "./transalg"
abc = "./abc"
aigtoaig = "aigtoaig"

init_steps = int(sys.argv[1])
gamma_num = int(sys.argv[2])
gamma_len = int(sys.argv[3])
vers = sys.argv[4]

work_dir = Path(f"./grain_enc/grain_v{vers}/grain{vers}_steps{init_steps}_keystream{gamma_len}_ivs{gamma_num}")
work_dir.mkdir(exist_ok=True, parents=True)
program_name = f"grain{vers}-steps{init_steps}-keystream{gamma_len}-ivs{gamma_num}"

if vers == "0":
    keylen = 80
    ivlen = 64
    vers = "0.0"
elif vers == "1":
    keylen = 80
    ivlen = 64
    vers = "1.0"
else:
    keylen = 128
    ivlen = 96

# Шаг 0.0
# Создаём программу для Трансалга с заданными значениями параметров
pattern_program_filename = f'pattern_grain_v{vers}.alg'
program_content = Path(pattern_program_filename).read_text()

gamma_len_pattern = '/* gamma_len */'
init_steps_pattern = '/* init_steps */'
gamma_len_pattern_index = program_content.find(gamma_len_pattern)
program_content = (
    program_content[:gamma_len_pattern_index]
    + str(gamma_len)
    + program_content[gamma_len_pattern_index + len(gamma_len_pattern):]
)
init_steps_pattern_index = program_content.find(init_steps_pattern)
program_content = (
    program_content[:init_steps_pattern_index]
    + str(init_steps)
    + program_content[init_steps_pattern_index + len(init_steps_pattern):]
)
program_filename = f'grain_v{vers}_{init_steps}init_steps_{gamma_len}gamma_len.alg'
program_path = (work_dir / program_filename).write_text(program_content)

print("======= Шаг 0: Запуск transalg ======")
aag0 = work_dir / f"make_aig.aag"
cmd = [transalg, "-i", (work_dir / program_filename), "-o", str(aag0), "--no-optimize", "-f", "aig"]
subprocess.run(cmd, check=True)

print("\n======== Шаг 1: Конвертация AAG -> AIG =======")
aig1 = work_dir / f"make_aig.aig"
subprocess.run([aigtoaig, str(aag0), str(aig1)], check=True)

print("\n======== Шаг 2: Упрощение через ABC (fraig) =======")
aig2 = work_dir / f"simple1.aig"
script_file = work_dir / "abc_commands.abc"
commands = f"""read {aig1}
ps
fraig
r2rs
r2rs
r2rs
fraig
ps
write {aig2}
quit
"""
script_file.write_text(commands)
subprocess.run([abc, "-f", str(script_file)], check=True)
script_file.unlink()

print("\n======== Шаг 3: Конвертация AIG -> AAG =======")
aag1 = work_dir / f"simple1.aag"
subprocess.run(f"{aigtoaig} -a -s {aig2} > {aag1}", shell=True, check=True)

print("\n======== Шаг 4: Дублирование кодировки =======")
aag2 = work_dir / f"duplicate.aag"
make_duplicate(str(aag1), str(aag2), int(keylen), int(gamma_num))

print("\n======== Шаг 5: Расширение кодировки =======")
aag3 = work_dir / f"define_ivs.aag"
define_gates(str(aag2), str(aag3), int(keylen), int(gamma_num), int(ivlen))

print("\n======== Шаг 6: Конвертация AAG -> AIG =======")
aig3 = work_dir / f"aag_to_aig.aig"
subprocess.run([aigtoaig, str(aag3), str(aig3)], check=True)

print("\n======== Шаг 7: Финальное упрощение в ABC =======")
aig_final = work_dir / f"final.aig"
script_file = work_dir / "abc_commands.abc"
commands = f"""read {aig3}
ps
fraig
r2rs
r2rs
r2rs
fraig
ps
write {aig_final}
quit
"""
script_file.write_text(commands)
subprocess.run([abc, "-f", str(script_file)], check=True)
script_file.unlink()

print("\n======== Шаг 8: Конвертация AIG -> AAG =======")
aag4 = work_dir / f"{program_name}-r2rs.aag"
subprocess.run(f"{aigtoaig} -a -s {aig_final} > {aag4}", shell=True, check=True)

print("\n======== Шаг 9: Конвертация AAG -> CNF =======")
final_cnf = work_dir / f"{program_name}-r2rs.cnf"
sys.argv = ["aag_to_cnf_v2.py", "-i", str(aag4), "-o", str(final_cnf), "-s", "0"]
aag_to_cnf_main(len(sys.argv), sys.argv)


print("\n======== Шаг 10: Получение файла для mpi программы ========")

random.seed(0)

file_name = str(final_cnf)
print(file_name)

# get key bits
random_key_bits = []
for i in range(1, keylen+1):
    bit = random.randint(0, 1)
    random_key_bits.append(i if bit==1 else -i)

cnf = Path(file_name).read_text()
formula = CNF(from_file=file_name)
output_bits = ""

outputs_pattern = "c outputs: "
ind_beg = cnf.find(outputs_pattern)
ind_end = cnf.find("\n", ind_beg)
outputs_str = cnf[ind_beg + len(outputs_pattern):ind_end - 1].strip()
output_vars = list(map(int, outputs_str.split()))

with Solver(name='cadical195') as solver:
    solver.append_formula(formula)
    if solver.solve(assumptions=random_key_bits):
        model = solver.get_model()
    for var in output_vars:
        if var in model:
            output_bits += f"{var} 0\n"
        elif -var in model:
            output_bits += f"{-var} 0\n"

output_file = file_name[:-4] + "-fixed-output.cnf"
with open(output_file, "w") as f:
    f.write(cnf)
    f.write(output_bits)