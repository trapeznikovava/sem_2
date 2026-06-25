# Один слой, один размер чанков, заданный пользователем


#!/usr/bin/env python3.8

import time
import sys
import os
import argparse
import random
import copy
import signal
import json
import pprint
import itertools
import functools
import subprocess
import math
import datetime
#import tempfile
#import shutil
from decimal import Decimal
from mpi4py import MPI
from functools import reduce
from threading import Timer
from itertools import combinations, product
print = functools.partial(print, flush=True)
from statistics import mean, median, variance, pvariance
#from pysat.pb import *
#from pysat.formula import CNF

#Parser
def createParser ():
  parser = argparse.ArgumentParser()
  parser.add_argument('-n', '--name', nargs='?', default = 'lec_CvK_12.cnf', help = 'Path to CNF')
  parser.add_argument('-ni', '--nofintervals', nargs='?', type = int, default = 10000, help = 'Number of intervals')
  parser.add_argument('-tl', '--tasklimit', nargs='?', type = int, default = 1000, help = 'Sample size')
  parser.add_argument('-e', '--encoding_type', nargs='?', type = int, default = 0)
  parser.add_argument('-si', '--shuffle_inputs', nargs='?', type = int, default = False)
  parser.add_argument('-s', '--solver', nargs='?', type = str, default = './kissat2022', help = 'Path to SAT solver')
  parser.add_argument('-ab', '--artborders', nargs='?', type = str, default = 'no_art_borders')
  parser.add_argument('-sf', '--solveflag', nargs='?', type = int, default = 1)
  return parser


class Error(Exception):
  pass


def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

def round_up(number): return int(number) + (number % 1 > 0)

def getCNF(from_file):
  dimacs = open(from_file).readlines()
  clauses = []
  header = None
  comments = []
  inputs = []
  vars_left = []
  outputs_first = []
  vars_right = []
  outputs_second = []
  miter_vars = []
  cubes_vars = []
  outputs = []
  gates_vars = []
  var_set = []
  for i in range(len(dimacs)):
    if dimacs[i][0] == 'p':
      header = dimacs[i][:-1] if dimacs[i][-1] == '\n' else dimacs[i]
    elif dimacs[i][0] == 'c':
      comments.append(dimacs[i][:-1] if dimacs[i][-1] == '\n' else dimacs[i])
      if 'c inputs: ' in dimacs[i]:
        inputs = list(map(int, dimacs[i].split(':')[1].split()))
      elif 'c variables for gates in first scheme' in dimacs[i]:
        vars_right = [x for x in range(int(dimacs[i].split()[-3]), int(dimacs[i].split()[-1])+1)]
      elif 'c outputs first scheme' in dimacs[i]:
        outputs_first = list(map(int, dimacs[i].split(':')[1].split()))
      elif 'c variables for gates in second scheme' in dimacs[i]:
        vars_left = [x for x in range(int(dimacs[i].split()[-3]), int(dimacs[i].split()[-1])+1)]
      elif 'c outputs second scheme' in dimacs[i]:
        outputs_second = list(map(int, dimacs[i].split(':')[1].split()))
      elif 'c miter variables' in dimacs[i]:
        miter_vars = list(map(int, dimacs[i].split(':')[1].split()))
      elif 'c cubes variables:' in dimacs[i]:
        cubes_vars = list(map(int, dimacs[i].split(':')[1].split()))
      elif 'c outputs: ' in dimacs[i]:
        outputs = list(map(int, dimacs[i].split(':')[1].split()))
      elif 'c variables for gates:' in dimacs[i]:
        gates_vars = [x for x in range(int(dimacs[i].split()[-3]), int(dimacs[i].split()[-1])+1)]
      elif 'c var_set:' in dimacs[i]:
        var_set = list(map(int, dimacs[i].split(':')[1].split()))
    else:
      if len(dimacs[i]) > 1:
        clauses.append(list(map(int,dimacs[i].split()[:-1])))
  return header, comments, inputs, outputs, gates_vars, vars_left, outputs_first, vars_right, outputs_second, miter_vars, cubes_vars, var_set, clauses

def make_pairs(*lists):
    for t in combinations(lists, 2):
        for pair in product(*t):
            yield pair

def dump_cnf(task_index, current_range, clauses, input_vars, weights, max_var, solver, encoding_type, cnf_name):
  lower_bound = current_range[0]
  upper_bound = current_range[-1]
  new_clauses = encode_rel(input_vars, 'both', tuple([lower_bound,upper_bound]))
  cnf_str = create_str_CNF(clauses, new_clauses, max_var)
  new_clauses_str = create_str_CNF([], new_clauses, max_var)
  subtask_cnf_name = 'PBR_direct_' + name_with_params + '_subtask_' + str(task_index) + '.cnf'
  subtask_clauses_name = 'PBR_direct_' + name_with_params + '_subtask_' + str(task_index) + '.clauses'
  print(cnf_str, file = open(subtask_cnf_name,'w'))
  print(new_clauses_str, file = open(subtask_clauses_name,'w'))

