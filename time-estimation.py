import sys
from pathlib import Path
from threading import Thread, BoundedSemaphore
from tempfile import NamedTemporaryFile
from subprocess import run as subprocess_run
from random import randint

# return code:
#   10 - SAT
#   20 - UNSAT

threads_number = 8
thread_limiter = BoundedSemaphore(threads_number)
right_keys_counter = 0


def run_solver(cnf_content, solver_filename, conflicts_limit=None, capture_output=False):
    current_dir = Path(r'.')
    in_file = NamedTemporaryFile(dir=current_dir)
    in_file.write(cnf_content)

    args = [solver_filename, '--relaxed']
    
    if conflicts_limit is not None:
        args += [f'--conflicts={conflicts_limit}']
    
    args += [in_file.name]

    result = subprocess_run(args, capture_output=True)
    retcode = result.returncode
    out = result.stdout if capture_output else None
    
    return (retcode, out)


def compute_outputs_parallel(sample, output_vars, cnf_content, solver_filename):
    output_sample = [None] * len(sample)

    def run_process(i):
        global thread_limiter
        thread_limiter.acquire()

        try:
            print(f'find outputs: {i}', flush=True)
            
            key_lit_bytes = b'\n'.join(map(lambda x: str(x).encode() + b' 0', sample[i]))
            cnf_with_key = cnf_content + b'\n' + key_lit_bytes
            
            retcode, output = run_solver(cnf_with_key, solver_filename, capture_output=True)
            assert(retcode == 10)
            
            literals = []
            first_var = str(output_vars[0]).encode()
            begin_index = output.find(first_var) - 1
            end_index = output.find(b'\nc\n', begin_index)
            
            for var in output_vars:
                var_bytes = str(var).encode()
                
                if output.find(b' ' + var_bytes, begin_index, end_index) != -1:
                    literal_bytes = var_bytes
                else:
                    literal_bytes = str(-var).encode()
                
                literals.append(literal_bytes + b' 0')
            
            output_sample[i] = literals
        finally:
            thread_limiter.release()
    
    threads = []

    for i in range(len(sample)):
        thread = Thread(target=run_process, args=(i, ))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    return output_sample


def measure_time_parallel(key_sample, out_sample, backdoor, cnf_content, solver_filename):
    statuses = [None] * len(key_sample)
    
    def run_process(i):
        global thread_limiter
        thread_limiter.acquire()

        print(f'solve instance: {i}', flush=True)
        
        backdoor_lits = [key_sample[i][j] for j, bit in enumerate(backdoor) if bit == 1]
        backdoor_lit_bytes = b'\n'.join(map(lambda x: str(x).encode() + b' 0', backdoor_lits))
        cnf_with_key = cnf_content + b'\n' + backdoor_lit_bytes
        cnf_with_outputs = cnf_with_key + b'\n' + b'\n'.join(out_sample[i])
        
        retcode, out = run_solver(cnf_with_outputs, solver_filename, capture_output=True)

        model_ind = out.find(b'SATISFIABLE')
        if model_ind != -1:
            model_key_str = out[model_ind: model_ind + 1000].decode().strip().split()
            key_sz = len(backdoor)
            model_key = [-j if str(-j) in model_key_str else j for j in range(1, key_sz + 1)]
            # print(i)
            # print(f'key set:', key_sample[i])
            # print(f'key found:', model_key)
            if key_sample[i] == model_key:
                # print(True)
                global right_keys_counter
                right_keys_counter += 1

        if retcode == 10:  # SAT
            end = out[-200:]
            lines = end.split(b'\n')
            time = lines[-6].split()[-2]
            time = float(time)
            statuses[i] = time
            print(f'ok: {statuses[i]}', flush=True)
        else:  # UNSAT
            statuses[i] = 0
            print(f'!: {i}', flush=True)

        thread_limiter.release()
    
    threads = []

    for i in range(len(key_sample)):
        thread = Thread(target=run_process, args=(i,))
        thread.start()
        threads.append(thread)
    
    for thread in threads:
        thread.join()

    total_time = sum(statuses)
    print(f'right_keys_counter = {right_keys_counter}')

    return total_time / sample_size


def get_average_time(sample, output_vars, backdoor, cnf_bytes, solver_filename):
    output_sample = compute_outputs_parallel(sample, output_vars, cnf_bytes, solver_filename)
    result = measure_time_parallel(sample, output_sample, backdoor, cnf_bytes, solver_filename)
    return result


def main(sample_size, backdoor, cnf_filename, output_vars, solver_filename):
    cnf_file = Path(cnf_filename)
    cnf_bytes = cnf_file.read_bytes()
    
    key_sample = []

    for i in range(sample_size):
        key = []

        for j in range(len(backdoor)):
            var = j + 1
            lit = var if randint(0, 1) == 1 else -var
            key.append(lit)
            
        key_sample.append(key)

    avg_time = get_average_time(key_sample, output_vars, backdoor, cnf_bytes, solver_filename)
    print(avg_time, flush=True)


def parse_dimacs_comments(filename: str) -> tuple[list, list]:
    input_vars_list = None
    output_vars_list = None

    with open(filename, 'r') as fin:
        for line in fin:
            if line[0] == 'p':
                continue

            if line[0] == 'c':
                elems = line.strip().split()
                
                if (elems[1], elems[2]) == ('input', 'vars'):
                    input_vars_list = list(map(int, elems[3:]))
                if (elems[1], elems[2]) == ('output', 'vars'):
                    output_vars_list = list(map(int, elems[3:]))
                
                continue
            
            break
    
    return input_vars_list, output_vars_list


if __name__ == '__main__':
    template_cnf_filename = sys.argv[1]
    sample_size = int(sys.argv[2])
    solver_filename = r'./kissat'

    input_vars, output_vars = parse_dimacs_comments(template_cnf_filename)
    backdoor = [0] * len(input_vars)

    main(sample_size, backdoor, template_cnf_filename, output_vars, solver_filename)
