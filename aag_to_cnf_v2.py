import sys


class Aiger:
    def __init__(self):
        self.input_vars = []
        self.output_vars = []
        self.all_vars = set()
        self.all_vars_vec = []
        self.equations = []
        self.pattern_linear_constraints = set()

        self.vars_cnt = 0
        self.input_vars_cnt = 0
        self.latches_cnt = 0
        self.output_vars_cnt = 0
        self.and_equations_cnt = 0

    def read_header(self, fin):
        print(" reading header ... ")
        header = fin.readline().strip()
        while header.startswith('c'):
            header = fin.readline().strip()

        parts = header.split()
        if parts[0] == "aag" and len(parts) == 6:
            self.vars_cnt = int(parts[1])
            self.input_vars_cnt = int(parts[2])
            self.latches_cnt = int(parts[3])
            self.output_vars_cnt = int(parts[4])
            self.and_equations_cnt = int(parts[5])
        else:
            print(
                "error: void read_header(): wrong input format: 'aag' expected but '",
                header,
                "' found",
            )
            exit(1)

        print("ok")

    def read_input(self, fin):
        print(" reading input ... ")
        self.input_vars = []

        for _ in range(self.input_vars_cnt):
            x = fin.readline().strip()
            while x.startswith('c'):
                x = fin.readline().strip()
            x = int(x)

            self.input_vars.append(x)
            if x not in (0, 1):
                self.all_vars.add(x if x % 2 == 0 else x - 1)

        print("ok")

    def read_output(self, fin):
        print(" reading output ... ")
        self.output_vars = []

        for _ in range(self.output_vars_cnt):
            x = fin.readline().strip()
            while x.startswith('c'):
                x = fin.readline().strip()
            x = int(x)

            self.output_vars.append(x)
            if x not in (0, 1):
                self.all_vars.add(x if x % 2 == 0 else x - 1)

        print("ok")

    def read_equations(self, fin):
        print(" reading equations ... ")
        self.equations = []

        for _ in range(self.and_equations_cnt):
            line = fin.readline().strip()
            parts = line.split()
            x, y, z = map(int, parts)
            y, z = min(y, z), max(y, z)

            eq = AndEquation(x, y, z)
            self.equations.append(eq)

            if x not in (0, 1):
                self.all_vars.add(x if x % 2 == 0 else x - 1)
            if y not in (0, 1):
                self.all_vars.add(y if y % 2 == 0 else y - 1)
            if z not in (0, 1):
                self.all_vars.add(z if z % 2 == 0 else z - 1)

        print("ok")

    def read_aig(self, in_filename):
        print("reading from '", in_filename, "' ...")
        with open(in_filename, "r") as fin:
            self.read_header(fin)
            self.read_input(fin)
            self.read_output(fin)
            self.read_equations(fin)

    def aig_to_cnf(self, cnf_filename, vars_map, add):
        print("aig to cnf ... ")
        disjuncts, cnf_output_vars, literals, cnf_vars_cnt = build_cnf_encoding(
            self, vars_map, add
        )
        print_cnf(
            cnf_filename,
            self.input_vars_cnt,
            self.output_vars_cnt,
            self.input_vars,
            cnf_vars_cnt,
            literals,
            cnf_output_vars,
            disjuncts,
            add,
        )
        print("ok")


class AndEquation:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


def init(argc, argv):
    in_filename = ""
    out_filename = ""
    lin_filename = ""
    simple = -1

    i = 1
    while i < argc:
        param = ""
        j = 0
        while j < len(argv[i]) and argv[i][j] != '=':
            param += argv[i][j]
            j += 1

        if param == "--help" or param == "-h":
            print("  -h, --help                               Вывод этой справки и выход.\n")
            print("  -i, --input <file>                       Файл с описанием И-Не графа.\n")
            print("  -o, --output <file>                      Файл для вывода КНФ.\n")
            print("  -s, --simple [0|1]     default=1         0 - вывод доп. информации, выход в последние переменные; 1 - нет.")
            exit(0)

        elif param == "--input" or param == "-i":
            if j == len(argv[i]):
                i += 1
                if i < argc:
                    in_filename = str(argv[i])
                else:
                    print("error: missing value for parameter -i")
                    exit(1)
            else:
                in_filename = argv[i][j + 1:]

        elif param == "--output" or param == "-o":
            if j == len(argv[i]):
                i += 1
                if i < argc:
                    out_filename = str(argv[i])
                else:
                    print("error: missing value for parameter -o")
                    exit(1)
            else:
                out_filename = argv[i][j + 1:]

        elif param == "--simple" or param == "-s":
            if j == len(argv[i]):
                i += 1
                if i < argc:
                    simple = int(argv[i])
                else:
                    print("error: missing value for parameter -s")
                    exit(1)
            else:
                simple = int(argv[i][j + 1:])

        else:
            print("unknown parameter: ", param, "\n")
            exit(1)

        i += 1

    if not in_filename:
        print("error: void init(): parameter -i (--input) is required\n")
        exit(1)

    if not out_filename:
        print("error: void init(): parameter -o (--output) is required\n")
        exit(1)

    if simple not in (0, 1):
        simple = 1
        print("warning: void init(): parameter -s has been set to default value '1'\n")

    return in_filename, out_filename, lin_filename, simple