def solve_range(task_index, current_range, clauses, input_vars, weights, max_var, solver, encoding_type):
  lower_bound = current_range[0]
  upper_bound = current_range[-1]
  new_clauses = encode_rel(input_vars, 'both', tuple([lower_bound,upper_bound]))
  answer, solvetime, conflicts = create_and_solve_CNF(task_index, clauses, new_clauses, max_var, solver)
  return answer, solvetime, conflicts


def create_and_solve_CNF(task_index, clauses, new_clauses, max_var, solver):
  cnf_str = create_str_CNF(clauses, new_clauses, max_var)
  #print(cnf_str, file = open('subtask'+str(task_index)+'.cnf','w'))
  result = solve_CNF(cnf_str, solver)
  answer = 'INDET'
  solvetime = None
  conflicts = None
  for line in result:
    if len(line) > 0 and line[0] == 's':
      if 'UNSAT' in line:
        answer = 'UNSAT'
      elif 'SAT' in line:
        answer = 'SAT'
    elif ('c process-time' in line and 'kissat' in solver) or ('c total process time' in line and 'cadical' in solver) or ('c CPU time' in line):
      solvetime = float(line.split()[-2])
    elif ('c conflicts:' in line and 'kissat' in solver) or ('c conflicts:' in line and 'cadical' in solver):
      conflicts = int(line.split()[-4])
    elif ('c conflicts ' in line):
      conflicts = int(line.split()[3])
  return answer, solvetime, conflicts


def create_str_CNF(clauses, new_clauses, max_var):
    lines = []
    header_ = 'p cnf ' + str(max_var) + ' ' + str(len(clauses)+len(new_clauses))
    lines.append(header_)
    lines.extend([' '.join(list(map(str,clause))) + ' 0' for clause in clauses])
    lines.extend([' '.join(list(map(str,clause))) + ' 0' for clause in new_clauses])
    cnf = '\n'.join(lines)
    return cnf


def solve_CNF(cnf, solver):
  params = ["./" + solver]
  if 'kissat' in solver:
    params.append('--relaxed')
  solver = subprocess.run(params, capture_output=True, text=True, input = cnf)
  result = solver.stdout.split('\n')
  errors = solver.stderr
  #print(result)
  if len(errors) > 0:
    return ['ERR', errors]
  return result

def solve_CNF_timelimit(cnf, solver, timelim):
  solver = subprocess.run(["./" + solver, '--time=' + str(timelim), '--relaxed'], capture_output=True, text=True, input = cnf)
  result = solver.stdout.split('\n')
  errors = solver.stderr
  #print(result)
  if len(errors) > 0:
    print(errors)
  return result

def len_loop(clist):
    counter = 0
    for item in clist:
        counter += 1
    return counter

def make_ranges(input_vars, nof_ranges, art_borders):
    if art_borders == 'no_art_borders':
        l_border = 0
        r_border = 2**len(input_vars)
    else:
        if 'v' in art_borders.split('-')[0]:
            l_border = int(art_borders.split('-')[0].split('v')[0])**int(art_borders.split('-')[0].split('v')[1])
        else:
            l_border = int(art_borders.split('-')[0])
        if 'v' in art_borders.split('-')[1]:
            r_border = int(art_borders.split('-')[1].split('v')[0])**int(art_borders.split('-')[1].split('v')[1])
        else:
            r_border = int(art_borders.split('-')[1])
    l = range(l_border, r_border)
    n = r_border - l_border
    k = nof_ranges
    return [l[i * (n // k) + min(i, n % k):(i+1) * (n // k) + min(i+1, n % k)] for i in range(k)]

def make_i_range(input_vars, nof_ranges, art_borders, i):
    if art_borders == 'no_art_borders':
        l_border = 0
        r_border = 2**len(input_vars)
    else:
        if 'v' in art_borders.split('-')[0]:
            l_border = int(art_borders.split('-')[0].split('v')[0])**int(art_borders.split('-')[0].split('v')[1])
        else:
            l_border = int(art_borders.split('-')[0])
        if 'v' in art_borders.split('-')[1]:
            r_border = int(art_borders.split('-')[1].split('v')[0])**int(art_borders.split('-')[1].split('v')[1])
        else:
            r_border = int(art_borders.split('-')[1])
    l = range(l_border, r_border)
    n = r_border - l_border
    k = nof_ranges
    return l[i * (n // k) + min(i, n % k):(i+1) * (n // k) + min(i+1, n % k)]

def make_random_range(input_vars, nof_ranges, art_borders):
    rand_index = random.randint(0, nof_ranges)
    return make_i_range(input_vars, nof_ranges, art_borders, rand_index), rand_index

######################################################################################################
##----------------------------------------UTILITY FUNCTIONS-----------------------------------------##
######################################################################################################

def str2bits(s):
    return [{'1': True, '0': False}[c] for c in s]

def bits2str(bits):
    return ''.join(str(int(b)) for b in bits)

def num2str(x, n):
    # return bin(x)[2:].rjust(n, '0')
    return f"{x:0{n}b}"

def num2bits(x, n):
    return str2bits(num2str(x, n))

def bits2num(bits):
    return int(bits2str(bits), 2)

######################################################################################################
##----------------------------------------ENCODING FUNCTIONS----------------------------------------##
######################################################################################################

def _encode_geq(x, a):
    assert len(x) == len(a)

    if len(x) == 0:
        return []

    clauses = []
    assert isinstance(a[0], bool)
    if a[0]:
        clauses.append([x[0]])
        clauses.extend(_encode_geq(x[1:], a[1:]))
    else:
        # Append (x=1) to all sub-clauses:
        for clause in _encode_geq(x[1:], a[1:]):
            clauses.append([x[0]] + clause)
    return clauses


def _encode_leq(x, b):
    assert len(x) == len(b)

    if len(x) == 0:
        return []

    clauses = []
    assert isinstance(b[0], bool)
    if not b[0]:
        clauses.append([-x[0]])
        clauses.extend(_encode_leq(x[1:], b[1:]))
    else:
        # Append (x=0) to all sub-clauses:
        for clause in _encode_leq(x[1:], b[1:]):
            clauses.append([-x[0]] + clause)
    return clauses


def _encode_both(x, a, b):
    assert len(x) == len(a)
    assert len(x) == len(b)

    if len(x) == 0:
        return []

    clauses = []
    assert isinstance(a[0], bool)
    assert isinstance(b[0], bool)
    if a[0]:
        assert b[0]
        clauses.append([x[0]])
        clauses.extend(_encode_both(x[1:], a[1:], b[1:]))
    elif not b[0]:
        assert not a[0]
        clauses.append([-x[0]])
        clauses.extend(_encode_both(x[1:], a[1:], b[1:]))
    else:
        assert not a[0]
        assert b[0]
        # Append (x=1) to all sub-clauses:
        for clause in _encode_geq(x[1:], a[1:]):
            clauses.append([x[0]] + clause)
        # Append (x=0) to all sub-clauses:
        for clause in _encode_leq(x[1:], b[1:]):
            clauses.append([-x[0]] + clause)
    return clauses


######################################################################################################
##----------------------------------------HIGH-LEVEL WRAPPER----------------------------------------##
######################################################################################################

def encode_rel(lits, mode, bound):
    """
    Returns a list of clauses encoding the fact `x _rel_ bound`, where:
    - `rel` is either `>=` (`mode='geq'`) or `<=` (`mode='leq'`),
    - `lits` are the bits of `x` (note: `lits[0]` is MSB).
    """

    n = len(lits)
    #print(f"=== Encoding '{mode}' for n = {n}, bound = {bound}")
    if mode == "geq":
        assert 0 <= bound < 2**n
        a = num2bits(bound, n)
        return _encode_geq(lits, a)
    elif mode == "leq":
        assert 0 <= bound < 2**n
        a = num2bits(bound, n)
        return _encode_leq(lits, a)
    elif mode == "both":
        if isinstance(bound, tuple):
            (min_bound, max_bound) = bound
            assert 0 <= min_bound < 2**n
            assert 0 <= max_bound < 2**n
        else:
            assert 0 <= bound < 2**n
            min_bound = max_bound = bound
        a = num2bits(min_bound, n)
        b = num2bits(max_bound, n)
        return _encode_both(lits, a, b)

######################################################################################################
##-----------------------------------------------MAIN-----------------------------------------------##
######################################################################################################


if __name__ == "__main__":
  # Define MPI message tags
  tags = enum('READY', 'START', 'DONE', 'EXIT')
  comm = MPI.COMM_WORLD
  rank = comm.Get_rank()
  size = comm.size
  status = MPI.Status()
  if rank == 0:
    start_time = MPI.Wtime()
    parser = createParser()
    namespace = parser.parse_args (sys.argv[1:])
    # Получаем КНФ из файла
    # cnf = [0 header, 1 inputs, 2 vars_first, 3 outputs_first, 4 vars_second, 5 outputs_second, 6 mut_gate, 7 mut_var, 8 clauses]
    filename = namespace.name
    cnf_name = ''.join(filename.split('/')[-1].split('.')[:-1])

    solver = namespace.solver
    encoding_type = namespace.encoding_type
    solve_flag = namespace.solveflag
    art_borders = namespace.artborders
    shuffle_inputs = False if namespace.shuffle_inputs == False else True



    # Считываем LEC КНФ из файла
    header, comments, inputs, outputs, gates_vars, vars_left, outputs_first, vars_right, outputs_second, miter_vars, current_buckets, var_set, clauses = getCNF(from_file = filename)
    max_var = int(header.split()[2])
    if shuffle_inputs == True:
      random.shuffle(inputs)

    nof_ranges = min(namespace.nofintervals, pow(2,len(inputs)))
    task_limit = min(namespace.tasklimit, nof_ranges)

    weights = [2**x for x in reversed(range(len(inputs)))]

    name_with_params = cnf_name+'_'+str(nof_ranges)+'intervals_' + str(task_limit)+'sample_'+str(art_borders)+'_'+str(namespace.shuffle_inputs)+'si'


  else:
    solver = None
    max_var = None
    clauses = None
    inputs = None
    encoding_type = None
    weights = None
    solve_flag = None
    name_with_params = None

  solver = comm.bcast(solver, root=0)
  clauses = comm.bcast(clauses, root=0)
  max_var = comm.bcast(max_var, root=0) 
  inputs = comm.bcast(inputs, root=0) 
  encoding_type = comm.bcast(encoding_type, root=0) 
  weights = comm.bcast(weights, root=0) 
  solve_flag = comm.bcast(solve_flag, root=0) 
  name_with_params = comm.bcast(name_with_params, root=0) 

  if rank == 0:
      # Master process executes code below
      task_index = 0
      num_workers = size - 1
      sats = []
      unsats = []
      closed_workers = 0
      results_table = []
      logfile_name = 'tmp_log_ID_PBI_direct_'
      logfile_name += name_with_params
      logfile_name += '.log'
      with open(logfile_name, 'w') as f:
        print('Master starting with %d workers and %d tasks' % (num_workers, nof_ranges), file = f)
        print('Name with params:', name_with_params, file = f)
        print('Inputs:', inputs, file = f)
        print('Artificial borders:', art_borders, file = f)
        print('Weights:', ['{:.2e}'.format(Decimal(x)) for x in weights], file = f)
        #print('Ranges:', ['range('+'{:.2e}'.format(Decimal(x[0]))+', '+'{:.2e}'.format(Decimal(x[-1]))+')' for x in ranges], file = f)
        #print('Ranges:', ranges, file = f)
        print('Number of intervals:', nof_ranges, file = f)
        if task_limit == nof_ranges:
          print('Full solving. Number of tasks:', task_limit, file = f)
        else:
          print('Sample size:', task_limit, file = f)
        while closed_workers < num_workers:
            data = comm.recv(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG, status=status)
            source = status.Get_source()
            tag = status.Get_tag()
            if tag == tags.READY:
                # Worker is ready, so send it a task
                if task_index < task_limit:
                    print('', file = f)
                    if task_limit == nof_ranges:
                        task = (task_index, make_i_range(inputs, nof_ranges, art_borders, task_index))
                        range_index = task_index
                    else:
                        random_range, range_index = make_random_range(inputs, nof_ranges, art_borders)
                        task = (task_index, random_range)
                    comm.send(task, dest=source, tag=tags.START)
                    print('Sending task %d (range %d) to worker %d (current runtime % 6.2f)' % (task_index, range_index, source, (MPI.Wtime() - start_time)), file = f)
                    print(task, file = f)
                    task_index += 1
                else:
                    comm.send(None, dest=source, tag=tags.EXIT)
            elif tag == tags.DONE:
                print('', file = f)
                print('Got data from worker %d (current runtime % 6.2f)' % (source,(MPI.Wtime() - start_time)), file = f)
                print(data, file = f)
                results_table.append(data)
                if 'UNSAT' in data[3]:
                  unsats.append(data[1])
                elif 'SAT' in data[3]:
                  sats.append(data[1])
                  print('SAT finded', file = f)
                  #task_index = task_limit
                if len(results_table) > 1:
                    current_avg_solvetime = round(sum([x[1] for x in results_table])/len(results_table), 2)
                    current_avg_conflicts = round(sum([x[2] for x in results_table])/len(results_table), 2)
                    print('Current time estimate: ', current_avg_solvetime*nof_ranges, '\nVariance of time:', round(variance([x[1] for x in results_table]),2), '\nStandard deviation of time:', round(math.sqrt(variance([x[1] for x in results_table])),2), '\nCurrent ratio:', (current_avg_conflicts*nof_ranges)/pow(2,len(inputs)), file = f)
            elif tag == tags.EXIT:
                print('Worker %d exited.' % source, file = f)
                closed_workers += 1
        print('Master finishing', file = f)
        print('Total runtime:', MPI.Wtime() - start_time, 'on', size, 'cores', file = f)
        print('', file = f)
        res_time_ = [x[1] for x in results_table]
        avg_solvetime = round(sum(res_time_)/len(results_table), 2)
        res_conflicts_ = [x[2] for x in results_table]
        avg_conflicts = round(sum(res_conflicts_)/len(results_table), 2)
        print('CNF name:', cnf_name, file = f)
        print('Solver:', solver, file = f)
        print('Solved (all)', len(results_table), 'tasks.', file = f)
        print('Decomposition type: PBR_direct', file = f)
        print('Total tasks:', nof_ranges, file = f)
        print('Average solvetime:',avg_solvetime, file = f)
        print('Median time:', round(median(res_time_),2), file = f)
        print('Min solvetime:',round(min(res_time_),2), file = f)
        print('Max solvetime:',round(max(res_time_),2), file = f)
        print('Variance of time:', round(variance(res_time_),2), file=f)
        if len(results_table) == nof_ranges:
          print('Sigma:', round(math.sqrt(variance(res_time_)),2), file=f)
          print('Real time for solving all tasks is ', sum(res_time_), sep = '', file = f)
        else:
          print('Sd:', round(math.sqrt(variance(res_time_)),2), file=f)
          print('Estimate time for solving all tasks is ', avg_solvetime*nof_ranges, sep = '', file = f)
          print()
        print('Average number of conflicts:',avg_conflicts, file = f)
        print('Median number of conflicts:', round(median(res_conflicts_),2), file = f)
        print('Min number of conflicts:',min(res_conflicts_), file = f)
        print('Max number of conflicts:',max(res_conflicts_), file = f)
        print('Variance of number of conflicts:', round(variance(res_conflicts_),2), file=f)
        if len(results_table) == nof_ranges:
          print('Real total number of conflicts for solving all tasks is ', sum(res_conflicts_), sep = '', file = f)
          print('(Number of conflicts / Brutforce actions) ratio:', round(sum(res_conflicts_)/pow(2,len(inputs)),10), file = f)
        else:
          print('Estimate number of conflicts for solving all tasks is ', avg_conflicts*nof_ranges, sep = '', file = f)
          print('(Number of conflicts / Brutforce actions) ratio:', round((avg_conflicts*nof_ranges)/pow(2,len(inputs)),10), file = f)
        print('Number of SATs:', len(sats), file = f)
        if len(sats) > 0:
          print('SATs total runtime:', sum(sats), file = f)
          print('SATs average runtime:', mean(sats), file = f)
          print('SATs median runtime:', median(sats), file = f)
          print('SATs variance of runtime:', variance(sats), file = f)
        print('Number of UNSATs:', len(unsats), file = f)
        if len(unsats) > 0:
          print('UNSATs total runtime:', sum(unsats), file = f)
          print('UNSATs average runtime:', mean(unsats), file = f)
          print('UNSATs median runtime:', median(unsats), file = f)
          print('UNSATs variance of runtime:', variance(unsats), file = f)
  else:
      # Worker processes execute code below
      name = MPI.Get_processor_name()
      #print("I am a worker with rank %d on %s." % (rank, name))
      while True:
          comm.send(None, dest=0, tag=tags.READY)
          task = comm.recv(source=0, tag=MPI.ANY_TAG, status=status)
          tag = status.Get_tag()
          if tag == tags.START:
              # Do the work here
              #starttime = MPI.Wtime()
              if solve_flag == 1:
                  answer, solvetime, conflicts = solve_range(task[0], task[1], clauses, inputs, weights, max_var, solver, encoding_type)
                  comm.send(tuple([task[1], solvetime, conflicts, answer]), dest=0, tag=tags.DONE)
              else:
                  dump_cnf(task[0], task[1], clauses, inputs, weights, max_var, solver, encoding_type, name_with_params)
                  comm.send(tuple([task[1], 1, 1, 'False']), dest=0, tag=tags.DONE)
          elif tag == tags.EXIT:
              break
      comm.send(None, dest=0, tag=tags.EXIT)