def aig_lit_to_dimacs_signed(lit, vars_map):
    mapped = vars_map[lit]
    return mapped // 2 if mapped % 2 == 0 else -(mapped // 2)


def build_cnf_encoding(aiger_instance, vars_map, add):
    disjuncts = []
    cnf_output_vars = []
    literals = 0

    # Уже существующие CNF-переменные
    cnf_vars_cnt = len(aiger_instance.all_vars_vec)

    for e in aiger_instance.equations:
        x = aig_lit_to_dimacs_signed(e.x, vars_map)

        y_lit = e.y
        z_lit = e.z

        y_is_const0 = (y_lit == 0)
        y_is_const1 = (y_lit == 1)
        z_is_const0 = (z_lit == 0)
        z_is_const1 = (z_lit == 1)

        y = None if (y_is_const0 or y_is_const1) else aig_lit_to_dimacs_signed(y_lit, vars_map)
        z = None if (z_is_const0 or z_is_const1) else aig_lit_to_dimacs_signed(z_lit, vars_map)

        if y_is_const0 or z_is_const0:
            disjuncts.append([-x])
            literals += 1

        elif y_is_const1 and z_is_const1:
            disjuncts.append([x])
            literals += 1

        elif z_is_const1:
            disjuncts.append([x, -y])
            disjuncts.append([-x, y])
            literals += 4

        elif y_is_const1:
            disjuncts.append([x, -z])
            disjuncts.append([-x, z])
            literals += 4

        else:
            disjuncts.append([-x, y])
            disjuncts.append([-x, z])
            disjuncts.append([x, -y, -z])
            literals += 7

    var_num = cnf_vars_cnt

    if add:
        for out_lit in aiger_instance.output_vars:
            var_num += 1
            cnf_output_vars.append(2 * var_num)

            if out_lit == 0:
                disjuncts.append([-var_num])
                literals += 1
            elif out_lit == 1:
                disjuncts.append([var_num])
                literals += 1
            else:
                x = aig_lit_to_dimacs_signed(out_lit, vars_map)
                disjuncts.append([var_num, -x])
                disjuncts.append([-var_num, x])
                literals += 4

        cnf_vars_cnt = var_num

    else:
        cnf_output_vars = []
        for out_lit in aiger_instance.output_vars:
            if out_lit in (0, 1):
                cnf_output_vars.append(out_lit)
            else:
                cnf_output_vars.append(vars_map[out_lit])

    return disjuncts, cnf_output_vars, literals, cnf_vars_cnt


def print_cnf_header(fout, vars_cnt, disjuncts_cnt):
    fout.write(f"p cnf {vars_cnt} {disjuncts_cnt}\n")


def print_cnf_comments(fout, input_vars_cnt, output_vars_cnt, input_vars, cnf_output_vars, literals):
    print("print_cnf_comments...")
    fout.write(f"c input variables {input_vars_cnt}\n")
    fout.write(f"c output variables {output_vars_cnt}\n")
    fout.write(f"c literals {literals}\n")

    fout.write("c inputs: ")
    for x in input_vars:
        if x == 0:
            value = 0
        elif x == 1:
            value = 1
        elif x & 1:
            value = -(x // 2)
        else:
            value = x // 2
        fout.write(f"{value} ")
    fout.write("\n")

    fout.write("c outputs: ")
    for x in cnf_output_vars:
        if x == 0:
            value = 0
        elif x == 1:
            value = 1
        elif x & 1:
            value = -(x // 2)
        else:
            value = x // 2
        fout.write(f"{value} ")
    fout.write("\n")
    print("ok")


def print_cnf_disjuncts(fout, disjuncts):
    for d in disjuncts:
        for x in d:
            fout.write(f"{x} ")
        fout.write("0\n")


def print_cnf(filename, input_vars_cnt, output_vars_cnt, input_vars, vars_cnt, literals_cnt, cnf_output_vars, disjuncts, add):
    with open(filename, "w") as fout:
        print_cnf_header(fout, vars_cnt, len(disjuncts))
        if add:
            print_cnf_comments(
                fout,
                input_vars_cnt,
                output_vars_cnt,
                input_vars,
                cnf_output_vars,
                literals_cnt,
            )
        print_cnf_disjuncts(fout, disjuncts)


def renumerate(all_vars_vec, vars_map):
    cur_var = 1
    for var in all_vars_vec:
        if var not in vars_map:
            vars_map[var] = 2 * cur_var
            vars_map[var ^ 1] = 2 * cur_var + 1
            cur_var += 1
    return vars_map


def main(argc, argv):
    in_filename, out_filename, linear_constraints_filename, simple = init(argc, argv)

    aiger_instance = Aiger()
    aiger_instance.read_aig(in_filename)

    aiger_instance.all_vars_vec = sorted(aiger_instance.all_vars)
    vars_map = {}
    renumerate(aiger_instance.all_vars_vec, vars_map)

    aiger_instance.aig_to_cnf(out_filename, vars_map, simple ^ 1)


if __name__ == "__main__":
    main(len(sys.argv), sys.argv)